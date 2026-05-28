"""
Tests for DBValidator — validating pre-built database artifacts.

Unit tests use minimal SQLite files with injected metadata — no real CV repos needed.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from esgvoc.admin.validator import DBValidator, ValidationResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_db(path: Path, metadata: dict | None = None, tables: dict[str, int] | None = None) -> Path:
    """Create a minimal SQLite DB with optional metadata and table stubs."""
    conn = sqlite3.connect(str(path))
    conn.execute(
        "CREATE TABLE IF NOT EXISTS _esgvoc_metadata (key TEXT PRIMARY KEY, value TEXT)"
    )
    if metadata:
        for k, v in metadata.items():
            conn.execute(
                "INSERT OR REPLACE INTO _esgvoc_metadata (key, value) VALUES (?, ?)",
                (k, v),
            )
    if tables:
        for table_name, row_count in tables.items():
            conn.execute(f"CREATE TABLE IF NOT EXISTS {table_name} (id TEXT)")
            for i in range(row_count):
                conn.execute(f"INSERT INTO {table_name} (id) VALUES (?)", (f"row_{i}",))
    conn.commit()
    conn.close()
    return path


_BASE_META = {
    "project_id": "testproject",
    "cv_version": "1.0.0",
    "build_date": "2025-01-01T00:00:00+00:00",
    "esgvoc_version": "4.0.1",
}

_UNIVERSE_META = {
    "project_id": "universe",
    "cv_version": "1.0.0",
    "build_date": "2025-01-01T00:00:00+00:00",
    "esgvoc_version": "4.0.1",
}


# ---------------------------------------------------------------------------
# ValidationResult
# ---------------------------------------------------------------------------

class TestValidationResult:

    def test_starts_passed(self):
        r = ValidationResult()
        assert r.passed

    def test_add_ok_stays_passed(self):
        r = ValidationResult()
        r.add("check1", True, "good")
        assert r.passed

    def test_add_fail_sets_failed(self):
        r = ValidationResult()
        r.add("check1", False, "bad")
        assert not r.passed

    def test_summary_contains_check_names(self):
        r = ValidationResult()
        r.add("alpha", True, "ok")
        r.add("beta", False, "nope")
        s = r.summary()
        assert "alpha" in s
        assert "beta" in s
        assert "FAILED" in s

    def test_summary_passed_when_all_ok(self):
        r = ValidationResult()
        r.add("only_check", True)
        assert "PASSED" in r.summary()


# ---------------------------------------------------------------------------
# DBValidator.validate — basic checks
# ---------------------------------------------------------------------------

class TestValidateBasic:

    def test_missing_file_fails(self, tmp_path):
        v = DBValidator()
        result = v.validate(tmp_path / "nonexistent.db")
        assert not result.passed

    def test_non_sqlite_file_fails(self, tmp_path):
        bad = tmp_path / "bad.db"
        bad.write_text("not a sqlite file")
        v = DBValidator()
        result = v.validate(bad)
        assert not result.passed

    def test_valid_project_db_passes(self, tmp_path):
        db = _make_db(
            tmp_path / "test.db",
            metadata=_BASE_META,
            tables={"pcollections": 2, "pterms": 5},
        )
        v = DBValidator()
        with patch.object(DBValidator, "_check_all_terms_via_api"):
            result = v.validate(db)
        assert result.passed

    def test_valid_universe_db_passes(self, tmp_path):
        db = _make_db(
            tmp_path / "universe.db",
            metadata=_UNIVERSE_META,
            tables={"universes": 1, "udata_descriptors": 3, "uterms": 10},
        )
        v = DBValidator()
        with patch.object(DBValidator, "_check_all_terms_via_api"):
            result = v.validate(db)
        assert result.passed

    def test_missing_metadata_key_fails(self, tmp_path):
        incomplete_meta = {k: v for k, v in _BASE_META.items() if k != "cv_version"}
        db = _make_db(
            tmp_path / "test.db",
            metadata=incomplete_meta,
            tables={"pcollections": 1, "pterms": 1},
        )
        v = DBValidator()
        with patch.object(DBValidator, "_check_all_terms_via_api"):
            result = v.validate(db)
        assert not result.passed

    def test_empty_table_fails(self, tmp_path):
        db = _make_db(
            tmp_path / "test.db",
            metadata=_BASE_META,
            tables={"pcollections": 0, "pterms": 5},
        )
        v = DBValidator()
        with patch.object(DBValidator, "_check_all_terms_via_api"):
            result = v.validate(db)
        assert not result.passed


# ---------------------------------------------------------------------------
# DBValidator.validate — ingestion_errors metadata check
# ---------------------------------------------------------------------------

class TestIngestionErrorsCheck:

    def test_zero_errors_passes(self, tmp_path):
        meta = {**_BASE_META, "ingestion_errors": "0"}
        db = _make_db(tmp_path / "test.db", metadata=meta, tables={"pcollections": 1, "pterms": 1})
        v = DBValidator()
        with patch.object(DBValidator, "_check_all_terms_via_api"):
            result = v.validate(db)
        assert result.passed
        check_names = [c[0] for c in result.checks]
        assert "ingestion_errors" in check_names

    def test_nonzero_errors_fails(self, tmp_path):
        meta = {**_BASE_META, "ingestion_errors": "3"}
        db = _make_db(tmp_path / "test.db", metadata=meta, tables={"pcollections": 1, "pterms": 1})
        v = DBValidator()
        with patch.object(DBValidator, "_check_all_terms_via_api"):
            result = v.validate(db)
        assert not result.passed
        err_check = [c for c in result.checks if c[0] == "ingestion_errors"]
        assert len(err_check) == 1
        assert not err_check[0][1]  # failed
        assert "3 term(s) failed" in err_check[0][2]

    def test_missing_ingestion_errors_key_is_ok(self, tmp_path):
        """If the key is absent (older DB), skip the check — don't fail."""
        db = _make_db(tmp_path / "test.db", metadata=_BASE_META, tables={"pcollections": 1, "pterms": 1})
        v = DBValidator()
        with patch.object(DBValidator, "_check_all_terms_via_api"):
            result = v.validate(db)
        assert result.passed
        check_names = [c[0] for c in result.checks]
        assert "ingestion_errors" not in check_names


# ---------------------------------------------------------------------------
# DBValidator._check_all_terms_via_api
# ---------------------------------------------------------------------------

class TestCheckAllTermsViaApi:

    def _run(self, tmp_path, project_id, result, *, is_universe=False,
             previous_active=None, collections=None, terms_side_effect=None,
             universe_terms=None):
        """Helper to run _check_all_terms_via_api with mocked UserState + API."""
        db = _make_db(tmp_path / "test.db")
        mock_state = MagicMock()
        mock_state.get_active.return_value = previous_active

        mock_user_state_cls = MagicMock()
        mock_user_state_cls.load.return_value = mock_state
        mock_user_state_cls.db_path.return_value = tmp_path / "dbs" / project_id / "_validate_temp.db"

        patches = [
            patch("esgvoc.core.service.user_state.UserState", mock_user_state_cls),
        ]
        if is_universe:
            patches.append(patch("esgvoc.api.get_all_terms_in_universe", return_value=universe_terms or []))
        else:
            patches.append(patch("esgvoc.api.get_all_collections_in_project", return_value=collections or []))
            if terms_side_effect is not None:
                patches.append(patch("esgvoc.api.get_all_terms_in_collection", side_effect=terms_side_effect))

        for p in patches:
            p.start()
        try:
            DBValidator._check_all_terms_via_api(db, project_id, result, is_universe=is_universe)
        finally:
            for p in patches:
                p.stop()

        return mock_state

    def test_project_all_collections_ok(self, tmp_path):
        result = ValidationResult()
        self._run(
            tmp_path, "testproject", result,
            collections=["coll_a", "coll_b"],
            terms_side_effect=[
                [MagicMock(), MagicMock()],  # coll_a: 2 terms
                [MagicMock()],               # coll_b: 1 term
            ],
        )
        assert result.passed
        api_check = [c for c in result.checks if c[0] == "API term instantiation"]
        assert len(api_check) == 1
        assert "3 terms across 2 collections" in api_check[0][2]

    def test_project_collection_failure(self, tmp_path):
        result = ValidationResult()
        self._run(
            tmp_path, "testproject", result,
            collections=["good", "bad"],
            terms_side_effect=[
                [MagicMock()],
                RuntimeError("parse error"),
            ],
        )
        assert not result.passed
        api_check = [c for c in result.checks if c[0] == "API term instantiation"]
        assert "1 collection(s) failed" in api_check[0][2]

    def test_universe_terms_ok(self, tmp_path):
        result = ValidationResult()
        self._run(
            tmp_path, "universe", result,
            is_universe=True,
            universe_terms=[MagicMock()] * 50,
        )
        assert result.passed
        api_check = [c for c in result.checks if c[0] == "API term instantiation"]
        assert "50 universe terms OK" in api_check[0][2]

    def test_restores_previous_active_state(self, tmp_path):
        result = ValidationResult()
        mock_state = self._run(
            tmp_path, "proj", result,
            previous_active="v1.0.0",
            collections=[],
        )
        # Should restore the previous active version
        mock_state.set_active.assert_called_with("proj", "v1.0.0", source="local")

    def test_removes_active_if_none_previously(self, tmp_path):
        result = ValidationResult()
        mock_state = self._run(
            tmp_path, "proj", result,
            previous_active=None,
            collections=[],
        )
        mock_state.remove_active.assert_called_once_with("proj")

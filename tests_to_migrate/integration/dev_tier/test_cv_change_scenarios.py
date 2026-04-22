"""
Dev Tier — CV Change Scenarios (Scenarios 17-20) tests.

Tests simulate the user-visible effects of CV changes across versions:
  - Scenario 17: New institution added in v2 → term appears after version switch
  - Scenario 18: Institution renamed in v2 → old name returns None, new name works
  - Scenario 19: Institution removed in v2 → term returns None in new version
  - Scenario 20: Universe term description updated → description reflects new value

Because both test DBs (v1 and v2) are built from the same repo HEAD (only the
cv_version metadata differs), these scenarios are tested by:
  1. Modifying a copy of the DB directly via sqlite3 to simulate the CV change.
  2. Injecting the modified DB and asserting the expected API behaviour.

Plan scenarios covered:
  DT-163  Scenario 17: new term added in v2 is findable via get_term_in_project
  DT-164  Scenario 17: new term not present in v1 DB returns None
  DT-165  Scenario 17: term count increases when new term is added
  DT-166  Scenario 18: renamed term — old id returns None in updated DB
  DT-167  Scenario 18: renamed term — new id is found in updated DB
  DT-168  Scenario 18: renamed term — old id still works in original DB
  DT-169  Scenario 19: removed term returns None in updated DB
  DT-170  Scenario 19: removed term is found in original DB (baseline)
  DT-171  Scenario 19: term count decreases when term is removed
  DT-172  Scenario 20: updated description reflects new value in updated DB
  DT-173  Scenario 20: original description is unaffected in original DB
"""
from __future__ import annotations

import json
import shutil
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

import esgvoc.api as ev
import esgvoc.core.service as svc
from esgvoc.core.db.connection import DBConnection

_PROJECT_ID = "cmip6"
_INSTITUTION_COLLECTION_PK = 12   # pk of institution_id in cmip6 DB
_INSTITUTION_COLLECTION = "institution_id"
_KNOWN_INSTITUTION_ID = "aer"     # exists in both v1 and v2 DBs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@contextmanager
def _inject(project_db: Path, universe_db: Path | None = None):
    original = svc.current_state
    project_conn = DBConnection(db_file_path=project_db)
    fake_project = SimpleNamespace(db_connection=project_conn)
    if universe_db and universe_db.exists():
        universe_conn = DBConnection(db_file_path=universe_db)
    else:
        universe_conn = None
    svc.current_state = SimpleNamespace(
        projects={_PROJECT_ID: fake_project},
        universe=SimpleNamespace(db_connection=universe_conn),
    )
    try:
        yield
    finally:
        project_conn.engine.dispose()
        if universe_conn:
            universe_conn.engine.dispose()
        svc.current_state = original


def _copy_db(src: Path, dst: Path) -> Path:
    shutil.copy2(src, dst)
    return dst


def _db_term_count(db_path: Path, collection_pk: int) -> int:
    conn = sqlite3.connect(str(db_path))
    try:
        return conn.execute(
            "SELECT COUNT(*) FROM pterms WHERE collection_pk = ?", (collection_pk,)
        ).fetchone()[0]
    finally:
        conn.close()


def _insert_term(db_path: Path, term_id: str, collection_pk: int, term_specs: dict) -> None:
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            "INSERT INTO pterms (id, specs, kind, collection_pk) VALUES (?, ?, ?, ?)",
            (term_id, json.dumps(term_specs), "PLAIN", collection_pk),
        )
        conn.commit()
    finally:
        conn.close()


def _delete_term(db_path: Path, term_id: str) -> None:
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("DELETE FROM pterms WHERE id = ?", (term_id,))
        conn.commit()
    finally:
        conn.close()


def _update_term_description(db_path: Path, term_id: str, new_description: str) -> None:
    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute("SELECT specs FROM pterms WHERE id = ?", (term_id,)).fetchone()
        if row:
            specs = json.loads(row[0])
            specs["description"] = new_description
            conn.execute(
                "UPDATE pterms SET specs = ? WHERE id = ?",
                (json.dumps(specs), term_id),
            )
            conn.commit()
    finally:
        conn.close()


def _new_institution_specs(term_id: str) -> dict:
    return {
        "@context": "https://wcrp-cmip.github.io/WCRP-universe/context/organisation",
        "id": term_id,
        "type": "organisation",
        "drs_name": term_id.upper(),
        "description": f"Scenario 17 test institution: {term_id}",
        "members": [],
    }


# ---------------------------------------------------------------------------
# DT-163  Scenario 17: new term added in v2 is findable
# ---------------------------------------------------------------------------

class TestScenario17NewTermAdded:
    """DT-163/164/165: Scenario 17 — New institution added in new DB version."""

    _NEW_TERM_ID = "new-institution-s17"

    @pytest.fixture
    def augmented_db(self, real_dbs, tmp_path):
        """DB with one extra institution term inserted (simulates v2 with new term)."""
        db_path = _copy_db(real_dbs["v1_path"], tmp_path / "augmented.db")
        _insert_term(
            db_path, self._NEW_TERM_ID,
            _INSTITUTION_COLLECTION_PK,
            _new_institution_specs(self._NEW_TERM_ID),
        )
        return db_path

    def test_new_term_found_in_updated_db(self, augmented_db, universe_db):
        """DT-163: Scenario 17 — added term is returned by get_term_in_project."""
        with _inject(augmented_db, universe_db):
            term = ev.get_term_in_project(_PROJECT_ID, self._NEW_TERM_ID)
        assert term is not None, f"Expected {self._NEW_TERM_ID!r} to be found in augmented DB"

    def test_new_term_has_correct_id(self, augmented_db, universe_db):
        with _inject(augmented_db, universe_db):
            term = ev.get_term_in_project(_PROJECT_ID, self._NEW_TERM_ID)
        assert term.id == self._NEW_TERM_ID

    def test_new_term_absent_in_original_db(self, real_dbs, universe_db):
        """DT-164: Scenario 17 — new term is NOT present in original DB (v1)."""
        with _inject(real_dbs["v1_path"], universe_db):
            term = ev.get_term_in_project(_PROJECT_ID, self._NEW_TERM_ID)
        assert term is None, (
            f"Term {self._NEW_TERM_ID!r} should NOT be in the original v1 DB"
        )

    def test_term_count_increases(self, real_dbs, augmented_db, universe_db):
        """DT-165: Scenario 17 — term count in institution_id increases by 1."""
        original_count = _db_term_count(real_dbs["v1_path"], _INSTITUTION_COLLECTION_PK)
        augmented_count = _db_term_count(augmented_db, _INSTITUTION_COLLECTION_PK)
        assert augmented_count == original_count + 1, (
            f"Expected augmented count {original_count + 1}, got {augmented_count}"
        )

    def test_original_terms_still_accessible(self, augmented_db, universe_db):
        """Adding a new term does not disturb existing terms."""
        with _inject(augmented_db, universe_db):
            term = ev.get_term_in_project(_PROJECT_ID, _KNOWN_INSTITUTION_ID)
        assert term is not None
        assert term.id == _KNOWN_INSTITUTION_ID


# ---------------------------------------------------------------------------
# DT-166/167/168  Scenario 18: renamed term
# ---------------------------------------------------------------------------

class TestScenario18TermRenamed:
    """DT-166/167/168: Scenario 18 — Institution renamed: old id gone, new id found."""

    _OLD_ID = "aer"
    _NEW_ID = "aer-renamed-s18"

    @pytest.fixture
    def renamed_db(self, real_dbs, tmp_path):
        """DB where 'aer' has been renamed to 'aer-renamed-s18' (delete old, insert new)."""
        db_path = _copy_db(real_dbs["v1_path"], tmp_path / "renamed.db")
        # Fetch original specs for the term to rename
        conn = sqlite3.connect(str(db_path))
        row = conn.execute(
            "SELECT specs, collection_pk FROM pterms WHERE id = ?", (self._OLD_ID,)
        ).fetchone()
        conn.close()
        assert row is not None, f"Term {self._OLD_ID!r} not found in source DB"
        specs = json.loads(row[0])
        coll_pk = row[1]
        # Delete old id, insert with new id
        _delete_term(db_path, self._OLD_ID)
        specs["id"] = self._NEW_ID
        _insert_term(db_path, self._NEW_ID, coll_pk, specs)
        return db_path

    def test_old_id_returns_none_after_rename(self, renamed_db, universe_db):
        """DT-166: Scenario 18 — old term id not found in updated DB."""
        with _inject(renamed_db, universe_db):
            term = ev.get_term_in_project(_PROJECT_ID, self._OLD_ID)
        assert term is None, (
            f"Scenario 18: old id {self._OLD_ID!r} should return None after rename"
        )

    def test_new_id_found_after_rename(self, renamed_db, universe_db):
        """DT-167: Scenario 18 — new term id found in updated DB."""
        with _inject(renamed_db, universe_db):
            term = ev.get_term_in_project(_PROJECT_ID, self._NEW_ID)
        assert term is not None, (
            f"Scenario 18: new id {self._NEW_ID!r} should be found after rename"
        )
        assert term.id == self._NEW_ID

    def test_old_id_still_works_in_original_db(self, real_dbs, universe_db):
        """DT-168: Scenario 18 — original DB still has old id (regression guard)."""
        with _inject(real_dbs["v1_path"], universe_db):
            term = ev.get_term_in_project(_PROJECT_ID, self._OLD_ID)
        assert term is not None
        assert term.id == self._OLD_ID

    def test_term_count_unchanged_after_rename(self, real_dbs, renamed_db, universe_db):
        """Renaming preserves term count (delete + insert = net zero)."""
        original_count = _db_term_count(real_dbs["v1_path"], _INSTITUTION_COLLECTION_PK)
        renamed_count = _db_term_count(renamed_db, _INSTITUTION_COLLECTION_PK)
        assert original_count == renamed_count


# ---------------------------------------------------------------------------
# DT-169/170/171  Scenario 19: term removed
# ---------------------------------------------------------------------------

class TestScenario19TermRemoved:
    """DT-169/170/171: Scenario 19 — Institution removed in new DB version."""

    _REMOVED_ID = "aer"

    @pytest.fixture
    def pruned_db(self, real_dbs, tmp_path):
        """DB with 'aer' institution term removed (simulates removal in v2)."""
        db_path = _copy_db(real_dbs["v1_path"], tmp_path / "pruned.db")
        _delete_term(db_path, self._REMOVED_ID)
        return db_path

    def test_removed_term_returns_none(self, pruned_db, universe_db):
        """DT-169: Scenario 19 — removed term returns None in updated DB."""
        with _inject(pruned_db, universe_db):
            term = ev.get_term_in_project(_PROJECT_ID, self._REMOVED_ID)
        assert term is None, (
            f"Scenario 19: removed term {self._REMOVED_ID!r} should return None"
        )

    def test_removed_term_existed_in_original(self, real_dbs, universe_db):
        """DT-170: Scenario 19 — baseline check: term was present before removal."""
        with _inject(real_dbs["v1_path"], universe_db):
            term = ev.get_term_in_project(_PROJECT_ID, self._REMOVED_ID)
        assert term is not None, (
            f"Baseline failed: {self._REMOVED_ID!r} should exist in original DB"
        )

    def test_term_count_decreases_after_removal(self, real_dbs, pruned_db, universe_db):
        """DT-171: Scenario 19 — term count decreases by 1 after removal."""
        original_count = _db_term_count(real_dbs["v1_path"], _INSTITUTION_COLLECTION_PK)
        pruned_count = _db_term_count(pruned_db, _INSTITUTION_COLLECTION_PK)
        assert pruned_count == original_count - 1, (
            f"Expected {original_count - 1} terms after removal, got {pruned_count}"
        )

    def test_other_terms_unaffected_by_removal(self, pruned_db, universe_db):
        """Removing one term does not affect other terms in the collection."""
        with _inject(pruned_db, universe_db):
            all_terms = ev.get_all_terms_in_collection(_PROJECT_ID, _INSTITUTION_COLLECTION)
        ids = {t.id for t in all_terms}
        assert self._REMOVED_ID not in ids
        # Other terms still present
        assert len(ids) > 0


# ---------------------------------------------------------------------------
# DT-172/173  Scenario 20: description updated in universe
# ---------------------------------------------------------------------------

class TestScenario20DescriptionUpdated:
    """DT-172/173: Scenario 20 — Universe term description updated in new version."""

    _TERM_ID = "aer"
    _NEW_DESCRIPTION = "Updated description for Scenario 20 testing — AER organisation"

    @pytest.fixture
    def updated_db(self, real_dbs, tmp_path):
        """DB where 'aer' institution description has been updated."""
        db_path = _copy_db(real_dbs["v1_path"], tmp_path / "updated.db")
        _update_term_description(db_path, self._TERM_ID, self._NEW_DESCRIPTION)
        return db_path

    def test_updated_description_reads_new_value(self, updated_db, universe_db):
        """DT-172: Scenario 20 — updated DB reflects new description."""
        with _inject(updated_db, universe_db):
            term = ev.get_term_in_project(_PROJECT_ID, self._TERM_ID)
        assert term is not None
        assert term.description == self._NEW_DESCRIPTION, (
            f"Expected updated description {self._NEW_DESCRIPTION!r}, got {term.description!r}"
        )

    def test_original_description_unchanged_in_original_db(self, real_dbs, universe_db):
        """DT-173: Scenario 20 — original DB description not affected by update."""
        with _inject(real_dbs["v1_path"], universe_db):
            original_term = ev.get_term_in_project(_PROJECT_ID, self._TERM_ID)
        with_update = _copy_db(real_dbs["v1_path"], Path(real_dbs["v1_path"].parent) / "check-isolation.db")
        _update_term_description(with_update, self._TERM_ID, self._NEW_DESCRIPTION)
        with _inject(real_dbs["v1_path"], universe_db):
            still_original = ev.get_term_in_project(_PROJECT_ID, self._TERM_ID)
        # Original DB should be unaffected
        assert original_term.description == still_original.description
        # Clean up temp file
        with_update.unlink(missing_ok=True)

    def test_description_field_is_accessible(self, real_dbs, universe_db):
        """Scenario 20 prerequisite: description is a first-class field on terms."""
        with _inject(real_dbs["v1_path"], universe_db):
            term = ev.get_term_in_project(_PROJECT_ID, self._TERM_ID)
        assert hasattr(term, "description")

    def test_description_update_does_not_affect_id(self, updated_db, universe_db):
        """Updating description must not change the term id."""
        with _inject(updated_db, universe_db):
            term = ev.get_term_in_project(_PROJECT_ID, self._TERM_ID)
        assert term.id == self._TERM_ID

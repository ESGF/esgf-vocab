"""
Dev Tier — CV change simulation tests using v1 vs v2 DBs.

Both DBs are built from the same cloned repo HEAD but carry different version
metadata (cv_version=1.0.0 for v1, cv_version=2.0.0 for v2), simulating two
successive published releases of the same CV.

Plan scenarios covered:
  DT-89  get_project returns different cv_version for v1 and v2 DBs
  DT-90  v1 and v2 have the same set of term IDs (regression — same source)
  DT-91  v2 DB cv_version is lexically greater than v1 DB cv_version
  DT-92  A known term is retrievable from both v1 and v2 without error
  DT-93  Both DBs expose the same collection list
  DT-94  Both DBs expose the same term count in activity_id
  DT-95  Validation produces identical results against v1 and v2 DBs
  DT-96  _esgvoc_metadata reflects the correct cv_version for each DB
  DT-97  Full DataDescriptor for same term is structurally identical across versions
  DT-98  Switching the injected DB from v1 to v2 changes the reported version
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

import esgvoc.api as ev
import esgvoc.core.service as svc
from esgvoc.core.db.connection import DBConnection

# ---------------------------------------------------------------------------
# Known constants from real cmip6 DB
# ---------------------------------------------------------------------------

_PROJECT_ID = "cmip6"
_KNOWN_COLLECTION = "activity_id"
_KNOWN_TERM = "aerchemmip"
_KNOWN_DRS_VALUE = "AerChemMIP"


# ---------------------------------------------------------------------------
# Context manager (same pattern as other dev_tier tests)
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
    fake_universe = SimpleNamespace(db_connection=universe_conn)

    svc.current_state = SimpleNamespace(
        projects={_PROJECT_ID: fake_project},
        universe=fake_universe,
    )
    try:
        yield
    finally:
        project_conn.engine.dispose()
        if universe_conn:
            universe_conn.engine.dispose()
        svc.current_state = original


# ---------------------------------------------------------------------------
# DT-89  get_project returns different cv_version for v1 and v2 DBs
# ---------------------------------------------------------------------------

class TestVersionMetadataDiffers:
    """DT-89: v1 and v2 DBs carry different cv_version in their metadata."""

    def test_v1_version_is_v1(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            specs = ev.get_project(_PROJECT_ID)
        assert specs is not None
        assert specs.version == "1.0.0", (
            f"Expected v1 DB to report cv_version='1.0.0'; got {specs.version!r}"
        )

    def test_v2_version_is_v2(self, real_dbs, universe_db):
        with _inject(real_dbs["v2_path"], universe_db):
            specs = ev.get_project(_PROJECT_ID)
        assert specs is not None
        assert specs.version == "2.0.0", (
            f"Expected v2 DB to report cv_version='2.0.0'; got {specs.version!r}"
        )

    def test_v1_and_v2_versions_differ(self, real_dbs, universe_db):
        """The two DBs should not report the same version string."""
        with _inject(real_dbs["v1_path"], universe_db):
            specs_v1 = ev.get_project(_PROJECT_ID)
        with _inject(real_dbs["v2_path"], universe_db):
            specs_v2 = ev.get_project(_PROJECT_ID)
        assert specs_v1.version != specs_v2.version, (
            f"v1 and v2 should differ but both report {specs_v1.version!r}"
        )


# ---------------------------------------------------------------------------
# DT-90  v1 and v2 have the same set of term IDs
# ---------------------------------------------------------------------------

class TestTermSetRegressionAcrossVersions:
    """DT-90: Both DBs are built from the same source so term IDs must match."""

    def _collect_term_ids(self, db_path: Path, universe_db: Path) -> set[str]:
        with _inject(db_path, universe_db):
            terms = ev.get_all_terms_in_collection(_PROJECT_ID, _KNOWN_COLLECTION)
        return {t.id for t in terms}

    def test_term_ids_match_between_v1_and_v2(self, real_dbs, universe_db):
        v1_ids = self._collect_term_ids(real_dbs["v1_path"], universe_db)
        v2_ids = self._collect_term_ids(real_dbs["v2_path"], universe_db)
        assert v1_ids == v2_ids, (
            f"Term ID sets differ between v1 and v2.\n"
            f"  Only in v1: {v1_ids - v2_ids}\n"
            f"  Only in v2: {v2_ids - v1_ids}"
        )

    def test_both_versions_have_known_term(self, real_dbs, universe_db):
        v1_ids = self._collect_term_ids(real_dbs["v1_path"], universe_db)
        v2_ids = self._collect_term_ids(real_dbs["v2_path"], universe_db)
        assert _KNOWN_TERM in v1_ids, f"'{_KNOWN_TERM}' missing from v1"
        assert _KNOWN_TERM in v2_ids, f"'{_KNOWN_TERM}' missing from v2"


# ---------------------------------------------------------------------------
# DT-91  v2 DB cv_version is lexically greater than v1 DB cv_version
# ---------------------------------------------------------------------------

class TestVersionOrdering:
    """DT-91: cv_version in v2 DB is numerically greater than in v1 DB."""

    def test_v2_version_greater_than_v1(self, real_dbs, universe_db):
        from packaging.version import Version

        with _inject(real_dbs["v1_path"], universe_db):
            v1_specs = ev.get_project(_PROJECT_ID)
        with _inject(real_dbs["v2_path"], universe_db):
            v2_specs = ev.get_project(_PROJECT_ID)

        try:
            v1 = Version(v1_specs.version)
            v2 = Version(v2_specs.version)
            assert v2 > v1, (
                f"Expected v2 ({v2_specs.version}) > v1 ({v1_specs.version})"
            )
        except Exception:
            # Fallback: string comparison is also acceptable for "1.0.0" vs "2.0.0"
            assert v2_specs.version > v1_specs.version, (
                f"Expected v2 ({v2_specs.version!r}) > v1 ({v1_specs.version!r})"
            )


# ---------------------------------------------------------------------------
# DT-92  A known term is retrievable from both v1 and v2 without error
# ---------------------------------------------------------------------------

class TestTermRetrievableInBothVersions:
    """DT-92: API does not raise when retrieving a known term from either DB."""

    def test_get_term_in_v1_does_not_raise(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            term = ev.get_term_in_collection(_PROJECT_ID, _KNOWN_COLLECTION, _KNOWN_TERM)
        assert term is not None
        assert term.id == _KNOWN_TERM

    def test_get_term_in_v2_does_not_raise(self, real_dbs, universe_db):
        with _inject(real_dbs["v2_path"], universe_db):
            term = ev.get_term_in_collection(_PROJECT_ID, _KNOWN_COLLECTION, _KNOWN_TERM)
        assert term is not None
        assert term.id == _KNOWN_TERM

    def test_get_term_in_project_v1(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            term = ev.get_term_in_project(_PROJECT_ID, _KNOWN_TERM)
        assert term is not None
        assert term.id == _KNOWN_TERM

    def test_get_term_in_project_v2(self, real_dbs, universe_db):
        with _inject(real_dbs["v2_path"], universe_db):
            term = ev.get_term_in_project(_PROJECT_ID, _KNOWN_TERM)
        assert term is not None
        assert term.id == _KNOWN_TERM


# ---------------------------------------------------------------------------
# DT-93  Both DBs expose the same collection list
# ---------------------------------------------------------------------------

class TestCollectionListConsistency:
    """DT-93: Collection IDs are identical in v1 and v2 (same source)."""

    def _get_collection_ids(self, db_path: Path, universe_db: Path) -> set[str]:
        with _inject(db_path, universe_db):
            collections = ev.get_all_collections_in_project(_PROJECT_ID)
        return {c.id for c in collections}

    def test_collection_ids_match(self, real_dbs, universe_db):
        v1_ids = self._get_collection_ids(real_dbs["v1_path"], universe_db)
        v2_ids = self._get_collection_ids(real_dbs["v2_path"], universe_db)
        assert v1_ids == v2_ids, (
            f"Collection ID sets differ.\n"
            f"  Only in v1: {v1_ids - v2_ids}\n"
            f"  Only in v2: {v2_ids - v1_ids}"
        )

    def test_both_have_known_collection(self, real_dbs, universe_db):
        v1_ids = self._get_collection_ids(real_dbs["v1_path"], universe_db)
        v2_ids = self._get_collection_ids(real_dbs["v2_path"], universe_db)
        assert _KNOWN_COLLECTION in v1_ids
        assert _KNOWN_COLLECTION in v2_ids


# ---------------------------------------------------------------------------
# DT-94  Both DBs expose the same term count in activity_id
# ---------------------------------------------------------------------------

class TestTermCountConsistency:
    """DT-94: Term count in activity_id is the same in v1 and v2."""

    def test_same_term_count_in_activity_id(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            v1_terms = ev.get_all_terms_in_collection(_PROJECT_ID, _KNOWN_COLLECTION)
        with _inject(real_dbs["v2_path"], universe_db):
            v2_terms = ev.get_all_terms_in_collection(_PROJECT_ID, _KNOWN_COLLECTION)
        assert len(v1_terms) == len(v2_terms), (
            f"v1 has {len(v1_terms)} terms, v2 has {len(v2_terms)} in {_KNOWN_COLLECTION}"
        )

    def test_term_count_is_positive(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            v1_terms = ev.get_all_terms_in_collection(_PROJECT_ID, _KNOWN_COLLECTION)
        assert len(v1_terms) > 0


# ---------------------------------------------------------------------------
# DT-95  Validation produces identical results against v1 and v2 DBs
# ---------------------------------------------------------------------------

class TestValidationConsistencyAcrossVersions:
    """DT-95: valid_term and valid_term_in_collection produce the same outcome in v1 and v2."""

    def test_valid_term_pass_same_in_v1_and_v2(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            report_v1 = ev.valid_term(
                _KNOWN_DRS_VALUE, _PROJECT_ID, _KNOWN_COLLECTION, _KNOWN_TERM
            )
        with _inject(real_dbs["v2_path"], universe_db):
            report_v2 = ev.valid_term(
                _KNOWN_DRS_VALUE, _PROJECT_ID, _KNOWN_COLLECTION, _KNOWN_TERM
            )
        assert report_v1.validated == report_v2.validated
        assert report_v1.nb_errors == report_v2.nb_errors

    def test_valid_term_in_collection_match_count_same(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            matches_v1 = ev.valid_term_in_collection(
                _KNOWN_DRS_VALUE, _PROJECT_ID, _KNOWN_COLLECTION
            )
        with _inject(real_dbs["v2_path"], universe_db):
            matches_v2 = ev.valid_term_in_collection(
                _KNOWN_DRS_VALUE, _PROJECT_ID, _KNOWN_COLLECTION
            )
        assert len(matches_v1) == len(matches_v2), (
            f"Match counts differ: v1={len(matches_v1)}, v2={len(matches_v2)}"
        )

    def test_valid_term_in_project_match_count_same(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            matches_v1 = ev.valid_term_in_project(_KNOWN_DRS_VALUE, _PROJECT_ID)
        with _inject(real_dbs["v2_path"], universe_db):
            matches_v2 = ev.valid_term_in_project(_KNOWN_DRS_VALUE, _PROJECT_ID)
        assert len(matches_v1) == len(matches_v2)


# ---------------------------------------------------------------------------
# DT-96  _esgvoc_metadata reflects the correct cv_version for each DB
# ---------------------------------------------------------------------------

class TestMetadataTableContent:
    """DT-96: Raw _esgvoc_metadata table stores the correct cv_version for each DB."""

    def _read_metadata(self, db_path: Path) -> dict[str, str]:
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        try:
            rows = conn.execute("SELECT key, value FROM _esgvoc_metadata").fetchall()
            return dict(rows)
        finally:
            conn.close()

    def test_v1_metadata_has_cv_version_1(self, real_dbs):
        meta = self._read_metadata(real_dbs["v1_path"])
        assert "cv_version" in meta, f"Missing 'cv_version' in metadata: {meta}"
        assert meta["cv_version"] == "1.0.0", (
            f"Expected '1.0.0', got {meta['cv_version']!r}"
        )

    def test_v2_metadata_has_cv_version_2(self, real_dbs):
        meta = self._read_metadata(real_dbs["v2_path"])
        assert "cv_version" in meta
        assert meta["cv_version"] == "2.0.0", (
            f"Expected '2.0.0', got {meta['cv_version']!r}"
        )

    def test_metadata_has_project_id(self, real_dbs):
        meta_v1 = self._read_metadata(real_dbs["v1_path"])
        meta_v2 = self._read_metadata(real_dbs["v2_path"])
        assert meta_v1.get("project_id") == _PROJECT_ID
        assert meta_v2.get("project_id") == _PROJECT_ID

    def test_metadata_has_build_date(self, real_dbs):
        meta = self._read_metadata(real_dbs["v1_path"])
        assert "build_date" in meta and meta["build_date"]


# ---------------------------------------------------------------------------
# DT-97  Full DataDescriptor for same term is structurally identical across versions
# ---------------------------------------------------------------------------

class TestTermStructureConsistency:
    """DT-97: Same term from v1 and v2 DBs has identical field structure."""

    def test_term_type_same_in_v1_and_v2(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            term_v1 = ev.get_term_in_collection(_PROJECT_ID, _KNOWN_COLLECTION, _KNOWN_TERM)
        with _inject(real_dbs["v2_path"], universe_db):
            term_v2 = ev.get_term_in_collection(_PROJECT_ID, _KNOWN_COLLECTION, _KNOWN_TERM)
        assert type(term_v1) == type(term_v2), (
            f"Term type differs: v1={type(term_v1).__name__}, v2={type(term_v2).__name__}"
        )

    def test_term_id_same_in_v1_and_v2(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            term_v1 = ev.get_term_in_collection(_PROJECT_ID, _KNOWN_COLLECTION, _KNOWN_TERM)
        with _inject(real_dbs["v2_path"], universe_db):
            term_v2 = ev.get_term_in_collection(_PROJECT_ID, _KNOWN_COLLECTION, _KNOWN_TERM)
        assert term_v1.id == term_v2.id

    def test_term_fields_same_in_v1_and_v2(self, real_dbs, universe_db):
        """Both versions return terms with the same field names."""
        with _inject(real_dbs["v1_path"], universe_db):
            term_v1 = ev.get_term_in_collection(_PROJECT_ID, _KNOWN_COLLECTION, _KNOWN_TERM)
        with _inject(real_dbs["v2_path"], universe_db):
            term_v2 = ev.get_term_in_collection(_PROJECT_ID, _KNOWN_COLLECTION, _KNOWN_TERM)
        v1_fields = set(vars(term_v1).keys())
        v2_fields = set(vars(term_v2).keys())
        assert v1_fields == v2_fields, (
            f"Field sets differ.\n  Only in v1: {v1_fields - v2_fields}\n"
            f"  Only in v2: {v2_fields - v1_fields}"
        )


# ---------------------------------------------------------------------------
# DT-98  Switching the injected DB from v1 to v2 changes the reported version
# ---------------------------------------------------------------------------

class TestVersionSwitching:
    """DT-98: Re-injecting a different DB swaps the version seen by the API."""

    def test_version_changes_when_db_swapped(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            specs_before = ev.get_project(_PROJECT_ID)
        with _inject(real_dbs["v2_path"], universe_db):
            specs_after = ev.get_project(_PROJECT_ID)
        assert specs_before.version != specs_after.version

    def test_api_state_restored_after_context_exit(self, real_dbs, universe_db):
        """After _inject exits, the original state is restored (no cross-test contamination)."""
        original_state = svc.current_state
        with _inject(real_dbs["v1_path"], universe_db):
            pass  # Enter and exit
        assert svc.current_state is original_state, (
            "_inject context manager must restore original current_state"
        )

    def test_sequential_version_injection_is_independent(self, real_dbs, universe_db):
        """Two sequential injections of different versions are independent."""
        with _inject(real_dbs["v1_path"], universe_db):
            v1_version = ev.get_project(_PROJECT_ID).version
        with _inject(real_dbs["v2_path"], universe_db):
            v2_version = ev.get_project(_PROJECT_ID).version
        assert v1_version == "1.0.0"
        assert v2_version == "2.0.0"

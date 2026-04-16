"""
Dev Tier — Data descriptor model field coverage tests.

Covers Scenarios 28/29 (model optional fields, backward compatibility)
and cross-project consistency (Scenario 5).

Scenario 28: Optional fields in DataDescriptors are accessible and
             gracefully return None when not stored in the DB.
Scenario 29: Required fields are present; min/max version compatibility
             is enforced at the fetcher level (already tested in UT-65–70).
Scenario 5:  Multiple projects sharing the same universe: terms retrieved
             from each project have the same id when they come from the
             same universe source.

Plan scenarios covered:
  DT-135  Institution has expected fields: acronyms, labels, location, ror, urls
  DT-136  Optional field ror is accessible (may be None) — Scenario 28
  DT-137  Frequency has drs_name field populated from real DB
  DT-138  Activity term has drs_name populated
  DT-139  get_term_in_collection returns correct concrete class (not just DataDescriptor)
  DT-140  DataDescriptor id matches the queried term_id
  DT-141  Two projects backed by same DB return same term for same universe term_id
  DT-142  get_all_terms_in_collection count is same across two projects sharing a DB
  DT-143  DATA_DESCRIPTOR_CLASS_MAPPING covers all known built-in data descriptor ids
  DT-144  DataDescriptorSubSet only carries id when selected_term_fields=[]
  DT-145  DataDescriptorSubSet carries requested field when it exists in the term
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
# Known constants
# ---------------------------------------------------------------------------

_PROJECT_ID = "cmip6"
_PROJECT_A = "cmip6_a"
_PROJECT_B = "cmip6_b"
_COLLECTION_ACTIVITY = "activity_id"
_COLLECTION_INSTITUTION = "institution_id"
_COLLECTION_FREQUENCY = "frequency"
_TERM_ACTIVITY = "aerchemmip"
_TERM_DRS_ACTIVITY = "AerChemMIP"


# ---------------------------------------------------------------------------
# Context managers
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


@contextmanager
def _inject_two_projects(project_db: Path, universe_db: Path | None = None):
    """Register the same DB under two project IDs — simulates Scenario 5."""
    original = svc.current_state
    conn_a = DBConnection(db_file_path=project_db)
    conn_b = DBConnection(db_file_path=project_db)
    if universe_db and universe_db.exists():
        universe_conn = DBConnection(db_file_path=universe_db)
    else:
        universe_conn = None
    svc.current_state = SimpleNamespace(
        projects={
            _PROJECT_A: SimpleNamespace(db_connection=conn_a),
            _PROJECT_B: SimpleNamespace(db_connection=conn_b),
        },
        universe=SimpleNamespace(db_connection=universe_conn),
    )
    try:
        yield
    finally:
        conn_a.engine.dispose()
        conn_b.engine.dispose()
        if universe_conn:
            universe_conn.engine.dispose()
        svc.current_state = original


# ---------------------------------------------------------------------------
# DT-135  Institution has expected fields
# ---------------------------------------------------------------------------

class TestInstitutionFields:
    """DT-135: Institution DataDescriptor has all expected fields."""

    def _get_first_institution(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            terms = ev.get_all_terms_in_collection(_PROJECT_ID, _COLLECTION_INSTITUTION)
        return next((t for t in terms), None)

    def test_institution_has_id(self, real_dbs, universe_db):
        term = self._get_first_institution(real_dbs, universe_db)
        if term is None:
            pytest.skip("No institutions in DB")
        assert hasattr(term, "id")
        assert term.id

    def test_institution_has_acronyms(self, real_dbs, universe_db):
        term = self._get_first_institution(real_dbs, universe_db)
        if term is None:
            pytest.skip("No institutions in DB")
        assert hasattr(term, "acronyms")
        assert isinstance(term.acronyms, list)

    def test_institution_has_labels(self, real_dbs, universe_db):
        term = self._get_first_institution(real_dbs, universe_db)
        if term is None:
            pytest.skip("No institutions in DB")
        assert hasattr(term, "labels")
        assert isinstance(term.labels, list)

    def test_institution_has_ror(self, real_dbs, universe_db):
        """ror is optional (may be None) — Scenario 28 analog."""
        term = self._get_first_institution(real_dbs, universe_db)
        if term is None:
            pytest.skip("No institutions in DB")
        assert hasattr(term, "ror")
        # ror can be None or a string — both are valid
        assert term.ror is None or isinstance(term.ror, str)

    def test_institution_has_urls(self, real_dbs, universe_db):
        term = self._get_first_institution(real_dbs, universe_db)
        if term is None:
            pytest.skip("No institutions in DB")
        assert hasattr(term, "urls")
        assert isinstance(term.urls, list)


# ---------------------------------------------------------------------------
# DT-136  Optional field ror is accessible and may be None (Scenario 28)
# ---------------------------------------------------------------------------

class TestOptionalFieldGracefulAccess:
    """DT-136: Optional fields in DataDescriptors don't raise when absent."""

    def test_ror_access_does_not_raise(self, real_dbs, universe_db):
        """Accessing ror never raises — it's None or a value."""
        with _inject(real_dbs["v1_path"], universe_db):
            terms = ev.get_all_terms_in_collection(_PROJECT_ID, _COLLECTION_INSTITUTION)
        for term in terms[:5]:  # Check first 5
            try:
                _ = term.ror
            except AttributeError:
                pytest.fail(f"term.ror raised AttributeError for term {term.id!r}")

    def test_none_ror_is_handled(self, real_dbs, universe_db):
        """Terms with ror=None are valid DataDescriptor instances."""
        with _inject(real_dbs["v1_path"], universe_db):
            terms = ev.get_all_terms_in_collection(_PROJECT_ID, _COLLECTION_INSTITUTION)
        none_ror = [t for t in terms if t.ror is None]
        str_ror = [t for t in terms if t.ror is not None]
        # At least some handling is correct — both groups valid
        for term in none_ror[:3]:
            assert term.id
        for term in str_ror[:3]:
            assert term.id and term.ror


# ---------------------------------------------------------------------------
# DT-137  Frequency term has drs_name
# ---------------------------------------------------------------------------

class TestFrequencyFields:
    """DT-137: Frequency DataDescriptor has drs_name populated from real DB."""

    def test_frequency_term_has_drs_name(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            terms = ev.get_all_terms_in_collection(_PROJECT_ID, _COLLECTION_FREQUENCY)
        if not terms:
            pytest.skip("No frequency terms in DB")
        for term in terms[:5]:
            assert hasattr(term, "drs_name"), f"Term {term.id!r} missing drs_name"
            assert term.drs_name  # non-empty

    def test_frequency_terms_have_valid_ids(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            terms = ev.get_all_terms_in_collection(_PROJECT_ID, _COLLECTION_FREQUENCY)
        for term in terms:
            assert term.id


# ---------------------------------------------------------------------------
# DT-138  Activity term has drs_name
# ---------------------------------------------------------------------------

class TestActivityFields:
    """DT-138: Activity DataDescriptor has drs_name populated from real DB."""

    def test_activity_term_has_drs_name(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            term = ev.get_term_in_collection(
                _PROJECT_ID, _COLLECTION_ACTIVITY, _TERM_ACTIVITY
            )
        assert term is not None
        assert hasattr(term, "drs_name")
        assert term.drs_name == _TERM_DRS_ACTIVITY

    def test_all_activity_terms_have_drs_name(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            terms = ev.get_all_terms_in_collection(_PROJECT_ID, _COLLECTION_ACTIVITY)
        for term in terms:
            assert hasattr(term, "drs_name")
            assert term.drs_name  # non-empty


# ---------------------------------------------------------------------------
# DT-139  get_term_in_collection returns concrete class
# ---------------------------------------------------------------------------

class TestConcreteClassReturned:
    """DT-139: API returns a concrete DataDescriptor subclass, not just the base."""

    def test_activity_returns_activity_class(self, real_dbs, universe_db):
        from esgvoc.api.data_descriptors.data_descriptor import DataDescriptor
        with _inject(real_dbs["v1_path"], universe_db):
            term = ev.get_term_in_collection(
                _PROJECT_ID, _COLLECTION_ACTIVITY, _TERM_ACTIVITY
            )
        assert isinstance(term, DataDescriptor)
        # Should be a proper subclass, not base DataDescriptor itself
        assert type(term).__name__ != "DataDescriptor"

    def test_institution_returns_institution_subclass(self, real_dbs, universe_db):
        from esgvoc.api.data_descriptors.data_descriptor import DataDescriptor
        with _inject(real_dbs["v1_path"], universe_db):
            terms = ev.get_all_terms_in_collection(_PROJECT_ID, _COLLECTION_INSTITUTION)
        if not terms:
            pytest.skip("No institution terms in DB")
        assert isinstance(terms[0], DataDescriptor)
        assert type(terms[0]).__name__ != "DataDescriptor"


# ---------------------------------------------------------------------------
# DT-140  DataDescriptor.id matches queried term_id
# ---------------------------------------------------------------------------

class TestDataDescriptorId:
    """DT-140: The id attribute of a returned term always matches the queried id."""

    def test_id_matches_for_known_term(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            term = ev.get_term_in_collection(
                _PROJECT_ID, _COLLECTION_ACTIVITY, _TERM_ACTIVITY
            )
        assert term.id == _TERM_ACTIVITY

    def test_all_terms_ids_match_in_collection(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            terms = ev.get_all_terms_in_collection(_PROJECT_ID, _COLLECTION_ACTIVITY)
        ids_as_set = {t.id for t in terms}
        assert len(ids_as_set) == len(terms), "Duplicate ids found in collection"


# ---------------------------------------------------------------------------
# DT-141  Two projects backed by same DB return same term (Scenario 5)
# ---------------------------------------------------------------------------

class TestMultipleProjectsConsistency:
    """DT-141: Scenario 5 — two projects sharing the same DB return identical terms."""

    def test_same_term_from_both_projects(self, real_dbs, universe_db):
        with _inject_two_projects(real_dbs["v1_path"], universe_db):
            term_a = ev.get_term_in_collection(
                _PROJECT_A, _COLLECTION_ACTIVITY, _TERM_ACTIVITY
            )
            term_b = ev.get_term_in_collection(
                _PROJECT_B, _COLLECTION_ACTIVITY, _TERM_ACTIVITY
            )
        assert term_a is not None
        assert term_b is not None
        assert term_a.id == term_b.id
        assert term_a.drs_name == term_b.drs_name

    def test_both_projects_have_same_project_list_shape(self, real_dbs, universe_db):
        with _inject_two_projects(real_dbs["v1_path"], universe_db):
            projects = ev.get_all_projects()
        ids = set(projects)
        assert _PROJECT_A in ids
        assert _PROJECT_B in ids


# ---------------------------------------------------------------------------
# DT-142  get_all_terms_in_collection count is same across two projects
# ---------------------------------------------------------------------------

class TestMultipleProjectsTermCount:
    """DT-142: Both projects (same source DB) report the same term count."""

    def test_same_term_count_in_both_projects(self, real_dbs, universe_db):
        with _inject_two_projects(real_dbs["v1_path"], universe_db):
            terms_a = ev.get_all_terms_in_collection(_PROJECT_A, _COLLECTION_ACTIVITY)
            terms_b = ev.get_all_terms_in_collection(_PROJECT_B, _COLLECTION_ACTIVITY)
        assert len(terms_a) == len(terms_b)
        assert len(terms_a) > 0

    def test_same_term_ids_in_both_projects(self, real_dbs, universe_db):
        with _inject_two_projects(real_dbs["v1_path"], universe_db):
            ids_a = {t.id for t in ev.get_all_terms_in_collection(_PROJECT_A, _COLLECTION_ACTIVITY)}
            ids_b = {t.id for t in ev.get_all_terms_in_collection(_PROJECT_B, _COLLECTION_ACTIVITY)}
        assert ids_a == ids_b


# ---------------------------------------------------------------------------
# DT-143  DATA_DESCRIPTOR_CLASS_MAPPING covers known built-in ids
# ---------------------------------------------------------------------------

class TestDataDescriptorClassMapping:
    """DT-143: DATA_DESCRIPTOR_CLASS_MAPPING includes the well-known data descriptor ids."""

    def test_mapping_contains_activity(self):
        from esgvoc.api.data_descriptors import DATA_DESCRIPTOR_CLASS_MAPPING
        assert "activity" in DATA_DESCRIPTOR_CLASS_MAPPING

    def test_mapping_contains_institution(self):
        from esgvoc.api.data_descriptors import DATA_DESCRIPTOR_CLASS_MAPPING
        assert "institution" in DATA_DESCRIPTOR_CLASS_MAPPING

    def test_mapping_contains_frequency(self):
        from esgvoc.api.data_descriptors import DATA_DESCRIPTOR_CLASS_MAPPING
        assert "frequency" in DATA_DESCRIPTOR_CLASS_MAPPING

    def test_mapping_contains_source(self):
        from esgvoc.api.data_descriptors import DATA_DESCRIPTOR_CLASS_MAPPING
        assert "source" in DATA_DESCRIPTOR_CLASS_MAPPING

    def test_all_values_are_classes(self):
        from esgvoc.api.data_descriptors import DATA_DESCRIPTOR_CLASS_MAPPING
        from esgvoc.api.data_descriptors.data_descriptor import DataDescriptor
        for name, cls in DATA_DESCRIPTOR_CLASS_MAPPING.items():
            assert callable(cls), f"{name} value is not callable"


# ---------------------------------------------------------------------------
# DT-144  DataDescriptorSubSet with selected_term_fields=[]
# ---------------------------------------------------------------------------

class TestDataDescriptorSubSetEmpty:
    """DT-144: selected_term_fields=[] returns subset with only id."""

    def test_empty_fields_gives_id_only(self, real_dbs, universe_db):
        from esgvoc.api.data_descriptors.data_descriptor import DataDescriptorSubSet
        with _inject(real_dbs["v1_path"], universe_db):
            terms = ev.get_all_terms_in_collection(
                _PROJECT_ID, _COLLECTION_ACTIVITY,
                selected_term_fields=[]
            )
        assert len(terms) > 0
        for t in terms:
            assert isinstance(t, DataDescriptorSubSet)
            assert hasattr(t, "id")
            assert t.id

    def test_empty_fields_subset_has_no_drs_name(self, real_dbs, universe_db):
        """drs_name should not be set when not requested."""
        with _inject(real_dbs["v1_path"], universe_db):
            terms = ev.get_all_terms_in_collection(
                _PROJECT_ID, _COLLECTION_ACTIVITY,
                selected_term_fields=[]
            )
        for t in terms:
            # drs_name was not requested — should not be in __pydantic_fields_set__
            assert "drs_name" not in (t.__pydantic_fields_set__ or set())


# ---------------------------------------------------------------------------
# DT-145  DataDescriptorSubSet carries requested field when it exists
# ---------------------------------------------------------------------------

class TestDataDescriptorSubSetWithField:
    """DT-145: selected_term_fields=['drs_name'] gives subset with drs_name accessible."""

    def test_drs_name_present_when_requested(self, real_dbs, universe_db):
        from esgvoc.api.data_descriptors.data_descriptor import DataDescriptorSubSet
        with _inject(real_dbs["v1_path"], universe_db):
            terms = ev.get_all_terms_in_collection(
                _PROJECT_ID, _COLLECTION_ACTIVITY,
                selected_term_fields=["drs_name"]
            )
        assert len(terms) > 0
        for t in terms:
            assert isinstance(t, DataDescriptorSubSet)
            assert hasattr(t, "drs_name")
            assert t.drs_name  # non-empty

    def test_known_term_drs_name_correct_in_subset(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            terms = ev.get_all_terms_in_collection(
                _PROJECT_ID, _COLLECTION_ACTIVITY,
                selected_term_fields=["drs_name"]
            )
        aerchemmip = next((t for t in terms if t.id == _TERM_ACTIVITY), None)
        assert aerchemmip is not None
        assert aerchemmip.drs_name == _TERM_DRS_ACTIVITY

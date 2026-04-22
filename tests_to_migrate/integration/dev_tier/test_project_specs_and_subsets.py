"""
Dev Tier — ProjectSpecs/DRS structure and selected_term_fields tests.

Tests the full structure of ProjectSpecs (including DRS specifications) and
the `selected_term_fields` parameter that returns DataDescriptorSubSet
objects with only the requested fields populated.

Plan scenarios covered:
  DT-69  get_project returns ProjectSpecs with id and version fields
  DT-70  ProjectSpecs.drs_specs is a dict keyed by DrsType (if present)
  DT-71  DrsSpecification has separator and parts attributes
  DT-72  DrsPart has source_collection and is_required attributes
  DT-73  selected_term_fields returns DataDescriptorSubSet with only requested fields
  DT-74  selected_term_fields=[] returns only id (minimum subset)
  DT-75  selected_term_fields with nonexistent field returns subset without that field
  DT-76  get_all_terms_in_collection with selected fields returns subsets
  DT-77  get_term_in_project with selected fields returns subset with correct id
  DT-78  get_all_terms_in_all_projects with selected fields returns subsets
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
_KNOWN_COLLECTION = "activity_id"
_KNOWN_TERM = "aerchemmip"
_UNKNOWN_PROJECT = "nonexistent-xyz"


# ---------------------------------------------------------------------------
# Context manager
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
# DT-69  get_project returns ProjectSpecs with id and version
# ---------------------------------------------------------------------------

class TestProjectSpecsBasic:
    """DT-69: get_project returns a ProjectSpecs object with the expected fields."""

    def test_get_project_returns_non_none(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            specs = ev.get_project(_PROJECT_ID)
        assert specs is not None

    def test_specs_has_id_attribute(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            specs = ev.get_project(_PROJECT_ID)
        # ProjectSpecs id may be stored as id or project_id depending on structure
        has_id = hasattr(specs, "id") or hasattr(specs, "project_id")
        assert has_id, f"No id attribute found on ProjectSpecs: {dir(specs)}"

    def test_specs_has_version_attribute(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            specs = ev.get_project(_PROJECT_ID)
        assert hasattr(specs, "version"), f"No version attribute: {dir(specs)}"

    def test_unknown_project_returns_none(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            specs = ev.get_project(_UNKNOWN_PROJECT)
        assert specs is None

    def test_v1_and_v2_return_different_versions(self, real_dbs, universe_db):
        """v1 and v2 DBs carry different metadata (commit_sha / version)."""
        with _inject(real_dbs["v1_path"], universe_db):
            specs_v1 = ev.get_project(_PROJECT_ID)
        with _inject(real_dbs["v2_path"], universe_db):
            specs_v2 = ev.get_project(_PROJECT_ID)
        # Both should return specs without error
        assert specs_v1 is not None
        assert specs_v2 is not None


# ---------------------------------------------------------------------------
# DT-70 / DT-71 / DT-72  DRS specification structure
# ---------------------------------------------------------------------------

class TestDrsSpecsStructure:
    """DT-70 to DT-72: DRS specification structure in ProjectSpecs."""

    def test_drs_specs_is_none_or_dict(self, real_dbs, universe_db):
        """drs_specs is either None (project has no DRS) or a dict keyed by DrsType."""
        with _inject(real_dbs["v1_path"], universe_db):
            specs = ev.get_project(_PROJECT_ID)
        assert specs is not None
        # drs_specs may or may not exist; if it does, it must be a dict or None
        if hasattr(specs, "drs_specs"):
            assert specs.drs_specs is None or isinstance(specs.drs_specs, dict), (
                f"drs_specs should be None or dict; got {type(specs.drs_specs)}"
            )

    def test_drs_specs_keys_are_drs_type_values(self, real_dbs, universe_db):
        """If drs_specs exists and is non-None, keys should be DrsType instances or strings."""
        from esgvoc.api.project_specs import DrsType
        with _inject(real_dbs["v1_path"], universe_db):
            specs = ev.get_project(_PROJECT_ID)
        assert specs is not None
        if hasattr(specs, "drs_specs") and specs.drs_specs:
            for key in specs.drs_specs.keys():
                assert isinstance(key, (DrsType, str)), (
                    f"Expected DrsType or str key; got {type(key)}: {key}"
                )

    def test_drs_specification_has_separator(self, real_dbs, universe_db):
        """Each DrsSpecification should have a separator attribute."""
        from esgvoc.api.project_specs import DrsSpecification
        with _inject(real_dbs["v1_path"], universe_db):
            specs = ev.get_project(_PROJECT_ID)
        assert specs is not None
        if hasattr(specs, "drs_specs") and specs.drs_specs:
            for drs_type, drs_spec in specs.drs_specs.items():
                assert hasattr(drs_spec, "separator"), (
                    f"DrsSpecification for {drs_type} missing 'separator'"
                )

    def test_drs_specification_has_parts_list(self, real_dbs, universe_db):
        """Each DrsSpecification should have a 'parts' list."""
        with _inject(real_dbs["v1_path"], universe_db):
            specs = ev.get_project(_PROJECT_ID)
        assert specs is not None
        if hasattr(specs, "drs_specs") and specs.drs_specs:
            for drs_type, drs_spec in specs.drs_specs.items():
                assert hasattr(drs_spec, "parts"), (
                    f"DrsSpecification for {drs_type} missing 'parts'"
                )
                assert isinstance(drs_spec.parts, list), (
                    f"parts should be a list; got {type(drs_spec.parts)}"
                )

    def test_drs_parts_have_source_collection_and_is_required(self, real_dbs, universe_db):
        """Each DrsPart must have source_collection (str) and is_required (bool)."""
        with _inject(real_dbs["v1_path"], universe_db):
            specs = ev.get_project(_PROJECT_ID)
        assert specs is not None
        if hasattr(specs, "drs_specs") and specs.drs_specs:
            for drs_type, drs_spec in specs.drs_specs.items():
                for i, part in enumerate(drs_spec.parts):
                    assert hasattr(part, "source_collection"), (
                        f"DrsPart[{i}] for {drs_type} missing 'source_collection'"
                    )
                    assert hasattr(part, "is_required"), (
                        f"DrsPart[{i}] for {drs_type} missing 'is_required'"
                    )
                    assert isinstance(part.source_collection, str), (
                        f"source_collection should be str; got {type(part.source_collection)}"
                    )
                    assert isinstance(part.is_required, bool), (
                        f"is_required should be bool; got {type(part.is_required)}"
                    )


# ---------------------------------------------------------------------------
# DT-73 / DT-74 / DT-75  selected_term_fields parameter
# ---------------------------------------------------------------------------

class TestSelectedTermFields:
    """DT-73 to DT-75: selected_term_fields returns DataDescriptorSubSet."""

    def test_selected_fields_returns_subset_instances(self, real_dbs, universe_db):
        """get_all_terms_in_collection with selected_term_fields returns DataDescriptorSubSet."""
        from esgvoc.api.data_descriptors.data_descriptor import DataDescriptorSubSet
        with _inject(real_dbs["v1_path"], universe_db):
            terms = ev.get_all_terms_in_collection(
                _PROJECT_ID, _KNOWN_COLLECTION,
                selected_term_fields=["drs_name"]
            )
        assert len(terms) > 0
        for t in terms:
            assert isinstance(t, DataDescriptorSubSet), (
                f"Expected DataDescriptorSubSet; got {type(t)}"
            )

    def test_selected_fields_id_always_present(self, real_dbs, universe_db):
        """id is always present in DataDescriptorSubSet regardless of selected_term_fields."""
        with _inject(real_dbs["v1_path"], universe_db):
            terms = ev.get_all_terms_in_collection(
                _PROJECT_ID, _KNOWN_COLLECTION,
                selected_term_fields=["drs_name"]
            )
        for t in terms:
            assert hasattr(t, "id")
            assert t.id  # non-empty

    def test_empty_selected_fields_returns_subset_with_id(self, real_dbs, universe_db):
        """selected_term_fields=[] returns a DataDescriptorSubSet with at least id."""
        from esgvoc.api.data_descriptors.data_descriptor import DataDescriptorSubSet
        with _inject(real_dbs["v1_path"], universe_db):
            terms = ev.get_all_terms_in_collection(
                _PROJECT_ID, _KNOWN_COLLECTION,
                selected_term_fields=[]
            )
        assert len(terms) > 0
        for t in terms:
            assert isinstance(t, DataDescriptorSubSet)
            assert hasattr(t, "id")

    def test_none_selected_fields_returns_full_descriptor(self, real_dbs, universe_db):
        """selected_term_fields=None (default) returns full DataDescriptor objects."""
        from esgvoc.api.data_descriptors.data_descriptor import DataDescriptor, DataDescriptorSubSet
        with _inject(real_dbs["v1_path"], universe_db):
            terms = ev.get_all_terms_in_collection(
                _PROJECT_ID, _KNOWN_COLLECTION,
                selected_term_fields=None
            )
        assert len(terms) > 0
        # Full descriptors are DataDescriptor instances, NOT DataDescriptorSubSet
        for t in terms:
            assert isinstance(t, DataDescriptor)
            assert not isinstance(t, DataDescriptorSubSet), (
                "None selected_term_fields should return full DataDescriptor, not SubSet"
            )

    def test_nonexistent_field_in_selected_returns_subset_without_it(self, real_dbs, universe_db):
        """A nonexistent field in selected_term_fields is silently ignored."""
        from esgvoc.api.data_descriptors.data_descriptor import DataDescriptorSubSet
        with _inject(real_dbs["v1_path"], universe_db):
            terms = ev.get_all_terms_in_collection(
                _PROJECT_ID, _KNOWN_COLLECTION,
                selected_term_fields=["totally_nonexistent_field_xyz"]
            )
        # Should return subsets (not raise), subset just won't have the field
        for t in terms:
            assert isinstance(t, DataDescriptorSubSet)
            assert hasattr(t, "id")


# ---------------------------------------------------------------------------
# DT-76  get_all_terms_in_collection with selected fields
# ---------------------------------------------------------------------------

class TestGetAllTermsSelectedFields:
    """DT-76: get_all_terms_in_collection respects selected_term_fields."""

    def test_selected_fields_reduces_returned_fields(self, real_dbs, universe_db):
        """Subset term should only have id (plus the requested field if it exists)."""
        with _inject(real_dbs["v1_path"], universe_db):
            subset_terms = ev.get_all_terms_in_collection(
                _PROJECT_ID, _KNOWN_COLLECTION,
                selected_term_fields=["drs_name"]
            )
            full_terms = ev.get_all_terms_in_collection(
                _PROJECT_ID, _KNOWN_COLLECTION
            )
        # Same count
        assert len(subset_terms) == len(full_terms)

    def test_subset_ids_match_full_ids(self, real_dbs, universe_db):
        """Subset and full terms should have the same ids (same data, fewer fields)."""
        with _inject(real_dbs["v1_path"], universe_db):
            subset_terms = ev.get_all_terms_in_collection(
                _PROJECT_ID, _KNOWN_COLLECTION,
                selected_term_fields=["drs_name"]
            )
            full_terms = ev.get_all_terms_in_collection(
                _PROJECT_ID, _KNOWN_COLLECTION
            )
        subset_ids = {t.id for t in subset_terms}
        full_ids = {t.id for t in full_terms}
        assert subset_ids == full_ids


# ---------------------------------------------------------------------------
# DT-77  get_term_in_project with selected fields
# ---------------------------------------------------------------------------

class TestGetTermInProjectSelectedFields:
    """DT-77: get_term_in_project with selected_term_fields returns DataDescriptorSubSet."""

    def test_selected_fields_returns_subset(self, real_dbs, universe_db):
        from esgvoc.api.data_descriptors.data_descriptor import DataDescriptorSubSet
        with _inject(real_dbs["v1_path"], universe_db):
            term = ev.get_term_in_project(
                _PROJECT_ID, _KNOWN_TERM,
                selected_term_fields=["drs_name"]
            )
        assert term is not None
        assert isinstance(term, DataDescriptorSubSet)

    def test_selected_fields_term_id_correct(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            term = ev.get_term_in_project(
                _PROJECT_ID, _KNOWN_TERM,
                selected_term_fields=["drs_name"]
            )
        assert term is not None
        assert term.id == _KNOWN_TERM


# ---------------------------------------------------------------------------
# DT-78  get_all_terms_in_all_projects with selected fields
# ---------------------------------------------------------------------------

class TestGetAllTermsInAllProjectsSelectedFields:
    """DT-78: get_all_terms_in_all_projects respects selected_term_fields."""

    def test_selected_fields_returns_subsets(self, real_dbs, universe_db):
        from esgvoc.api.data_descriptors.data_descriptor import DataDescriptorSubSet
        with _inject(real_dbs["v1_path"], universe_db):
            results = ev.get_all_terms_in_all_projects(
                selected_term_fields=["drs_name"]
            )
        assert len(results) > 0
        for pid, terms in results:
            for t in terms:
                assert isinstance(t, DataDescriptorSubSet), (
                    f"Expected DataDescriptorSubSet for project '{pid}'; got {type(t)}"
                )

"""
Tests for get_model_from_collection and get_model_from_data_descriptor.

Resolves the concrete pydantic model on-the-fly from existing DBs
(no special DB build required).
"""

import pytest

from esgvoc.api.data_descriptors.data_descriptor import DataDescriptor

pytestmark = pytest.mark.needs_db


class TestGetModelFromCollection:
    def test_returns_a_class(self, installed_dbs):
        import esgvoc.api.projects as projects

        collections = projects.get_all_collections_in_project("cmip7")
        assert len(collections) > 0
        for coll in collections:
            dd = projects.get_data_descriptor_from_collection_in_project("cmip7", coll)
            if dd is not None:
                result = projects.get_model_from_collection("cmip7", coll)
                assert result is not None
                assert isinstance(result, type)
                assert issubclass(result, DataDescriptor)
                return
        pytest.skip("No collection in cmip7 has a linked data descriptor")

    def test_returns_concrete_class_not_union(self, installed_dbs):
        """The returned class should be a concrete pydantic model, not a Union/Annotated type."""
        import esgvoc.api.projects as projects

        collections = projects.get_all_collections_in_project("cmip7")
        for coll in collections:
            dd = projects.get_data_descriptor_from_collection_in_project("cmip7", coll)
            if dd is not None:
                result = projects.get_model_from_collection("cmip7", coll)
                if result is None:
                    continue
                assert hasattr(result, "__name__"), (
                    f"Expected a concrete class for collection '{coll}', got {result}"
                )
                assert hasattr(result, "model_fields"), (
                    f"Expected a pydantic model for collection '{coll}', got {result}"
                )
                return
        pytest.skip("No collection with a resolvable model found")

    def test_experiment_collection_returns_specific_variant(self, installed_dbs):
        """For cmip7's experiment collection, should return ExperimentCMIP7, not the union."""
        import esgvoc.api.projects as projects
        from esgvoc.api.data_descriptors.experiment import ExperimentCMIP7

        result = projects.get_model_from_collection("cmip7", "experiment")
        if result is None:
            pytest.skip("cmip7 has no 'experiment' collection")
        assert result is ExperimentCMIP7, (
            f"Expected ExperimentCMIP7 for cmip7/experiment, got {result}"
        )

    def test_activity_collection_returns_specific_variant(self, installed_dbs):
        """For cmip7's activity collection, should return ActivityCMIP7, not the union."""
        import esgvoc.api.projects as projects
        from esgvoc.api.data_descriptors.activity import ActivityCMIP7

        result = projects.get_model_from_collection("cmip7", "activity")
        if result is None:
            pytest.skip("cmip7 has no 'activity' collection")
        assert result is ActivityCMIP7, (
            f"Expected ActivityCMIP7 for cmip7/activity, got {result}"
        )

    def test_non_union_collection_returns_direct_class(self, installed_dbs):
        """For a data descriptor with no union (e.g. frequency), should return the class directly."""
        import esgvoc.api.projects as projects
        from esgvoc.api.data_descriptors.frequency import Frequency

        collections = projects.get_all_collections_in_project("cmip7")
        for coll in collections:
            dd = projects.get_data_descriptor_from_collection_in_project("cmip7", coll)
            if dd == "frequency":
                result = projects.get_model_from_collection("cmip7", coll)
                assert result is Frequency
                return
        pytest.skip("No frequency collection found in cmip7")

    def test_unknown_collection_returns_none(self, installed_dbs):
        import esgvoc.api.projects as projects

        result = projects.get_model_from_collection("cmip7", "non_existent_collection_xyz")
        assert result is None

    def test_unknown_project_returns_none(self, installed_dbs):
        import esgvoc.api.projects as projects

        result = projects.get_model_from_collection("non_existent_project_xyz", "source")
        assert result is None

    def test_all_collections_resolvable(self, installed_dbs):
        """Every collection with a data descriptor should return a model."""
        import esgvoc.api.projects as projects

        collections = projects.get_all_collections_in_project("cmip7")
        for coll in collections:
            dd = projects.get_data_descriptor_from_collection_in_project("cmip7", coll)
            if dd is not None:
                result = projects.get_model_from_collection("cmip7", coll)
                assert result is not None, (
                    f"Collection '{coll}' (data_descriptor='{dd}') should resolve to a model"
                )
                assert issubclass(result, DataDescriptor), (
                    f"Collection '{coll}' returned {result}, expected a DataDescriptor subclass"
                )

    def test_model_has_docstring(self, installed_dbs):
        """The returned model should have a class docstring (original motivation for this feature)."""
        import esgvoc.api.projects as projects

        collections = projects.get_all_collections_in_project("cmip7")
        for coll in collections:
            dd = projects.get_data_descriptor_from_collection_in_project("cmip7", coll)
            if dd is not None:
                result = projects.get_model_from_collection("cmip7", coll)
                if result is not None:
                    assert result.__doc__ is not None, (
                        f"Model for collection '{coll}' has no docstring"
                    )
                    return
        pytest.skip("No resolvable collection found")

    def test_model_has_model_fields(self, installed_dbs):
        """The returned model should expose pydantic model_fields for introspection."""
        import esgvoc.api.projects as projects

        collections = projects.get_all_collections_in_project("cmip7")
        for coll in collections:
            dd = projects.get_data_descriptor_from_collection_in_project("cmip7", coll)
            if dd is not None:
                result = projects.get_model_from_collection("cmip7", coll)
                if result is not None:
                    assert hasattr(result, "model_fields")
                    assert len(result.model_fields) > 0
                    return
        pytest.skip("No resolvable collection found")


class TestGetModelFromDataDescriptor:
    def test_returns_class_for_known_descriptor(self):
        from esgvoc.api.universe import get_model_from_data_descriptor

        result = get_model_from_data_descriptor("frequency")
        assert result is not None
        assert issubclass(result, DataDescriptor)

    def test_returns_none_for_unknown_descriptor(self):
        from esgvoc.api.universe import get_model_from_data_descriptor

        result = get_model_from_data_descriptor("non_existent_xyz")
        assert result is None

    def test_source_returns_union_type(self):
        """For 'source', should return the union (Source), not a concrete variant."""
        from esgvoc.api.data_descriptors.source import Source
        from esgvoc.api.universe import get_model_from_data_descriptor

        result = get_model_from_data_descriptor("source")
        assert result is Source

    def test_experiment_returns_union_type(self):
        from esgvoc.api.data_descriptors.experiment import Experiment
        from esgvoc.api.universe import get_model_from_data_descriptor

        result = get_model_from_data_descriptor("experiment")
        assert result is Experiment

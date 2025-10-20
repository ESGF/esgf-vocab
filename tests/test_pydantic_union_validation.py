"""
Tests for Pydantic validation with Union types for mixed resolved/unresolved references.

This tests the ability of our Pydantic models to accept both string IDs and resolved objects
in the same field, which is necessary when some references can be resolved and others cannot.
"""

import pytest
from pydantic import ValidationError, TypeAdapter
from esgvoc.api.data_descriptors.experiment import Experiment, ExperimentCMI7, ExperimentBeforeCMIP7
from esgvoc.api.data_descriptors.source import Source
from esgvoc.api.data_descriptors.activity import Activity
from esgvoc.api.data_descriptors.source_type import SourceType


def test_experiment_with_all_resolved_activity():
    """Test Experiment validates when activity is fully resolved to Activity objects."""
    experiment_data = {
        "id": "test_exp",
        "type": "experiment",
        "drs_name": "test-exp",
        "activity": [
            {
                "id": "scenariomip",
                "type": "activity",
                "name": "ScenarioMIP",
                "drs_name": "ScenarioMIP",
                "long_name": "Scenario Model Intercomparison Project",
                "url": None
            }
        ],
        "additional_allowed_model_components": [],
        "branch_information": None,
        "end_timestamp": None,
        "min_ensemble_size": 1,
        "min_number_yrs_per_sim": 100.0,
        "parent_activity": None,
        "parent_experiment": None,
        "parent_mip_era": None,
        "required_model_components": ["agcm"],
        "start_timestamp": "1901-01-01",
        "tier": 2
    }

    # Should validate successfully
    exp = TypeAdapter(Experiment).validate_python(experiment_data)
    assert exp.id == "test_exp"
    assert len(exp.activity) == 1
    assert isinstance(exp.activity[0], Activity)
    assert exp.activity[0].id == "scenariomip"


def test_experiment_with_mixed_model_components():
    """Test Experiment validates with mixed str and SourceType in model_components."""
    experiment_data = {
        "id": "test_exp",
        "type": "experiment",
        "drs_name": "test-exp",
        "activity": [],
        "additional_allowed_model_components": [
            {
                "id": "bgc",
                "type": "source_type",
                "drs_name": "BGC",
                "description": "Biogeochemistry component"
            },
            "chem"  # String for unresolved reference
        ],
        "branch_information": None,
        "end_timestamp": None,
        "min_ensemble_size": 1,
        "min_number_yrs_per_sim": 100.0,
        "parent_activity": None,
        "parent_experiment": None,
        "parent_mip_era": None,
        "required_model_components": [
            "agcm",  # String
            {
                "id": "land",
                "type": "source_type",
                "drs_name": "land",
                "description": "Land Surface component"
            }
        ],
        "start_timestamp": "1901-01-01",
        "tier": 2
    }

    # Should validate successfully
    exp = TypeAdapter(Experiment).validate_python(experiment_data)
    assert len(exp.required_model_components) == 2
    assert isinstance(exp.required_model_components[0], str)
    assert exp.required_model_components[0] == "agcm"
    assert isinstance(exp.required_model_components[1], SourceType)

    assert len(exp.additional_allowed_model_components) == 2
    assert isinstance(exp.additional_allowed_model_components[0], SourceType)
    assert isinstance(exp.additional_allowed_model_components[1], str)


def test_source_with_mixed_activity_participation():
    """Test Source validates with mixed str and Activity in activity_participation."""
    source_data = {
        "id": "test_source",
        "type": "source",
        "drs_name": "test-source",
        "activity_participation": [
            {
                "id": "cmip",
                "type": "activity",
                "name": "CMIP",
                "drs_name": "CMIP",
                "long_name": "Coupled Model Intercomparison Project",
                "url": None
            },
            "ramip"  # String for unresolved reference
        ],
        "cohort": ["Published"],
        "organisation_id": ["test-org"],
        "label": "Test Source"
    }

    # Should validate successfully
    source = TypeAdapter(Source).validate_python(source_data)
    assert len(source.activity_participation) == 2
    assert isinstance(source.activity_participation[0], Activity)
    assert source.activity_participation[0].id == "cmip"
    assert isinstance(source.activity_participation[1], str)
    assert source.activity_participation[1] == "ramip"


def test_source_with_all_string_activity_participation():
    """Test Source validates when all activity_participation are strings."""
    source_data = {
        "id": "test_source",
        "type": "source",
        "drs_name": "test-source",
        "activity_participation": ["cmip", "scenariomip"],
        "cohort": [],
        "organisation_id": [],
        "label": "Test Source"
    }

    source = TypeAdapter(Source).validate_python(source_data)
    assert all(isinstance(a, str) for a in source.activity_participation)


def test_source_with_all_resolved_activity_participation():
    """Test Source validates when all activity_participation are Activity objects."""
    source_data = {
        "id": "test_source",
        "type": "source",
        "drs_name": "test-source",
        "activity_participation": [
            {
                "id": "cmip",
                "type": "activity",
                "name": "CMIP",
                "drs_name": "CMIP",
                "long_name": "Coupled Model Intercomparison Project",
                "url": None
            },
            {
                "id": "scenariomip",
                "type": "activity",
                "name": "ScenarioMIP",
                "drs_name": "ScenarioMIP",
                "long_name": "Scenario Model Intercomparison Project",
                "url": None
            }
        ],
        "cohort": [],
        "organisation_id": [],
        "label": "Test Source"
    }

    source = TypeAdapter(Source).validate_python(source_data)
    assert all(isinstance(a, Activity) for a in source.activity_participation)


def test_experiment_discriminator_cmip7():
    """Test that Experiment Union correctly discriminates to ExperimentCMI7."""
    experiment_data = {
        "id": "test_exp",
        "type": "experiment",
        "drs_name": "test-exp",
        "activity": [],
        "additional_allowed_model_components": [],
        "branch_information": None,
        "end_timestamp": None,
        "min_ensemble_size": 1,
        "min_number_yrs_per_sim": 100.0,
        "parent_activity": None,
        "parent_experiment": None,
        "parent_mip_era": None,
        "required_model_components": [],
        "start_timestamp": "1901-01-01",
        "tier": 2
    }

    exp = TypeAdapter(Experiment).validate_python(experiment_data)
    # The presence of CMIP7-specific fields should make it ExperimentCMI7
    assert isinstance(exp, ExperimentCMI7)


def test_experiment_discriminator_before_cmip7():
    """Test that Experiment Union correctly discriminates to ExperimentBeforeCMIP7."""
    experiment_data = {
        "id": "old_exp",
        "type": "experiment",
        "drs_name": "old-exp",
        "activity": [],
        "description": "Old experiment",
        "tier": 1,
        "experiment_id": "old_exp",
        "sub_experiment_id": None,
        "experiment": "Old Experiment",
        "required_model_components": None,
        "additional_allowed_model_components": [],
        "start_year": 1850,
        "end_year": 2014,
        "min_number_yrs_per_sim": None,
        "parent_activity_id": None,
        "parent_experiment_id": None
    }

    exp = TypeAdapter(Experiment).validate_python(experiment_data)
    # The presence of old-style fields should make it ExperimentBeforeCMIP7
    assert isinstance(exp, ExperimentBeforeCMIP7)


def test_experiment_invalid_activity_type():
    """Test that Experiment validation fails if activity has wrong type."""
    experiment_data = {
        "id": "test_exp",
        "type": "experiment",
        "drs_name": "test-exp",
        "activity": [
            123  # Invalid: neither string nor Activity object
        ],
        "additional_allowed_model_components": [],
        "branch_information": None,
        "end_timestamp": None,
        "min_ensemble_size": 1,
        "min_number_yrs_per_sim": 100.0,
        "parent_activity": None,
        "parent_experiment": None,
        "parent_mip_era": None,
        "required_model_components": [],
        "start_timestamp": "1901-01-01",
        "tier": 2
    }

    with pytest.raises(ValidationError):
        TypeAdapter(Experiment).validate_python(experiment_data)


def test_source_invalid_activity_participation_type():
    """Test that Source validation fails if activity_participation has wrong type."""
    source_data = {
        "id": "test_source",
        "type": "source",
        "drs_name": "test-source",
        "activity_participation": [
            {"invalid": "object"}  # Invalid: missing required Activity fields
        ],
        "cohort": [],
        "organisation_id": [],
        "label": "Test Source"
    }

    with pytest.raises(ValidationError):
        TypeAdapter(Source).validate_python(source_data)


def test_experiment_shallow_parent():
    """Test Experiment validates with shallow-resolved parent_experiment.

    The parent experiment uses BeforeCMIP7 format which allows activity as list[str].
    """
    experiment_data = {
        "id": "child_exp",
        "type": "experiment",
        "drs_name": "child-exp",
        "activity": [],
        "additional_allowed_model_components": [],
        "branch_information": "Branch from parent",
        "end_timestamp": None,
        "min_ensemble_size": 1,
        "min_number_yrs_per_sim": 100.0,
        "parent_activity": None,
        "parent_experiment": [
            {
                # Parent experiment in BeforeCMIP7 format (activity as strings)
                "id": "parent_exp",
                "type": "experiment",
                "drs_name": "parent-exp",
                "activity": ["cmip"],  # Shallow: kept as string IDs
                "description": "Parent experiment description",
                "experiment_id": "parent_exp",
                "sub_experiment_id": None,
                "experiment": "Parent Experiment",
                "required_model_components": ["agcm"],  # Shallow: kept as strings
                "additional_allowed_model_components": [],
                "start_year": 1850,
                "end_year": 2014,
                "min_number_yrs_per_sim": None,
                "parent_activity_id": None,
                "parent_experiment_id": None,
                "tier": 1
            }
        ],
        "parent_mip_era": None,
        "required_model_components": [],
        "start_timestamp": "1901-01-01",
        "tier": 2
    }

    # Should validate successfully
    exp = TypeAdapter(Experiment).validate_python(experiment_data)
    assert exp.parent_experiment is not None
    assert len(exp.parent_experiment) == 1
    # Parent experiment's nested fields remain as raw data (not recursively resolved)
    parent = exp.parent_experiment[0]
    assert parent.id == "parent_exp"
    # The parent should be ExperimentBeforeCMIP7 since it has the old-style fields
    assert isinstance(parent, ExperimentBeforeCMIP7)

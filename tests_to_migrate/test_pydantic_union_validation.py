"""
Tests for Pydantic validation with Union types for mixed resolved/unresolved references.

This tests the ability of our Pydantic models to accept both string IDs and resolved objects
in the same field, which is necessary when some references can be resolved and others cannot.
"""

import pytest
from pydantic import ValidationError, TypeAdapter
from esgvoc.api.data_descriptors.experiment import Experiment, ExperimentCMIP7, ExperimentLegacy
from esgvoc.api.data_descriptors.source import Source, SourceCMIP7, SourceLegacy
from esgvoc.api.data_descriptors.activity import Activity
from esgvoc.api.data_descriptors.source_type import SourceType


def test_experiment_cmip7_with_string_activity():
    """Test ExperimentCMIP7 validates with string activity reference."""
    experiment_data = {
        "id": "test_exp",
        "type": "experiment",
        "drs_name": "test-exp",
        "activity": "scenariomip",  # CMIP7 expects single string
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
        "tier": 2,
        "experiments": [],  # Required for CMIP7
        "urls": []  # Required for CMIP7
    }

    # Should validate successfully as ExperimentCMIP7
    exp = TypeAdapter(Experiment).validate_python(experiment_data)
    assert exp.id == "test_exp"
    assert isinstance(exp, ExperimentCMIP7)
    assert exp.activity == "scenariomip"


def test_experiment_legacy_with_activity_list():
    """Test ExperimentLegacy validates with list of activity strings."""
    experiment_data = {
        "id": "test_exp",
        "type": "experiment",
        "drs_name": "test-exp",
        "activity_id": ["scenariomip", "cmip"],  # Legacy uses activity_id, not activity
        "tier": 2,
        "experiment_id": "test_exp",
        "sub_experiment_id": None,
        "experiment": "test-exp",
        "required_model_components": ["agcm"],
        "additional_allowed_model_components": [],
        "start_year": 1901,
        "end_year": 2000,
        "min_number_yrs_per_sim": 100,
        "parent_activity_id": None,
        "parent_experiment_id": None
    }

    # Should validate successfully as ExperimentLegacy
    exp = TypeAdapter(Experiment).validate_python(experiment_data)
    assert exp.id == "test_exp"
    assert isinstance(exp, ExperimentLegacy)
    assert len(exp.activity_id) == 2
    assert "scenariomip" in exp.activity_id


def test_experiment_with_mixed_model_components():
    """Test ExperimentCMIP7 validates with string model_components."""
    experiment_data = {
        "id": "test_exp",
        "type": "experiment",
        "drs_name": "test-exp",
        "activity": "cmip",  # CMIP7 expects single string
        "additional_allowed_model_components": ["bgc", "chem"],  # Strings only
        "branch_information": None,
        "end_timestamp": None,
        "min_ensemble_size": 1,
        "min_number_yrs_per_sim": 100.0,
        "parent_activity": None,
        "parent_experiment": None,
        "parent_mip_era": None,
        "required_model_components": ["agcm", "land"],  # Strings only
        "start_timestamp": "1901-01-01",
        "tier": 2,
        "experiments": [],
        "urls": []
    }

    # Should validate successfully as ExperimentCMIP7
    exp = TypeAdapter(Experiment).validate_python(experiment_data)
    assert isinstance(exp, ExperimentCMIP7)
    assert len(exp.required_model_components) == 2
    assert exp.required_model_components[0] == "agcm"
    assert exp.required_model_components[1] == "land"
    assert len(exp.additional_allowed_model_components) == 2
    assert exp.additional_allowed_model_components[0] == "bgc"
    assert exp.additional_allowed_model_components[1] == "chem"


def test_source_legacy_with_activity_participation():
    """Test SourceLegacy validates with string activity_participation."""
    source_data = {
        "id": "test_source",
        "type": "source",
        "drs_name": "test-source",
        "activity_participation": ["cmip", "ramip"],  # Legacy expects list of strings
        "cohort": ["Published"],
        "organisation_id": ["test-org"],
        "label": "Test Source"
    }

    # Should validate successfully as SourceLegacy
    source = TypeAdapter(Source).validate_python(source_data)
    assert isinstance(source, SourceLegacy)
    assert len(source.activity_participation) == 2
    assert "cmip" in source.activity_participation
    assert "ramip" in source.activity_participation


def test_source_cmip7_with_contributors():
    """Test SourceCMIP7 validates with contributors and model_components."""
    source_data = {
        "id": "test_source",
        "type": "source",
        "drs_name": "test-source",
        "label": "Test Source",
        "label_extended": "Test Source Extended",
        "contributors": ["contributor1", "contributor2"],  # Strings
        "model_components": ["agcm", "ogcm"]  # Strings
    }

    source = TypeAdapter(Source).validate_python(source_data)
    assert isinstance(source, SourceCMIP7)
    assert len(source.contributors) == 2
    assert len(source.model_components) == 2


def test_source_legacy_without_model_component():
    """Test SourceLegacy validates without model_component field."""
    source_data = {
        "id": "test_source",
        "type": "source",
        "drs_name": "test-source",
        "activity_participation": ["cmip"],
        "cohort": [],
        "organisation_id": [],
        "label": "Test Source",
        "label_extended": "Test Source Extended",
        "license": {},
        "model_component": None,
        "release_year": 2023
    }

    source = TypeAdapter(Source).validate_python(source_data)
    assert isinstance(source, SourceLegacy)
    assert source.release_year == 2023


def test_experiment_discriminator_cmip7():
    """Test that Experiment Union correctly discriminates to ExperimentCMIP7."""
    experiment_data = {
        "id": "test_exp",
        "type": "experiment",
        "drs_name": "test-exp",
        "activity": "cmip",  # CMIP7 expects string
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
        "tier": 2,
        "experiments": [],  # CMIP7-specific field
        "urls": []  # CMIP7-specific field
    }

    exp = TypeAdapter(Experiment).validate_python(experiment_data)
    # The presence of CMIP7-specific fields should make it ExperimentCMIP7
    assert isinstance(exp, ExperimentCMIP7)


def test_experiment_discriminator_before_cmip7():
    """Test that Experiment Union correctly discriminates to ExperimentLegacy."""
    experiment_data = {
        "id": "old_exp",
        "type": "experiment",
        "drs_name": "old-exp",
        "activity_id": [],
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
    # The presence of old-style fields should make it ExperimentLegacy
    assert isinstance(exp, ExperimentLegacy)


def test_experiment_invalid_activity_type():
    """Test that Experiment validation fails if activity has wrong type."""
    experiment_data = {
        "id": "test_exp",
        "type": "experiment",
        "drs_name": "test-exp",
        "activity": 123,  # Invalid: should be string for CMIP7 or list for Legacy
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
            123  # Invalid: should be strings
        ],
        "cohort": [],
        "organisation_id": [],
        "label": "Test Source"
    }

    with pytest.raises(ValidationError):
        TypeAdapter(Source).validate_python(source_data)


def test_experiment_with_parent_experiment():
    """Test ExperimentCMIP7 validates with parent_experiment as Legacy format."""
    experiment_data = {
        "id": "child_exp",
        "type": "experiment",
        "drs_name": "child-exp",
        "activity": "cmip",  # CMIP7 expects string
        "additional_allowed_model_components": [],
        "branch_information": "Branch from parent",
        "end_timestamp": None,
        "min_ensemble_size": 1,
        "min_number_yrs_per_sim": 100.0,
        "parent_activity": None,
        "parent_experiment": {
            # Parent experiment in Legacy format
            "id": "parent_exp",
            "type": "experiment",
            "drs_name": "parent-exp",
            "activity_id": ["cmip"],  # Legacy uses activity_id, not activity
            "description": "Parent experiment description",
            "experiment_id": "parent_exp",
            "sub_experiment_id": None,
            "experiment": "Parent Experiment",
            "required_model_components": ["agcm"],
            "additional_allowed_model_components": [],
            "start_year": 1850,
            "end_year": 2014,
            "min_number_yrs_per_sim": None,
            "parent_activity_id": None,
            "parent_experiment_id": None,
            "tier": 1
        },
        "parent_mip_era": None,
        "required_model_components": [],
        "start_timestamp": "1901-01-01",
        "tier": 2,
        "experiments": [],
        "urls": []
    }

    # Should validate successfully as ExperimentCMIP7
    exp = TypeAdapter(Experiment).validate_python(experiment_data)
    assert isinstance(exp, ExperimentCMIP7)
    assert exp.parent_experiment is not None
    # The parent should be ExperimentLegacy since it has the old-style fields
    assert isinstance(exp.parent_experiment, ExperimentLegacy)
    assert exp.parent_experiment.id == "parent_exp"

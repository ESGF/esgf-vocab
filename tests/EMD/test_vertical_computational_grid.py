"""
Tests for the EMD VerticalComputationalGrid class validators (EMD v1.0 Section 4.2).

These tests verify:
- description is required when vertical_coordinate is 'none' (warning)
- description is required when n_z and n_z_range are both not set (warning)
- description is required when thickness fields are not set (warning)
- n_z and n_z_range are mutually exclusive
- n_z_range validation (min <= max, values >= 1)
"""

import warnings

import pytest
from pydantic import ValidationError

from esgvoc.api.data_descriptors.EMD_models.vertical_computational_grid import VerticalComputationalGrid


def _create_base_vcg_data(**overrides) -> dict:
    """Create base VerticalComputationalGrid data for testing."""
    data = {
        "id": "test_vcg",
        "type": "vertical_computational_grid",
        "vertical_coordinate": "height",
    }
    data.update(overrides)
    return data


class TestDescriptionRequirementsValidation:
    """Tests for description requirements validation (EMD Conformance 4.2)."""

    def test_description_required_when_coordinate_is_none_warns(self):
        """Test warning when vertical_coordinate is 'none' and no description."""
        data = _create_base_vcg_data(
            vertical_coordinate="none",
            # No description
        )
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            VerticalComputationalGrid(**data)
            emd_warnings = [x for x in w if "EMD Conformance" in str(x.message)]
            assert any("vertical_coordinate is 'none'" in str(x.message) for x in emd_warnings)

    def test_description_provided_when_coordinate_is_none_no_warning(self):
        """Test no warning when vertical_coordinate is 'none' but description is provided."""
        data = _create_base_vcg_data(
            vertical_coordinate="none",
            description="No vertical dimension in this component",
            n_z=1,
            top_of_model=0.0,
            bottom_layer_thickness=1.0,
            top_layer_thickness=1.0,
        )
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            VerticalComputationalGrid(**data)
            emd_warnings = [x for x in w if "EMD Conformance" in str(x.message)]
            # When description is provided, no EMD conformance warnings should appear
            assert len(emd_warnings) == 0

    def test_description_required_when_n_z_not_set_warns(self):
        """Test warning when n_z and n_z_range are both not set and no description."""
        data = _create_base_vcg_data(
            vertical_coordinate="height",
            # n_z not set
            # n_z_range not set
            # description not set
        )
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            VerticalComputationalGrid(**data)
            emd_warnings = [x for x in w if "EMD Conformance" in str(x.message)]
            assert any("n_z and n_z_range are both not set" in str(x.message) for x in emd_warnings)

    def test_no_warning_when_n_z_set(self):
        """Test no n_z warning when n_z is set."""
        data = _create_base_vcg_data(
            vertical_coordinate="height",
            n_z=50,
            top_of_model=80000.0,
            bottom_layer_thickness=20.0,
            top_layer_thickness=5000.0,
        )
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            VerticalComputationalGrid(**data)
            emd_warnings = [x for x in w if "EMD Conformance" in str(x.message)]
            assert not any("n_z and n_z_range" in str(x.message) for x in emd_warnings)

    def test_no_warning_when_n_z_range_set(self):
        """Test no n_z warning when n_z_range is set."""
        data = _create_base_vcg_data(
            vertical_coordinate="height",
            n_z_range=[40, 60],
            top_of_model=80000.0,
            bottom_layer_thickness=20.0,
            top_layer_thickness=5000.0,
        )
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            VerticalComputationalGrid(**data)
            emd_warnings = [x for x in w if "EMD Conformance" in str(x.message)]
            assert not any("n_z and n_z_range" in str(x.message) for x in emd_warnings)

    def test_description_required_when_thickness_fields_missing_warns(self):
        """Test warning when thickness fields are missing and no description."""
        data = _create_base_vcg_data(
            vertical_coordinate="height",
            n_z=50,
            # top_of_model not set
            # bottom_layer_thickness not set
            # top_layer_thickness not set
        )
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            VerticalComputationalGrid(**data)
            emd_warnings = [x for x in w if "EMD Conformance" in str(x.message)]
            assert any("top_of_model" in str(x.message) or "bottom_layer_thickness" in str(x.message) or "top_layer_thickness" in str(x.message) for x in emd_warnings)

    def test_no_warning_when_all_fields_set(self):
        """Test no warning when all recommended fields are set."""
        data = _create_base_vcg_data(
            vertical_coordinate="height",
            n_z=50,
            top_of_model=80000.0,
            bottom_layer_thickness=20.0,
            top_layer_thickness=5000.0,
        )
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            VerticalComputationalGrid(**data)
            emd_warnings = [x for x in w if "EMD Conformance" in str(x.message)]
            assert len(emd_warnings) == 0


class TestNZValidation:
    """Tests for n_z and n_z_range validation."""

    def test_n_z_valid(self):
        """Test valid n_z value."""
        data = _create_base_vcg_data(n_z=50)
        vcg = VerticalComputationalGrid(**data)
        assert vcg.n_z == 50

    def test_n_z_minimum(self):
        """Test n_z must be >= 1."""
        data = _create_base_vcg_data(n_z=1)
        vcg = VerticalComputationalGrid(**data)
        assert vcg.n_z == 1

        data = _create_base_vcg_data(n_z=0)
        with pytest.raises(ValidationError):
            VerticalComputationalGrid(**data)

    def test_n_z_and_n_z_range_mutually_exclusive(self):
        """Test that n_z and n_z_range cannot both be set."""
        data = _create_base_vcg_data(
            n_z=50,
            n_z_range=[40, 60],
        )
        with pytest.raises(ValidationError) as exc_info:
            VerticalComputationalGrid(**data)
        assert "cannot both be set" in str(exc_info.value)


class TestNZRangeValidation:
    """Tests for n_z_range validation."""

    def test_n_z_range_valid(self):
        """Test valid n_z_range."""
        data = _create_base_vcg_data(n_z_range=[40, 60])
        vcg = VerticalComputationalGrid(**data)
        assert vcg.n_z_range == [40, 60]

    def test_n_z_range_equal_values(self):
        """Test n_z_range with equal min and max."""
        data = _create_base_vcg_data(n_z_range=[50, 50])
        vcg = VerticalComputationalGrid(**data)
        assert vcg.n_z_range == [50, 50]

    def test_n_z_range_min_greater_than_max_raises(self):
        """Test that n_z_range min > max raises ValidationError."""
        data = _create_base_vcg_data(n_z_range=[60, 40])
        with pytest.raises(ValidationError) as exc_info:
            VerticalComputationalGrid(**data)
        assert "minimum must be <= maximum" in str(exc_info.value)

    def test_n_z_range_values_must_be_positive(self):
        """Test that n_z_range values must be >= 1."""
        data = _create_base_vcg_data(n_z_range=[0, 50])
        with pytest.raises(ValidationError) as exc_info:
            VerticalComputationalGrid(**data)
        assert "must be >= 1" in str(exc_info.value)

    def test_n_z_range_wrong_length_raises(self):
        """Test that wrong number of values raises ValidationError."""
        data = _create_base_vcg_data(n_z_range=[40])
        with pytest.raises(ValidationError):
            VerticalComputationalGrid(**data)

        data = _create_base_vcg_data(n_z_range=[40, 50, 60])
        with pytest.raises(ValidationError):
            VerticalComputationalGrid(**data)


class TestVerticalCoordinateValidation:
    """Tests for vertical_coordinate validation."""

    def test_vertical_coordinate_empty_string_raises(self):
        """Test that empty vertical_coordinate raises ValidationError."""
        data = _create_base_vcg_data(vertical_coordinate="")
        with pytest.raises(ValidationError) as exc_info:
            VerticalComputationalGrid(**data)
        assert "cannot be empty" in str(exc_info.value)

    def test_vertical_coordinate_whitespace_only_raises(self):
        """Test that whitespace-only vertical_coordinate raises ValidationError."""
        data = _create_base_vcg_data(vertical_coordinate="   ")
        with pytest.raises(ValidationError) as exc_info:
            VerticalComputationalGrid(**data)
        assert "cannot be empty" in str(exc_info.value)

    def test_vertical_coordinate_stripped(self):
        """Test that vertical_coordinate is stripped of whitespace."""
        data = _create_base_vcg_data(vertical_coordinate="  height  ")
        vcg = VerticalComputationalGrid(**data)
        assert vcg.vertical_coordinate == "height"


class TestThicknessValidation:
    """Tests for thickness field validation."""

    def test_thickness_must_be_positive(self):
        """Test that thickness values must be > 0."""
        data = _create_base_vcg_data(bottom_layer_thickness=20.0)
        vcg = VerticalComputationalGrid(**data)
        assert vcg.bottom_layer_thickness == 20.0

        data = _create_base_vcg_data(bottom_layer_thickness=0.0)
        with pytest.raises(ValidationError):
            VerticalComputationalGrid(**data)

        data = _create_base_vcg_data(top_layer_thickness=-100.0)
        with pytest.raises(ValidationError):
            VerticalComputationalGrid(**data)

    def test_top_of_model_can_be_any_value(self):
        """Test that top_of_model can be any value (including negative for ocean)."""
        # Positive (atmosphere)
        data = _create_base_vcg_data(top_of_model=80000.0)
        vcg = VerticalComputationalGrid(**data)
        assert vcg.top_of_model == 80000.0

        # Zero
        data = _create_base_vcg_data(top_of_model=0.0)
        vcg = VerticalComputationalGrid(**data)
        assert vcg.top_of_model == 0.0

        # Negative (ocean depth)
        data = _create_base_vcg_data(top_of_model=-5000.0)
        vcg = VerticalComputationalGrid(**data)
        assert vcg.top_of_model == -5000.0

"""
Tests for the EMD HorizontalGridCells class validators (EMD v1.0 Section 4.1.3).

These tests verify:
- southernmost_latitude and westernmost_longitude must both be set or neither
- truncation_method and truncation_number must both be set or neither
- resolution_range_km validation
- horizontal_units validation
"""

import pytest
from pydantic import ValidationError

from esgvoc.api.data_descriptors.EMD_models.horizontal_grid_cells import HorizontalGridCells


def _create_base_grid_cells_data(**overrides) -> dict:
    """Create base HorizontalGridCells data for testing."""
    data = {
        "id": "test_grid_cells",
        "type": "horizontal_grid_cells",
        "drs_name": "test_grid_cells",
        "region": "global",
        "grid_type": "regular_latitude_longitude",
        "temporal_refinement": "static",
    }
    data.update(overrides)
    return data


class TestLatLonPairValidation:
    """Tests for southernmost_latitude and westernmost_longitude pair validation (EMD Conformance 4.1.3)."""

    def test_both_lat_lon_set_valid(self):
        """Test that both latitude and longitude set is valid."""
        data = _create_base_grid_cells_data(
            southernmost_latitude=-90.0,
            westernmost_longitude=0.0,
        )
        grid = HorizontalGridCells(**data)
        assert grid.southernmost_latitude == -90.0
        assert grid.westernmost_longitude == 0.0

    def test_neither_lat_lon_set_valid(self):
        """Test that neither latitude nor longitude set is valid."""
        data = _create_base_grid_cells_data()
        grid = HorizontalGridCells(**data)
        assert grid.southernmost_latitude is None
        assert grid.westernmost_longitude is None

    def test_only_latitude_set_raises(self):
        """Test that only latitude set raises ValidationError."""
        data = _create_base_grid_cells_data(
            southernmost_latitude=-90.0,
            # westernmost_longitude not set
        )
        with pytest.raises(ValidationError) as exc_info:
            HorizontalGridCells(**data)
        assert "southernmost_latitude and westernmost_longitude must both be set or neither" in str(exc_info.value)

    def test_only_longitude_set_raises(self):
        """Test that only longitude set raises ValidationError."""
        data = _create_base_grid_cells_data(
            westernmost_longitude=0.0,
            # southernmost_latitude not set
        )
        with pytest.raises(ValidationError) as exc_info:
            HorizontalGridCells(**data)
        assert "southernmost_latitude and westernmost_longitude must both be set or neither" in str(exc_info.value)

    def test_latitude_bounds(self):
        """Test latitude value bounds (-90 to 90)."""
        # Valid minimum
        data = _create_base_grid_cells_data(southernmost_latitude=-90.0, westernmost_longitude=0.0)
        grid = HorizontalGridCells(**data)
        assert grid.southernmost_latitude == -90.0

        # Valid maximum
        data = _create_base_grid_cells_data(southernmost_latitude=90.0, westernmost_longitude=0.0)
        grid = HorizontalGridCells(**data)
        assert grid.southernmost_latitude == 90.0

        # Below minimum
        data = _create_base_grid_cells_data(southernmost_latitude=-91.0, westernmost_longitude=0.0)
        with pytest.raises(ValidationError):
            HorizontalGridCells(**data)

        # Above maximum
        data = _create_base_grid_cells_data(southernmost_latitude=91.0, westernmost_longitude=0.0)
        with pytest.raises(ValidationError):
            HorizontalGridCells(**data)

    def test_longitude_bounds(self):
        """Test longitude value bounds (0 to <360)."""
        # Valid minimum
        data = _create_base_grid_cells_data(southernmost_latitude=0.0, westernmost_longitude=0.0)
        grid = HorizontalGridCells(**data)
        assert grid.westernmost_longitude == 0.0

        # Valid near maximum (exclusive)
        data = _create_base_grid_cells_data(southernmost_latitude=0.0, westernmost_longitude=359.9)
        grid = HorizontalGridCells(**data)
        assert grid.westernmost_longitude == 359.9

        # At maximum (should fail - lt=360.0)
        data = _create_base_grid_cells_data(southernmost_latitude=0.0, westernmost_longitude=360.0)
        with pytest.raises(ValidationError):
            HorizontalGridCells(**data)

        # Below minimum
        data = _create_base_grid_cells_data(southernmost_latitude=0.0, westernmost_longitude=-1.0)
        with pytest.raises(ValidationError):
            HorizontalGridCells(**data)


class TestTruncationPairValidation:
    """Tests for truncation_method and truncation_number pair validation (EMD Conformance 4.1.3)."""

    def test_both_truncation_set_valid(self):
        """Test that both truncation_method and truncation_number set is valid."""
        data = _create_base_grid_cells_data(
            truncation_method="triangular",
            truncation_number=42,
        )
        grid = HorizontalGridCells(**data)
        assert grid.truncation_method == "triangular"
        assert grid.truncation_number == 42

    def test_neither_truncation_set_valid(self):
        """Test that neither truncation field set is valid."""
        data = _create_base_grid_cells_data()
        grid = HorizontalGridCells(**data)
        assert grid.truncation_method is None
        assert grid.truncation_number is None

    def test_only_truncation_method_set_raises(self):
        """Test that only truncation_method set raises ValidationError."""
        data = _create_base_grid_cells_data(
            truncation_method="triangular",
            # truncation_number not set
        )
        with pytest.raises(ValidationError) as exc_info:
            HorizontalGridCells(**data)
        assert "truncation_number is required when truncation_method is set" in str(exc_info.value)

    def test_only_truncation_number_set_raises(self):
        """Test that only truncation_number set raises ValidationError."""
        data = _create_base_grid_cells_data(
            truncation_number=42,
            # truncation_method not set
        )
        with pytest.raises(ValidationError) as exc_info:
            HorizontalGridCells(**data)
        assert "truncation_method is required when truncation_number is set" in str(exc_info.value)

    def test_truncation_number_minimum(self):
        """Test truncation_number must be >= 1."""
        data = _create_base_grid_cells_data(
            truncation_method="triangular",
            truncation_number=1,
        )
        grid = HorizontalGridCells(**data)
        assert grid.truncation_number == 1

        data = _create_base_grid_cells_data(
            truncation_method="triangular",
            truncation_number=0,
        )
        with pytest.raises(ValidationError):
            HorizontalGridCells(**data)


class TestResolutionRangeValidation:
    """Tests for resolution_range_km validation."""

    def test_valid_resolution_range(self):
        """Test valid resolution range with min < max."""
        data = _create_base_grid_cells_data(
            resolution_range_km=[10.0, 100.0],
        )
        grid = HorizontalGridCells(**data)
        assert grid.resolution_range_km == [10.0, 100.0]

    def test_resolution_range_equal_values(self):
        """Test resolution range with equal min and max."""
        data = _create_base_grid_cells_data(
            resolution_range_km=[50.0, 50.0],
        )
        grid = HorizontalGridCells(**data)
        assert grid.resolution_range_km == [50.0, 50.0]

    def test_resolution_range_min_greater_than_max_raises(self):
        """Test that min > max raises ValidationError."""
        data = _create_base_grid_cells_data(
            resolution_range_km=[100.0, 10.0],  # min > max
        )
        with pytest.raises(ValidationError) as exc_info:
            HorizontalGridCells(**data)
        assert "minimum must be <= maximum" in str(exc_info.value)

    def test_resolution_range_non_positive_raises(self):
        """Test that non-positive values raise ValidationError."""
        data = _create_base_grid_cells_data(
            resolution_range_km=[0.0, 100.0],  # min is 0
        )
        with pytest.raises(ValidationError) as exc_info:
            HorizontalGridCells(**data)
        assert "must be > 0" in str(exc_info.value)

        data = _create_base_grid_cells_data(
            resolution_range_km=[-10.0, 100.0],  # negative
        )
        with pytest.raises(ValidationError) as exc_info:
            HorizontalGridCells(**data)
        assert "must be > 0" in str(exc_info.value)

    def test_resolution_range_wrong_length_raises(self):
        """Test that wrong number of values raises ValidationError."""
        data = _create_base_grid_cells_data(
            resolution_range_km=[10.0],  # Only one value
        )
        with pytest.raises(ValidationError):
            HorizontalGridCells(**data)

        data = _create_base_grid_cells_data(
            resolution_range_km=[10.0, 50.0, 100.0],  # Three values
        )
        with pytest.raises(ValidationError):
            HorizontalGridCells(**data)


class TestHorizontalUnitsValidation:
    """Tests for horizontal_units validation."""

    def test_horizontal_units_required_with_resolution(self):
        """Test that horizontal_units is required when resolution is set."""
        data = _create_base_grid_cells_data(
            x_resolution=1.0,
            # horizontal_units not set
        )
        with pytest.raises(ValidationError) as exc_info:
            HorizontalGridCells(**data)
        assert "horizontal_units is required" in str(exc_info.value)

    def test_horizontal_units_valid_values(self):
        """Test valid horizontal_units values."""
        for units in ["km", "degree"]:
            data = _create_base_grid_cells_data(
                x_resolution=1.0,
                horizontal_units=units,
            )
            grid = HorizontalGridCells(**data)
            assert grid.horizontal_units == units

    def test_horizontal_units_invalid_value_raises(self):
        """Test invalid horizontal_units value raises ValidationError."""
        data = _create_base_grid_cells_data(
            x_resolution=1.0,
            horizontal_units="meters",  # Invalid
        )
        with pytest.raises(ValidationError) as exc_info:
            HorizontalGridCells(**data)
        assert "must be one of" in str(exc_info.value)

    def test_horizontal_units_without_resolution_raises(self):
        """Test that horizontal_units without resolution raises ValidationError."""
        data = _create_base_grid_cells_data(
            horizontal_units="km",
            # No x_resolution or y_resolution
        )
        with pytest.raises(ValidationError) as exc_info:
            HorizontalGridCells(**data)
        assert "must also be None" in str(exc_info.value)


class TestNCellsValidation:
    """Tests for n_cells validation."""

    def test_n_cells_valid(self):
        """Test valid n_cells value."""
        data = _create_base_grid_cells_data(n_cells=1000)
        grid = HorizontalGridCells(**data)
        assert grid.n_cells == 1000

    def test_n_cells_minimum(self):
        """Test n_cells must be >= 1."""
        data = _create_base_grid_cells_data(n_cells=1)
        grid = HorizontalGridCells(**data)
        assert grid.n_cells == 1

        data = _create_base_grid_cells_data(n_cells=0)
        with pytest.raises(ValidationError):
            HorizontalGridCells(**data)


class TestResolutionValidation:
    """Tests for x_resolution and y_resolution validation."""

    def test_resolution_must_be_positive(self):
        """Test that resolution values must be > 0."""
        data = _create_base_grid_cells_data(
            x_resolution=1.0,
            horizontal_units="degree",
        )
        grid = HorizontalGridCells(**data)
        assert grid.x_resolution == 1.0

        data = _create_base_grid_cells_data(
            x_resolution=0.0,
            horizontal_units="degree",
        )
        with pytest.raises(ValidationError):
            HorizontalGridCells(**data)

        data = _create_base_grid_cells_data(
            y_resolution=-1.0,
            horizontal_units="degree",
        )
        with pytest.raises(ValidationError):
            HorizontalGridCells(**data)

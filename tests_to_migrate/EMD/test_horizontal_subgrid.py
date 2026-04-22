"""
Tests for the EMD HorizontalSubgrid class validators (EMD v1.0 Section 4.1.2).

These tests verify:
- cell_variable_type must have at least one value (warning)
- cell_variable_type values must be unique (warning)
"""

import warnings

import pytest

from esgvoc.api.data_descriptors.EMD_models.horizontal_subgrid import HorizontalSubgrid


def _create_base_subgrid_data(**overrides) -> dict:
    """Create base HorizontalSubgrid data for testing."""
    data = {
        "id": "test_subgrid",
        "type": "horizontal_subgrid",
        "drs_name": "test_subgrid",
        "cell_variable_type": ["mass"],
        "horizontal_grid_cells": {
            "id": "test_grid_cells",
            "type": "horizontal_grid_cells",
            "drs_name": "test_grid_cells",
            "region": "global",
            "grid_type": "regular_latitude_longitude",
            "temporal_refinement": "static",
        },
    }
    data.update(overrides)
    return data


class TestCellVariableTypeValidation:
    """Tests for cell_variable_type validation (EMD Conformance Section 4.1.2)."""

    def test_valid_single_cell_variable_type(self):
        """Test valid single cell_variable_type."""
        data = _create_base_subgrid_data(cell_variable_type=["mass"])
        subgrid = HorizontalSubgrid(**data)
        assert subgrid.cell_variable_type == ["mass"]

    def test_valid_multiple_cell_variable_types(self):
        """Test valid multiple cell_variable_types."""
        data = _create_base_subgrid_data(cell_variable_type=["mass", "x_velocity", "y_velocity"])
        subgrid = HorizontalSubgrid(**data)
        assert len(subgrid.cell_variable_type) == 3

    def test_empty_cell_variable_type_warns(self):
        """Test warning when cell_variable_type is empty."""
        data = _create_base_subgrid_data(cell_variable_type=[])
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            HorizontalSubgrid(**data)
            emd_warnings = [x for x in w if "EMD Conformance" in str(x.message)]
            assert any("At least one cell_variable_type must be specified" in str(x.message) for x in emd_warnings)

    def test_duplicate_cell_variable_type_warns(self):
        """Test warning when cell_variable_type has duplicates."""
        data = _create_base_subgrid_data(cell_variable_type=["mass", "mass"])  # Duplicate
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            HorizontalSubgrid(**data)
            emd_warnings = [x for x in w if "EMD Conformance" in str(x.message)]
            assert any("appears multiple times" in str(x.message) for x in emd_warnings)

    def test_multiple_duplicates_warn_for_each(self):
        """Test warning for each duplicate in cell_variable_type."""
        data = _create_base_subgrid_data(cell_variable_type=["mass", "mass", "velocity", "velocity"])
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            HorizontalSubgrid(**data)
            emd_warnings = [x for x in w if "EMD Conformance" in str(x.message) and "appears multiple times" in str(x.message)]
            # Should warn for 'mass' and 'velocity' duplicates
            assert len(emd_warnings) >= 2

    def test_unique_cell_variable_types_no_warning(self):
        """Test no warning when all cell_variable_types are unique."""
        data = _create_base_subgrid_data(cell_variable_type=["mass", "x_velocity", "y_velocity", "velocity"])
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            HorizontalSubgrid(**data)
            emd_warnings = [x for x in w if "EMD Conformance" in str(x.message) and "appears multiple times" in str(x.message)]
            assert len(emd_warnings) == 0


class TestHorizontalSubgridCreation:
    """Tests for HorizontalSubgrid creation."""

    def test_create_with_minimal_data(self):
        """Test creating a subgrid with minimal required data."""
        data = _create_base_subgrid_data()
        subgrid = HorizontalSubgrid(**data)
        assert subgrid.id == "test_subgrid"
        assert subgrid.horizontal_grid_cells is not None

    def test_horizontal_grid_cells_nested_validation(self):
        """Test that nested horizontal_grid_cells is validated."""
        data = _create_base_subgrid_data()
        # Add invalid lat/lon pair (only lat set)
        data["horizontal_grid_cells"]["southernmost_latitude"] = -90.0
        # westernmost_longitude not set - should fail

        with pytest.raises(Exception):  # Could be ValidationError
            HorizontalSubgrid(**data)

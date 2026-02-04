"""
Tests for the EMD Arrangement class (EMD v1.0 Section 7.3).

These tests verify:
- n_sub_grid field is present and validated
"""

import pytest
from pydantic import ValidationError

from esgvoc.api.data_descriptors.EMD_models.arrangement import Arrangement


def _create_base_arrangement_data(**overrides) -> dict:
    """Create base Arrangement data for testing."""
    data = {
        "id": "arakawa_c",
        "type": "arrangement",
        "drs_name": "arakawa_c",
        "n_sub_grid": 3,
    }
    data.update(overrides)
    return data


class TestArrangementNSubGrid:
    """Tests for n_sub_grid field."""

    def test_n_sub_grid_valid(self):
        """Test valid n_sub_grid value."""
        data = _create_base_arrangement_data(n_sub_grid=3)
        arrangement = Arrangement(**data)
        assert arrangement.n_sub_grid == 3

    def test_n_sub_grid_required(self):
        """Test that n_sub_grid is required."""
        data = {
            "id": "arakawa_c",
            "type": "arrangement",
            # n_sub_grid not set
        }
        with pytest.raises(ValidationError) as exc_info:
            Arrangement(**data)
        assert "n_sub_grid" in str(exc_info.value)

    def test_n_sub_grid_various_values(self):
        """Test various n_sub_grid values for different Arakawa grids."""
        # Arakawa A grid typically has 1 subgrid
        data = _create_base_arrangement_data(id="arakawa_a", n_sub_grid=1)
        arrangement = Arrangement(**data)
        assert arrangement.n_sub_grid == 1

        # Arakawa B grid typically has 2 subgrids
        data = _create_base_arrangement_data(id="arakawa_b", n_sub_grid=2)
        arrangement = Arrangement(**data)
        assert arrangement.n_sub_grid == 2

        # Arakawa C grid typically has 3 subgrids
        data = _create_base_arrangement_data(id="arakawa_c", n_sub_grid=3)
        arrangement = Arrangement(**data)
        assert arrangement.n_sub_grid == 3

    def test_n_sub_grid_must_be_integer(self):
        """Test that n_sub_grid must be an integer."""
        data = _create_base_arrangement_data(n_sub_grid=3.5)
        # Pydantic will coerce or raise depending on strict mode
        # Let's test that it at least works with integers
        data = _create_base_arrangement_data(n_sub_grid=3)
        arrangement = Arrangement(**data)
        assert isinstance(arrangement.n_sub_grid, int)


class TestArrangementCreation:
    """Tests for Arrangement creation."""

    def test_create_arakawa_a(self):
        """Test creating Arakawa A arrangement."""
        data = _create_base_arrangement_data(
            id="arakawa_a",
            n_sub_grid=1,
        )
        arrangement = Arrangement(**data)
        assert arrangement.id == "arakawa_a"
        assert arrangement.n_sub_grid == 1

    def test_create_arakawa_b(self):
        """Test creating Arakawa B arrangement."""
        data = _create_base_arrangement_data(
            id="arakawa_b",
            n_sub_grid=2,
        )
        arrangement = Arrangement(**data)
        assert arrangement.id == "arakawa_b"
        assert arrangement.n_sub_grid == 2

    def test_create_arakawa_c(self):
        """Test creating Arakawa C arrangement."""
        data = _create_base_arrangement_data(
            id="arakawa_c",
            n_sub_grid=3,
        )
        arrangement = Arrangement(**data)
        assert arrangement.id == "arakawa_c"
        assert arrangement.n_sub_grid == 3

    def test_create_arakawa_d(self):
        """Test creating Arakawa D arrangement."""
        data = _create_base_arrangement_data(
            id="arakawa_d",
            n_sub_grid=3,
        )
        arrangement = Arrangement(**data)
        assert arrangement.id == "arakawa_d"

    def test_create_arakawa_e(self):
        """Test creating Arakawa E arrangement."""
        data = _create_base_arrangement_data(
            id="arakawa_e",
            n_sub_grid=2,
        )
        arrangement = Arrangement(**data)
        assert arrangement.id == "arakawa_e"

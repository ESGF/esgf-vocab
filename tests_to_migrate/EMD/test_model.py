"""
Tests for the EMD Model class validators (EMD v1.0 Section 2).

These tests verify:
- model_components must match dynamic_components in length
- embedded_components validation (pairs from dynamic_components, different, unique embedding)
- coupled_components validation (pairs from dynamic_components, different, connectivity)
- embedded/coupled exclusivity (components are embedded XOR coupled)
"""

import warnings

import pytest
from pydantic import ValidationError

from esgvoc.api.data_descriptors.EMD_models.model import Model


def _create_reference() -> dict:
    """Create a valid reference dict for testing."""
    return {
        "id": "ref1",
        "type": "reference",
        "drs_name": "ref1",
        "citation": "Test Author et al. (2024). Test Paper. Test Journal.",
        "doi": "https://doi.org/10.1234/test",
    }


def _create_minimal_model_component(component_id: str) -> dict:
    """Create a minimal model component dict for testing."""
    return {
        "id": f"{component_id}_mc",
        "type": "model_component",
        "drs_name": f"{component_id}_mc",
        "component": component_id,
        "name": f"Test {component_id.title()} Component",
        "family": "Test Family",
        "description": f"A test model component for {component_id}",
        "label": f"Test {component_id}",
        "label_extended": f"Extended test {component_id}",
        "code_base": "https://example.com/code",
        "horizontal_computational_grid": {
            "id": "test_hcg",
            "type": "horizontal_computational_grid",
            "arrangement": "arakawa_c",
            "horizontal_subgrids": [
                {
                    "id": "test_subgrid",
                    "type": "horizontal_subgrid",
                    "drs_name": "test_subgrid",
                    "cell_variable_type": ["mass"],
                    "horizontal_grid_cells": {
                        "id": "test_cells",
                        "type": "horizontal_grid_cells",
                        "drs_name": "test_cells",
                        "region": "global",
                        "grid_type": "regular_latitude_longitude",
                        "temporal_refinement": "static",
                    },
                }
            ],
        },
        "vertical_computational_grid": {
            "id": "test_vcg",
            "type": "vertical_computational_grid",
            "vertical_coordinate": "none",
            "description": "No vertical dimension",
        },
        "references": [_create_reference()],
    }


def _create_base_model_data(
    dynamic_components: list[str],
    model_components: list[str] | None = None,
    embedded_components: list[tuple[str, str]] | None = None,
    coupled_components: list[tuple[str, str]] | None = None,
) -> dict:
    """Create base model data for testing."""
    if model_components is None:
        model_components = dynamic_components

    return {
        "id": "test_model",
        "type": "model",
        "drs_name": "test_model",
        "name": "Test Model",
        "family": "Test Family",
        "dynamic_components": dynamic_components,
        "prescribed_components": [],
        "omitted_components": [],
        "description": "A test model",
        "calendar": ["gregorian"],
        "release_year": 2024,
        "references": [_create_reference()],
        "model_components": [_create_minimal_model_component(c) for c in model_components],
        "embedded_components": embedded_components or [],
        "coupled_components": coupled_components or [],
    }


class TestModelComponentsLength:
    """Tests for model_components length validation."""

    def test_model_components_match_dynamic_components_length(self):
        """Test that model_components can have the same length as dynamic_components."""
        data = _create_base_model_data(
            dynamic_components=["atmos", "ocean"],
            model_components=["atmos", "ocean"],
            coupled_components=[("atmos", "ocean")],
        )
        model = Model(**data)
        assert len(model.model_components) == len(model.dynamic_components)

    def test_model_components_length_mismatch_raises(self):
        """Test that mismatched lengths raise ValidationError."""
        data = _create_base_model_data(
            dynamic_components=["atmos", "ocean", "land"],
            model_components=["atmos", "ocean"],  # Only 2, should be 3
            coupled_components=[("atmos", "ocean"), ("ocean", "land")],
        )
        with pytest.raises(ValidationError) as exc_info:
            Model(**data)
        assert "model_components" in str(exc_info.value)


class TestEmbeddedComponentsValidation:
    """Tests for embedded_components validation (EMD Conformance Section 2)."""

    def test_valid_embedded_components(self):
        """Test valid embedded_components configuration."""
        data = _create_base_model_data(
            dynamic_components=["atmos", "land", "ocean"],
            embedded_components=[("land", "atmos")],  # land is embedded in atmos
            coupled_components=[("atmos", "ocean")],  # atmos and ocean are coupled
        )
        # Should not raise any warnings for valid config
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            model = Model(**data)
            # Filter for EMD Conformance warnings only
            emd_warnings = [x for x in w if "EMD Conformance" in str(x.message)]
            # May have warnings about non-coupled components, but not about embedded validation
            embedded_errors = [x for x in emd_warnings if "Embedded" in str(x.message) and "not in dynamic" in str(x.message)]
            assert len(embedded_errors) == 0

    def test_embedded_component_not_in_dynamic_components_warns(self):
        """Test warning when embedded component is not in dynamic_components."""
        data = _create_base_model_data(
            dynamic_components=["atmos", "ocean"],
            embedded_components=[("land", "atmos")],  # land is not in dynamic_components
            coupled_components=[("atmos", "ocean")],
        )
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            Model(**data)
            emd_warnings = [x for x in w if "EMD Conformance" in str(x.message)]
            assert any("land" in str(x.message) and "not in dynamic_components" in str(x.message) for x in emd_warnings)

    def test_host_component_not_in_dynamic_components_warns(self):
        """Test warning when host component is not in dynamic_components."""
        data = _create_base_model_data(
            dynamic_components=["atmos", "ocean"],
            embedded_components=[("ocean", "land")],  # land (host) is not in dynamic_components
            coupled_components=[("atmos", "ocean")],
        )
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            Model(**data)
            emd_warnings = [x for x in w if "EMD Conformance" in str(x.message)]
            assert any("land" in str(x.message) and "not in dynamic_components" in str(x.message) for x in emd_warnings)

    def test_embedded_same_as_host_warns(self):
        """Test warning when embedded and host components are the same."""
        data = _create_base_model_data(
            dynamic_components=["atmos", "ocean"],
            embedded_components=[("atmos", "atmos")],  # Same component
            coupled_components=[("atmos", "ocean")],
        )
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            Model(**data)
            emd_warnings = [x for x in w if "EMD Conformance" in str(x.message)]
            assert any("must be different" in str(x.message) for x in emd_warnings)

    def test_component_embedded_in_multiple_hosts_warns(self):
        """Test warning when a component is embedded in multiple hosts."""
        data = _create_base_model_data(
            dynamic_components=["atmos", "ocean", "land", "ice"],
            model_components=["atmos", "ocean", "land", "ice"],
            embedded_components=[("land", "atmos"), ("land", "ocean")],  # land embedded twice
            coupled_components=[("atmos", "ocean"), ("ocean", "ice")],
        )
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            Model(**data)
            emd_warnings = [x for x in w if "EMD Conformance" in str(x.message)]
            assert any("embedded in multiple hosts" in str(x.message) for x in emd_warnings)


class TestCoupledComponentsValidation:
    """Tests for coupled_components validation (EMD Conformance Section 2)."""

    def test_valid_coupled_components(self):
        """Test valid coupled_components configuration."""
        data = _create_base_model_data(
            dynamic_components=["atmos", "ocean"],
            coupled_components=[("atmos", "ocean")],
        )
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            Model(**data)
            emd_warnings = [x for x in w if "EMD Conformance" in str(x.message) and "Coupled" in str(x.message)]
            # Should not have coupled-specific errors
            coupled_errors = [x for x in emd_warnings if "not in dynamic_components" in str(x.message)]
            assert len(coupled_errors) == 0

    def test_coupled_component_not_in_dynamic_components_warns(self):
        """Test warning when coupled component is not in dynamic_components."""
        data = _create_base_model_data(
            dynamic_components=["atmos", "ocean"],
            coupled_components=[("atmos", "land")],  # land not in dynamic_components
        )
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            Model(**data)
            emd_warnings = [x for x in w if "EMD Conformance" in str(x.message)]
            assert any("land" in str(x.message) and "not in dynamic_components" in str(x.message) for x in emd_warnings)

    def test_coupled_same_components_warns(self):
        """Test warning when coupled pair has same component twice."""
        data = _create_base_model_data(
            dynamic_components=["atmos", "ocean"],
            coupled_components=[("atmos", "atmos")],  # Same component
        )
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            Model(**data)
            emd_warnings = [x for x in w if "EMD Conformance" in str(x.message)]
            assert any("must be different" in str(x.message) for x in emd_warnings)

    def test_coupled_pairs_must_share_components(self):
        """Test warning when coupled pairs don't share any components."""
        data = _create_base_model_data(
            dynamic_components=["atmos", "ocean", "land", "ice"],
            model_components=["atmos", "ocean", "land", "ice"],
            coupled_components=[("atmos", "ocean"), ("land", "ice")],  # No shared components
        )
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            Model(**data)
            emd_warnings = [x for x in w if "EMD Conformance" in str(x.message)]
            assert any("does not share any component" in str(x.message) for x in emd_warnings)

    def test_coupled_pairs_sharing_components_valid(self):
        """Test no warning when coupled pairs share components (connected graph)."""
        data = _create_base_model_data(
            dynamic_components=["atmos", "ocean", "land"],
            coupled_components=[("atmos", "ocean"), ("ocean", "land")],  # ocean is shared
        )
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            Model(**data)
            emd_warnings = [x for x in w if "EMD Conformance" in str(x.message)]
            assert not any("does not share any component" in str(x.message) for x in emd_warnings)


class TestEmbeddedCoupledExclusivity:
    """Tests for embedded/coupled exclusivity (EMD Conformance Section 2)."""

    def test_component_both_embedded_and_coupled_warns(self):
        """Test warning when a component is both embedded and coupled."""
        data = _create_base_model_data(
            dynamic_components=["atmos", "ocean", "land"],
            embedded_components=[("land", "atmos")],  # land is embedded
            coupled_components=[("land", "ocean")],  # land is also coupled
        )
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            Model(**data)
            emd_warnings = [x for x in w if "EMD Conformance" in str(x.message)]
            assert any("both embedded and coupled" in str(x.message) for x in emd_warnings)

    def test_non_embedded_must_be_coupled_warns(self):
        """Test warning when a non-embedded component is not coupled."""
        # Create a case where a component is neither embedded nor coupled
        data = _create_base_model_data(
            dynamic_components=["atmos", "ocean", "land"],
            embedded_components=[],  # No embedded components
            coupled_components=[("atmos", "ocean")],  # Only atmos and ocean coupled, land is orphaned
        )
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            Model(**data)
            emd_warnings = [x for x in w if "EMD Conformance" in str(x.message)]
            assert any("neither embedded nor coupled" in str(x.message) for x in emd_warnings)

    def test_all_components_properly_classified(self):
        """Test no warning when all components are either embedded or coupled (not both)."""
        data = _create_base_model_data(
            dynamic_components=["atmos", "ocean", "land"],
            embedded_components=[("land", "atmos")],  # land is embedded in atmos
            coupled_components=[("atmos", "ocean")],  # atmos and ocean are coupled
            # land is embedded, atmos and ocean are coupled - all accounted for
        )
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            Model(**data)
            emd_warnings = [x for x in w if "EMD Conformance" in str(x.message)]
            # Should not warn about exclusivity issues
            assert not any("both embedded and coupled" in str(x.message) for x in emd_warnings)
            assert not any("neither embedded nor coupled" in str(x.message) for x in emd_warnings)


class TestModelComponentsMatchDynamic:
    """Tests for model_component.component matching dynamic_components."""

    def test_model_component_not_in_dynamic_warns(self):
        """Test warning when model_component.component is not in dynamic_components."""
        data = _create_base_model_data(
            dynamic_components=["atmos", "ocean"],
            model_components=["atmos", "land"],  # land is not a dynamic component
            coupled_components=[("atmos", "ocean")],
        )
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            Model(**data)
            emd_warnings = [x for x in w if "EMD Conformance" in str(x.message)]
            assert any("land" in str(x.message) and "not in dynamic_components" in str(x.message) for x in emd_warnings)

    def test_duplicate_model_component_warns(self):
        """Test warning when same component appears multiple times in model_components."""
        # Create model components with same component ID
        mc1 = _create_minimal_model_component("atmos")
        mc2 = _create_minimal_model_component("atmos")  # Duplicate
        mc2["id"] = "atmos_mc_2"  # Different model component ID but same component
        mc2["drs_name"] = "atmos_mc_2"

        data = {
            "id": "test_model",
            "type": "model",
            "drs_name": "test_model",
            "name": "Test Model",
            "family": "Test Family",
            "dynamic_components": ["atmos", "ocean"],
            "prescribed_components": [],
            "omitted_components": [],
            "description": "A test model",
            "calendar": ["gregorian"],
            "release_year": 2024,
            "references": [_create_reference()],
            "model_components": [mc1, mc2],  # Both reference "atmos"
            "embedded_components": [],
            "coupled_components": [("atmos", "ocean")],
        }
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            Model(**data)
            emd_warnings = [x for x in w if "EMD Conformance" in str(x.message)]
            assert any("appears multiple times" in str(x.message) for x in emd_warnings)

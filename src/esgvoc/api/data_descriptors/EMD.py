"""
Essential Model Documentation (EMD) - Comprehensive Module

This module contains all EMD-related models including:
- Controlled Vocabulary (CV) models
- Core EMD classes (Model, EMDModelComponent, grids, references)

All CV fields are properly typed using their respective CV models instead of plain strings.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

# Import existing CV models from other files
from esgvoc.api.data_descriptors.calendar_new import Calendar
from esgvoc.api.data_descriptors.component_type_new import ComponentType
from esgvoc.api.data_descriptors.data_descriptor import DataDescriptor, PlainTermDataDescriptor
from esgvoc.api.data_descriptors.grid_coordinate_new import Coordinate
from esgvoc.api.data_descriptors.horizontal_grid import HorizontalGrid

# ============================================================================
# NEW CV MODELS
# ============================================================================


class VerticalUnits(PlainTermDataDescriptor):
    """
    Vertical units CV (7.14 vertical_units CV).

    Physical units of vertical grid thickness and position values.
    Options include: m, Pa, K
    """

    pass


# ============================================================================
# REFERENCE MODEL
# ============================================================================


class Reference(BaseModel):
    """
    Academic reference to published work for the top-level model or model components.

    An academic reference to published work for the top-level model or one of its model
    components is defined by the following properties:

    • Citation
        ◦ A human-readable citation for the work.
        ◦ E.g. Smith, R. S., Mathiot, P., Siahaan, A., Lee, V., Cornford, S. L., Gregory, J. M.,
          et al. (2021). Coupling the U.K. Earth System model to dynamic models of the Greenland
          and Antarctic ice sheets. Journal of Advances in Modeling Earth Systems, 13,
          e2021MS002520. https://doi.org/10.1029/2021MS002520, 2023
    • DOI
        ◦ The persistent identifier (DOI) used to identify the work.
        ◦ A DOI is required for all references. A reference that does not already have a DOI
          (as could be the case for some technical reports, for instance) must be given one
          (e.g. with a service like Zenodo).
        ◦ E.g. https://doi.org/10.1029/2021MS002520
    """

    citation: str = Field(description="A human-readable citation for the work.", min_length=1)
    doi: str = Field(
        description="The persistent identifier (DOI) used to identify the work. Must be a valid DOI URL.", min_length=1
    )

    @field_validator("doi")
    @classmethod
    def validate_doi(cls, v):
        """Validate that DOI follows proper format."""
        if not v.startswith("https://doi.org/"):
            raise ValueError('DOI must start with "https://doi.org/"')
        if len(v) <= len("https://doi.org/"):
            raise ValueError('DOI must contain identifier after "https://doi.org/"')
        return v

    @field_validator("citation")
    @classmethod
    def validate_citation(cls, v):
        """Validate that citation is not empty."""
        if not v.strip():
            raise ValueError("Citation cannot be empty")
        return v.strip()


# ============================================================================
# NATIVE VERTICAL GRID
# ============================================================================


class NativeVerticalGrid(DataDescriptor):
    """
    Native vertical grid description (Section 4.2).

    The model component's native vertical grid is described by a subset of the following properties.
    """

    coordinate: str | Coordinate = Field(
        description="The coordinate type of the vertical grid. Taken from 7.13 coordinate CV. If there is no vertical grid, then the value 'none' must be selected."
    )
    n_z: Optional[int] = Field(
        default=None,
        description="The number of layers (i.e. grid cells) in the Z direction. Omit when not applicable or not constant. If the number of layers varies in time or across the horizontal grid, then the n_z_range property may be used instead.",
        ge=1,
    )
    n_z_range: Optional[List[int]] = Field(
        default=None,
        description="The minimum and maximum number of layers for vertical grids with a time- or space-varying number of layers. Omit if the n_z property has been set.",
        min_length=2,
        max_length=2,
    )
    bottom_layer_thickness: Optional[float] = Field(
        default=None,
        description="The thickness of the bottom model layer (i.e. the layer closest to the centre of the Earth). The value should be reported as a dimensional (as opposed to parametric) quantity. The value's physical units are given by the vertical_units property.",
        gt=0,
    )
    top_layer_thickness: Optional[float] = Field(
        default=None,
        description="The thickness of the top model layer (i.e. the layer furthest away from the centre of the Earth). The value should be reported as a dimensional (as opposed to parametric) quantity. The value's physical units are given by the vertical_units property.",
        gt=0,
    )
    top_of_model: Optional[float] = Field(
        default=None,
        description="The upper boundary of the top model layer (i.e. the upper boundary of the layer that is furthest away from the centre of the Earth). The value should be relative to the lower boundary of the bottom layer of the model, or an appropriate datum (such as mean sea level). The value's physical units are given by the vertical_units property.",
    )
    vertical_units: Optional[str | VerticalUnits] = Field(
        default=None,
        description="The physical units of the bottom_layer_thickness, top_layer_thickness, and top_of_model property values. Taken from 7.14 vertical_units CV.",
    )

    @field_validator("coordinate", mode="before")
    @classmethod
    def validate_coordinate(cls, v):
        """Validate that coordinate is not empty if it's a string."""
        if isinstance(v, str):
            if not v.strip():
                raise ValueError("Coordinate cannot be empty")
            return v.strip()
        return v

    @field_validator("n_z_range")
    @classmethod
    def validate_n_z_range(cls, v):
        """Validate that n_z_range has exactly 2 values and min <= max."""
        if v is not None:
            if len(v) != 2:
                raise ValueError("n_z_range must contain exactly 2 values [min, max]")
            if v[0] > v[1]:
                raise ValueError("n_z_range: minimum must be <= maximum")
            if any(val < 1 for val in v):
                raise ValueError("n_z_range values must be >= 1")
        return v

    @field_validator("vertical_units", mode="before")
    @classmethod
    def validate_units_requirement(cls, v, info):
        """Validate that vertical_units is provided when thickness/top_of_model values are set."""
        thickness_fields = ["bottom_layer_thickness", "top_layer_thickness", "top_of_model"]
        has_thickness_values = any(info.data.get(field) is not None for field in thickness_fields)

        if has_thickness_values and not v:
            raise ValueError(
                "vertical_units is required when bottom_layer_thickness, top_layer_thickness, or top_of_model are set"
            )
        return v

    @field_validator("n_z")
    @classmethod
    def validate_n_z_exclusivity(cls, v, info):
        """Validate that n_z and n_z_range are mutually exclusive."""
        if v is not None and info.data.get("n_z_range") is not None:
            raise ValueError("n_z and n_z_range cannot both be set")
        return v

    def accept(self, visitor):
        """Accept a data descriptor visitor."""
        return visitor.visit_plain_term(self)


# ============================================================================
# EMD MODEL COMPONENT
# ============================================================================


class EMDModelComponent(PlainTermDataDescriptor):
    """
    Properties that provide a description of individual model components (Section 3).

    Eight model components are defined that somewhat independently account for different
    sets of interactive processes: aerosol, atmosphere, atmospheric chemistry, land surface,
    land ice, ocean, ocean biogeochemistry, and sea ice.
    """

    component: str | ComponentType = Field(description="The type of the model component. Taken from 7.1 component CV.")
    name: str = Field(description="The name of the model component.", min_length=1)
    family: str = Field(
        description="The model component's 'family' name. Use 'none' to indicate that there is no such family.",
        min_length=1,
    )
    references: List[Reference] = Field(
        description="One or more references to published work for the model component.", min_length=1
    )
    code_base: str = Field(
        description="A URL (preferably for a DOI) for the source code for the model component. Set to 'private' if not publicly available.",
        min_length=1,
    )
    embedded_in: Optional[str | ComponentType] = Field(
        default=None,
        description="The host model component (identified by its component property) in which this component is 'embedded'. Taken from 7.1 component CV. Omit when this component is coupled with other components.",
    )
    coupled_with: Optional[List[str | ComponentType]] = Field(
        default=None,
        description="The model components (identified by their component properties) with which this component is 'coupled'. Taken from 7.1 component CV. Omit when this component is embedded in another component.",
    )
    native_horizontal_grid: HorizontalGrid = Field(
        description="A standardised description of the model component's horizontal grid."
    )
    native_vertical_grid: NativeVerticalGrid = Field(
        description="A standardised description of the model component's vertical grid."
    )

    @field_validator("component", "name", "family", "code_base", mode="before")
    @classmethod
    def validate_non_empty_strings(cls, v):
        """Validate that string fields are not empty."""
        if isinstance(v, str):
            if not v.strip():
                raise ValueError("Field cannot be empty")
            return v.strip()
        return v

    @field_validator("coupled_with")
    @classmethod
    def validate_coupling_exclusivity(cls, v, info):
        """Validate that a component cannot be both embedded and coupled."""
        if v is not None and info.data.get("embedded_in") is not None:
            raise ValueError(
                "A component cannot be both embedded_in another component and coupled_with other components"
            )
        return v

    @field_validator("embedded_in")
    @classmethod
    def validate_embedding_exclusivity(cls, v, info):
        """Validate that a component cannot be both embedded and coupled."""
        if v is not None and info.data.get("coupled_with") is not None:
            raise ValueError(
                "A component cannot be both embedded_in another component and coupled_with other components"
            )
        return v

    @field_validator("code_base", mode="before")
    @classmethod
    def validate_code_base_format(cls, v):
        """Validate code_base is either 'private' or a URL."""
        if isinstance(v, str):
            v = v.strip()
            if v.lower() != "private" and not (v.startswith("http://") or v.startswith("https://")):
                raise ValueError('code_base must be either "private" or a valid URL starting with http:// or https://')
        return v


# ============================================================================
# TOP-LEVEL MODEL
# ============================================================================


class Model(PlainTermDataDescriptor):
    """
    Top-level model description (Section 2).

    The following properties provide a top-level description of the model as a whole.
    """

    name: str = Field(
        description="The name of the top-level model. For CMIP7, this name will be registered as the model's source_id.",
        min_length=1,
    )
    family: str = Field(
        description="The top-level model's 'family' name. Use 'none' to indicate that there is no such family.",
        min_length=1,
    )
    dynamic_components: List[str | ComponentType] = Field(
        description="The model components that are dynamically simulated within the top-level model. Taken from 7.1 component CV.",
        min_length=1,
    )
    prescribed_components: List[str | ComponentType] = Field(
        description="The components that are represented in the top-level model with prescribed values. Taken from 7.1 component CV.",
        default_factory=list,
    )
    omitted_components: List[str | ComponentType] = Field(
        description="The components that are wholly omitted from the top-level model. Taken from 7.1 component CV.",
        default_factory=list,
    )
    calendar: List[str | Calendar] = Field(
        description="The calendar, or calendars, that define which dates are permitted in the top-level model. Taken from 7.2 calendar CV.",
        min_length=1,
    )
    release_year: int = Field(
        description="The year in which the top-level model being documented was released, or first used for published simulations.",
        ge=1900,
        le=2100,
    )
    references: List[Reference] = Field(
        description="One or more references to published work for the top-level model as a whole.", min_length=1
    )
    model_components: Optional[List[EMDModelComponent]] = Field(
        default=None, description="The model components that dynamically simulate processes within the model."
    )

    @field_validator("name", "family", mode="before")
    @classmethod
    def validate_non_empty_strings(cls, v):
        """Validate that string fields are not empty."""
        if isinstance(v, str):
            if not v.strip():
                raise ValueError("Field cannot be empty")
            return v.strip()
        return v

    @field_validator("dynamic_components", "prescribed_components", "omitted_components", mode="before")
    @classmethod
    def validate_component_lists(cls, v):
        """Validate component lists contain valid strings or ComponentType objects."""
        if v is None:
            return []
        # Filter out empty strings, keep ComponentType objects
        cleaned = []
        for item in v:
            if isinstance(item, str):
                if item.strip():
                    cleaned.append(item.strip())
            else:
                cleaned.append(item)
        return cleaned

    @field_validator("calendar", mode="before")
    @classmethod
    def validate_calendar_list(cls, v):
        """Validate calendar list contains valid strings or Calendar objects."""
        if not v:
            raise ValueError("At least one calendar must be specified")
        # Filter out empty strings, keep Calendar objects
        cleaned = []
        for item in v:
            if isinstance(item, str):
                if item.strip():
                    cleaned.append(item.strip())
            else:
                cleaned.append(item)
        if not cleaned:
            raise ValueError("Calendar list cannot be empty")
        return cleaned

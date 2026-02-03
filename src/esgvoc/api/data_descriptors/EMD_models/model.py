"""
Top-level model description (EMD v1.0 Section 2).

The following properties provide a top-level description of the model as a whole.
"""

from __future__ import annotations

import warnings
from typing import List, Optional, Tuple

from pydantic import Field, field_validator, model_validator

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor

from .calendar import Calendar
from .component_type import ComponentType
from .model_component import EMDModelComponent
from .reference import Reference


class Model(PlainTermDataDescriptor):
    """
    Top-level model description (EMD v1.0 Section 2).

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
        description="The model components that are dynamically simulated within the top-level model. "
        "Taken from 7.1 component CV.",
        min_length=1,
    )

    prescribed_components: List[str | ComponentType] = Field(
        description="The components that are represented in the top-level model with prescribed values. "
        "Taken from 7.1 component CV.",
        default_factory=list,
    )

    omitted_components: List[str | ComponentType] = Field(
        description="The components that are wholly omitted from the top-level model. Taken from 7.1 component CV.",
        default_factory=list,
    )

    description: str = Field(
        description="A scientific overview of the top-level model. The description should include a brief mention "
        "of all the components listed in the 7.1 component CV, whether dynamically simulated, prescribed, or omitted.",
        min_length=1,
        default="",
    )

    calendar: List[str | Calendar] = Field(
        description="The calendar, or calendars, that define which dates are permitted in the top-level model. "
        "Taken from 7.2 calendar CV.",
        min_length=1,
    )

    release_year: int = Field(
        description="The year in which the top-level model being documented was released, "
        "or first used for published simulations.",
        ge=1900,
        le=2100,
    )

    references: List[str | Reference] = Field(
        description="One or more references to published work for the top-level model as a whole.", min_length=1
    )

    model_components: List[str | EMDModelComponent] = Field(
        description="The model components that dynamically simulate processes within the model."
    )

    embedded_components: List[Tuple[str | ComponentType, str | ComponentType]] = Field(
        description="Pairs of (embedded, host) dynamically simulated components"
    )
    coupled_components: List[Tuple[str | ComponentType, str | ComponentType]] = Field(
        description="Pairs of coupled dynamically simulated components"
    )

    @field_validator("model_components")
    @classmethod
    def validate_same_dynamic_components(cls, v, info):
        """Validate that model_components has the same length as dynamic_components."""
        if "dynamic_components" in info.data:
            dynamic_components = info.data["dynamic_components"]
            if len(v) != len(dynamic_components):
                raise ValueError(
                    f"Number of model_components ({len(v)}) must equal number of dynamic_components({len(dynamic_components)})"
                )
        return v

    @field_validator("name", "family", "description", mode="before")
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

    def _get_component_id(self, component) -> str:
        """Extract component identifier from string or ComponentType object."""
        if isinstance(component, str):
            return component
        return getattr(component, "id", str(component))

    @model_validator(mode="after")
    def validate_model_components_match_dynamic(self):
        """Validate each model_component.component matches a unique dynamic_component (warning mode)."""
        dynamic_ids = {self._get_component_id(c) for c in self.dynamic_components}
        seen_components = set()

        for mc in self.model_components:
            if isinstance(mc, str):
                continue  # Skip string references
            mc_component = self._get_component_id(mc.component)
            if mc_component not in dynamic_ids:
                warnings.warn(
                    f"EMD Conformance: Model component '{mc_component}' is not in dynamic_components: {dynamic_ids}",
                    UserWarning,
                    stacklevel=2,
                )
            if mc_component in seen_components:
                warnings.warn(
                    f"EMD Conformance: Model component '{mc_component}' appears multiple times - each must be unique",
                    UserWarning,
                    stacklevel=2,
                )
            seen_components.add(mc_component)
        return self

    @model_validator(mode="after")
    def validate_embedded_components(self):
        """Validate embedded_components pairs (EMD Conformance Section 2) (warning mode)."""
        if not self.embedded_components:
            return self

        dynamic_ids = {self._get_component_id(c) for c in self.dynamic_components}
        embedded_set = set()

        for embedded, host in self.embedded_components:
            embedded_id = self._get_component_id(embedded)
            host_id = self._get_component_id(host)

            # Components in each pair MUST be from dynamic_components
            if embedded_id not in dynamic_ids:
                warnings.warn(
                    f"EMD Conformance: Embedded component '{embedded_id}' is not in dynamic_components",
                    UserWarning,
                    stacklevel=2,
                )
            if host_id not in dynamic_ids:
                warnings.warn(
                    f"EMD Conformance: Host component '{host_id}' is not in dynamic_components",
                    UserWarning,
                    stacklevel=2,
                )

            # Components in each pair MUST be different
            if embedded_id == host_id:
                warnings.warn(
                    f"EMD Conformance: Embedded and host components must be different, got '{embedded_id}' for both",
                    UserWarning,
                    stacklevel=2,
                )

            # Each embedded component MUST only be embedded in one host
            if embedded_id in embedded_set:
                warnings.warn(
                    f"EMD Conformance: Component '{embedded_id}' is embedded in multiple hosts - each can only be embedded once",
                    UserWarning,
                    stacklevel=2,
                )
            embedded_set.add(embedded_id)

        return self

    @model_validator(mode="after")
    def validate_coupled_components(self):
        """Validate coupled_components pairs (EMD Conformance Section 2) (warning mode)."""
        if not self.coupled_components:
            return self

        dynamic_ids = {self._get_component_id(c) for c in self.dynamic_components}

        for comp1, comp2 in self.coupled_components:
            comp1_id = self._get_component_id(comp1)
            comp2_id = self._get_component_id(comp2)

            # Components in each pair MUST be from dynamic_components
            if comp1_id not in dynamic_ids:
                warnings.warn(
                    f"EMD Conformance: Coupled component '{comp1_id}' is not in dynamic_components",
                    UserWarning,
                    stacklevel=2,
                )
            if comp2_id not in dynamic_ids:
                warnings.warn(
                    f"EMD Conformance: Coupled component '{comp2_id}' is not in dynamic_components",
                    UserWarning,
                    stacklevel=2,
                )

            # Components in each pair MUST be different
            if comp1_id == comp2_id:
                warnings.warn(
                    f"EMD Conformance: Coupled components in a pair must be different, got '{comp1_id}' for both",
                    UserWarning,
                    stacklevel=2,
                )

        # When there are two or more pairs, each pair must share at least one component with another pair
        if len(self.coupled_components) >= 2:
            pairs_as_sets = [
                {self._get_component_id(c1), self._get_component_id(c2)} for c1, c2 in self.coupled_components
            ]
            for i, pair in enumerate(pairs_as_sets):
                shares_component = False
                for j, other_pair in enumerate(pairs_as_sets):
                    if i != j and pair & other_pair:
                        shares_component = True
                        break
                if not shares_component:
                    warnings.warn(
                        f"EMD Conformance: Coupled pair {pair} does not share any component with other pairs",
                        UserWarning,
                        stacklevel=2,
                    )

        return self

    @model_validator(mode="after")
    def validate_embedded_coupled_exclusivity(self):
        """Validate every component is embedded XOR coupled, not both (EMD Conformance Section 2) (warning mode)."""
        dynamic_ids = {self._get_component_id(c) for c in self.dynamic_components}

        # Collect embedded components
        embedded_ids = set()
        for embedded, _ in self.embedded_components:
            embedded_ids.add(self._get_component_id(embedded))

        # Collect coupled components
        coupled_ids = set()
        for comp1, comp2 in self.coupled_components:
            coupled_ids.add(self._get_component_id(comp1))
            coupled_ids.add(self._get_component_id(comp2))

        # An embedded component MUST NOT be a coupled component
        overlap = embedded_ids & coupled_ids
        if overlap:
            warnings.warn(
                f"EMD Conformance: Components cannot be both embedded and coupled: {overlap}",
                UserWarning,
                stacklevel=2,
            )

        # All non-embedded components MUST be coupled components
        non_embedded = dynamic_ids - embedded_ids
        non_coupled_non_embedded = non_embedded - coupled_ids
        if non_coupled_non_embedded:
            warnings.warn(
                f"EMD Conformance: All non-embedded dynamic components must be coupled: {non_coupled_non_embedded} are neither embedded nor coupled",
                UserWarning,
                stacklevel=2,
            )

        return self

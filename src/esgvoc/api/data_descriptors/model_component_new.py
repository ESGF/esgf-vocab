from typing import Optional, List
from pydantic import Field, field_validator
from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor
from esgvoc.api.data_descriptors.reference_new import Reference
from esgvoc.api.data_descriptors.native_horizontal_grid_new import NativeHorizontalGrid
from esgvoc.api.data_descriptors.native_vertical_grid_new import NativeVerticalGrid


class EMDModelComponent(PlainTermDataDescriptor):
    """
    Properties that provide a description of individual model components.
    Eight model components are defined that somewhat independently account for different sets of interactive processes: aerosol, atmosphere, atmospheric chemistry, land surface, land ice, ocean, ocean biogeochemistry, and sea ice. The interactive processes covered by each  component are described in more detail in section 7.1. Model Component Type CV.
    Each component is characterized as “dynamic”, “prescribed”, or “omitted” (see 2. Model properties), but only model components that dynamically simulate their processes are described in this section of the EMD. Relationships among dynamically simulated components are indicated by specifying that they are “embedded in” or “coupled with” other components (see 3.1. Embedded and Coupled components).
    Note for CMIP7: The component types in the 7.1. Model Component Type CV have similar names and definitions to the CMIP “realms” given by the CMIP6_realm.json file (Durack et al., 2025), but the context in which they are used is different. An EMD component type defines a set of physical process that are simulated by one model component; whereas as one or more CMIP realms are assigned to an individual model output variable according to which sets of processes the variable is physically related to, rather than which model component created it. The CMIP realms for an output variable often include the EMD component type that created it, but this is not always the case.
    In the property examples, underlined and italicised values are taken from section 7. Controlled vocabularies.
    • Component
        ◦ The type of the model component.
        ◦ Taken from a standardised list: 7.1. Model Component Type CV.
        ◦ E.g. aerosol
    • Name
        ◦ The name of the model component.
        ◦ If the component is embedded in a host component and has no commonly recognised name, then a name can be constructed by combining the host component’s Name with this component’s Component type, separated by a hyphen.
        ◦ E.g. BISICLES-UKESM-ISMIP6
        ◦ E.g. MOSES2
        ◦ E.g. HadAM3-aerosol
    • Family
        ◦ The model component’s “family” name. For a component, its family members should all share much of their code bases, but the members may be configured in different ways (e.g. different resolutions, parameter choices, or the inclusion or not of particular sub-process). See Masson and Knutti (2011) for an example of how the family can be used to inform model genealogies.
        ◦ Use a value of “none” to indicate that there is no such family for the model component.
        ◦ E.g. BISICLES
        ◦ E.g. CLM
        ◦ E.g. none
    • Description
        ◦ A scientific overview of the model component.
        ◦ The description should summarise the key processes simulated by the model component.
        ◦ For CMIP7, easy-to-answer MIP-relevant questions may be posed, which should be addressed using free text. For instance “Are aerosols driven by emissions or concentration?” or “What is the aerosol activation scheme?”.
    • References
        ◦ References to published work for the model component.
        ◦ Each reference must include the properties described in section 4. References.
    • Code base
        ◦ A URL (preferably for a DOI) for the source code for the model component.
        ◦ If the source code is in a versioncontrolled repository (e.g. a git or svn repository) then the URL must identify a specific point in the repository’s history.
        ◦ Set to “private” if not publicly available.
    • Embedded in
        ◦ The host model component (identified by its Component property) in which this component is “embedded”.
        ◦ See section 3.1. Embedded and Coupled model components for a definition of an embedded component. Note that a component must be either embedded in a another component or else coupled with other components, but can not be both.
        ◦ Taken from a standardised list: 7.1. Model Component Type CV.
        ◦ Omit when this component is coupled with other components (see the Coupled with property).
        ◦ E.g. in some cases, for an aerosol model component: atmosphere
    • Coupled with
        ◦ The model components (identified by their Component properties) with which this component is “coupled”.
        ◦ See section 3.1. Embedded and Coupled model components for a definition of a coupled component. Note that a component must be either embedded in a another component or else coupled with other components, but can not be both.
        ◦ Taken from a standardised list: 7.1. Model Components Type CV.
        ◦ Omit when this component is embedded in another component (see the Embedded in property).
        ◦ E.g. In some cases for a land ice component: atmosphere, land surface, ocean
    • Native horizontal grid
        ◦ A standardised description of the model component’s horizontal grid.
        ◦ The grid is described by defining the properties listed in section 5.1. Native horizontal grid properties.
    • Native vertical grid
        ◦ A standardised description of the model component’s vertical grid.
        ◦ The grid is described by defining the properties listed in section 5.2. Native vertical grid properties.
    """

    component: str = Field(
        description="The type of the model component. Taken from a standardised list: 7.1 component CV."
    )
    name: str = Field(
        description="The name of the model component.", min_length=1)
    family: str = Field(
        description="The model component's 'family' name. Use 'none' to indicate that there is no such family.",
        min_length=1,
    )
    description: str = Field(
        description="A scientific overview of the model component. The description should summarise the key processes simulated by the model component.",
        min_length=1,
    )
    references: List[Reference] = Field(
        description="One or more references to published work for the model component.", min_length=1
    )
    code_base: str = Field(
        description="A URL (preferably for a DOI) for the source code for the model component. Set to 'private' if not publicly available.",
        min_length=1,
    )
    embedded_in: Optional[str] = Field(
        default=None,
        description="The host model component (identified by its component property) in which this component is 'embedded'. Taken from a standardised list: 7.1 component CV. Omit when this component is coupled with other components.",
    )
    coupled_with: Optional[List[str]] = Field(
        default=None,
        description="The model components (identified by their component properties) with which this component is 'coupled'. Taken from a standardised list: 7.1 component CV. Omit when this component is embedded in another component.",
    )
    native_horizontal_grid: NativeHorizontalGrid = Field(
        description="A standardised description of the model component's horizontal grid."
    )
    native_vertical_grid: NativeVerticalGrid = Field(
        description="A standardised description of the model component's vertical grid."
    )

    @field_validator("component", "name", "family", "description", "code_base")
    @classmethod
    def validate_non_empty_strings(cls, v):
        """Validate that string fields are not empty."""
        if not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()

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

    @field_validator("code_base")
    @classmethod
    def validate_code_base_format(cls, v):
        """Validate code_base is either 'private' or a URL."""
        v = v.strip()
        if v.lower() != "private" and not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError(
                'code_base must be either "private" or a valid URL starting with http:// or https://')
        return v

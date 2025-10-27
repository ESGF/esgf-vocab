"""
Support for generating CMOR CVs tables

Note: this really shouldn't be in esgvoc.
It should be in CMOR, as CMOR knows the structure it needs,
not esgvoc. Anyway, can do that later.
"""

from functools import partial
from typing import Any, TypeAlias

from pydantic import BaseModel, ConfigDict, HttpUrl

import esgvoc.api as ev_api

AllowedDict: TypeAlias = dict[str, Any]
"""
Dictionary (key-value pairs). The keys define the allowed values for the given attribute

The values can be anything,
they generally provide extra information about the meaning of the keys.
"""

RegularExpressionValidators: TypeAlias = list[str]
"""
List of values which are assumed to be regular expressions

Attribute values provided by teams are then validated
against these regular expressions.
"""


class CMORExperimentDefinition(BaseModel):
    """
    CMOR experiment definition
    """

    activity_id: str
    """
    Activity ID to which this experiment belongs
    """

    required_model_components: RegularExpressionValidators
    """
    Required model components to run this experiment
    """

    additional_allowed_model_components: RegularExpressionValidators
    """
    Additional model components that can be included when running this experiment
    """

    description: str
    """
    Experiment description
    """

    experiment: str
    """
    Experiment description (same as description)
    """

    # TODO: check if we should switch to timestamps
    start_year: int | None
    """Start year of the experiment"""

    end_year: int | None
    """End year of the experiment"""

    min_number_yrs_per_sim: int | None
    """Minimum number of years of simulation required"""

    experiment_id: str
    """
    Experiment ID
    """

    # # Not a thing anymore, hence remove
    # host_collection: str
    # """
    # Host collection of this experiment
    # """

    parent_activity_id: str | None
    """Activity ID for the parent of this experiment"""

    parent_experiment_id: str | None
    """Experiment ID for the parent of this experiment"""

    tier: int
    """
    Tier i.e. priority of this experiment

    Lower is higher priority i.e. 1 is the highest priority
    """


class CMORFrequencyDefinition(BaseModel):
    """
    CMOR frequency definition
    """

    approx_interval: float
    """
    Approximate interval in days
    """

    description: str
    """
    Description
    """


class CMORSpecificLicenseDefinition(BaseModel):
    """
    CMOR-style specific license definition
    """

    license_type: str
    """
    Type of the license
    """

    license_url: HttpUrl
    """
    URL that describes the license
    """


class CMORLicenseDefinition(BaseModel):
    """
    CMOR license definition
    """

    license_id: dict[str, CMORSpecificLicenseDefinition]
    """
    Supported licenses
    """

    # (rightfully) not in esgvoc
    license_template: str
    """
    Template for writing license strings
    """


class CMORCVsTable(BaseModel):
    """
    Representation of the JSON table required by CMOR for CVs
    CMOR also takes in variable tables,
    as well as a user input table.
    This model doesn't consider those tables
    or their interactions with this table at the moment.
    """

    model_config = ConfigDict(extra="forbid")

    # Note; not a required global attribute hence dropped
    # archive_id: AllowedDict
    # """
    # Allowed values of `archive_id`
    # """

    activity_id: AllowedDict
    """
    Allowed values of `activity_id`
    """

    area_label: AllowedDict
    """
    Allowed values of `area_label`
    """

    branding_suffix: str
    """
    Template for branding suffix
    """

    branded_variable: str
    """
    Template for branded variable
    """

    creation_date: RegularExpressionValidators
    """
    Allowed patterns for `creation_date`
    """

    data_specs_version: str
    """
    Allowed value of `data_specs_version`
    """

    drs_specs: AllowedDict
    """
    Allowed values of `drs_specs`
    """

    experiment_id: dict[str, CMORExperimentDefinition]
    """
    CMOR-style experiment definitions
    """

    forcing_index: RegularExpressionValidators
    """
    Allowed patterns for `forcing_index`
    """

    frequency: AllowedDict
    """
    Allowed values of `frequency`
    """

    grid_label: AllowedDict
    """
    Allowed values of `grid_label`
    """

    horizontal_label: AllowedDict
    """
    Allowed values of `horizontal_label`
    """

    initialization_index: RegularExpressionValidators
    """
    Allowed patterns for `initialization_index`
    """

    institution_id: AllowedDict
    """
    Allowed values of `institution_id`
    """

    license: CMORLicenseDefinition
    """
    CMOR-style license definition
    """

    mip_era: str
    """
    Allowed value of `mip_era`
    """

    nominal_resolution: AllowedDict
    """
    Allowed values of `nominal_resolution`
    """

    physics_index: RegularExpressionValidators
    """
    Allowed patterns for `physics_index`
    """

    product: AllowedDict
    """
    Allowed values of `product`
    """

    realization_index: RegularExpressionValidators
    """
    Allowed patterns for `realization_index`
    """

    realm: AllowedDict
    """
    Allowed values of `realm`
    """

    region: AllowedDict
    """
    Allowed values of `region`
    """

    required_global_attributes: list[str]
    """
    Required global attributes
    """

    temporal_label: AllowedDict
    """
    Allowed values of `temporal_label`
    """

    tracking_id: RegularExpressionValidators
    """
    Allowed patterns for `tracking_id`
    """

    variable_id: AllowedDict
    """
    Allowed values of `variable_id`
    """

    variant_label: RegularExpressionValidators
    """
    Allowed patterns for `variant_label`
    """

    vertical_label: AllowedDict
    """
    Allowed values of `vertical_label`
    """

    def to_cvs_json(
        self, top_level_key: str = "CV"
    ) -> dict[str, dict[str, str, AllowedDict, RegularExpressionValidators]]:
        md = self.model_dump(mode="json")

        # # Unclear why this is done for some keys and not others,
        # # which makes reasoning hard.
        # to_hyphenise = list(md["drs"].keys())
        # for k in to_hyphenise:
        #     md["drs"][k.replace("_", "-")] = md["drs"].pop(k)
        #
        # md["experiment_id"] = {k: v.to_json() for k, v in self.experiment_id.experiments.items()}
        # # More fun
        # md["DRS"] = md.pop("drs")

        cvs_json = {top_level_key: md}

        return cvs_json


def get_project_attribute_property(
    attribute_value: str, attribute_to_match: str, ev_project: ev_api.project_specs.ProjectSpecs
) -> ev_api.project_specs.AttributeProperty:
    for ev_attribute_property in ev_project.attr_specs:
        if getattr(ev_attribute_property, attribute_to_match) == attribute_value:
            break

    else:
        msg = f"Nothing in attr_specs had {attribute_to_match} equal to {attribute_value}"
        raise KeyError(msg)

    return ev_attribute_property


def get_allowed_dict_for_attribute(attribute_name: str, ev_project: ev_api.project_specs.ProjectSpecs) -> AllowedDict:
    ev_attribute_property = get_project_attribute_property(
        attribute_value=attribute_name,
        attribute_to_match="field_name",
        ev_project=ev_project,
    )

    attribute_instances = ev_api.get_all_terms_in_collection(
        ev_project.project_id, ev_attribute_property.source_collection
    )

    res = {v.drs_name: v.description for v in attribute_instances}

    return res


def get_regular_expression_validator_for_attribute(
    attribute_property: ev_api.project_specs.AttributeProperty,
    ev_project: ev_api.project_specs.ProjectSpecs,
) -> RegularExpressionValidators:
    attribute_instances = ev_api.get_all_terms_in_collection(
        ev_project.project_id, attribute_property.source_collection
    )
    res = [v.regex for v in attribute_instances]

    return res


def get_template_for_composite_attribute(attribute_name: str, ev_project: ev_api.project_specs.ProjectSpecs) -> str:
    ev_attribute_property = get_project_attribute_property(
        attribute_value=attribute_name,
        attribute_to_match="field_name",
        ev_project=ev_project,
    )
    terms = ev_api.get_all_terms_in_collection(ev_project.project_id, ev_attribute_property.source_collection)
    if len(terms) > 1:
        raise AssertionError(terms)

    term = terms[0]

    parts_l = []
    for v in term.parts:
        va = get_project_attribute_property(v.type, "source_collection", ev_project)
        parts_l.append(f"<{va.field_name}>")

    res = term.separator.join(parts_l)

    return res


def get_single_allowed_value_for_attribute(attribute_name: str, ev_project: ev_api.project_specs.ProjectSpecs) -> str:
    ev_attribute_property = get_project_attribute_property(
        attribute_value=attribute_name,
        attribute_to_match="field_name",
        ev_project=ev_project,
    )
    terms = ev_api.get_all_terms_in_collection(ev_project.project_id, ev_attribute_property.source_collection)
    if len(terms) > 1:
        raise AssertionError(terms)

    term = terms[0]

    res = term.drs_name

    return res


def get_cmor_license_definition(
    source_collection: str, ev_project: ev_api.project_specs.ProjectSpecs
) -> CMORLicenseDefinition:
    terms = ev_api.get_all_terms_in_collection(ev_project.project_id, source_collection)

    license_ids_d = {
        v.drs_name: CMORSpecificLicenseDefinition(
            license_type=v.description,
            license_url=v.url,
        )
        for v in terms
    }

    res = CMORLicenseDefinition(
        license_id=license_ids_d,
        license_template=(
            "<license_id>; CMIP7 data produced by <institution_id> "
            "is licensed under a <license_type> License (<license_url>). "
            "Consult [TODO terms of use link] for terms of use governing CMIP7 output, "
            "including citation requirements and proper acknowledgment. "
            "The data producers and data providers make no warranty, "
            "either express or implied, including, but not limited to, "
            "warranties of merchantability and fitness for a particular purpose. "
            "All liabilities arising from the supply of the information "
            "(including any liability arising in negligence) "
            "are excluded to the fullest extent permitted by law."
        ),
    )

    return res


def get_approx_interval(interval: float, units: str) -> float:
    try:
        import pint

        ur = pint.get_application_registry()
    except ImportError as exc:
        msg = "Missing optional dependency `pint`, please install"
        raise ImportError(msg) from exc

    if units == "month":
        # Special case, month is 30 days
        res = interval * 30.0
    else:
        res = ur.Quantity(interval, units).to("day").m

    return res


def get_cmor_experiment_id_definitions(
    source_collection: str, ev_project: ev_api.project_specs.ProjectSpecs
) -> dict[str, CMORExperimentDefinition]:
    terms = ev_api.get_all_terms_in_collection(ev_project.project_id, source_collection)

    get_term = partial(ev_api.get_term_in_project, ev_project.project_id)
    res = {}
    for v in terms:
        res[v.drs_name] = CMORExperimentDefinition(
            activity_id=get_term(v.activity).drs_name,
            required_model_components=[get_term(vv).drs_name for vv in v.required_model_components],
            additional_allowed_model_components=[get_term(vv).drs_name for vv in v.additional_allowed_model_components],
            description=v.description,
            experiment=v.description,
            start_year=v.start_timestamp.year if v.start_timestamp else v.start_timestamp,
            end_year=v.end_timestamp.year if v.end_timestamp else v.end_timestamp,
            min_number_yrs_per_sim=v.min_number_yrs_per_sim,
            experiment_id=v.drs_name,
            parent_activity_id=v.parent_activity.drs_name if v.parent_activity else v.parent_activity,
            parent_experiment_id=v.parent_experiment.drs_name if v.parent_experiment else v.parent_experiment,
            tier=v.tier,
        )

    return res


def get_cmor_frequency_definitions(
    source_collection: str, ev_project: ev_api.project_specs.ProjectSpecs
) -> dict[str, CMORFrequencyDefinition]:
    terms = ev_api.get_all_terms_in_collection(ev_project.project_id, source_collection)

    res = {
        v.drs_name: CMORFrequencyDefinition(
            description=v.description,
            approx_interval=get_approx_interval(v.interval, units=v.units),
        )
        if v.interval
        # I'm still not convinced that it wouldn't be simpler to use the same schema for all types
        else "fixed (time invariant) field"
        for v in terms
    }

    return res


def generate_cvs_table(project: str) -> CMORCVsTable:
    ev_project = ev_api.projects.get_project(project)

    init_kwargs = {"required_global_attributes": []}
    for attr_property in ev_project.attr_specs:
        if attr_property.is_required:
            init_kwargs["required_global_attributes"].append(attr_property.field_name)

        print((attr_property.source_collection, attr_property.field_name))
        # Logic: https://github.com/WCRP-CMIP/CMIP7-CVs/issues/271#issuecomment-3286291815
        if attr_property.field_name in [
            "Conventions",
        ]:
            # Not handled in CMOR tables
            continue

        elif attr_property.field_name in [
            "data_specs_version",
            "mip_era",
        ]:
            # Special single value entries
            value = get_single_allowed_value_for_attribute(attr_property.field_name, ev_project)
            kwarg = attr_property.field_name

        elif attr_property.field_name == "license_id":
            value = get_cmor_license_definition(attr_property.source_collection, ev_project)
            kwarg = "license"

        elif attr_property.field_name == "frequency":
            value = get_cmor_frequency_definitions(attr_property.source_collection, ev_project)
            kwarg = attr_property.field_name

        elif attr_property.field_name == "experiment_id":
            value = get_cmor_experiment_id_definitions(attr_property.source_collection, ev_project)
            kwarg = attr_property.field_name

        elif attr_property.field_name == "source_id":
            continue
            raise NotImplementedError
            # value = get_cmor_license_definition(attr_property.source_collection, ev_project)
            # kwarg = attr_property.field_name

        else:
            kwarg = attr_property.field_name
            pydantic_class = ev_api.pydantic_handler.get_pydantic_class(attr_property.source_collection)
            if issubclass(pydantic_class, ev_api.data_descriptors.data_descriptor.PlainTermDataDescriptor):
                value = get_allowed_dict_for_attribute(attr_property.field_name, ev_project)

            elif issubclass(pydantic_class, ev_api.data_descriptors.data_descriptor.PatternTermDataDescriptor):
                value = get_regular_expression_validator_for_attribute(attr_property, ev_project)

            elif issubclass(pydantic_class, ev_api.data_descriptors.data_descriptor.CompositeTermDataDescriptor):
                value = get_template_for_composite_attribute(attr_property.field_name, ev_project)

            else:
                raise NotImplementedError(pydantic_class)

        init_kwargs[kwarg] = value

    # TODO: add DRS
    cmor_cvs_table = CMORCVsTable(**init_kwargs)

    return cmor_cvs_table

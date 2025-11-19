"""
Support for generating CMOR CVs tables

Note: this really shouldn't be in esgvoc.
It should be in CMOR, as CMOR knows the structure it needs,
not esgvoc. Anyway, can do that later.
"""

import re
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


class CMORDRSDefinition(BaseModel):
    """
    CMOR data reference syntax (DRS) definition
    """

    directory_path_example: str
    """
    Example of a directory path that follows this DRS
    """

    directory_path_template: str
    """
    Template to use for generating directory paths
    """

    filename_path_example: str
    """
    Example of a filename path that follows this DRS
    """

    filename_path_template: str
    """
    Template to use for generating filename paths
    """


class CMORExperimentDefinition(BaseModel):
    """
    CMOR experiment definition
    """

    activity_id: list[str]
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

    parent_activity_id: list[str]
    """Activity ID for the parent of this experiment"""

    parent_experiment_id: list[str]
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


class CMORModelComponentDefintion(BaseModel):
    """
    CMOR model component definition
    """

    description: str
    """Description"""

    native_nominal_resolution: str
    """Native nominal resolution of this component"""


class CMORSourceDefinition(BaseModel):
    """
    CMOR source definition

    The meaning of 'source' is a bit fuzzy across projects,
    but for CMIP phases it refers to the model which provided the simulation.
    """

    # # Don't think this is used or relevant hence drop
    # activity_participation: RegularExpressionValidators
    # """
    # Activities in which this source has participated
    # """

    # # Don't know what this is hence drop
    # cohort: RegularExpressionValidators
    # """
    # Cohort to which this source belongs
    #
    # TODO: clarify what this means
    # """

    institution_id: RegularExpressionValidators
    """
    Institution ID for this source
    """

    label: str
    """
    Label to use for this source ID

    TODO: check, does this mean in graphs/plots?
    """

    label_extended: str
    """
    Extended label to use for this source ID

    TODO: check, does this mean in graphs/plots?
    """

    model_component: dict[str, CMORModelComponentDefintion]
    """
    Model components of this source
    """

    # # Not relevant hence drop
    # release_year: int | None
    # """
    # Release year of the model/source
    #
    # `None` if the release concept does not apply to this source
    # """

    source: str
    """
    Source information

    Combination of source name and information about each model component
    """

    source_id: str
    """
    Source ID for `self`
    """


def convert_none_value_to_empty_string(v: Any) -> Any:
    return v if v is not None else ""


def remove_none_values_from_dict(inv: dict[str, Any]) -> dict[str, Any]:
    res = {}
    for k, v in inv.items():
        if isinstance(v, list):
            res[k] = [convert_none_value_to_empty_string(vv) for vv in v]

        elif isinstance(v, dict):
            res[k] = remove_none_values_from_dict(v)

        else:
            res[k] = convert_none_value_to_empty_string(v)

    return res


class CMORCVsTable(BaseModel):
    """
    Representation of the JSON table required by CMOR for CVs
    CMOR also takes in variable tables,
    as well as a user input table.
    This model doesn't consider those tables
    or their interactions with this table at the moment.
    """

    model_config = ConfigDict(extra="forbid")

    DRS: CMORDRSDefinition
    """
    CMOR definition of the data reference syntax
    """

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

    source_id: dict[str, CMORSourceDefinition]
    """
    CMOR-style source definitions
    """

    temporal_label: AllowedDict
    """
    Allowed values of `temporal_label`
    """

    tracking_id: RegularExpressionValidators
    """
    Allowed patterns for `tracking_id`
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

        md_no_none = remove_none_values_from_dict(md)

        cvs_json = {top_level_key: md_no_none}

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


def convert_python_regex_to_cmor_regex(inv: str) -> str:
    # Not ideal that we have to do this ourselves,
    # but I can't see another way
    # (it doesn't make sense to use posix regex in the CV JSON
    # because then esgvoc's Python API won't work)

    # Get rid of Python style capturing groups.
    # Super brittle, might break if there are brackets inside the caught expression.
    # We'll have to fix as we find problems, regex is annoyingly complicated.
    res = re.sub(r"\(\?P\<[^>]*\>([^)]*)\)", r"\1", inv)

    # Other things we seem to have to change
    res = res.replace("{", r"\{")
    res = res.replace("}", r"\}")
    res = res.replace("(", r"\(")
    res = res.replace(")", r"\)")
    res = res.replace(r"\d", "[[:digit:]]")
    res = res.replace("+", r"\{1,\}")
    res = res.replace("?", r"\{0,\}")

    return res


def get_regular_expression_validator_for_attribute(
    attribute_property: ev_api.project_specs.AttributeProperty,
    ev_project: ev_api.project_specs.ProjectSpecs,
) -> RegularExpressionValidators:
    attribute_instances = ev_api.get_all_terms_in_collection(
        ev_project.project_id, attribute_property.source_collection
    )
    res = [convert_python_regex_to_cmor_regex(v.regex) for v in attribute_instances]

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

    if term.separator != "-":
        msg = f"CMOR only supports '-' as a separator, received {term.separator=} for {term=}"
        raise NotImplementedError(msg)

    res = "".join(parts_l)

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
            activity_id=[get_term(v.activity).drs_name],
            required_model_components=[vv.drs_name for vv in v.required_model_components],
            additional_allowed_model_components=[vv.drs_name for vv in v.additional_allowed_model_components],
            description=v.description,
            experiment=v.description,
            start_year=v.start_timestamp.year if v.start_timestamp else v.start_timestamp,
            end_year=v.end_timestamp.year if v.end_timestamp else v.end_timestamp,
            min_number_yrs_per_sim=v.min_number_yrs_per_sim,
            experiment_id=v.drs_name,
            parent_activity_id=[v.parent_activity.drs_name] if v.parent_activity else [],
            parent_experiment_id=[v.parent_experiment.drs_name] if v.parent_experiment else [],
            tier=v.tier,
        )

    return res


def get_cmor_source_id_definitions(
    source_collection: str, ev_project: ev_api.project_specs.ProjectSpecs
) -> dict[str, CMORSourceDefinition]:
    terms = ev_api.get_all_terms_in_collection(ev_project.project_id, source_collection)

    get_term = partial(ev_api.get_term_in_project, ev_project.project_id)
    res = {}
    for v in terms:
        model_components = {}
        for mc in v.model_components:
            raise NotImplementedError(mc)

        source = "\n".join([f"{v.drs_name}:", *[f"{key}: {v.description}" for key, v in model_components.items()]])
        res[v.drs_name] = CMORSourceDefinition(
            institution_id=[get_term(vv).drs_name for vv in v.contributors],
            label=v.label,
            label_extended=v.label_extended,
            model_component=model_components,
            source=source,
            source_id=v.drs_name,
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


def get_cmor_drs_definition(ev_project: ev_api.project_specs.ProjectSpecs) -> CMORDRSDefinition:
    # Creating a valid example is quite hard because of the coupling between elements.
    # Try and anticipate those here.
    # Note that a perfect way to do this is beyond me right now.
    # grid region
    activity_example = ev_api.get_term_in_collection(ev_project.project_id, "activity", "cmip")
    experiment_example = ev_api.get_term_in_collection(
        ev_project.project_id, "experiment", activity_example.experiments[0]
    )

    institution_example = ev_api.get_all_terms_in_collection(ev_project.project_id, "organisation")[0]
    sources = ev_api.get_all_terms_in_collection(ev_project.project_id, "source")
    for source in sources:
        if institution_example.id in source.contributors:
            source_example = source
            break
    else:
        msg = f"No example source found for {institution_example.id}"
        raise AssertionError(msg)

    grid_example = ev_api.get_all_terms_in_collection(ev_project.project_id, "grid")[0]
    region_example = ev_api.get_term_in_collection(ev_project.project_id, "region", grid_example.region)

    frequency_example = "mon"
    time_range_example = "185001-202112"

    # Creating example regexp terms on the fly also doesn't work
    variant_label_example = "r1i1p1f1"
    branded_suffix_example = "tavg-h2m-hxy-u"

    directory_path_template_l = []
    directory_path_example_l = []
    for part in ev_project.drs_specs["directory"].parts:
        if not part.is_required:
            raise NotImplementedError

        if part.source_collection == "directory_date":
            # Maybe should be using catalogue specs rather than attr specs?
            # Hard-coded CMOR weirdness
            directory_path_template_l.append("<version>")
            directory_path_example_l.append("20251104")

            continue

        project_attribute_property = get_project_attribute_property(
            attribute_value=part.source_collection, attribute_to_match="source_collection", ev_project=ev_project
        )
        directory_path_template_l.append(f"<{project_attribute_property.field_name}>")

        if part.source_collection == "activity":
            directory_path_example_l.append(activity_example.drs_name)
        elif part.source_collection == "experiment":
            directory_path_example_l.append(experiment_example.drs_name)
        elif part.source_collection == "frequency":
            directory_path_example_l.append(frequency_example)
        elif part.source_collection == "institution":
            directory_path_example_l.append(institution_example.drs_name)
        elif part.source_collection == "source":
            directory_path_example_l.append(source_example.drs_name)
        elif part.source_collection == "grid":
            directory_path_example_l.append(grid_example.drs_name)
        elif part.source_collection == "region":
            directory_path_example_l.append(region_example.drs_name)
        elif part.source_collection == "variant_label":
            # Urgh
            directory_path_example_l.append(variant_label_example)
        elif part.source_collection == "branded_suffix":
            # Urgh
            directory_path_example_l.append(branded_suffix_example)
        else:
            example_drs_name = ev_api.get_all_terms_in_collection(ev_project.project_id, part.source_collection)[
                0
            ].drs_name
            directory_path_example_l.append(example_drs_name)

    directory_path_template = ev_project.drs_specs["directory"].separator.join(directory_path_template_l)
    directory_path_example = ev_project.drs_specs["directory"].separator.join(directory_path_example_l)

    filename_path_template_l = []
    filename_path_example_l = []
    for i, part in enumerate(ev_project.drs_specs["file_name"].parts):
        if i > 0:
            prefix = ev_project.drs_specs["file_name"].separator
        else:
            prefix = ""

        if part.source_collection == "time_range":
            # Maybe should be using catalogue specs rather than attr specs?
            # Hard-coded CMOR weirdness
            cmor_placeholder = "timeRange"
            example_value = time_range_example

        else:
            project_attribute_property = get_project_attribute_property(
                attribute_value=part.source_collection, attribute_to_match="source_collection", ev_project=ev_project
            )
            cmor_placeholder = project_attribute_property.field_name

            if part.source_collection == "experiment":
                example_value = experiment_example.drs_name
            elif part.source_collection == "frequency":
                example_value = frequency_example
            elif part.source_collection == "source":
                example_value = source_example.drs_name
            elif part.source_collection == "grid":
                example_value = grid_example.drs_name
            elif part.source_collection == "region":
                example_value = region_example.drs_name
            elif part.source_collection == "variant_label":
                # Urgh
                example_value = variant_label_example
            elif part.source_collection == "branded_suffix":
                # Urgh
                example_value = branded_suffix_example
            else:
                example_value = ev_api.get_all_terms_in_collection(ev_project.project_id, part.source_collection)[
                    0
                ].drs_name

        if part.is_required:
            filename_path_template_l.append(f"{prefix}<{cmor_placeholder}>")
        else:
            filename_path_template_l.append(f"[{prefix}<{cmor_placeholder}>]")

        filename_path_example_l.append(f"{prefix}{example_value}")

    filename_path_template_excl_ext = "".join(filename_path_template_l)
    filename_path_template = f"{filename_path_template_excl_ext}.nc"
    filename_path_example_excl_ext = "".join(filename_path_example_l)
    filename_path_example = f"{filename_path_example_excl_ext}.nc"

    res = CMORDRSDefinition(
        directory_path_example=directory_path_example,
        directory_path_template=directory_path_template,
        filename_path_example=filename_path_example,
        filename_path_template=filename_path_template,
    )

    return res


def generate_cvs_table(project: str) -> CMORCVsTable:
    ev_project = ev_api.projects.get_project(project)

    init_kwargs = {"required_global_attributes": []}
    for attr_property in ev_project.attr_specs:
        if attr_property.is_required:
            init_kwargs["required_global_attributes"].append(attr_property.field_name)

        # Logic: https://github.com/WCRP-CMIP/CMIP7-CVs/issues/271#issuecomment-3286291815
        if attr_property.field_name in [
            "Conventions",
            "branded_variable",
            "variable_id",
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
            value = get_cmor_source_id_definitions(attr_property.source_collection, ev_project)
            kwarg = attr_property.field_name

        elif attr_property.field_name in ("activity_id",):
            # Hard-code for now
            # TODO: figure out how to unpack typing.Annotated
            kwarg = attr_property.field_name
            value = get_allowed_dict_for_attribute(attr_property.field_name, ev_project)

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

    init_kwargs["DRS"] = get_cmor_drs_definition(ev_project)

    cmor_cvs_table = CMORCVsTable(**init_kwargs)

    return cmor_cvs_table

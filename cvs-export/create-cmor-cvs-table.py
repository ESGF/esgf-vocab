"""
Prototype for creating a CMOR CVs table from esgvoc

Suggestions:

1. this is translated into an esgvoc app
1. the CMORCVs model/schema and related classes get used/endorsed by CMOR
   so the contract/API we're working to is formally documented/agreed
   (at present it seems not to be so formally described anywhere?)
"""

import json
from pathlib import Path
from typing import Any, TypeAlias

from pydantic import BaseModel, Field

import esgvoc.api as ev

RegularExpressionValidators: TypeAlias = list[str]
"""
List of values which are assumed to be regular expressions

Attribute values provided by teams are then validated
against these regular expressions.
"""

AllowedDict: TypeAlias = dict[str, Any]
"""
Dictionary (key-value pairs). The keys define the allowed values for the given attribute

The values can be anything,
they generally provide extra information about the meaning of the keys.
"""


class DataReferenceSyntax(BaseModel):
    """
    Data reference syntax specification
    """

    directory_path_example: str
    """
    Example of a directory path that follows this DRS
    """

    directory_path_sub_experiment_example: str
    """
    Example of a directory path including a sub-experiment that follows this DRS
    """

    directory_path_template: str
    """
    Template to use for generating directory paths
    """

    filename_path_example: str
    """
    Example of a filename path that follows this DRS
    """

    filename_path_sub_experiment_example: str
    """
    Example of a filename path including a sub-experiment that follows this DRS
    """

    filename_path_template: str
    """
    Template to use for generating filename paths
    """


class ExperimentDefinition(BaseModel):
    """
    Single experiment definition
    """

    activity_id: RegularExpressionValidators
    """
    Activity ID to which this experiment belongs
    """
    # Validation, only one allowed value

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

    start_year: int | None
    """Start year of the experiment"""

    end_year: int | None
    """End year of the experiment"""

    min_number_yrs_per_sim: int
    """Minimum number of years of simulation required"""

    experiment_id: str
    """
    Experiment ID

    TODO: discuss whether `_id` should be kept or dropped
    or whether there is some way to know when it should be `_id` vs `DD` vs no difference
    """

    host_collection: str
    """
    Host collection of this experiment
    """

    parent_activity_id: list[str] = Field(default_factory=list)
    """Activity ID for the parent of this experiment"""
    # TODO: validation, only one value

    parent_experiment_id: list[str] = Field(default_factory=list)
    """Experiment ID for the parent of this experiment"""
    # TODO: validation, only one value

    tier: int
    """
    Tier i.e. priority of this experiment

    Lower is higher priority i.e. 1 is the highest priority
    """

    def to_json(self) -> dict[str, str | int | RegularExpressionValidators]:
        # make experiment the same as description, no idea why there are two fields
        res = self.model_dump()

        # Unclear if we should also be making model components capitals too
        # i.e. additional_allowed_model_components and required_model_components
        res["experiment"] = res["description"]

        return res


class ExperimentID(BaseModel):
    """
    Experiment ID definitions
    """

    experiments: dict[str, ExperimentDefinition]
    """
    Experiment definitions
    """


# TODO: check if same or different as esgvoc model
class LicenseDefinition(BaseModel):
    """
    License definition
    """

    license_type: str
    """
    Type of the license
    """
    # TODO: validation, should be SPDX identifier
    # http://spdx.org/licenses

    license_url: str
    """
    URL that describes the license
    """
    # TODO: redundant with SPDX identifiers but ok


class License(BaseModel):
    """
    License ID definitions
    """

    license_id: dict[str, LicenseDefinition]
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

    archive_id: AllowedDict
    """
    Identifier(s) of the archive(s) to which data can belong
    """

    area_label: AllowedDict
    """
    Identifier(s) of the area label(s)
    """

    branding_suffix: str
    """
    Template for branding suffix
    """

    # Switch to DataSpecsVersion when it has attributes we can use
    # data_specs_version: DataSpecsVersion
    data_specs_version: str
    """
    Version of the data specification used to generate the CVs

    Note that the exact meaning of this
    (i.e. what exactly defines the data specs)
    is still fuzzy.
    """
    # Validation(?): must be a version of the form X.Y.Z[.alpha[0-9]*]

    # Note: esgvoc doesn't have this model,
    # it just has DrsSpecification
    # which applies to either the directory or the filename,
    # but no aggregate object for the two together
    drs: DataReferenceSyntax
    """
    Data reference syntax definition
    """

    experiment_id: ExperimentID
    """
    Experiment ID definitions
    """

    frequency: AllowedDict
    """
    Frequency options
    """

    grid_label: AllowedDict
    """
    Grid label options
    """

    horizontal_label: AllowedDict
    """
    Horizontal label options
    """

    institution_id: AllowedDict
    """
    Known institution IDs
    """

    license: License
    """
    License definitions
    """

    # TODO: switch to using esgvoc's model once it is clear what key we should use for 'value'
    mip_era: str
    """
    MIP era to which the data applies
    """
    # Validation(?): must be equal to CMIP7

    # TODO: add to esgvoc?
    nominal_resolution: RegularExpressionValidators
    """
    Nominal resolution options

    TODO: link to tool which can be used for calculating this
    if people don't know how to figure this out
    """

    product: RegularExpressionValidators
    """
    Options for rough description of the kind of data product
    """

    realm: AllowedDict
    """
    Options for the data realm (TODO: check this)
    """

    region: AllowedDict
    """
    Options for the data region (this is just a rough description, not unambiguous in all cases)
    """

    required_global_attributes: list[str]
    """
    Required global attributes
    """

    def to_json(self) -> dict[str, dict[str, str, AllowedDict, RegularExpressionValidators]]:
        md = self.model_dump()

        # Unclear why this is done for some keys and not others,
        # which makes reasoning hard.
        to_hyphenise = list(md["drs"].keys())
        for k in to_hyphenise:
            md["drs"][k.replace("_", "-")] = md["drs"].pop(k)

        md["experiment_id"] = {k: v.to_json() for k, v in self.experiment_id.experiments.items()}
        # More fun
        md["DRS"] = md.pop("drs")

        cvs_json = {"CV": md}

        return cvs_json


def get_drs() -> DataReferenceSyntax:
    # Hard-coded as there are hard-coded examples below specific to CMIP7
    project = "cmip7"

    cmip7_drs_specs = ev.get_project(project).drs_specs
    directory_path_template_l = []
    directory_path_example_l = []
    # Note: this doesn't generate a valid example
    # because there are couplings between the different parts
    # and we're not capturing those when we generate the example this way
    # (e.g. the experiment-activity combination we end up with is invalid).
    # Expressing those couplings will require some thinking.
    for part in cmip7_drs_specs["directory"].parts:
        directory_path_template_l.append(f"<{part.source_collection}>")
        if part.source_collection == "drsSpecs":
            # Need esgvoc to supply examples in future
            example_value = "MIP-DRS7"

        elif part.source_collection == "source":
            # Need esgvoc to supply examples in future
            example_value = "CanESM6-MR"

        elif part.source_collection == "datasetVariant":
            # TODO: see if esgvoc wants to supply examples in future
            example_value = "r1i1p1f1"

        elif part.source_collection == "variable":
            # Need esgvoc to supply examples in future
            example_value = "tas"

        elif part.source_collection == "branding_suffix":
            # Need esgvoc to supply examples in future
            example_value = "tavg-h2m-hxy-u"

        elif part.source_collection == "datasetVersion":
            # Need esgvoc to supply examples in future
            # TODO: check if we're dropping the leading v or not
            example_value = "20251011"

        else:
            example_value = ev.get_all_terms_in_collection("cmip7", part.source_collection)[0].drs_name

        directory_path_example_l.append(example_value)

    # TODO: CMOR uses snake case for the attribute values in the templates
    # (e.g. `<branding_suffix>`)
    # rather than camelCase (e.g. `<brandingSuffix>`)
    # which is how the data descriptors are defined.
    # I guess we either need to translate on the fly
    # or update CMOR to handle data descriptors
    # rather than the snake case versions thereof.
    directory_path_template = cmip7_drs_specs["directory"].separator.join(directory_path_template_l)
    directory_path_example = cmip7_drs_specs["directory"].separator.join(directory_path_example_l)

    filename_template_l = []
    filename_path_example_l = []
    for i, part in enumerate(cmip7_drs_specs["file_name"].parts):
        if i > 0:
            prefix = cmip7_drs_specs["file_name"].separator
        else:
            prefix = ""

        if part.is_required:
            filename_template_l.append(f"{prefix}<{part.source_collection}>")
        else:
            filename_template_l.append(f"[{prefix}<{part.source_collection}>]")

        if part.source_collection == "source":
            # Need esgvoc to supply examples in future
            example_value = "CanESM6-MR"

        elif part.source_collection == "datasetVariant":
            # TODO: see if esgvoc wants to supply examples in future
            example_value = "r1i1p1f1"

        elif part.source_collection == "variable":
            # Need esgvoc to supply examples in future
            example_value = "tas"

        elif part.source_collection == "branding_suffix":
            # Need esgvoc to supply examples in future
            example_value = "tavg-h2m-hxy-u"

        elif part.source_collection == "timeRange":
            # Need esgvoc to supply examples in future
            example_value = "20250101-21001231"

        else:
            example_value = ev.get_all_terms_in_collection("cmip7", part.source_collection)[0].drs_name

        filename_path_example_l.append(example_value)

    filename_template = "".join(filename_template_l)
    filename_template = f"{filename_template}{cmip7_drs_specs['file_name'].properties['extension_separator']}{cmip7_drs_specs['file_name'].properties['extension']}"
    filename_path_example = cmip7_drs_specs["file_name"].separator.join(filename_path_example_l)
    filename_path_example = f"{filename_path_example}{cmip7_drs_specs['file_name'].properties['extension_separator']}{cmip7_drs_specs['file_name'].properties['extension']}"

    drs = DataReferenceSyntax(
        directory_path_template=directory_path_template,
        directory_path_example=directory_path_example,
        directory_path_sub_experiment_example="",
        filename_path_template=filename_template,
        filename_path_example=filename_path_example,
        filename_path_sub_experiment_example="",
    )

    return drs


def main():
    """
    Create the CMOR CVs table
    """
    OUT_FILE = Path(".") / "CMIP7-CV_for-cmor.json"

    # Fine to hard-code I think?
    project = "cmip7"

    mip_era = project.upper()

    archive_id_esgvoc = ev.get_all_terms_in_collection(project, "archive")
    archive_id = {
        v.drs_name: "TODO: description in esgvoc (or learn how to use ev to get the description)"
        for v in archive_id_esgvoc
    }

    # Bit annoying that we have to jump back and forth
    # between collection and data descriptor
    area_label_esgvoc = ev.get_all_terms_in_data_descriptor("area_label")
    area_label = {v.drs_name: v.description for v in area_label_esgvoc}

    experiment_esgvoc = ev.get_all_terms_in_data_descriptor("experiment")

    def get_min_number_yrs_per_sim(inv):
        if isinstance(inv, str):
            return int(int)

        if inv is None:
            # This shouldn't be needed, data errors in definition
            return 1

        return inv

    experiment_id = ExperimentID(
        experiments={
            v.drs_name: ExperimentDefinition(
                activity_id=v.activity,
                required_model_components=v.required_model_components,
                additional_allowed_model_components=v.additional_allowed_model_components,
                description=v.description,
                start_year=v.start_year if not isinstance(v.start_year, str) else int(v.start_year),
                end_year=v.end_year if not isinstance(v.end_year, str) else int(v.end_year),
                min_number_yrs_per_sim=get_min_number_yrs_per_sim(v.min_number_yrs_per_sim),
                experiment_id=v.experiment_id,
                host_collection=mip_era,  # yuck - should be in esgvoc?
                parent_activity_id=v.parent_activity_id,
                parent_experiment_id=v.parent_experiment_id,
                tier=v.tier,
            )
            for v in experiment_esgvoc
        }
    )

    # TOOD: put in esgvoc?
    def get_approx_interval(frequency: str) -> float:
        if frequency.startswith("1hr"):
            return 1.0 / 24.0

        if frequency.startswith("subhr"):
            return 1.0 / 24.0

        if frequency.startswith("3hr"):
            return 3.0 / 24.0

        if frequency.startswith("6hr"):
            return 6.0 / 24.0

        if frequency.startswith("day"):
            return 1.0

        if frequency.startswith("dec"):
            return 365.0 * 10.0

        if frequency.startswith("mon"):
            return 30.0

        if frequency.startswith("yr"):
            return 365.0

        raise NotImplementedError(frequency)

    frequency_esgvoc = ev.get_all_terms_in_data_descriptor("frequency")
    frequency = {
        v.drs_name: {"description": v.description, "approx_interval": get_approx_interval(v.drs_name)}
        if v.drs_name != "fx"
        # I'm still not convinced that it wouldn't be simpler to use the same schema for all types
        else "fixed (time invariant) field"
        for v in frequency_esgvoc
    }

    # TODO: clear all these out in preparation for the conclusion of
    # https://github.com/WCRP-CMIP/CMIP7-CVs/issues/202
    # TODO: Annoying differences between grid and grid_label.
    # TODO: Unify across sources or at least write down logic.
    grid_label_esgvoc = ev.get_all_terms_in_data_descriptor("grid")
    grid_label = {v.drs_name: v.description for v in grid_label_esgvoc}

    horizontal_label_esgvoc = ev.get_all_terms_in_data_descriptor("horizontal_label")
    horizontal_label = {v.drs_name: v.description for v in horizontal_label_esgvoc}

    institution_id_esgvoc = ev.get_all_terms_in_data_descriptor("institution")
    # TODO: name seems the wrong key?
    # TODO: lots of the values need checking
    institution_id = {v.drs_name: v.name for v in institution_id_esgvoc}

    license = License(
        license_id={
            "CC BY 4.0": LicenseDefinition(
                license_type="Creative Commons Attribution 4.0 International",
                license_url="https://creativecommons.org/licenses/by/4.0/",
            ),
            "CC0 1.0": LicenseDefinition(
                license_type="Creative Commons CC0 1.0 Universal Public Domain Dedication",
                license_url="https://creativecommons.org/publicdomain/zero/1.0/",
            ),
        },
        license_template="<license_id>; CMIP7 data produced by <institution_id> is licensed under a <license_type> License (<license_url>). Consult https://pcmdi.llnl.gov/CMIP7/TermsOfUse for terms of use governing CMIP7 output, including citation requirements and proper acknowledgment. The data producers and data providers make no warranty, either express or implied, including, but not limited to, warranties of merchantability and fitness for a particular purpose. All liabilities arising from the supply of the information (including any liability arising in negligence) are excluded to the fullest extent permitted by law.",
    )

    # Not  sure if we can get this from elsewhere, it's not in esgvoc
    nominal_resolution = [
        "0.5 km",
        "1 km",
        "10 km",
        "100 km",
        "1000 km",
        "10000 km",
        "1x1 degree",
        "2.5 km",
        "25 km",
        "250 km",
        "2500 km",
        "5 km",
        "50 km",
        "500 km",
        "5000 km",
    ]

    product_esgvoc = ev.get_all_terms_in_data_descriptor("product")
    product = [v.drs_name for v in product_esgvoc]

    realm_esgvoc = ev.get_all_terms_in_data_descriptor("realm")
    realm = {v.drs_name: v.description for v in realm_esgvoc}

    # These values do not look correct
    region_esgvoc = ev.get_all_terms_in_data_descriptor("region")
    region = {v.drs_name: v.description for v in region_esgvoc}

    required_global_attributes = []
    for v in ev.get_project(project).attr_specs:
        if v.is_required:
            # Really don't like needing this `if` statement,
            # can we just have an `attribute_name` on esgvoc terms?
            if v.field_name is None:
                required_global_attributes.append(v.source_collection)
            else:
                required_global_attributes.append(v.field_name)

    drs = get_drs()

    cmor_cvs_table = CMORCVsTable(
        archive_id=archive_id,
        area_label=area_label,
        # Hard-code, fine?
        # Maybe possible to get from esgvoc...
        branding_suffix="<temporal_label><vertical_label><horizontal_label><area_label>",
        drs=drs,
        experiment_id=experiment_id,
        frequency=frequency,
        grid_label=grid_label,
        horizontal_label=horizontal_label,
        institution_id=institution_id,
        license=license,
        nominal_resolution=nominal_resolution,
        product=product,
        realm=realm,
        region=region,
        required_global_attributes=required_global_attributes,
        # Hard-coded values, no need to/can't be retrieved from esgvoc ?
        data_specs_version="placeholder",
        mip_era=mip_era,
    )

    cmor_cvs_table_json = cmor_cvs_table.to_json()
    with open(OUT_FILE, "w") as fh:
        json.dump(cmor_cvs_table_json, fh, indent=4, sort_keys=True)

    print(f"Wrote {OUT_FILE}")


if __name__ == "__main__":
    main()

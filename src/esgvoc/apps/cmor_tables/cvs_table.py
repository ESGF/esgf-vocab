"""
Support for generating CMOR CVs tables
"""

from typing import Any, TypeAlias

from pydantic import BaseModel

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
    Allowed values of `archive_id`
    """

    area_label: AllowedDict
    """
    Allowed values of `area_label`
    """

    branding_suffix: str
    """
    Template for branding suffix
    """

    def to_cvs_json(
        self, top_level_key: str = "CV"
    ) -> dict[str, dict[str, str, AllowedDict, RegularExpressionValidators]]:
        md = self.model_dump()

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
    attribute_name: str, ev_project: ev_api.project_specs.ProjectSpecs
) -> ev_api.project_specs.AttributeProperty:
    for ev_attribute_property in ev_project.attr_specs:
        if ev_attribute_property.field_name == attribute_name:
            break

    else:
        raise KeyError(attribute_name)

    return ev_attribute_property


def get_allowed_dict_for_attribute_name(
    attribute_name: str, ev_project: ev_api.project_specs.ProjectSpecs
) -> AllowedDict:
    ev_attribute_property = get_project_attribute_property(attribute_name=attribute_name, ev_project=ev_project)

    attribute_instances = ev_api.get_all_terms_in_collection(
        ev_project.project_id, ev_attribute_property.source_collection
    )

    res = {v.drs_name: v.description for v in attribute_instances}

    return res


def get_template_for_composite_term(attribute_name: str, ev_project: ev_api.project_specs.ProjectSpecs) -> str:
    ev_attribute_property = get_project_attribute_property(attribute_name=attribute_name, ev_project=ev_project)
    terms = ev_api.get_all_terms_in_collection(ev_project.project_id, ev_attribute_property.source_collection)
    if len(terms) > 1:
        raise AssertionError(terms)

    term = terms[0]

    parts_l = []
    for v in term.parts:
        va = get_project_attribute_property(v.type, ev_project)
        parts_l.append(f"<{va.field_name}>")

    res = term.separator.join(parts_l)

    return res


def generate_cvs_table(project: str) -> CMORCVsTable:
    ev_project = ev_api.projects.get_project(project)

    cmor_cvs_table = CMORCVsTable(
        **{
            key: get_allowed_dict_for_attribute_name(key, ev_project)
            for key in [
                "archive_id",
                "area_label",
            ]
        },
        **{
            key: get_template_for_composite_term(key, ev_project)
            for key in [
                # Called branded_suffix everywhere else, why did we choose different name for attribute?
                "branding_suffix",
            ]
        },
    )

    return cmor_cvs_table

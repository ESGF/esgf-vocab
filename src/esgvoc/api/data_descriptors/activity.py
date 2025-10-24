"""
Model (i.e. schema/definition) of the activity data descriptor
"""

import re
from typing import TYPE_CHECKING

from pydantic import HttpUrl, field_validator

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor

if TYPE_CHECKING:
    from esgvoc.api.data_descriptors.experiment import Experiment


class Activity(PlainTermDataDescriptor):
    """
    Identifier of the CMIP activity to which a dataset belongs

    Examples: "PMIP", "CMIP", "CFMIP", "ScenarioMIP"

    An 'activity' refers to a coordinated set of modeling experiments
    designed to address specific scientific questions or objectives.
    Activities generally have the suffix "MIP",
    for "model intercomparison project"
    (even though they're not referred to as projects within CMIP CVs).

    Activity DRS names should not include a phase.
    For example, the activity should always be ScenarioMIP,
    not ScenarioMIP6, ScenarioMIP7 etc.

    It is now considered essential for each :py:class:`Experiment`
    to be associated with a single :py:class:`Activity`.
    However, this was not followed in CMIP6,
    which significantly complicates definition and validation
    of the schemas for these two classes.
    """

    experiments: list["Experiment"]
    """
    Experiments 'sponsored' by this activity
    """

    # TODO: think - should this be a list ?
    url: HttpUrl | None
    """
    URL with more information about this activity
    """

    @field_validator("drs_name")
    def name_must_not_end_in_number(cls, v):
        if re.match(r".*\d$", v):
            msg = f"`drs_name` for {cls} must not end in a number. Received: {v}"
            raise ValueError(msg)

        return v

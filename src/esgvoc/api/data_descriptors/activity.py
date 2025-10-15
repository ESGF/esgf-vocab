"""
Model (i.e. schema/definition) of the activity data descriptor
"""

from typing import TYPE_CHECKING

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
    [TODO: How do we validate this? Forbid drs_name from ending in a number?]

    It is now considered essential for each :py:class:`Experiment`
    to be associated with a single :py:class:`Activity`.
    However, this was not followed in CMIP6,
    which significantly complicates definition and validation
    of the schemas for these two classes.
    """

    # None not allowed, empty list should be used
    # if there are no additional_allowed_model_components.
    # Getting the cross-referencing right to avoid
    # circular imports is fiddly.
    # Using a string like this and then calling
    # `.model_rebuild()` at some point
    # is the only way I know to do this.
    experiments: list["Experiment"]
    """
    Experiments 'sponsored' by this activity
    """

    url: str | None
    """
    URL with more information about this activity
    """

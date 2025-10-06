"""
Model (i.e. schema/definition) of the activity data descriptor
"""

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


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

    name: str
    # TODO: remove - redundant given we have drs_name ?
    long_name: str
    # TODO: Change to description for consistency?
    url: str | None
    """
    URL with more information about this activity
    """

    # TODO: add link to experiments
    # (I'm not sure how easy this is with pydantic,
    # but it is possible with e.g. SQLModel
    # although it does complicate things a bit
    # as you need to define a class that represents the database model
    # (with ID cross-links) and a class that represents the data model
    # i.e. that doesn't have database-specific IDs.
    # I think this complexity would be worth it,
    # but we'd have to discuss as it would be non-zero effort.)
    # experiments: list[Experiment] = Field(default_factory=list)

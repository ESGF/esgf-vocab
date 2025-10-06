"""
Model (i.e. schema/definition) of the experiment data descriptor
"""

from pydantic import Field

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class Experiment(PlainTermDataDescriptor):
    """
    Identifier of the CMIP experiment to which a dataset belongs/a dataset is derived from

    Examples: "historical", "piControl", "ssp126"

    An 'experiment' refers to a specific, controlled simulation
    conducted using climate models to investigate particular aspects of the Earth's climate system.
    These experiments are designed with set parameters, such as initial conditions,
    external forcings (like greenhouse gas  concentrations or solar radiation),
    and duration, to explore and understand climate behavior under various conditions.

    It is now considered essential for each :py:class:`Experiment`
    to be associated with a single :py:class:`Activity`.
    However, this was not followed in CMIP6,
    which significantly complicates definition and validation
    of the schemas for these two classes.
    """

    # TODO: discuss how/if this could be only a single value for
    # everything except CMIP6
    # activity: list[Activity] = Field(default_factory=list)
    # activity: Activity | list[Activity] = Field(default=None)
    activity: list[str] = Field(default_factory=list)
    """
    Activity to which this experiment belongs

    Could also be phrased as,
    "activity with which this experiment is most strongly associated"
    """

    description: str
    """
    Description of the experiment
    """

    tier: int | None
    """
    Priority tier for this experiment

    1 is highest priority.
    If `None`, no priority is specified for this experiment.
    """

    experiment_id: str
    # TODO: remove? redundant with drs_name

    sub_experiment_id: list[str] | None
    # TODO: figure out what this means

    experiment: str
    # TODO: remove? redundant with description

    # TODO: discuss this change
    # required_model_components: list[ModelComponent] = Field(default=None)
    required_model_components: list[str] | None
    """
    Model components required to run this experiment

    [TODO: delete this if we switch to a default of empty list rather than `None`]
    If `None`, then no particular model components are required to run this experiment.
    However, please also check `additional_allowed_model_components`
    as `None` does not mean that any model components are allowed.
    """

    # TODO: discuss this change
    # additional_allowed_model_components: list[ModelComponent] = Field(default_factory=list)
    additional_allowed_model_components: list[str] = Field(default_factory=list)
    """
    Non-compulsory model components that are allowed when running this experiment
    """

    # TODO: do we need to support str here or are experiments always specified with start years
    # (rather than start dates)?
    start_year: int | None
    """
    Start year of the experiment

    A value of `None` indicates that simulations may start with any year,
    no particular value is required.
    """

    # TODO: do we need to support str here or are experiments always specified with end years
    # (rather than end dates)?
    end_year: int | None
    """
    End year of the experiment

    A value of `None` indicates that simulations may end with any year,
    no particular value is required.
    """

    min_number_yrs_per_sim: int | None
    """
    Minimum number of years required per simulation for this experiment

    If `None`, then there is no minimum number of years required.
    You can submit as few years as you like, even just one.
    """

    # # TODO: should be
    # parent_activity_id: Activity
    # # or
    # parent_activity: Activity
    # # or
    # parent_activity_id: str
    # # rationale: more than one parent activity is not allowed
    # parent_activity_id: list[str] | None
    """
    Activity to which this experiment's parent experiment belongs

    If `None`, this experiment has no parent experiment.
    """

    # # TODO: should be
    # parent_experiment_id: Experiment
    # # or
    # parent_experiment: str
    # # or
    # parent_experiment_id: str
    # # rationale: more than one parent activity is not allowed
    parent_experiment_id: list[str] | None
    """
    This experiment's parent experiment

    If `None`, this experiment has no parent experiment.
    """

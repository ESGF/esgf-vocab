from __future__ import annotations
from typing import Union
from typing_extensions import Annotated
from pydantic import Field
from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor
from typing import Optional
from esgvoc.api.data_descriptors.activity import Activity
from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor
from esgvoc.api.data_descriptors.mip_era import MipEra
from esgvoc.api.data_descriptors.model_component import ModelComponent
from esgvoc.api.data_descriptors.source_type import SourceType
from esgvoc.api.pydantic_handler import create_union


class ExperimentCMI7(PlainTermDataDescriptor):
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

    activity: list[str]
    """
    Activity to which this experiment belongs

    Could also be phrased as,
    "activity with which this experiment is most strongly associated".
    """

    # None not allowed, empty list should be used
    # if there are no additional_allowed_model_components
    additional_allowed_model_components: list[str] = Field(default_factory=list)
    """
    Non-compulsory model components that are allowed when running this experiment
    """

    branch_information: str | None
    """
    Information about how this experiment should branch from its parent

    If `None`, this experiment has no parent
    and therefore no branching information is required.
    """

    # TODO: get Dan to help with pydantic type hint
    # https://docs.pydantic.dev/2.2/usage/types/datetime/
    end_timestamp: str | None
    """
    End timestamp (ISO-8601) of the experiment

    A value of `None` indicates that simulations may end at any time,
    no particular value is required.
    """

    min_ensemble_size: int
    """
    Minimum number of ensemble members to run for this experiment

    This is the minimum ensemble size requested by the definer of the experiment.
    For other uses, other ensemble sizes may be required
    so please double check the application your simulations
    (as defined in e.g. the data request)
    are intended for too before deciding on your ensemble size.
    """

    # `min_length: str | None` or something
    # so people can specify units rather than having to convert
    # everything to years would allow slightly more flexibility
    # and precision. However, I don't think we have a use case for this
    # so the extra flexibility and precision probably isn't worth the headache.
    min_number_yrs_per_sim: float | None
    """
    Minimum number of years required per simulation for this experiment

    If `None`, then there is no minimum number of years required.
    You can submit as short a simulation as you like.
    """

    parent_activity: Activity | None
    """
    Activity to which this experiment's parent experiment belongs

    If `None`, this parent experiment has no parent activity.
    """

    parent_experiment: Optional[list[str]]
    """
    This experiment's parent experiment

    If `None`, this experiment has no parent experiment.
    """

    parent_mip_era: MipEra | None
    """
    The MIP era to which this experiment's parent experiment belongs

    If `None`, this experiment has no parent experiment.
    """

    required_model_components: list[str]
    """
    Model components required to run this experiment
    """

    # TODO: get Dan to help with pydantic type hint
    # https://docs.pydantic.dev/2.2/usage/types/datetime/
    start_timestamp: str | None
    """
    Start timestamp (ISO-8601) of the experiment

    A value of `None` indicates that simulations may start with any year,
    no particular value is required.
    """

    tier: int | None
    """
    Priority tier for this experiment

    1 is highest priority.
    If `None`, no priority is specified for this experiment.
    """


class ExperimentBeforeCMIP7(PlainTermDataDescriptor):
    """
    An 'experiment' refers to a specific, controlled simulation conducted using climate models to \
    investigate particular aspects of the Earth's climate system. These experiments are designed \
    with set parameters, such as initial conditions, external forcings (like greenhouse gas \
    concentrations or solar radiation), and duration, to explore and understand climate behavior \
    under various scenarios and conditions.
    """

    activity: list[str] = Field(default_factory=list)
    description: str
    tier: int | None
    experiment_id: str
    sub_experiment_id: list[str] | None
    experiment: str
    required_model_components: list[str] | None
    additional_allowed_model_components: list[str] = Field(default_factory=list)
    start_year: str | int | None
    end_year: str | int | None
    min_number_yrs_per_sim: int | None
    parent_activity_id: list[str] | None
    parent_experiment_id: list[str] | None


Experiment = create_union(ExperimentCMI7, ExperimentBeforeCMIP7)

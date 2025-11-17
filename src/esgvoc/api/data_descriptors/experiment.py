"""
Model (i.e. schema/definition) of the experiment data descriptor
"""

from __future__ import annotations

from datetime import datetime
from typing import Union

from pydantic import BeforeValidator, Field
from typing_extensions import Annotated

from esgvoc.api.data_descriptors.activity import Activity
from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor
from esgvoc.api.data_descriptors.mip_era import MipEra
from esgvoc.api.data_descriptors.model_component import ModelComponent
from esgvoc.api.pydantic_handler import create_union


def ensure_iso8601_compliant_or_none(value: str | None) -> datetime | None:
    """
    Ensure that a value is ISO-8601 compliant or `None`

    Parameters
    ----------
    value
        Value to check

    Returns
    -------
    :
        Value, cast to `datetime.datetime` if `value is not None`
    """
    if value is None:
        return None

    res = datetime.fromisoformat(value.replace("Z", "+00:00"))

    return res


class ExperimentCMIP7(PlainTermDataDescriptor):
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

    # # Can't be Activity to avoid circularity (?).
    # # Or it can be, but you have to be very careful
    # # (SQLModel makes this easier).
    # activity: Activity
    activity: str
    """
    Activity to which this experiment belongs

    Could also be phrased as,
    "activity with which this experiment is most strongly associated".
    """

    # Note: Allowing str or ModelComponent is under discussion.
    # Using this to get things working.
    # Long-term, we might do something different.
    additional_allowed_model_components: list[str] | list[ModelComponent]
    """
    Non-compulsory model components that are allowed when running this experiment
    """

    branch_information: str | None
    """
    Information about how this experiment should branch from its parent

    If `None`, this experiment has no parent
    and therefore no branching information is required.
    """

    end_timestamp: Annotated[datetime | None, BeforeValidator(ensure_iso8601_compliant_or_none)]
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

    min_number_yrs_per_sim: float | None
    """
    Minimum number of years required per simulation for this experiment

    If `None`, then there is no minimum number of years required.
    You can submit as short a simulation as you like.
    """

    # Note: Allowing str or Activity is under discussion.
    # Using this to get things working.
    # Long-term, we might do something different.
    parent_activity: Activity | str | None
    """
    Activity to which this experiment's parent experiment belongs

    If `None`, this experiment has no parent experiment.
    """

    # Note: Allowing str or Experiment is under discussion.
    # Using this to get things working.
    # Long-term, we might do something different.
    parent_experiment: Union[str, "Experiment", None]
    """
    This experiment's parent experiment

    If `None`, this experiment has no parent experiment.
    """

    # Note: Allowing str or MipEra is under discussion.
    # Using this to get things working.
    # Long-term, we might do something different.
    parent_mip_era: MipEra | str | None
    """
    The MIP era to which this experiment's parent experiment belongs

    If `None`, this experiment has no parent experiment.
    """

    # Note: Allowing str or ModelComponent is under discussion.
    # Using this to get things working.
    # Long-term, we might do something different.
    required_model_components: list[ModelComponent | str]
    """
    Model components required to run this experiment
    """

    start_timestamp: Annotated[datetime | None, BeforeValidator(ensure_iso8601_compliant_or_none)]
    """
    Start timestamp (ISO-8601) of the experiment

    A value of `None` indicates that simulations may start at any time,
    no particular value is required.
    """

    tier: int | None
    """
    Priority tier for this experiment

    1 is highest priority.
    If `None`, no priority is specified for this experiment.
    """


class ExperimentLegacy(PlainTermDataDescriptor):
    """
    An 'experiment' refers to a specific, controlled simulation conducted using climate models to \
    investigate particular aspects of the Earth's climate system. These experiments are designed \
    with set parameters, such as initial conditions, external forcings (like greenhouse gas \
    concentrations or solar radiation), and duration, to explore and understand climate behavior \
    under various scenarios and conditions.
    """

    activity: list[str] = Field(default_factory=list)
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


Experiment = create_union(ExperimentCMIP7, ExperimentLegacy)

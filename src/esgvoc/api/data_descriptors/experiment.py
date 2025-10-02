from pydantic import Field

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class Experiment(PlainTermDataDescriptor):
    """
    An 'experiment' refers to a specific, controlled simulation conducted using climate models to \
    investigate particular aspects of the Earth's climate system. These experiments are designed \
    with set parameters, such as initial conditions, external forcings (like greenhouse gas \
    concentrations or solar radiation), and duration, to explore and understand climate behavior \
    under various scenarios and conditions.
    """

    activity: list[str] = Field(default_factory=list)
    # Should only be one allowed value here
    description: str
    tier: int | None
    experiment_id: str
    sub_experiment_id: list[str] | None
    experiment: str
    required_model_components: list[str] | None
    additional_allowed_model_components: list[str] = Field(default_factory=list)
    start_year: str | int | None  # str allowed?
    end_year: str | int | None  # str allowed?
    min_number_yrs_per_sim: int | None  # None should not be allowed
    parent_activity_id: list[str] | None
    parent_experiment_id: list[str] | None
    # host_collection, used by CMOR, missing here

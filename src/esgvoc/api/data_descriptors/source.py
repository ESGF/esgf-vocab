"""
Model (i.e. schema/definition) of the source descriptor
"""

from typing import Optional

from pydantic import Field

from esgvoc.api.data_descriptors.activity import Activity
from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor
from esgvoc.api.data_descriptors.organisation import Organisation


# TODO: strip down to minimal set as advised by Matt
# see https://github.com/ESGF/esgf-vocab/pull/51#issuecomment-3432513075
class Source(PlainTermDataDescriptor):
    """
    Source of the dataset

    Examples: "CanESM6-MR", "CR-CMIP-1-0-0"

    The more precise meaning of source depends on the kind of dataset this is.
    For model output, 'source' refers to a numerical representations of the Earth's climate system.
    This source is the model which was used to generate the dataset.
    Such models simulate the interactions between the atmosphere, oceans, land surface, and ice.
    They are based on fundamental physical, chemical, and biological processes
    and are used to understand past, present, and future climate conditions.
    Each source or model is typically associated with a specific research institution, center, or group.
    For instance, models like 'EC-Earth' are developed by a consortium of European institutes,
    while 'GFDL-CM4' is developed by the Geophysical Fluid Dynamics Laboratory (GFDL) in the United States.

    For model inputs i.e. forcings, the 'source' is a unique identifier
    for the group that produced the data and its version.
    This is a different convention from almost all other cases
    (which really muddies the meaning of the term).
    """

    activity_participation: list[Activity]
    """
    Activities in which this source has participated
    """
    # TODO: discuss moving this out of the CVs.
    # This list changes over time, which is incompatible with the idea of a static CV.
    # TODO: delete ? If people want this, they should get it from the EMD

    cohort: list[str] = Field(default_factory=list)
    """
    TODO: discuss what this is
    """
    # TODO: discuss moving this out of the CVs.
    # Given that one of the values I have seen used for this is 'published',
    # this list changes over time, which is incompatible with the idea of a static CV.

    organisation: Organisation
    """
    Organisation responsible for this source

    Reponsible is vaguely defined, but in practice it is the group
    that submits data using this source.
    """

    label: str
    # TODO: delete, get from Organisation instead

    label_extended: Optional[str] = None
    # TODO: delete, get from Organisation instead

    license: dict = Field(default_factory=dict)
    # TODO: delete, separate CV

    model_component: Optional[dict] = None
    # TODO: delete. If people want this, they should get it from the EMD

    release_year: int | None
    """
    Year that this source was released

    Only really applies to models.
    If `None`, the release year is either unknown
    or this concept does not apply (e.g. because the source is not a model).
    """
    # TODO: delete. If people want this, they should get it from the EMD

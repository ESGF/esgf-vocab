"""
Model (i.e. schema/definition) of the data reference syntax (DRS) specifications data descriptor
"""

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class DRSSpecs(PlainTermDataDescriptor):
    """
    Data reference syntax (DRS) specification

    Examples: "MIP-DRS7"

    Identifier of the the data reference syntax used to name files,
    define directory trees, and uniquely identify datasets.
    This data descriptor is self-referential:
    for a given set of CVs (e.g. CMIP7 CVs),
    it can only have a single value.
    [In practice, this term was a nice idea,
    but the way things are architected at the moment,
    we can't really exploit it.
    As background, the idea was that multiple projects could use the same DRS
    e.g. CMIP8 could use the same DRS as CMIP7 if it wanted.
    In practice, `project_specs` is currently defined per project by esgvoc
    so there is no way for one project to point at another project's specs
    to specify the DRS.
    The way of using the same DRS would be to simply copy the project specs.
    I actually don't think this is a bad thing
    (new projects spin up slowly so copying one file is not a big issue).
    It just means that this label points basically nowhere,
    there is no 'DRS registry' so people can say,
    "I have DRS MIP-DRS7, so I go here and look up exactly what that means,
    then off I go".
    However, it does open up the possibility of such centralisation/re-use in future
    so while it's a bit redundant now, having it adds only minor extra work
    and may be useful so I guess we just go with it.]
    """

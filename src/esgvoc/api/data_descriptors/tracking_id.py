"""
Model (i.e. schema/definition) of the tracking ID data descriptor
"""

from esgvoc.api.data_descriptors.data_descriptor import PatternTermDataDescriptor


class TrackingId(PatternTermDataDescriptor):
    """
    Tracking ID, i.e. unique ID, of a file

    Examples: "hdl:21.14107/f6635404-8a1a-4aa9-918d-3792e8321f04",
              "hdl:21.14100/718ee427-4efb-46a8-9f89-8192593b15fe"

    This data descriptor applies only at the file level,
    not to datasets as a whole (each file in a dataset gets a unique ID).

    The regex is of the form `hdl:<prefix>/<uuid>`,
    where `<prefix>` is a prefix which is the same for all files in the same 'group'
    and `<uuid>` is a universally unique ID (UUID).

    The 'group' is a bit loosely defined and can be defined in different ways
    for different purposes.
    For CMIP phases, the 'group' is usually the CMIP phase
    i.e. all files that are part of the same CMIP phase use the same tracking ID prefix
    (e.g. all CMIP6 files have the same prefix, all CMIP7 files have the same prefix).
    (Also note that some projects haven't really got this right,
    e.g. the input4MIPs project has re-used the CMIP6 prefix, rather than using its own.)

    The prefixes come from [handle.net](https://www.handle.net/index.html).
    [handle.net](https://www.handle.net/index.html) prefixes
    are allotted to different CMIP (or other project) exercises.
    These prefixes are used by the
    [handle.net](https://www.handle.net/index.html)
    service to group all the entries for the given exercise together.
    These prefixes allow a) each file to have a unique ID
    and b) users to look up entries for all files using their unique ID
    via the [handle.net](https://www.handle.net/index.html) service.
    The prefixes are currently managed and registered by DKRZ
    on behalf of the ESGF team (we think, it's not 100% clear).

    The last part of the tracking ID is a UUID.
    The specification of a UUID is defined elsewhere
    (apparently in ISO/IEC 9834-8:2014).
    A new UUID must be generated for every single file
    such that every file has a unique tracking id
    (this uniqueness is both within a project thanks to the differing UUIDs
    and across projects thanks to the differing prefixes).
    Most programming languages have native support for UUID generation
    (e.g. the `uuid` library is part of Python's standard library).
    For a standalone solution, the OSSP utility is available.
    It can be accessed from http://www.ossp.org/pkg/lib/uuid/.
    Since CMIP6, version 4 UUIDs (random number based) have been required.

    The tracking IDs are
    used by a PID service
    so that users can find further information about the file
    by going to `hdl.handle.net/<tracking_id_after_the_hdl_colon_prefix_is_removed>`
    e.g. `hdl.handle.net/21.14107/f6635404-8a1a-4aa9-918d-3792e8321f04`
    (a working link from CMIP6 for those who would like to see a live demonstration is
    [hdl.handle.net/21.14100/f2f502c9-9626-31c6-b016-3f7c0534803b](),
    which was inferred from a file in which the tracking ID is
    `hdl:21.14100/f2f502c9-9626-31c6-b016-3f7c0534803b`).
    (Or at least this link with handle.net is the intention.
    It hasn't always happened
    e.g this is not the case for all CMIP7 input4MIPs files)
    """

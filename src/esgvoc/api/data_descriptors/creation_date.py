"""
Model (i.e. schema/definition) of the creation date data descriptor
"""

from esgvoc.api.data_descriptors.data_descriptor import PatternTermDataDescriptor


class CreationDate(PatternTermDataDescriptor):
    r"""
    Date (more specifically timestamp) that the file was created

    Examples: "2025-08-21T04:23:12Z", "2024-04-11T14:03:10Z"

    Note that the examples above assume a `regex` of
    `\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z`
    (this matches ISO 8601 timestamps in UTC,
    although even this isn't really complete and regex validating timestamps is a nightmare,
    see e.g. https://stackoverflow.com/questions/28020805/regex-validate-correct-iso8601-date-string-with-time,
    would we consider just having a `ValidatedTermDataDescriptor`
    to support cases where the term is validated by a function
    rather than only allowing regex validation).
    If you use a different regex, different examples would be needed.
    """

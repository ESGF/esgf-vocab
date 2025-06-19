from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class Activity(PlainTermDataDescriptor):
    """
    An 'activity' refers to a coordinated set of modeling experiments designed to address specific \
    scientific questions or objectives. Each activity is focused on different aspects of climate \
    science and utilizes various models to study a wide range of climate phenomena. \
    Activities are often organized around key research themes and may involve multiple experiments, \
    scenarios, and model configurations.
    """
    name: str
    long_name: str
    url: str | None

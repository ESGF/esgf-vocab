from esgvoc.api.data_descriptors.data_descriptor import DataDescriptor, PlainTermDataDescriptor


class Model(PlainTermDataDescriptor):
    """
    The following properties provide a top-level description of the model as whole.
    In the property examples, underlined and italicised values are taken from section 7. Controlled vocabularies.
    """

    name: str
    family: str
    dynamic_components: str
    prescribed_components: str
    ommited_components: str
    description: str
    calendar: str
    release_year: str
    references: str

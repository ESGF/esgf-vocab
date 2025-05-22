from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class Reference(PlainTermDataDescriptor):
    """
    The top-level model and its model components must each have at least one reference, defined by the following properties:

    • Citation
        ◦ A human-readable citation for the work.
        ◦ E.g. Smith, R. S., Mathiot, P., Siahaan, A., Lee, V., Cornford, S. L., Gregory, J. M., et al. (2021). Coupling the U.K. Earth System model to dynamic models of the Greenland and Antarctic ice sheets. Journal of Advances in Modeling Earth Systems, 13, e2021MS002520. https://doi.org/10.1029/2021MS002520, 2023
    • DOI
        ◦ The persistent identifier (DOI) used to identify the work.
        ◦ A DOI is required for all references. A reference that does not already have a DOI (as could be the case for some technical reports, for instance) must be given one (e.g. with a service like Zenodo).
        ◦ E.g. https://doi.org/10.1029/2021MS002520
    """

    citation: str
    doi: str

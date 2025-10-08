from pydantic import BaseModel, Field, field_validator
from esgvoc.api.data_descriptors.data_descriptor import DataDescriptor, PlainTermDataDescriptor


class Reference(BaseModel):
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

    citation: str = Field(
        description="A human-readable citation for the work.", min_length=1)
    doi: str = Field(
        description="The persistent identifier (DOI) used to identify the work. Must be a valid DOI URL.", min_length=1
    )

    @field_validator("doi")
    @classmethod
    def validate_doi(cls, v):
        """Validate that DOI follows proper format."""
        if not v.startswith("https://doi.org/"):
            raise ValueError('DOI must start with "https://doi.org/"')
        if len(v) <= len("https://doi.org/"):
            raise ValueError(
                'DOI must contain identifier after "https://doi.org/"')
        return v

    @field_validator("citation")
    @classmethod
    def validate_citation(cls, v):
        """Validate that citation is not empty."""
        if not v.strip():
            raise ValueError("Citation cannot be empty")
        return v.strip()

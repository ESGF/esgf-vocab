from pydantic import BaseModel


class MatchingTerm(BaseModel):
    """
    Place holder for a term that matches a value (term validation).
    """
    project_id: str
    """The project id to which the term belongs."""
    collection_id: str
    """The collection id to which the term belongs."""
    term_id: str
    """The term id."""

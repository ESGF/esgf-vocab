from typing import Iterable
from enum import Enum
from pydantic import BaseModel
from sqlalchemy import ColumnElement, func
from sqlmodel import col


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


class SearchType(Enum):
    """
    The search types used for to find terms.
    """
    EXACT = "exact"
    """Performs exact match."""
    LIKE = "like"  # can interpret %
    """As SQL operator, it can interpret % as a wildcard."""
    STARTS_WITH = "starts_with"  # can interpret %
    """Prefix based search."""
    ENDS_WITH = "ends_with"  # can interpret %
    """Suffix based search."""
    REGEX = "regex"
    """Search based on regex."""


class SearchSettings(BaseModel):
    """
    Search configuration.
    """
    type: SearchType = SearchType.EXACT
    """The type of search."""
    case_sensitive: bool = True
    """Enable case sensitivity or not."""
    not_operator: bool = False
    """Give the opposite result like the NOT SQL operator."""
    selected_term_fields: Iterable[str]|None = None
    """Term fields to select"""


def _create_str_comparison_expression(field: str,
                                      value: str,
                                      settings: SearchSettings|None) -> ColumnElement:
    '''
    SQLite LIKE is case insensitive (and so STARTS/ENDS_WITH which are implemented with LIKE).
    So the case sensitive LIKE is implemented with REGEX.
    The i versions of SQLAlchemy operators (icontains, etc.) are not useful
    (but other dbs than SQLite should use them).
    If the provided `settings` is None, this functions returns an exact search expression.
    '''
    does_wild_cards_in_value_have_to_be_interpreted = False
    # Shortcut.
    if settings is None:
        return col(field).is_(other=value)
    else:
        match settings.type:
            # Early return because not operator is not implement with tilde symbol.
            case SearchType.EXACT:
                if settings.case_sensitive:
                    if settings.not_operator:
                        return col(field).is_not(other=value)
                    else:
                        return col(field).is_(other=value)
                else:
                    if settings.not_operator:
                        return func.lower(field) != func.lower(value)
                    else:
                        return func.lower(field) == func.lower(value)
            case SearchType.LIKE:
                if settings.case_sensitive:
                    result = col(field).regexp_match(pattern=f".*{value}.*")
                else:
                    result = col(field).contains(
                        other=value,
                        autoescape=not does_wild_cards_in_value_have_to_be_interpreted,
                    )
            case SearchType.STARTS_WITH:
                if settings.case_sensitive:
                    result = col(field).regexp_match(pattern=f"^{value}.*")
                else:
                    result = col(field).startswith(
                        other=value,
                        autoescape=not does_wild_cards_in_value_have_to_be_interpreted,
                    )
            case SearchType.ENDS_WITH:
                if settings.case_sensitive:
                    result = col(field).regexp_match(pattern=f"{value}$")
                else:
                    result = col(field).endswith(
                        other=value,
                        autoescape=not does_wild_cards_in_value_have_to_be_interpreted,
                    )
            case SearchType.REGEX:
                if settings.case_sensitive:
                    result = col(field).regexp_match(pattern=value)
                else:
                    raise NotImplementedError(
                        "regex string comparison case insensitive is not implemented"
                    )
        if settings.not_operator:
            return ~result
        else:
            return result
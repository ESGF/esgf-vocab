from enum import Enum

from pydantic import BaseModel
from sqlalchemy import ColumnElement, func
from sqlmodel import col


class MatchingTerm(BaseModel):
    project_id: str
    collection_id: str
    term_id: str


class SearchType(Enum):
    EXACT = "exact"
    LIKE = "like"  # can interpret %
    STARTS_WITH = "starts_with"  # can interpret %
    ENDS_WITH = "ends_with"  # can interpret %
    REGEX = "regex"


class SearchSettings(BaseModel):
    type: SearchType = SearchType.EXACT
    case_sensitive: bool = True
    not_operator: bool = False


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
import json
from enum import Enum
from pathlib import Path

from pydantic import BaseModel
from sqlalchemy import BinaryExpression, func
from sqlmodel import col

from cmipld.models.pydantic import DATA_DESCRIPTOR_CLASS_MAPPING


def read_json_file(json_file_path: Path) -> dict:
    return json.loads(json_file_path.read_text())


def get_pydantic_class(data_descriptor_id: str) -> type[BaseModel]:
    if data_descriptor_id in DATA_DESCRIPTOR_CLASS_MAPPING:
        return DATA_DESCRIPTOR_CLASS_MAPPING[data_descriptor_id]
    else:
        raise ValueError(f"{data_descriptor_id} pydantic class not found")


class SearchType(Enum):
    EXACT = ("exact",)
    LIKE = ("like",)  # can interpret %
    STARTS_WITH = ("starts_with",)  # can interpret %
    ENDS_WITH = "ends_with"  # can interpret %
    REGEX = ("regex",)


class SearchSettings:
    def __init__(
        self,
        type: SearchType = SearchType.EXACT,
        is_case_sensitive: bool = True,
        add_not_operator: bool = False,
    ):
        self.type = type
        self.is_case_sensitive = is_case_sensitive
        self.has_not_operator = add_not_operator


# SQLite LIKE is case insensitive (and so STARTS/ENDS_WITH which are implemented with LIKE).
# So the case sensitive LIKE is implemented with REGEX.
# The i versions of SQLAlchemy operators (icontains, etc.) are not usefull (but other dbs than SQLite should use them).
def create_str_comparison_expression(
    field: str, value: str, settings: SearchSettings
) -> BinaryExpression:
    does_wild_cards_in_value_have_to_be_interpreted = False
    match settings.type:
        # Early return because not operator is not implement with tilde symbol.
        case SearchType.EXACT:
            if settings.is_case_sensitive:
                if settings.has_not_operator:
                    return col(field).is_not(other=value)
                else:
                    return col(field).is_(other=value)
            else:
                if settings.has_not_operator:
                    return func.lower(field) != func.lower(value)
                else:
                    return func.lower(field) == func.lower(value)
        case SearchType.LIKE:
            if settings.is_case_sensitive:
                result = col(field).regexp_match(pattern=f".*{value}.*")
            else:
                result = col(field).contains(
                    other=value,
                    autoescape=not does_wild_cards_in_value_have_to_be_interpreted,
                )
        case SearchType.STARTS_WITH:
            if settings.is_case_sensitive:
                result = col(field).regexp_match(pattern=f"^{value}.*")
            else:
                result = col(field).startswith(
                    other=value,
                    autoescape=not does_wild_cards_in_value_have_to_be_interpreted,
                )
        case SearchType.ENDS_WITH:
            if settings.is_case_sensitive:
                result = col(field).regexp_match(pattern=f"{value}$")
            else:
                result = col(field).endswith(
                    other=value,
                    autoescape=not does_wild_cards_in_value_have_to_be_interpreted,
                )
        case SearchType.REGEX:
            if settings.is_case_sensitive:
                result = col(field).regexp_match(pattern=value)
            else:
                raise NotImplementedError(
                    "regex string comparison case insensitive is not implemented"
                )
    if settings.has_not_operator:
        return ~result
    else:
        return result

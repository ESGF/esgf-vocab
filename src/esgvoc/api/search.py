from enum import Enum
from typing import Any, Iterable, MutableSequence, Sequence

import sqlalchemy as sa
from pydantic import BaseModel
from sqlalchemy import ColumnElement
from sqlalchemy.exc import OperationalError
from sqlalchemy.sql.expression import Select
from sqlalchemy.sql.selectable import ExecutableReturnsRows
from sqlmodel import Column, Field, Session, col

import esgvoc.core.constants as api_settings
import esgvoc.core.service as service
from esgvoc.api.data_descriptors import DATA_DESCRIPTOR_CLASS_MAPPING
from esgvoc.api.data_descriptors.data_descriptor import DataDescriptor, DataDescriptorSubSet
from esgvoc.core.db.models.project import PCollectionFTS5, PTerm, PTermFTS5
from esgvoc.core.db.models.universe import UDataDescriptorFTS5, UTerm, UTermFTS5
from esgvoc.core.exceptions import EsgvocDbError, EsgvocValueError


class ItemKind(Enum):
    DATA_DESCRIPTOR = "data_descriptor"
    """Corresponds to a data descriptor"""
    COLLECTION = "collection"
    """Corresponds to a collection"""
    TERM = "term"
    """Corresponds to a term"""


class Item(BaseModel):
    """An item from the universe or a project (data descriptor, collection or term)."""
    id: str
    """The id of the item."""
    kind: ItemKind = Field(sa_column=Column(sa.Enum(ItemKind)))
    """The kind of the item."""
    parent_id: str
    """The id of the parent of the item."""


def get_pydantic_class(data_descriptor_id_or_term_type: str) -> type[DataDescriptor]:
    if data_descriptor_id_or_term_type in DATA_DESCRIPTOR_CLASS_MAPPING:
        return DATA_DESCRIPTOR_CLASS_MAPPING[data_descriptor_id_or_term_type]
    else:
        raise EsgvocDbError(f"'{data_descriptor_id_or_term_type}' pydantic class not found")


def get_universe_session() -> Session:

    UNIVERSE_DB_CONNECTION = service.current_state.universe.db_connection
    if UNIVERSE_DB_CONNECTION:
        return UNIVERSE_DB_CONNECTION.create_session()
    else:
        raise EsgvocDbError('universe connection is not initialized')


def instantiate_pydantic_term(term: UTerm | PTerm,
                              selected_term_fields: Iterable[str] | None) -> DataDescriptor:
    type = term.specs[api_settings.TERM_TYPE_JSON_KEY]
    if selected_term_fields is not None:
        subset = DataDescriptorSubSet(id=term.id, type=type)
        for field in selected_term_fields:
            setattr(subset, field, term.specs.get(field, None))
        for field in DataDescriptorSubSet.MANDATORY_TERM_FIELDS:
            setattr(subset, field, term.specs.get(field, None))
        return subset
    else:
        term_class = get_pydantic_class(type)
        return term_class(**term.specs)


def instantiate_pydantic_terms(db_terms: Iterable[UTerm | PTerm],
                               list_to_populate: MutableSequence[DataDescriptor],
                               selected_term_fields: Iterable[str] | None) -> None:
    for db_term in db_terms:
        term = instantiate_pydantic_term(db_term, selected_term_fields)
        list_to_populate.append(term)


def process_expression(expression: str) -> str:
    """
    Allows only SQLite FST operators AND OR NOT and perform prefix search for single word expressions.
    """
    # 1. Remove single and double quotes.
    result = expression.replace('"', '')
    result = result.replace("'", '')

    # 2. Escape keywords.
    result = result.replace('NEAR', '"NEAR"')
    result = result.replace('+', '"+"')
    result = result.replace('-', '"-"')
    result = result.replace(':', '":"')
    result = result.replace('^', '"^"')
    result = result.replace('(', '"("')
    result = result.replace(')', '")"')
    result = result.replace(',', '","')

    # 3. Make single word request a prefix search.
    if not result.endswith('*'):
        tokens = result.split(sep=None)
        if len(tokens) == 1:
            result += '*'
    return result


def generate_matching_condition(cls: type[UTermFTS5] | type[UDataDescriptorFTS5] |
                                type[PTermFTS5] | type[PCollectionFTS5],
                                expression: str,
                                only_id: bool) -> ColumnElement[bool]:
    processed_expression = process_expression(expression)
    # TODO: fix this when specs will ba available in collections and Data descriptors.
    if cls is PTermFTS5 or cls is UTermFTS5:
        if only_id:
            result = col(cls.id).match(processed_expression)
        else:
            result = col(cls.specs).match(processed_expression)  # type: ignore
    else:
        result = col(cls.id).match(processed_expression)
    return result


def handle_rank_limit_offset(statement: Select, limit: int | None, offset: int | None) -> Select:
    statement = statement.order_by(sa.text('rank'))
    if limit and limit > 0:  # False if == 0 and is None ; True if != 0 and is not None.
        statement = statement.limit(limit)
    if offset and offset > 0:  # False if == 0 and is None ; True if != 0 and is not None.
        statement = statement.offset(offset)
    return statement


def execute_match_statement(expression: str, statement: ExecutableReturnsRows, session: Session) \
                                                                                        -> Sequence:
    try:
        raw_results = session.exec(statement)  # type: ignore
        # raw_results.all() returns a list of sqlalquemy rows.
        results = [result[0] for result in raw_results.all()]
        return results
    except OperationalError as e:
        raise EsgvocValueError(f"unable to interpret expression '{expression}'") from e


def execute_find_item_statements(session: Session,
                                 expression: str,
                                 first_statement: Select,
                                 second_statement: Select,
                                 limit: int | None,
                                 offset: int | None) -> list[Item]:
    try:
        # Items found are kind of tuple with an object, a kindness, a parent id and a rank.
        first_statement_found = session.exec(first_statement).all()  # type: ignore
        second_statement_found = session.exec(second_statement).all()  # type: ignore
        tmp_result: list[Any] = list()
        tmp_result.extend(first_statement_found)
        tmp_result.extend(second_statement_found)
        # According to https://sqlite.org/fts5.html#the_bm25_function,
        # "the better matches are assigned numerically lower scores."
        # Sort on the rank column (index 3).
        sorted_tmp_result = sorted(tmp_result, key=lambda r: r[3], reverse=False)
        if offset and offset > 0:  # False if == 0 and is None ; True if != 0 and is not None.
            start = offset
        else:
            start = 0
        if limit and limit > 0:  # False if == 0 and is None ; True if != 0 and is not None.
            stop = start + limit
            framed_tmp_result = sorted_tmp_result[start: stop]  # is OK if stop > len of the list.
        else:
            framed_tmp_result = sorted_tmp_result[start:]
        result = [Item(id=r[0], kind=r[1], parent_id=r[2]) for r in framed_tmp_result]
    except OperationalError as e:
        raise EsgvocValueError(f"unable to interpret expression '{expression}'") from e
    return result


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

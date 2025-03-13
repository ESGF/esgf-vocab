import logging
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects.sqlite import JSON
from sqlmodel import Column, Field, Relationship, SQLModel

import esgvoc.core.db.connection as db
from esgvoc.core.db.models.mixins import IdMixin, PkMixin, TermKind

_LOGGER = logging.getLogger("universe_db_creation")


class Universe(SQLModel, PkMixin, table=True):
    __tablename__ = "universes"
    git_hash: str
    data_descriptors: list["UDataDescriptor"] = Relationship(back_populates="universe")


class UDataDescriptor(SQLModel, PkMixin, IdMixin, table=True):
    __tablename__ = "data_descriptors"
    context: dict = Field(sa_column=sa.Column(JSON))
    universe_pk: int | None = Field(default=None, foreign_key="universes.pk")
    universe: Universe = Relationship(back_populates="data_descriptors")
    terms: list["UTerm"] = Relationship(back_populates="data_descriptor")
    term_kind: TermKind = Field(sa_column=Column(sa.Enum(TermKind)))


# Well, the following instructions are not data duplication. It is more building an index.
# Read: https://sqlite.org/fts5.html
class UDataDescriptorFTS5(SQLModel, PkMixin, IdMixin, table=True):
    __tablename__ = "data_descriptors_fts5"
    context: dict = Field(sa_column=sa.Column(JSON))
    universe_pk: int | None = Field(default=None, foreign_key="universes.pk")
    term_kind: TermKind = Field(sa_column=Column(sa.Enum(TermKind)))


class UTerm(SQLModel, PkMixin, IdMixin, table=True):
    __tablename__ = "uterms"
    specs: dict = Field(sa_column=sa.Column(JSON))
    kind: TermKind = Field(sa_column=Column(sa.Enum(TermKind)))
    data_descriptor_pk: int | None = Field(default=None, foreign_key="data_descriptors.pk")
    data_descriptor: UDataDescriptor = Relationship(back_populates="terms")


# Well, the following instructions are not data duplication. It is more building an index.
# Read: https://sqlite.org/fts5.html
class UTermFTS5(SQLModel, PkMixin, IdMixin, table=True):
    __tablename__ = "uterms_fts5"
    specs: dict = Field(sa_column=sa.Column(JSON))
    kind: TermKind = Field(sa_column=Column(sa.Enum(TermKind)))
    data_descriptor_pk: int | None = Field(default=None, foreign_key="data_descriptors.pk")


def universe_create_db(db_file_path: Path) -> None:
    try:
        connection = db.DBConnection(db_file_path)
    except Exception as e:
        msg = f'Unable to create SQLite file at {db_file_path}. Abort.'
        _LOGGER.fatal(msg)
        raise RuntimeError(msg) from e
    try:
        # Avoid creating project tables.
        tables_to_be_created = [SQLModel.metadata.tables['uterms'],
                                SQLModel.metadata.tables['data_descriptors'],
                                SQLModel.metadata.tables['universes']]
        SQLModel.metadata.create_all(connection.get_engine(), tables=tables_to_be_created)
    except Exception as e:
        msg = f'Unable to create tables in SQLite database at {db_file_path}. Abort.'
        _LOGGER.fatal(msg)
        raise RuntimeError(msg) from e
    try:
        with connection.create_session() as session:
            sql_query = 'CREATE VIRTUAL TABLE IF NOT EXISTS uterms_fts5 USING ' + \
                        'fts5(pk, id, specs, kind, data_descriptor_pk, content=uterms, content_rowid=pk);'
            session.exec(text(sql_query))
            session.commit()
    except Exception as e:
        msg = f'Unable to create table uterms_fts5 for {db_file_path}. Abort.'
        _LOGGER.fatal(msg)
        raise RuntimeError(msg) from e
    try:
        with connection.create_session() as session:
            sql_query = 'CREATE VIRTUAL TABLE IF NOT EXISTS pcollections_fts5 USING ' + \
                        'fts5(pk, id, universe_pk, context, ' + \
                        'term_kind, content=data_descriptors, content_rowid=pk);'
            session.exec(text(sql_query))
            session.commit()
    except Exception as e:
        msg = f'Unable to create table pterms_fts5 for {db_file_path}. Abort.'
        _LOGGER.fatal(msg)
        raise RuntimeError(msg) from e


if __name__ == "__main__":
    pass

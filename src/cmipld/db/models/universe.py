import logging
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.dialects.sqlite import JSON
from sqlmodel import Column, Field, Relationship, SQLModel

import cmipld.db as db
from cmipld.db.models.mixins import IdMixin, PkMixin, TermKind

_LOGGER = logging.getLogger("universe_db_creation")


class Universe(SQLModel, PkMixin, table=True):
    __tablename__ = "universes"
    git_hash: str
    data_descriptors: list["DataDescriptor"] = Relationship(back_populates="universe")


class DataDescriptor(SQLModel, PkMixin, IdMixin, table=True):
    __tablename__ = "data_descriptors"
    context: dict = Field(sa_column=sa.Column(JSON))
    universe_pk: int | None = Field(default=None, foreign_key="universes.pk")
    universe: Universe = Relationship(back_populates="data_descriptors")
    terms: list["UTerm"] = Relationship(back_populates="data_descriptor")
    term_kind: TermKind = Field(sa_column=Column(sa.Enum(TermKind)))


class UTerm(SQLModel, PkMixin, IdMixin, table=True):
    __tablename__ = "uterms"
    specs: dict = Field(sa_column=sa.Column(JSON))
    kind: TermKind = Field(sa_column=Column(sa.Enum(TermKind)))
    data_descriptor_pk: int | None = Field(
        default=None, foreign_key="data_descriptors.pk"
    )
    data_descriptor: DataDescriptor = Relationship(back_populates="terms")


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


if __name__ == "__main__":
    universe_create_db(db.UNIVERSE_DB_FILE_PATH)
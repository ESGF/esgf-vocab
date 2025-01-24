import logging
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.dialects.sqlite import JSON
from sqlmodel import Column, Field, Relationship, SQLModel

import esgvoc.core.db.connection as db
from esgvoc.core.db.models.mixins import IdMixin, PkMixin, TermKind
_LOGGER = logging.getLogger("project_db_creation")


class Project(SQLModel, PkMixin, IdMixin, table=True):
    __tablename__ = "projects"
    specs: dict = Field(sa_column=sa.Column(JSON))
    git_hash: str
    collections: list["Collection"] = Relationship(back_populates="project")


class Collection(SQLModel, PkMixin, IdMixin, table=True):
    __tablename__ = "collections"
    data_descriptor_id: str = Field(index=True)
    context: dict = Field(sa_column=sa.Column(JSON))
    project_pk: int | None = Field(default=None, foreign_key="projects.pk")
    project: Project = Relationship(back_populates="collections")
    terms: list["PTerm"] = Relationship(back_populates="collection")
    term_kind: TermKind = Field(sa_column=Column(sa.Enum(TermKind)))


class PTerm(SQLModel, PkMixin, IdMixin, table=True):
    __tablename__ = "pterms"
    specs: dict = Field(sa_column=sa.Column(JSON))
    kind: TermKind = Field(sa_column=Column(sa.Enum(TermKind)))
    collection_pk: int | None = Field(default=None, foreign_key="collections.pk")
    collection: Collection = Relationship(back_populates="terms")
    __table_args__ = (sa.Index(
             "drs_name_index", specs.sa_column["drs_name"]

         ),)

def project_create_db(db_file_path: Path):
    try:
        connection = db.DBConnection(db_file_path)
    except Exception as e:
        msg = f'Unable to create SQlite file at {db_file_path}. Abort.'
        _LOGGER.fatal(msg)
        raise RuntimeError(msg) from e
    try:
        tables_to_be_created = [SQLModel.metadata.tables['projects'],
                                SQLModel.metadata.tables['collections'],
                                SQLModel.metadata.tables['pterms']]
        SQLModel.metadata.create_all(connection.get_engine(), tables=tables_to_be_created)
    except Exception as e:
        msg = f'Unable to create tables in SQLite database at {db_file_path}. Abort.'
        _LOGGER.fatal(msg)
        raise RuntimeError(msg) from e


if __name__ == "__main__":
    pass
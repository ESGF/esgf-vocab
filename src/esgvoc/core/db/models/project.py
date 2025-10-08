import logging
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects.sqlite import JSON
from sqlmodel import Column, Field, Relationship, SQLModel

import esgvoc.core.db.connection as db
from esgvoc.core.db.models.mixins import IdMixin, PkMixin, TermKind
from esgvoc.core.exceptions import EsgvocDbError

_LOGGER = logging.getLogger(__name__)


class Project(SQLModel, PkMixin, IdMixin, table=True):
    __tablename__ = "projects"
    specs: dict = Field(sa_column=sa.Column(JSON))
    git_hash: str
    collections: list["PCollection"] = Relationship(back_populates="project")


class PCollection(SQLModel, PkMixin, IdMixin, table=True):
    __tablename__ = "pcollections"
    data_descriptor_id: str = Field(index=True)
    context: dict = Field(sa_column=sa.Column(JSON))
    project_pk: int | None = Field(default=None, foreign_key="projects.pk")
    project: Project = Relationship(back_populates="collections")
    terms: list["PTerm"] = Relationship(back_populates="collection")
    term_kind: TermKind = Field(sa_column=Column(sa.Enum(TermKind)))


# Well, the following instructions are not data duplication. It is more building an index.
# Read: https://sqlite.org/fts5.html
class PCollectionFTS5(SQLModel, PkMixin, IdMixin, table=True):
    __tablename__ = "pcollections_fts5"
    data_descriptor_id: str
    context: dict = Field(sa_column=sa.Column(JSON))
    project_pk: int | None = Field(default=None, foreign_key="projects.pk")
    term_kind: TermKind = Field(sa_column=Column(sa.Enum(TermKind)))


class PTerm(SQLModel, PkMixin, IdMixin, table=True):
    __tablename__ = "pterms"
    specs: dict = Field(sa_column=sa.Column(JSON))
    kind: TermKind = Field(sa_column=Column(sa.Enum(TermKind)))
    collection_pk: int | None = Field(default=None, foreign_key="pcollections.pk")
    collection: PCollection = Relationship(back_populates="terms")
    __table_args__ = (sa.Index("drs_name_index", specs.sa_column["drs_name"]), )  # type: ignore


# Well, the following instructions are not data duplication. It is more building an index.
# Read: https://sqlite.org/fts5.html
class PTermFTS5(SQLModel, PkMixin, IdMixin, table=True):
    __tablename__ = "pterms_fts5"
    specs: dict = Field(sa_column=sa.Column(JSON))
    kind: TermKind = Field(sa_column=Column(sa.Enum(TermKind)))
    collection_pk: int | None = Field(default=None, foreign_key="pcollections.pk")


def project_create_db(db_file_path: Path):
    try:
        connection = db.DBConnection(db_file_path)
    except Exception as e:
        msg = f'unable to create SQlite file at {db_file_path}'
        _LOGGER.fatal(msg)
        raise EsgvocDbError(msg) from e
    try:
        # Do not include pterms_fts5 table: it is build from a raw SQL query.
        tables_to_be_created = [SQLModel.metadata.tables['projects'],
                                SQLModel.metadata.tables['pcollections'],
                                SQLModel.metadata.tables['pterms']]
        SQLModel.metadata.create_all(connection.get_engine(), tables=tables_to_be_created)
    except Exception as e:
        msg = f'unable to create tables in SQLite database at {db_file_path}'
        _LOGGER.fatal(msg)
        raise EsgvocDbError(msg) from e
    try:
        with connection.create_session() as session:
            sql_query = "CREATE VIRTUAL TABLE IF NOT EXISTS pterms_fts5 USING " + \
                        "fts5(pk, id, specs, kind, collection_pk, content=pterms, content_rowid=pk, prefix=3);"
            session.exec(text(sql_query))  # type: ignore
            session.commit()
    except Exception as e:
        msg = f'unable to create table pterms_fts5 for {db_file_path}'
        _LOGGER.fatal(msg)
        raise EsgvocDbError(msg) from e
    try:
        with connection.create_session() as session:
            sql_query = 'CREATE VIRTUAL TABLE IF NOT EXISTS pcollections_fts5 USING ' + \
                        'fts5(pk, id, data_descriptor_id, context, project_pk, ' + \
                        'term_kind, content=pcollections, content_rowid=pk, prefix=3);'
            session.exec(text(sql_query))  # type: ignore
            session.commit()
    except Exception as e:
        msg = f'unable to create table pcollections_fts5 for {db_file_path}'
        _LOGGER.fatal(msg)
        raise EsgvocDbError(msg) from e


if __name__ == "__main__":
    pass

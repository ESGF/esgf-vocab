"""Focused tests for exact JSON-field lookups in project terms."""

from pathlib import Path

from esgvoc.api import projects
from esgvoc.core.db.connection import DBConnection
from esgvoc.core.db.models.mixins import TermKind
from esgvoc.core.db.models.project import (
    PCollection,
    Project,
    PTerm,
    project_create_db,
)


def make_project_database(path: Path, value: str) -> DBConnection:
    project_create_db(path)
    connection = DBConnection(path)
    with connection.create_session() as session:
        project = Project(
            id="cordex-cmip6",
            specs={},
            git_hash="test",
        )
        collection = PCollection(
            id="driving_source_id",
            data_descriptor_id="source",
            context={},
            project=project,
            term_kind=TermKind.PLAIN,
        )
        term = PTerm(
            id="example-model",
            specs={
                "id": "example-model",
                "type": "source",
                "driving_source": value,
            },
            kind=TermKind.PLAIN,
            collection=collection,
        )
        session.add(term)
        session.commit()
    return connection


def test_key_value_queries_escape_json_string_values(tmp_path: Path) -> None:
    value = 'Example (2026):\natmos: "configuration"\npath: C:\\model'
    connection = make_project_database(tmp_path / "project.db", value)

    with connection.create_session() as session:
        collection_matches = projects._get_terms_by_key_value_in_collection(
            "driving_source",
            value,
            "driving_source_id",
            session,
        )
        project_matches = projects._get_terms_by_key_value_in_project(
            "driving_source",
            value,
            session,
        )

    assert [term.id for term in collection_matches] == ["example-model"]
    assert [term.id for term in project_matches] == ["example-model"]

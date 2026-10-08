"""
Duplicate terms and term file names.

Rules checked at build time:
- a term id is unique within a project collection (it may appear in other collections);
- term file names are lowercase;
- any ingestion error fails the build.
In the universe, a duplicate id or drs_name is only a warning.

At query time, a database that still holds a duplicate (built by an older esgvoc)
raises EsgvocDbError instead of SQLAlchemy's MultipleResultsFound.
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
from pathlib import Path

import pytest
from sqlalchemy.exc import IntegrityError

import esgvoc.api.projects as projects
from esgvoc.admin.builder import DBBuilder
from esgvoc.core.db.connection import DBConnection
from esgvoc.core.db.models.mixins import TermKind
from esgvoc.core.db.models.project import PCollection, Project, PTerm, project_create_db
from esgvoc.core.exceptions import EsgvocDbError, EsgvocValueError

_UNIVERSE_CONTEXT = {
    "@context": {
        "@base": "https://esgvoc.ipsl.fr/resource/universe/activity/",
        "@vocab": "http://schema.org/",
        "id": "@id",
        "type": "@type",
        "description": {"@id": "https://schema.org/description"},
        "drs_name": {"@id": "acronym"},
    }
}

_COLLECTION_CONTEXT = {
    "@context": {
        "id": "@id",
        "type": "@type",
        "@base": "https://esgvoc.ipsl.fr/resource/universe/activity/",
        "activity": "https://esgvoc.ipsl.fr/resource/universe/activity",
    }
}


def _write_json(path: Path, content: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content))


def _universe_term(term_id: str, drs_name: str) -> dict:
    return {"@context": "000_context.jsonld", "id": term_id, "type": "activity", "drs_name": drs_name}


def _project_term(term_id: str) -> dict:
    return {"@context": "000_context.jsonld", "id": term_id, "type": "activity"}


@pytest.fixture
def repos(tmp_path) -> tuple[Path, Path]:
    """A universe with one data descriptor and a project with two collections linked to it."""
    universe = tmp_path / "universe"
    _write_json(universe / "activity" / "000_context.jsonld", _UNIVERSE_CONTEXT)
    _write_json(universe / "activity" / "cmip.json", _universe_term("cmip", "CMIP"))
    _write_json(universe / "activity" / "scenariomip.json", _universe_term("scenariomip", "ScenarioMIP"))

    project = tmp_path / "project"
    project.mkdir()
    (project / "project_specs.yaml").write_text("project_id: testproj\n")
    for collection in ("activity_id", "parent_activity_id"):
        _write_json(project / collection / "000_context.jsonld", _COLLECTION_CONTEXT)
        _write_json(project / collection / "cmip.json", _project_term("cmip"))
    _write_json(project / "activity_id" / "scenariomip.json", _project_term("scenariomip"))
    return universe, project


def _build(repos: tuple[Path, Path], tmp_path: Path) -> Path:
    universe, project = repos
    output = tmp_path / "out.db"
    DBBuilder(work_dir=tmp_path / "work", verbose=False).build_dev(project, universe, output)
    return output


def _drop_unique_constraint(db_path: Path) -> None:
    """Rebuild pterms without its unique constraint, like a DB built by esgvoc <= 6.2."""
    conn = sqlite3.connect(str(db_path))
    sql = conn.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'pterms'").fetchone()[0]
    legacy_sql = re.sub(r",\s*CONSTRAINT pterm_id_unique_in_collection UNIQUE \(collection_pk, id\)", "", sql)
    assert legacy_sql != sql
    conn.executescript(
        "ALTER TABLE pterms RENAME TO pterms_old; "  # noqa: S608
        + legacy_sql
        + "; INSERT INTO pterms SELECT * FROM pterms_old; DROP TABLE pterms_old;"
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Build time
# ---------------------------------------------------------------------------


class TestBuildChecks:
    def test_same_id_in_two_collections_builds(self, repos, tmp_path):
        output = _build(repos, tmp_path)
        rows = sqlite3.connect(str(output)).execute("SELECT count(*) FROM pterms WHERE id = 'cmip'").fetchone()
        assert rows[0] == 2

    def test_duplicate_id_in_collection_fails_build(self, repos, tmp_path, caplog):
        _, project = repos
        _write_json(project / "activity_id" / "cmip_copy.json", _project_term("cmip"))
        with pytest.raises(EsgvocDbError, match=r"1 term\(s\) failed to ingest"):
            _build(repos, tmp_path)
        assert "duplicate term id 'cmip', already defined by cmip.json" in caplog.text

    def test_mixed_case_project_file_name_fails_build(self, repos, tmp_path, caplog):
        _, project = repos
        (project / "activity_id" / "scenariomip.json").rename(project / "activity_id" / "ScenarioMIP.json")
        with pytest.raises(EsgvocDbError, match=r"project: 1"):
            _build(repos, tmp_path)
        assert "term file names must be lowercase" in caplog.text

    def test_mixed_case_universe_file_name_fails_build(self, repos, tmp_path, caplog):
        universe, _ = repos
        _write_json(universe / "activity" / "DAMIP.json", _universe_term("damip", "DAMIP"))
        with pytest.raises(EsgvocDbError, match=r"universe: 1"):
            _build(repos, tmp_path)
        assert "term file names must be lowercase" in caplog.text

    def test_duplicate_id_in_universe_only_warns(self, repos, tmp_path, caplog):
        universe, _ = repos
        _write_json(universe / "activity" / "firemip.json", _universe_term("scenariomip", "FireMIP"))
        with caplog.at_level(logging.WARNING, logger="esgvoc"):
            _build(repos, tmp_path)
        assert "term id 'scenariomip' of scenariomip.json is already defined by firemip.json" in caplog.text

    def test_duplicate_drs_name_only_warns(self, repos, tmp_path, caplog):
        universe, project = repos
        _write_json(universe / "activity" / "cmip_bis.json", _universe_term("cmip_bis", "CMIP"))
        _write_json(project / "activity_id" / "cmip_bis.json", _project_term("cmip_bis"))
        with caplog.at_level(logging.WARNING, logger="esgvoc"):
            _build(repos, tmp_path)
        assert "drs_name 'CMIP' of cmip_bis.json is already used by cmip.json in data descriptor" in caplog.text
        assert "drs_name 'CMIP' of cmip_bis.json is already used by cmip.json in collection" in caplog.text

    def test_unique_constraint_on_project_terms(self, tmp_path):
        db_path = tmp_path / "project.db"
        project_create_db(db_path)
        with DBConnection(db_path).create_session() as session:
            project = Project(id="testproj", specs={}, git_hash="x")
            collection = PCollection(
                id="activity_id", context={}, project=project, data_descriptor_id="activity", term_kind=TermKind.PLAIN
            )
            for _ in range(2):
                session.add(PTerm(id="cmip", specs={}, collection=collection, kind=TermKind.PLAIN))
            with pytest.raises(IntegrityError):
                session.commit()


# ---------------------------------------------------------------------------
# Query time
# ---------------------------------------------------------------------------


@pytest.fixture
def use_db(monkeypatch):
    def _use(db_path: Path) -> None:
        monkeypatch.setattr(projects, "_get_project_connection", lambda *args, **kwargs: DBConnection(db_path))

    return _use


class TestQueries:
    def test_duplicate_term_in_legacy_db_raises_esgvoc_error(self, repos, tmp_path, use_db):
        output = _build(repos, tmp_path)
        _drop_unique_constraint(output)
        conn = sqlite3.connect(str(output))
        conn.execute(
            "INSERT INTO pterms (id, specs, kind, collection_pk) "
            "SELECT id, specs, kind, collection_pk FROM pterms WHERE id = 'scenariomip'"
        )
        conn.commit()
        conn.close()
        use_db(output)
        with pytest.raises(
            EsgvocDbError,
            match="duplicate term 'scenariomip' in collection 'activity_id' of project 'testproj'",
        ):
            projects.get_term_in_collection("testproj", "activity_id", "scenariomip")

    def test_universe_term_used_by_two_collections(self, repos, tmp_path, use_db):
        use_db(_build(repos, tmp_path))
        found = projects.get_terms_from_universe_term_id_in_project("testproj", "activity", "cmip")
        assert sorted(collection_id for collection_id, _ in found) == ["activity_id", "parent_activity_id"]
        assert all(term.id == "cmip" for _, term in found)

    def test_deprecated_lookup_single_match(self, repos, tmp_path, use_db):
        use_db(_build(repos, tmp_path))
        with pytest.warns(DeprecationWarning):
            found = projects.get_term_from_universe_term_id_in_project("testproj", "activity", "scenariomip")
        assert found is not None
        assert found[0] == "activity_id"
        assert found[1].id == "scenariomip"

    def test_deprecated_lookup_several_matches_raises(self, repos, tmp_path, use_db):
        use_db(_build(repos, tmp_path))
        with pytest.warns(DeprecationWarning), pytest.raises(EsgvocValueError, match="several collections"):
            projects.get_term_from_universe_term_id_in_project("testproj", "activity", "cmip")

    def test_all_projects_lookup_returns_every_match(self, repos, tmp_path, use_db, monkeypatch):
        use_db(_build(repos, tmp_path))
        monkeypatch.setattr(projects, "get_all_projects", lambda: ["testproj"])
        found = projects.get_term_from_universe_term_id_in_all_projects("activity", "cmip")
        assert sorted((p, c) for p, c, _ in found) == [
            ("testproj", "activity_id"),
            ("testproj", "parent_activity_id"),
        ]

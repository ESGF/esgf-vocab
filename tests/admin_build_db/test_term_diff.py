"""
Term-level diff of project DBs (``esgvoc admin diff --terms``).

The main use: compare a published project DB with a rebuild of the same
project sources against a newer universe, to see whether the universe
release changed the project's terms (project terms embed the universe data
they link to).
"""

from __future__ import annotations

import json
import shutil
import sqlite3
from pathlib import Path

import pytest
from typer.testing import CliRunner

from esgvoc.admin.builder import DBBuilder
from esgvoc.admin.cli import app as admin_app
from esgvoc.admin.term_diff import diff_project_terms

runner = CliRunner()

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


def _universe_term(term_id: str, drs_name: str, description: str = "") -> dict:
    return {
        "@context": "000_context.jsonld",
        "id": term_id,
        "type": "activity",
        "drs_name": drs_name,
        "description": description,
    }


def _project_term(term_id: str) -> dict:
    return {"@context": "000_context.jsonld", "id": term_id, "type": "activity"}


@pytest.fixture
def repos(tmp_path) -> tuple[Path, Path]:
    """A universe with one data descriptor and a project with one collection linked to it."""
    universe = tmp_path / "universe"
    _write_json(universe / "activity" / "000_context.jsonld", _UNIVERSE_CONTEXT)
    _write_json(universe / "activity" / "cmip.json", _universe_term("cmip", "CMIP", "CMIP DECK"))
    _write_json(universe / "activity" / "scenariomip.json", _universe_term("scenariomip", "ScenarioMIP"))
    _write_json(universe / "activity" / "aerchemmip.json", _universe_term("aerchemmip", "AerChemMIP"))

    project = tmp_path / "project"
    project.mkdir()
    (project / "project_specs.yaml").write_text("project_id: testproj\n")
    _write_json(project / "activity_id" / "000_context.jsonld", _COLLECTION_CONTEXT)
    _write_json(project / "activity_id" / "cmip.json", _project_term("cmip"))
    _write_json(project / "activity_id" / "scenariomip.json", _project_term("scenariomip"))
    return universe, project


def _build(repos: tuple[Path, Path], output: Path) -> Path:
    universe, project = repos
    DBBuilder(work_dir=output.parent / f"work-{output.stem}", verbose=False).build_dev(project, universe, output)
    return output


@pytest.fixture
def baseline(repos, tmp_path) -> Path:
    return _build(repos, tmp_path / "baseline.db")


class TestDiffProjectTerms:
    def test_rebuild_of_same_sources_has_no_change(self, repos, baseline, tmp_path):
        rebuilt = _build(repos, tmp_path / "rebuilt.db")
        diff = diff_project_terms(baseline, rebuilt)
        assert not diff.has_changes
        assert diff.changelog() == []

    def test_linked_universe_term_change_modifies_project_term(self, repos, baseline, tmp_path):
        universe, _ = repos
        _write_json(universe / "activity" / "cmip.json", _universe_term("cmip", "CMIP", "New description"))
        updated = _build(repos, tmp_path / "updated.db")

        diff = diff_project_terms(baseline, updated)

        assert diff.has_changes
        [change] = diff.collections
        assert change.collection_id == "activity_id"
        assert [(m.term_id, m.fields) for m in change.modified] == [("cmip", ["description"])]
        assert diff.changelog() == ["- activity_id: 1 modified"]

    def test_unlinked_universe_term_change_has_no_change(self, repos, baseline, tmp_path):
        universe, _ = repos
        # aerchemmip is in the universe but not used by the project
        _write_json(universe / "activity" / "aerchemmip.json", _universe_term("aerchemmip", "AerChemMIP", "Changed"))
        _write_json(universe / "activity" / "damip.json", _universe_term("damip", "DAMIP"))
        updated = _build(repos, tmp_path / "updated.db")

        assert not diff_project_terms(baseline, updated).has_changes

    def test_project_terms_added_and_removed(self, repos, baseline, tmp_path):
        _, project = repos
        (project / "activity_id" / "scenariomip.json").unlink()
        _write_json(project / "activity_id" / "aerchemmip.json", _project_term("aerchemmip"))
        updated = _build(repos, tmp_path / "updated.db")

        diff = diff_project_terms(baseline, updated)

        [change] = diff.collections
        assert change.added == ["aerchemmip"]
        assert change.removed == ["scenariomip"]
        assert change.modified == []
        assert diff.changelog() == ["- activity_id: 1 added, 1 removed"]

    def test_new_and_removed_collections(self, repos, baseline, tmp_path):
        _, project = repos
        shutil.copytree(project / "activity_id", project / "parent_activity_id")
        updated = _build(repos, tmp_path / "updated.db")

        diff = diff_project_terms(baseline, updated)
        assert diff.collections_added == ["parent_activity_id"]
        assert diff.changelog() == ["- parent_activity_id: new collection"]

        reverse = diff_project_terms(updated, baseline)
        assert reverse.collections_removed == ["parent_activity_id"]
        assert reverse.changelog() == ["- parent_activity_id: collection removed"]


class TestDiffCli:
    def test_json_output_with_terms(self, repos, baseline, tmp_path):
        universe, _ = repos
        _write_json(universe / "activity" / "cmip.json", _universe_term("cmip", "CMIP", "New description"))
        updated = _build(repos, tmp_path / "updated.db")

        result = runner.invoke(admin_app, ["diff", str(baseline), str(updated), "--terms", "--format", "json"])

        assert result.exit_code == 0, result.output
        terms = json.loads(result.output)["terms"]
        assert terms["has_changes"] is True
        assert terms["collections"]["activity_id"]["modified"] == {"cmip": ["description"]}
        assert terms["changelog"] == ["- activity_id: 1 modified"]

    def test_json_output_without_terms_has_no_terms_key(self, baseline):
        result = runner.invoke(admin_app, ["diff", str(baseline), str(baseline), "--format", "json"])
        assert result.exit_code == 0, result.output
        assert "terms" not in json.loads(result.output)

    def test_text_output_no_change(self, baseline):
        result = runner.invoke(admin_app, ["diff", str(baseline), str(baseline), "--terms"])
        assert result.exit_code == 0, result.output
        assert "No project term changed." in result.output

    def test_terms_on_non_project_db_fails(self, baseline, tmp_path):
        not_a_project = tmp_path / "empty.db"
        sqlite3.connect(not_a_project).close()
        result = runner.invoke(admin_app, ["diff", str(not_a_project), str(baseline), "--terms"])
        assert result.exit_code == 1
        assert "Cannot compare the terms" in result.output

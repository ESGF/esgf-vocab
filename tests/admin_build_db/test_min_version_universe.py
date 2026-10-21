"""
A project DB embeds universe data, so its esgvoc_min_version is at least the
universe manifest's min_version.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

import esgvoc
from esgvoc.admin.builder import DBBuilder, _effective_min_version

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


def _write_manifest(repo: Path, project_id: str, min_version: str | None) -> None:
    esgvoc_section = f"esgvoc:\n  min_version: {min_version}\n" if min_version else ""
    (repo / "esgvoc_manifest.yaml").write_text(
        f"schema_version: '1'\nproject:\n  id: {project_id}\ncv_version: 1.0.0\nuniverse_version: 1.0.0\n"
        + esgvoc_section
    )


def _build(tmp_path: Path, universe_min: str | None, project_min: str | None, overrides=None) -> str:
    universe = tmp_path / "universe"
    _write_json(universe / "activity" / "000_context.jsonld", _UNIVERSE_CONTEXT)
    _write_json(
        universe / "activity" / "cmip.json",
        {"@context": "000_context.jsonld", "id": "cmip", "type": "activity", "drs_name": "CMIP"},
    )
    project = tmp_path / "project"
    project.mkdir()
    (project / "project_specs.yaml").write_text("project_id: testproj\n")
    _write_json(project / "activity_id" / "000_context.jsonld", _COLLECTION_CONTEXT)
    _write_json(
        project / "activity_id" / "cmip.json", {"@context": "000_context.jsonld", "id": "cmip", "type": "activity"}
    )
    if universe_min != "no manifest":
        _write_manifest(universe, "universe", universe_min)
    _write_manifest(project, "testproj", project_min)

    output = tmp_path / "out.db"
    DBBuilder(work_dir=tmp_path / "work", verbose=False).build_dev(
        project, universe, output, manifest_overrides=overrides
    )
    with sqlite3.connect(output) as conn:
        return conn.execute("SELECT value FROM _esgvoc_metadata WHERE key = 'esgvoc_min_version'").fetchone()[0]


@pytest.mark.parametrize(
    ("universe_min", "project_min", "expected"),
    [
        ("7.1.0", "7.0.0", "7.1.0"),  # the universe needs more than the project says
        ("7.1.0", "8.0.0", "8.0.0"),  # the project needs more
        ("7.1.0", None, "7.1.0"),  # no project min_version
        ("no manifest", "7.0.0", "7.0.0"),  # universe without a manifest
        (None, "7.0.0", "7.0.0"),  # universe manifest without min_version
    ],
)
def test_project_min_version_is_at_least_the_universe_one(tmp_path, universe_min, project_min, expected):
    assert _build(tmp_path, universe_min, project_min) == expected


def test_no_min_version_anywhere_uses_the_current_esgvoc_version(tmp_path):
    assert _build(tmp_path, None, None) == esgvoc.__version__


def test_override_is_raised_to_the_universe_min_version(tmp_path):
    assert _build(tmp_path, "7.1.0", "6.0.0", overrides={"esgvoc_min_version": "6.5.0"}) == "7.1.0"


def test_effective_min_version():
    assert _effective_min_version("7.0.0", "7.1.0") == "7.1.0"
    assert _effective_min_version("10.0.0", "9.9.9") == "10.0.0"
    assert _effective_min_version(None, "7.1.0") == "7.1.0"
    assert _effective_min_version("7.0.0", None) == "7.0.0"
    assert _effective_min_version(None, None) is None
    # a value that isn't a version is kept as given
    assert _effective_min_version("0.5", "7.1.0") == "0.5"

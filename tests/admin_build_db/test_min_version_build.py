"""
End-to-end esgvoc_min_version chain on a real build:
CV manifest (esgvoc.min_version) → admin build → DB metadata → activation / opening refused.

Requires WCRP-universe and CMIP6_CVs clones (see conftest.py).
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

import esgvoc
from esgvoc.admin.builder import DBBuilder
from esgvoc.admin.cli import app as admin_app
from esgvoc.api import projects
from esgvoc.cli.use import app as use_app
from esgvoc.core.exceptions import EsgvocIncompatibleDBError
from esgvoc.core.service.user_state import UserState

pytestmark = [pytest.mark.needs_real_repos, pytest.mark.slow]

runner = CliRunner()


def _metadata(db_path: Path) -> dict[str, str]:
    conn = sqlite3.connect(str(db_path))
    rows = dict(conn.execute("SELECT key, value FROM _esgvoc_metadata").fetchall())
    conn.close()
    return rows


def _build(tmp_path_factory, universe_repo_path, cmip6_cvs_repo_path, name: str, overrides: dict) -> Path:
    work = tmp_path_factory.mktemp(name)
    builder = DBBuilder(work_dir=work / "work", fail_on_missing_links=False)
    result = builder.build_dev(
        project_path=cmip6_cvs_repo_path,
        universe_path=universe_repo_path,
        output_path=work / "cmip6.db",
        manifest_overrides={"project_id": "cmip6", "cv_version": "test", **overrides},
    )
    return result.output_path


@pytest.fixture(scope="module")
def future_db(tmp_path_factory, local_repos_available, universe_repo_path, cmip6_cvs_repo_path) -> Path:
    """A real cmip6 DB whose CV requires a future esgvoc."""
    if not local_repos_available:
        pytest.skip("Local CV repos not found (see tests/admin_build_db/conftest.py).")
    return _build(
        tmp_path_factory, universe_repo_path, cmip6_cvs_repo_path, "future", {"esgvoc_min_version": "99.0.0"}
    )


@pytest.fixture(scope="module")
def manifest_db(tmp_path_factory, local_repos_available, universe_repo_path, cmip6_cvs_repo_path) -> Path:
    """A real cmip6 DB built with the min_version of the CV manifest."""
    if not local_repos_available:
        pytest.skip("Local CV repos not found (see tests/admin_build_db/conftest.py).")
    return _build(tmp_path_factory, universe_repo_path, cmip6_cvs_repo_path, "manifest", {})


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("ESGVOC_HOME", str(tmp_path))
    monkeypatch.delenv("ESGVOC_DB_DIR", raising=False)


class TestBuildEmbedsMinVersion:
    def test_override_is_embedded(self, future_db):
        assert _metadata(future_db)["esgvoc_min_version"] == "99.0.0"

    def test_manifest_value_is_embedded(self, manifest_db, cmip6_cvs_repo_path):
        manifest = yaml.safe_load((cmip6_cvs_repo_path / "esgvoc_manifest.yaml").read_text())
        expected = (manifest.get("esgvoc") or {}).get("min_version") or esgvoc.__version__
        assert _metadata(manifest_db)["esgvoc_min_version"] == str(expected)


class TestRealDbIsRefused:
    def test_admin_install_activate_refused(self, future_db):
        result = runner.invoke(admin_app, ["install", "cmip6", str(future_db), "--name", "future", "--activate"])
        assert result.exit_code == 1
        assert "cmip6@future requires esgvoc >= 99.0.0" in result.output
        assert UserState.load().get_active("cmip6") is None

    def test_use_refused(self, future_db):
        assert runner.invoke(admin_app, ["install", "cmip6", str(future_db), "--name", "future"]).exit_code == 0
        result = runner.invoke(use_app, ["cmip6@future"])
        assert result.exit_code == 1
        assert 'pip install --upgrade "esgvoc>=99.0.0"' in result.output

    def test_api_refuses_to_open(self, future_db):
        assert runner.invoke(admin_app, ["install", "cmip6", str(future_db), "--name", "future"]).exit_code == 0
        UserState.load().set_active("cmip6", "future", source="local")
        with pytest.raises(EsgvocIncompatibleDBError):
            projects.get_all_terms_in_collection("cmip6", "frequency")
        assert projects.get_all_projects() == []


class TestRealDbIsAccepted:
    def test_manifest_db_activates_and_opens(self, manifest_db):
        result = runner.invoke(admin_app, ["install", "cmip6", str(manifest_db), "--name", "current", "--activate"])
        assert result.exit_code == 0, result.output
        assert UserState.load().get_active("cmip6") == "current"
        assert projects.get_all_terms_in_collection("cmip6", "frequency")
        assert projects.get_all_projects() == ["cmip6"]

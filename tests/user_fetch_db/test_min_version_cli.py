"""
Tests for the esgvoc_min_version enforcement in the CLI commands that activate a project version:
`esgvoc use`, `esgvoc update`, `esgvoc import` and `esgvoc admin install --activate`.

Downloads are intercepted by patching DBFetcher — no real network calls.
"""
from __future__ import annotations

import json
import tarfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

import esgvoc
from esgvoc.admin.cli import app as admin_app
from esgvoc.cli.export_import import app as export_import_app
from esgvoc.cli.update import app as update_app
from esgvoc.cli.use import app as use_app
from esgvoc.core.db_snapshot import DBSnapshot
from esgvoc.core.service.user_state import UserState

from .conftest import make_db, sha256

runner = CliRunner()

INSTALLED = "6.2.0"
COMPATIBLE = "6.2.0"
INCOMPATIBLE = "7.0.0"


@pytest.fixture(autouse=True)
def installed_esgvoc(monkeypatch):
    monkeypatch.setattr(esgvoc, "__version__", INSTALLED)


def _install(project_id: str, version: str, min_version: str | None) -> Path:
    return make_db(UserState.db_path(project_id, version), project_id, version, min_version)


def _active(project_id: str) -> str | None:
    return UserState.load().get_active(project_id)


def _assert_refusal_message(output: str, project_id: str, version: str, min_version: str) -> None:
    assert f"{project_id}@{version} requires esgvoc >= {min_version}" in output
    assert f'pip install --upgrade "esgvoc>={min_version}"' in output


# ---------------------------------------------------------------------------
# Registry mock
# ---------------------------------------------------------------------------


def _registry(project_id: str, version: str, min_version: str | None, tmp_path: Path) -> MagicMock:
    """A DBFetcher mock whose registry serves *project_id*@*version* requiring *min_version*."""
    reference = make_db(tmp_path / "registry" / f"{project_id}-{version}.db", project_id, version, min_version)
    snapshot = DBSnapshot(
        project_id=project_id,
        version=version,
        download_url=f"https://example.com/{project_id}-{version}.db",
        checksum_sha256=sha256(reference),
        size_bytes=reference.stat().st_size,
        is_prerelease=False,
    )
    fetcher = MagicMock()
    fetcher.get_snapshot.return_value = snapshot

    def _download(snap, target, show_progress=True, **kw):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(reference.read_bytes())

    fetcher.download_db.side_effect = _download
    return fetcher


def _patched(fetcher: MagicMock):
    # DBFetcher is lazily imported inside the command bodies.
    return patch("esgvoc.core.db_fetcher.DBFetcher", return_value=fetcher)


# ---------------------------------------------------------------------------
# esgvoc use
# ---------------------------------------------------------------------------


class TestUseLocal:
    def test_refuses_incompatible(self):
        _install("cmip7", "future", INCOMPATIBLE)
        result = runner.invoke(use_app, ["cmip7@future"])
        assert result.exit_code == 1
        assert "Cannot activate cmip7@future" in result.output
        _assert_refusal_message(result.output, "cmip7", "future", INCOMPATIBLE)
        assert _active("cmip7") is None

    def test_keeps_previous_active(self):
        _install("cmip7", "current", COMPATIBLE)
        _install("cmip7", "future", INCOMPATIBLE)
        assert runner.invoke(use_app, ["cmip7@current"]).exit_code == 0
        assert runner.invoke(use_app, ["cmip7@future"]).exit_code == 1
        assert _active("cmip7") == "current"

    @pytest.mark.parametrize("min_version", [COMPATIBLE, "5.0.0", None])
    def test_activates_compatible(self, min_version):
        _install("cmip7", "current", min_version)
        result = runner.invoke(use_app, ["cmip7@current"])
        assert result.exit_code == 0, result.output
        assert _active("cmip7") == "current"

    def test_newest_installed_incompatible_is_refused(self):
        _install("cmip7", "v1.0.0", COMPATIBLE)
        _install("cmip7", "v2.0.0", INCOMPATIBLE)
        result = runner.invoke(use_app, ["cmip7"])
        assert result.exit_code == 1
        _assert_refusal_message(result.output, "cmip7", "v2.0.0", INCOMPATIBLE)

    def test_one_refused_project_does_not_activate_the_others_after_it(self):
        _install("cmip7", "future", INCOMPATIBLE)
        _install("cmip6", "current", COMPATIBLE)
        result = runner.invoke(use_app, ["cmip7@future", "cmip6@current"])
        assert result.exit_code == 1
        assert _active("cmip7") is None


class TestUseRegistry:
    def test_refuses_downloaded_incompatible(self, tmp_path):
        fetcher = _registry("cmip7", "v2.4.0", INCOMPATIBLE, tmp_path)
        with _patched(fetcher):
            result = runner.invoke(use_app, ["cmip7@v2.4.0"])
        assert result.exit_code == 1
        _assert_refusal_message(result.output, "cmip7", "v2.4.0", INCOMPATIBLE)
        assert _active("cmip7") is None
        # Kept on disk: usable as soon as esgvoc is upgraded.
        assert UserState.db_path("cmip7", "v2.4.0").exists()

    def test_refuses_already_downloaded_incompatible(self, tmp_path):
        fetcher = _registry("cmip7", "v2.4.0", INCOMPATIBLE, tmp_path)
        fetcher.download_db(fetcher.get_snapshot(), UserState.db_path("cmip7", "v2.4.0"))
        fetcher.download_db.reset_mock()
        with _patched(fetcher):
            result = runner.invoke(use_app, ["cmip7@v2.4.0"])
        assert result.exit_code == 1
        fetcher.download_db.assert_not_called()
        assert _active("cmip7") is None

    def test_activates_downloaded_compatible(self, tmp_path):
        fetcher = _registry("cmip7", "v2.4.0", COMPATIBLE, tmp_path)
        with _patched(fetcher):
            result = runner.invoke(use_app, ["cmip7@v2.4.0"])
        assert result.exit_code == 0, result.output
        assert _active("cmip7") == "v2.4.0"


# ---------------------------------------------------------------------------
# esgvoc update
# ---------------------------------------------------------------------------


class TestUpdate:
    def test_incompatible_is_installed_not_activated(self, tmp_path):
        _install("cmip7", "v2.3.0", COMPATIBLE)
        UserState.load().set_active("cmip7", "v2.3.0")
        with _patched(_registry("cmip7", "v2.4.0", INCOMPATIBLE, tmp_path)):
            result = runner.invoke(update_app, ["cmip7"])
        assert result.exit_code == 0, result.output
        assert "cmip7: v2.4.0 installed but not activated" in result.output
        _assert_refusal_message(result.output, "cmip7", "v2.4.0", INCOMPATIBLE)
        assert _active("cmip7") == "v2.3.0"
        assert UserState.db_path("cmip7", "v2.4.0").exists()

    def test_compatible_is_activated(self, tmp_path):
        _install("cmip7", "v2.3.0", COMPATIBLE)
        UserState.load().set_active("cmip7", "v2.3.0")
        with _patched(_registry("cmip7", "v2.4.0", COMPATIBLE, tmp_path)):
            result = runner.invoke(update_app, ["cmip7"])
        assert result.exit_code == 0, result.output
        assert _active("cmip7") == "v2.4.0"

    def test_no_activate_does_not_complain(self, tmp_path):
        _install("cmip7", "v2.3.0", COMPATIBLE)
        UserState.load().set_active("cmip7", "v2.3.0")
        with _patched(_registry("cmip7", "v2.4.0", INCOMPATIBLE, tmp_path)):
            result = runner.invoke(update_app, ["cmip7", "--no-activate"])
        assert result.exit_code == 0, result.output
        assert "installed (not activated)" in result.output
        assert "requires esgvoc" not in result.output
        assert _active("cmip7") == "v2.3.0"

    def test_other_projects_are_still_updated(self, tmp_path):
        for pid in ("cmip6", "cmip7"):
            _install(pid, "v1.0.0", COMPATIBLE)
            UserState.load().set_active(pid, "v1.0.0")
        fetchers = {
            "cmip6": _registry("cmip6", "v1.1.0", COMPATIBLE, tmp_path),
            "cmip7": _registry("cmip7", "v2.0.0", INCOMPATIBLE, tmp_path),
        }
        fetcher = MagicMock()
        fetcher.get_snapshot.side_effect = lambda pid, version: fetchers[pid].get_snapshot()
        fetcher.download_db.side_effect = lambda snap, target, **kw: fetchers[snap.project_id].download_db(
            snap, target
        )
        with _patched(fetcher):
            result = runner.invoke(update_app, [])
        assert result.exit_code == 0, result.output
        assert _active("cmip6") == "v1.1.0"
        assert _active("cmip7") == "v1.0.0"


# ---------------------------------------------------------------------------
# esgvoc import
# ---------------------------------------------------------------------------


def _bundle(tmp_path: Path, dbs: dict[tuple[str, str], str | None]) -> Path:
    """A bundle holding one DB per (project_id, version), all active, requiring the given min_version."""
    root = tmp_path / "bundle"
    projects_meta, active = [], {}
    for (project_id, version), min_version in dbs.items():
        filename = f"{project_id}-{version}.db"
        make_db(root / "dbs" / filename, project_id, version, min_version)
        projects_meta.append({"project_id": project_id, "version": version, "filename": filename})
        active[project_id] = version
    (root / "manifest.json").write_text(json.dumps({"esgvoc_bundle_version": "1", "projects": projects_meta}))
    (root / "state.json").write_text(json.dumps({"active_versions": active}))
    bundle = tmp_path / "bundle.tar.gz"
    with tarfile.open(bundle, "w:gz") as tar:
        for path in root.rglob("*"):
            tar.add(path, arcname=str(path.relative_to(root)))
    return bundle


class TestImport:
    def test_incompatible_is_imported_not_activated(self, tmp_path):
        bundle = _bundle(tmp_path, {("cmip7", "v2.4.0"): INCOMPATIBLE, ("cmip6", "v1.0.0"): COMPATIBLE})
        result = runner.invoke(export_import_app, ["import", str(bundle)])
        assert result.exit_code == 0, result.output
        assert "cmip7@v2.4.0 imported but not activated" in result.output
        _assert_refusal_message(result.output, "cmip7", "v2.4.0", INCOMPATIBLE)
        assert UserState.db_path("cmip7", "v2.4.0").exists()
        assert _active("cmip7") is None
        assert _active("cmip6") == "v1.0.0"

    def test_no_activate_does_not_complain(self, tmp_path):
        bundle = _bundle(tmp_path, {("cmip7", "v2.4.0"): INCOMPATIBLE})
        result = runner.invoke(export_import_app, ["import", str(bundle), "--no-activate"])
        assert result.exit_code == 0, result.output
        assert "requires esgvoc" not in result.output
        assert _active("cmip7") is None


# ---------------------------------------------------------------------------
# esgvoc admin install
# ---------------------------------------------------------------------------


class TestAdminInstall:
    def test_activate_refuses_incompatible(self, tmp_path):
        db = make_db(tmp_path / "cmip7.db", "cmip7", "dev", INCOMPATIBLE)
        result = runner.invoke(admin_app, ["install", "cmip7", str(db), "--name", "future", "--activate"])
        assert result.exit_code == 1
        assert "Not activated" in result.output
        _assert_refusal_message(result.output, "cmip7", "future", INCOMPATIBLE)
        assert UserState.db_path("cmip7", "future").exists()
        assert _active("cmip7") is None

    def test_activate_compatible(self, tmp_path):
        db = make_db(tmp_path / "cmip7.db", "cmip7", "dev", COMPATIBLE)
        result = runner.invoke(admin_app, ["install", "cmip7", str(db), "--name", "current", "--activate"])
        assert result.exit_code == 0, result.output
        assert _active("cmip7") == "current"

    def test_install_without_activate_accepts_incompatible(self, tmp_path):
        db = make_db(tmp_path / "cmip7.db", "cmip7", "dev", INCOMPATIBLE)
        result = runner.invoke(admin_app, ["install", "cmip7", str(db), "--name", "future"])
        assert result.exit_code == 0, result.output
        assert UserState.db_path("cmip7", "future").exists()

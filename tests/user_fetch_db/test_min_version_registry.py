"""
Tests for the esgvoc_min_version published in the registry index: release selection by
DBFetcher, refusal before download in `esgvoc use` / `esgvoc update`, and `esgvoc list-remote`.

A real DBFetcher is used with a fake registry index: only HTTP and downloads are stubbed.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

import esgvoc
from esgvoc.cli.update import app as update_app
from esgvoc.cli.use import app as use_app
from esgvoc.cli.versions import app as versions_app
from esgvoc.core.db_compat import newer_incompatible_release, snapshot_incompatibility_message
from esgvoc.core.db_fetcher import DBFetcher, EsgvocVersionNotFoundError
from esgvoc.core.db_snapshot import DBSnapshot
from esgvoc.core.service.user_state import UserState

from .conftest import make_db

runner = CliRunner()

INSTALLED = "6.2.0"
COMPATIBLE = "6.2.0"
INCOMPATIBLE = "7.0.0"


@pytest.fixture(autouse=True)
def installed_esgvoc(monkeypatch):
    monkeypatch.setattr(esgvoc, "__version__", INSTALLED)


def _release(version: str, min_version: str | None = None, is_prerelease: bool = False) -> dict:
    release = {
        "version": version,
        "url": f"https://example.com/{version}.db",
        "checksum_sha256": "0" * 64,
        "size_bytes": 1024,
        "is_prerelease": is_prerelease,
        "published_at": "2026-09-01T00:00:00Z",
    }
    if min_version is not None:
        release["esgvoc_min_version"] = min_version
    return release


def _fetcher(*releases: dict) -> DBFetcher:
    """A real DBFetcher reading *releases* as the registry index; downloads write a DB whose
    metadata matches the release."""
    fetcher = DBFetcher()
    response = MagicMock(status_code=200)
    response.json.return_value = {"releases": list(releases)}
    fetcher._session = MagicMock()
    fetcher._session.get.return_value = response

    def _download(snapshot: DBSnapshot, target: Path, show_progress: bool = True, **kw) -> Path:
        return make_db(target, snapshot.project_id, snapshot.version, snapshot.esgvoc_min_version)

    fetcher.download_db = MagicMock(side_effect=_download)
    return fetcher


def _patched(fetcher: DBFetcher):
    # DBFetcher is lazily imported inside the command bodies.
    return patch("esgvoc.core.db_fetcher.DBFetcher", return_value=fetcher)


def _active(project_id: str) -> str | None:
    return UserState.load().get_active(project_id)


# ---------------------------------------------------------------------------
# DBFetcher / db_compat
# ---------------------------------------------------------------------------


class TestIndexParsing:
    def test_min_version_is_read(self):
        snapshot = _fetcher(_release("v2.4.0", INCOMPATIBLE)).get_snapshot("cmip7", "v2.4.0")
        assert snapshot.esgvoc_min_version == INCOMPATIBLE

    def test_missing_min_version_is_none(self):
        assert _fetcher(_release("v2.4.0")).get_snapshot("cmip7", "v2.4.0").esgvoc_min_version is None


class TestLatestSelection:
    def test_newest_when_compatible(self):
        fetcher = _fetcher(_release("v2.4.0", COMPATIBLE), _release("v2.3.0", COMPATIBLE))
        assert fetcher.get_snapshot("cmip7", "latest").version == "v2.4.0"

    def test_skips_newer_incompatible(self):
        fetcher = _fetcher(
            _release("v2.5.0", INCOMPATIBLE), _release("v2.4.0", INCOMPATIBLE), _release("v2.3.0", COMPATIBLE)
        )
        assert fetcher.get_snapshot("cmip7", "latest").version == "v2.3.0"

    def test_releases_without_min_version_are_compatible(self):
        fetcher = _fetcher(_release("v2.5.0", INCOMPATIBLE), _release("v2.4.0"))
        assert fetcher.get_snapshot("cmip7", "latest").version == "v2.4.0"

    def test_newest_when_none_is_compatible(self):
        fetcher = _fetcher(_release("v2.5.0", INCOMPATIBLE), _release("v2.4.0", INCOMPATIBLE))
        assert fetcher.get_snapshot("cmip7", "latest").version == "v2.5.0"

    def test_compatible_only_false_returns_newest(self):
        fetcher = _fetcher(_release("v2.5.0", INCOMPATIBLE), _release("v2.4.0", COMPATIBLE))
        assert fetcher.get_snapshot("cmip7", "latest", compatible_only=False).version == "v2.5.0"

    def test_prereleases_are_not_selected(self):
        fetcher = _fetcher(_release("dev-latest", COMPATIBLE, is_prerelease=True), _release("v2.4.0", COMPATIBLE))
        assert fetcher.get_snapshot("cmip7", "latest").version == "v2.4.0"

    def test_no_stable_release_still_raises(self):
        fetcher = _fetcher(_release("dev-latest", COMPATIBLE, is_prerelease=True))
        with pytest.raises(EsgvocVersionNotFoundError):
            fetcher.get_snapshot("cmip7", "latest")

    @pytest.mark.parametrize("version", ["v2.5.0", "dev-latest"])
    def test_explicit_version_is_returned_even_if_incompatible(self, version):
        fetcher = _fetcher(
            _release("dev-latest", INCOMPATIBLE, is_prerelease=True),
            _release("v2.5.0", INCOMPATIBLE),
            _release("v2.4.0", COMPATIBLE),
        )
        assert fetcher.get_snapshot("cmip7", version).version == version


class TestCompatibilityOfSnapshots:
    def test_check_compatibility(self):
        fetcher = _fetcher(_release("v2.5.0", INCOMPATIBLE), _release("v2.4.0", COMPATIBLE))
        compatible, message = fetcher.check_compatibility(fetcher.get_snapshot("cmip7", "v2.5.0"))
        assert not compatible
        assert "cmip7@v2.5.0 requires esgvoc >= 7.0.0" in message
        assert fetcher.check_compatibility(fetcher.get_snapshot("cmip7", "v2.4.0")) == (True, "")

    def test_snapshot_message_is_the_db_message(self):
        snapshot = _fetcher(_release("v2.5.0", INCOMPATIBLE)).get_snapshot("cmip7", "v2.5.0")
        assert "esgvoc list-remote cmip7" in snapshot_incompatibility_message(snapshot)

    def test_newer_incompatible_release(self):
        fetcher = _fetcher(_release("v2.5.0", INCOMPATIBLE), _release("v2.4.0", COMPATIBLE))
        newer = newer_incompatible_release(fetcher, fetcher.get_snapshot("cmip7", "latest"))
        assert newer is not None and newer.version == "v2.5.0"

    @pytest.mark.parametrize(
        "releases",
        [
            [_release("v2.5.0", COMPATIBLE), _release("v2.4.0", COMPATIBLE)],  # newest is compatible
            [_release("v2.4.0", COMPATIBLE)],  # nothing newer
            [_release("v2.5.0", INCOMPATIBLE)],  # the snapshot is the newest one
        ],
    )
    def test_no_newer_incompatible_release(self, releases):
        fetcher = _fetcher(*releases)
        assert newer_incompatible_release(fetcher, fetcher.get_snapshot("cmip7", "latest")) is None


# ---------------------------------------------------------------------------
# esgvoc use
# ---------------------------------------------------------------------------


class TestUse:
    def test_explicit_incompatible_is_refused_before_download(self):
        fetcher = _fetcher(_release("v2.5.0", INCOMPATIBLE), _release("v2.4.0", COMPATIBLE))
        with _patched(fetcher):
            result = runner.invoke(use_app, ["cmip7@v2.5.0"])
        assert result.exit_code == 1
        assert "Cannot activate cmip7@v2.5.0" in result.output
        assert 'pip install --upgrade "esgvoc>=7.0.0"' in result.output
        fetcher.download_db.assert_not_called()
        assert not UserState.db_path("cmip7", "v2.5.0").exists()
        assert _active("cmip7") is None

    def test_latest_picks_newest_compatible_and_says_why(self):
        fetcher = _fetcher(_release("v2.5.0", INCOMPATIBLE), _release("v2.4.0", COMPATIBLE))
        with _patched(fetcher):
            result = runner.invoke(use_app, ["cmip7@latest"])
        assert result.exit_code == 0, result.output
        assert "cmip7@v2.5.0 is available but requires esgvoc >= 7.0.0: using v2.4.0" in result.output
        assert _active("cmip7") == "v2.4.0"

    def test_latest_without_newer_release_says_nothing(self):
        fetcher = _fetcher(_release("v2.4.0", COMPATIBLE))
        with _patched(fetcher):
            result = runner.invoke(use_app, ["cmip7@latest"])
        assert result.exit_code == 0, result.output
        assert "is available but requires" not in result.output
        assert _active("cmip7") == "v2.4.0"

    def test_latest_refused_when_nothing_is_compatible(self):
        fetcher = _fetcher(_release("v2.5.0", INCOMPATIBLE), _release("v2.4.0", INCOMPATIBLE))
        with _patched(fetcher):
            result = runner.invoke(use_app, ["cmip7@latest"])
        assert result.exit_code == 1
        assert "Cannot activate cmip7@v2.5.0" in result.output
        fetcher.download_db.assert_not_called()

    def test_registry_without_min_version_falls_back_to_the_db(self):
        # Old index entry, but the downloaded DB itself requires a more recent esgvoc.
        fetcher = _fetcher(_release("v2.5.0"))
        fetcher.download_db.side_effect = lambda snapshot, target, **kw: make_db(
            target, "cmip7", "v2.5.0", INCOMPATIBLE
        )
        with _patched(fetcher):
            result = runner.invoke(use_app, ["cmip7@v2.5.0"])
        assert result.exit_code == 1
        fetcher.download_db.assert_called_once()
        assert _active("cmip7") is None


# ---------------------------------------------------------------------------
# esgvoc update
# ---------------------------------------------------------------------------


def _installed(project_id: str, version: str) -> None:
    make_db(UserState.db_path(project_id, version), project_id, version, COMPATIBLE)
    UserState.load().set_active(project_id, version)


class TestUpdate:
    def test_updates_to_newest_compatible_and_says_why(self):
        _installed("cmip7", "v2.3.0")
        fetcher = _fetcher(_release("v2.5.0", INCOMPATIBLE), _release("v2.4.0", COMPATIBLE))
        with _patched(fetcher):
            result = runner.invoke(update_app, ["cmip7"])
        assert result.exit_code == 0, result.output
        assert "cmip7: v2.5.0 is available but requires esgvoc >= 7.0.0" in result.output
        assert _active("cmip7") == "v2.4.0"
        assert not UserState.db_path("cmip7", "v2.5.0").exists()

    def test_already_at_newest_compatible_still_says_why(self):
        _installed("cmip7", "v2.4.0")
        fetcher = _fetcher(_release("v2.5.0", INCOMPATIBLE), _release("v2.4.0", COMPATIBLE))
        with _patched(fetcher):
            result = runner.invoke(update_app, ["cmip7"])
        assert result.exit_code == 0, result.output
        assert "cmip7: v2.5.0 is available but requires esgvoc >= 7.0.0" in result.output
        assert "already at v2.4.0" in result.output
        fetcher.download_db.assert_not_called()

    def test_nothing_compatible_is_not_downloaded(self):
        _installed("cmip7", "v2.3.0")
        fetcher = _fetcher(_release("v2.5.0", INCOMPATIBLE))
        with _patched(fetcher):
            result = runner.invoke(update_app, ["cmip7"])
        assert result.exit_code == 0, result.output
        assert "cmip7: v2.5.0 not installed" in result.output
        assert 'pip install --upgrade "esgvoc>=7.0.0"' in result.output
        fetcher.download_db.assert_not_called()
        assert _active("cmip7") == "v2.3.0"

    def test_check_mode_reports_newest_compatible(self):
        _installed("cmip7", "v2.3.0")
        fetcher = _fetcher(_release("v2.5.0", INCOMPATIBLE), _release("v2.4.0", COMPATIBLE))
        with _patched(fetcher):
            result = runner.invoke(update_app, ["cmip7", "--check"])
        assert result.exit_code == 0, result.output
        assert "v2.3.0 → v2.4.0" in result.output
        fetcher.download_db.assert_not_called()

    def test_prerelease_incompatible_is_not_downloaded(self):
        _installed("cmip7", "v2.3.0")
        fetcher = _fetcher(_release("dev-latest", INCOMPATIBLE, is_prerelease=True), _release("v2.3.0", COMPATIBLE))
        with _patched(fetcher):
            result = runner.invoke(update_app, ["cmip7", "--pre"])
        assert result.exit_code == 0, result.output
        assert "cmip7: dev-latest not installed" in result.output
        fetcher.download_db.assert_not_called()


# ---------------------------------------------------------------------------
# esgvoc list-remote
# ---------------------------------------------------------------------------


class TestListRemote:
    def test_shows_min_version_and_compat(self):
        fetcher = _fetcher(_release("v2.5.0", INCOMPATIBLE), _release("v2.4.0", COMPATIBLE), _release("v2.3.0"))
        with _patched(fetcher):
            result = runner.invoke(versions_app, ["list-remote", "cmip7"])
        assert result.exit_code == 0, result.output
        lines = {line.split("│")[1].strip(): line for line in result.output.splitlines() if "│ v2." in line}
        assert INCOMPATIBLE in lines["v2.5.0"] and "✗" in lines["v2.5.0"]
        assert COMPATIBLE in lines["v2.4.0"] and "✓" in lines["v2.4.0"]
        assert "✓" in lines["v2.3.0"]

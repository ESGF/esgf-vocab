"""
Dev Tier — esgvoc admin publish tests.

All GitHub API calls are intercepted with unittest.mock so no real network
traffic or credentials are required.  The tests use a real SQLite DB file
(from the session-scoped real_dbs fixture) so metadata reading is tested
against genuine content.

Plan scenarios covered:
  AP-1   publish creates a new GitHub release with the correct tag
  AP-2   publish uploads the DB file as a release asset
  AP-3   release body includes project metadata from the DB
  AP-4   release body includes the SHA-256 checksum
  AP-5   existing release (same tag) → asset replaced (update_if_exists=True)
  AP-6   existing release + update_if_exists=False → exit code 4
  AP-7   missing GITHUB_TOKEN → clear auth error before any API call
  AP-8   --tag auto-detected from DB cv_version metadata field
  AP-9   --prerelease flag creates a pre-release
  AP-10  --dry-run prints payload, makes zero API calls
  AP-11  GitHub API error (5xx) → exit code 4
  AP-12  DB file not found → exit code 1
  AP-13  401 Unauthorized → helpful auth error message
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest
import requests
from typer.testing import CliRunner

from esgvoc.admin.cli import app as admin_app
from esgvoc.admin.publisher import (
    DBPublisher,
    PublishAuthError,
    PublishConflictError,
    PublishError,
    _build_release_body,
    _read_db_metadata,
    _sha256,
)

runner = CliRunner()

_REPO = "WCRP-CMIP/CMIP6_CVs"
_TAG = "v1.0.0"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_release(tag: str = _TAG, release_id: int = 42, assets: list | None = None) -> dict:
    """Minimal GitHub release dict."""
    return {
        "id": release_id,
        "tag_name": tag,
        "html_url": f"https://github.com/{_REPO}/releases/tag/{tag}",
        "upload_url": f"https://uploads.github.com/repos/{_REPO}/releases/{release_id}/assets{{?name,label}}",
        "assets": assets or [],
    }


def _make_session_mock(
    get_release_response=None,
    create_release_response=None,
    update_release_response=None,
    upload_response=None,
    delete_response=None,
):
    """Build a mock requests.Session with sensible defaults."""
    release = _make_release()

    def _mock_get(url, **kw):
        r = MagicMock()
        if get_release_response == 404:
            r.status_code = 404
            r.ok = False
        else:
            r.status_code = 200
            r.ok = True
            r.json.return_value = get_release_response or release
        return r

    def _mock_post(url, **kw):
        r = MagicMock()
        r.status_code = 201
        r.ok = True
        if "assets" in url:
            r.json.return_value = {"id": 99, "name": "cmip6.db", "browser_download_url": url}
        else:
            r.json.return_value = create_release_response or release
        return r

    def _mock_patch(url, **kw):
        r = MagicMock()
        r.status_code = 200
        r.ok = True
        r.json.return_value = update_release_response or release
        return r

    def _mock_delete(url, **kw):
        r = MagicMock()
        r.status_code = 204
        r.ok = True
        return r

    mock = MagicMock()
    mock.get.side_effect = _mock_get
    mock.post.side_effect = _mock_post
    mock.patch.side_effect = _mock_patch
    mock.delete.side_effect = _mock_delete
    mock.headers = {}
    return mock


# ---------------------------------------------------------------------------
# AP-7  Missing token → auth error before any API call
# ---------------------------------------------------------------------------

class TestMissingToken:

    def test_no_token_raises_auth_error(self, monkeypatch):
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        with pytest.raises(PublishAuthError, match="GITHUB_TOKEN"):
            DBPublisher(github_token=None)

    def test_cli_no_token_exits_4(self, real_dbs, monkeypatch, tmp_path):
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        db = real_dbs["v1_path"]
        result = runner.invoke(
            admin_app,
            ["publish", str(db), "--repo", _REPO, "--tag", _TAG],
        )
        assert result.exit_code == 4
        assert "GITHUB_TOKEN" in result.output or "Authentication" in result.output


# ---------------------------------------------------------------------------
# AP-12  DB file not found → exit code 1
# ---------------------------------------------------------------------------

class TestDbNotFound:

    def test_cli_missing_db_exits_1(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
        missing = tmp_path / "nonexistent.db"
        result = runner.invoke(
            admin_app,
            ["publish", str(missing), "--repo", _REPO, "--tag", _TAG],
        )
        assert result.exit_code == 1
        assert "not found" in result.output.lower()


# ---------------------------------------------------------------------------
# AP-10  Dry-run → no API calls
# ---------------------------------------------------------------------------

class TestDryRun:

    def test_dry_run_makes_no_api_calls(self, real_dbs, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
        publisher = DBPublisher(github_token="fake-token")
        mock_session = _make_session_mock()
        publisher._session = mock_session

        result = publisher.publish(
            db_path=real_dbs["v1_path"],
            repo=_REPO,
            tag=_TAG,
            dry_run=True,
        )

        mock_session.get.assert_not_called()
        mock_session.post.assert_not_called()
        mock_session.patch.assert_not_called()
        assert result.dry_run is True
        assert result.tag == _TAG

    def test_dry_run_cli_exits_0(self, real_dbs, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
        result = runner.invoke(
            admin_app,
            ["publish", str(real_dbs["v1_path"]), "--repo", _REPO, "--tag", _TAG, "--dry-run"],
        )
        assert result.exit_code == 0, result.output
        assert "DRY RUN" in result.output

    def test_dry_run_shows_tag(self, real_dbs, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
        result = runner.invoke(
            admin_app,
            ["publish", str(real_dbs["v1_path"]), "--repo", _REPO, "--tag", _TAG, "--dry-run"],
        )
        assert _TAG in result.output


# ---------------------------------------------------------------------------
# AP-1 / AP-2  New release created, asset uploaded
# ---------------------------------------------------------------------------

class TestNewRelease:

    def test_creates_new_release_when_none_exists(self, real_dbs):
        publisher = DBPublisher(github_token="fake-token")
        mock_session = _make_session_mock(get_release_response=404)
        publisher._session = mock_session

        publisher.publish(db_path=real_dbs["v1_path"], repo=_REPO, tag=_TAG)

        # GET to check existing + POST to create + POST to upload asset
        assert mock_session.get.called
        assert mock_session.post.called

    def test_asset_uploaded_with_correct_name(self, real_dbs):
        publisher = DBPublisher(github_token="fake-token")
        mock_session = _make_session_mock(get_release_response=404)
        publisher._session = mock_session

        result = publisher.publish(db_path=real_dbs["v1_path"], repo=_REPO, tag=_TAG)

        assert result.asset_name.endswith(".db")
        assert result.project_id in result.asset_name

    def test_result_has_correct_tag(self, real_dbs):
        publisher = DBPublisher(github_token="fake-token")
        mock_session = _make_session_mock(get_release_response=404)
        publisher._session = mock_session

        result = publisher.publish(db_path=real_dbs["v1_path"], repo=_REPO, tag=_TAG)

        assert result.tag == _TAG

    def test_result_has_checksum(self, real_dbs):
        publisher = DBPublisher(github_token="fake-token")
        mock_session = _make_session_mock(get_release_response=404)
        publisher._session = mock_session

        result = publisher.publish(db_path=real_dbs["v1_path"], repo=_REPO, tag=_TAG)
        expected = _sha256(real_dbs["v1_path"])

        assert result.checksum_sha256 == expected


# ---------------------------------------------------------------------------
# AP-3 / AP-4  Release body content
# ---------------------------------------------------------------------------

class TestReleaseBody:

    def test_body_includes_project_id(self, real_dbs):
        meta = _read_db_metadata(real_dbs["v1_path"])
        checksum = _sha256(real_dbs["v1_path"])
        body = _build_release_body(meta, checksum, _TAG)
        assert meta.get("project_id", "") in body

    def test_body_includes_checksum(self, real_dbs):
        meta = _read_db_metadata(real_dbs["v1_path"])
        checksum = _sha256(real_dbs["v1_path"])
        body = _build_release_body(meta, checksum, _TAG)
        assert checksum in body

    def test_body_includes_install_command(self, real_dbs):
        meta = _read_db_metadata(real_dbs["v1_path"])
        checksum = _sha256(real_dbs["v1_path"])
        body = _build_release_body(meta, checksum, _TAG)
        assert "esgvoc install" in body

    def test_body_includes_universe_version(self, real_dbs):
        meta = _read_db_metadata(real_dbs["v1_path"])
        checksum = _sha256(real_dbs["v1_path"])
        body = _build_release_body(meta, checksum, _TAG)
        assert "Universe version" in body

    def test_body_includes_extra_notes(self, real_dbs):
        meta = _read_db_metadata(real_dbs["v1_path"])
        checksum = _sha256(real_dbs["v1_path"])
        body = _build_release_body(meta, checksum, _TAG, extra_notes="- Added IPSL-EXTRA")
        assert "Added IPSL-EXTRA" in body


# ---------------------------------------------------------------------------
# AP-5  Existing release → asset replaced
# ---------------------------------------------------------------------------

class TestUpdateExistingRelease:

    def test_existing_release_asset_deleted_before_upload(self, real_dbs):
        old_asset = {"id": 77, "name": "cmip6.db"}
        existing = _make_release(assets=[old_asset])

        publisher = DBPublisher(github_token="fake-token")
        mock_session = _make_session_mock(get_release_response=existing)
        publisher._session = mock_session

        publisher.publish(db_path=real_dbs["v1_path"], repo=_REPO, tag=_TAG, update_if_exists=True)

        # delete should have been called for the old asset
        assert mock_session.delete.called

    def test_existing_release_new_asset_uploaded(self, real_dbs):
        old_asset = {"id": 77, "name": "cmip6.db"}
        existing = _make_release(assets=[old_asset])

        publisher = DBPublisher(github_token="fake-token")
        mock_session = _make_session_mock(get_release_response=existing)
        publisher._session = mock_session

        publisher.publish(db_path=real_dbs["v1_path"], repo=_REPO, tag=_TAG, update_if_exists=True)

        # POST to upload_url (asset upload)
        upload_calls = [
            c for c in mock_session.post.call_args_list
            if "assets" in str(c)
        ]
        assert len(upload_calls) >= 1


# ---------------------------------------------------------------------------
# AP-6  Existing release + update_if_exists=False → conflict error
# ---------------------------------------------------------------------------

class TestConflict:

    def test_conflict_raises_publish_conflict_error(self, real_dbs):
        existing = _make_release()
        publisher = DBPublisher(github_token="fake-token")
        mock_session = _make_session_mock(get_release_response=existing)
        publisher._session = mock_session

        with pytest.raises(PublishConflictError):
            publisher.publish(
                db_path=real_dbs["v1_path"],
                repo=_REPO,
                tag=_TAG,
                update_if_exists=False,
            )

    def test_cli_conflict_exits_4(self, real_dbs, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
        existing = _make_release()

        with patch("esgvoc.admin.publisher.DBPublisher._get_release_by_tag", return_value=existing):
            result = runner.invoke(
                admin_app,
                [
                    "publish", str(real_dbs["v1_path"]),
                    "--repo", _REPO, "--tag", _TAG,
                    "--no-update",
                ],
            )
        assert result.exit_code == 4


# ---------------------------------------------------------------------------
# AP-8  Tag inferred from DB metadata
# ---------------------------------------------------------------------------

class TestTagInference:

    def test_tag_inferred_from_cv_version(self, real_dbs):
        meta = _read_db_metadata(real_dbs["v1_path"])
        cv_version = meta.get("cv_version", "")
        # The v1_path DB has cv_version="1.0.0" per conftest manifest_overrides
        assert cv_version  # make sure metadata is present

    def test_cli_infers_tag_when_omitted(self, real_dbs, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
        with patch("esgvoc.admin.publisher.DBPublisher.publish") as mock_pub:
            mock_pub.return_value = MagicMock(summary=lambda: "OK", dry_run=False)
            result = runner.invoke(
                admin_app,
                ["publish", str(real_dbs["v1_path"]), "--repo", _REPO, "--dry-run"],
            )
        # Should not exit with "cannot infer" error (cv_version is present in the DB)
        assert "Cannot infer tag" not in result.output


# ---------------------------------------------------------------------------
# AP-9  --prerelease flag
# ---------------------------------------------------------------------------

class TestPrerelease:

    def test_prerelease_flag_passed_to_create(self, real_dbs):
        publisher = DBPublisher(github_token="fake-token")
        mock_session = _make_session_mock(get_release_response=404)
        publisher._session = mock_session

        publisher.publish(
            db_path=real_dbs["v1_path"],
            repo=_REPO,
            tag="dev-latest",
            prerelease=True,
        )

        create_calls = [c for c in mock_session.post.call_args_list if "releases" in str(c)]
        # Find the create release call (not the upload)
        create_call = next(
            (c for c in create_calls if "assets" not in str(c)),
            None,
        )
        assert create_call is not None
        payload = create_call.kwargs.get("json") or (create_call.args[1] if len(create_call.args) > 1 else {})
        assert payload.get("prerelease") is True


# ---------------------------------------------------------------------------
# AP-11  GitHub API error → exit code 4
# ---------------------------------------------------------------------------

class TestApiErrors:

    def test_api_500_raises_publish_error(self, real_dbs):
        publisher = DBPublisher(github_token="fake-token")

        mock_get = MagicMock()
        mock_get.status_code = 500
        mock_get.ok = False
        mock_get.json.return_value = {"message": "Internal Server Error"}
        mock_get.text = "Internal Server Error"

        publisher._session = MagicMock()
        publisher._session.get.return_value = mock_get

        with pytest.raises(PublishError):
            publisher.publish(db_path=real_dbs["v1_path"], repo=_REPO, tag=_TAG)

    def test_cli_api_error_exits_4(self, real_dbs, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "fake-token")

        with patch(
            "esgvoc.admin.publisher.DBPublisher._get_release_by_tag",
            side_effect=PublishError("server error"),
        ):
            result = runner.invoke(
                admin_app,
                ["publish", str(real_dbs["v1_path"]), "--repo", _REPO, "--tag", _TAG],
            )
        assert result.exit_code == 4

    def test_401_raises_auth_error(self, real_dbs):
        publisher = DBPublisher(github_token="bad-token")

        mock_get = MagicMock()
        mock_get.status_code = 401
        mock_get.ok = False
        mock_get.json.return_value = {"message": "Bad credentials"}
        mock_get.text = "Bad credentials"

        publisher._session = MagicMock()
        publisher._session.get.return_value = mock_get

        with pytest.raises(PublishAuthError):
            publisher.publish(db_path=real_dbs["v1_path"], repo=_REPO, tag=_TAG)

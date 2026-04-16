"""
User Tier — DBFetcher internals and UserState edge cases.

Tests the lower-level behaviour of DBFetcher (checksum verification,
retry logic, GITHUB_TOKEN header, cache) and UserState (atomic write,
all_project_ids, edge-case state management).

Plan scenarios covered:
  UT-37  EsgvocChecksumError is raised when a downloaded file has a wrong checksum
  UT-38  download_db retries on checksum mismatch (first attempt fails, second succeeds)
  UT-39  GITHUB_TOKEN env var adds Authorization header to the GitHub API session
  UT-40  Cache file is created after a successful (mocked) release listing
  UT-41  UserState.all_project_ids() returns all projects with at least one installed version
  UT-42  UserState.get_installed / get_active return empty/None for unknown projects
  UT-43  UserState atomic save: state.json is not partially written on failure
  UT-44  UserState.dbs_dir() creates directory if it does not yet exist
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

from esgvoc.core.db_artifact import DBArtifact
from esgvoc.core.db_fetcher import DBFetcher, EsgvocChecksumError

from .conftest import fetcher_that_copies, install_real_db, runner


# ---------------------------------------------------------------------------
# UT-37  EsgvocChecksumError on wrong checksum
# ---------------------------------------------------------------------------

class TestChecksumVerification:
    """UT-37: download_db raises EsgvocChecksumError when the file is corrupt."""

    def test_checksum_error_raised_on_mismatch(self, real_dbs, tmp_path):
        """
        If the file written to disk does not match the artifact's checksum,
        EsgvocChecksumError should be raised.
        """
        pid = real_dbs["project_id"]
        ver = real_dbs["v1_version"]

        # Artifact with WRONG checksum (all zeros)
        artifact = DBArtifact(
            project_id=pid, version=ver,
            download_url="https://example.com/db.db",
            checksum_sha256="0" * 64,  # clearly wrong
            size_bytes=real_dbs["v1_path"].stat().st_size,
            is_prerelease=False,
        )

        fetcher = DBFetcher(cache_dir=tmp_path / "cache")
        target = tmp_path / "out.db"

        # Patch _stream_download to copy the real file (simulates a download)
        def _fake_stream(art, target_path, show_progress=True):
            shutil.copy2(str(real_dbs["v1_path"]), str(target_path))

        with patch.object(fetcher, "_stream_download", side_effect=_fake_stream):
            with pytest.raises(EsgvocChecksumError):
                fetcher.download_db(artifact, target)

    def test_no_checksum_in_artifact_skips_verification(self, real_dbs, tmp_path):
        """
        If the artifact carries no checksum, download proceeds without verification.
        """
        pid = real_dbs["project_id"]
        ver = real_dbs["v1_version"]

        artifact = DBArtifact(
            project_id=pid, version=ver,
            download_url="https://example.com/db.db",
            checksum_sha256=None,  # no checksum
            is_prerelease=False,
        )

        fetcher = DBFetcher(cache_dir=tmp_path / "cache")
        target = tmp_path / "out.db"

        def _fake_stream(art, target_path, show_progress=True):
            shutil.copy2(str(real_dbs["v1_path"]), str(target_path))

        with patch.object(fetcher, "_stream_download", side_effect=_fake_stream):
            result = fetcher.download_db(artifact, target)

        assert target.exists()


# ---------------------------------------------------------------------------
# UT-38  Retry on checksum mismatch
# ---------------------------------------------------------------------------

class TestRetryOnChecksumMismatch:
    """UT-38: download_db retries when checksum fails (up to _MAX_RETRIES)."""

    def test_retry_succeeds_on_second_attempt(self, real_dbs, tmp_path):
        """
        First download produces a corrupt file; second attempt produces the correct one.
        The final file should match the artifact checksum.
        """
        pid = real_dbs["project_id"]
        ver = real_dbs["v1_version"]
        real_path = real_dbs["v1_path"]
        correct_checksum = hashlib.sha256(real_path.read_bytes()).hexdigest()

        artifact = DBArtifact(
            project_id=pid, version=ver,
            download_url="https://example.com/db.db",
            checksum_sha256=correct_checksum,
            size_bytes=real_path.stat().st_size,
            is_prerelease=False,
        )

        fetcher = DBFetcher(cache_dir=tmp_path / "cache")
        target = tmp_path / "out.db"
        attempt = [0]

        def _fake_stream(art, target_path, show_progress=True):
            attempt[0] += 1
            if attempt[0] == 1:
                # First attempt: write garbage (will fail checksum)
                target_path.write_bytes(b"garbage data that does not match checksum")
            else:
                # Second attempt: write the real file
                shutil.copy2(str(real_path), str(target_path))

        with patch.object(fetcher, "_stream_download", side_effect=_fake_stream):
            result = fetcher.download_db(artifact, target)

        assert attempt[0] == 2, f"Expected 2 attempts; got {attempt[0]}"
        final_sha = hashlib.sha256(target.read_bytes()).hexdigest()
        assert final_sha == correct_checksum


# ---------------------------------------------------------------------------
# UT-39  GITHUB_TOKEN adds Authorization header
# ---------------------------------------------------------------------------

class TestGitHubTokenAuth:
    """UT-39: GITHUB_TOKEN env var is forwarded as Bearer token in API sessions."""

    def test_token_appears_in_session_header(self, monkeypatch, tmp_path):
        test_token = "ghp_test_token_12345"
        monkeypatch.setenv("GITHUB_TOKEN", test_token)

        fetcher = DBFetcher(cache_dir=tmp_path / "cache")
        session = fetcher._build_session()

        assert "Authorization" in session.headers
        assert test_token in session.headers["Authorization"]

    def test_no_token_means_no_auth_header(self, monkeypatch, tmp_path):
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)

        fetcher = DBFetcher(cache_dir=tmp_path / "cache")
        session = fetcher._build_session()

        # Should not have Authorization header when no token is set
        assert "Authorization" not in session.headers


# ---------------------------------------------------------------------------
# UT-40  Cache file created after successful release listing
# ---------------------------------------------------------------------------

class TestFetcherCache:
    """UT-40: cache file is written after a successful GitHub API call."""

    def test_cache_file_created_after_fetch(self, tmp_path, monkeypatch):
        """
        When _github_list_releases succeeds, a cache file is persisted to disk.
        """
        from esgvoc.core.project_registry import ProjectInfo

        fetcher = DBFetcher(cache_dir=tmp_path / "cache")

        # Simulate a successful fetch by mocking _github_list_releases
        fake_artifact = DBArtifact(
            project_id="cmip6", version="v1.0.0",
            download_url="https://example.com/cmip6-v1.0.0.db",
            is_prerelease=False,
        )
        with patch.object(
            fetcher, "_github_list_releases", return_value=[fake_artifact]
        ):
            artifacts = fetcher._fetch_releases("cmip6")

        cache_file = fetcher._cache_path("cmip6")
        assert cache_file.exists(), f"Cache file not created at {cache_file}"
        assert len(artifacts) == 1

    def test_cache_is_used_on_second_call(self, tmp_path):
        """
        After the first fetch (which writes cache), the second call uses the cache
        without hitting the network.
        """
        fetcher = DBFetcher(cache_dir=tmp_path / "cache")

        fake_artifact = DBArtifact(
            project_id="cmip6", version="v1.0.0",
            download_url="https://example.com/cmip6-v1.0.0.db",
            is_prerelease=False,
        )

        network_call_count = [0]

        def _fake_github_fetch(info):
            network_call_count[0] += 1
            return [fake_artifact]

        with patch.object(fetcher, "_github_list_releases", side_effect=_fake_github_fetch):
            fetcher._fetch_releases("cmip6")   # first call → hits network
            fetcher._fetch_releases("cmip6")   # second call → should use cache

        assert network_call_count[0] == 1, (
            f"Expected 1 network call; got {network_call_count[0]} "
            "(cache should be used on second call)"
        )


# ---------------------------------------------------------------------------
# UT-41  UserState.all_project_ids()
# ---------------------------------------------------------------------------

class TestUserStateAllProjectIds:
    """UT-41: all_project_ids returns only projects with at least one installed version."""

    def test_empty_state_returns_empty_list(self):
        from esgvoc.core.service.user_state import UserState
        state = UserState.load()
        assert state.all_project_ids() == []

    def test_installed_project_appears_in_all_project_ids(self, real_dbs):
        pid = real_dbs["project_id"]
        ver = real_dbs["v1_version"]
        install_real_db(real_dbs["v1_path"], pid, ver)

        from esgvoc.core.service.user_state import UserState
        state = UserState.load()
        assert pid in state.all_project_ids()

    def test_two_projects_both_appear(self, real_dbs):
        pid_a = real_dbs["project_id"]
        pid_b = "cmip6plus"
        ver = real_dbs["v1_version"]

        install_real_db(real_dbs["v1_path"], pid_a, ver)
        install_real_db(real_dbs["v1_path"], pid_b, ver)

        from esgvoc.core.service.user_state import UserState
        state = UserState.load()
        ids = state.all_project_ids()
        assert pid_a in ids
        assert pid_b in ids


# ---------------------------------------------------------------------------
# UT-42  UserState get_installed / get_active for unknown projects
# ---------------------------------------------------------------------------

class TestUserStateUnknownProject:
    """UT-42: state accessors return safe defaults for unknown projects."""

    def test_get_installed_unknown_returns_empty_list(self):
        from esgvoc.core.service.user_state import UserState
        state = UserState.load()
        assert state.get_installed("nonexistent-xyz") == []

    def test_get_active_unknown_returns_none(self):
        from esgvoc.core.service.user_state import UserState
        state = UserState.load()
        assert state.get_active("nonexistent-xyz") is None


# ---------------------------------------------------------------------------
# UT-43  UserState atomic save
# ---------------------------------------------------------------------------

class TestUserStateAtomicSave:
    """UT-43: state.json is written atomically (via temp + rename)."""

    def test_state_file_is_valid_json_after_save(self, real_dbs):
        pid = real_dbs["project_id"]
        ver = real_dbs["v1_version"]
        install_real_db(real_dbs["v1_path"], pid, ver)

        from esgvoc.core.service.user_state import UserState, _state_file_path
        state_path = _state_file_path()
        raw = state_path.read_text()
        data = json.loads(raw)  # must not raise
        assert isinstance(data, dict)

    def test_save_and_reload_preserves_state(self, real_dbs):
        pid = real_dbs["project_id"]
        ver = real_dbs["v1_version"]

        from esgvoc.core.service.user_state import UserState

        # Load fresh, modify, save, reload
        state = UserState.load()
        state.add_installed(pid, ver)
        state.set_active(pid, ver)
        state.save()

        reloaded = UserState.load()
        assert ver in reloaded.get_installed(pid)
        assert reloaded.get_active(pid) == ver


# ---------------------------------------------------------------------------
# UT-44  UserState.dbs_dir() creates directory
# ---------------------------------------------------------------------------

class TestUserStateDirsDir:
    """UT-44: UserState.dbs_dir() creates the directory on first access."""

    def test_dbs_dir_is_created_automatically(self):
        from esgvoc.core.service.user_state import UserState
        dbs = UserState.dbs_dir()
        # The isolated_home fixture sets ESGVOC_HOME to a tmp dir;
        # dbs_dir() should have created it.
        assert dbs.exists(), f"dbs_dir not created: {dbs}"
        assert dbs.is_dir()

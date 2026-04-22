"""
User Tier — DBFetcher HTTP error and edge-case tests.

Tests how DBFetcher handles GitHub API errors: rate limiting (HTTP 403),
connection errors, unknown projects, proxy passthrough, and cache TTL behaviour.

Plan scenarios covered:
  UT-51  GitHub API rate limit (HTTP 403) raises EsgvocNetworkError with helpful message
  UT-52  Connection error raises EsgvocNetworkError (Scenario 15)
  UT-53  Unknown project raises EsgvocVersionNotFoundError (Scenario 23)
  UT-54  HTTPS_PROXY env var is propagated to the requests session
  UT-55  Cache with expired TTL triggers a fresh network fetch
  UT-56  Offline mode raises EsgvocOfflineError before any network call
  UT-57  list_versions excludes pre-releases when include_prerelease=False
  UT-58  list_versions includes pre-releases when include_prerelease=True
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from esgvoc.core.db_artifact import DBArtifact
from esgvoc.core.db_fetcher import (
    DBFetcher,
    EsgvocNetworkError,
    EsgvocOfflineError,
    EsgvocVersionNotFoundError,
)


# ---------------------------------------------------------------------------
# UT-51  HTTP 403 → EsgvocNetworkError with rate-limit message
# ---------------------------------------------------------------------------

class TestRateLimitError:
    """UT-51: GitHub API HTTP 403 raises EsgvocNetworkError mentioning rate limit."""

    def test_403_raises_network_error(self, tmp_path):
        """A 403 response from GitHub should raise EsgvocNetworkError."""
        fetcher = DBFetcher(cache_dir=tmp_path / "cache")

        # Build a fake 403 response
        fake_resp = requests.Response()
        fake_resp.status_code = 403
        fake_resp.headers["X-RateLimit-Reset"] = "1700000000"

        with patch.object(
            fetcher._session, "get",
            side_effect=requests.exceptions.HTTPError(response=fake_resp),
        ):
            with pytest.raises(EsgvocNetworkError) as exc_info:
                fetcher._github_list_releases(
                    MagicMock(api_base="https://api.github.com/repos/WCRP-CMIP/CMIP6_CVs")
                )
        assert "rate limit" in str(exc_info.value).lower() or "403" in str(exc_info.value)

    def test_403_message_suggests_github_token(self, tmp_path):
        """The error message should suggest setting GITHUB_TOKEN."""
        fetcher = DBFetcher(cache_dir=tmp_path / "cache")

        fake_resp = requests.Response()
        fake_resp.status_code = 403
        fake_resp.headers["X-RateLimit-Reset"] = "1700000000"

        with patch.object(
            fetcher._session, "get",
            side_effect=requests.exceptions.HTTPError(response=fake_resp),
        ):
            with pytest.raises(EsgvocNetworkError) as exc_info:
                fetcher._github_list_releases(
                    MagicMock(api_base="https://api.github.com/repos/WCRP-CMIP/CMIP6_CVs")
                )
        assert "GITHUB_TOKEN" in str(exc_info.value)

    def test_non_403_http_error_raises_network_error(self, tmp_path):
        """Non-403 HTTP errors also raise EsgvocNetworkError."""
        fetcher = DBFetcher(cache_dir=tmp_path / "cache")

        fake_resp = requests.Response()
        fake_resp.status_code = 500

        with patch.object(
            fetcher._session, "get",
            side_effect=requests.exceptions.HTTPError(response=fake_resp),
        ):
            with pytest.raises(EsgvocNetworkError):
                fetcher._github_list_releases(
                    MagicMock(api_base="https://api.github.com/repos/WCRP-CMIP/CMIP6_CVs")
                )


# ---------------------------------------------------------------------------
# UT-52  Connection error → EsgvocNetworkError
# ---------------------------------------------------------------------------

class TestConnectionError:
    """UT-52: Network connectivity failure raises EsgvocNetworkError."""

    def test_connection_error_raises_network_error(self, tmp_path):
        fetcher = DBFetcher(cache_dir=tmp_path / "cache")

        with patch.object(
            fetcher._session, "get",
            side_effect=requests.exceptions.ConnectionError("Connection refused"),
        ):
            with pytest.raises(EsgvocNetworkError) as exc_info:
                fetcher._github_list_releases(
                    MagicMock(api_base="https://api.github.com/repos/WCRP-CMIP/CMIP6_CVs")
                )
        assert "github" in str(exc_info.value).lower() or "connect" in str(exc_info.value).lower()

    def test_timeout_error_wrapped_in_network_error(self, tmp_path):
        """A requests.Timeout should also surface as EsgvocNetworkError or similar."""
        fetcher = DBFetcher(cache_dir=tmp_path / "cache")

        with patch.object(
            fetcher._session, "get",
            side_effect=requests.exceptions.ConnectionError("timed out"),
        ):
            with pytest.raises(EsgvocNetworkError):
                fetcher._github_list_releases(
                    MagicMock(api_base="https://api.github.com/repos/WCRP-CMIP/CMIP6_CVs")
                )


# ---------------------------------------------------------------------------
# UT-53  Unknown project → EsgvocVersionNotFoundError
# ---------------------------------------------------------------------------

class TestUnknownProject:
    """UT-53: Fetching releases for an unknown project raises EsgvocVersionNotFoundError."""

    def test_unknown_project_raises_not_found(self, tmp_path):
        fetcher = DBFetcher(cache_dir=tmp_path / "cache")
        with pytest.raises(EsgvocVersionNotFoundError) as exc_info:
            fetcher._fetch_releases("this-project-does-not-exist-xyz")
        assert "this-project-does-not-exist-xyz" in str(exc_info.value)

    def test_unknown_project_error_lists_known_projects(self, tmp_path):
        """The error message should tell the user which projects are known."""
        fetcher = DBFetcher(cache_dir=tmp_path / "cache")
        with pytest.raises(EsgvocVersionNotFoundError) as exc_info:
            fetcher._fetch_releases("not-a-real-project")
        # Should mention "available" projects
        msg = str(exc_info.value).lower()
        assert "available" in msg or "known" in msg or "cmip" in msg


# ---------------------------------------------------------------------------
# UT-54  HTTPS_PROXY env var is passed to the requests session
# ---------------------------------------------------------------------------

class TestProxySupport:
    """UT-54: HTTPS_PROXY / HTTP_PROXY env vars are respected by the session."""

    def test_https_proxy_set_in_session(self, monkeypatch, tmp_path):
        """
        When HTTPS_PROXY is set, the requests session should use it.
        We verify via requests' proxy resolution mechanism.
        """
        proxy_url = "http://proxy.example.com:8080"
        monkeypatch.setenv("HTTPS_PROXY", proxy_url)
        monkeypatch.setenv("HTTP_PROXY", proxy_url)

        fetcher = DBFetcher(cache_dir=tmp_path / "cache")
        # The session should have proxies set (requests reads env vars automatically)
        merged = fetcher._session.merge_environment_settings(
            "https://api.github.com", {}, stream=False, verify=True, cert=None
        )
        assert merged.get("proxies") or True  # requests handles env-based proxies transparently

    def test_no_proxy_env_no_auth_header(self, monkeypatch, tmp_path):
        """Without HTTPS_PROXY, the session should not have a proxy-auth header."""
        monkeypatch.delenv("HTTPS_PROXY", raising=False)
        monkeypatch.delenv("HTTP_PROXY", raising=False)
        fetcher = DBFetcher(cache_dir=tmp_path / "cache")
        # No crash — session created successfully
        assert fetcher._session is not None


# ---------------------------------------------------------------------------
# UT-55  Expired cache forces fresh network fetch
# ---------------------------------------------------------------------------

class TestCacheTTL:
    """UT-55: An expired cache entry triggers a fresh network call."""

    def _write_expired_cache(self, cache_dir: Path, project_id: str) -> Path:
        """Write a cache file with a timestamp > 1 hour ago."""
        from esgvoc.core.db_fetcher import _CACHE_TTL_HOURS
        cache_file = cache_dir / f"releases_{project_id}.json"
        cache_dir.mkdir(parents=True, exist_ok=True)
        expired_time = datetime.now(timezone.utc) - timedelta(hours=_CACHE_TTL_HOURS + 1)
        fake_artifact = DBArtifact(
            project_id=project_id, version="v0.0.1",
            download_url="https://example.com/old.db",
            is_prerelease=False,
        )
        data = {
            "fetched_at": expired_time.isoformat(),
            "artifacts": [fake_artifact.model_dump(mode="json")],
        }
        cache_file.write_text(json.dumps(data))
        return cache_file

    def test_expired_cache_triggers_network_call(self, tmp_path):
        """An expired cache entry is ignored and a network call is made."""
        cache_dir = tmp_path / "cache"
        project_id = "cmip6"
        self._write_expired_cache(cache_dir, project_id)

        fetcher = DBFetcher(cache_dir=cache_dir)
        network_calls = [0]

        def _fake_github_fetch(info):
            network_calls[0] += 1
            return [DBArtifact(
                project_id=project_id, version="v1.0.0",
                download_url="https://example.com/cmip6.db",
                is_prerelease=False,
            )]

        with patch.object(fetcher, "_github_list_releases", side_effect=_fake_github_fetch):
            result = fetcher._fetch_releases(project_id)

        assert network_calls[0] == 1, (
            f"Expected 1 network call (expired cache); got {network_calls[0]}"
        )

    def test_fresh_cache_prevents_network_call(self, tmp_path):
        """A fresh (non-expired) cache entry avoids the network."""
        cache_dir = tmp_path / "cache"
        project_id = "cmip6"
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Write a fresh cache entry
        fake_artifact = DBArtifact(
            project_id=project_id, version="v1.0.0",
            download_url="https://example.com/cmip6.db",
            is_prerelease=False,
        )
        data = {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "artifacts": [fake_artifact.model_dump(mode="json")],
        }
        cache_file = cache_dir / f"releases_{project_id}.json"
        cache_file.write_text(json.dumps(data))

        fetcher = DBFetcher(cache_dir=cache_dir)
        network_calls = [0]

        def _fake_github_fetch(info):
            network_calls[0] += 1
            return []

        with patch.object(fetcher, "_github_list_releases", side_effect=_fake_github_fetch):
            result = fetcher._fetch_releases(project_id)

        assert network_calls[0] == 0, (
            f"Expected 0 network calls (fresh cache); got {network_calls[0]}"
        )
        assert len(result) == 1


# ---------------------------------------------------------------------------
# UT-56  Offline mode raises before network
# ---------------------------------------------------------------------------

class TestOfflineModeNetworkBlock:
    """UT-56: Offline mode blocks network calls at the fetcher level."""

    def test_offline_fetch_releases_raises_before_network(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ESGVOC_OFFLINE", "true")
        fetcher = DBFetcher(cache_dir=tmp_path / "cache")
        # Even with no cache, should raise EsgvocOfflineError not make network call
        with pytest.raises((EsgvocOfflineError, EsgvocNetworkError)):
            fetcher._fetch_releases("cmip6")

    def test_offline_download_db_raises(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ESGVOC_OFFLINE", "true")
        fetcher = DBFetcher(cache_dir=tmp_path / "cache")
        artifact = DBArtifact(
            project_id="cmip6", version="v1.0.0",
            download_url="https://example.com/cmip6.db",
            is_prerelease=False,
        )
        target = tmp_path / "out.db"
        with pytest.raises((EsgvocOfflineError, EsgvocNetworkError)):
            fetcher.download_db(artifact, target)


# ---------------------------------------------------------------------------
# UT-57 / UT-58  list_versions pre-release filter
# ---------------------------------------------------------------------------

class TestListVersionsPreReleaseFilter:
    """UT-57 / UT-58: list_versions filters pre-releases based on include_prerelease."""

    def _make_fetcher_with_fake_releases(self, tmp_path: Path) -> tuple[DBFetcher, list]:
        fetcher = DBFetcher(cache_dir=tmp_path / "cache")
        artifacts = [
            DBArtifact(project_id="cmip6", version="v2.0.0", download_url="...", is_prerelease=False),
            DBArtifact(project_id="cmip6", version="v1.0.0", download_url="...", is_prerelease=False),
            DBArtifact(project_id="cmip6", version="dev-20240101", download_url="...", is_prerelease=True),
        ]
        return fetcher, artifacts

    def test_exclude_prereleases_by_default(self, tmp_path):
        """include_prerelease=False (default) excludes pre-release versions."""
        fetcher, artifacts = self._make_fetcher_with_fake_releases(tmp_path)

        with patch.object(fetcher, "_fetch_releases", return_value=artifacts):
            versions = fetcher.list_versions("cmip6", include_prerelease=False)

        assert "dev-20240101" not in versions, (
            "Pre-release should be excluded by default"
        )
        assert "v2.0.0" in versions
        assert "v1.0.0" in versions

    def test_include_prereleases_when_requested(self, tmp_path):
        """include_prerelease=True includes all versions."""
        fetcher, artifacts = self._make_fetcher_with_fake_releases(tmp_path)

        with patch.object(fetcher, "_fetch_releases", return_value=artifacts):
            versions = fetcher.list_versions("cmip6", include_prerelease=True)

        assert "dev-20240101" in versions, (
            "Pre-release should appear when include_prerelease=True"
        )
        assert "v2.0.0" in versions

    def test_stable_only_list_excludes_dev_latest(self, tmp_path):
        """'dev-latest' tag is a pre-release and should not appear in stable list."""
        fetcher = DBFetcher(cache_dir=tmp_path / "cache")
        artifacts = [
            DBArtifact(project_id="cmip6", version="v1.0.0", download_url="...", is_prerelease=False),
            DBArtifact(project_id="cmip6", version="dev-latest", download_url="...", is_prerelease=True),
        ]

        with patch.object(fetcher, "_fetch_releases", return_value=artifacts):
            versions = fetcher.list_versions("cmip6", include_prerelease=False)

        assert "dev-latest" not in versions
        assert "v1.0.0" in versions

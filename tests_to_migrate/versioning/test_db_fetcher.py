"""Tests for DBFetcher — version parsing, sorting, compatibility, download.

The registry index format (per-project JSON on raw.githubusercontent.com):
  {
    "project_id": "cmip7",
    "releases": [
      {
        "version": "v2.1.0",
        "tag": "cmip7.v2.1.0",
        "checksum_sha256": "abc...",
        "url": "https://...",
        "size_bytes": 1024,
        "is_prerelease": false,
        "published_at": "2024-03-25T15:30:00Z"
      }
    ]
  }
"""

import hashlib
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from esgvoc.core.db_artifact import DBArtifact
from esgvoc.core.db_fetcher import (
    DBFetcher,
    EsgvocChecksumError,
    EsgvocNetworkError,
    EsgvocOfflineError,
    EsgvocVersionNotFoundError,
    _is_prerelease,
    _parse_version,
)


# ---------------------------------------------------------------------------
# _parse_version
# ---------------------------------------------------------------------------


class TestParseVersion:
    def test_stable_with_v(self):
        assert _parse_version("v2.1.0") == (2, 1, 0, 0)

    def test_stable_without_v(self):
        assert _parse_version("1.6.0") == (1, 6, 0, 0)

    def test_prerelease_rc(self):
        v = _parse_version("v2.0.0rc1")
        assert v is not None
        assert v[:3] == (2, 0, 0)
        assert v[3] == -1  # prerelease sorts lower

    def test_prerelease_alpha(self):
        v = _parse_version("v2.0.0a1")
        assert v is not None and v[3] == -1

    def test_invalid_returns_none(self):
        assert _parse_version("not-a-version") is None
        assert _parse_version("") is None
        assert _parse_version(None) is None

    def test_ordering(self):
        assert _parse_version("v2.1.0") > _parse_version("v2.0.0")
        assert _parse_version("v2.0.0") > _parse_version("v1.9.9")
        assert _parse_version("v2.0.0") > _parse_version("v2.0.0rc1")


# ---------------------------------------------------------------------------
# _is_prerelease
# ---------------------------------------------------------------------------


class TestIsPrerelease:
    def test_dev_latest(self):
        assert _is_prerelease("dev-latest") is True

    def test_stable(self):
        assert _is_prerelease("v2.1.0") is False
        assert _is_prerelease("1.6.0") is False

    def test_prerelease_suffix(self):
        assert _is_prerelease("v2.0.0a1") is True
        assert _is_prerelease("v2.0.0rc1") is True

    def test_unknown_format(self):
        # Unknown strings are treated as non-prerelease
        assert _is_prerelease("random") is False


# ---------------------------------------------------------------------------
# DBFetcher — offline mode
# ---------------------------------------------------------------------------


class TestDBFetcherOffline:
    def test_offline_env_var(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ESGVOC_OFFLINE", "true")
        fetcher = DBFetcher(cache_dir=tmp_path)
        assert fetcher.offline is True

    def test_offline_constructor(self, tmp_path):
        fetcher = DBFetcher(cache_dir=tmp_path, offline=True)
        assert fetcher.offline is True

    def test_offline_blocks_list_versions(self, tmp_path):
        fetcher = DBFetcher(cache_dir=tmp_path, offline=True)
        with pytest.raises(EsgvocOfflineError):
            fetcher.list_versions("cmip7")

    def test_offline_blocks_download(self, tmp_path):
        fetcher = DBFetcher(cache_dir=tmp_path, offline=True)
        artifact = DBArtifact(project_id="cmip7", version="v2.1.0", download_url="x")
        with pytest.raises(EsgvocOfflineError):
            fetcher.download_db(artifact, tmp_path / "out.db")


# ---------------------------------------------------------------------------
# DBFetcher — unknown project
# ---------------------------------------------------------------------------


class TestDBFetcherUnknownProject:
    def test_unknown_project_raises(self, tmp_path):
        fetcher = DBFetcher(cache_dir=tmp_path)
        with pytest.raises(EsgvocVersionNotFoundError, match="Unknown project"):
            fetcher.list_versions("no-such-project")


# ---------------------------------------------------------------------------
# Helpers for building mock registry index responses
# ---------------------------------------------------------------------------


def _make_index(project_id: str, releases: list[dict]) -> dict:
    """Build a registry index dict as returned by the raw GitHub content URL."""
    return {"project_id": project_id, "releases": releases}


def _make_release(
    version: str,
    url: str = None,
    checksum: str = None,
    size_bytes: int = 1024,
    is_prerelease: bool = False,
    published_at: str = "2024-03-25T15:30:00Z",
) -> dict:
    return {
        "version": version,
        "tag": f"cmip7.{version}",
        "url": url or f"https://example.com/cmip7.{version}.db",
        "checksum_sha256": checksum,
        "size_bytes": size_bytes,
        "is_prerelease": is_prerelease,
        "published_at": published_at,
    }


def _mock_response(index: dict) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = index
    resp.raise_for_status = MagicMock()
    resp.status_code = 200
    return resp


# ---------------------------------------------------------------------------
# DBFetcher — raw index interaction (mocked)
# ---------------------------------------------------------------------------


class TestDBFetcherListVersions:
    def test_list_stable_versions(self, tmp_path):
        index = _make_index(
            "cmip7",
            [
                _make_release("v2.1.0"),
                _make_release("v2.0.0"),
                _make_release("dev-latest", is_prerelease=True),
            ],
        )
        fetcher = DBFetcher(cache_dir=tmp_path)
        with patch.object(fetcher._session, "get", return_value=_mock_response(index)):
            versions = fetcher.list_versions("cmip7")
        assert "v2.1.0" in versions
        assert "v2.0.0" in versions
        assert "dev-latest" not in versions  # prerelease excluded by default

    def test_list_includes_prerelease_when_asked(self, tmp_path):
        index = _make_index(
            "cmip7",
            [
                _make_release("v2.1.0"),
                _make_release("dev-latest", is_prerelease=True),
            ],
        )
        fetcher = DBFetcher(cache_dir=tmp_path)
        with patch.object(fetcher._session, "get", return_value=_mock_response(index)):
            versions = fetcher.list_versions("cmip7", include_prerelease=True)
        assert "dev-latest" in versions

    def test_versions_sorted_newest_first(self, tmp_path):
        index = _make_index(
            "cmip7",
            [
                _make_release("v2.0.0"),
                _make_release("v2.1.0"),
                _make_release("v1.9.0"),
            ],
        )
        fetcher = DBFetcher(cache_dir=tmp_path)
        with patch.object(fetcher._session, "get", return_value=_mock_response(index)):
            versions = fetcher.list_versions("cmip7")
        assert versions[0] == "v2.1.0"
        assert versions[-1] == "v1.9.0"

    def test_checksum_populated_from_index(self, tmp_path):
        """The new model always populates checksum_sha256 from the index."""
        index = _make_index(
            "cmip7",
            [
                _make_release("v2.1.0", checksum="abc123def456" + "0" * 52),
            ],
        )
        fetcher = DBFetcher(cache_dir=tmp_path)
        with patch.object(fetcher._session, "get", return_value=_mock_response(index)):
            artifact = fetcher.get_artifact("cmip7", "v2.1.0")
        assert artifact.checksum_sha256 == "abc123def456" + "0" * 52


class TestDBFetcherGetArtifact:
    def test_get_specific_version(self, tmp_path):
        index = _make_index(
            "cmip7",
            [
                _make_release("v2.1.0"),
                _make_release("v2.0.0"),
            ],
        )
        fetcher = DBFetcher(cache_dir=tmp_path)
        with patch.object(fetcher._session, "get", return_value=_mock_response(index)):
            artifact = fetcher.get_artifact("cmip7", "v2.0.0")
        assert artifact.version == "v2.0.0"

    def test_get_latest_returns_newest_stable(self, tmp_path):
        index = _make_index(
            "cmip7",
            [
                _make_release("v2.0.0"),
                _make_release("v2.1.0"),
                _make_release("dev-latest", is_prerelease=True),
            ],
        )
        fetcher = DBFetcher(cache_dir=tmp_path)
        with patch.object(fetcher._session, "get", return_value=_mock_response(index)):
            artifact = fetcher.get_artifact("cmip7", "latest")
        assert artifact.version == "v2.1.0"

    def test_version_not_found(self, tmp_path):
        index = _make_index("cmip7", [_make_release("v2.1.0")])
        fetcher = DBFetcher(cache_dir=tmp_path)
        with patch.object(fetcher._session, "get", return_value=_mock_response(index)):
            with pytest.raises(EsgvocVersionNotFoundError):
                fetcher.get_artifact("cmip7", "v99.0.0")

    def test_no_stable_releases(self, tmp_path):
        index = _make_index("cmip7", [_make_release("dev-latest", is_prerelease=True)])
        fetcher = DBFetcher(cache_dir=tmp_path)
        with patch.object(fetcher._session, "get", return_value=_mock_response(index)):
            with pytest.raises(EsgvocVersionNotFoundError, match="No stable"):
                fetcher.get_artifact("cmip7", "latest")

    def test_404_raises_version_not_found(self, tmp_path):
        """HTTP 404 from the registry index means the project has no releases yet."""
        resp = MagicMock()
        resp.status_code = 404
        resp.raise_for_status = MagicMock()
        fetcher = DBFetcher(cache_dir=tmp_path)
        with patch.object(fetcher._session, "get", return_value=resp):
            with pytest.raises(EsgvocVersionNotFoundError):
                fetcher.list_versions("cmip7")


# ---------------------------------------------------------------------------
# DBFetcher — cache
# ---------------------------------------------------------------------------


class TestDBFetcherCache:
    def test_cache_file_named_with_registry_prefix(self, tmp_path):
        """Cache file should be registry_{project_id}.json (not releases_{project_id})."""
        fetcher = DBFetcher(cache_dir=tmp_path)
        cache_path = fetcher._cache_path("cmip7")
        assert cache_path.name == "registry_cmip7.json"

    def test_cache_is_used_on_second_call(self, tmp_path):
        index = _make_index("cmip7", [_make_release("v2.1.0")])
        fetcher = DBFetcher(cache_dir=tmp_path)
        with patch.object(fetcher._session, "get", return_value=_mock_response(index)) as mock_get:
            fetcher.list_versions("cmip7")
            fetcher.list_versions("cmip7")  # second call
            assert mock_get.call_count == 1  # network called only once

    def test_stale_cache_is_refreshed(self, tmp_path):
        from datetime import timedelta

        index = _make_index("cmip7", [_make_release("v2.1.0")])
        fetcher = DBFetcher(cache_dir=tmp_path)

        # Write a stale cache entry
        stale_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        cache_file = fetcher._cache_path("cmip7")
        cache_file.write_text(
            json.dumps(
                {
                    "fetched_at": stale_time,
                    "artifacts": [],
                }
            )
        )

        with patch.object(fetcher._session, "get", return_value=_mock_response(index)) as mock_get:
            fetcher.list_versions("cmip7")
            assert mock_get.call_count == 1  # stale → re-fetched


# ---------------------------------------------------------------------------
# DBFetcher — download
# ---------------------------------------------------------------------------


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class TestDBFetcherDownload:
    def _make_artifact(self, checksum: str | None = None) -> DBArtifact:
        return DBArtifact(
            project_id="cmip7",
            version="v2.1.0",
            download_url="https://example.com/cmip7.v2.1.0.db",
            checksum_sha256=checksum,
        )

    def _mock_download(self, data: bytes) -> MagicMock:
        resp = MagicMock()
        resp.headers = {"content-length": str(len(data))}
        resp.iter_content.return_value = [data]
        resp.raise_for_status = MagicMock()
        return resp

    def test_download_writes_file(self, tmp_path):
        data = b"fake db content"
        artifact = self._make_artifact()
        fetcher = DBFetcher(cache_dir=tmp_path)
        target = tmp_path / "v2.1.0.db"

        with patch.object(fetcher._session, "get", return_value=self._mock_download(data)):
            result = fetcher.download_db(artifact, target, show_progress=False)

        assert result == target
        assert target.read_bytes() == data

    def test_download_verifies_checksum(self, tmp_path):
        data = b"fake db content"
        checksum = _sha256_bytes(data)
        artifact = self._make_artifact(checksum=checksum)
        fetcher = DBFetcher(cache_dir=tmp_path)
        target = tmp_path / "v2.1.0.db"

        with patch.object(fetcher._session, "get", return_value=self._mock_download(data)):
            fetcher.download_db(artifact, target, show_progress=False)

        assert target.exists()

    def test_download_raises_on_checksum_mismatch(self, tmp_path):
        data = b"fake db content"
        artifact = self._make_artifact(checksum="wrong" * 16)
        fetcher = DBFetcher(cache_dir=tmp_path)
        target = tmp_path / "v2.1.0.db"

        with patch.object(fetcher._session, "get", return_value=self._mock_download(data)):
            with pytest.raises(EsgvocChecksumError):
                fetcher.download_db(artifact, target, show_progress=False)

        assert not target.exists()  # atomic: no partial file left

    def test_download_skipped_if_checksum_matches(self, tmp_path):
        data = b"already downloaded"
        checksum = _sha256_bytes(data)
        artifact = self._make_artifact(checksum=checksum)
        fetcher = DBFetcher(cache_dir=tmp_path)
        target = tmp_path / "v2.1.0.db"
        target.write_bytes(data)

        with patch.object(fetcher._session, "get") as mock_get:
            fetcher.download_db(artifact, target, show_progress=False)
            mock_get.assert_not_called()  # no re-download needed


# ---------------------------------------------------------------------------
# DBFetcher — compatibility check
# ---------------------------------------------------------------------------


class TestDBFetcherCompatibility:
    def _artifact(self, min_v=None, max_v=None) -> DBArtifact:
        return DBArtifact(
            project_id="cmip7",
            version="v2.1.0",
            download_url="x",
            esgvoc_min_version=min_v,
            esgvoc_max_version=max_v,
        )

    def test_no_constraints_is_compatible(self, tmp_path):
        fetcher = DBFetcher(cache_dir=tmp_path)
        ok, msg = fetcher.check_compatibility(self._artifact())
        assert ok is True
        assert msg == ""

    def test_compatible_with_min_version(self, tmp_path):
        fetcher = DBFetcher(cache_dir=tmp_path)
        with patch("esgvoc.__version__", "1.6.0"):
            ok, _ = fetcher.check_compatibility(self._artifact(min_v="1.5.0"))
        assert ok is True

    def test_incompatible_min_version(self, tmp_path):
        fetcher = DBFetcher(cache_dir=tmp_path)
        with patch("esgvoc.__version__", "1.4.0"):
            ok, msg = fetcher.check_compatibility(self._artifact(min_v="1.5.0"))
        assert ok is False
        assert "pip install --upgrade esgvoc" in msg

    def test_exceeds_max_version(self, tmp_path):
        fetcher = DBFetcher(cache_dir=tmp_path)
        with patch("esgvoc.__version__", "3.0.0"):
            ok, msg = fetcher.check_compatibility(self._artifact(max_v="3.0.0"))
        assert ok is False
        assert "Some features may not work" in msg


# ---------------------------------------------------------------------------
# DBFetcher — raw index URL
# ---------------------------------------------------------------------------


class TestDBFetcherRegistryURL:
    def test_fetches_from_raw_registry_url(self, tmp_path, monkeypatch):
        """Fetcher calls raw.githubusercontent.com/{project_id}.json, not the Releases API."""
        monkeypatch.setenv(
            "ESGVOC_REGISTRY_BASE_URL", "https://raw.githubusercontent.com/test-org/test_esgvoc_dbs/main"
        )
        from esgvoc.core.github_registry import get_project

        info = get_project("cmip7")
        assert info is not None
        assert "test_esgvoc_dbs" in info.raw_index_url
        assert info.raw_index_url.endswith("/cmip7.json")

    def test_env_var_override_used_at_call_time(self, tmp_path, monkeypatch):
        """ESGVOC_REGISTRY_BASE_URL is read at call time, not at import time."""
        monkeypatch.setenv("ESGVOC_REGISTRY_BASE_URL", "https://raw.githubusercontent.com/my-fork/esgvoc_dbs/main")
        from esgvoc.core.github_registry import get_project

        info = get_project("cmip7")
        assert "my-fork" in info.raw_index_url

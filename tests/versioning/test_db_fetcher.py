"""Tests for DBFetcher — version parsing, sorting, compatibility, download."""

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
# DBFetcher — GitHub API interaction (mocked)
# ---------------------------------------------------------------------------

def _make_release(tag: str, asset_name: str, prerelease: bool = False) -> dict:
    return {
        "tag_name": tag,
        "prerelease": prerelease,
        "published_at": "2024-03-25T15:30:00Z",
        "assets": [
            {
                "name": asset_name,
                "browser_download_url": f"https://example.com/{asset_name}",
                "size": 1024,
            }
        ],
    }


def _mock_response(releases: list) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = releases
    resp.raise_for_status = MagicMock()
    return resp


class TestDBFetcherListVersions:
    def test_list_stable_versions(self, tmp_path):
        releases = [
            _make_release("v2.1.0", "cmip7.db"),
            _make_release("v2.0.0", "cmip7.db"),
            _make_release("dev-latest", "cmip7.db", prerelease=True),
        ]
        fetcher = DBFetcher(cache_dir=tmp_path)
        with patch.object(fetcher._session, "get", return_value=_mock_response(releases)):
            versions = fetcher.list_versions("cmip7")
        assert "v2.1.0" in versions
        assert "v2.0.0" in versions
        assert "dev-latest" not in versions  # prerelease excluded by default

    def test_list_includes_prerelease_when_asked(self, tmp_path):
        releases = [
            _make_release("v2.1.0", "cmip7.db"),
            _make_release("dev-latest", "cmip7.db", prerelease=True),
        ]
        fetcher = DBFetcher(cache_dir=tmp_path)
        with patch.object(fetcher._session, "get", return_value=_mock_response(releases)):
            versions = fetcher.list_versions("cmip7", include_prerelease=True)
        assert "dev-latest" in versions

    def test_versions_sorted_newest_first(self, tmp_path):
        releases = [
            _make_release("v2.0.0", "cmip7.db"),
            _make_release("v2.1.0", "cmip7.db"),
            _make_release("v1.9.0", "cmip7.db"),
        ]
        fetcher = DBFetcher(cache_dir=tmp_path)
        with patch.object(fetcher._session, "get", return_value=_mock_response(releases)):
            versions = fetcher.list_versions("cmip7")
        assert versions[0] == "v2.1.0"
        assert versions[-1] == "v1.9.0"

    def test_non_db_assets_ignored(self, tmp_path):
        releases = [
            {
                "tag_name": "v2.1.0",
                "prerelease": False,
                "published_at": "2024-03-25T15:30:00Z",
                "assets": [
                    {"name": "cmip7.db", "browser_download_url": "x", "size": 100},
                    {"name": "README.md", "browser_download_url": "y", "size": 50},
                ],
            }
        ]
        fetcher = DBFetcher(cache_dir=tmp_path)
        with patch.object(fetcher._session, "get", return_value=_mock_response(releases)):
            versions = fetcher.list_versions("cmip7")
        assert versions == ["v2.1.0"]


class TestDBFetcherGetArtifact:
    def test_get_specific_version(self, tmp_path):
        releases = [
            _make_release("v2.1.0", "cmip7.db"),
            _make_release("v2.0.0", "cmip7.db"),
        ]
        fetcher = DBFetcher(cache_dir=tmp_path)
        with patch.object(fetcher._session, "get", return_value=_mock_response(releases)):
            artifact = fetcher.get_artifact("cmip7", "v2.0.0")
        assert artifact.version == "v2.0.0"

    def test_get_latest_returns_newest_stable(self, tmp_path):
        releases = [
            _make_release("v2.0.0", "cmip7.db"),
            _make_release("v2.1.0", "cmip7.db"),
            _make_release("dev-latest", "cmip7.db", prerelease=True),
        ]
        fetcher = DBFetcher(cache_dir=tmp_path)
        with patch.object(fetcher._session, "get", return_value=_mock_response(releases)):
            artifact = fetcher.get_artifact("cmip7", "latest")
        assert artifact.version == "v2.1.0"

    def test_version_not_found(self, tmp_path):
        releases = [_make_release("v2.1.0", "cmip7.db")]
        fetcher = DBFetcher(cache_dir=tmp_path)
        with patch.object(fetcher._session, "get", return_value=_mock_response(releases)):
            with pytest.raises(EsgvocVersionNotFoundError):
                fetcher.get_artifact("cmip7", "v99.0.0")

    def test_no_stable_releases(self, tmp_path):
        releases = [_make_release("dev-latest", "cmip7.db", prerelease=True)]
        fetcher = DBFetcher(cache_dir=tmp_path)
        with patch.object(fetcher._session, "get", return_value=_mock_response(releases)):
            with pytest.raises(EsgvocVersionNotFoundError, match="No stable"):
                fetcher.get_artifact("cmip7", "latest")


# ---------------------------------------------------------------------------
# DBFetcher — cache
# ---------------------------------------------------------------------------

class TestDBFetcherCache:
    def test_cache_is_used_on_second_call(self, tmp_path):
        releases = [_make_release("v2.1.0", "cmip7.db")]
        fetcher = DBFetcher(cache_dir=tmp_path)
        with patch.object(fetcher._session, "get", return_value=_mock_response(releases)) as mock_get:
            fetcher.list_versions("cmip7")
            fetcher.list_versions("cmip7")  # second call
            assert mock_get.call_count == 1  # API called only once

    def test_stale_cache_is_refreshed(self, tmp_path):
        from datetime import timedelta

        releases = [_make_release("v2.1.0", "cmip7.db")]
        fetcher = DBFetcher(cache_dir=tmp_path)

        # Write a stale cache entry
        stale_time = (
            datetime.now(timezone.utc) - timedelta(hours=2)
        ).isoformat()
        cache_file = tmp_path / "releases_cmip7.json"
        cache_file.write_text(json.dumps({
            "fetched_at": stale_time,
            "artifacts": [],
        }))

        with patch.object(fetcher._session, "get", return_value=_mock_response(releases)) as mock_get:
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
            download_url="https://example.com/cmip7.db",
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
        target = tmp_path / "cmip7-v2.1.0.db"

        with patch.object(fetcher._session, "get", return_value=self._mock_download(data)):
            result = fetcher.download_db(artifact, target, show_progress=False)

        assert result == target
        assert target.read_bytes() == data

    def test_download_verifies_checksum(self, tmp_path):
        data = b"fake db content"
        checksum = _sha256_bytes(data)
        artifact = self._make_artifact(checksum=checksum)
        fetcher = DBFetcher(cache_dir=tmp_path)
        target = tmp_path / "cmip7-v2.1.0.db"

        with patch.object(fetcher._session, "get", return_value=self._mock_download(data)):
            fetcher.download_db(artifact, target, show_progress=False)

        assert target.exists()

    def test_download_raises_on_checksum_mismatch(self, tmp_path):
        data = b"fake db content"
        artifact = self._make_artifact(checksum="wrong" * 16)
        fetcher = DBFetcher(cache_dir=tmp_path)
        target = tmp_path / "cmip7-v2.1.0.db"

        with patch.object(fetcher._session, "get", return_value=self._mock_download(data)):
            with pytest.raises(EsgvocChecksumError):
                fetcher.download_db(artifact, target, show_progress=False)

        assert not target.exists()  # atomic: no partial file left

    def test_download_skipped_if_checksum_matches(self, tmp_path):
        data = b"already downloaded"
        checksum = _sha256_bytes(data)
        artifact = self._make_artifact(checksum=checksum)
        fetcher = DBFetcher(cache_dir=tmp_path)
        target = tmp_path / "cmip7-v2.1.0.db"
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

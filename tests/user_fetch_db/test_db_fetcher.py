"""
Tests for DBFetcher — version listing, snapshot lookup, download, checksum.

Network tests are marked `needs_network` and use the test registry URL.
All other tests mock HTTP responses.
"""
from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from esgvoc.core.db_snapshot import DBSnapshot
from esgvoc.core.db_fetcher import (
    DBFetcher,
    EsgvocChecksumError,
    EsgvocOfflineError,
    EsgvocVersionNotFoundError,
    _parse_version,
    _sha256,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_index(releases: list[dict]) -> dict:
    return {"releases": releases}


def _release(
    version: str,
    url: str = "https://example.com/file.db",
    checksum: str = "abc123",
    is_prerelease: bool = False,
) -> dict:
    return {
        "version": version,
        "url": url,
        "checksum_sha256": checksum,
        "size_bytes": 1024,
        "is_prerelease": is_prerelease,
        "published_at": "2026-01-01T00:00:00Z",
    }


def _mock_session(json_data: dict):
    """Return a mock requests.Session that returns json_data on .get()."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    session = MagicMock()
    session.get.return_value = resp
    return session


# ---------------------------------------------------------------------------
# Unit tests (no network)
# ---------------------------------------------------------------------------

class TestParseVersion:
    def test_stable_version(self):
        assert _parse_version("v1.2.3") == (1, 2, 3, 0)

    def test_without_v_prefix(self):
        assert _parse_version("1.2.3") == (1, 2, 3, 0)

    def test_prerelease_sorts_lower(self):
        stable = _parse_version("v1.0.0")
        pre = _parse_version("v1.0.0-rc1")
        assert stable > pre

    def test_none_on_invalid(self):
        assert _parse_version("dev-latest") is None
        assert _parse_version("") is None
        assert _parse_version(None) is None


class TestSha256:
    def test_sha256_matches_hashlib(self, tmp_path):
        f = tmp_path / "test.bin"
        f.write_bytes(b"hello world")
        expected = hashlib.sha256(b"hello world").hexdigest()
        assert _sha256(f) == expected


class TestOfflineMode:
    def test_offline_raises_on_list_versions(self, tmp_path):
        fetcher = DBFetcher(offline=True)
        with pytest.raises(EsgvocOfflineError):
            fetcher.list_versions("universe")

    def test_offline_env_var(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ESGVOC_OFFLINE", "true")
        fetcher = DBFetcher()
        with pytest.raises(EsgvocOfflineError):
            fetcher.list_versions("universe")


class TestVersionListing:
    def test_list_stable_versions(self, tmp_path):
        index = _make_index([
            _release("v2.0.0"),
            _release("v1.0.0"),
            _release("dev-latest", is_prerelease=True),
        ])
        fetcher = DBFetcher()
        fetcher._session = _mock_session(index)
        versions = fetcher.list_versions("universe")
        assert "v2.0.0" in versions
        assert "v1.0.0" in versions
        assert "dev-latest" not in versions

    def test_list_includes_prerelease_when_requested(self, tmp_path):
        index = _make_index([
            _release("v1.0.0"),
            _release("dev-latest", is_prerelease=True),
        ])
        fetcher = DBFetcher()
        fetcher._session = _mock_session(index)
        versions = fetcher.list_versions("universe", include_prerelease=True)
        assert "dev-latest" in versions

    def test_unknown_project_raises(self, tmp_path):
        fetcher = DBFetcher()
        with pytest.raises(EsgvocVersionNotFoundError):
            fetcher.list_versions("nonexistent_xyz")

    def test_stable_versions_sorted_newest_first(self, tmp_path):
        index = _make_index([
            _release("v1.0.0"),
            _release("v2.0.0"),
            _release("v1.5.0"),
        ])
        fetcher = DBFetcher()
        fetcher._session = _mock_session(index)
        versions = fetcher.list_versions("universe")
        assert versions[0] == "v2.0.0"


class TestGetSnapshot:
    def test_get_specific_version(self, tmp_path):
        index = _make_index([_release("v1.0.0"), _release("v2.0.0")])
        fetcher = DBFetcher()
        fetcher._session = _mock_session(index)
        art = fetcher.get_snapshot("universe", "v1.0.0")
        assert art.version == "v1.0.0"

    def test_get_latest_returns_newest_stable(self, tmp_path):
        index = _make_index([
            _release("v2.0.0"),
            _release("v1.0.0"),
            _release("dev-latest", is_prerelease=True),
        ])
        fetcher = DBFetcher()
        fetcher._session = _mock_session(index)
        art = fetcher.get_snapshot("universe", "latest")
        assert art.version == "v2.0.0"

    def test_version_not_found_raises(self, tmp_path):
        index = _make_index([_release("v1.0.0")])
        fetcher = DBFetcher()
        fetcher._session = _mock_session(index)
        with pytest.raises(EsgvocVersionNotFoundError):
            fetcher.get_snapshot("universe", "v99.0.0")

    def test_no_stable_releases_raises_for_latest(self, tmp_path):
        index = _make_index([_release("dev-latest", is_prerelease=True)])
        fetcher = DBFetcher()
        fetcher._session = _mock_session(index)
        with pytest.raises(EsgvocVersionNotFoundError):
            fetcher.get_snapshot("universe", "latest")



class TestDownload:
    def _make_snapshot(self, content: bytes, tmp_path: Path) -> DBSnapshot:
        checksum = hashlib.sha256(content).hexdigest()
        return DBSnapshot(
            project_id="universe",
            version="v1.0.0",
            download_url="https://example.com/universe-v1.0.0.db",
            checksum_sha256=checksum,
            size_bytes=len(content),
        )

    def test_download_writes_file(self, tmp_path):
        content = b"fake-db-content"
        snapshot = self._make_snapshot(content, tmp_path)
        target = tmp_path / "universe" / "v1.0.0.db"

        fetcher = DBFetcher()
        resp = MagicMock()
        resp.headers = {"content-length": str(len(content))}
        resp.iter_content.return_value = [content]
        resp.raise_for_status.return_value = None
        fetcher._session = MagicMock()
        fetcher._session.get.return_value = resp

        result = fetcher.download_db(snapshot, target, show_progress=False)
        assert result == target
        assert target.read_bytes() == content

    def test_download_skipped_if_checksum_matches(self, tmp_path):
        content = b"already-there"
        snapshot = self._make_snapshot(content, tmp_path)
        target = tmp_path / "universe" / "v1.0.0.db"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)

        fetcher = DBFetcher()
        fetcher._session = MagicMock()

        fetcher.download_db(snapshot, target, show_progress=False)
        fetcher._session.get.assert_not_called()

    def test_checksum_mismatch_raises(self, tmp_path):
        content = b"correct-content"
        snapshot = DBSnapshot(
            project_id="universe",
            version="v1.0.0",
            download_url="https://example.com/x.db",
            checksum_sha256="wrongchecksum000",
        )
        target = tmp_path / "universe" / "v1.0.0.db"

        fetcher = DBFetcher()
        resp = MagicMock()
        resp.headers = {"content-length": str(len(content))}
        resp.iter_content.return_value = [content]
        resp.raise_for_status.return_value = None
        fetcher._session = MagicMock()
        fetcher._session.get.return_value = resp

        with pytest.raises(EsgvocChecksumError):
            fetcher.download_db(snapshot, target, show_progress=False)

    def test_download_offline_raises(self, tmp_path):
        snapshot = DBSnapshot(
            project_id="universe", version="v1.0.0",
            download_url="https://example.com/x.db",
        )
        fetcher = DBFetcher(offline=True)
        with pytest.raises(EsgvocOfflineError):
            fetcher.download_db(snapshot, tmp_path / "out.db", show_progress=False)


# ---------------------------------------------------------------------------
# Network integration tests
# ---------------------------------------------------------------------------

@pytest.mark.needs_network
class TestNetworkFetch:
    """These tests require network access and the test registry to be live."""

    @pytest.fixture(autouse=True)
    def use_test_registry(self, monkeypatch, test_registry_url):
        monkeypatch.setenv("ESGVOC_REGISTRY_BASE_URL", test_registry_url)

    def test_list_universe_versions(self, tmp_path):
        fetcher = DBFetcher()
        versions = fetcher.list_versions("universe")
        assert len(versions) > 0
        assert any(v.startswith("v") for v in versions)

    def test_get_universe_v1_snapshot(self, tmp_path):
        fetcher = DBFetcher()
        art = fetcher.get_snapshot("universe", "v1.0.0")
        assert art.version == "v1.0.0"
        assert art.download_url.startswith("https://")

    def test_download_universe_v1(self, tmp_path):
        fetcher = DBFetcher()
        art = fetcher.get_snapshot("universe", "v1.0.0")
        target = tmp_path / "universe" / "v1.0.0.db"
        fetcher.download_db(art, target, show_progress=False)
        assert target.exists()
        assert target.stat().st_size > 0
        # Verify it's a readable SQLite file
        conn = sqlite3.connect(str(target))
        conn.execute("PRAGMA integrity_check").fetchone()
        conn.close()

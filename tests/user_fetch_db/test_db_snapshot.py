"""Tests for DBSnapshot — metadata model for versioned database snapshots."""
from datetime import datetime, timezone

from esgvoc.core.db_snapshot import DBSnapshot


class TestDBSnapshotBasics:
    def test_minimal_snapshot(self):
        s = DBSnapshot(
            project_id="cmip7",
            version="v1.0.0",
            download_url="https://example.com/cmip7-v1.0.0.db",
        )
        assert s.project_id == "cmip7"
        assert s.version == "v1.0.0"
        assert s.checksum_sha256 is None
        assert s.is_prerelease is False

    def test_full_snapshot(self):
        s = DBSnapshot(
            project_id="cmip7",
            version="v1.0.0",
            universe_version="v1.0.0",
            esgvoc_min_version="0.5.0",
            published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            size_bytes=1024 * 1024,
            checksum_sha256="abc123def456",
            download_url="https://example.com/cmip7-v1.0.0.db",
            release_notes="Initial release",
            commit_sha="deadbeef",
            is_prerelease=False,
        )
        assert s.universe_version == "v1.0.0"
        assert s.size_bytes == 1024 * 1024


class TestDBSnapshotMethods:
    def test_is_dev_build_false_for_stable(self):
        s = DBSnapshot(
            project_id="cmip7", version="v1.0.0",
            download_url="https://example.com/x.db",
        )
        assert s.is_dev_build() is False

    def test_is_dev_build_true_for_dev_latest(self):
        s = DBSnapshot(
            project_id="cmip7", version="dev-latest",
            download_url="https://example.com/x.db",
            is_prerelease=True,
        )
        assert s.is_dev_build() is True

    def test_is_dev_build_true_for_prerelease(self):
        s = DBSnapshot(
            project_id="cmip7", version="v1.0.0-rc1",
            download_url="https://example.com/x.db",
            is_prerelease=True,
        )
        assert s.is_dev_build() is True

    def test_db_filename_stable(self):
        s = DBSnapshot(
            project_id="cmip7", version="v1.0.0",
            download_url="https://example.com/x.db",
        )
        assert s.db_filename() == "v1.0.0.db"

    def test_db_filename_dev_latest(self):
        s = DBSnapshot(
            project_id="cmip7", version="dev-latest",
            download_url="https://example.com/x.db",
        )
        assert s.db_filename() == "dev-latest.db"

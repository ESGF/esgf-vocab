"""Tests for DBArtifact — metadata model for versioned database artifacts."""
from datetime import datetime, timezone

import pytest

from esgvoc.core.db_artifact import DBArtifact


class TestDBArtifactBasics:
    def test_minimal_artifact(self):
        a = DBArtifact(
            project_id="cmip7",
            version="v1.0.0",
            download_url="https://example.com/cmip7-v1.0.0.db",
        )
        assert a.project_id == "cmip7"
        assert a.version == "v1.0.0"
        assert a.checksum_sha256 is None
        assert a.is_prerelease is False

    def test_full_artifact(self):
        a = DBArtifact(
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
        assert a.universe_version == "v1.0.0"
        assert a.size_bytes == 1024 * 1024


class TestDBArtifactMethods:
    def test_is_dev_build_false_for_stable(self):
        a = DBArtifact(
            project_id="cmip7", version="v1.0.0",
            download_url="https://example.com/x.db",
        )
        assert a.is_dev_build() is False

    def test_is_dev_build_true_for_dev_latest(self):
        a = DBArtifact(
            project_id="cmip7", version="dev-latest",
            download_url="https://example.com/x.db",
            is_prerelease=True,
        )
        assert a.is_dev_build() is True

    def test_is_dev_build_true_for_prerelease(self):
        a = DBArtifact(
            project_id="cmip7", version="v1.0.0-rc1",
            download_url="https://example.com/x.db",
            is_prerelease=True,
        )
        assert a.is_dev_build() is True

    def test_db_filename_stable(self):
        a = DBArtifact(
            project_id="cmip7", version="v1.0.0",
            download_url="https://example.com/x.db",
        )
        assert a.db_filename() == "v1.0.0.db"

    def test_db_filename_dev_latest(self):
        a = DBArtifact(
            project_id="cmip7", version="dev-latest",
            download_url="https://example.com/x.db",
        )
        assert a.db_filename() == "dev-latest.db"

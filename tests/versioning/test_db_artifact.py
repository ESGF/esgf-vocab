"""Tests for DBArtifact model."""

from datetime import datetime, timezone

import pytest

from esgvoc.core.db_artifact import DBArtifact


class TestDBArtifactBasic:
    def test_minimal_creation(self):
        a = DBArtifact(
            project_id="cmip7",
            version="v2.1.0",
            download_url="https://example.com/cmip7.db",
        )
        assert a.project_id == "cmip7"
        assert a.version == "v2.1.0"
        assert a.is_prerelease is False

    def test_full_creation(self):
        a = DBArtifact(
            project_id="cmip7",
            version="v2.1.0",
            universe_version="v1.2.0",
            esgvoc_min_version="1.5.0",
            esgvoc_max_version=None,
            published_at=datetime(2024, 3, 25, tzinfo=timezone.utc),
            size_bytes=47185920,
            checksum_sha256="a1b2c3d4" * 8,
            download_url="https://example.com/cmip7.db",
            release_notes="Added new institution.",
            commit_sha="abc1234",
            is_prerelease=False,
        )
        assert a.universe_version == "v1.2.0"
        assert a.size_bytes == 47185920


class TestDBArtifactFilename:
    def test_stable_filename(self):
        a = DBArtifact(project_id="cmip7", version="v2.1.0", download_url="x")
        assert a.db_filename() == "cmip7-v2.1.0.db"

    def test_dev_filename(self):
        a = DBArtifact(project_id="cmip7", version="dev-latest", download_url="x", is_prerelease=True)
        assert a.db_filename() == "cmip7-dev-latest.db"

    def test_other_project(self):
        a = DBArtifact(project_id="cmip6", version="v6.5.0", download_url="x")
        assert a.db_filename() == "cmip6-v6.5.0.db"


class TestDBArtifactDevBuild:
    def test_dev_latest_is_dev(self):
        a = DBArtifact(project_id="cmip7", version="dev-latest", download_url="x", is_prerelease=True)
        assert a.is_dev_build() is True

    def test_prerelease_is_dev(self):
        a = DBArtifact(project_id="cmip7", version="v2.0.0-rc1", download_url="x", is_prerelease=True)
        assert a.is_dev_build() is True

    def test_stable_is_not_dev(self):
        a = DBArtifact(project_id="cmip7", version="v2.1.0", download_url="x")
        assert a.is_dev_build() is False

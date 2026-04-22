"""
Tests for DBBuilder — building databases from local CV repositories.

Local repo paths are resolved by the `repos_dir` fixture in conftest.py
(defaults to the parent of the project root; override with ESGVOC_REPOS_DIR).
Tests are skipped automatically when the repos are not present.

Markers used here:
  slow           — build_dev ingests a full CV repo (~15 s per test)
  needs_network  — remote builds that clone from GitHub
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from esgvoc.admin.builder import DBBuilder, BuildResult


class TestBuildResult:
    def test_summary_contains_project_id(self, tmp_path):
        from datetime import datetime, timezone
        result = BuildResult(
            output_path=tmp_path / "test.db",
            project_id="cmip6",
            cv_version="1.0.0",
            universe_version="1.0.0",
            commit_sha="abc123",
            universe_commit_sha="def456",
            build_date=datetime.now(timezone.utc),
            esgvoc_version="0.1.0",
            checksum_sha256="sha256hash",
            size_bytes=1024 * 1024,
        )
        summary = result.summary()
        assert "cmip6" in summary
        assert "1.0.0" in summary
        assert "sha256hash" in summary


class TestDBBuilderInit:
    def test_builder_instantiation(self, tmp_path):
        builder = DBBuilder(work_dir=tmp_path)
        assert builder is not None

    def test_builder_fail_on_missing_links_flag(self, tmp_path):
        builder = DBBuilder(work_dir=tmp_path, fail_on_missing_links=False)
        assert builder is not None


@pytest.mark.slow
class TestBuildDev:
    """
    Fully local build: both repos already on disk, no git clone needed.
    Uses build_dev() which takes direct local paths for both project and universe.
    Each test ingests a full CV repo — expect ~15 s per test.
    """

    def test_build_dev_produces_sqlite_file(
        self, tmp_path, skip_if_no_local_repos, universe_repo_path, cmip6_cvs_repo_path
    ):
        output = tmp_path / "cmip6.db"
        builder = DBBuilder(work_dir=tmp_path / "work", fail_on_missing_links=False)

        result = builder.build_dev(
            project_path=cmip6_cvs_repo_path,
            universe_path=universe_repo_path,
            output_path=output,
            manifest_overrides={"project_id": "cmip6", "cv_version": "test"},
        )

        assert result.output_path.exists()
        assert result.output_path.stat().st_size > 0

        conn = sqlite3.connect(str(result.output_path))
        conn.execute("PRAGMA integrity_check").fetchone()
        conn.close()

    def test_build_dev_embeds_metadata(
        self, tmp_path, skip_if_no_local_repos, universe_repo_path, cmip6_cvs_repo_path
    ):
        output = tmp_path / "cmip6.db"
        builder = DBBuilder(work_dir=tmp_path / "work", fail_on_missing_links=False)
        result = builder.build_dev(
            project_path=cmip6_cvs_repo_path,
            universe_path=universe_repo_path,
            output_path=output,
            manifest_overrides={"project_id": "cmip6", "cv_version": "test"},
        )

        conn = sqlite3.connect(str(result.output_path))
        rows = dict(conn.execute("SELECT key, value FROM _esgvoc_metadata").fetchall())
        conn.close()
        assert "project_id" in rows
        assert "cv_version" in rows
        assert "universe_version" in rows
        assert "build_date" in rows

    def test_build_dev_returns_checksum(
        self, tmp_path, skip_if_no_local_repos, universe_repo_path, cmip6_cvs_repo_path
    ):
        output = tmp_path / "cmip6.db"
        builder = DBBuilder(work_dir=tmp_path / "work", fail_on_missing_links=False)
        result = builder.build_dev(
            project_path=cmip6_cvs_repo_path,
            universe_path=universe_repo_path,
            output_path=output,
            manifest_overrides={"project_id": "cmip6", "cv_version": "test"},
        )
        assert result.checksum_sha256
        assert len(result.checksum_sha256) == 64  # SHA-256 hex string

    def test_build_dev_nonexistent_project_raises(
        self, tmp_path, skip_if_no_local_repos, universe_repo_path
    ):
        builder = DBBuilder(work_dir=tmp_path / "work")
        with pytest.raises(Exception):
            builder.build_dev(
                project_path=tmp_path / "nonexistent",
                universe_path=universe_repo_path,
                output_path=tmp_path / "out.db",
            )


@pytest.mark.needs_network
@pytest.mark.slow
class TestBuildRemote:
    """Build by cloning from GitHub — requires network access and is time-expensive."""

    def test_build_universe_from_github(self, tmp_path):
        """Build universe DB from GitHub using build_universe() — smoke test."""
        output = tmp_path / "universe.db"
        builder = DBBuilder(work_dir=tmp_path / "work", fail_on_missing_links=False)

        result = builder.build_universe(
            universe_repo="WCRP-CMIP/WCRP-universe",
            universe_ref="main",
            output_path=output,
        )
        assert result.output_path.exists()
        assert result.checksum_sha256

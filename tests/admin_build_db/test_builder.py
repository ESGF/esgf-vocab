"""
Tests for DBBuilder — building databases from local CV repositories.

Tests marked ``needs_real_repos`` require locally cloned CV repositories and
are excluded from the default run.  See conftest.py for full setup instructions.

Quick start
-----------
1. Clone the repos alongside esgf-vocab/ (the default location):

       git clone https://github.com/WCRP-CMIP/WCRP-universe
       git clone https://github.com/WCRP-CMIP/CMIP6_CVs
       git clone https://github.com/WCRP-CMIP/CMIP7_CVs

   If they live elsewhere, export ESGVOC_REPOS_DIR=/path/to/parent/dir

2. Run:

       uv run pytest -m needs_real_repos tests/admin_build_db/

Markers used here:
  needs_real_repos — requires local CV repo clones (excluded by default)
  slow             — time-expensive (~15 s per build test)
  needs_network    — remote builds that clone from GitHub
"""
from __future__ import annotations

import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from esgvoc.admin.builder import BuildResult, DBBuilder, _resolve_repo_url, _sha256


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_result(tmp_path: Path) -> BuildResult:
    return BuildResult(
        output_path=tmp_path / "out.db",
        project_id="test",
        cv_version="1.0",
        universe_version="1.0",
        commit_sha="abc123",
        universe_commit_sha="def456",
        build_date=datetime.now(timezone.utc),
        esgvoc_version="0.1.0",
        checksum_sha256="a" * 64,
        size_bytes=1024,
    )


def _make_sqlite(path: Path) -> None:
    """Create a minimal valid SQLite file at *path*."""
    conn = sqlite3.connect(str(path))
    conn.close()


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


@pytest.mark.needs_real_repos
@pytest.mark.slow
class TestBuildDevCmip6:
    """
    Fully local build using CMIP6_CVs + WCRP-universe.
    Each test ingests a full CV repo — expect ~15 s per test.
    Requires WCRP-universe/ and CMIP6_CVs/ clones (see conftest.py).
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
        assert rows["project_id"] == "cmip6"
        assert "cv_version" in rows
        assert "universe_version" in rows
        assert "build_date" in rows
        assert "esgvoc_version" in rows

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
        assert len(result.checksum_sha256) == 64

    def test_build_dev_result_fields(
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
        assert result.project_id == "cmip6"
        assert result.size_bytes > 0
        assert result.commit_sha is not None
        assert result.universe_commit_sha is not None
        assert "cmip6" in result.summary()


@pytest.mark.needs_real_repos
@pytest.mark.slow
class TestBuildDevCmip7:
    """
    Fully local build using CMIP7_CVs + WCRP-universe.
    Each test ingests a full CV repo — expect ~15 s per test.
    Requires WCRP-universe/ and CMIP7_CVs/ clones (see conftest.py).
    """

    def test_build_dev_produces_sqlite_file(
        self, tmp_path, skip_if_no_cmip7_repos, universe_repo_path, cmip7_cvs_repo_path
    ):
        output = tmp_path / "cmip7.db"
        builder = DBBuilder(work_dir=tmp_path / "work", fail_on_missing_links=False)
        result = builder.build_dev(
            project_path=cmip7_cvs_repo_path,
            universe_path=universe_repo_path,
            output_path=output,
            manifest_overrides={"project_id": "cmip7", "cv_version": "test"},
        )
        assert result.output_path.exists()
        assert result.output_path.stat().st_size > 0
        conn = sqlite3.connect(str(result.output_path))
        conn.execute("PRAGMA integrity_check").fetchone()
        conn.close()

    def test_build_dev_embeds_metadata(
        self, tmp_path, skip_if_no_cmip7_repos, universe_repo_path, cmip7_cvs_repo_path
    ):
        output = tmp_path / "cmip7.db"
        builder = DBBuilder(work_dir=tmp_path / "work", fail_on_missing_links=False)
        result = builder.build_dev(
            project_path=cmip7_cvs_repo_path,
            universe_path=universe_repo_path,
            output_path=output,
            manifest_overrides={"project_id": "cmip7", "cv_version": "test"},
        )
        conn = sqlite3.connect(str(result.output_path))
        rows = dict(conn.execute("SELECT key, value FROM _esgvoc_metadata").fetchall())
        conn.close()
        assert rows["project_id"] == "cmip7"
        assert "cv_version" in rows
        assert "build_date" in rows

    def test_build_dev_result_fields(
        self, tmp_path, skip_if_no_cmip7_repos, universe_repo_path, cmip7_cvs_repo_path
    ):
        output = tmp_path / "cmip7.db"
        builder = DBBuilder(work_dir=tmp_path / "work", fail_on_missing_links=False)
        result = builder.build_dev(
            project_path=cmip7_cvs_repo_path,
            universe_path=universe_repo_path,
            output_path=output,
            manifest_overrides={"project_id": "cmip7", "cv_version": "test"},
        )
        assert result.project_id == "cmip7"
        assert result.size_bytes > 0
        assert "cmip7" in result.summary()


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


# ---------------------------------------------------------------------------
# Module-level helpers — no repos needed
# ---------------------------------------------------------------------------

class TestResolveRepoUrl:
    def test_owner_repo_shorthand_becomes_github_https(self):
        url = _resolve_repo_url("WCRP-CMIP/WCRP-universe")
        assert url == "https://github.com/WCRP-CMIP/WCRP-universe.git"

    def test_full_https_url_passes_through(self):
        url = _resolve_repo_url("https://github.com/owner/repo.git")
        assert url == "https://github.com/owner/repo.git"

    def test_full_http_url_passes_through(self):
        url = _resolve_repo_url("http://internal.host/repo.git")
        assert url == "http://internal.host/repo.git"

    def test_absolute_local_path_raises(self):
        with pytest.raises(ValueError):
            _resolve_repo_url("/local/path/to/repo")

    def test_plain_name_without_slash_raises(self):
        with pytest.raises(ValueError):
            _resolve_repo_url("myrepo")


class TestSha256:
    def test_produces_64_char_hex(self, tmp_path):
        f = tmp_path / "data.bin"
        f.write_bytes(b"hello world")
        result = _sha256(f)
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_is_deterministic(self, tmp_path):
        f = tmp_path / "data.bin"
        f.write_bytes(b"deterministic content")
        assert _sha256(f) == _sha256(f)

    def test_different_content_different_hash(self, tmp_path):
        f1 = tmp_path / "a.bin"
        f2 = tmp_path / "b.bin"
        f1.write_bytes(b"aaa")
        f2.write_bytes(b"bbb")
        assert _sha256(f1) != _sha256(f2)


class TestEmbedMetadata:
    def test_writes_key_value_pairs(self, tmp_path):
        db = tmp_path / "test.db"
        DBBuilder._embed_metadata(db, {"project_id": "cmip7", "cv_version": "1.0"})
        conn = sqlite3.connect(str(db))
        rows = dict(conn.execute("SELECT key, value FROM _esgvoc_metadata").fetchall())
        conn.close()
        assert rows["project_id"] == "cmip7"
        assert rows["cv_version"] == "1.0"

    def test_overwrites_existing_key(self, tmp_path):
        db = tmp_path / "test.db"
        DBBuilder._embed_metadata(db, {"key": "old"})
        DBBuilder._embed_metadata(db, {"key": "new"})
        conn = sqlite3.connect(str(db))
        rows = dict(conn.execute("SELECT key, value FROM _esgvoc_metadata").fetchall())
        conn.close()
        assert rows["key"] == "new"

    def test_multiple_keys_stored(self, tmp_path):
        db = tmp_path / "test.db"
        meta = {"a": "1", "b": "2", "c": "3"}
        DBBuilder._embed_metadata(db, meta)
        conn = sqlite3.connect(str(db))
        rows = dict(conn.execute("SELECT key, value FROM _esgvoc_metadata").fetchall())
        conn.close()
        assert rows == meta


class TestGitSha:
    def test_returns_sha_for_valid_repo(self):
        # The esgf-vocab project itself is a git repo
        project_root = Path(__file__).parent.parent.parent
        sha = DBBuilder._git_sha(project_root)
        assert sha is not None
        assert len(sha) == 40
        assert all(c in "0123456789abcdef" for c in sha)

    def test_returns_none_for_nonexistent_dir(self, tmp_path):
        sha = DBBuilder._git_sha(tmp_path / "no_such_dir")
        assert sha is None

    def test_returns_none_for_non_git_dir(self, tmp_path):
        sha = DBBuilder._git_sha(tmp_path)
        assert sha is None


class TestTempWorkspace:
    def test_yields_existing_directory(self):
        builder = DBBuilder()
        with builder._temp_workspace() as tmp:
            assert tmp.exists()
            assert tmp.is_dir()

    def test_uses_work_dir_when_provided(self, tmp_path):
        work = tmp_path / "mywork"
        builder = DBBuilder(work_dir=work)
        with builder._temp_workspace() as tmp:
            assert tmp == work
            assert work.exists()

    def test_cleans_up_temp_dir_without_work_dir(self):
        builder = DBBuilder()
        with builder._temp_workspace() as tmp:
            p = tmp
        assert not p.exists()


class TestLog:
    def test_verbose_true_prints(self, capsys):
        builder = DBBuilder(verbose=True)
        builder._log("hello from log")
        out = capsys.readouterr().out
        assert "hello from log" in out

    def test_verbose_false_silent(self, capsys):
        builder = DBBuilder(verbose=False)
        builder._log("should not appear")
        out = capsys.readouterr().out
        assert out == ""


# ---------------------------------------------------------------------------
# build_dev / build_local path-validation errors — no repos needed
# ---------------------------------------------------------------------------

class TestBuildDevErrors:
    def test_nonexistent_project_raises(self, tmp_path):
        builder = DBBuilder(verbose=False)
        with pytest.raises(FileNotFoundError, match="Project path not found"):
            builder.build_dev(
                project_path=tmp_path / "no_project",
                universe_path=tmp_path,
                output_path=tmp_path / "out.db",
            )

    def test_nonexistent_universe_raises(self, tmp_path):
        builder = DBBuilder(verbose=False)
        with pytest.raises(FileNotFoundError, match="Universe path not found"):
            builder.build_dev(
                project_path=tmp_path,
                universe_path=tmp_path / "no_universe",
                output_path=tmp_path / "out.db",
            )

    def test_build_local_nonexistent_project_raises(self, tmp_path):
        builder = DBBuilder(verbose=False)
        with pytest.raises(FileNotFoundError, match="Project path not found"):
            builder.build_local(
                project_path=tmp_path / "no_project",
                universe_repo="owner/repo",
                universe_ref="main",
                output_path=tmp_path / "out.db",
            )


# ---------------------------------------------------------------------------
# build_local orchestration — mock _clone + _run_build (no network)
# ---------------------------------------------------------------------------

class TestBuildLocalOrchestration:
    def test_clone_called_once_for_universe(self, tmp_path):
        builder = DBBuilder(work_dir=tmp_path / "work", verbose=False)
        fake = _fake_result(tmp_path)
        with patch.object(builder, "_clone") as mock_clone, \
             patch.object(builder, "_run_build", return_value=fake):
            result = builder.build_local(
                project_path=tmp_path,
                universe_repo="WCRP-CMIP/WCRP-universe",
                universe_ref="main",
                output_path=tmp_path / "out.db",
            )
        mock_clone.assert_called_once()
        call_args = mock_clone.call_args[0]
        assert "WCRP-CMIP/WCRP-universe" in call_args
        assert result is fake

    def test_run_build_receives_paths(self, tmp_path):
        builder = DBBuilder(work_dir=tmp_path / "work", verbose=False)
        fake = _fake_result(tmp_path)
        with patch.object(builder, "_clone"), \
             patch.object(builder, "_run_build", return_value=fake) as mock_run:
            builder.build_local(
                project_path=tmp_path,
                universe_repo="WCRP-CMIP/WCRP-universe",
                universe_ref="main",
                output_path=tmp_path / "out.db",
                manifest_overrides={"project_id": "cmip6"},
            )
        _, kwargs = mock_run.call_args
        assert kwargs["manifest_overrides"] == {"project_id": "cmip6"}
        assert kwargs["project_path"] == tmp_path.resolve()


# ---------------------------------------------------------------------------
# build_remote orchestration — mock _clone + _run_build (no network)
# ---------------------------------------------------------------------------

class TestBuildRemoteOrchestration:
    def test_clone_called_twice(self, tmp_path):
        builder = DBBuilder(work_dir=tmp_path / "work", verbose=False)
        fake = _fake_result(tmp_path)
        with patch.object(builder, "_clone") as mock_clone, \
             patch.object(builder, "_run_build", return_value=fake):
            result = builder.build_remote(
                project_repo="WCRP-CMIP/CMIP6_CVs",
                project_ref="main",
                universe_repo="WCRP-CMIP/WCRP-universe",
                universe_ref="main",
                output_path=tmp_path / "out.db",
            )
        assert mock_clone.call_count == 2
        repos_cloned = [c[0][0] for c in mock_clone.call_args_list]
        assert "WCRP-CMIP/CMIP6_CVs" in repos_cloned
        assert "WCRP-CMIP/WCRP-universe" in repos_cloned
        assert result is fake

    def test_run_build_called_once(self, tmp_path):
        builder = DBBuilder(work_dir=tmp_path / "work", verbose=False)
        fake = _fake_result(tmp_path)
        with patch.object(builder, "_clone"), \
             patch.object(builder, "_run_build", return_value=fake) as mock_run:
            builder.build_remote(
                project_repo="WCRP-CMIP/CMIP6_CVs",
                project_ref="v1",
                universe_repo="WCRP-CMIP/WCRP-universe",
                universe_ref="v2",
                output_path=tmp_path / "out.db",
            )
        mock_run.assert_called_once()


# ---------------------------------------------------------------------------
# build_universe orchestration — mock _clone + _build_universe_db (no network)
# ---------------------------------------------------------------------------

class TestBuildUniverseOrchestration:
    def test_returns_build_result(self, tmp_path):
        builder = DBBuilder(work_dir=tmp_path / "work", verbose=False)
        output = tmp_path / "universe.db"

        def _fake_build_universe_db(universe_path, universe_db, universe_sha):
            _make_sqlite(universe_db)

        with patch.object(builder, "_clone"), \
             patch.object(builder, "_build_universe_db", side_effect=_fake_build_universe_db):
            result = builder.build_universe(
                universe_repo="WCRP-CMIP/WCRP-universe",
                universe_ref="main",
                output_path=output,
            )
        assert result.output_path == output
        assert result.project_id == "universe"
        assert output.exists()
        assert len(result.checksum_sha256) == 64

    def test_clone_called_once(self, tmp_path):
        builder = DBBuilder(work_dir=tmp_path / "work", verbose=False)
        output = tmp_path / "universe.db"

        def _fake_build_universe_db(universe_path, universe_db, universe_sha):
            _make_sqlite(universe_db)

        with patch.object(builder, "_clone") as mock_clone, \
             patch.object(builder, "_build_universe_db", side_effect=_fake_build_universe_db):
            builder.build_universe(
                universe_repo="WCRP-CMIP/WCRP-universe",
                universe_ref="main",
                output_path=output,
            )
        mock_clone.assert_called_once()

    def test_universe_version_in_metadata(self, tmp_path):
        builder = DBBuilder(work_dir=tmp_path / "work", verbose=False)
        output = tmp_path / "universe.db"

        def _fake_build_universe_db(universe_path, universe_db, universe_sha):
            _make_sqlite(universe_db)

        with patch.object(builder, "_clone"), \
             patch.object(builder, "_build_universe_db", side_effect=_fake_build_universe_db):
            result = builder.build_universe(
                universe_repo="WCRP-CMIP/WCRP-universe",
                universe_ref="main",
                output_path=output,
                universe_version="3.14",
            )
        assert result.cv_version == "3.14"
        assert result.universe_version == "3.14"
        conn = sqlite3.connect(str(output))
        rows = dict(conn.execute("SELECT key, value FROM _esgvoc_metadata").fetchall())
        conn.close()
        assert rows["universe_version"] == "3.14"

    def test_standalone_version_used_when_none(self, tmp_path):
        builder = DBBuilder(work_dir=tmp_path / "work", verbose=False)
        output = tmp_path / "universe.db"

        def _fake_build_universe_db(universe_path, universe_db, universe_sha):
            _make_sqlite(universe_db)

        with patch.object(builder, "_clone"), \
             patch.object(builder, "_build_universe_db", side_effect=_fake_build_universe_db):
            result = builder.build_universe(
                universe_repo="WCRP-CMIP/WCRP-universe",
                universe_ref="main",
                output_path=output,
            )
        assert result.cv_version == "standalone"


# ---------------------------------------------------------------------------
# _run_build manifest override branches (lines 335, 337, 339)
# ---------------------------------------------------------------------------

class TestRunBuildManifestOverrides:
    def _make_mocked_builder(self, tmp_path):
        builder = DBBuilder(work_dir=tmp_path, verbose=False)
        return builder

    def test_all_manifest_overrides_applied(self, tmp_path):
        builder = self._make_mocked_builder(tmp_path)
        output = tmp_path / "out.db"

        def _fake_universe_db(universe_path, universe_db, universe_sha):
            _make_sqlite(universe_db)

        def _fake_project_db(project_path, universe_path, universe_db, project_db, project_sha):
            _make_sqlite(project_db)

        with patch.object(builder, "_build_universe_db", side_effect=_fake_universe_db), \
             patch.object(builder, "_build_project_db", side_effect=_fake_project_db):
            result = builder._run_build(
                project_path=tmp_path,
                universe_path=tmp_path,
                project_sha="aaaa",
                universe_sha="bbbb",
                output_path=output,
                tmp=tmp_path,
                manifest_overrides={
                    "project_id": "myproject",
                    "cv_version": "9.9",
                    "universe_version": "8.8",
                    "esgvoc_min_version": "0.5",
                },
            )
        assert result.project_id == "myproject"
        assert result.cv_version == "9.9"
        assert result.universe_version == "8.8"
        conn = sqlite3.connect(str(output))
        rows = dict(conn.execute("SELECT key, value FROM _esgvoc_metadata").fetchall())
        conn.close()
        assert rows["project_id"] == "myproject"
        assert rows["cv_version"] == "9.9"
        assert rows["universe_version"] == "8.8"
        assert rows["esgvoc_min_version"] == "0.5"

    def test_partial_overrides_only_change_specified_fields(self, tmp_path):
        builder = self._make_mocked_builder(tmp_path)
        output = tmp_path / "out.db"

        def _fake_universe_db(universe_path, universe_db, universe_sha):
            _make_sqlite(universe_db)

        def _fake_project_db(project_path, universe_path, universe_db, project_db, project_sha):
            _make_sqlite(project_db)

        with patch.object(builder, "_build_universe_db", side_effect=_fake_universe_db), \
             patch.object(builder, "_build_project_db", side_effect=_fake_project_db):
            result = builder._run_build(
                project_path=tmp_path,
                universe_path=tmp_path,
                project_sha=None,
                universe_sha=None,
                output_path=output,
                tmp=tmp_path,
                manifest_overrides={"universe_version": "7.0"},
            )
        assert result.universe_version == "7.0"


# ---------------------------------------------------------------------------
# _clone — subprocess paths
# ---------------------------------------------------------------------------

class TestClone:
    def test_clone_success_calls_subprocess(self, tmp_path):
        builder = DBBuilder(verbose=False)
        dest = tmp_path / "clone_dest"
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            builder._clone("WCRP-CMIP/WCRP-universe", "main", dest)
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "git" in cmd
        assert "clone" in cmd
        assert "https://github.com/WCRP-CMIP/WCRP-universe.git" in cmd
        assert "main" in cmd

    def test_clone_failure_raises_runtime_error(self, tmp_path):
        builder = DBBuilder(verbose=False)
        dest = tmp_path / "clone_dest"
        error = subprocess.CalledProcessError(128, "git", stderr=b"repo not found")
        with patch("subprocess.run", side_effect=error):
            with pytest.raises(RuntimeError, match="Failed to clone"):
                builder._clone("WCRP-CMIP/WCRP-universe", "main", dest)

    def test_clone_failure_stderr_in_message(self, tmp_path):
        builder = DBBuilder(verbose=False)
        dest = tmp_path / "clone_dest"
        error = subprocess.CalledProcessError(128, "git", stderr=b"repo not found")
        with patch("subprocess.run", side_effect=error):
            with pytest.raises(RuntimeError, match="repo not found"):
                builder._clone("WCRP-CMIP/WCRP-universe", "main", dest)

    def test_clone_failure_no_stderr_still_raises(self, tmp_path):
        builder = DBBuilder(verbose=False)
        dest = tmp_path / "clone_dest"
        error = subprocess.CalledProcessError(128, "git", stderr=None)
        with patch("subprocess.run", side_effect=error):
            with pytest.raises(RuntimeError, match="Failed to clone"):
                builder._clone("WCRP-CMIP/WCRP-universe", "main", dest)


# ---------------------------------------------------------------------------
# Missing-links tracker raise paths (lines 413-415, 442-444)
# ---------------------------------------------------------------------------

class TestMissingLinksTrackerPaths:
    def test_build_universe_db_raises_on_missing_links(self, tmp_path):
        _sentinel = RuntimeError("missing links sentinel")

        mock_tracker = MagicMock()
        mock_tracker.has_missing_links.return_value = True
        mock_tracker.check_and_raise.side_effect = _sentinel

        builder = DBBuilder(fail_on_missing_links=True, verbose=False)
        universe_db = tmp_path / "universe.db"

        with patch("esgvoc.admin.builder.MissingLinksTracker", return_value=mock_tracker), \
             patch("esgvoc.core.db.models.universe.universe_create_db"), \
             patch("esgvoc.core.db.connection.DBConnection"), \
             patch("esgvoc.core.db.universe_ingestion.ingest_metadata_universe"), \
             patch("esgvoc.core.db.universe_ingestion.ingest_universe"):
            with pytest.raises(RuntimeError, match="missing links sentinel"):
                builder._build_universe_db(tmp_path, universe_db, "abc123")

        mock_tracker.has_missing_links.assert_called_once()
        mock_tracker.print_summary.assert_called_once()
        mock_tracker.check_and_raise.assert_called_once()

    def test_build_project_db_raises_on_missing_links(self, tmp_path):
        _sentinel = RuntimeError("missing links sentinel")

        mock_tracker = MagicMock()
        mock_tracker.has_missing_links.return_value = True
        mock_tracker.check_and_raise.side_effect = _sentinel

        builder = DBBuilder(fail_on_missing_links=True, verbose=False)
        universe_db = tmp_path / "universe.db"
        project_db = tmp_path / "project.db"
        _make_sqlite(universe_db)

        with patch("esgvoc.admin.builder.MissingLinksTracker", return_value=mock_tracker), \
             patch("esgvoc.core.db.models.project.project_create_db"), \
             patch("esgvoc.core.db.project_ingestion.ingest_project"):
            with pytest.raises(RuntimeError, match="missing links sentinel"):
                builder._build_project_db(
                    project_path=tmp_path,
                    universe_path=tmp_path,
                    universe_db=universe_db,
                    project_db=project_db,
                    project_sha="abc123",
                )

        mock_tracker.has_missing_links.assert_called_once()
        mock_tracker.print_summary.assert_called_once()
        mock_tracker.check_and_raise.assert_called_once()

    def test_no_raise_when_fail_on_missing_links_false(self, tmp_path):
        """When fail_on_missing_links=False, tracker is None — no raise even if links missing."""
        builder = DBBuilder(fail_on_missing_links=False, verbose=False)
        universe_db = tmp_path / "universe.db"

        with patch("esgvoc.admin.builder.MissingLinksTracker") as MockTracker, \
             patch("esgvoc.core.db.models.universe.universe_create_db"), \
             patch("esgvoc.core.db.connection.DBConnection"), \
             patch("esgvoc.core.db.universe_ingestion.ingest_metadata_universe"), \
             patch("esgvoc.core.db.universe_ingestion.ingest_universe"):
            builder._build_universe_db(tmp_path, universe_db, None)

        # MissingLinksTracker should never be instantiated when flag is False
        MockTracker.assert_not_called()

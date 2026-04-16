"""
User Tier — Multi-project installation and update scenarios.

Tests that two projects can coexist in the User Tier state, that
``esgvoc update`` (without a project argument) updates all installed
projects, and that ``esgvoc status --user`` reports all of them.

The second "project" is simulated by re-using the same real cmip6 DB
but registering it under a different project_id (``cmip6-copy``).  This
avoids the need for a second real network clone while still exercising
the multi-project state machine.

Plan scenarios covered:
  UT-16  Two projects installed simultaneously — both in state.json
  UT-17  Status --user shows both installed projects
  UT-18  update (all projects) downloads / activates for each project
  UT-19  remove one project — other project untouched
"""
from __future__ import annotations

import pytest
from typer.testing import CliRunner

from esgvoc.cli.install import app as install_app
from esgvoc.cli.remove import app as remove_app
from esgvoc.cli.status import app as status_app
from esgvoc.cli.update import app as update_app
from esgvoc.cli.versions import app as versions_app

from .conftest import fetcher_that_copies, install_real_db, runner


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PROJECT_A = "cmip6"
_PROJECT_B = "cmip6plus"   # second project id (re-uses same DB file)


def _install_two_projects(real_dbs):
    """
    Install both projects into the isolated home using the mock fetcher.
    Returns (pid_a, ver_a, pid_b, ver_b).
    """
    pid_a = real_dbs["project_id"]  # "cmip6"
    ver_a = real_dbs["v1_version"]
    pid_b = _PROJECT_B
    ver_b = real_dbs["v1_version"]  # same version string, different project

    ctx_a, _, _ = fetcher_that_copies(real_dbs["v1_path"], pid_a, ver_a)
    with ctx_a:
        runner.invoke(install_app, [pid_a])

    ctx_b, _, _ = fetcher_that_copies(real_dbs["v1_path"], pid_b, ver_b)
    with ctx_b:
        runner.invoke(install_app, [pid_b])

    return pid_a, ver_a, pid_b, ver_b


# ---------------------------------------------------------------------------
# UT-16  Two projects installed simultaneously
# ---------------------------------------------------------------------------

class TestTwoProjectsCoexist:
    """UT-16: Both projects appear in UserState after separate installs."""

    def test_both_projects_registered_in_state(self, real_dbs):
        pid_a, ver_a, pid_b, ver_b = _install_two_projects(real_dbs)

        from esgvoc.core.service.user_state import UserState
        state = UserState.load()

        assert ver_a in state.get_installed(pid_a), \
            f"{pid_a}@{ver_a} not found in installed"
        assert ver_b in state.get_installed(pid_b), \
            f"{pid_b}@{ver_b} not found in installed"

    def test_both_db_files_exist_on_disk(self, real_dbs):
        pid_a, ver_a, pid_b, ver_b = _install_two_projects(real_dbs)

        from esgvoc.core.service.user_state import UserState
        assert UserState.db_path(pid_a, ver_a).exists(), \
            f"DB for {pid_a}@{ver_a} missing on disk"
        assert UserState.db_path(pid_b, ver_b).exists(), \
            f"DB for {pid_b}@{ver_b} missing on disk"

    def test_both_projects_have_correct_active_version(self, real_dbs):
        pid_a, ver_a, pid_b, ver_b = _install_two_projects(real_dbs)

        from esgvoc.core.service.user_state import UserState
        state = UserState.load()

        assert state.get_active(pid_a) == ver_a
        assert state.get_active(pid_b) == ver_b

    def test_list_command_shows_both_projects(self, real_dbs):
        pid_a, ver_a, pid_b, ver_b = _install_two_projects(real_dbs)

        result = runner.invoke(versions_app, [])
        assert result.exit_code == 0, result.output
        assert pid_a in result.output
        assert pid_b in result.output


# ---------------------------------------------------------------------------
# UT-17  Status --user shows both projects
# ---------------------------------------------------------------------------

class TestStatusShowsBothProjects:
    """UT-17: esgvoc status --user lists all installed projects."""

    def test_status_user_contains_both_project_ids(self, real_dbs):
        pid_a, ver_a, pid_b, ver_b = _install_two_projects(real_dbs)

        result = runner.invoke(status_app, ["--user"])
        assert result.exit_code == 0, result.output
        assert pid_a in result.output
        assert pid_b in result.output

    def test_status_user_contains_active_versions(self, real_dbs):
        pid_a, ver_a, pid_b, ver_b = _install_two_projects(real_dbs)

        result = runner.invoke(status_app, ["--user"])
        assert result.exit_code == 0, result.output
        # Both active versions should appear in the status output
        assert ver_a in result.output
        assert ver_b in result.output

    def test_status_paths_shows_db_files_for_both(self, real_dbs):
        pid_a, ver_a, pid_b, ver_b = _install_two_projects(real_dbs)

        result = runner.invoke(status_app, ["--user", "--paths"])
        assert result.exit_code == 0, result.output
        assert ".db" in result.output


# ---------------------------------------------------------------------------
# UT-18  update (all projects)
# ---------------------------------------------------------------------------

class TestUpdateAllProjects:
    """UT-18: esgvoc update with no argument upgrades every installed project."""

    def test_update_all_reports_each_project(self, real_dbs):
        """update (no args) should process both installed projects."""
        pid_a = real_dbs["project_id"]
        ver_a = real_dbs["v1_version"]
        ver_a_new = real_dbs["v2_version"]
        pid_b = _PROJECT_B
        ver_b = real_dbs["v1_version"]
        ver_b_new = real_dbs["v2_version"]

        # Install v1 of both projects
        ctx_a, _, _ = fetcher_that_copies(real_dbs["v1_path"], pid_a, ver_a)
        with ctx_a:
            runner.invoke(install_app, [pid_a])

        ctx_b, _, _ = fetcher_that_copies(real_dbs["v1_path"], pid_b, ver_b)
        with ctx_b:
            runner.invoke(install_app, [pid_b])

        # Now update both: fetcher returns v2 as "latest"
        from unittest.mock import patch, MagicMock
        import hashlib, shutil
        from esgvoc.core.db_artifact import DBArtifact

        def _make_mock_fetcher(db_path, pid, ver):
            checksum = hashlib.sha256(db_path.read_bytes()).hexdigest()
            artifact = DBArtifact(
                project_id=pid, version=ver,
                download_url=f"https://example.com/{pid}-{ver}.db",
                checksum_sha256=checksum, size_bytes=db_path.stat().st_size,
                is_prerelease=False,
            )
            mock = MagicMock()
            mock.get_artifact.return_value = artifact
            mock.list_versions.return_value = [ver]

            def _copy(art, target, **kw):
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(db_path), str(target))

            mock.download_db.side_effect = _copy
            return mock

        # The update CLI constructs a single DBFetcher instance; we need it to
        # return v2 for both project ids.  Use a factory side_effect on the class.
        fetcher_a = _make_mock_fetcher(real_dbs["v2_path"], pid_a, ver_a_new)
        fetcher_b = _make_mock_fetcher(real_dbs["v2_path"], pid_b, ver_b_new)

        call_count = [0]
        def _fetcher_factory(*args, **kwargs):
            call_count[0] += 1
            # Return the same mock that handles both projects
            combined = MagicMock()
            def _get_artifact(pid, version="latest"):
                if pid == pid_a:
                    return fetcher_a.get_artifact(pid_a, version)
                return fetcher_b.get_artifact(pid_b, version)
            combined.get_artifact.side_effect = _get_artifact
            combined.download_db.side_effect = fetcher_a.download_db
            return combined

        with patch("esgvoc.core.db_fetcher.DBFetcher", side_effect=_fetcher_factory):
            result = runner.invoke(update_app, [])

        assert result.exit_code == 0, result.output
        # Both projects should be mentioned in the update output
        assert pid_a in result.output
        assert pid_b in result.output

    def test_update_all_when_nothing_installed_exits_0(self):
        """update with no projects installed should exit 0 with a hint."""
        result = runner.invoke(update_app, [])
        assert result.exit_code == 0, result.output
        assert "no projects" in result.output.lower()


# ---------------------------------------------------------------------------
# UT-19  remove one project — other untouched
# ---------------------------------------------------------------------------

class TestRemoveOneProjectLeavesOther:
    """UT-19: Removing one project does not affect the other."""

    def test_remove_first_project_leaves_second_installed(self, real_dbs):
        pid_a, ver_a, pid_b, ver_b = _install_two_projects(real_dbs)

        result = runner.invoke(remove_app, [f"{pid_a}@{ver_a}", "--yes"])
        assert result.exit_code == 0, result.output

        from esgvoc.core.service.user_state import UserState
        state = UserState.load()

        # project A should be gone
        assert ver_a not in state.get_installed(pid_a)
        # project B should be intact
        assert ver_b in state.get_installed(pid_b)

    def test_remove_first_project_db_file_deleted(self, real_dbs):
        pid_a, ver_a, pid_b, ver_b = _install_two_projects(real_dbs)

        from esgvoc.core.service.user_state import UserState
        db_a = UserState.db_path(pid_a, ver_a)
        db_b = UserState.db_path(pid_b, ver_b)

        runner.invoke(remove_app, [f"{pid_a}@{ver_a}", "--yes"])

        assert not db_a.exists(), f"DB for removed project still exists: {db_a}"
        assert db_b.exists(), f"DB for kept project was deleted: {db_b}"

    def test_status_after_partial_remove_shows_remaining(self, real_dbs):
        pid_a, ver_a, pid_b, ver_b = _install_two_projects(real_dbs)

        runner.invoke(remove_app, [f"{pid_a}@{ver_a}", "--yes"])

        result = runner.invoke(status_app, ["--user"])
        assert result.exit_code == 0, result.output
        # pid_b should still appear
        assert pid_b in result.output

    def test_remove_all_versions_of_one_project(self, real_dbs):
        """remove --all on one project should leave the other intact."""
        pid_a, ver_a, pid_b, ver_b = _install_two_projects(real_dbs)

        result = runner.invoke(remove_app, [pid_a, "--all", "--yes"])
        assert result.exit_code == 0, result.output

        from esgvoc.core.service.user_state import UserState
        state = UserState.load()
        assert state.get_installed(pid_a) == [], f"{pid_a} still has installed versions"
        assert ver_b in state.get_installed(pid_b), f"{pid_b} was affected by remove --all"

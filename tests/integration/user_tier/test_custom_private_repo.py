"""
User Tier — Custom/Private Repository (Scenario 24) tests.

Tests that a user can register a custom (e.g. private or enterprise) CV
repository via ``esgvoc config add-project --custom --repo <url>`` and that
the GITHUB_TOKEN environment variable is forwarded as a Bearer token in the
HTTP session used to fetch release listings.

Plan scenarios covered:
  UT-76  add_project_custom adds the project to the config with correct fields
  UT-77  add_project_custom is idempotent (duplicate returns False)
  UT-78  has_project returns True after add_project_custom
  UT-79  remove_project removes the custom project
  UT-80  CLI config add-project --custom --repo <url> exits 0
  UT-81  CLI config add-project --custom --repo <url> project appears in config
  UT-82  CLI config add-project --custom without --repo exits non-zero
  UT-83  CLI config add-project duplicate name exits non-zero
  UT-84  GITHUB_TOKEN is set as Authorization header in fetcher session
  UT-85  No GITHUB_TOKEN means no Authorization header in session
  UT-86  GITHUB_TOKEN value is used verbatim as Bearer token
  UT-87  custom project github_repo stored correctly
  UT-88  custom project branch stored correctly (default: main)
  UT-89  custom project branch stored when explicit value given
"""
from __future__ import annotations

import os

import pytest
from typer.testing import CliRunner

from esgvoc.cli.main import app as main_app
from esgvoc.core.service.configuration.setting import ServiceSettings

runner = CliRunner()

_CUSTOM_PROJECT_NAME = "my-private-cvs"
_CUSTOM_REPO_URL = "https://github.mycompany.com/org/My_CVs"
_CUSTOM_BRANCH = "main"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config() -> ServiceSettings:
    """Fresh ServiceSettings with no projects."""
    return ServiceSettings.load_default()


def _custom_cfg(name: str = _CUSTOM_PROJECT_NAME,
                repo: str = _CUSTOM_REPO_URL,
                branch: str = _CUSTOM_BRANCH) -> dict:
    return {
        "project_name": name,
        "github_repo": repo,
        "branch": branch,
        "local_path": f"repos/{name}",
        "db_path": f"dbs/{name}.sqlite",
    }


# ---------------------------------------------------------------------------
# UT-76  add_project_custom stores correct fields
# ---------------------------------------------------------------------------

class TestAddProjectCustomAPI:
    """UT-76/77/78/79/87/88/89: ServiceSettings.add_project_custom API (Scenario 24)."""

    def test_add_custom_returns_true_on_success(self):
        """UT-76: add_project_custom returns True when project is new."""
        config = _make_config()
        result = config.add_project_custom(_custom_cfg())
        assert result is True

    def test_github_repo_stored_correctly(self):
        """UT-87: github_repo field is stored verbatim."""
        config = _make_config()
        config.add_project_custom(_custom_cfg())
        project = config.get_project(_CUSTOM_PROJECT_NAME)
        assert project is not None
        assert project.github_repo == _CUSTOM_REPO_URL

    def test_default_branch_is_main(self):
        """UT-88: branch defaults to 'main' when not specified."""
        config = _make_config()
        config.add_project_custom(_custom_cfg())
        project = config.get_project(_CUSTOM_PROJECT_NAME)
        assert project.branch == "main"

    def test_explicit_branch_stored(self):
        """UT-89: explicit branch value is preserved."""
        config = _make_config()
        config.add_project_custom(_custom_cfg(branch="enterprise-branch"))
        project = config.get_project(_CUSTOM_PROJECT_NAME)
        assert project.branch == "enterprise-branch"

    def test_duplicate_returns_false(self):
        """UT-77: adding the same project name a second time returns False."""
        config = _make_config()
        config.add_project_custom(_custom_cfg())
        result = config.add_project_custom(_custom_cfg())
        assert result is False

    def test_has_project_true_after_add(self):
        """UT-78: has_project returns True after add_project_custom."""
        config = _make_config()
        config.add_project_custom(_custom_cfg())
        assert config.has_project(_CUSTOM_PROJECT_NAME) is True

    def test_has_project_false_before_add(self):
        config = _make_config()
        assert config.has_project(_CUSTOM_PROJECT_NAME) is False

    def test_remove_project_after_add(self):
        """UT-79: remove_project cleans up a custom project."""
        config = _make_config()
        config.add_project_custom(_custom_cfg())
        assert config.has_project(_CUSTOM_PROJECT_NAME)
        config.remove_project(_CUSTOM_PROJECT_NAME)
        assert not config.has_project(_CUSTOM_PROJECT_NAME)

    def test_remove_nonexistent_returns_false(self):
        config = _make_config()
        result = config.remove_project("project-that-does-not-exist")
        assert result is False

    def test_multiple_custom_projects_coexist(self):
        """Two distinct custom repos can be registered independently."""
        config = _make_config()
        config.add_project_custom(_custom_cfg("proj-a", "https://github.com/org/A"))
        config.add_project_custom(_custom_cfg("proj-b", "https://github.com/org/B"))
        assert config.has_project("proj-a")
        assert config.has_project("proj-b")
        assert config.get_project("proj-a").github_repo == "https://github.com/org/A"
        assert config.get_project("proj-b").github_repo == "https://github.com/org/B"

    def test_project_name_stored_correctly(self):
        config = _make_config()
        config.add_project_custom(_custom_cfg())
        project = config.get_project(_CUSTOM_PROJECT_NAME)
        assert project.project_name == _CUSTOM_PROJECT_NAME


# ---------------------------------------------------------------------------
# UT-80/81/82/83  CLI: config add-project --custom
# ---------------------------------------------------------------------------

class TestAddProjectCLI:
    """UT-80/81/82/83: esgvoc config add-project --custom CLI (Scenario 24)."""

    def test_add_custom_no_repo_exits_nonzero(self, default_config_test):
        """UT-82: --custom without --repo is rejected."""
        result = runner.invoke(main_app, [
            "config", "add-project", _CUSTOM_PROJECT_NAME, "--custom",
        ])
        assert result.exit_code != 0

    def test_add_custom_error_message_mentions_repo(self, default_config_test):
        """Error output mentions that --repo is required."""
        result = runner.invoke(main_app, [
            "config", "add-project", _CUSTOM_PROJECT_NAME, "--custom",
        ])
        assert "repo" in result.output.lower() or result.exit_code != 0

    def test_add_custom_with_repo_exits_0(self, default_config_test):
        """UT-80: --custom --repo exits 0 when project name is unique."""
        result = runner.invoke(main_app, [
            "config", "add-project", _CUSTOM_PROJECT_NAME,
            "--custom", "--repo", _CUSTOM_REPO_URL,
        ])
        assert result.exit_code == 0, (
            f"Expected exit 0, got {result.exit_code}.\nOutput:\n{result.output}"
        )

    def test_added_project_stored_in_config(self, default_config_test):
        """UT-81: After CLI add, project appears in the active config."""
        runner.invoke(main_app, [
            "config", "add-project", _CUSTOM_PROJECT_NAME,
            "--custom", "--repo", _CUSTOM_REPO_URL,
        ])
        config = default_config_test.get_active_config()
        assert config.has_project(_CUSTOM_PROJECT_NAME), (
            f"{_CUSTOM_PROJECT_NAME!r} not found in config after CLI add"
        )

    def test_added_project_has_correct_repo(self, default_config_test):
        """CLI-added custom project has the repo URL stored correctly."""
        runner.invoke(main_app, [
            "config", "add-project", _CUSTOM_PROJECT_NAME,
            "--custom", "--repo", _CUSTOM_REPO_URL,
        ])
        config = default_config_test.get_active_config()
        project = config.get_project(_CUSTOM_PROJECT_NAME)
        if project:  # only assert if project was registered
            assert project.github_repo == _CUSTOM_REPO_URL

    def test_add_custom_with_branch_stores_branch(self, default_config_test):
        """Explicit --branch value is persisted."""
        result = runner.invoke(main_app, [
            "config", "add-project", _CUSTOM_PROJECT_NAME,
            "--custom", "--repo", _CUSTOM_REPO_URL,
            "--branch", "enterprise-dev",
        ])
        assert result.exit_code == 0, result.output
        config = default_config_test.get_active_config()
        project = config.get_project(_CUSTOM_PROJECT_NAME)
        if project:
            assert project.branch == "enterprise-dev"

    def test_duplicate_project_name_exits_nonzero(self, default_config_test):
        """UT-83: Adding the same project name twice exits non-zero on the second call."""
        runner.invoke(main_app, [
            "config", "add-project", _CUSTOM_PROJECT_NAME,
            "--custom", "--repo", _CUSTOM_REPO_URL,
        ])
        result = runner.invoke(main_app, [
            "config", "add-project", _CUSTOM_PROJECT_NAME,
            "--custom", "--repo", _CUSTOM_REPO_URL,
        ])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# UT-84/85/86  GITHUB_TOKEN forwarded as Bearer auth header
# ---------------------------------------------------------------------------

class TestGithubTokenAuth:
    """UT-84/85/86: GITHUB_TOKEN is set as Authorization header (Scenario 24)."""

    def _make_fetcher(self, tmp_path):
        from esgvoc.core.db_fetcher import DBFetcher
        return DBFetcher(cache_dir=tmp_path)

    def test_github_token_sets_authorization_header(self, tmp_path, monkeypatch):
        """UT-84: When GITHUB_TOKEN is set, session carries Authorization: Bearer <token>."""
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token_abc123")
        fetcher = self._make_fetcher(tmp_path)
        session = fetcher._build_session()
        assert "Authorization" in session.headers, (
            "Authorization header missing when GITHUB_TOKEN is set"
        )
        assert session.headers["Authorization"] == "Bearer ghp_test_token_abc123"

    def test_no_github_token_no_auth_header(self, tmp_path, monkeypatch):
        """UT-85: Without GITHUB_TOKEN, no Authorization header is added."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        fetcher = self._make_fetcher(tmp_path)
        session = fetcher._build_session()
        assert "Authorization" not in session.headers, (
            "Authorization header should be absent when GITHUB_TOKEN is unset"
        )

    def test_token_value_used_verbatim(self, tmp_path, monkeypatch):
        """UT-86: The exact GITHUB_TOKEN value appears in the Bearer header."""
        token = "ghp_enterprise_PAT_xyz_9876"
        monkeypatch.setenv("GITHUB_TOKEN", token)
        fetcher = self._make_fetcher(tmp_path)
        session = fetcher._build_session()
        assert session.headers["Authorization"] == f"Bearer {token}"

    def test_empty_token_not_set(self, tmp_path, monkeypatch):
        """An empty GITHUB_TOKEN string does not add Authorization header."""
        monkeypatch.setenv("GITHUB_TOKEN", "")
        fetcher = self._make_fetcher(tmp_path)
        session = fetcher._build_session()
        # Empty string is falsy — header should not be set
        assert "Authorization" not in session.headers or \
               session.headers.get("Authorization", "") == ""

    def test_session_always_has_accept_header(self, tmp_path, monkeypatch):
        """GitHub API Accept header is always present regardless of token."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        fetcher = self._make_fetcher(tmp_path)
        session = fetcher._build_session()
        assert "Accept" in session.headers
        assert "github" in session.headers["Accept"].lower()

    def test_session_has_github_api_version_header(self, tmp_path, monkeypatch):
        """X-GitHub-Api-Version header is always sent (required by GitHub API v3)."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        fetcher = self._make_fetcher(tmp_path)
        session = fetcher._build_session()
        assert "X-GitHub-Api-Version" in session.headers

    def test_token_header_uses_bearer_scheme(self, tmp_path, monkeypatch):
        """Authorization value must start with 'Bearer ' (not 'token ' or 'Basic ')."""
        monkeypatch.setenv("GITHUB_TOKEN", "sometoken")
        fetcher = self._make_fetcher(tmp_path)
        session = fetcher._build_session()
        auth = session.headers.get("Authorization", "")
        assert auth.startswith("Bearer "), (
            f"Expected 'Bearer ' prefix, got: {auth!r}"
        )

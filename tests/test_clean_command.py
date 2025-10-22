"""
Tests for the clean CLI command functionality.
"""

import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from esgvoc.cli.clean import app
from esgvoc.core.service.configuration.setting import ProjectSettings, ServiceSettings, UniverseSettings


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def temp_dirs():
    """Create temporary directories for testing."""
    temp_base = tempfile.mkdtemp()

    # Create test repository and database directories
    universe_repo = Path(temp_base) / "universe_repo"
    universe_db = Path(temp_base) / "universe.db"
    project_repo = Path(temp_base) / "project_repo"
    project_db = Path(temp_base) / "project.db"

    # Create the directories and files
    universe_repo.mkdir(parents=True)
    (universe_repo / "test_file.txt").write_text("universe content")
    universe_db.write_text("universe db content")

    project_repo.mkdir(parents=True)
    (project_repo / "test_file.txt").write_text("project content")
    project_db.write_text("project db content")

    yield {
        "base": temp_base,
        "universe_repo": str(universe_repo),
        "universe_db": str(universe_db),
        "project_repo": str(project_repo),
        "project_db": str(project_db)
    }

    # Cleanup
    shutil.rmtree(temp_base, ignore_errors=True)


@pytest.fixture
def mock_settings(temp_dirs):
    """Create mock settings for testing."""
    universe_settings = Mock(spec=UniverseSettings)
    universe_settings.get_absolute_local_path.return_value = temp_dirs["universe_repo"]
    universe_settings.get_absolute_db_path.return_value = temp_dirs["universe_db"]

    project_settings = Mock(spec=ProjectSettings)
    project_settings.get_absolute_local_path.return_value = temp_dirs["project_repo"]
    project_settings.get_absolute_db_path.return_value = temp_dirs["project_db"]

    settings = Mock(spec=ServiceSettings)
    settings.universe = universe_settings
    settings.projects = {"test_project": project_settings}

    return settings


class TestCleanRepos:
    def test_clean_repos_success(self, runner, mock_settings, temp_dirs):
        """Test successful repository cleaning."""
        with patch("esgvoc.cli.clean.config_manager") as mock_config:
            mock_config.get_active_config.return_value = mock_settings

            result = runner.invoke(app, ["repos", "--force"])

            assert result.exit_code == 0
            assert "✓ Cleaned 2 repositories:" in result.stdout
            assert "Universe repository:" in result.stdout
            assert "Project 'test_project' repository:" in result.stdout

            # Verify repositories were actually deleted
            assert not Path(temp_dirs["universe_repo"]).exists()
            assert not Path(temp_dirs["project_repo"]).exists()
            # Verify databases still exist
            assert Path(temp_dirs["universe_db"]).exists()
            assert Path(temp_dirs["project_db"]).exists()

    def test_clean_repos_with_config(self, runner, mock_settings):
        """Test cleaning repos with specific config."""
        with patch("esgvoc.cli.clean.config_manager") as mock_config:
            mock_config.get_config.return_value = mock_settings

            result = runner.invoke(app, ["repos", "--config", "test_config", "--force"])

            assert result.exit_code == 0
            mock_config.get_config.assert_called_once_with("test_config")

    def test_clean_repos_no_repos_found(self, runner, temp_dirs):
        """Test when no repositories exist to clean."""
        # Delete the test repos first
        shutil.rmtree(temp_dirs["universe_repo"])
        shutil.rmtree(temp_dirs["project_repo"])

        universe_settings = Mock(spec=UniverseSettings)
        universe_settings.get_absolute_local_path.return_value = temp_dirs["universe_repo"]

        project_settings = Mock(spec=ProjectSettings)
        project_settings.get_absolute_local_path.return_value = temp_dirs["project_repo"]

        settings = Mock(spec=ServiceSettings)
        settings.universe = universe_settings
        settings.projects = {"test_project": project_settings}

        with patch("esgvoc.cli.clean.config_manager") as mock_config:
            mock_config.get_active_config.return_value = settings

            result = runner.invoke(app, ["repos", "--force"])

            assert result.exit_code == 0
            assert "No repositories found to clean" in result.stdout


class TestCleanDbs:
    def test_clean_dbs_success(self, runner, mock_settings, temp_dirs):
        """Test successful database cleaning."""
        with patch("esgvoc.cli.clean.config_manager") as mock_config:
            mock_config.get_active_config.return_value = mock_settings

            result = runner.invoke(app, ["dbs", "--force"])

            assert result.exit_code == 0
            assert "✓ Cleaned 2 databases:" in result.stdout
            assert "Universe database:" in result.stdout
            assert "Project 'test_project' database:" in result.stdout

            # Verify databases were actually deleted
            assert not Path(temp_dirs["universe_db"]).exists()
            assert not Path(temp_dirs["project_db"]).exists()
            # Verify repositories still exist
            assert Path(temp_dirs["universe_repo"]).exists()
            assert Path(temp_dirs["project_repo"]).exists()

    def test_clean_dbs_no_dbs_found(self, runner, temp_dirs):
        """Test when no databases exist to clean."""
        # Delete the test dbs first
        os.remove(temp_dirs["universe_db"])
        os.remove(temp_dirs["project_db"])

        universe_settings = Mock(spec=UniverseSettings)
        universe_settings.get_absolute_db_path.return_value = temp_dirs["universe_db"]

        project_settings = Mock(spec=ProjectSettings)
        project_settings.get_absolute_db_path.return_value = temp_dirs["project_db"]

        settings = Mock(spec=ServiceSettings)
        settings.universe = universe_settings
        settings.projects = {"test_project": project_settings}

        with patch("esgvoc.cli.clean.config_manager") as mock_config:
            mock_config.get_active_config.return_value = settings

            result = runner.invoke(app, ["dbs", "--force"])

            assert result.exit_code == 0
            assert "No databases found to clean" in result.stdout


class TestCleanAll:
    def test_clean_all_success(self, runner, mock_settings, temp_dirs):
        """Test successful cleaning of both repositories and databases."""
        with patch("esgvoc.cli.clean.config_manager") as mock_config:
            mock_config.get_active_config.return_value = mock_settings

            result = runner.invoke(app, ["all", "--force"])

            assert result.exit_code == 0
            assert "✓ Cleaned 4 items:" in result.stdout
            assert "Repositories (2):" in result.stdout
            assert "Databases (2):" in result.stdout

            # Verify everything was deleted
            assert not Path(temp_dirs["universe_repo"]).exists()
            assert not Path(temp_dirs["project_repo"]).exists()
            assert not Path(temp_dirs["universe_db"]).exists()
            assert not Path(temp_dirs["project_db"]).exists()


class TestCleanComponent:
    def test_clean_component_universe_repos(self, runner, mock_settings, temp_dirs):
        """Test cleaning universe component repositories only."""
        with patch("esgvoc.cli.clean.config_manager") as mock_config:
            mock_config.get_active_config.return_value = mock_settings

            result = runner.invoke(app, ["component", "universe", "--what", "repos", "--force"])

            assert result.exit_code == 0
            assert "✓ Cleaned 1 items for component 'universe':" in result.stdout
            assert "Repository:" in result.stdout

            # Verify only universe repo was deleted
            assert not Path(temp_dirs["universe_repo"]).exists()
            assert Path(temp_dirs["project_repo"]).exists()
            assert Path(temp_dirs["universe_db"]).exists()
            assert Path(temp_dirs["project_db"]).exists()

    def test_clean_component_project_dbs(self, runner, mock_settings, temp_dirs):
        """Test cleaning specific project databases only."""
        with patch("esgvoc.cli.clean.config_manager") as mock_config:
            mock_config.get_active_config.return_value = mock_settings

            result = runner.invoke(app, ["component", "test_project", "--what", "dbs", "--force"])

            assert result.exit_code == 0
            assert "✓ Cleaned 1 items for component 'test_project':" in result.stdout
            assert "Database:" in result.stdout

            # Verify only project db was deleted
            assert Path(temp_dirs["universe_repo"]).exists()
            assert Path(temp_dirs["project_repo"]).exists()
            assert Path(temp_dirs["universe_db"]).exists()
            assert not Path(temp_dirs["project_db"]).exists()

    def test_clean_component_invalid_component(self, runner, mock_settings):
        """Test error when component doesn't exist."""
        with patch("esgvoc.cli.clean.config_manager") as mock_config:
            mock_config.get_active_config.return_value = mock_settings

            result = runner.invoke(app, ["component", "nonexistent", "--force"])

            assert result.exit_code == 1
            assert "Component 'nonexistent' not found" in result.stdout

    def test_clean_component_invalid_what(self, runner, mock_settings):
        """Test error when invalid --what option is provided."""
        with patch("esgvoc.cli.clean.config_manager") as mock_config:
            mock_config.get_active_config.return_value = mock_settings

            result = runner.invoke(app, ["component", "universe", "--what", "invalid", "--force"])

            assert result.exit_code == 1
            assert "Invalid value for --what: invalid" in result.stdout


class TestCleanConfirmation:
    def test_clean_repos_confirmation_cancelled(self, runner, mock_settings):
        """Test that operation is cancelled when user declines confirmation."""
        with patch("esgvoc.cli.clean.config_manager") as mock_config:
            with patch("esgvoc.cli.clean.Confirm.ask", return_value=False):
                mock_config.get_active_config.return_value = mock_settings

                result = runner.invoke(app, ["repos"])

                assert result.exit_code == 0
                assert "Operation cancelled" in result.stdout

    def test_clean_repos_confirmation_accepted(self, runner, mock_settings):
        """Test that operation proceeds when user accepts confirmation."""
        with patch("esgvoc.cli.clean.config_manager") as mock_config:
            with patch("esgvoc.cli.clean.Confirm.ask", return_value=True):
                mock_config.get_active_config.return_value = mock_settings

                result = runner.invoke(app, ["repos"])

                assert result.exit_code == 0
                assert "Operation cancelled" not in result.stdout


class TestCleanErrors:
    def test_clean_repos_config_error(self, runner):
        """Test error handling when config loading fails."""
        with patch("esgvoc.cli.clean.config_manager") as mock_config:
            mock_config.get_active_config.side_effect = Exception("Config error")

            result = runner.invoke(app, ["repos", "--force"])

            assert result.exit_code == 1
            assert "Error: Config error" in result.stdout
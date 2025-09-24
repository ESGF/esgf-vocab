import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import toml
from typer.testing import CliRunner
from platformdirs import PlatformDirs

# Import your actual CLI app - adjust this import path
from esgvoc.cli.config import app  # Replace with your actual CLI module path
from esgvoc.core.service.configuration.setting import ServiceSettings



class MockConfigManager:
    """Mock config manager for testing without actual service dependencies."""

    def __init__(self, config_dir: Path, active_config: str = "default"):
        self.config_dir = config_dir
        self.data_config_dir = str(config_dir.parent / "data")  # Add missing attribute
        self.active_config = active_config
        self.configs = {}
        self._target_config = None  # Track which config is being modified
        self._load_configs()

    def _load_configs(self):
        """Load all config files from directory."""
        for config_file in self.config_dir.glob("*.toml"):
            config_name = config_file.stem
            self.configs[config_name] = str(config_file)

    def list_configs(self):
        """Return dictionary of config names to paths."""
        self._load_configs()  # Reload to pick up new files
        return self.configs.copy()

    def get_active_config_name(self):
        """Return the name of the active configuration."""
        return self.active_config

    def get_config(self, name: str):
        """Load and return a configuration."""
        if name not in self.configs:
            raise FileNotFoundError(f"Configuration '{name}' not found")

        config_path = self.configs[name]
        return ServiceSettings.load_from_file(config_path)

    def add_config(self, name: str, config_data: dict):
        """Add a new configuration."""
        config_path = self.config_dir / f"{name}.toml"
        with open(config_path, "w") as f:
            toml.dump(config_data, f)
        self.configs[name] = str(config_path)

    def remove_config(self, name: str):
        """Remove a configuration."""
        if name in self.configs:
            config_path = Path(self.configs[name])
            if config_path.exists():
                config_path.unlink()
            del self.configs[name]

            # If we removed the active config, switch to default
            if self.active_config == name:
                self.active_config = "default"

    def switch_config(self, name: str):
        """Switch to a different configuration."""
        if name not in self.configs:
            raise ValueError(f"Configuration '{name}' not found")
        self.active_config = name

    def save_active_config(self, config: ServiceSettings):
        """Save the active configuration."""
        config_path = self.configs[self.active_config]
        config.save_to_file(config_path)

    def save_config_by_name(self, config: ServiceSettings, config_name: str):
        """Save a specific configuration by name."""
        if config_name in self.configs:
            config_path = self.configs[config_name]
            config.save_to_file(config_path)


class TestConfigCLI:
    """Test suite for configuration CLI commands."""

    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Set up a fresh test environment for each test."""
        # Create temporary directory for test configs
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir) / "configs"
        self.config_dir.mkdir(parents=True)

        # Create test configuration files
        self.default_config_path = self.config_dir / "default.toml"
        self.test_config_path = self.config_dir / "test.toml"

        # Create default configuration with only the default projects (cmip6, cmip6plus)
        # Using relative paths that will be automatically converted to absolute by ServiceSettings
        default_config_data = {
            "universe": {
                "github_repo": "https://github.com/WCRP-CMIP/WCRP-universe",
                "branch": "esgvoc",
                "local_path": "repos/WCRP-universe",
                "db_path": "dbs/universe.sqlite",
            },
            "projects": [
                {
                    "project_name": "cmip6",
                    "github_repo": "https://github.com/WCRP-CMIP/CMIP6_CVs",
                    "branch": "esgvoc",
                    "local_path": "repos/CMIP6_CVs",
                    "db_path": "dbs/cmip6.sqlite",
                },
                {
                    "project_name": "cmip6plus",
                    "github_repo": "https://github.com/WCRP-CMIP/CMIP6Plus_CVs",
                    "branch": "esgvoc",
                    "local_path": "repos/CMIP6Plus_CVs",
                    "db_path": "dbs/cmip6plus.sqlite",
                },
            ],
        }

        with open(self.default_config_path, "w") as f:
            toml.dump(default_config_data, f)

        # Create test configuration (copy of default)
        shutil.copy(self.default_config_path, self.test_config_path)

        # Create mock config manager
        self.mock_config_manager = MockConfigManager(self.config_dir, "default")

        # Set up CLI runner
        self.runner = CliRunner()

        yield

        # Cleanup
        shutil.rmtree(self.temp_dir)

    def _patch_service_calls(self):
        """Context manager to patch service calls with our mock."""
        # Create a mock state object with synchronize_all method
        mock_state = type("MockState", (), {"synchronize_all": lambda *args, **kwargs: None})()

        # Create a mock service module
        mock_service = MagicMock()
        mock_service.get_config_manager.return_value = self.mock_config_manager
        mock_service.current_state = mock_state
        mock_service.get_state.return_value = mock_state

        # Mock the get_service function to return our mock service
        return patch("esgvoc.cli.config.get_service", return_value=mock_service)

    # Configuration Management Tests
    def test_list_configs(self):
        """Test listing available configurations."""
        with self._patch_service_calls():
            result = self.runner.invoke(app, ["list"])

            assert result.exit_code == 0
            assert "Available Configurations" in result.stdout
            assert "default" in result.stdout
            assert "test" in result.stdout

    def test_show_active_config(self):
        """Test showing the active configuration."""
        with self._patch_service_calls():
            result = self.runner.invoke(app, ["show"])

            assert result.exit_code == 0
            assert "Showing active configuration: default" in result.stdout
            assert 'project_name = "cmip6"' in result.stdout
            assert 'project_name = "cmip6plus"' in result.stdout

    def test_show_specific_config(self):
        """Test showing a specific configuration."""
        with self._patch_service_calls():
            result = self.runner.invoke(app, ["show", "test"])

            assert result.exit_code == 0
            assert 'project_name = "cmip6"' in result.stdout
            assert 'project_name = "cmip6plus"' in result.stdout

    def test_show_nonexistent_config(self):
        """Test showing a configuration that doesn't exist."""
        with self._patch_service_calls():
            result = self.runner.invoke(app, ["show", "nonexistent"])

            assert result.exit_code == 1
            assert "Configuration 'nonexistent' not found" in result.stdout

    def test_switch_config(self):
        """Test switching to a different configuration."""
        with self._patch_service_calls():
            result = self.runner.invoke(app, ["switch", "test"])

            assert result.exit_code == 0
            assert "Successfully switched to configuration: test" in result.stdout
            assert self.mock_config_manager.active_config == "test"

    def test_switch_nonexistent_config(self):
        """Test switching to a configuration that doesn't exist."""
        with self._patch_service_calls():
            result = self.runner.invoke(app, ["switch", "nonexistent"])

            assert result.exit_code == 1
            assert "Configuration 'nonexistent' not found" in result.stdout

    # Configuration Creation and Removal Tests
    def test_create_config_default(self):
        """Test creating a new configuration from default."""
        with self._patch_service_calls():
            result = self.runner.invoke(app, ["create", "new_config"])

            assert result.exit_code == 0
            assert "Successfully created configuration: new_config" in result.stdout

            # Verify the config file was created
            new_config_path = self.config_dir / "new_config.toml"
            assert new_config_path.exists()

            # Verify content is correct
            with open(new_config_path) as f:
                data = toml.load(f)
            assert len(data["projects"]) == 2  # Default projects
            assert any(p["project_name"] == "cmip6" for p in data["projects"])
            assert any(p["project_name"] == "cmip6plus" for p in data["projects"])

    def test_create_config_from_base(self):
        """Test creating a new configuration from an existing one."""
        with self._patch_service_calls():
            result = self.runner.invoke(app, ["create", "new_config", "--base", "test"])

            assert result.exit_code == 0
            assert "Successfully created configuration: new_config" in result.stdout

            # Verify the config file was created
            new_config_path = self.config_dir / "new_config.toml"
            assert new_config_path.exists()

    def test_create_config_with_switch(self):
        """Test creating a new configuration and switching to it."""
        with self._patch_service_calls():
            result = self.runner.invoke(app, ["create", "new_config", "--switch"])

            assert result.exit_code == 0
            assert "Successfully created configuration: new_config" in result.stdout
            assert "Switched to configuration: new_config" in result.stdout
            assert self.mock_config_manager.active_config == "new_config"

    def test_create_existing_config(self):
        """Test creating a configuration that already exists."""
        with self._patch_service_calls():
            result = self.runner.invoke(app, ["create", "default"])

            assert result.exit_code == 1
            assert "Configuration 'default' already exists" in result.stdout

    def test_create_config_nonexistent_base(self):
        """Test creating a configuration from a nonexistent base."""
        with self._patch_service_calls():
            result = self.runner.invoke(app, ["create", "new_config", "--base", "nonexistent"])

            assert result.exit_code == 1
            assert "Base configuration 'nonexistent' not found" in result.stdout

    def test_remove_config(self):
        """Test removing a configuration."""
        with self._patch_service_calls():
            # Create a config to remove
            result = self.runner.invoke(app, ["create", "to_remove"])
            assert result.exit_code == 0

            # Remove it
            result = self.runner.invoke(app, ["remove", "to_remove"], input="y\n")

            assert result.exit_code == 0
            assert "Successfully removed configuration: to_remove" in result.stdout

            # Verify it's gone
            removed_path = self.config_dir / "to_remove.toml"
            assert not removed_path.exists()

    def test_remove_config_cancel(self):
        """Test canceling configuration removal."""
        with self._patch_service_calls():
            result = self.runner.invoke(app, ["remove", "test"], input="n\n")

            assert result.exit_code == 0
            assert "Operation cancelled" in result.stdout

            # Verify config still exists
            assert self.test_config_path.exists()

    def test_remove_default_config(self):
        """Test that default configuration cannot be removed."""
        with self._patch_service_calls():
            result = self.runner.invoke(app, ["remove", "default"])

            assert result.exit_code == 1
            assert "Cannot remove the default configuration" in result.stdout

    def test_remove_active_config(self):
        """Test removing the active configuration switches to default."""
        with self._patch_service_calls():
            # Switch to test config
            self.runner.invoke(app, ["switch", "test"])

            # Remove the active config
            result = self.runner.invoke(app, ["remove", "test"], input="y\n")

            assert result.exit_code == 0
            assert "Successfully removed configuration: test" in result.stdout

    # Project Listing Tests
    def test_list_available_projects(self):
        """Test listing available default projects."""
        with self._patch_service_calls():
            result = self.runner.invoke(app, ["list-available-projects"])

            assert result.exit_code == 0
            assert "Available Default Projects" in result.stdout
            assert "cmip6" in result.stdout
            assert "cmip6plus" in result.stdout
            assert "input4mip" in result.stdout
            assert "obs4ref" in result.stdout

    def test_list_projects(self):
        """Test listing projects in active configuration."""
        with self._patch_service_calls():
            result = self.runner.invoke(app, ["list-projects"])

            assert result.exit_code == 0
            assert "Projects in Configuration: default" in result.stdout
            assert "cmip6" in result.stdout
            assert "cmip6plus" in result.stdout

    def test_list_projects_specific_config(self):
        """Test listing projects in a specific configuration."""
        with self._patch_service_calls():
            result = self.runner.invoke(app, ["list-projects", "--config", "test"])

            assert result.exit_code == 0
            assert "Projects in Configuration: test" in result.stdout
            assert "cmip6" in result.stdout
            assert "cmip6plus" in result.stdout

    def test_list_projects_empty_config(self):
        """Test listing projects in a configuration with no projects."""
        # Create empty config
        empty_config_data = {
            "universe": {
                "github_repo": "https://github.com/WCRP-CMIP/WCRP-universe",
                "branch": "esgvoc",
                "local_path": "repos/WCRP-universe",
                "db_path": "dbs/universe.sqlite",
            },
            "projects": [],
        }

        empty_config_path = self.config_dir / "empty.toml"
        with open(empty_config_path, "w") as f:
            toml.dump(empty_config_data, f)

        with self._patch_service_calls():
            result = self.runner.invoke(app, ["list-projects", "--config", "empty"])

            assert result.exit_code == 0
            assert "No projects found in configuration 'empty'" in result.stdout

    # Project Addition Tests
    def test_add_project_from_default(self):
        """Test adding a project from default configuration."""
        with self._patch_service_calls():
            result = self.runner.invoke(app, ["add-project", "input4mip"])

            assert result.exit_code == 0
            assert "Successfully added default project input4mip" in result.stdout

            # Verify project was added to file
            with open(self.default_config_path) as f:
                data = toml.load(f)

            project_names = [p["project_name"] for p in data["projects"]]
            assert "input4mip" in project_names
            assert len(data["projects"]) == 3  # Original 2 + 1 new

    def test_add_project_custom(self):
        """Test adding a custom project."""
        with self._patch_service_calls():
            result = self.runner.invoke(
                app,
                [
                    "add-project",
                    "custom_project",
                    "--custom",
                    "--repo",
                    "https://github.com/test/custom",
                    "--branch",
                    "main",
                    "--local",
                    "repos/custom",
                    "--db",
                    "dbs/custom.sqlite",
                ],
            )

            assert result.exit_code == 0
            assert "Successfully added custom project custom_project" in result.stdout

            # Verify project was added
            with open(self.default_config_path) as f:
                data = toml.load(f)

            custom_project = next((p for p in data["projects"] if p["project_name"] == "custom_project"), None)
            assert custom_project is not None
            assert custom_project["github_repo"] == "https://github.com/test/custom"
            assert custom_project["branch"] == "main"
            assert custom_project["local_path"] == "repos/custom"
            assert custom_project["db_path"] == "dbs/custom.sqlite"

    def test_add_project_custom_minimal(self):
        """Test adding a custom project with minimal parameters."""
        with self._patch_service_calls():
            result = self.runner.invoke(
                app, ["add-project", "minimal_project", "--custom", "--repo", "https://github.com/test/minimal"]
            )

            assert result.exit_code == 0
            assert "Successfully added custom project minimal_project" in result.stdout

            # Verify default paths were set
            with open(self.default_config_path) as f:
                data = toml.load(f)

            project = next((p for p in data["projects"] if p["project_name"] == "minimal_project"), None)
            assert project is not None
            assert project["local_path"] == "repos/minimal_project"
            assert project["db_path"] == "dbs/minimal_project.sqlite"
            assert project["branch"] == "main"

    def test_add_project_already_exists(self):
        """Test adding a project that already exists."""
        with self._patch_service_calls():
            result = self.runner.invoke(app, ["add-project", "cmip6"])

            assert result.exit_code == 1
            assert "Project 'cmip6' already exists" in result.stdout

    def test_add_project_invalid_default(self):
        """Test adding an invalid default project."""
        with self._patch_service_calls():
            result = self.runner.invoke(app, ["add-project", "invalid_project"])

            assert result.exit_code == 1
            # The exact error message might vary, so check for key parts
            assert "not a valid default project" in result.stdout or "Unknown project" in result.stdout

    def test_add_project_custom_without_repo(self):
        """Test adding a custom project without specifying repository."""
        with self._patch_service_calls():
            result = self.runner.invoke(app, ["add-project", "no_repo", "--custom"])

            assert result.exit_code == 1
            assert "--repo is required when adding custom projects" in result.stdout

    # Project Removal Tests
    def test_remove_project(self):
        """Test removing a project."""
        with self._patch_service_calls():
            result = self.runner.invoke(app, ["remove-project", "cmip6"], input="y\n")

            assert result.exit_code == 0
            assert "Successfully removed project cmip6" in result.stdout

            # Verify project was removed
            with open(self.default_config_path) as f:
                data = toml.load(f)

            project_names = [p["project_name"] for p in data["projects"]]
            assert "cmip6" not in project_names
            assert "cmip6plus" in project_names  # Other project should remain

    def test_remove_project_force(self):
        """Test removing a project with force flag."""
        with self._patch_service_calls():
            result = self.runner.invoke(app, ["remove-project", "cmip6", "--force"])

            assert result.exit_code == 0
            assert "Successfully removed project cmip6" in result.stdout

            # Verify project was removed
            with open(self.default_config_path) as f:
                data = toml.load(f)

            project_names = [p["project_name"] for p in data["projects"]]
            assert "cmip6" not in project_names

    def test_remove_project_cancel(self):
        """Test canceling project removal."""
        with self._patch_service_calls():
            result = self.runner.invoke(app, ["remove-project", "cmip6"], input="n\n")

            assert result.exit_code == 0
            assert "Operation cancelled" in result.stdout

            # Verify project still exists
            with open(self.default_config_path) as f:
                data = toml.load(f)

            project_names = [p["project_name"] for p in data["projects"]]
            assert "cmip6" in project_names

    def test_remove_nonexistent_project(self):
        """Test removing a project that doesn't exist."""
        with self._patch_service_calls():
            result = self.runner.invoke(app, ["remove-project", "nonexistent"])

            assert result.exit_code == 1
            assert "Project 'nonexistent' not found" in result.stdout

    # Project Update Tests
    def test_update_project(self):
        """Test updating project settings."""
        with self._patch_service_calls():
            result = self.runner.invoke(
                app,
                [
                    "update-project",
                    "cmip6",
                    "--repo",
                    "https://github.com/new/repo",
                    "--branch",
                    "new_branch",
                    "--local",
                    "repos/new_path",
                    "--db",
                    "dbs/new.sqlite",
                ],
            )

            assert result.exit_code == 0
            assert "Successfully updated project cmip6" in result.stdout

            # Verify changes were saved
            with open(self.default_config_path) as f:
                data = toml.load(f)

            project = next((p for p in data["projects"] if p["project_name"] == "cmip6"), None)
            assert project is not None
            assert project["github_repo"] == "https://github.com/new/repo"
            assert project["branch"] == "new_branch"
            assert project["local_path"] == "repos/new_path"
            assert project["db_path"] == "dbs/new.sqlite"

    def test_update_project_partial(self):
        """Test updating only some project settings."""
        with self._patch_service_calls():
            result = self.runner.invoke(app, ["update-project", "cmip6", "--branch", "develop"])

            assert result.exit_code == 0
            assert "Successfully updated project cmip6" in result.stdout

            # Verify only branch was changed
            with open(self.default_config_path) as f:
                data = toml.load(f)

            project = next((p for p in data["projects"] if p["project_name"] == "cmip6"), None)
            assert project["branch"] == "develop"
            # Unchanged
            assert project["github_repo"] == "https://github.com/WCRP-CMIP/CMIP6_CVs"

    def test_update_nonexistent_project(self):
        """Test updating a project that doesn't exist."""
        with self._patch_service_calls():
            result = self.runner.invoke(app, ["update-project", "nonexistent", "--branch", "test"])

            assert result.exit_code == 1
            assert "Project 'nonexistent' not found" in result.stdout

    def test_update_project_no_changes(self):
        """Test updating a project without specifying any changes."""
        with self._patch_service_calls():
            result = self.runner.invoke(app, ["update-project", "cmip6"])

            assert result.exit_code == 0
            assert "No updates specified" in result.stdout

    # Settings Modification Tests
    def test_set_universe_settings(self):
        """Test setting universe configuration."""
        with self._patch_service_calls():
            result = self.runner.invoke(
                app, ["set", "universe:branch=new_branch", "universe:local_path=repos/new_universe"]
            )

            assert result.exit_code == 0
            assert "Updated universe.branch = new_branch" in result.stdout
            assert "Updated universe.local_path = repos/new_universe" in result.stdout

            # Verify changes were saved
            with open(self.default_config_path) as f:
                data = toml.load(f)

            assert data["universe"]["branch"] == "new_branch"
            assert data["universe"]["local_path"] == "repos/new_universe"

    def test_set_project_settings(self):
        """Test setting project configuration."""
        with self._patch_service_calls():
            result = self.runner.invoke(app, ["set", "cmip6:branch=test_branch", "cmip6:local_path=repos/test"])

            assert result.exit_code == 0
            assert "Updated cmip6.branch = test_branch" in result.stdout
            assert "Updated cmip6.local_path = repos/test" in result.stdout

            # Verify changes were saved
            with open(self.default_config_path) as f:
                data = toml.load(f)

            project = next((p for p in data["projects"] if p["project_name"] == "cmip6"), None)
            assert project["branch"] == "test_branch"
            assert project["local_path"] == "repos/test"

    def test_set_invalid_format(self):
        """Test set command with invalid format."""
        with self._patch_service_calls():
            result = self.runner.invoke(app, ["set", "invalid_format"])

            assert result.exit_code == 0
            assert "Invalid change format 'invalid_format'" in result.stdout

    def test_set_unknown_component(self):
        """Test set command with unknown component."""
        with self._patch_service_calls():
            result = self.runner.invoke(app, ["set", "unknown:setting=value"])

            assert result.exit_code == 0
            assert "Component 'unknown' not found in configuration" in result.stdout

    # NEW: Simple config command tests
    def test_debug_commands_available(self):
        """Debug test to check if new commands are available."""
        with self._patch_service_calls():
            result = self.runner.invoke(app, ["--help"])

            # Check if the new commands are in the help output
            assert result.exit_code == 0
            assert "add" in result.stdout or "Commands:" in result.stdout

    def test_config_add_single_project(self):
        """Test adding a single project using the simple 'add' command."""
        with self._patch_service_calls():
            result = self.runner.invoke(app, ["add", "input4mip"])

            assert result.exit_code == 0
            assert "✓ Added project input4mip" in result.stdout
            assert "✓ Successfully installed CVs" in result.stdout

            # Verify project was added
            with open(self.default_config_path) as f:
                data = toml.load(f)

            project_names = [p["project_name"] for p in data["projects"]]
            assert "input4mip" in project_names
            assert len(data["projects"]) == 3  # Original 2 + 1 new

    def test_config_add_multiple_projects(self):
        """Test adding multiple projects using the simple 'add' command."""
        with self._patch_service_calls():
            result = self.runner.invoke(app, ["add", "input4mip", "obs4ref", "cordex-cmip6"])

            assert result.exit_code == 0
            assert "✓ Added project input4mip" in result.stdout
            assert "✓ Added project obs4ref" in result.stdout
            assert "✓ Added project cordex-cmip6" in result.stdout
            assert "Successfully added 3 project(s)" in result.stdout
            assert "✓ Successfully installed CVs for all added projects" in result.stdout

            # Verify all projects were added
            with open(self.default_config_path) as f:
                data = toml.load(f)

            project_names = [p["project_name"] for p in data["projects"]]
            assert "input4mip" in project_names
            assert "obs4ref" in project_names
            assert "cordex-cmip6" in project_names
            assert len(data["projects"]) == 5  # Original 2 + 3 new

    def test_config_add_existing_project(self):
        """Test adding a project that already exists."""
        with self._patch_service_calls():
            result = self.runner.invoke(app, ["add", "cmip6"])

            assert result.exit_code == 0
            assert "⚠ Project 'cmip6' already exists - skipping" in result.stdout
            assert "Skipped 1 existing project(s)" in result.stdout

    def test_config_add_mixed_valid_invalid(self):
        """Test adding a mix of valid, invalid, and existing projects."""
        with self._patch_service_calls():
            result = self.runner.invoke(app, ["add", "input4mip", "cmip6", "invalid_project", "obs4ref"])

            assert result.exit_code == 0
            assert "✓ Added project input4mip" in result.stdout
            assert "✓ Added project obs4ref" in result.stdout
            assert "⚠ Project 'cmip6' already exists - skipping" in result.stdout
            assert "✗ Invalid project 'invalid_project'" in result.stdout
            assert "Successfully added 2 project(s)" in result.stdout
            assert "Skipped 1 existing project(s)" in result.stdout
            assert "Invalid project(s): invalid_project" in result.stdout

    def test_config_add_all_invalid(self):
        """Test adding only invalid projects."""
        with self._patch_service_calls():
            result = self.runner.invoke(app, ["add", "invalid1", "invalid2"])

            assert result.exit_code == 1
            # The error message format from the actual implementation
            assert "✗ Invalid project 'invalid1'" in result.stdout
            assert "✗ Invalid project 'invalid2'" in result.stdout
            assert "Invalid project(s): invalid1, invalid2" in result.stdout

    def test_config_rm_single_project(self):
        """Test removing a single project using the simple 'rm' command."""
        with self._patch_service_calls():
            result = self.runner.invoke(app, ["rm", "cmip6"], input="y\n")

            assert result.exit_code == 0
            assert "✓ Removed cmip6 from configuration" in result.stdout
            assert "Successfully removed 1 project(s): cmip6" in result.stdout

            # Verify project was removed
            with open(self.default_config_path) as f:
                data = toml.load(f)

            project_names = [p["project_name"] for p in data["projects"]]
            assert "cmip6" not in project_names
            assert "cmip6plus" in project_names  # Other project should remain

    def test_config_rm_multiple_projects(self):
        """Test removing multiple projects using the simple 'rm' command."""
        with self._patch_service_calls():
            result = self.runner.invoke(app, ["rm", "cmip6", "cmip6plus"], input="y\n")

            assert result.exit_code == 0
            assert "Projects to remove: cmip6, cmip6plus" in result.stdout
            assert "✓ Removed cmip6 from configuration" in result.stdout
            assert "✓ Removed cmip6plus from configuration" in result.stdout
            assert "Successfully removed 2 project(s): cmip6, cmip6plus" in result.stdout

            # Verify all projects were removed
            with open(self.default_config_path) as f:
                data = toml.load(f)

            project_names = [p["project_name"] for p in data["projects"]]
            assert "cmip6" not in project_names
            assert "cmip6plus" not in project_names
            assert len(data["projects"]) == 0

    def test_config_rm_with_force(self):
        """Test removing projects with force flag (no confirmation)."""
        with self._patch_service_calls():
            result = self.runner.invoke(app, ["rm", "cmip6", "cmip6plus", "--force"])

            assert result.exit_code == 0
            assert "Successfully removed 2 project(s): cmip6, cmip6plus" in result.stdout

            # Verify projects were removed
            with open(self.default_config_path) as f:
                data = toml.load(f)

            assert len(data["projects"]) == 0

    def test_config_rm_with_keep_files(self):
        """Test removing projects with keep-files flag."""
        with self._patch_service_calls():
            result = self.runner.invoke(app, ["rm", "cmip6", "--force", "--keep-files"])

            assert result.exit_code == 0
            assert "✓ Removed cmip6 from configuration" in result.stdout
            # Should not see file deletion messages when using --keep-files
            assert "✓ Deleted repository:" not in result.stdout
            assert "✓ Deleted database:" not in result.stdout

    def test_config_rm_cancel(self):
        """Test canceling project removal."""
        with self._patch_service_calls():
            result = self.runner.invoke(app, ["rm", "cmip6"], input="n\n")

            assert result.exit_code == 0
            assert "Operation cancelled" in result.stdout

            # Verify project still exists
            with open(self.default_config_path) as f:
                data = toml.load(f)

            project_names = [p["project_name"] for p in data["projects"]]
            assert "cmip6" in project_names

    def test_config_rm_nonexistent_projects(self):
        """Test removing projects that don't exist."""
        with self._patch_service_calls():
            result = self.runner.invoke(app, ["rm", "nonexistent1", "nonexistent2"])

            assert result.exit_code == 1
            assert "✗ Project 'nonexistent1' not found in configuration" in result.stdout
            assert "✗ Project 'nonexistent2' not found in configuration" in result.stdout
            assert "No valid projects to remove" in result.stdout

    def test_config_rm_mixed_valid_invalid(self):
        """Test removing a mix of valid and invalid projects."""
        with self._patch_service_calls():
            result = self.runner.invoke(app, ["rm", "cmip6", "nonexistent", "cmip6plus"], input="y\n")

            assert result.exit_code == 0
            assert "✗ Project 'nonexistent' not found in configuration" in result.stdout
            assert "Projects to remove: cmip6, cmip6plus" in result.stdout
            assert "✓ Removed cmip6 from configuration" in result.stdout
            assert "✓ Removed cmip6plus from configuration" in result.stdout
            assert "Successfully removed 2 project(s): cmip6, cmip6plus" in result.stdout

    def test_config_init_basic(self):
        """Test creating an empty configuration with init command."""
        with self._patch_service_calls():
            result = self.runner.invoke(app, ["init", "empty_config"])

            assert result.exit_code == 0
            assert "✓ Created empty configuration: empty_config" in result.stdout
            assert "✓ Switched to configuration: empty_config" in result.stdout

            # Verify config file was created
            empty_config_path = self.config_dir / "empty_config.toml"
            assert empty_config_path.exists()

            # Verify it's empty (no projects)
            with open(empty_config_path) as f:
                data = toml.load(f)

            assert len(data["projects"]) == 0
            assert "universe" in data
            assert self.mock_config_manager.active_config == "empty_config"

    def test_config_init_with_no_switch(self):
        """Test creating empty configuration without switching to it."""
        with self._patch_service_calls():
            original_active = self.mock_config_manager.active_config
            result = self.runner.invoke(app, ["init", "empty_config", "--no-switch"])

            assert result.exit_code == 0
            assert "✓ Created empty configuration: empty_config" in result.stdout
            assert "✓ Switched to configuration" not in result.stdout
            assert self.mock_config_manager.active_config == original_active

    def test_config_init_existing_name(self):
        """Test creating configuration with existing name."""
        with self._patch_service_calls():
            result = self.runner.invoke(app, ["init", "default"])

            assert result.exit_code == 1
            assert "Configuration 'default' already exists" in result.stdout

    def test_config_avail_basic(self):
        """Test showing available projects with avail command."""
        with self._patch_service_calls():
            result = self.runner.invoke(app, ["avail"])

            assert result.exit_code == 0
            assert "Available Projects (Configuration: default)" in result.stdout
            assert "✓ Active" in result.stdout  # cmip6 and cmip6plus should be active
            assert "○ Available" in result.stdout  # input4mip, obs4ref should be available

            # Check specific projects
            assert "cmip6" in result.stdout
            assert "cmip6plus" in result.stdout
            assert "input4mip" in result.stdout
            assert "obs4ref" in result.stdout
            assert "cordex-cmip6" in result.stdout

            # Check summary
            import re

            assert re.search(r"2/\d+ projects active", result.stdout)

    def test_config_avail_specific_config(self):
        """Test showing available projects for specific configuration."""
        with self._patch_service_calls():
            result = self.runner.invoke(app, ["avail", "--config", "test"])

            assert result.exit_code == 0
            assert "Available Projects (Configuration: test)" in result.stdout
            import re

            assert re.search(r"2/\d+ projects active", result.stdout)

    def test_config_avail_empty_config(self):
        """Test showing available projects for empty configuration."""
        # Create empty config
        empty_config_data = {
            "universe": {
                "github_repo": "https://github.com/WCRP-CMIP/WCRP-universe",
                "branch": "esgvoc",
                "local_path": "repos/WCRP-universe",
                "db_path": "dbs/universe.sqlite",
            },
            "projects": [],
        }

        empty_config_path = self.config_dir / "empty.toml"
        with open(empty_config_path, "w") as f:
            toml.dump(empty_config_data, f)

        with self._patch_service_calls():
            result = self.runner.invoke(app, ["avail", "--config", "empty"])

            assert result.exit_code == 0
            assert "Available Projects (Configuration: empty)" in result.stdout
            assert "○ Available" in result.stdout
            assert "✓ Active" not in result.stdout  # No projects should be active
            import re

            assert re.search(r"0/\d+ projects active", result.stdout)

    def test_config_avail_nonexistent_config(self):
        """Test showing available projects for nonexistent configuration."""
        with self._patch_service_calls():
            result = self.runner.invoke(app, ["avail", "--config", "nonexistent"])

            assert result.exit_code == 1
            assert "Configuration 'nonexistent' not found" in result.stdout

    def test_config_add_specific_config(self):
        """Test adding project to specific configuration."""
        with self._patch_service_calls():
            result = self.runner.invoke(app, ["add", "input4mip", "--config", "test"])

            assert result.exit_code == 0
            assert "✓ Added project input4mip" in result.stdout

            # Verify project was added to test config
            with open(self.test_config_path) as f:
                data = toml.load(f)

            project_names = [p["project_name"] for p in data["projects"]]
            assert "input4mip" in project_names

    def test_config_rm_specific_config(self):
        """Test removing project from specific configuration."""
        with self._patch_service_calls():
            result = self.runner.invoke(app, ["rm", "cmip6", "--config", "test", "--force"])

            assert result.exit_code == 0
            assert "✓ Removed cmip6 from configuration" in result.stdout

            # Verify project was removed from test config
            with open(self.test_config_path) as f:
                data = toml.load(f)

            project_names = [p["project_name"] for p in data["projects"]]
            assert "cmip6" not in project_names

    # Integration Tests
    @pytest.mark.integration
    def test_integration_workflow(self):
        """Test a complete workflow: create, add projects, modify, remove."""
        with self._patch_service_calls():
            # 1. Create new config
            result = self.runner.invoke(app, ["create", "workflow_test", "--switch"])
            assert result.exit_code == 0

            # 2. Add optional projects
            result = self.runner.invoke(app, ["add-project", "input4mip"])
            assert result.exit_code == 0

            result = self.runner.invoke(app, ["add-project", "obs4ref"])
            assert result.exit_code == 0

            # 3. Add custom project
            result = self.runner.invoke(
                app, ["add-project", "custom", "--custom", "--repo", "https://github.com/test/custom"]
            )
            assert result.exit_code == 0

            # 4. Verify all projects are there
            result = self.runner.invoke(app, ["list-projects"])
            assert "cmip6" in result.stdout
            assert "cmip6plus" in result.stdout
            assert "input4mip" in result.stdout
            assert "obs4ref" in result.stdout
            assert "custom" in result.stdout

            # 5. Update a project
            result = self.runner.invoke(app, ["update-project", "custom", "--branch", "develop"])
            assert result.exit_code == 0

            # 6. Remove a project
            result = self.runner.invoke(app, ["remove-project", "obs4ref", "--force"])
            assert result.exit_code == 0

            # 7. Verify final state
            result = self.runner.invoke(app, ["list-projects"])
            assert "obs4ref" not in result.stdout
            assert "custom" in result.stdout

            # 8. Check config file directly
            workflow_config_path = self.config_dir / "workflow_test.toml"
            with open(workflow_config_path) as f:
                data = toml.load(f)

            project_names = [p["project_name"] for p in data["projects"]]
            assert "obs4ref" not in project_names
            assert "custom" in project_names

            custom_project = next((p for p in data["projects"] if p["project_name"] == "custom"), None)
            assert custom_project["branch"] == "develop"

    @pytest.mark.integration
    def test_integration_simple_config_workflow(self):
        """Test complete workflow using the new simple config commands."""
        with self._patch_service_calls():
            # 1. Create empty config and switch to it
            result = self.runner.invoke(app, ["init", "simple_workflow"])
            assert result.exit_code == 0
            assert "✓ Created empty configuration: simple_workflow" in result.stdout
            assert "✓ Switched to configuration: simple_workflow" in result.stdout

            # 2. Check that it's empty
            result = self.runner.invoke(app, ["avail"])
            import re

            assert re.search(r"0/\d+ projects active", result.stdout)

            # 3. Add multiple projects at once
            result = self.runner.invoke(app, ["add", "cmip6", "input4mip", "obs4ref"])
            assert result.exit_code == 0
            assert "Successfully added 3 project(s): cmip6, input4mip, obs4ref" in result.stdout

            # 4. Check projects were added
            result = self.runner.invoke(app, ["avail"])
            assert re.search(r"3/\d+ projects active", result.stdout)

            # 5. Try to add existing and new projects
            result = self.runner.invoke(app, ["add", "cmip6", "cmip6plus", "cordex-cmip6"])
            assert result.exit_code == 0
            assert "⚠ Project 'cmip6' already exists - skipping" in result.stdout
            assert "Successfully added 2 project(s): cmip6plus, cordex-cmip6" in result.stdout

            # 6. Verify all are now active
            result = self.runner.invoke(app, ["avail"])
            assert re.search(r"5/\d+ projects active", result.stdout)

            # 7. Remove some projects
            result = self.runner.invoke(app, ["rm", "obs4ref", "cordex-cmip6", "--force"])
            assert result.exit_code == 0
            assert "Successfully removed 2 project(s): obs4ref, cordex-cmip6" in result.stdout

            # 8. Check final state
            result = self.runner.invoke(app, ["avail"])
            assert re.search(r"3/\d+ projects active", result.stdout)

            # 9. Verify configuration file directly
            simple_workflow_path = self.config_dir / "simple_workflow.toml"
            with open(simple_workflow_path) as f:
                data = toml.load(f)

            project_names = [p["project_name"] for p in data["projects"]]
            assert "cmip6" in project_names
            assert "cmip6plus" in project_names
            assert "input4mip" in project_names
            assert "obs4ref" not in project_names
            assert "cordex-cmip6" not in project_names
            assert len(project_names) == 3


class TestEdgeCases:
    """Additional tests for edge cases and error conditions."""

    @pytest.fixture
    def isolated_cli_test(self):
        """Fixture for tests that need complete isolation."""
        temp_dir = tempfile.mkdtemp()
        config_dir = Path(temp_dir) / "configs"
        config_dir.mkdir(parents=True)

        # Create minimal config
        config_data = {
            "universe": {
                "github_repo": "https://github.com/WCRP-CMIP/WCRP-universe",
                "branch": "esgvoc",
                "local_path": "repos/WCRP-universe",
                "db_path": "dbs/universe.sqlite",
            },
            "projects": [],
        }

        config_path = config_dir / "isolated.toml"
        with open(config_path, "w") as f:
            toml.dump(config_data, f)

        mock_manager = MockConfigManager(config_dir, "isolated")

        yield {
            "temp_dir": temp_dir,
            "config_dir": config_dir,
            "config_path": config_path,
            "mock_manager": mock_manager,
            "runner": CliRunner(),
        }

        shutil.rmtree(temp_dir)

    def test_malformed_config_file(self, isolated_cli_test):
        """Test behavior with malformed TOML files."""
        test_data = isolated_cli_test
        config_path = test_data["config_path"]
        runner = test_data["runner"]
        mock_manager = test_data["mock_manager"]

        # Create malformed TOML
        with open(config_path, "w") as f:
            f.write("invalid toml content [[[")

        mock_service = MagicMock()
        mock_service.get_config_manager.return_value = mock_manager
        mock_service.current_state = None
        mock_service.get_state.return_value = None

        with patch("esgvoc.cli.config.get_service", return_value=mock_service):
            result = runner.invoke(app, ["show", "isolated"])
            # Should handle the error gracefully
            assert result.exit_code == 0

    @pytest.mark.slow
    def test_large_number_of_projects(self, isolated_cli_test):
        """Test CLI performance with many projects."""
        test_data = isolated_cli_test
        config_path = test_data["config_path"]
        runner = test_data["runner"]
        mock_manager = test_data["mock_manager"]

        # Create config with many projects
        large_config = {
            "universe": {
                "github_repo": "https://github.com/WCRP-CMIP/WCRP-universe",
                "branch": "esgvoc",
                "local_path": "repos/WCRP-universe",
                "db_path": "dbs/universe.sqlite",
            },
            "projects": [
                {
                    "project_name": f"project_{i}",
                    "github_repo": f"https://github.com/test/project_{i}",
                    "branch": "main",
                    "local_path": f"repos/project_{i}",
                    "db_path": f"dbs/project_{i}.sqlite",
                }
                for i in range(50)  # 50 projects
            ],
        }

        with open(config_path, "w") as f:
            toml.dump(large_config, f)

        mock_service = MagicMock()
        mock_service.get_config_manager.return_value = mock_manager
        mock_service.current_state = None
        mock_service.get_state.return_value = None

        with patch("esgvoc.cli.config.get_service", return_value=mock_service):
            # Test that listing projects works with many entries
            result = runner.invoke(app, ["list-projects", "--config", "isolated"])
            assert result.exit_code == 0
            assert "project_0" in result.stdout
            assert "project_49" in result.stdout

    def test_new_commands_error_handling(self, isolated_cli_test):
        """Test error handling in new simple config commands."""
        test_data = isolated_cli_test
        runner = test_data["runner"]
        mock_manager = test_data["mock_manager"]

        mock_service = MagicMock()
        mock_service.get_config_manager.return_value = mock_manager
        mock_service.current_state = None
        mock_service.get_state.return_value = None

        with patch("esgvoc.cli.config.get_service", return_value=mock_service):
            # Test add with nonexistent config
            result = runner.invoke(app, ["add", "cmip6", "--config", "nonexistent"])
            assert result.exit_code == 1
            assert "Configuration 'nonexistent' not found" in result.stdout

            # Test rm with nonexistent config
            result = runner.invoke(app, ["rm", "cmip6", "--config", "nonexistent"])
            assert result.exit_code == 1
            assert "Configuration 'nonexistent' not found" in result.stdout

            # Test avail with nonexistent config
            result = runner.invoke(app, ["avail", "--config", "nonexistent"])
            assert result.exit_code == 1
            assert "Configuration 'nonexistent' not found" in result.stdout

    def test_filesystem_cleanup_edge_cases(self, isolated_cli_test):
        """Test filesystem cleanup edge cases in rm command."""
        test_data = isolated_cli_test
        config_path = test_data["config_path"]
        runner = test_data["runner"]
        mock_manager = test_data["mock_manager"]

        # Create config with project
        config_data = {
            "universe": {
                "github_repo": "https://github.com/WCRP-CMIP/WCRP-universe",
                "branch": "esgvoc",
                "local_path": "repos/WCRP-universe",
                "db_path": "dbs/universe.sqlite",
            },
            "projects": [
                {
                    "project_name": "test_project",
                    "github_repo": "https://github.com/test/project",
                    "branch": "main",
                    "local_path": "repos/test_project",
                    "db_path": "dbs/test_project.sqlite",
                }
            ],
        }

        with open(config_path, "w") as f:
            toml.dump(config_data, f)

        mock_service = MagicMock()
        mock_service.get_config_manager.return_value = mock_manager
        mock_service.current_state = None
        mock_service.get_state.return_value = None

        with patch("esgvoc.cli.config.get_service", return_value=mock_service):
            # Mock the config manager data_config_dir to avoid actual file operations
            mock_manager.data_config_dir = str(test_data["temp_dir"])

            # Test rm with files that don't exist (should handle gracefully)
            result = runner.invoke(app, ["rm", "test_project", "--force"])
            assert result.exit_code == 0
            assert "✓ Removed test_project from configuration" in result.stdout
            # Should show warnings for missing files
            assert "Repository not found:" in result.stdout or "Database not found:" in result.stdout

    def test_batch_operations_edge_cases(self, isolated_cli_test):
        """Test edge cases in batch add/rm operations."""
        test_data = isolated_cli_test
        config_path = test_data["config_path"]
        runner = test_data["runner"]
        mock_manager = test_data["mock_manager"]

        # Create config with some projects
        config_data = {
            "universe": {
                "github_repo": "https://github.com/WCRP-CMIP/WCRP-universe",
                "branch": "esgvoc",
                "local_path": "repos/WCRP-universe",
                "db_path": "dbs/universe.sqlite",
            },
            "projects": [
                {
                    "project_name": "cmip6",
                    "github_repo": "https://github.com/WCRP-CMIP/CMIP6_CVs",
                    "branch": "esgvoc",
                    "local_path": "repos/CMIP6_CVs",
                    "db_path": "dbs/cmip6.sqlite",
                }
            ],
        }

        with open(config_path, "w") as f:
            toml.dump(config_data, f)

        mock_service = MagicMock()
        mock_service.get_config_manager.return_value = mock_manager
        mock_service.current_state = None
        mock_service.get_state.return_value = None

        with patch("esgvoc.cli.config.get_service", return_value=mock_service):
            # Test adding empty list (edge case)
            result = runner.invoke(app, ["add"])
            assert result.exit_code == 2  # Typer error for missing argument

            # Test removing empty list (edge case)
            result = runner.invoke(app, ["rm"])
            assert result.exit_code == 2  # Typer error for missing argument

            # Test mixed case with all existing projects
            result = runner.invoke(app, ["add", "cmip6"])
            assert result.exit_code == 0
            assert "Skipped 1 existing project(s): cmip6" in result.stdout
            assert "Successfully added" not in result.stdout  # Nothing was actually added


# Helper functions for test setup and assertions


def create_test_config(config_dir: Path, name: str, projects: list = None) -> Path:
    """Helper to create test configuration files."""
    if projects is None:
        projects = [
            {
                "project_name": "cmip6",
                "github_repo": "https://github.com/WCRP-CMIP/CMIP6_CVs",
                "branch": "esgvoc",
                "local_path": "repos/CMIP6_CVs",
                "db_path": "dbs/cmip6.sqlite",
            }
        ]

    config_data = {
        "universe": {
            "github_repo": "https://github.com/WCRP-CMIP/WCRP-universe",
            "branch": "esgvoc",
            "local_path": "repos/WCRP-universe",
            "db_path": "dbs/universe.sqlite",
        },
        "projects": projects,
    }

    config_path = config_dir / f"{name}.toml"
    with open(config_path, "w") as f:
        toml.dump(config_data, f)

    return config_path


def assert_project_in_config(config_path: Path, project_name: str, should_exist: bool = True):
    """Helper to assert project existence in config file."""
    with open(config_path) as f:
        data = toml.load(f)

    project_names = [p["project_name"] for p in data["projects"]]

    if should_exist:
        assert project_name in project_names, f"Project '{project_name}' should exist in config"
    else:
        assert project_name not in project_names, f"Project '{project_name}' should not exist in config"


def assert_project_settings(config_path: Path, project_name: str, expected_settings: dict):
    """Helper to assert specific project settings."""
    with open(config_path) as f:
        data = toml.load(f)

    project = next((p for p in data["projects"] if p["project_name"] == project_name), None)
    assert project is not None, f"Project '{project_name}' not found"

    for key, expected_value in expected_settings.items():
        actual_value = project.get(key)
        assert actual_value == expected_value, f"Expected {key}='{expected_value}', got '{actual_value}'"


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")


if __name__ == "__main__":
    # This file is meant to be run with pytest, not directly with Python
    print("Please run tests using:")
    print("  uv run pytest tests/test_cli_config.py -v")
    print("")
    print("Common test commands:")
    print("  # Run all tests")
    print("  uv run pytest tests/test_cli_config.py -v")
    print("")
    print("  # Run specific test")
    print("  uv run pytest tests/test_cli_config.py::TestConfigCLI::test_add_project_from_default -v")
    print("")
    print("  # Run edge case tests only")
    print("  uv run pytest tests/test_cli_config.py::TestEdgeCases -v")
    print("")
    print("  # Run with coverage")
    print("  uv run pytest tests/test_cli_config.py --cov=esgvoc.cli.config --cov-report=html")
    print("")
    print("  # Run integration tests only")
    print("  uv run pytest tests/test_cli_config.py -m integration -v")
    print("")
    print("  # Run excluding slow tests")
    print("  uv run pytest tests/test_cli_config.py -m 'not slow' -v")
    exit(1)

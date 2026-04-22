"""
Tests for offline mode configuration functionality.

This module tests that offline_mode settings are correctly handled
in configuration files, default settings, and ServiceSettings operations.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import toml

from esgvoc.core.service.configuration.setting import ServiceSettings, ProjectSettings, UniverseSettings


class TestOfflineModeConfiguration:
    """Test offline mode configuration functionality."""

    def test_project_settings_offline_mode_default(self):
        """Test that ProjectSettings has offline_mode=False by default."""
        project = ProjectSettings(
            project_name="test",
            github_repo="https://github.com/test/repo"
        )
        assert project.offline_mode is False

    def test_project_settings_offline_mode_explicit(self):
        """Test that ProjectSettings can set offline_mode explicitly."""
        project = ProjectSettings(
            project_name="test",
            github_repo="https://github.com/test/repo",
            offline_mode=True
        )
        assert project.offline_mode is True

    def test_universe_settings_offline_mode_default(self):
        """Test that UniverseSettings has offline_mode=False by default."""
        universe = UniverseSettings(
            github_repo="https://github.com/test/universe"
        )
        assert universe.offline_mode is False

    def test_universe_settings_offline_mode_explicit(self):
        """Test that UniverseSettings can set offline_mode explicitly."""
        universe = UniverseSettings(
            github_repo="https://github.com/test/universe",
            offline_mode=True
        )
        assert universe.offline_mode is True

    def test_service_settings_default_includes_offline_mode(self):
        """Test that default settings include offline_mode=False."""
        defaults = ServiceSettings._get_default_settings()

        # Check universe offline_mode
        assert "offline_mode" in defaults["universe"]
        assert defaults["universe"]["offline_mode"] is False

        # Check projects offline_mode
        for project in defaults["projects"]:
            assert "offline_mode" in project
            assert project["offline_mode"] is False

    def test_service_settings_default_project_configs_include_offline_mode(self):
        """Test that default project configs include offline_mode=False."""
        defaults = ServiceSettings._get_default_project_configs()

        for project_name, config in defaults.items():
            assert "offline_mode" in config, f"Project {project_name} missing offline_mode"
            assert config["offline_mode"] is False

    def test_service_settings_load_with_offline_mode(self):
        """Test loading ServiceSettings from config with offline_mode."""
        config_data = {
            "universe": {
                "github_repo": "https://github.com/WCRP-CMIP/WCRP-universe",
                "branch": "esgvoc",
                "local_path": "repos/WCRP-universe",
                "db_path": "dbs/universe.sqlite",
                "offline_mode": True,
            },
            "projects": [
                {
                    "project_name": "cmip6",
                    "github_repo": "https://github.com/WCRP-CMIP/CMIP6_CVs",
                    "branch": "esgvoc",
                    "local_path": "repos/CMIP6_CVs",
                    "db_path": "dbs/cmip6.sqlite",
                    "offline_mode": False,
                },
                {
                    "project_name": "cmip6plus",
                    "github_repo": "https://github.com/WCRP-CMIP/CMIP6Plus_CVs",
                    "branch": "esgvoc",
                    "local_path": "repos/CMIP6Plus_CVs",
                    "db_path": "dbs/cmip6plus.sqlite",
                    "offline_mode": True,
                },
            ],
        }

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            toml.dump(config_data, f)
            temp_path = f.name

        try:
            settings = ServiceSettings.load_from_file(temp_path)

            # Check universe offline mode
            assert settings.universe.offline_mode is True

            # Check project offline modes
            assert settings.projects["cmip6"].offline_mode is False
            assert settings.projects["cmip6plus"].offline_mode is True

        finally:
            Path(temp_path).unlink()

    def test_service_settings_update_project_offline_mode_boolean(self):
        """Test updating project offline_mode with boolean value."""
        settings = ServiceSettings.load_default()

        # cmip6 should already be loaded by default
        assert "cmip6" in settings.projects

        # Update offline_mode with boolean
        result = settings.update_project("cmip6", offline_mode=True)
        assert result is True
        assert settings.projects["cmip6"].offline_mode is True

    def test_service_settings_update_project_offline_mode_string_true(self):
        """Test updating project offline_mode with string 'true' values."""
        settings = ServiceSettings.load_default()

        # cmip6 should already be loaded by default
        assert "cmip6" in settings.projects

        # Test various true string values
        for true_value in ["true", "1", "yes", "on", "TRUE", "True"]:
            result = settings.update_project("cmip6", offline_mode=true_value)
            assert result is True
            assert settings.projects["cmip6"].offline_mode is True, f"Failed for value: {true_value}"

    def test_service_settings_update_project_offline_mode_string_false(self):
        """Test updating project offline_mode with string 'false' values."""
        settings = ServiceSettings.load_default()

        # cmip6 should already be loaded by default
        assert "cmip6" in settings.projects

        # Test various false string values
        for false_value in ["false", "0", "no", "off", "FALSE", "False", "anything_else"]:
            result = settings.update_project("cmip6", offline_mode=false_value)
            assert result is True
            assert settings.projects["cmip6"].offline_mode is False, f"Failed for value: {false_value}"

    def test_service_settings_save_and_load_offline_mode(self):
        """Test saving and loading settings preserves offline_mode."""
        # Create settings with offline mode enabled
        settings = ServiceSettings.load_default()
        settings.universe.offline_mode = True
        settings.projects["cmip6"].offline_mode = True

        # Save to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            temp_path = f.name

        try:
            settings.save_to_file(temp_path)

            # Load from file
            loaded_settings = ServiceSettings.load_from_file(temp_path)

            # Check that offline mode is preserved
            assert loaded_settings.universe.offline_mode is True
            assert loaded_settings.projects["cmip6"].offline_mode is True

            # Verify the file content directly
            with open(temp_path, 'r') as f:
                content = toml.load(f)

            assert content["universe"]["offline_mode"] is True
            cmip6_project = next(p for p in content["projects"] if p["project_name"] == "cmip6")
            assert cmip6_project["offline_mode"] is True

        finally:
            Path(temp_path).unlink()

    def test_project_settings_model_dump_includes_offline_mode(self):
        """Test that model_dump includes offline_mode field."""
        project = ProjectSettings(
            project_name="test",
            github_repo="https://github.com/test/repo",
            offline_mode=True
        )

        dumped = project.model_dump()
        assert "offline_mode" in dumped
        assert dumped["offline_mode"] is True

    def test_universe_settings_model_dump_includes_offline_mode(self):
        """Test that model_dump includes offline_mode field."""
        universe = UniverseSettings(
            github_repo="https://github.com/test/universe",
            offline_mode=True
        )

        dumped = universe.model_dump()
        assert "offline_mode" in dumped
        assert dumped["offline_mode"] is True

    def test_service_settings_create_from_dict_with_offline_mode(self):
        """Test creating ServiceSettings from dict with offline_mode."""
        config_dict = {
            "universe": {
                "github_repo": "https://github.com/test/universe",
                "offline_mode": True,
            },
            "projects": [
                {
                    "project_name": "test",
                    "github_repo": "https://github.com/test/repo",
                    "offline_mode": False,
                }
            ],
        }

        settings = ServiceSettings.load_from_dict(config_dict)

        assert settings.universe.offline_mode is True
        assert settings.projects["test"].offline_mode is False

    def test_service_settings_backward_compatibility_without_offline_mode(self):
        """Test that ServiceSettings works with configs missing offline_mode."""
        config_dict = {
            "universe": {
                "github_repo": "https://github.com/test/universe",
                "branch": "main",
                "local_path": "repos/universe",
                "db_path": "dbs/universe.sqlite",
                # No offline_mode field
            },
            "projects": [
                {
                    "project_name": "test",
                    "github_repo": "https://github.com/test/repo",
                    "branch": "main",
                    "local_path": "repos/test",
                    "db_path": "dbs/test.sqlite",
                    # No offline_mode field
                }
            ],
        }

        # Should not raise an error and default to False
        settings = ServiceSettings.load_from_dict(config_dict)

        assert settings.universe.offline_mode is False
        assert settings.projects["test"].offline_mode is False


class TestOfflineModeProjectOperations:
    """Test offline mode behavior in project operations."""

    def test_add_project_preserves_offline_mode_default(self):
        """Test that adding a project uses default offline_mode=False."""
        settings = ServiceSettings.load_default()

        # Add project using default config
        result = settings.add_project_from_default("input4mip")

        assert result is True
        assert settings.projects["input4mip"].offline_mode is False

    def test_add_project_custom_offline_mode(self):
        """Test adding a project with custom offline_mode."""
        settings = ServiceSettings.load_default()

        custom_config = settings.DEFAULT_PROJECT_CONFIGS["input4mip"].copy()
        custom_config["offline_mode"] = True

        result = settings.add_project_custom(custom_config)

        assert result is True
        assert settings.projects["input4mip"].offline_mode is True

    def test_remove_project_with_offline_mode(self):
        """Test that removing a project works regardless of offline_mode."""
        settings = ServiceSettings.load_default()

        # Add project with offline mode enabled
        custom_config = settings.DEFAULT_PROJECT_CONFIGS["input4mip"].copy()
        custom_config["offline_mode"] = True
        settings.add_project_custom(custom_config)

        # Verify it was added with offline mode
        assert settings.projects["input4mip"].offline_mode is True

        # Remove the project
        result = settings.remove_project("input4mip")

        assert result is True
        assert "input4mip" not in settings.projects

    def test_update_project_multiple_fields_including_offline_mode(self):
        """Test updating multiple project fields including offline_mode."""
        settings = ServiceSettings.load_default()
        # cmip6 should already be loaded by default
        assert "cmip6" in settings.projects

        # Update multiple fields including offline_mode
        result = settings.update_project(
            "cmip6",
            branch="dev",
            offline_mode=True,
            local_path="repos/cmip6_dev"
        )

        assert result is True
        assert settings.projects["cmip6"].branch == "dev"
        assert settings.projects["cmip6"].offline_mode is True
        assert settings.projects["cmip6"].local_path == "repos/cmip6_dev"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
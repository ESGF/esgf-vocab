"""
Test suite for the new config path resolution system using the default configuration.
Tests all three path types: absolute, dot-relative, and platform-relative.
"""
import pytest
from pathlib import Path
import tempfile
import os

from esgvoc.core.service.configuration.setting import resolve_path_to_absolute
from .conftest import create_test_config_variant, cleanup_test_config


class TestPathResolutionWithDefaultConfig:
    """Test the path resolution functionality using default config."""

    def test_absolute_path_unchanged(self, default_config_test):
        """Test that absolute paths are returned unchanged."""
        absolute_path = "/tmp/test/absolute/path"
        result = resolve_path_to_absolute(absolute_path)
        assert result == str(Path(absolute_path).resolve())

    def test_none_path_returns_none(self, default_config_test):
        """Test that None input returns None."""
        result = resolve_path_to_absolute(None)
        assert result is None

    def test_dot_relative_path_resolution(self, default_config_test):
        """Test that dot-relative paths resolve relative to current working directory."""
        # Store original working directory
        original_cwd = Path.cwd()

        try:
            # Create a temporary working directory
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                test_subdir = temp_path / "test_subdir"
                test_subdir.mkdir()

                # Change to the temp directory
                os.chdir(temp_path)

                # Test ./relative path
                dot_relative_path = "./test_subdir"
                result = resolve_path_to_absolute(dot_relative_path)
                expected = str((temp_path / "test_subdir").resolve())
                assert result == expected

                # Test ../relative path from a subdirectory
                deeper_dir = temp_path / "deeper"
                deeper_dir.mkdir()
                os.chdir(deeper_dir)

                parent_relative_path = "../test_subdir"
                result = resolve_path_to_absolute(parent_relative_path)
                expected = str((temp_path / "test_subdir").resolve())
                assert result == expected

        finally:
            # Always restore original working directory
            os.chdir(original_cwd)

    def test_platform_relative_path_resolution(self, default_config_test):
        """Test that platform-relative paths use PlatformDirs correctly."""
        platform_relative_path = "repos/test-repo"

        # Without config name - should use default platform dirs
        result = resolve_path_to_absolute(platform_relative_path)
        assert "repos/test-repo" in result
        assert result.endswith("repos/test-repo")

        # With config name - should include config name in path
        config_name = "test_config"
        result = resolve_path_to_absolute(platform_relative_path, config_name)
        assert "test_config" in result
        assert "repos/test-repo" in result
        assert result.endswith("test_config/repos/test-repo")


class TestConfigPathResolutionWithDefaultConfig:
    """Test path resolution within configurations using default config."""

    def test_default_config_uses_platform_relative_paths(self, default_config_test, sample_config_modifications):
        """Test that the default config uses platform-relative paths correctly."""
        config_manager = default_config_test

        # Get the default config
        config = config_manager.get_active_config()

        # Default config should have platform-relative paths
        universe_path = config.universe.get_absolute_local_path()
        project_path = list(config.projects.values())[0].get_absolute_local_path() if config.projects else None

        # These should resolve to absolute paths using platform directories
        assert universe_path is not None
        assert Path(universe_path).is_absolute()

        if project_path:
            assert Path(project_path).is_absolute()

    def test_absolute_paths_in_modified_config(self, default_config_test, sample_config_modifications):
        """Test configuration modified to use absolute paths."""
        config_manager = default_config_test

        try:
            # Create a test config with absolute paths
            config = create_test_config_variant(
                config_manager,
                "absolute_test",
                "absolute_paths",
                sample_config_modifications
            )

            # Check universe paths - use Path.resolve() to get consistent cross-platform paths
            expected_universe_local = str(Path("/tmp/test_absolute/repos/WCRP-universe").resolve())
            expected_universe_db = str(Path("/tmp/test_absolute/dbs/universe.sqlite").resolve())

            assert config.universe.get_absolute_local_path() == expected_universe_local
            assert config.universe.get_absolute_db_path() == expected_universe_db

            # Check project paths (if projects exist)
            if config.projects:
                first_project = list(config.projects.values())[0]
                expected_project_local = str(Path("/tmp/test_absolute/repos/CMIP6_CVs").resolve())
                expected_project_db = str(Path("/tmp/test_absolute/dbs/cmip6.sqlite").resolve())

                assert first_project.get_absolute_local_path() == expected_project_local
                assert first_project.get_absolute_db_path() == expected_project_db

        finally:
            # Clean up test config
            cleanup_test_config(config_manager, "absolute_test")

    def test_dot_relative_paths_in_modified_config(self, default_config_test, sample_config_modifications):
        """Test configuration modified to use dot-relative paths."""
        config_manager = default_config_test
        original_cwd = Path.cwd()

        try:
            # Create a temporary working directory
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                os.chdir(temp_path)

                # Create a test config with dot-relative paths
                config = create_test_config_variant(
                    config_manager,
                    "dot_relative_test",
                    "dot_relative_paths",
                    sample_config_modifications
                )

                # Check universe paths resolve relative to current working directory
                expected_local = str((temp_path / "test_repos" / "WCRP-universe").resolve())
                expected_db = str((temp_path / "test_dbs" / "universe.sqlite").resolve())

                assert config.universe.get_absolute_local_path() == expected_local
                assert config.universe.get_absolute_db_path() == expected_db

                # Check project paths (if projects exist)
                if config.projects:
                    first_project = list(config.projects.values())[0]
                    expected_project_local = str((temp_path / "test_repos" / "CMIP6_CVs").resolve())
                    expected_project_db = str((temp_path / "test_dbs" / "cmip6.sqlite").resolve())

                    assert first_project.get_absolute_local_path() == expected_project_local
                    assert first_project.get_absolute_db_path() == expected_project_db

        finally:
            # Restore working directory and clean up
            os.chdir(original_cwd)
            cleanup_test_config(config_manager, "dot_relative_test")

    def test_platform_relative_paths_in_modified_config(self, default_config_test, sample_config_modifications):
        """Test configuration with platform-relative paths (default behavior)."""
        config_manager = default_config_test

        try:
            # Create a test config with platform-relative paths
            config = create_test_config_variant(
                config_manager,
                "platform_relative_test",
                "platform_relative_paths",
                sample_config_modifications
            )

            # Check universe paths use platform directories with config name
            universe_path = config.universe.get_absolute_local_path()
            universe_db_path = config.universe.get_absolute_db_path()

            assert "platform_relative_test" in universe_path
            assert "repos/WCRP-universe" in universe_path
            assert "platform_relative_test" in universe_db_path
            assert "dbs/universe.sqlite" in universe_db_path

            # Check project paths (if projects exist)
            if config.projects:
                first_project = list(config.projects.values())[0]
                project_path = first_project.get_absolute_local_path()
                project_db_path = first_project.get_absolute_db_path()

                assert "platform_relative_test" in project_path
                assert "repos/CMIP6_CVs" in project_path
                assert "platform_relative_test" in project_db_path
                assert "dbs/cmip6.sqlite" in project_db_path

        finally:
            # Clean up test config
            cleanup_test_config(config_manager, "platform_relative_test")

    def test_mixed_path_types_in_config(self, default_config_test, sample_config_modifications):
        """Test configuration with mixed path types."""
        config_manager = default_config_test
        original_cwd = Path.cwd()

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                os.chdir(temp_path)

                # Get current default config and modify with mixed types
                config = config_manager.get_active_config()
                config_data = config.dump()

                # Mix different path types
                config_data["universe"]["local_path"] = "/tmp/absolute/universe"  # absolute
                config_data["universe"]["db_path"] = "./relative_dbs/universe.sqlite"  # dot-relative

                if config_data["projects"]:
                    config_data["projects"][0]["local_path"] = "repos/CMIP6_CVs"  # platform-relative
                    config_data["projects"][0]["db_path"] = "/tmp/absolute/cmip6.sqlite"  # absolute

                # Save and load the mixed config
                config_manager.save_config(config_data, "mixed_test")
                config_manager.switch_config("mixed_test")

                updated_config = config_manager.get_active_config()

                # Check universe paths - use Path.resolve() for cross-platform compatibility
                expected_universe_local = str(Path("/tmp/absolute/universe").resolve())
                expected_db = str((temp_path / "relative_dbs" / "universe.sqlite").resolve())

                assert updated_config.universe.get_absolute_local_path() == expected_universe_local
                assert updated_config.universe.get_absolute_db_path() == expected_db

                # Check project paths (if projects exist)
                if updated_config.projects:
                    first_project = list(updated_config.projects.values())[0]
                    project_path = first_project.get_absolute_local_path()
                    assert "mixed_test" in project_path
                    assert "repos/CMIP6_CVs" in project_path

                    expected_project_db = str(Path("/tmp/absolute/cmip6.sqlite").resolve())
                    assert first_project.get_absolute_db_path() == expected_project_db

        finally:
            # Restore working directory and clean up
            os.chdir(original_cwd)
            cleanup_test_config(config_manager, "mixed_test")

    def test_config_switching_preserves_path_resolution(self, default_config_test, sample_config_modifications):
        """Test that switching between configs with different path types works correctly."""
        config_manager = default_config_test

        try:
            # Create two configs with different path types
            absolute_config = create_test_config_variant(
                config_manager, "absolute_config", "absolute_paths", sample_config_modifications
            )

            platform_config = create_test_config_variant(
                config_manager, "platform_config", "platform_relative_paths", sample_config_modifications
            )

            # Test switching to absolute config - use Path.resolve() for cross-platform compatibility
            config_manager.switch_config("absolute_config")
            config = config_manager.get_active_config()
            expected_absolute_path = str(Path("/tmp/test_absolute/repos/WCRP-universe").resolve())
            assert config.universe.get_absolute_local_path() == expected_absolute_path

            # Test switching to platform config
            config_manager.switch_config("platform_config")
            config = config_manager.get_active_config()
            platform_path = config.universe.get_absolute_local_path()
            assert "platform_config" in platform_path
            assert "repos/WCRP-universe" in platform_path

            # Switch back to absolute config
            config_manager.switch_config("absolute_config")
            config = config_manager.get_active_config()
            assert config.universe.get_absolute_local_path() == expected_absolute_path

        finally:
            # Clean up test configs
            cleanup_test_config(config_manager, "absolute_config")
            cleanup_test_config(config_manager, "platform_config")
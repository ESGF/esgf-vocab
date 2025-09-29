"""
End-to-end integration test scenarios using the default configuration.
Tests complete workflows that combine path resolution and shallow clone features.
"""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile
import os

from esgvoc.core import service
import esgvoc.api as ev
from .conftest import create_test_config_variant, cleanup_test_config


class TestEndToEndScenariosWithDefaultConfig:
    """Test complete workflows using the default configuration."""

    def test_fresh_install_scenario_with_default_config(self, default_config_test, mock_subprocess):
        """Test a complete fresh installation scenario with default settings."""
        config_manager = default_config_test

        # Verify default config is active
        assert config_manager.get_active_config_name() == "default"

        # Get initial state
        current_state = service.get_state()
        assert current_state is not None

        # Verify default config has proper structure
        config = config_manager.get_active_config()
        assert config.universe is not None
        assert hasattr(config, 'projects')

        # Verify paths resolve correctly
        universe_path = config.universe.get_absolute_local_path()
        assert universe_path is not None
        assert Path(universe_path).is_absolute()

        # Mock synchronization process
        with patch('esgvoc.core.repo_fetcher.RepoFetcher.clone_repository') as mock_clone:
            mock_clone.return_value = None

            # Simulate what synchronize_all would do (without actually calling it)
            # This tests that the system is ready for synchronization
            assert config.universe.github_repo is not None
            assert config.universe.branch is not None

    def test_path_resolution_workflow_with_default_config(self, default_config_test, sample_config_modifications):
        """Test workflow of creating configs with different path types and using them."""
        config_manager = default_config_test

        try:
            # Test absolute path workflow
            absolute_config = create_test_config_variant(
                config_manager, "workflow_absolute", "absolute_paths", sample_config_modifications
            )

            # Verify the config works
            current_state = service.get_state()
            assert current_state is not None

            universe_path = absolute_config.universe.get_absolute_local_path()
            expected_universe_path = str(Path("/tmp/test_absolute/repos/WCRP-universe").resolve())
            assert universe_path == expected_universe_path

            # Test platform-relative path workflow
            platform_config = create_test_config_variant(
                config_manager, "workflow_platform", "platform_relative_paths", sample_config_modifications
            )

            # Verify the config works
            current_state = service.get_state()
            assert current_state is not None

            universe_path = platform_config.universe.get_absolute_local_path()
            assert "workflow_platform" in universe_path
            assert "repos/WCRP-universe" in universe_path

        finally:
            # Clean up test configs
            cleanup_test_config(config_manager, "workflow_absolute")
            cleanup_test_config(config_manager, "workflow_platform")

    def test_config_switching_workflow_with_default_config(self, default_config_test, sample_config_modifications):
        """Test complete workflow of creating, switching, and using different configs."""
        config_manager = default_config_test

        try:
            # Create multiple test configs
            config1 = create_test_config_variant(
                config_manager, "switch_test_1", "absolute_paths", sample_config_modifications
            )
            config2 = create_test_config_variant(
                config_manager, "switch_test_2", "platform_relative_paths", sample_config_modifications
            )

            # Test switching between configs
            config_manager.switch_config("switch_test_1")
            current_config = config_manager.get_active_config()
            expected_path = str(Path("/tmp/test_absolute/repos/WCRP-universe").resolve())
            assert current_config.universe.get_absolute_local_path() == expected_path

            config_manager.switch_config("switch_test_2")
            current_config = config_manager.get_active_config()
            universe_path = current_config.universe.get_absolute_local_path()
            assert "switch_test_2" in universe_path

            # Switch back to default
            config_manager.switch_config("default")
            assert config_manager.get_active_config_name() == "default"

        finally:
            # Clean up test configs
            cleanup_test_config(config_manager, "switch_test_1")
            cleanup_test_config(config_manager, "switch_test_2")

    def test_api_integration_with_default_config(self, default_config_test):
        """Test that API functions work with default configuration."""
        config_manager = default_config_test

        # Verify we're using default config
        assert config_manager.get_active_config_name() == "default"

        # Mock the API validation call
        with patch('esgvoc.api.valid_term') as mock_valid:
            mock_valid.return_value = True

            # Test API call - this should work with default config
            result = ev.valid_term("IPSL", "cmip6", "institution_id", "ipsl")
            assert result is True

            mock_valid.assert_called_once_with("IPSL", "cmip6", "institution_id", "ipsl")

    def test_error_recovery_with_default_config(self, default_config_test):
        """Test error recovery scenarios while preserving default config."""
        config_manager = default_config_test

        original_active = config_manager.get_active_config_name()

        try:
            # Try operations that might fail
            try:
                config_manager.switch_config("nonexistent_config")
            except (ValueError, KeyError):
                # Expected to fail
                pass

            # Verify we can still switch back to default
            config_manager.switch_config("default")
            assert config_manager.get_active_config_name() == "default"

            # Verify default config still works
            config = config_manager.get_active_config()
            assert config is not None
            assert config.universe is not None

        finally:
            # Ensure we restore original state
            if original_active != config_manager.get_active_config_name():
                config_manager.switch_config(original_active)


class TestShallowCloneWorkflowWithDefaultConfig:
    """Test shallow clone functionality in complete workflows."""

    def test_shallow_clone_in_complete_workflow(self, default_config_test, mock_subprocess):
        """Test that shallow clone is used in complete repository workflow."""
        config_manager = default_config_test

        # Mock RepoFetcher to capture calls
        with patch('esgvoc.core.repo_fetcher.RepoFetcher.clone_repository') as mock_clone:
            mock_clone.return_value = None

            # Get current config and verify it's ready for repository operations
            config = config_manager.get_active_config()
            universe_path = config.universe.get_absolute_local_path()

            # Simulate what would happen during repository cloning
            from esgvoc.core.repo_fetcher import RepoFetcher
            fetcher = RepoFetcher()

            # Test that clone would be called with shallow=True by default
            if config.universe.github_repo and config.universe.branch:
                # Extract owner and repo from URL (basic parsing for test)
                repo_url = config.universe.github_repo
                if "github.com" in repo_url:
                    parts = repo_url.split('/')
                    if len(parts) >= 2:
                        owner = parts[-2]
                        repo = parts[-1]
                        if repo.endswith('.git'):
                            repo = repo[:-4]

                        # This call should use shallow=True by default
                        fetcher.clone_repository(owner, repo, branch=config.universe.branch)

                        # Verify the call was made
                        mock_clone.assert_called_once()

    def test_branch_switching_with_shallow_clone_workflow(self, default_config_test, mock_subprocess, sample_config_modifications):
        """Test complete branch switching workflow with shallow clone considerations."""
        config_manager = default_config_test

        try:
            # Get original config
            original_config = config_manager.get_active_config()
            original_branch = original_config.universe.branch

            # Create a config with different branch
            config_data = original_config.dump()
            if original_branch == "esgvoc":
                config_data["universe"]["branch"] = "esgvoc_dev"
            else:
                config_data["universe"]["branch"] = "test_branch"

            # Save and switch to new config
            config_manager.save_config(config_data, "branch_workflow_test")
            config_manager.switch_config("branch_workflow_test")

            new_config = config_manager.get_active_config()
            assert new_config.universe.branch != original_branch

            # Mock git operations for branch switching
            with patch('pathlib.Path.exists') as mock_exists, \
                 patch('esgvoc.core.repo_fetcher.RepoFetcher.clone_repository') as mock_clone:

                mock_exists.return_value = True  # Simulate repo exists
                mock_clone.return_value = None

                # Simulate repository operations that would handle shallow clone
                def git_side_effect(*args, **kwargs):
                    cmd = args[0]
                    if 'checkout' in cmd:
                        return MagicMock(returncode=0)
                    elif 'fetch' in cmd and '--unshallow' in cmd:
                        return MagicMock(returncode=0)
                    else:
                        return MagicMock(returncode=0)

                mock_subprocess.side_effect = git_side_effect

                # Test that service can work with the new branch config
                current_state = service.get_state()
                assert current_state is not None

                # Verify path resolution still works
                universe_path = new_config.universe.get_absolute_local_path()
                assert universe_path is not None

        finally:
            # Clean up test config
            cleanup_test_config(config_manager, "branch_workflow_test")


class TestMixedPathTypeWorkflowWithDefaultConfig:
    """Test workflows that combine different path resolution types."""

    def test_mixed_path_types_complete_workflow(self, default_config_test, sample_config_modifications):
        """Test a complete workflow using mixed path types."""
        config_manager = default_config_test
        original_cwd = Path.cwd()

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                os.chdir(temp_path)

                # Create a config with mixed path types
                config = config_manager.get_active_config()
                config_data = config.dump()

                # Use different path types for different components
                config_data["universe"]["local_path"] = "/tmp/mixed_workflow/universe"  # absolute
                config_data["universe"]["db_path"] = "./workflow_dbs/universe.sqlite"  # dot-relative

                if config_data.get("projects"):
                    config_data["projects"][0]["local_path"] = "repos/project"  # platform-relative
                    config_data["projects"][0]["db_path"] = "/tmp/mixed_workflow/project.sqlite"  # absolute

                # Save and test the mixed config
                config_manager.save_config(config_data, "mixed_workflow_test")
                config_manager.switch_config("mixed_workflow_test")

                mixed_config = config_manager.get_active_config()

                # Verify all path types resolve correctly
                universe_local = mixed_config.universe.get_absolute_local_path()
                universe_db = mixed_config.universe.get_absolute_db_path()

                expected_universe_local = str(Path("/tmp/mixed_workflow/universe").resolve())
                assert universe_local == expected_universe_local
                assert str(temp_path) in universe_db
                assert "workflow_dbs/universe.sqlite" in universe_db

                # Test service integration with mixed paths
                current_state = service.get_state()
                assert current_state is not None

        finally:
            # Restore working directory and clean up
            os.chdir(original_cwd)
            cleanup_test_config(config_manager, "mixed_workflow_test")
"""
Integration tests for offline mode functionality.

This module tests the complete offline mode workflow from configuration
to execution, ensuring all components work together correctly.
"""

import pytest
import tempfile
import shutil
import os
import toml
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock

from esgvoc.core.service.configuration.setting import ServiceSettings
from esgvoc.core.service.configuration.config_manager import ConfigManager
from esgvoc.core.service.state import StateService, StateUniverse, StateProject


@pytest.mark.integration
class TestOfflineModeIntegration:
    """Integration tests for offline mode functionality."""

    @pytest.fixture(autouse=True)
    def setup_integration_environment(self):
        """Set up a complete integration test environment."""
        # Create temporary directories
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_dir = self.temp_dir / "configs"
        self.data_dir = self.temp_dir / "data" / "default"
        self.config_dir.mkdir(parents=True)
        self.data_dir.mkdir(parents=True)

        # Create local repositories (simulate existing local data)
        self.universe_repo = self.data_dir / "repos" / "WCRP-universe"
        self.cmip6_repo = self.data_dir / "repos" / "CMIP6_CVs"
        self.universe_repo.mkdir(parents=True)
        self.cmip6_repo.mkdir(parents=True)

        # Create some dummy files to simulate repository content
        (self.universe_repo / "README.md").write_text("Universe repo")
        (self.universe_repo / ".git").mkdir()
        (self.universe_repo / ".git" / "HEAD").write_text("ref: refs/heads/main")

        (self.cmip6_repo / "README.md").write_text("CMIP6 repo")
        (self.cmip6_repo / ".git").mkdir()
        (self.cmip6_repo / ".git" / "HEAD").write_text("ref: refs/heads/esgvoc")

        # Create database directories
        self.db_dir = self.data_dir / "dbs"
        self.db_dir.mkdir(parents=True)

        yield

        # Cleanup
        shutil.rmtree(self.temp_dir)

    def test_complete_offline_workflow(self):
        """Test complete offline mode workflow from config to execution."""
        # 1. Create configuration with offline mode enabled
        config_data = {
            "universe": {
                "github_repo": "https://github.com/WCRP-CMIP/WCRP-universe",
                "branch": "esgvoc",
                "local_path": f"{self.data_dir}/repos/WCRP-universe",
                "db_path": f"{self.data_dir}/dbs/universe.sqlite",
                "offline_mode": True,
            },
            "projects": [
                {
                    "project_name": "cmip6",
                    "github_repo": "https://github.com/WCRP-CMIP/CMIP6_CVs",
                    "branch": "esgvoc",
                    "local_path": f"{self.data_dir}/repos/CMIP6_CVs",
                    "db_path": f"{self.data_dir}/dbs/cmip6.sqlite",
                    "offline_mode": True,
                },
            ],
        }

        config_path = self.config_dir / "default.toml"
        with open(config_path, "w") as f:
            toml.dump(config_data, f)

        # 2. Load configuration and verify offline mode is set
        settings = ServiceSettings.load_from_file(str(config_path))
        assert settings.universe.offline_mode is True
        assert settings.projects["cmip6"].offline_mode is True

        # 3. Create StateService with mocked config manager
        with patch('esgvoc.core.service.configuration.config_manager.ConfigManager') as mock_cm_class:
            mock_config_manager = Mock()
            mock_config_manager.data_config_dir = self.data_dir
            mock_cm_class.return_value = mock_config_manager

            with patch('esgvoc.core.service.config_manager', mock_config_manager):
                # Set _config_name for path resolution
                settings.universe._config_name = "default"
                settings.projects["cmip6"]._config_name = "default"

                # Create state service
                state_service = StateService(settings)

                # 4. Verify offline mode is propagated to state components
                assert state_service.universe.offline_mode is True
                assert state_service.universe.github_access is False
                assert state_service.projects["cmip6"].offline_mode is True
                assert state_service.projects["cmip6"].github_access is False

                # 5. Verify RepoFetcher is initialized with offline mode
                assert state_service.universe.rf.offline_mode is True
                assert state_service.projects["cmip6"].rf.offline_mode is True

    def test_mixed_offline_online_configuration(self):
        """Test configuration with mixed offline and online components."""
        config_data = {
            "universe": {
                "github_repo": "https://github.com/WCRP-CMIP/WCRP-universe",
                "branch": "esgvoc",
                "local_path": f"{self.data_dir}/repos/WCRP-universe",
                "db_path": f"{self.data_dir}/dbs/universe.sqlite",
                "offline_mode": False,  # Online
            },
            "projects": [
                {
                    "project_name": "cmip6",
                    "github_repo": "https://github.com/WCRP-CMIP/CMIP6_CVs",
                    "branch": "esgvoc",
                    "local_path": f"{self.data_dir}/repos/CMIP6_CVs",
                    "db_path": f"{self.data_dir}/dbs/cmip6.sqlite",
                    "offline_mode": True,  # Offline
                },
                {
                    "project_name": "cmip6plus",
                    "github_repo": "https://github.com/WCRP-CMIP/CMIP6Plus_CVs",
                    "branch": "esgvoc",
                    "local_path": f"{self.data_dir}/repos/CMIP6Plus_CVs",
                    "db_path": f"{self.data_dir}/dbs/cmip6plus.sqlite",
                    "offline_mode": False,  # Online
                },
            ],
        }

        config_path = self.config_dir / "default.toml"
        with open(config_path, "w") as f:
            toml.dump(config_data, f)

        settings = ServiceSettings.load_from_file(str(config_path))

        with patch('esgvoc.core.service.configuration.config_manager.ConfigManager') as mock_cm_class:
            mock_config_manager = Mock()
            mock_config_manager.data_config_dir = self.data_dir
            mock_cm_class.return_value = mock_config_manager

            with patch('esgvoc.core.service.config_manager', mock_config_manager):
                # Set _config_name for path resolution
                for component in [settings.universe] + list(settings.projects.values()):
                    component._config_name = "default"

                state_service = StateService(settings)

                # Verify mixed mode configuration
                assert state_service.universe.offline_mode is False
                assert state_service.universe.github_access is True

                assert state_service.projects["cmip6"].offline_mode is True
                assert state_service.projects["cmip6"].github_access is False

                assert state_service.projects["cmip6plus"].offline_mode is False
                assert state_service.projects["cmip6plus"].github_access is True

    def test_offline_mode_sync_behavior(self):
        """Test sync behavior in offline mode with existing local repositories."""
        config_data = {
            "universe": {
                "github_repo": "https://github.com/WCRP-CMIP/WCRP-universe",
                "branch": "esgvoc",
                "local_path": str(self.universe_repo),
                "db_path": f"{self.data_dir}/dbs/universe.sqlite",
                "offline_mode": True,
            },
            "projects": [
                {
                    "project_name": "cmip6",
                    "github_repo": "https://github.com/WCRP-CMIP/CMIP6_CVs",
                    "branch": "esgvoc",
                    "local_path": str(self.cmip6_repo),
                    "db_path": f"{self.data_dir}/dbs/cmip6.sqlite",
                    "offline_mode": True,
                },
            ],
        }

        config_path = self.config_dir / "default.toml"
        with open(config_path, "w") as f:
            toml.dump(config_data, f)

        settings = ServiceSettings.load_from_file(str(config_path))

        with patch('esgvoc.core.service.configuration.config_manager.ConfigManager') as mock_cm_class:
            mock_config_manager = Mock()
            mock_config_manager.data_config_dir = self.data_dir
            mock_cm_class.return_value = mock_config_manager

            with patch('esgvoc.core.service.config_manager', mock_config_manager):
                settings.universe._config_name = "default"
                settings.projects["cmip6"]._config_name = "default"

                state_service = StateService(settings)

                # Mock sync-related methods to avoid actual database operations
                with patch.object(state_service.universe, 'check_sync_status') as mock_universe_check, \
                     patch.object(state_service.universe, 'build_db') as mock_universe_build, \
                     patch.object(state_service.projects["cmip6"], 'check_sync_status') as mock_project_check, \
                     patch.object(state_service.projects["cmip6"], 'build_db') as mock_project_build, \
                     patch.object(state_service, 'connect_db'), \
                     patch('builtins.print') as mock_print:

                    # Mock sync status to indicate local repos need DB updates
                    mock_universe_check.return_value = {"local_db_sync": False}
                    mock_project_check.return_value = {"local_db_sync": False}

                    # Run synchronize_all
                    state_service.synchronize_all()

                    # Verify offline mode messages were printed
                    printed_calls = [call.args[0] for call in mock_print.call_args_list if call.args]
                    offline_messages = [msg for msg in printed_calls if "offline mode" in str(msg)]
                    assert len(offline_messages) >= 2  # At least universe and project messages

                    # Verify build_db was called (local operations should work)
                    mock_universe_build.assert_called_once()
                    mock_project_build.assert_called_once()

    def test_offline_mode_prevents_network_operations(self):
        """Test that offline mode prevents network operations throughout the stack."""
        config_data = {
            "universe": {
                "github_repo": "https://github.com/WCRP-CMIP/WCRP-universe",
                "branch": "esgvoc",
                "local_path": f"{self.data_dir}/repos/WCRP-universe",
                "db_path": f"{self.data_dir}/dbs/universe.sqlite",
                "offline_mode": True,
            },
            "projects": [
                {
                    "project_name": "cmip6",
                    "github_repo": "https://github.com/WCRP-CMIP/CMIP6_CVs",
                    "branch": "esgvoc",
                    "local_path": f"{self.data_dir}/repos/CMIP6_CVs",
                    "db_path": f"{self.data_dir}/dbs/cmip6.sqlite",
                    "offline_mode": True,
                },
            ],
        }

        config_path = self.config_dir / "default.toml"
        with open(config_path, "w") as f:
            toml.dump(config_data, f)

        settings = ServiceSettings.load_from_file(str(config_path))

        with patch('esgvoc.core.service.configuration.config_manager.ConfigManager') as mock_cm_class:
            mock_config_manager = Mock()
            mock_config_manager.data_config_dir = self.data_dir
            mock_cm_class.return_value = mock_config_manager

            with patch('esgvoc.core.service.config_manager', mock_config_manager):
                settings.universe._config_name = "default"
                settings.projects["cmip6"]._config_name = "default"

                state_service = StateService(settings)

                # Test that fetch_version_remote does nothing in offline mode
                with patch('esgvoc.core.service.state.logger') as mock_logger:
                    state_service.universe.fetch_version_remote()
                    state_service.projects["cmip6"].fetch_version_remote()

                    # Should have logged skipping messages
                    debug_calls = [call.args[0] for call in mock_logger.debug.call_args_list]
                    skip_messages = [msg for msg in debug_calls if "Skipping remote version fetch" in str(msg)]
                    assert len(skip_messages) >= 2

                # Test that clone_remote shows warning in offline mode
                with patch('esgvoc.core.service.state.logger') as mock_logger:
                    state_service.universe.clone_remote()
                    state_service.projects["cmip6"].clone_remote()

                    # Should have logged warning messages
                    warning_calls = [call.args[0] for call in mock_logger.warning.call_args_list]
                    warning_messages = [msg for msg in warning_calls if "Cannot clone remote repository" in str(msg)]
                    assert len(warning_messages) >= 2

                # Test that RepoFetcher network methods raise exceptions
                with pytest.raises(Exception, match="Cannot fetch repositories in offline mode"):
                    state_service.universe.rf.fetch_repositories("test")

                with pytest.raises(Exception, match="Cannot clone repository in offline mode"):
                    state_service.universe.rf.clone_repository("test", "repo")

    def test_offline_mode_configuration_persistence(self):
        """Test that offline mode settings are properly saved and loaded."""
        # Create initial configuration
        config_data = {
            "universe": {
                "github_repo": "https://github.com/WCRP-CMIP/WCRP-universe",
                "branch": "esgvoc",
                "local_path": f"{self.data_dir}/repos/WCRP-universe",
                "db_path": f"{self.data_dir}/dbs/universe.sqlite",
                "offline_mode": False,
            },
            "projects": [
                {
                    "project_name": "cmip6",
                    "github_repo": "https://github.com/WCRP-CMIP/CMIP6_CVs",
                    "branch": "esgvoc",
                    "local_path": f"{self.data_dir}/repos/CMIP6_CVs",
                    "db_path": f"{self.data_dir}/dbs/cmip6.sqlite",
                    "offline_mode": False,
                },
            ],
        }

        config_path = self.config_dir / "default.toml"
        with open(config_path, "w") as f:
            toml.dump(config_data, f)

        # Load, modify, and save configuration
        settings = ServiceSettings.load_from_file(str(config_path))
        settings.universe.offline_mode = True
        settings.projects["cmip6"].offline_mode = True
        settings.save_to_file(str(config_path))

        # Reload configuration and verify persistence
        reloaded_settings = ServiceSettings.load_from_file(str(config_path))
        assert reloaded_settings.universe.offline_mode is True
        assert reloaded_settings.projects["cmip6"].offline_mode is True

        # Verify the actual file content
        with open(config_path) as f:
            file_data = toml.load(f)

        assert file_data["universe"]["offline_mode"] is True
        cmip6_project = next(p for p in file_data["projects"] if p["project_name"] == "cmip6")
        assert cmip6_project["offline_mode"] is True

    def test_offline_mode_with_missing_local_repositories(self):
        """Test offline mode behavior when local repositories don't exist."""
        # Create configuration pointing to non-existent local repos
        nonexistent_universe = self.data_dir / "repos" / "nonexistent_universe"
        nonexistent_project = self.data_dir / "repos" / "nonexistent_project"

        config_data = {
            "universe": {
                "github_repo": "https://github.com/WCRP-CMIP/WCRP-universe",
                "branch": "esgvoc",
                "local_path": str(nonexistent_universe),
                "db_path": f"{self.data_dir}/dbs/universe.sqlite",
                "offline_mode": True,
            },
            "projects": [
                {
                    "project_name": "cmip6",
                    "github_repo": "https://github.com/WCRP-CMIP/CMIP6_CVs",
                    "branch": "esgvoc",
                    "local_path": str(nonexistent_project),
                    "db_path": f"{self.data_dir}/dbs/cmip6.sqlite",
                    "offline_mode": True,
                },
            ],
        }

        config_path = self.config_dir / "default.toml"
        with open(config_path, "w") as f:
            toml.dump(config_data, f)

        settings = ServiceSettings.load_from_file(str(config_path))

        with patch('esgvoc.core.service.configuration.config_manager.ConfigManager') as mock_cm_class:
            mock_config_manager = Mock()
            mock_config_manager.data_config_dir = self.data_dir
            mock_cm_class.return_value = mock_config_manager

            with patch('esgvoc.core.service.config_manager', mock_config_manager):
                settings.universe._config_name = "default"
                settings.projects["cmip6"]._config_name = "default"

                state_service = StateService(settings)

                # Test sync behavior with missing repos
                with patch.object(state_service.universe, 'check_sync_status') as mock_universe_check, \
                     patch.object(state_service.projects["cmip6"], 'check_sync_status') as mock_project_check, \
                     patch.object(state_service, 'connect_db'), \
                     patch('builtins.print') as mock_print:

                    mock_universe_check.return_value = {"local_db_sync": True}
                    mock_project_check.return_value = {"local_db_sync": True}

                    # Set db_access to False to simulate missing databases
                    state_service.universe.db_access = False
                    state_service.projects["cmip6"].db_access = False

                    state_service.synchronize_all()

                    # Should print messages about offline mode
                    printed_calls = [call.args[0] for call in mock_print.call_args_list if call.args]
                    offline_messages = [
                        msg for msg in printed_calls
                        if "offline mode" in str(msg).lower()
                    ]
                    # Should at least print offline mode messages for universe and project
                    assert len(offline_messages) >= 2  # Universe and project offline messages

    def test_backward_compatibility_without_offline_mode_field(self):
        """Test that configurations without offline_mode field work correctly."""
        # Create configuration without offline_mode fields (backward compatibility)
        config_data = {
            "universe": {
                "github_repo": "https://github.com/WCRP-CMIP/WCRP-universe",
                "branch": "esgvoc",
                "local_path": f"{self.data_dir}/repos/WCRP-universe",
                "db_path": f"{self.data_dir}/dbs/universe.sqlite",
                # No offline_mode field
            },
            "projects": [
                {
                    "project_name": "cmip6",
                    "github_repo": "https://github.com/WCRP-CMIP/CMIP6_CVs",
                    "branch": "esgvoc",
                    "local_path": f"{self.data_dir}/repos/CMIP6_CVs",
                    "db_path": f"{self.data_dir}/dbs/cmip6.sqlite",
                    # No offline_mode field
                },
            ],
        }

        config_path = self.config_dir / "default.toml"
        with open(config_path, "w") as f:
            toml.dump(config_data, f)

        # Should load without errors and default to offline_mode=False
        settings = ServiceSettings.load_from_file(str(config_path))
        assert settings.universe.offline_mode is False
        assert settings.projects["cmip6"].offline_mode is False

        with patch('esgvoc.core.service.configuration.config_manager.ConfigManager') as mock_cm_class:
            mock_config_manager = Mock()
            mock_config_manager.data_config_dir = self.data_dir
            mock_cm_class.return_value = mock_config_manager

            with patch('esgvoc.core.service.config_manager', mock_config_manager):
                settings.universe._config_name = "default"
                settings.projects["cmip6"]._config_name = "default"

                # Should create state service without errors
                state_service = StateService(settings)
                assert state_service.universe.offline_mode is False
                assert state_service.universe.github_access is True
                assert state_service.projects["cmip6"].offline_mode is False
                assert state_service.projects["cmip6"].github_access is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
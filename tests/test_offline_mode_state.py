"""
Tests for offline mode behavior in BaseState and StateService classes.

This module tests that offline mode correctly affects state management,
version fetching, sync operations, and repository handling.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from esgvoc.core.service.state import BaseState, StateService, StateUniverse, StateProject
from esgvoc.core.service.configuration.setting import ServiceSettings, UniverseSettings, ProjectSettings


class TestBaseStateOfflineMode:
    """Test BaseState offline mode functionality."""

    def test_base_state_offline_mode_false_by_default(self):
        """Test that BaseState has github_access=True when offline_mode=False."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('esgvoc.core.service.config_manager') as mock_config_manager:
                mock_config_manager.data_config_dir = Path(temp_dir)

                state = BaseState(
                    github_repo="https://github.com/test/repo",
                    offline_mode=False
                )

                assert state.offline_mode is False
                assert state.github_access is True

    def test_base_state_offline_mode_true_disables_github_access(self):
        """Test that BaseState has github_access=False when offline_mode=True."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('esgvoc.core.service.config_manager') as mock_config_manager:
                mock_config_manager.data_config_dir = Path(temp_dir)

                state = BaseState(
                    github_repo="https://github.com/test/repo",
                    offline_mode=True
                )

                assert state.offline_mode is True
                assert state.github_access is False

    def test_base_state_fetch_version_remote_skipped_in_offline_mode(self):
        """Test that fetch_version_remote is skipped when offline_mode=True."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('esgvoc.core.service.config_manager') as mock_config_manager:
                mock_config_manager.data_config_dir = Path(temp_dir)

                # Create offline state
                state = BaseState(
                    github_repo="https://github.com/test/repo",
                    offline_mode=True
                )

                # Mock the RepoFetcher to ensure it's not called
                mock_rf = Mock()
                state.rf = mock_rf

                # Call fetch_version_remote
                state.fetch_version_remote()

                # RepoFetcher should not be called in offline mode
                mock_rf.get_github_version.assert_not_called()
                assert state.github_access is False
                assert state.github_version is None

    def test_base_state_fetch_version_remote_works_in_online_mode(self):
        """Test that fetch_version_remote works when offline_mode=False."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('esgvoc.core.service.config_manager') as mock_config_manager:
                mock_config_manager.data_config_dir = Path(temp_dir)

                # Create online state
                state = BaseState(
                    github_repo="https://github.com/test/repo",
                    branch="main",
                    offline_mode=False
                )

                # Mock successful RepoFetcher
                mock_rf = Mock()
                mock_rf.get_github_version.return_value = "abc123"
                state.rf = mock_rf

                # Call fetch_version_remote
                state.fetch_version_remote()

                # RepoFetcher should be called
                mock_rf.get_github_version.assert_called_once_with("test", "repo", "main")
                assert state.github_access is True
                assert state.github_version == "abc123"

    def test_base_state_clone_remote_blocked_in_offline_mode(self):
        """Test that clone_remote is blocked when offline_mode=True."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('esgvoc.core.service.config_manager') as mock_config_manager:
                mock_config_manager.data_config_dir = Path(temp_dir)

                state = BaseState(
                    github_repo="https://github.com/test/repo",
                    offline_mode=True
                )

                # Mock the RepoFetcher
                mock_rf = Mock()
                state.rf = mock_rf

                # Mock logger to capture warning
                with patch('esgvoc.core.service.state.logger') as mock_logger:
                    state.clone_remote()

                    # Should log warning and not call RepoFetcher
                    mock_logger.warning.assert_called_once_with("Cannot clone remote repository in offline mode")
                    mock_rf.clone_repository.assert_not_called()

    def test_base_state_clone_remote_works_in_online_mode(self):
        """Test that clone_remote works when offline_mode=False."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('esgvoc.core.service.config_manager') as mock_config_manager:
                mock_config_manager.data_config_dir = Path(temp_dir)

                state = BaseState(
                    github_repo="https://github.com/test/repo",
                    branch="main",
                    local_path="repos/test",
                    offline_mode=False
                )

                # Mock the RepoFetcher and fetch_version_local
                mock_rf = Mock()
                state.rf = mock_rf

                with patch.object(state, 'fetch_version_local') as mock_fetch_local:
                    state.clone_remote()

                    # Should call RepoFetcher
                    mock_rf.clone_repository.assert_called_once_with("test", "repo", "main", "repos/test")
                    mock_fetch_local.assert_called_once()

    def test_base_state_sync_offline_mode_with_local_repo(self):
        """Test sync in offline mode with existing local repository."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('esgvoc.core.service.config_manager') as mock_config_manager:
                mock_config_manager.data_config_dir = Path(temp_dir)

                # Create test local path
                local_path = os.path.join(temp_dir, "test_repo")
                os.makedirs(local_path)

                state = BaseState(
                    github_repo="https://github.com/test/repo",
                    local_path=local_path,
                    db_path="test.db",
                    offline_mode=True
                )

                # Mock methods
                with patch.object(state, 'check_sync_status') as mock_check_sync, \
                     patch.object(state, 'build_db') as mock_build_db, \
                     patch('builtins.print') as mock_print:

                    # Mock sync status to indicate local DB needs update
                    mock_check_sync.return_value = {"local_db_sync": False}

                    # Call sync
                    result = state.sync()

                    # Should build DB and print offline message
                    assert result is True
                    mock_build_db.assert_called_once()
                    mock_print.assert_any_call("Running in offline mode - only using local repositories and databases")

    def test_base_state_sync_offline_mode_no_local_repo(self):
        """Test sync in offline mode without local repository."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('esgvoc.core.service.config_manager') as mock_config_manager:
                mock_config_manager.data_config_dir = Path(temp_dir)

                local_path = os.path.join(temp_dir, "nonexistent_repo")

                state = BaseState(
                    github_repo="https://github.com/test/repo",
                    local_path=local_path,
                    db_path="test.db",
                    offline_mode=True
                )

                # Mock methods
                with patch.object(state, 'check_sync_status') as mock_check_sync, \
                     patch('builtins.print') as mock_print:

                    mock_check_sync.return_value = {"local_db_sync": True}
                    state.db_access = False  # Simulate no DB access

                    # Call sync
                    result = state.sync()

                    # Should print offline mode message
                    mock_print.assert_any_call("Running in offline mode - only using local repositories and databases")
                    # The exact behavior may vary, but we should see offline mode handling

    def test_base_state_sync_online_mode_normal_flow(self):
        """Test that sync works normally in online mode."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('esgvoc.core.service.config_manager') as mock_config_manager:
                mock_config_manager.data_config_dir = Path(temp_dir)

                state = BaseState(
                    github_repo="https://github.com/test/repo",
                    offline_mode=False
                )

                # Mock methods for normal online flow
                with patch.object(state, 'check_sync_status') as mock_check_sync, \
                     patch.object(state, 'clone_remote') as mock_clone, \
                     patch.object(state, 'build_db') as mock_build_db, \
                     patch('builtins.print') as mock_print:

                    # Mock sync status to trigger clone and build
                    mock_check_sync.return_value = {
                        "github_db_sync": None,
                        "local_db_sync": None,
                        "github_local_sync": None
                    }

                    # Call sync
                    result = state.sync()

                    # Should use normal online flow
                    assert result is True
                    mock_clone.assert_called_once()
                    mock_build_db.assert_called_once()
                    # Should not print offline mode message
                    mock_print.assert_not_called()


class TestStateUniverseOfflineMode:
    """Test StateUniverse offline mode functionality."""

    def test_state_universe_passes_offline_mode_to_base_state(self):
        """Test that StateUniverse passes offline_mode to BaseState."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('esgvoc.core.service.config_manager') as mock_config_manager:
                mock_config_manager.data_config_dir = Path(temp_dir)

                # Create UniverseSettings with offline mode
                universe_settings = UniverseSettings(
                    github_repo="https://github.com/test/universe",
                    offline_mode=True
                )
                universe_settings._config_name = "test"

                with patch.object(UniverseSettings, 'get_absolute_local_path', return_value=temp_dir), \
                     patch.object(UniverseSettings, 'get_absolute_db_path', return_value=f"{temp_dir}/test.db"):

                    state_universe = StateUniverse(universe_settings)

                    # Should pass offline_mode to BaseState
                    assert state_universe.offline_mode is True
                    assert state_universe.github_access is False


class TestStateProjectOfflineMode:
    """Test StateProject offline mode functionality."""

    def test_state_project_passes_offline_mode_to_base_state(self):
        """Test that StateProject passes offline_mode to BaseState."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('esgvoc.core.service.config_manager') as mock_config_manager:
                mock_config_manager.data_config_dir = Path(temp_dir)

                # Create ProjectSettings with offline mode
                project_settings = ProjectSettings(
                    project_name="test_project",
                    github_repo="https://github.com/test/project",
                    offline_mode=True
                )
                project_settings._config_name = "test"

                with patch.object(ProjectSettings, 'get_absolute_local_path', return_value=temp_dir), \
                     patch.object(ProjectSettings, 'get_absolute_db_path', return_value=f"{temp_dir}/test.db"):

                    state_project = StateProject(project_settings)

                    # Should pass offline_mode to BaseState
                    assert state_project.offline_mode is True
                    assert state_project.github_access is False
                    assert state_project.project_name == "test_project"


class TestStateServiceOfflineMode:
    """Test StateService offline mode functionality."""

    def test_state_service_synchronize_all_with_offline_components(self):
        """Test StateService synchronize_all shows offline mode messages."""
        # Create test settings with mixed offline modes
        config_dict = {
            "universe": {
                "github_repo": "https://github.com/test/universe",
                "offline_mode": True,
            },
            "projects": [
                {
                    "project_name": "project1",
                    "github_repo": "https://github.com/test/project1",
                    "offline_mode": False,
                },
                {
                    "project_name": "project2",
                    "github_repo": "https://github.com/test/project2",
                    "offline_mode": True,
                }
            ],
        }

        settings = ServiceSettings.load_from_dict(config_dict)

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('esgvoc.core.service.config_manager') as mock_config_manager:
                mock_config_manager.data_config_dir = Path(temp_dir)

                # Set config names
                for component in [settings.universe] + list(settings.projects.values()):
                    component._config_name = "test"

                with patch.object(UniverseSettings, 'get_absolute_local_path', return_value=temp_dir), \
                     patch.object(UniverseSettings, 'get_absolute_db_path', return_value=f"{temp_dir}/test.db"), \
                     patch.object(ProjectSettings, 'get_absolute_local_path', return_value=temp_dir), \
                     patch.object(ProjectSettings, 'get_absolute_db_path', return_value=f"{temp_dir}/test.db"):

                    state_service = StateService(settings)

                    # Mock sync methods and connect_db
                    for state in [state_service.universe] + list(state_service.projects.values()):
                        state.sync = Mock(return_value=False)
                        state.connect_db = Mock()

                    with patch.object(state_service, 'connect_db'), \
                         patch('builtins.print') as mock_print:

                        state_service.synchronize_all()

                        # Should print offline mode messages
                        mock_print.assert_any_call("Universe is in offline mode")
                        mock_print.assert_any_call("Project project2 is in offline mode")
                        # Should NOT print message for project1 (online mode)

    def test_state_service_all_online_no_offline_messages(self):
        """Test StateService doesn't show offline messages when all components are online."""
        # Create test settings with all components online
        config_dict = {
            "universe": {
                "github_repo": "https://github.com/test/universe",
                "offline_mode": False,
            },
            "projects": [
                {
                    "project_name": "project1",
                    "github_repo": "https://github.com/test/project1",
                    "offline_mode": False,
                }
            ],
        }

        settings = ServiceSettings.load_from_dict(config_dict)

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('esgvoc.core.service.config_manager') as mock_config_manager:
                mock_config_manager.data_config_dir = Path(temp_dir)

                # Set config names
                for component in [settings.universe] + list(settings.projects.values()):
                    component._config_name = "test"

                with patch.object(UniverseSettings, 'get_absolute_local_path', return_value=temp_dir), \
                     patch.object(UniverseSettings, 'get_absolute_db_path', return_value=f"{temp_dir}/test.db"), \
                     patch.object(ProjectSettings, 'get_absolute_local_path', return_value=temp_dir), \
                     patch.object(ProjectSettings, 'get_absolute_db_path', return_value=f"{temp_dir}/test.db"):

                    state_service = StateService(settings)

                    # Mock sync methods and connect_db
                    for state in [state_service.universe] + list(state_service.projects.values()):
                        state.sync = Mock(return_value=False)
                        state.connect_db = Mock()

                    with patch.object(state_service, 'connect_db'), \
                         patch('builtins.print') as mock_print:

                        state_service.synchronize_all()

                        # Should NOT print offline mode messages
                        printed_calls = [call.args[0] for call in mock_print.call_args_list]
                        offline_messages = [msg for msg in printed_calls if "offline mode" in str(msg)]
                        assert len(offline_messages) == 0

    def test_repo_fetcher_initialized_with_offline_mode(self):
        """Test that RepoFetcher is initialized with correct offline_mode."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('esgvoc.core.service.config_manager') as mock_config_manager:
                mock_config_manager.data_config_dir = Path(temp_dir)

                # Test offline mode
                state_offline = BaseState(
                    github_repo="https://github.com/test/repo",
                    offline_mode=True
                )
                assert state_offline.rf.offline_mode is True

                # Test online mode
                state_online = BaseState(
                    github_repo="https://github.com/test/repo",
                    offline_mode=False
                )
                assert state_online.rf.offline_mode is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
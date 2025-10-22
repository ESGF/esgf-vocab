"""
Tests for offline mode restrictions in RepoFetcher.

This module tests that RepoFetcher properly blocks network operations
when initialized with offline_mode=True and works normally when offline_mode=False.
"""

import pytest
from unittest.mock import patch, Mock
import subprocess

from esgvoc.core.repo_fetcher import RepoFetcher


class TestRepoFetcherOfflineMode:
    """Test RepoFetcher offline mode functionality."""

    def test_repo_fetcher_offline_mode_default_false(self):
        """Test that RepoFetcher has offline_mode=False by default."""
        fetcher = RepoFetcher()
        assert fetcher.offline_mode is False

    def test_repo_fetcher_offline_mode_explicit_true(self):
        """Test that RepoFetcher can be set to offline_mode=True."""
        fetcher = RepoFetcher(offline_mode=True)
        assert fetcher.offline_mode is True

    def test_repo_fetcher_offline_mode_explicit_false(self):
        """Test that RepoFetcher can be explicitly set to offline_mode=False."""
        fetcher = RepoFetcher(offline_mode=False)
        assert fetcher.offline_mode is False

    @patch("esgvoc.core.repo_fetcher.requests.get")
    def test_fetch_repositories_blocked_in_offline_mode(self, mock_get):
        """Test that fetch_repositories raises exception in offline mode."""
        fetcher = RepoFetcher(offline_mode=True)

        with pytest.raises(Exception, match="Cannot fetch repositories in offline mode"):
            fetcher.fetch_repositories("testuser")

        # Ensure no network call was made
        mock_get.assert_not_called()

    @patch("esgvoc.core.repo_fetcher.requests.get")
    def test_fetch_repositories_works_in_online_mode(self, mock_get):
        """Test that fetch_repositories works normally in online mode."""
        fetcher = RepoFetcher(offline_mode=False)

        # Mock successful response
        mock_response = {
            "id": 12345,
            "name": "test-repo",
            "full_name": "testuser/test-repo",
            "description": "A test repository",
            "html_url": "https://github.com/testuser/test-repo",
            "stargazers_count": 10,
            "forks_count": 5,
            "language": "Python",
            "created_at": "2020-01-01T00:00:00Z",
            "updated_at": "2020-06-01T00:00:00Z",
        }
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = [mock_response]

        repos = fetcher.fetch_repositories("testuser")

        # Should make network call and return results
        mock_get.assert_called_once()
        assert len(repos) == 1
        assert repos[0].name == "test-repo"

    @patch("esgvoc.core.repo_fetcher.requests.get")
    def test_fetch_repository_details_blocked_in_offline_mode(self, mock_get):
        """Test that fetch_repository_details raises exception in offline mode."""
        fetcher = RepoFetcher(offline_mode=True)

        with pytest.raises(Exception, match="Cannot fetch repository details in offline mode"):
            fetcher.fetch_repository_details("testuser", "test-repo")

        # Ensure no network call was made
        mock_get.assert_not_called()

    @patch("esgvoc.core.repo_fetcher.requests.get")
    def test_fetch_repository_details_works_in_online_mode(self, mock_get):
        """Test that fetch_repository_details works normally in online mode."""
        fetcher = RepoFetcher(offline_mode=False)

        # Mock successful response
        mock_response = {
            "id": 12345,
            "name": "test-repo",
            "full_name": "testuser/test-repo",
            "description": "A test repository",
            "html_url": "https://github.com/testuser/test-repo",
            "stargazers_count": 10,
            "forks_count": 5,
            "language": "Python",
            "created_at": "2020-01-01T00:00:00Z",
            "updated_at": "2020-06-01T00:00:00Z",
        }
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_response

        repo = fetcher.fetch_repository_details("testuser", "test-repo")

        # Should make network call and return results
        mock_get.assert_called_once()
        assert repo.name == "test-repo"

    @patch("esgvoc.core.repo_fetcher.requests.get")
    def test_fetch_branch_details_blocked_in_offline_mode(self, mock_get):
        """Test that fetch_branch_details raises exception in offline mode."""
        fetcher = RepoFetcher(offline_mode=True)

        with pytest.raises(Exception, match="Cannot fetch branch details in offline mode"):
            fetcher.fetch_branch_details("testuser", "test-repo", "main")

        # Ensure no network call was made
        mock_get.assert_not_called()

    @patch("esgvoc.core.repo_fetcher.requests.get")
    def test_fetch_branch_details_works_in_online_mode(self, mock_get):
        """Test that fetch_branch_details works normally in online mode."""
        fetcher = RepoFetcher(offline_mode=False)

        # Mock successful response
        mock_response = {
            "name": "main",
            "commit": {
                "sha": "abc123",
                "url": "https://api.github.com/repos/testuser/test-repo/commits/abc123",
            },
            "protected": False,
        }
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_response

        branch = fetcher.fetch_branch_details("testuser", "test-repo", "main")

        # Should make network call and return results
        mock_get.assert_called_once()
        assert branch.name == "main"
        assert branch.commit["sha"] == "abc123"

    @patch("esgvoc.core.repo_fetcher.requests.get")
    def test_list_directory_blocked_in_offline_mode(self, mock_get):
        """Test that list_directory raises exception in offline mode."""
        fetcher = RepoFetcher(offline_mode=True)

        with pytest.raises(Exception, match="Cannot list directories in offline mode"):
            fetcher.list_directory("testuser", "test-repo", "main")

        # Ensure no network call was made
        mock_get.assert_not_called()

    @patch("esgvoc.core.repo_fetcher.requests.get")
    def test_list_directory_works_in_online_mode(self, mock_get):
        """Test that list_directory works normally in online mode."""
        fetcher = RepoFetcher(offline_mode=False)

        # Mock successful response
        mock_response = [
            {"name": "src", "type": "dir"},
            {"name": "README.md", "type": "file"},
            {"name": "tests", "type": "dir"},
        ]
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_response

        directories = fetcher.list_directory("testuser", "test-repo", "main")

        # Should make network call and return directories only
        mock_get.assert_called_once()
        assert directories == ["src", "tests"]

    @patch("esgvoc.core.repo_fetcher.requests.get")
    def test_list_files_blocked_in_offline_mode(self, mock_get):
        """Test that list_files raises exception in offline mode."""
        fetcher = RepoFetcher(offline_mode=True)

        with pytest.raises(Exception, match="Cannot list files in offline mode"):
            fetcher.list_files("testuser", "test-repo", "src", "main")

        # Ensure no network call was made
        mock_get.assert_not_called()

    @patch("esgvoc.core.repo_fetcher.requests.get")
    def test_list_files_works_in_online_mode(self, mock_get):
        """Test that list_files works normally in online mode."""
        fetcher = RepoFetcher(offline_mode=False)

        # Mock successful response
        mock_response = [
            {"name": "__init__.py", "type": "file"},
            {"name": "main.py", "type": "file"},
            {"name": "utils", "type": "dir"},
        ]
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_response

        files = fetcher.list_files("testuser", "test-repo", "src", "main")

        # Should make network call and return files only
        mock_get.assert_called_once()
        assert files == ["__init__.py", "main.py"]

    @patch("subprocess.run")
    def test_clone_repository_blocked_in_offline_mode(self, mock_run):
        """Test that clone_repository raises exception in offline mode."""
        fetcher = RepoFetcher(offline_mode=True)

        with pytest.raises(Exception, match="Cannot clone repository in offline mode"):
            fetcher.clone_repository("testuser", "test-repo")

        # Ensure no subprocess call was made
        mock_run.assert_not_called()

    @patch("subprocess.run")
    def test_clone_repository_works_in_online_mode(self, mock_run):
        """Test that clone_repository works normally in online mode."""
        fetcher = RepoFetcher(offline_mode=False)

        # Mock successful subprocess run
        mock_run.return_value = Mock()

        fetcher.clone_repository("testuser", "test-repo")

        # Should make subprocess call
        mock_run.assert_called_once()
        expected_cmd = [
            "git", "clone", "https://github.com/testuser/test-repo.git",
            ".cache/repos/test-repo", "--depth", "1"
        ]
        mock_run.assert_called_with(expected_cmd, check=True)

    @patch("subprocess.run")
    def test_clone_repository_with_branch_in_online_mode(self, mock_run):
        """Test that clone_repository with branch works normally in online mode."""
        fetcher = RepoFetcher(offline_mode=False)

        # Mock successful subprocess run
        mock_run.return_value = Mock()

        fetcher.clone_repository("testuser", "test-repo", branch="develop")

        # Should make subprocess call with branch
        mock_run.assert_called_once()
        expected_cmd = [
            "git", "clone", "https://github.com/testuser/test-repo.git",
            ".cache/repos/test-repo", "--depth", "1", "--branch", "develop"
        ]
        mock_run.assert_called_with(expected_cmd, check=True)

    def test_get_github_version_blocked_in_offline_mode(self):
        """Test that get_github_version returns None in offline mode."""
        fetcher = RepoFetcher(offline_mode=True)

        with patch('esgvoc.core.repo_fetcher._LOGGER') as mock_logger:
            result = fetcher.get_github_version("testuser", "test-repo", "main")

            # Should return None and log debug message
            assert result is None
            mock_logger.debug.assert_called_with("Cannot get GitHub version in offline mode")

    @patch("subprocess.run")
    def test_get_github_version_works_in_online_mode(self, mock_run):
        """Test that get_github_version works normally in online mode."""
        fetcher = RepoFetcher(offline_mode=False)

        # Mock successful subprocess run
        mock_result = Mock()
        mock_result.stdout = "abc123def456\trefs/heads/main\n"
        mock_run.return_value = mock_result

        result = fetcher.get_github_version("testuser", "test-repo", "main")

        # Should make subprocess call and return commit hash
        mock_run.assert_called_once()
        assert result == "abc123def456"

    @patch("subprocess.run")
    def test_get_github_version_handles_subprocess_error_in_online_mode(self, mock_run):
        """Test that get_github_version handles subprocess errors in online mode."""
        fetcher = RepoFetcher(offline_mode=False)

        # Mock subprocess error
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        with patch('esgvoc.core.repo_fetcher._LOGGER') as mock_logger:
            result = fetcher.get_github_version("testuser", "test-repo", "main")

            # Should return None and log error
            assert result is None
            mock_logger.debug.assert_called()

    def test_get_github_version_with_api_blocked_in_offline_mode(self):
        """Test that get_github_version_with_api raises exception in offline mode."""
        fetcher = RepoFetcher(offline_mode=True)

        with pytest.raises(Exception, match="Cannot get GitHub version in offline mode"):
            fetcher.get_github_version_with_api("testuser", "test-repo", "main")

    @patch("esgvoc.core.repo_fetcher.requests.get")
    def test_get_github_version_with_api_works_in_online_mode(self, mock_get):
        """Test that get_github_version_with_api works normally in online mode."""
        fetcher = RepoFetcher(offline_mode=False)

        # Mock successful API response
        mock_response = {
            "name": "main",
            "commit": {
                "sha": "abc123def456",
                "url": "https://api.github.com/repos/testuser/test-repo/commits/abc123def456",
            },
            "protected": False,
        }
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_response

        result = fetcher.get_github_version_with_api("testuser", "test-repo", "main")

        # Should make API call and return commit hash
        mock_get.assert_called_once()
        assert result == "abc123def456"

    def test_get_local_repo_version_works_regardless_of_offline_mode(self):
        """Test that get_local_repo_version works regardless of offline mode."""
        # This method should work the same in both online and offline modes
        # since it only accesses local files

        fetcher_offline = RepoFetcher(offline_mode=True)
        fetcher_online = RepoFetcher(offline_mode=False)

        with patch('subprocess.run') as mock_run, \
             patch('os.path.exists', return_value=True), \
             patch('subprocess.check_output') as mock_check_output:
            mock_result = Mock()
            mock_result.stdout = "abc123def456"
            mock_result.stderr = ""
            mock_result.returncode = 0
            mock_run.return_value = mock_result
            mock_check_output.return_value = "abc123def456"

            # Both should work the same way
            result_offline = fetcher_offline.get_local_repo_version("/fake/repo/path")
            result_online = fetcher_online.get_local_repo_version("/fake/repo/path")

            assert result_offline == "abc123def456"
            assert result_online == "abc123def456"
            assert mock_run.call_count == 2


class TestRepoFetcherInitialization:
    """Test RepoFetcher initialization with different parameters."""

    def test_repo_fetcher_init_all_parameters(self):
        """Test RepoFetcher initialization with all parameters."""
        fetcher = RepoFetcher(
            base_url="https://api.custom.com",
            local_path="/custom/path",
            offline_mode=True
        )

        assert fetcher.base_url == "https://api.custom.com"
        assert fetcher.repo_dir == "/custom/path"
        assert fetcher.offline_mode is True

    def test_repo_fetcher_init_default_parameters(self):
        """Test RepoFetcher initialization with default parameters."""
        fetcher = RepoFetcher()

        assert fetcher.base_url == "https://api.github.com"
        assert fetcher.repo_dir == ".cache/repos"
        assert fetcher.offline_mode is False


class TestRepoFetcherMixedOperations:
    """Test RepoFetcher with mixed online/offline operations."""

    def test_switch_offline_mode_during_runtime(self):
        """Test that RepoFetcher respects offline_mode changes."""
        fetcher = RepoFetcher(offline_mode=False)

        # Initially should be online
        assert fetcher.offline_mode is False

        # Switch to offline mode
        fetcher.offline_mode = True

        # Now network operations should be blocked
        with pytest.raises(Exception, match="Cannot fetch repositories in offline mode"):
            fetcher.fetch_repositories("testuser")

        # Switch back to online mode
        fetcher.offline_mode = False

        # Now network operations should work again
        with patch("esgvoc.core.repo_fetcher.requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = []

            try:
                fetcher.fetch_repositories("testuser")
                # Should not raise exception
            except Exception as e:
                pytest.fail(f"Unexpected exception: {e}")

    def test_local_operations_unaffected_by_offline_mode(self):
        """Test that local operations work the same in both modes."""
        fetcher_offline = RepoFetcher(offline_mode=True)
        fetcher_online = RepoFetcher(offline_mode=False)

        # Local operations should work the same way
        with patch('subprocess.run') as mock_run, \
             patch('os.path.exists', return_value=True), \
             patch('subprocess.check_output') as mock_check_output:

            mock_result = Mock()
            mock_result.stdout = "abc123"
            mock_result.stderr = ""
            mock_result.returncode = 0
            mock_run.return_value = mock_result
            mock_check_output.return_value = "abc123"

            # Both should work identically for local operations
            result1 = fetcher_offline.get_local_repo_version("/fake/path")
            result2 = fetcher_online.get_local_repo_version("/fake/path")

            assert result1 == result2 == "abc123"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
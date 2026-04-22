
import pytest
from unittest.mock import patch
from esgvoc.core.repo_fetcher import RepoFetcher 

@pytest.fixture
def fetcher():
    return RepoFetcher()


@patch("esgvoc.core.repo_fetcher.requests.get")
def test_fetch_repositories_success(mock_get, fetcher):
    """
    Test successful fetching of repositories for a user.
    """
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

    assert len(repos) == 1
    assert repos[0].id == 12345
    assert repos[0].name == "test-repo"
    assert repos[0].full_name == "testuser/test-repo"
    assert repos[0].stargazers_count == 10
    assert repos[0].forks_count == 5
    assert repos[0].language == "Python"


@patch("esgvoc.core.repo_fetcher.requests.get")
def test_fetch_repositories_failure(mock_get, fetcher):
    """
    Test failure when fetching repositories with a non-200 status code.
    """
    mock_get.return_value.status_code = 404
    mock_get.return_value.json.return_value = {"message": "Not Found"}

    with pytest.raises(Exception, match="Failed to fetch data: 404 - .*"):
        fetcher.fetch_repositories("invaliduser")


@patch("esgvoc.core.repo_fetcher.requests.get")
def test_fetch_repository_details_success(mock_get, fetcher):
    """
    Test successful fetching of a single repository's details.
    """
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

    assert repo.id == 12345
    assert repo.name == "test-repo"
    assert repo.full_name == "testuser/test-repo"
    assert repo.stargazers_count == 10
    assert repo.forks_count == 5
    assert repo.language == "Python"


@patch("esgvoc.core.repo_fetcher.requests.get")
def test_fetch_repository_details_failure(mock_get, fetcher):
    """
    Test failure when fetching a repository's details with a non-200 status code.
    """
    mock_get.return_value.status_code = 404
    mock_get.return_value.json.return_value = {"message": "Not Found"}

    with pytest.raises(Exception, match="Failed to fetch data: 404 - .*"):
        fetcher.fetch_repository_details("invaliduser", "invalid-repo")


@patch("esgvoc.core.repo_fetcher.requests.get")
def test_fetch_branch_details_success(mock_get, fetcher):
    """
    Test successful fetching of a specific branch's details.
    """
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

    assert branch.name == "main"
    assert branch.commit["sha"] == "abc123"
    assert branch.protected is False


@patch("esgvoc.core.repo_fetcher.requests.get")
def test_fetch_branch_details_failure(mock_get, fetcher):
    """
    Test failure when fetching a branch's details with a non-200 status code.
    """
    mock_get.return_value.status_code = 404
    mock_get.return_value.json.return_value = {"message": "Branch not found"}

    with pytest.raises(Exception, match="Failed to fetch branch data: 404 - .*"):
        fetcher.fetch_branch_details("invaliduser", "invalid-repo", "nonexistent-branch")


@patch("subprocess.run")
def test_clone_repository(mock_run,fetcher):

    # Test cloning the default branch (shallow by default)
    fetcher.clone_repository("testuser","test-repo")
    mock_run.assert_called_with(["git", "clone", "https://github.com/testuser/test-repo.git", '.cache/repos/test-repo', "--depth", "1"], check=True)

    # Test cloning a specific branch (shallow by default)
    fetcher.clone_repository("testuser","test-repo", branch="develop")
    mock_run.assert_called_with(
        ["git", "clone", "https://github.com/testuser/test-repo.git", '.cache/repos/test-repo', "--depth", "1", "--branch", "develop"],
        check=True
    )

    # Test cloning without shallow (full clone)
    fetcher.clone_repository("testuser","test-repo", shallow=False)
    mock_run.assert_called_with(
        ["git", "clone", "https://github.com/testuser/test-repo.git", '.cache/repos/test-repo'],
        check=True
    )

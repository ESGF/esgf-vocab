import logging
import os
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import List, Optional

import requests
from pydantic import BaseModel, ValidationError

_LOGGER = logging.getLogger(__name__)


@contextmanager
def redirect_stdout_to_log(level=logging.INFO):
    """
    Redirect stdout to the global _LOGGER temporarily.
    """

    class StreamToLogger:
        def __init__(self, log_level):
            self.log_level = log_level

        def write(self, message):
            if message.strip():  # Avoid logging empty lines
                _LOGGER.debug(self.log_level, message.strip())

        def flush(self):
            pass  # No-op for compatibility

    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = StreamToLogger(level)
    sys.stderr = StreamToLogger(level)
    try:
        yield
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr


class GitHubRepository(BaseModel):
    id: int
    name: str
    full_name: str
    description: Optional[str]
    html_url: str
    stargazers_count: int
    forks_count: int
    language: Optional[str]
    created_at: str
    updated_at: str


class GitHubBranch(BaseModel):
    name: str
    commit: dict
    protected: bool


class RepoFetcher:
    """
    DataFetcher is responsible for fetching data from external sources such as GitHub.
    """

    def __init__(self, base_url: str = "https://api.github.com", local_path: str = ".cache/repos"):
        self.base_url = base_url
        self.repo_dir = local_path

    def fetch_repositories(self, user: str) -> List[GitHubRepository]:
        """
        Fetch repositories of a given GitHub user.
        :param user: GitHub username
        :return: List of GitHubRepository objects
        """
        url = f"{self.base_url}/users/{user}/repos"
        response = requests.get(url)

        if response.status_code != 200:
            raise Exception(f"Failed to fetch data: {response.status_code} - {response.text}")

        try:
            data = response.json()
            return [GitHubRepository(**repo) for repo in data]
        except ValidationError as e:
            raise Exception(f"Data validation error: {e}")

    def fetch_repository_details(self, owner: str, repo: str) -> GitHubRepository:
        """
        Fetch details of a specific repository.
        :param owner: Repository owner
        :param repo: Repository name
        :return: GitHubRepository object
        """
        url = f"{self.base_url}/repos/{owner}/{repo}"
        response = requests.get(url)

        if response.status_code != 200:
            raise Exception(f"Failed to fetch data: {response.status_code} - {response.text}")

        try:
            data = response.json()
            return GitHubRepository(**data)
        except ValidationError as e:
            raise Exception(f"Data validation error: {e}")

    def fetch_branch_details(self, owner: str, repo: str, branch: str) -> GitHubBranch:
        """
        Fetch details of a specific branch in a repository.
        :param owner: Repository owner
        :param repo: Repository name
        :param branch: Branch name
        :return: GitHubBranch object
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/branches/{branch}"
        response = requests.get(url)

        if response.status_code != 200:
            raise Exception(f"Failed to fetch branch data: {response.status_code} - {response.text}")

        try:
            return GitHubBranch(**response.json())
        except ValidationError as e:
            raise Exception(f"Data validation error: {e}")

    def list_directory(self, owner, repo, branch="main"):
        """
        List directories in the root of a GitHub repository.

        :param owner: GitHub username or organization name.
        :param repo: Repository name.
        :param branch: Branch name (default: 'main').
        :return: List of directories in the repository.
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/?ref={branch}"
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad responses
        contents = response.json()
        directories = [item["name"] for item in contents if item["type"] == "dir"]
        return directories

    def list_files(self, owner, repo, directory, branch="main"):
        """
        List files in a specific directory of a GitHub repository.

        :param owner: GitHub username or organization name.
        :param repo: Repository name.
        :param directory: Target directory path within the repo.
        :param branch: Branch name (default: 'main').
        :return: List of files in the specified directory.
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{directory}?ref={branch}"
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad responses
        contents = response.json()
        files = [item["name"] for item in contents if item["type"] == "file"]
        return files

    def clone_repository(self, owner: str, repo: str, branch: Optional[str] = None, local_path: str | None = None):
        """
        Clone a GitHub repository to a target directory.
        :param owner: Repository owner
        :param repo: Repository name
        :param target_dir: The directory where the repository should be cloned.
        :param branch: (Optional) The branch to clone. Clones the default branch if None.
        """
        repo_url = f"https://github.com/{owner}/{repo}.git"
        destination = local_path if local_path else f"{self.repo_dir}/{repo}"

        command = ["git", "clone", repo_url, destination]
        if branch:
            command.extend(["--branch", branch])
        with redirect_stdout_to_log():
            try:
                if not Path(destination).exists():
                    subprocess.run(command, check=True)
                    _LOGGER.debug(f"Repository cloned successfully into {destination}")
                else:
                    current_work_dir = os.getcwd()
                    os.chdir(f"{destination}")
                    command = ["git", "pull"]
                    subprocess.run(command, check=True)
                    os.chdir(current_work_dir)

            except Exception as e:
                raise Exception(f"Failed to clone repository: {e}")

    def get_github_version_with_api(self, owner: str, repo: str, branch: str = "main"):
        """Fetch the latest commit version (or any other versioning scheme) from GitHub."""
        details = self.fetch_branch_details(owner, repo, branch)
        return details.commit.get("sha")

    def get_github_version(self, owner: str, repo: str, branch: str = "main"):
        """Fetch the latest commit version (or any other versioning scheme) from GitHub. with command git fetch"""
        repo_url = f"https://github.com/{owner}/{repo}.git"
        command = ["git", "ls-remote", repo_url, f"{self.repo_dir}/{repo}"]
        if branch:
            command.extend([branch])

        # with redirect_stdout_to_log():
        output = None
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            # Parse the output to get the commit hash
            output = result.stdout.strip()
            _LOGGER.debug(f"Repository fetch successfully from {self.repo_dir}/{repo}")
        except Exception as e:
            _LOGGER.debug("error in with git fetch " + repr(e))
        if output is not None:
            commit_hash = output.split()[0]
            return commit_hash
        return None

        # return git_hash

    def get_local_repo_version(self, repo_path: str, branch: Optional[str] = "main"):
        """Check the version of the local repository by fetching the latest commit hash."""
        # repo_path = os.path.join(self.repo_dir, repo)
        if os.path.exists(repo_path):
            # print("EXIST")
            command = ["git", "-C", repo_path]
            if branch:
                command.extend(["switch", branch])
            # Ensure we are on the correct branch
            with redirect_stdout_to_log():
                subprocess.run(
                    command,
                    stdout=subprocess.PIPE,  # Capture stdout
                    stderr=subprocess.PIPE,  # Capture stderr
                    text=True,
                )  # Decode output as text
                # Get the latest commit hash (SHA) from the local repository
                commit_hash = subprocess.check_output(
                    ["git", "-C", repo_path, "rev-parse", "HEAD"], stderr=subprocess.PIPE, text=True
                ).strip()
            return commit_hash
        return None


if __name__ == "__main__":
    fetcher = RepoFetcher()

    # Fetch repositories for a user
    # repos = fetcher.fetch_repositories("ESPRI-Mod")
    # for repo in repos:
    #    print(repo)

    # Fetch a specific repository's details
    # repo_details = fetcher.fetch_repository_details("ESPRI-Mod", "mip-cmor-tables")
    # "print(repo_details)
    # branch_details = fetcher.fetch_branch_details("ESPRI-Mod", "mip-cmor-tables", "uni_proj_ld")
    # print(branch_details)

    fetcher.clone_repository("ESPRI-Mod", "mip-cmor-tables", branch="uni_proj_ld")

    # a =fetcher.get_github_version("ESPRI-Mod", "mip-cmor-tables", "uni_proj_ld")
    # print(a)
    # a = fetcher.get_local_repo_version("mip-cmor-tables","uni_proj_ld")
    # print(a)

    fetcher.clone_repository("ESPRI-Mod", "CMIP6Plus_CVs", branch="uni_proj_ld")

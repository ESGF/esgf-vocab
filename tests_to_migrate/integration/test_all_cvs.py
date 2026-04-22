"""
Integration tests for all CV repositories.

This test module is designed to test all CVs conjointly by running the
`esgvoc test run` command for each CV. These tests are NOT run during
regular pytest execution and must be explicitly invoked.

Usage:
    # Run all CV tests
    pytest -m cvtest

    # Run a specific CV test
    pytest -m cvtest -k cmip6

    # Run with verbose output
    pytest -m cvtest -v

    # Run in parallel (if pytest-xdist is installed)
    pytest -m cvtest -n auto
"""

import subprocess
from typing import List

import pytest


class TestAllCVs:
    """Integration tests for all CV repositories.

    These tests validate that each CV repository:
    1. Can be configured and synchronized
    2. Has valid repository structure
    3. Is accessible via the esgvoc API

    Tests use the esgvoc CLI test command which orchestrates:
    - Configuration setup
    - Repository cloning/syncing
    - Structure validation
    - API access validation
    """

    # List of all CVs to test
    CVS: List[str] = [
        "cmip6",
        "cmip6plus",
        "cmip7",
        "cordex-cmip6",
        "emd",
        "input4mip",
        "obs4ref",
    ]

    # Default branches for testing
    DEFAULT_BRANCH = "esgvoc_dev"
    DEFAULT_UNIVERSE_BRANCH = "esgvoc_dev"

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.cvtest
    @pytest.mark.parametrize("cv_name", CVS)
    def test_cv_via_cli(self, cv_name: str):
        """Test individual CV repository via CLI command.

        This test runs the complete CV test suite using the CLI:
            uv run esgvoc test run <cv_name> --branch <branch> --universe-branch <universe_branch>

        Args:
            cv_name: Name of the CV to test (e.g., "cmip6", "obs4ref")

        Raises:
            AssertionError: If the CV test fails (non-zero exit code)
        """
        # Build the command
        cmd = [
            "uv",
            "run",
            "esgvoc",
            "test",
            "run",
            cv_name,
            "--branch",
            self.DEFAULT_BRANCH,
            "--universe-branch",
            self.DEFAULT_UNIVERSE_BRANCH,
        ]

        # Run the command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout per CV
        )

        # Check result
        assert result.returncode == 0, (
            f"CV test failed for '{cv_name}'\n"
            f"Command: {' '.join(cmd)}\n"
            f"Exit code: {result.returncode}\n"
            f"\n--- STDOUT ---\n{result.stdout}\n"
            f"\n--- STDERR ---\n{result.stderr}"
        )

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

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.cvtest
    def test_all_cvs_sequentially(self):
        """Test all CVs sequentially in a single test.

        This alternative test runs all CV tests in sequence and collects
        results. Useful if you want a single pass/fail result rather than
        individual test results per CV.

        Note: This test is in addition to the parametrized test above.
        You can run either:
        - test_cv_via_cli: One test result per CV (recommended)
        - test_all_cvs_sequentially: Single test result for all CVs
        """
        failed_cvs = []
        results = {}

        for cv_name in self.CVS:
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

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,
            )

            results[cv_name] = {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

            if result.returncode != 0:
                failed_cvs.append(cv_name)

        # Generate detailed failure message if any CV failed
        if failed_cvs:
            failure_details = [f"\nFailed CVs: {', '.join(failed_cvs)}\n"]
            for cv_name in failed_cvs:
                failure_details.append(f"\n{'='*60}")
                failure_details.append(f"CV: {cv_name}")
                failure_details.append(f"{'='*60}")
                failure_details.append(f"Exit code: {results[cv_name]['returncode']}")
                failure_details.append(f"\n--- STDOUT ---\n{results[cv_name]['stdout']}")
                failure_details.append(f"\n--- STDERR ---\n{results[cv_name]['stderr']}")

            pytest.fail("\n".join(failure_details))

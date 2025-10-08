#!/usr/bin/env python3
"""
Example usage of the CV Testing Application

This script demonstrates how to use the CVTester class programmatically.
"""

from pathlib import Path
from rich.console import Console

from .cv_tester import CVTester

console = Console()


def example_test_default_project():
    """Example: Test a default project with its standard configuration"""
    console.print("[bold blue]Example 1: Testing default obs4mip project[/bold blue]")

    tester = CVTester()

    try:
        # Test with default obs4mip configuration
        success = tester.run_complete_test(
            project_name="obs4mip",
            repo_path=".",  # Assuming we're in the CV repository
        )

        if success:
            console.print("[green]✅ Default project test completed successfully[/green]")
        else:
            console.print("[red]❌ Default project test failed[/red]")

    finally:
        tester.cleanup()


def example_test_custom_branch():
    """Example: Test a project with custom branch"""
    console.print("[bold blue]Example 2: Testing obs4mip with custom branch[/bold blue]")

    tester = CVTester()

    try:
        # Test with custom branch
        success = tester.run_complete_test(
            project_name="obs4mip",
            branch="test-branch",  # Custom branch
            repo_path=".",
        )

        if success:
            console.print("[green]✅ Custom branch test completed successfully[/green]")
        else:
            console.print("[red]❌ Custom branch test failed[/red]")

    finally:
        tester.cleanup()


def example_test_universe_branch_override():
    """Example: Test with custom universe branch"""
    console.print("[bold blue]Example 2b: Testing input4mip with custom universe branch[/bold blue]")

    tester = CVTester()

    try:
        # Test with custom universe branch
        success = tester.run_complete_test(
            project_name="input4mip",
            branch="esgvoc",  # Project branch
            universe_branch="esgvoc_dev",  # Custom universe branch
            repo_path=".",
        )

        if success:
            console.print("[green]✅ Universe branch override test completed successfully[/green]")
        else:
            console.print("[red]❌ Universe branch override test failed[/red]")

    finally:
        tester.cleanup()


def example_test_custom_repo():
    """Example: Test with completely custom repository"""
    console.print("[bold blue]Example 3: Testing custom repository[/bold blue]")

    tester = CVTester()

    try:
        # Test with custom repo and branch
        success = tester.run_complete_test(
            project_name="obs4mip",  # Use obs4mip project structure
            repo_url="https://github.com/my-org/my-custom-cvs",
            branch="main",
            repo_path=".",
        )

        if success:
            console.print("[green]✅ Custom repository test completed successfully[/green]")
        else:
            console.print("[red]❌ Custom repository test failed[/red]")

    finally:
        tester.cleanup()


def example_test_custom_repo_and_universe():
    """Example: Test with custom repository and custom universe branch"""
    console.print("[bold blue]Example 3b: Testing custom repository with custom universe[/bold blue]")

    tester = CVTester()

    try:
        # Test with custom repo, project branch, and universe branch
        success = tester.run_complete_test(
            project_name="obs4mip",  # Use obs4mip project structure
            repo_url="https://github.com/my-org/my-custom-cvs",
            branch="main",  # Project branch
            universe_branch="development",  # Custom universe branch
            repo_path=".",
        )

        if success:
            console.print("[green]✅ Custom repository and universe test completed successfully[/green]")
        else:
            console.print("[red]❌ Custom repository and universe test failed[/red]")

    finally:
        tester.cleanup()


def example_individual_tests():
    """Example: Run individual test components"""
    console.print("[bold blue]Example 4: Running individual test components[/bold blue]")

    tester = CVTester()

    try:
        # Step 1: Configure for testing with universe branch override
        console.print("Step 1: Configuring...")
        if not tester.configure_for_testing(
            project_name="obs4mip",
            branch="main",  # Custom project branch
            universe_branch="esgvoc_dev"  # Custom universe branch
        ):
            console.print("[red]Configuration failed[/red]")
            return

        # Step 2: Sync CVs
        console.print("Step 2: Synchronizing CVs...")
        if not tester.synchronize_cvs():
            console.print("[red]Synchronization failed[/red]")
            return

        # Step 3: Test repository structure only
        console.print("Step 3: Testing repository structure...")
        if not tester.test_repository_structure("."):
            console.print("[red]Structure test failed[/red]")
            return

        # Step 4: Test API access only
        console.print("Step 4: Testing API access...")
        if not tester.test_esgvoc_api_access("obs4mip", "."):
            console.print("[red]API test failed[/red]")
            return

        console.print("[green]✅ All individual tests completed successfully[/green]")

    finally:
        tester.cleanup()


def example_list_available_projects():
    """Example: List all available projects for testing"""
    console.print("[bold blue]Example 5: Listing available projects[/bold blue]")

    tester = CVTester()
    projects = tester.get_available_projects()

    console.print(f"Available projects ({len(projects)}):")
    for project in projects:
        console.print(f"  • {project}")


def main():
    """Run all examples"""
    console.print("[bold green]CV Testing Application Examples[/bold green]\n")

    # List available projects
    example_list_available_projects()
    console.print()

    # Note: The following examples would need actual CV repositories to work
    console.print("[yellow]Note: The following examples require actual CV repositories[/yellow]\n")

    # Show example configurations (without actually running them)
    console.print("[bold blue]Example configurations:[/bold blue]")
    console.print("1. Test default project: CVTester().run_complete_test('obs4mip')")
    console.print("2. Test custom branch: CVTester().run_complete_test('obs4mip', branch='test-branch')")
    console.print("3. Test custom universe: CVTester().run_complete_test('input4mip', branch='esgvoc', universe_branch='esgvoc_dev')")
    console.print(
        "4. Test custom repo: CVTester().run_complete_test('obs4mip', repo_url='https://github.com/...', branch='main')"
    )
    console.print(
        "5. Test custom repo + universe: CVTester().run_complete_test('obs4mip', repo_url='https://github.com/...', branch='main', universe_branch='dev')"
    )
    console.print(
        "6. Individual tests: configure_for_testing(universe_branch='dev') -> synchronize_cvs() -> test_repository_structure() -> test_esgvoc_api_access()"
    )


if __name__ == "__main__":
    main()


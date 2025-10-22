"""
Test CV CLI commands

Provides commands for testing project CVs and Universe CVs integrated with esgvoc CLI.
"""

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from esgvoc.apps.test_cv.cv_tester import CVTester
from esgvoc.core.service.configuration.setting import ServiceSettings

app = typer.Typer()
console = Console()


@app.command()
def list_projects():
    """List all available CV projects that can be tested."""
    tester = CVTester()
    projects = tester.get_available_projects()

    table = Table(title="Available CV Projects for Testing")
    table.add_column("Project Name", style="cyan")
    table.add_column("Repository", style="green")
    table.add_column("Default Branch", style="yellow")
    table.add_column("Local Path", style="blue")

    default_configs = ServiceSettings._get_default_project_configs()
    for project_name in projects:
        config = default_configs[project_name]
        table.add_row(project_name, config["github_repo"], config["branch"], config["local_path"])

    console.print(table)
    console.print(f"\n[blue]Total: {len(projects)} projects available for testing[/blue]")


@app.command()
def configure(
    project: str = typer.Argument(..., help="Project name to configure for testing"),
    repo_url: Optional[str] = typer.Option(None, "--repo", "-r", help="Custom repository URL"),
    branch: Optional[str] = typer.Option(None, "--branch", "-b", help="Custom branch to test"),
    universe_branch: Optional[str] = typer.Option(None, "--universe-branch", "-u", help="Custom universe branch"),
    sync: bool = typer.Option(True, "--sync/--no-sync", help="Synchronize CVs after configuration"),
):
    """
    Configure esgvoc with a specific project for testing.

    Examples:
        esgvoc test configure obs4mip
        esgvoc test configure cmip6 --branch my-test-branch
        esgvoc test configure cmip6 --universe-branch my-universe-branch
        esgvoc test configure custom --repo https://github.com/me/my-cvs --branch main --universe-branch dev
    """
    tester = CVTester()

    try:
        # Configure
        if not tester.configure_for_testing(project, repo_url, branch, None, universe_branch):
            raise typer.Exit(1)

        # Optionally synchronize
        if sync:
            if not tester.synchronize_cvs():
                raise typer.Exit(1)

        console.print(f"[green]✅ Successfully configured project '{project}' for testing[/green]")
        if not sync:
            console.print("[yellow]Note: CVs not synchronized. Run 'esgvoc test sync' to download.[/yellow]")

    except Exception as e:
        console.print(f"[red]❌ Configuration failed: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def sync():
    """Synchronize/download CVs for the currently configured project."""
    tester = CVTester()

    try:
        if not tester.synchronize_cvs():
            raise typer.Exit(1)
        console.print("[green]✅ CVs synchronized successfully[/green]")
    except Exception as e:
        console.print(f"[red]❌ Synchronization failed: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def structure(
    path: str = typer.Argument(".", help="Path to CV repository to validate"),
):
    """
    Test CV repository structure and file format compliance.

    Validates:
    - Collection directory structure
    - JSONLD context files
    - Element JSON files
    - project_specs.json references

    Examples:
        esgvoc test structure .
        esgvoc test structure /path/to/cv/repo
    """
    tester = CVTester()

    try:
        if not tester.test_repository_structure(path):
            raise typer.Exit(1)
        console.print("[green]✅ Repository structure validation passed[/green]")
    except Exception as e:
        console.print(f"[red]❌ Structure validation failed: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def api(
    project: str = typer.Argument(..., help="Project name to test API access for"),
    path: str = typer.Argument(".", help="Path to CV repository"),
    debug_terms: bool = typer.Option(True, "--debug-terms/--no-debug-terms", help="Show detailed debugging info for missing terms"),
):
    """
    Test esgvoc API access for all repository collections and elements.

    Validates:
    - Project is accessible via esgvoc API
    - All repository collections are queryable
    - All repository elements are accessible
    - API functions work correctly

    Examples:
        esgvoc test api obs4mip .
        esgvoc test api cmip6 /path/to/cmip6/repo
    """
    tester = CVTester(debug_missing_terms=debug_terms)

    try:
        if not tester.test_esgvoc_api_access(project, path):
            raise typer.Exit(1)
        console.print("[green]✅ ESGVoc API access validation passed[/green]")
    except Exception as e:
        console.print(f"[red]❌ API validation failed: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def run(
    project: str = typer.Argument(..., help="Project name to test"),
    path: Optional[str] = typer.Argument(None, help="Path to CV repository (auto-detected if not provided)"),
    repo_url: Optional[str] = typer.Option(None, "--repo", "-r", help="Custom repository URL"),
    branch: Optional[str] = typer.Option(None, "--branch", "-b", help="Custom branch to test"),
    universe_branch: Optional[str] = typer.Option(None, "--universe-branch", "-u", help="Custom universe branch"),
    debug_terms: bool = typer.Option(True, "--debug-terms/--no-debug-terms", help="Show detailed debugging info for missing terms"),
):
    """
    Run complete CV test suite: configure, sync, structure, and API tests.

    This is the comprehensive test that runs all validation steps:
    1. Configure esgvoc with the specified project
    2. Synchronize/download CVs
    3. Validate repository structure
    4. Test esgvoc API access

    Examples:
        esgvoc test run obs4mip
        esgvoc test run cmip6 --branch my-test-branch
        esgvoc test run cmip6 --universe-branch my-universe-branch
        esgvoc test run cmip6 /path/to/custom/repo --branch my-test-branch --universe-branch dev
        esgvoc test run custom --repo https://github.com/me/cvs --branch main --universe-branch main
    """
    tester = CVTester(debug_missing_terms=debug_terms)

    try:
        success = tester.run_complete_test(project, repo_url, branch, path, None, universe_branch)
        if success:
            console.print(f"[bold green]🎉 All tests passed for project '{project}'![/bold green]")
        else:
            # The detailed failure information is already printed by cv_tester
            raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Test suite failed: {e}[/red]")
        raise typer.Exit(1)
    finally:
        tester.cleanup()


@app.command()
def env(
    command: str = typer.Argument(..., help="Environment mode command: 'configure' or 'test'"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project name (auto-detected if not provided)"),
    repo_url: Optional[str] = typer.Option(
        None, "--repo-url", help="Repository URL (from REPO_URL env var if not provided)"
    ),
    branch: Optional[str] = typer.Option(None, "--branch", help="Branch (from TEST_BRANCH env var if not provided)"),
    universe_branch: Optional[str] = typer.Option(None, "--universe-branch", help="Universe branch (from UNIVERSE_BRANCH env var if not provided)"),
    debug_terms: bool = typer.Option(True, "--debug-terms/--no-debug-terms", help="Show detailed debugging info for missing terms"),
):
    """
    Environment variable mode for CI/CD integration and automated testing.

    Reads configuration from environment variables:
    - REPO_URL: Repository URL to test
    - TEST_BRANCH: Branch to test
    - PROJECT_NAME: Project name (auto-detected if not set)
    - UNIVERSE_BRANCH: Universe branch to test (optional)
    - ESGVOC_LIBRARY_BRANCH: ESGVoc library branch (informational)

    Examples:
        # Set environment and run
        export REPO_URL=https://github.com/me/obs4MIPs_CVs
        export TEST_BRANCH=test-branch
        export UNIVERSE_BRANCH=my-universe-branch
        esgvoc test env configure
        esgvoc test env test

        # Or use options
        esgvoc test env configure --project obs4mip --repo-url https://github.com/me/repo --branch main --universe-branch dev
    """
    import os

    # Get config from environment or options
    final_repo_url = repo_url or os.environ.get("REPO_URL")
    final_branch = branch or os.environ.get("TEST_BRANCH")
    final_universe_branch = universe_branch or os.environ.get("UNIVERSE_BRANCH")
    final_project = project or os.environ.get("PROJECT_NAME")

    # Auto-detect project if not provided
    if not final_project:
        from esgvoc.apps.test_cv.cv_tester import detect_project_name

        final_project = detect_project_name()

    if command == "configure":
        if not final_repo_url or not final_branch:
            console.print("[red]❌ REPO_URL and TEST_BRANCH are required for env configure[/red]")
            console.print("Set environment variables or use --repo-url and --branch options")
            raise typer.Exit(1)

        # Use configure command
        configure(final_project, final_repo_url, final_branch, final_universe_branch, sync=True)

    elif command == "test":
        # Use run command
        run(final_project, None, final_repo_url, final_branch, final_universe_branch, debug_terms)

    else:
        console.print(f"[red]❌ Invalid env command '{command}'. Use 'configure' or 'test'[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()


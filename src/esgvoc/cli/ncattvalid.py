import sys
from pathlib import Path
from typing import Optional

import typer
from esgvoc.apps.ncattvalid.exceptions import InvalidNcdumpError
from esgvoc.apps.ncattvalid.validator import (
    AttributeResult,
    GAReport,
    GAValidator,
)
from rich.console import Console, Group
from rich.panel import Panel

app = typer.Typer(
    help="Validate NetCDF global attributes against ESGVOC controlled vocabularies."
)
console = Console()


def _make_panel(
    title: str,
    lines: list[str],
    style: str,
) -> Panel:
    return Panel(
        Group(*lines),
        title=title,
        border_style=style,
    )


def _display_attribute_result(results: list[AttributeResult]) -> None:
    """
    Render a single attribute validation result.
    """

    for result in results:
        if result.is_valid:
            console.print(
                f"✅ [yellow]{result.name}[/yellow]=[green]{result.value!r}[/green]"
            )
        else:
            console.print(
                f"❌ [yellow]{result.name}[/yellow]=[red]{result.value!r}[/red]"
            )
            console.print(f"   [white]{result.message}[/white]")


def _display_report(
    report: GAReport,
    verbose: bool = False,
) -> None:
    """
    Render a GA validation report.
    """

    if report.is_valid:
        console.rule(
            "[bold green]Validation successful[/bold green]",
            style="green"
        )
    else:
        console.rule(
            "[bold red]Validation failed[/bold red]",
            style="red"
        )

    if report.filename:
        console.print(f"[bold blue]File:[/bold blue] {report.filename}", highlight=False)

    console.print(f"[bold blue]Project:[/bold blue] {report.project_id}")

    valid_results = [result for result in report.results if result.is_valid]
    invalid_results = [result for result in report.results if not result.is_valid]

    if verbose:
        if valid_results:
            valid_lines = []

            for result in valid_results:
                valid_lines.append(
                    f"✅ [yellow]{result.name}[/yellow]=[green]{result.value!r}[/green]"
                )

            console.print(
                _make_panel(
                    "Valid attributes",
                    valid_lines,
                    "green",
                )
            )

    if invalid_results:
        invalid_lines = []

        for result in invalid_results:
            invalid_lines.append(
                f"❌ [yellow]{result.name}[/yellow]=[red]{result.value!r}[/red]"
            )

            invalid_lines.append(
                f"   [white]{result.message}[/white]"
            )

        console.print(
            _make_panel(
                "Invalid attributes",
                invalid_lines,
                "red",
            )
        )

    if report.missing:
        console.print(
            _make_panel(
                "Missing required attributes",
                [f"❓ [yellow]{attr}[/yellow]" for attr in report.missing],
                "yellow",
            )
        )

    if verbose:
        if report.extra:
            console.print(
                _make_panel(
                    "Extra attributes",
                    [f"➕ [yellow]{attr}[/yellow]" for attr in report.extra],
                    "blue",
                )
            )


@app.command()
def ncattvalid(
    project: str = typer.Argument(
        ...,
        help="Project identifier (e.g. cmip6, cmip7)",
    ),
    attribute_name: Optional[str] = typer.Argument(
        None,
        help="Attribute name",
    ),
    attribute_value: Optional[str] = typer.Argument(
        None,
        help="Attribute value",
    ),
    header_file: Optional[Path] = typer.Option(
        None,
        "--file",
        "-f",
        help="Text file containing ncdump -h output.",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Display valid attributes in addition to errors.",
    ),
):
    """
    Validate NetCDF global attributes against ESGVOC vocabularies.

    Examples:

        Validate one attribute:
            esgvoc ncattvalid cmip6 activity_id CMIP

        Validate ncdump header from stdin:
            ncdump -h file.nc | esgvoc ncattvalid cmip6

        Validate ncdump header from file:
            esgvoc ncattvalid cmip6 --file header.txt

        Verbose mode:
            esgvoc ncattvalid cmip6 --file header.txt -v
    """

    validator = GAValidator(project)

    # Single attribute validation
    if attribute_name is not None and attribute_value is not None:
        results = validator.validate_one(
            attribute_name,
            attribute_value,
        )

        _display_attribute_result(results)

        raise typer.Exit(code=0 if all(result.is_valid for result in results) else 1)

    # Invalid partial arguments
    if attribute_name is not None or attribute_value is not None:
        console.print(
            "[red]Error:[/red] expected either:"
        )
        console.print("  • ATTRIBUTE_NAME ATTRIBUTE_VALUE")
        console.print("  • --file HEADER_FILE")
        console.print("  • stdin via pipe")
        raise typer.Exit(code=1)

    # ncdump validation from file
    if header_file is not None:

        if not header_file.exists():
            console.print(
                f"[red]File not found:[/red] {header_file}"
            )
            raise typer.Exit(code=1)

        ncdump_output = header_file.read_text(encoding="utf-8")
    else:
        # ncdump validation from stdin
        ncdump_output = sys.stdin.read()

        if not ncdump_output.strip():
            console.print(
                "[red]No ncdump input received from stdin[/red]"
            )
            raise typer.Exit(code=1)

    try:
        report = validator.validate_ncdump(
            ncdump_output,
        )
    except InvalidNcdumpError as ncdump_error:
        console.print(f"[red]{ncdump_error}[/red]")
        raise typer.Exit(1) from ncdump_error

    _display_report(
        report,
        verbose,
    )

    raise typer.Exit(code=0 if report.is_valid else 1)

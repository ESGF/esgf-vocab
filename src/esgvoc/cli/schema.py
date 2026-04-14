import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from esgvoc.api.projects import get_all_projects
from esgvoc.apps.jsg.json_schema_generator import generate_json_schema, pretty_print_json_node

app = typer.Typer()
console = Console()

_LOGGER = logging.getLogger(__name__)


@app.command()
def schema(
    project_id: str = typer.Argument(..., help="The project id (e.g., cmip7, cmip6plus)"),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path. If not specified, outputs to stdout.",
    ),
    indent: int = typer.Option(
        2,
        "--indent",
        "-i",
        help="JSON indentation level.",
    ),
):
    """
    Generate a JSON schema for a project's catalog specification.

    This command generates a JSON schema based on the project's catalog_specs.yaml
    configuration. The schema can be used to validate STAC catalog entries.

    Examples:
        Generate schema and print to stdout:
            esgvoc schema cmip7

        Generate schema and save to file:
            esgvoc schema cmip7 -o cmip7_schema.json

        Generate schema with custom indentation:
            esgvoc schema cmip7 -o cmip7_schema.json --indent 4
    """
    known_projects = get_all_projects()

    if project_id not in known_projects:
        console.print(f"[red]Error: Unknown project '{project_id}'[/red]")
        console.print(f"[yellow]Available projects: {', '.join(known_projects.keys())}[/yellow]")
        raise typer.Exit(code=1)

    try:
        _LOGGER.info(f"Generating JSON schema for project '{project_id}'")
        schema_dict = generate_json_schema(project_id)

        import json

        json_str = json.dumps(schema_dict, indent=indent)

        if output:
            output.write_text(json_str)
            console.print(f"[green]Schema written to {output}[/green]")
        else:
            print(json_str)

    except Exception as e:
        console.print(f"[red]Error generating schema: {e}[/red]")
        _LOGGER.exception("Schema generation failed")
        raise typer.Exit(code=1)

import logging
import typing
from typing import List, Optional, get_args, get_origin

import typer
from pydantic import BaseModel
from rich.console import Console
from rich.table import Table

from esgvoc.api.projects import (
    get_all_collections_in_project,
    get_all_projects,
    get_model_from_collection,
)
from esgvoc.api.universe import get_model_from_data_descriptor

app = typer.Typer()
console = Console()

_LOGGER = logging.getLogger(__name__)


def _is_union_type(cls) -> bool:
    """Check if cls is an Annotated union (from create_union) rather than a concrete class."""
    return get_origin(cls) is typing.Annotated


def _get_union_variants(cls) -> list[type[BaseModel]]:
    """Extract concrete model classes from an Annotated union type."""
    variants = []
    for arg in get_args(cls):
        origin = get_origin(arg)
        if origin is typing.Union:
            for union_arg in get_args(arg):
                inner_args = get_args(union_arg)
                for inner in inner_args:
                    if isinstance(inner, type) and issubclass(inner, BaseModel):
                        variants.append(inner)
    return variants


def _display_concrete_model(model_cls: type[BaseModel], name: str) -> None:
    """Display a concrete pydantic model's fields and docstring."""
    table = Table(title=f"{name} → {model_cls.__name__}")
    table.add_column("Field", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Required", style="yellow")
    for field_name, field_info in model_cls.model_fields.items():
        required = "yes" if field_info.is_required() else "no"
        annotation = field_info.annotation
        type_str = getattr(annotation, "__name__", str(annotation))
        table.add_row(field_name, type_str, required)
    console.print(table)
    if model_cls.__doc__:
        console.print(f"\n[dim]{model_cls.__doc__.strip()}[/dim]\n")


def _display_model(model_cls, name: str) -> None:
    """Display model info, handling both concrete classes and union types."""
    if _is_union_type(model_cls):
        variants = _get_union_variants(model_cls)
        if variants:
            variant_names = [v.__name__ for v in variants]
            console.print(f"\n[bold]{name}[/bold] is a union of: {', '.join(variant_names)}\n")
            for variant in variants:
                _display_concrete_model(variant, name)
        else:
            console.print(f"[yellow]{name} is a union type but no variants could be extracted[/yellow]")
    else:
        _display_concrete_model(model_cls, name)


@app.command()
def describe(
    args: List[str] = typer.Argument(..., help="[project] <collection|data_descriptor>"),
    fields: Optional[bool] = typer.Option(False, "--fields", "-f", help="Show model fields"),
):
    """
    Describe the pydantic model for a collection or data descriptor.

    Usage:\n
        `describe <data_descriptor>`           universe data descriptor\n
        `describe universe <data_descriptor>`   same as above\n
        `describe <project> <collection>`       project collection (concrete model)\n
        `describe <project>`                    list all models for a project\n

    Examples:\n
        `esgvoc describe source`                → Source (union)\n
        `esgvoc describe cmip7 experiment`      → ExperimentCMIP7\n
        `esgvoc describe cmip7`                 → all collection models\n
    """
    known_projects = get_all_projects()

    if len(args) == 1:
        target = args[0]
        if target in known_projects:
            # List all models for this project
            _describe_all_collections(target)
        else:
            # Universe data descriptor
            _describe_universe(target)
    elif len(args) == 2:
        first, second = args
        if first == "" or first == "universe":
            _describe_universe(second)
        elif first in known_projects:
            _describe_collection(first, second)
        else:
            console.print(f"[red]Unknown project '{first}'[/red]")
            console.print(f"[yellow]Available projects: {', '.join(known_projects.keys())}[/yellow]")
            raise typer.Exit(code=1)
    else:
        console.print("[red]Expected 1 or 2 arguments: [project] <collection|data_descriptor>[/red]")
        raise typer.Exit(code=1)


def _describe_universe(data_descriptor_id: str) -> None:
    model_cls = get_model_from_data_descriptor(data_descriptor_id)
    if model_cls is None:
        console.print(f"[red]Unknown data descriptor '{data_descriptor_id}'[/red]")
        raise typer.Exit(code=1)
    _display_model(model_cls, f"universe:{data_descriptor_id}")


def _describe_collection(project_id: str, collection_id: str) -> None:
    model_cls = get_model_from_collection(project_id, collection_id)
    if model_cls is None:
        console.print(f"[red]Could not resolve model for '{project_id}:{collection_id}'[/red]")
        raise typer.Exit(code=1)
    _display_model(model_cls, f"{project_id}:{collection_id}")


def _describe_all_collections(project_id: str) -> None:
    collections = get_all_collections_in_project(project_id)
    if not collections:
        console.print(f"[red]No collections found for project '{project_id}'[/red]")
        raise typer.Exit(code=1)

    table = Table(title=f"Models for project '{project_id}'")
    table.add_column("Collection", style="cyan")
    table.add_column("Model", style="green")

    for coll in collections:
        model_cls = get_model_from_collection(project_id, coll)
        model_name = model_cls.__name__ if model_cls else "[dim]unresolved[/dim]"
        table.add_row(coll, model_name)

    console.print(table)

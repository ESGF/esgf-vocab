import logging
import types
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


def _is_nullable(annotation) -> bool:
    """Check if a type annotation accepts None (e.g. str | None, Optional[str])."""
    origin = get_origin(annotation)
    if origin is types.UnionType or origin is typing.Union:
        return type(None) in get_args(annotation)
    # Handle ForwardRef like Union[str, 'Experiment', None]
    if isinstance(annotation, typing.ForwardRef):
        arg = annotation.__forward_arg__
        if arg.startswith("Union[") and "None" in arg:
            return True
    return False


def _format_type(annotation) -> str:
    """Format a type annotation into a readable string."""
    # Handle ForwardRef - extract the inner type string and clean it up
    if isinstance(annotation, typing.ForwardRef):
        arg = annotation.__forward_arg__
        # Parse Union[X, Y, None] forward refs into "X | Y"
        if arg.startswith("Union[") and arg.endswith("]"):
            inner = arg[6:-1]
            parts = [p.strip().strip("'\"") for p in inner.split(",")]
            parts = [p for p in parts if p != "None"]
            return " | ".join(parts)
        return arg
    origin = get_origin(annotation)
    # Handle Annotated types (e.g. from create_union)
    if origin is typing.Annotated:
        inner_args = get_args(annotation)
        if inner_args:
            inner = inner_args[0]
            inner_origin = get_origin(inner)
            # Detect create_union pattern: Annotated[X | Y, Discriminator(...)]
            if inner_origin is types.UnionType or inner_origin is typing.Union:
                variants = _get_union_variants(annotation)
                if variants:
                    return " | ".join(v.__name__ for v in variants)
            return _format_type(inner)
        return str(annotation)
    # Handle X | None (UnionType or typing.Union)
    if origin is types.UnionType or origin is typing.Union:
        args = [a for a in get_args(annotation) if a is not type(None)]
        if len(args) == 1:
            return _format_type(args[0])
        return " | ".join(_format_type(a) for a in args)
    # Handle generic types like list[str], dict[str, int]
    if origin is not None:
        args = get_args(annotation)
        origin_name = getattr(origin, "__name__", str(origin))
        if args:
            args_str = ", ".join(_format_type(a) for a in args)
            return f"{origin_name}[{args_str}]"
        return origin_name
    return getattr(annotation, "__name__", str(annotation))


def _display_concrete_model(model_cls: type[BaseModel], name: str) -> None:
    """Display a concrete pydantic model's fields and docstring."""
    table = Table(title=f"{name} → {model_cls.__name__}")
    table.add_column("Field", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Required", style="yellow")
    for field_name, field_info in model_cls.model_fields.items():
        annotation = field_info.annotation
        nullable = _is_nullable(annotation)
        required = "yes" if field_info.is_required() and not nullable else "no"
        type_str = _format_type(annotation)
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

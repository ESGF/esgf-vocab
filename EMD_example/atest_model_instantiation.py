#!/usr/bin/env python3
"""
Test script to read the EMD JSON example and instantiate the improved Pydantic models.
Uses rich for beautiful console output.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.tree import Tree
    from rich.table import Table
    from rich.text import Text
    from rich import print as rprint
except ImportError:
    print("Error: rich library not found. Install with: pip install rich")
    sys.exit(1)

# Add the src directory to Python path to import our models
src_path = Path(__file__).parent.parent / "src"
if src_path.exists():
    sys.path.insert(0, str(src_path))

try:
    from esgvoc.api.data_descriptors.model_new import Model
    from esgvoc.api.data_descriptors.model_component_new import EMDModelComponent
    from esgvoc.api.data_descriptors.reference_new import Reference
    from esgvoc.api.data_descriptors.native_horizontal_grid_new import NativeHorizontalGrid
    from esgvoc.api.data_descriptors.native_vertical_grid_new import NativeVerticalGrid
except ImportError as e:
    print(f"Error importing Pydantic models: {e}")
    print("Make sure the models are in the correct path and have no syntax errors.")
    sys.exit(1)


def load_json_data(file_path: Path) -> Dict[str, Any]:
    """Load JSON data from file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: JSON file not found at {file_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {file_path}: {e}")
        sys.exit(1)


def create_reference_from_dict(ref_data: Dict[str, Any], index: int = 0) -> Reference:
    """Create a Reference object from dictionary data."""
    return Reference(
        id=f"ref_{index}",  # Required by DataDescriptor
        type="reference_new",  # Required by DataDescriptor
        drs_name=f"reference_{index}",  # Required by PlainTermDataDescriptor
        citation=ref_data["citation"],
        doi=ref_data["doi"],
    )


def create_horizontal_grid_from_dict(grid_data: Dict[str, Any], grid_id: str = "hgrid") -> NativeHorizontalGrid:
    """Create a NativeHorizontalGrid object from dictionary data."""
    return NativeHorizontalGrid(
        id=grid_id,  # Required by DataDescriptor
        type="native_horizontal_grid_new",  # Required by DataDescriptor
        drs_name=grid_id,  # Required by PlainTermDataDescriptor
        grid=grid_data["grid"],
        description=grid_data.get("description"),
        grid_mapping=grid_data["grid_mapping"],
        region=grid_data["region"],
        temporal_refinement=grid_data["temporal_refinement"],
        arrangement=grid_data["arrangement"],
        resolution_x=grid_data.get("resolution_x"),
        resolution_y=grid_data.get("resolution_y"),
        horizontal_units=grid_data.get("horizontal_units"),
        n_cells=grid_data["n_cells"],
        n_sides=grid_data.get("n_sides"),
        n_vertices=grid_data.get("n_vertices"),
        truncation_method=grid_data.get("truncation_method"),
        truncation_number=grid_data.get("truncation_number"),
        resolution_range_km=grid_data["resolution_range_km"],
        mean_resolution_km=grid_data["mean_resolution_km"],
        nominal_resolution=grid_data["nominal_resolution"],
    )


def create_vertical_grid_from_dict(grid_data: Dict[str, Any], grid_id: str = "vgrid") -> NativeVerticalGrid:
    """Create a NativeVerticalGrid object from dictionary data."""
    return NativeVerticalGrid(
        id=grid_id,  # Required by DataDescriptor
        type="native_vertical_grid_new",  # Required by DataDescriptor
        drs_name=grid_id,  # Required by PlainTermDataDescriptor
        coordinate=grid_data["coordinate"],
        description=grid_data.get("description"),
        n_z=grid_data.get("n_z"),
        n_z_range=grid_data.get("n_z_range"),
        bottom_layer_thickness=grid_data.get("bottom_layer_thickness"),
        top_layer_thickness=grid_data.get("top_layer_thickness"),
        top_of_model=grid_data.get("top_of_model"),
        vertical_units=grid_data.get("vertical_units"),
    )


def create_model_component_from_dict(comp_data: Dict[str, Any], comp_index: int = 0) -> EMDModelComponent:
    """Create an EMDModelComponent object from dictionary data."""
    comp_id = f"comp_{comp_index}_{comp_data['component']}"

    # Create references
    references = [create_reference_from_dict(
        ref, i) for i, ref in enumerate(comp_data["references"])]

    # Create grids
    horizontal_grid = create_horizontal_grid_from_dict(
        comp_data["native_horizontal_grid"], f"{comp_id}_hgrid")
    vertical_grid = create_vertical_grid_from_dict(
        comp_data["native_vertical_grid"], f"{comp_id}_vgrid")

    return EMDModelComponent(
        id=comp_id,  # Required by DataDescriptor
        type="model_component_new",  # Required by DataDescriptor
        drs_name=comp_id,  # Required by PlainTermDataDescriptor
        component=comp_data["component"],
        name=comp_data["name"],
        family=comp_data["family"],
        description=comp_data["description"],
        references=references,
        code_base=comp_data["code_base"],
        embedded_in=comp_data.get("embedded_in"),
        coupled_with=comp_data.get("coupled_with"),
        native_horizontal_grid=horizontal_grid,
        native_vertical_grid=vertical_grid,
    )


def create_model_from_json(data: Dict[str, Any]) -> Model:
    """Create a complete Model object from JSON data."""
    # Create references
    references = [create_reference_from_dict(
        ref, i) for i, ref in enumerate(data["references"])]

    # Create model components
    model_components = []
    if "model_components" in data:
        model_components = [
            create_model_component_from_dict(comp, i) for i, comp in enumerate(data["model_components"])
        ]

    # Create the main model (without model_components for now since it's not in the Model schema)
    model = Model(
        id="main_model",  # Required by DataDescriptor
        type="model_new",  # Required by DataDescriptor
        # Required by PlainTermDataDescriptor
        drs_name=data["name"].lower().replace("-", "_"),
        name=data["name"],
        family=data["family"],
        dynamic_components=data["dynamic_components"],
        prescribed_components=data["prescribed_components"],
        omitted_components=data["omitted_components"],
        description=data["description"],
        calendar=data["calendar"],
        release_year=data["release_year"],
        references=references,
    )

    return model, model_components


def print_model_summary(console: Console, model: Model, components: list):
    """Print a beautiful summary of the model using rich."""

    # Main model panel
    console.print()
    console.print(
        Panel.fit(
            f"[bold blue]{model.name}[/bold blue]\n"
            f"[dim]Family: {model.family}[/dim]\n"
            f"[dim]Release Year: {model.release_year}[/dim]",
            title="[bold]EMD Top-Level Model[/bold]",
            border_style="blue",
        )
    )

    # Components summary
    comp_table = Table(title="Model Components Overview")
    comp_table.add_column("Type", style="cyan")
    comp_table.add_column("Status", style="magenta")
    comp_table.add_column("Count", justify="right", style="green")

    comp_table.add_row("Dynamic", "✅ Simulated",
                       str(len(model.dynamic_components)))
    comp_table.add_row("Prescribed", "📋 Fixed", str(
        len(model.prescribed_components)))
    comp_table.add_row("Omitted", "❌ Excluded",
                       str(len(model.omitted_components)))

    console.print()
    console.print(comp_table)

    # Component details tree
    if components:
        console.print()
        tree = Tree("[bold]Model Component Details[/bold]")

        for comp in components:
            comp_node = tree.add(
                f"[bold cyan]{comp.component}[/bold cyan]: {comp.name}")
            comp_node.add(f"[dim]Family:[/dim] {comp.family}")
            comp_node.add(f"[dim]Code Base:[/dim] {comp.code_base}")

            if comp.embedded_in:
                comp_node.add(
                    f"[yellow]Embedded in:[/yellow] {comp.embedded_in}")
            elif comp.coupled_with:
                comp_node.add(
                    f"[green]Coupled with:[/green] {', '.join(comp.coupled_with)}")

            # Grid info
            grid_node = comp_node.add("[bold]Grids[/bold]")
            grid_node.add(
                f"[dim]Horizontal:[/dim] {comp.native_horizontal_grid.grid} ({
                    comp.native_horizontal_grid.nominal_resolution
                })"
            )
            grid_node.add(
                f"[dim]Vertical:[/dim] {comp.native_vertical_grid.coordinate}")

            # References
            ref_node = comp_node.add(
                f"[bold]References[/bold] ({len(comp.references)})")
            for ref in comp.references:
                ref_node.add(f"[dim]{ref.doi}[/dim]")

        console.print(tree)

    # Model description
    console.print()
    console.print(Panel(model.description,
                  title="[bold]Model Description[/bold]", border_style="green"))

    # References
    console.print()
    ref_table = Table(title="Model References")
    ref_table.add_column("Citation", style="cyan", width=60)
    ref_table.add_column("DOI", style="blue")

    for ref in model.references:
        ref_table.add_row(
            ref.citation[:100] + "..." if len(ref.citation) > 100 else ref.citation, ref.doi)

    console.print(ref_table)


def print_validation_success(console: Console):
    """Print validation success message."""
    console.print()
    console.print(
        Panel.fit(
            "[bold green]✅ Validation Successful![/bold green]\n"
            "[dim]All Pydantic models instantiated correctly with proper types and validation.[/dim]",
            title="[bold]Validation Status[/bold]",
            border_style="green",
        )
    )


def main():
    """Main function to test model instantiation."""
    console = Console()

    console.print(
        Panel.fit(
            "[bold]EMD Pydantic Model Instantiation Test[/bold]\n"
            "[dim]Reading JSON and creating strongly-typed model objects[/dim]",
            border_style="blue",
        )
    )

    # Load JSON data
    json_file = Path(__file__).parent / "complete_top_model_example.json"
    console.print(f"\n[dim]Loading JSON from:[/dim] {json_file}")

    data = load_json_data(json_file)

    # Create model objects
    console.print("[dim]Instantiating Pydantic models...[/dim]")

    try:
        model, components = create_model_from_json(data)
        print_validation_success(console)
        print_model_summary(console, model, components)

        # Print technical details
        console.print()
        console.print(
            Panel.fit(
                f"[bold]Technical Details[/bold]\n"
                f"[dim]Model Type:[/dim] {type(model).__name__}\n"
                f"[dim]Components:[/dim] {len(components)} instances of {
                    type(components[0]).__name__ if components else 'None'
                }\n"
                f"[dim]References:[/dim] {len(model.references)} instances of {
                    type(
                        model.references[0]).__name__ if model.references else 'None'
                }\n"
                f"[dim]Total Grid Objects:[/dim] {
                    len(components) * 2} (horizontal + vertical per component)",
                title="[bold]Object Instantiation Summary[/bold]",
                border_style="yellow",
            )
        )

    except Exception as e:
        console.print()
        console.print(
            Panel.fit(
                f"[bold red]❌ Validation Failed![/bold red]\n[dim]Error:[/dim] {
                    str(e)}",
                title="[bold]Validation Status[/bold]",
                border_style="red",
            )
        )
        console.print(f"\n[dim]Error Type:[/dim] {type(e).__name__}")
        raise


if __name__ == "__main__":
    main()

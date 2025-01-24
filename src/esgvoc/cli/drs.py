from esgvoc.apps.drs.generator import DrsGenerator
from esgvoc.apps.drs.report import DrsValidationReport, DrsGeneratorReport
from esgvoc.apps.drs.validator import DrsValidator
import sys
import typer
from rich.console import Console
from rich.table import Table
from typing import List, Optional
import esgvoc.api as ev
import shlex

app = typer.Typer()
console = Console()



# Predefined list of projects and DRS types
# projects = ["cmip5", "cmip6","cmip6plus", "cmip7"]
projects = ev.get_all_projects()
drs_types = ["filename", "directory", "dataset"]

def display(table):
    """
    Function to display a rich table in the console.

    :param table: The table to be displayed
    """
    console = Console(record=True, width=200)
    console.print(table)


@app.command()
def drsvalid(
    drs_entries: Optional[List[str]] = typer.Argument(None, help="List of DRS validation inputs in the form <project> <drstype> <string>"),
    file: Optional[typer.FileText] = typer.Option(None, "--file", "-f", help="File containing DRS validation inputs, one per line in the form <project> <drstype> <string>"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Provide detailed validation results"),
    output: Optional[str] = typer.Option(None, "-o", "--output", help="File to save the DRS entries validation"),

) -> List[DrsValidationReport]:
    """
    Validates DRS strings for a specific project and type.

    Args:
        drs_entries (Optional[List[str]]): A list of DRS validation inputs in the form <project> <drstype> <string>.
        file (Optional[typer.FileText]): File containing DRS validation inputs, one per line.
        verbose (bool): If true, prints detailed validation results.

    Usage Examples:
        # Validate multiple filenames for CMIP6
        drsvalid cmip6 filename file1.nc file2.nc file3.nc

        # Validate using a file
        drsvalid --file drs_input.txt
    """
    current_project = None
    current_drs_type = None
    reports = []

    entries = drs_entries or []

    if not sys.stdin.isatty():  # Check if input is being piped via stdin
        entries.extend(el for line in sys.stdin for el in shlex.split(line))


    if file:
        entries.extend(el for line in file for el in line.strip().split(" "))

    i = 0
    while i < len(entries):
        if entries[i] in [""," "]:
            i+=1
            continue

        if entries[i] in projects:
            current_project = entries[i]
            i += 1
            continue
        if entries[i] in drs_types:
            current_drs_type = entries[i]
            i += 1
            continue

        if current_project is None:
            raise typer.BadParameter(f"Invalid project: {entries[i]}")

        if current_drs_type is None:
            raise typer.BadParameter(f"Invalid drs_type: {entries[i]}")

        string = entries[i]
        i += 1
        validator = DrsValidator(current_project)
        report = None
        match current_drs_type:
            case "filename":
                report = validator.validate_file_name(string)
            case "directory":
                report = validator.validate_directory(string)
            case "dataset":
                report = validator.validate_dataset_id(string)
            case _:
                raise RuntimeError("drstype is not known")
        reports.append(report)

    if verbose:
        table = Table(title="Validation result")
        table.add_column("entry", style="cyan")
        table.add_column("warnings", style="magenta")
        table.add_column("errors", style="red")
        table.add_column("valid")

        for report in reports:
            entry = str(report.project_id) + " " + report.type + " " + str(report.expression)
            warnings = "\n".join(["⚠️ " + str(warning) for warning in report.warnings])
            errors = "\n".join(["⚠️ " + str(error) for error in report.errors])
            valid = "✅ Valid" if report else "❌ Invalid"

            table.add_row(entry, warnings, errors, valid)

        console.print(table)
    elif output:
        with open(output, "w") as f:
            for report in reports:
                f.write(str(report.message) + "\n")
        console.print(f"DRS validation entries saved to [green]{output}[/green]")


    else:
        for report in reports:
            console.print(report.message)

    return reports


@app.command()
def drsgen(
    drs_entries: Optional[List[str]] = typer.Argument(None, help="List of inputs to generate DRS in the form <project> <drstype> <bag_of_words>"),
    file: Optional[typer.FileText] = typer.Option(None, "--file", "-f", help="File containing DRS generation inputs, one per line in the form <project> <drstype> <bag_of_words>"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Provide detailed generation results"),
    output: Optional[str] = typer.Option(None, "-o", "--output", help="File to save the generated DRS entries"),
) -> List[DrsGeneratorReport]:
    """
    Generates DRS strings for a specific project and type based on input bag of words.

    Args:
        drs_entries (Optional[List[str]]): A list of inputs in the form <project> <drstype> <bag_of_words>.
        file (Optional[typer.FileText]): File containing DRS generation inputs, one per line.
        verbose (bool): If true, prints detailed generation results.
        output (Optional[str]): File path to save the generated DRS entries.

    Usage Examples:
        # Generate multiple filenames for CMIP6
        drsgen cmip6 filename var1=tas var2=pr

        # Generate using a file
        drsgen --file drs_input.txt
    """
    current_project = None
    current_drs_type = None
    generated_reports = []

    entries = drs_entries or []

    if not sys.stdin.isatty():  # Check if input is being piped via stdin
        entries.extend(el for line in sys.stdin for el in shlex.split(line))

    if file:
        entries.extend(el for line in file for el in shlex.split(line))

    i = 0
    while i < len(entries):
        if entries[i] in [""," "]:
            i+=1
            continue
        if entries[i] in projects:
            current_project = entries[i]
            i += 1
            continue
        if entries[i] in drs_types:
            current_drs_type = entries[i]
            i += 1
            continue

        if current_project is None:
            raise typer.BadParameter(f"Invalid project: {entries[i]}")

        if current_drs_type is None:
            raise typer.BadParameter(f"Invalid drs_type: {entries[i]}")

        bag_of_words = entries[i]
        bag_of_words = set(entries[i].split(" "))
        i += 1

        generator = DrsGenerator(current_project)
        report = None
        match current_drs_type:
            case "filename":
                report = generator.generate_file_name_from_bag_of_tokens(bag_of_words)
            case "directory":
                report = generator.generate_directory_from_bag_of_tokens(bag_of_words)
            case "dataset":
                report = generator.generate_dataset_id_from_bag_of_tokens(bag_of_words)
            case _:
                raise RuntimeError("drstype is not known")
        generated_reports.append(report)

    if verbose:
        table = Table(title="Generation result")
        table.add_column("deduced mapping entry", style="cyan")
        table.add_column("warnings", style="magenta")
        table.add_column("errors", style="red")
        table.add_column("result", style="green", width=10)
        for report in generated_reports:
            entry = str(report.given_mapping_or_bag_of_words)
            warnings = "\n".join(["⚠️ " + str(warning) for warning in report.warnings])
            errors = "\n".join([f"🔍 {error}" for error in report.errors])
            result = report.computed_drs_expression
            table.add_row(entry, warnings, errors, result)
            table.add_row("----", "----", "----", "----")
            if table.columns[3].width is not None and len(result) > table.columns[3].width:
                table.columns[3].width = len(result)+1
        console.print(table)

    elif output:
        with open(output, "w") as f:
            for report in generated_reports:
                f.write(str(report.message) + "\n")
        console.print(f"Generated entries saved to [green]{output}[/green]")

    else:
        for report in generated_reports:
            console.print(report.message)

    return generated_reports
if __name__ == "__main__":
    app()


from typing import List
from esgvoc.api.projects import (
    valid_term, 
    valid_term_in_collection, 
    valid_term_in_project, 
    valid_term_in_all_projects
)
from requests import logging
from rich.table import Table
import typer
import re
from rich.console import Console

app = typer.Typer()
console = Console()

_LOGGER = logging.getLogger(__name__)

@app.command()
def valid(
    strings_targets: List[str] = typer.Argument(
        ..., 
        help=(
            "Pairs of strings to validate against a key in the form '<StringToValidate> <Project:Collection:Term>'.\n"
            "Multiple pairs can be provided. The key '<Project:Collection:Term>' consists of three parts:\n"
            "- 'Project' (optional)\n"
            "- 'Collection' (optional)\n"
            "- 'Term' (optional)\n"
            "Only the ':' separators are mandatory. For example:\n"
            "  - 'my_string ::'\n"
            "  - 'my_string Project::'\n"
            "  - 'my_string Project:Collection:'\n"
            "  - 'my_string Project:Collection:Term'\n"
            "The function validates based on the provided parts."
        )
    ),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Provide detailed validation results")
):
    """
    Validates one or more strings against specified Project:Collection:Term configurations.

    Depending on the provided key structure, the function performs different validation operations:
    - If all are None (e.g., "::"), validates the term across all projects (`valid_term_in_all_projects`).
    - If Term is None (e.g., "Project:Collection:"), validates the term in the specified collection (`valid_term_in_collection`).
    - If Term and Collection are None (e.g., "Project::"), validates the term in the specified project (`valid_term_in_project`).
    - If all are specified (e.g., "Project:Collection:Term"), validates the term exactly (`valid_term`).

    Parameters:
        strings_targets (List[str]): A list of validation pairs, where each pair consists of:
            - A string to validate.
            - A key in the form '<Project:Collection:Term>'.
    Usage :
        Valid one: 
        esgvocab valid IPSL cmip6plus:institution_id:ipsl
        esgvocab valid IPSL cmip6plus:institution_id:
        esgvocab valid IPSL cmip6plus::
        esgvocab valid IPSL ::
        
        Unvalid one:
        esgvocab valid IPSL_invalid cmip6plus:institution_id:ipsl
        esgvocab valid IPSL cmip6plus:institution_id:isl <= term cant be found
        esgvocab valid IPSL cmip6plus:institutin_id:ispl <= collection cant be found
        esgvocab valid IPSL cmip6pls:institution_id:ispl <= project cant be found

        Multiple validation for all known projects: 
        esgvocab valid IPSL :: IPS :: 
            result will be [True, False]
        
        esgvocab valid --verbose IPS :: IPSL :: 
            result will be 
            ┏━━━━━━━━┳━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
            ┃ String ┃ Key ┃ Result     ┃ Errors                      ┃
            ┡━━━━━━━━╇━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
            │ IPS    │ ::  │ ❌ Invalid │ did not found matching term │
            │ IPSL   │ ::  │ ✅ Valid   │ None                        │
            └────────┴─────┴────────────┴─────────────────────────────┘
    Returns:
        List[bool]: Validation results for each pair in the input.
    """
    results = []
    detailed_results = []

    # Combine string and target into pairs
    pairs = [strings_targets[i] + " " + strings_targets[i + 1] for i in range(0, len(strings_targets), 2)]

    # Validate each string against each target
    for validation in pairs:
        match = re.match(r"(.+)\s+([^:]*):([^:]*):([^:]*)", validation)
        if not match:
            console.print(f"[red]Invalid input format: {validation}[/red]")
            results.append(False)
            detailed_results.append({"validation": validation, "errors": ["Invalid input format"]})
            continue

        string_to_validate, project, collection, term = match.groups()
        exception_message= None
        try:
            # Perform the appropriate validation
            if project and collection and term:
                validation_result = valid_term(string_to_validate, project, collection, term)
            elif project and collection:
                validation_result = valid_term_in_collection(string_to_validate, project, collection)
            elif project:
                validation_result = valid_term_in_project(string_to_validate, project)
            else:
                validation_result = valid_term_in_all_projects(string_to_validate)

        except Exception as e:
            validation_result=False
            exception_message = repr(e)
        
        # Handle validation result

        if validation_result:
            results.append(True)
            detailed_results.append({"validation": validation, "errors": []})
        else:
            # Parse and collect errors for verbose mode
            if validation_result == []:
                detailed_results.append({"validation":validation, "errors":["did not found matching term"]})
            results.append(False)
            if project and collection and term and exception_message is None:
                errors = [str(error) for error in validation_result.errors]
                detailed_results.append({"validation": validation, "errors": errors})
            if exception_message is not None:
                detailed_results.append({"validation": validation, "errors": [exception_message]})


    # Output results
    if verbose:
        table = Table(title="Validation Results")
        table.add_column("String", style="cyan")
        table.add_column("Key", style="magenta")
        table.add_column("Result", style="green" if all(results) else "red")
        table.add_column("Errors", style="red")

        for detail in detailed_results:
            validation = detail["validation"]
            validation_parts = validation.split()
            string = validation_parts[0]
            key = validation_parts[1] if len(validation_parts) > 1 else "::"
            result = "✅ Valid" if detail["errors"] == [] else "❌ Invalid"
            print(detail)
            errors = "\n".join(detail["errors"]) if detail["errors"] else "None"
            table.add_row(string, key, result, errors)

        console.print(table)
    else:
        console.print(results)

    return results

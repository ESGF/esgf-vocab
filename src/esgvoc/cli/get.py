import logging
import re
from typing import Any, List, Optional

import typer
from pydantic import BaseModel
from rich.console import Console
from rich.json import JSON
from rich.table import Table

from esgvoc.api.projects import (
    get_all_collections_in_project,
    get_all_projects,
    get_all_terms_in_collection,
    get_term_in_collection,
    get_term_in_project,
)
from esgvoc.api.universe import (
    get_all_data_descriptors_in_universe,
    get_all_terms_in_data_descriptor,
    get_term_in_data_descriptor,
    get_term_in_universe,
)

app = typer.Typer()
console = Console()

_LOGGER = logging.getLogger(__name__)


def validate_key_format(key: str):
    """
    Validate if the key matches the XXXX:YYYY:ZZZZ format.
    """
    if not re.match(r"^[a-zA-Z0-9\/_-]*:[a-zA-Z0-9\/_-]*:[a-zA-Z0-9\/_.-]*$", key):
        raise typer.BadParameter(f"Invalid key format: {key}. Must be XXXX:YYYY:ZZZZ.")
    return key.split(":")


def handle_universe(data_descriptor_id: str | None, term_id: str | None, options=None):
    _LOGGER.debug(f"Handling universe with data_descriptor_id={data_descriptor_id}, term_id={term_id}")
    if data_descriptor_id and term_id:
        return get_term_in_data_descriptor(data_descriptor_id, term_id, options)
        # BaseModel|dict[str: BaseModel]|None:

    elif term_id:
        return get_term_in_universe(term_id, options)
        # dict[str, BaseModel] | dict[str, dict[str, BaseModel]] | None:

    elif data_descriptor_id:
        return get_all_terms_in_data_descriptor(data_descriptor_id, options)
        # dict[str, BaseModel]|None:

    else:
        return get_all_data_descriptors_in_universe()
        # dict[str, dict]:


def handle_project(project_id: str, collection_id: str | None, term_id: str | None, options=None):
    _LOGGER.debug(f"Handling project {project_id} with Y={collection_id}, Z={term_id}, options = {options}")

    if project_id and collection_id and term_id:
        return get_term_in_collection(project_id, collection_id, term_id, options)
        # BaseModel|dict[str: BaseModel]|None:

    elif term_id:
        return get_term_in_project(project_id, term_id, options)
        # dict[str, BaseModel] | dict[str, dict[str, BaseModel]] | None:

    elif collection_id:
        return get_all_terms_in_collection(project_id, collection_id, options)
        # dict[str, BaseModel]|None:

    else:
        res = get_all_collections_in_project(project_id)
        if res is None:
            return None
        else:
            return res
        # dict[str, dict]:


def handle_unknown(x: str | None, y: str | None, z: str | None):
    print(f"Something wrong in X,Y or Z : X={x}, Y={y}, Z={z}")


def display(data: Any):
    if isinstance(data, BaseModel):
        # Pydantic Model - use mode='json' to serialize datetime and other types
        console.print(JSON.from_data(data.model_dump(mode="json")))
    elif isinstance(data, dict):
        # Dictionary as JSON
        console.print(data.keys())
    elif isinstance(data, list):
        # List as Table
        table = Table(title="List")
        table.add_column("Index")
        table.add_column("Item")
        for i, item in enumerate(data):
            table.add_row(str(i), str(item))
        console.print(table)
    else:
        # Fallback to simple print
        console.print(data)


@app.command()
def get(
    keys: List[str] = typer.Argument(..., help="List of keys in XXXX:YYYY:ZZZZ format"),
    select: Optional[List[str]] = typer.Option(None, "--select", help="keys selected for the result. Can be used as --select field1 --select field2 or --select [field1,field2]"),
):
    """
    Retrieve a specific value from the database system.\n
    This command allows you to fetch a value by specifying the universe/project, data_descriptor/collection,
    and term in a structured format.\n
    \n

    Usage:\n
        `get <project>:<collection>:<term>`\n
        `get <project>:<collection>:<term> --select <field>`\n
        `get <project>:<collection>:<term> --select [<field1>,<field2>,...]`\n
    \n
    Arguments:\n
        <project>\tThe project id to query. like `cmip6plus`\n
        <collection>\tThe collection id in the specified database.\n
        <term>\t\tThe term id within the specified collection.\n
    \n
    Options:\n
        --select\tSelect specific fields to display. By default, all fields are returned.\n
        \t\tThe result will always include the 'id' field plus the selected fields.\n
        \t\tYou can use this option in multiple ways:\n
        \t\t  - Single field: --select drs_name\n
        \t\t  - Multiple flags: --select drs_name --select description\n
        \t\t  - Bracket notation: --select [drs_name,description]\n
    \n
    Examples:\n
        Retrieve full term information:\n
            `get cmip6plus:institution_id:ipsl`\n
        \n
        Retrieve only specific fields:\n
            `get :activity:volmip --select drs_name`\n
            Returns: id='volmip' drs_name='VolMIP'\n
        \n
        Retrieve multiple fields using bracket notation:\n
            `get :activity:volmip --select [drs_name,description]`\n
            Returns: id='volmip' drs_name='VolMIP' description=...\n
        \n
        Retrieve multiple fields using multiple flags:\n
            `get :activity:volmip --select drs_name --select description`\n
        \n
        List all terms in a collection with selected fields:\n
            `get :activity: --select drs_name`\n
        \n
        The default project is the universe CV: the argument would be like `universe:institution:ipsl` or `:institution:ipsl`\n
        \n
    \n
    Notes:\n
        - Ensure data exist in your system before using this command (use `esgvoc status` command to see whats available).\n
        - Use a colon (`:`) to separate the parts of the argument.  \n
        - If more than one argument is given i.e get X:Y:Z A:B:C the 2 results are appended. \n
        - The 'id' field is always included in the result, even when using --select.\n
    \n
    """
    # Parse select parameter to handle bracket notation [field1,field2,...]
    parsed_select = None
    if select is not None:
        parsed_select = []
        for item in select:
            # Check if item is in bracket notation like [field1,field2]
            if item.startswith("[") and item.endswith("]"):
                # Remove brackets and split by comma
                fields = item[1:-1].split(",")
                # Strip whitespace and quotes from each field
                parsed_select.extend([f.strip().strip("'\"") for f in fields if f.strip()])
            else:
                # Regular field, just add it
                parsed_select.append(item.strip().strip("'\""))

    known_projects = get_all_projects()

    # Validate and process each key
    for key in keys:
        validated_key = validate_key_format(key)
        _LOGGER.debug(f"Processed key: {validated_key}")
        where, what, who = validated_key
        what = what if what != "" else None
        who = who if who != "" else None
        if where == "" or where == "universe":
            res = handle_universe(what, who, parsed_select)
        elif where in known_projects:
            res = handle_project(where, what, who, parsed_select)
        else:
            res = handle_unknown(where, what, who)

        display(res)

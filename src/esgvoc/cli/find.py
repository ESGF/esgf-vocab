import re
from typing import Any

import typer
from pydantic import BaseModel
from requests import logging
from rich.console import Console
from rich.json import JSON
from rich.table import Table

from esgvoc.api.projects import (
    find_collections_in_project,
    find_items_in_project,
    find_terms_in_all_projects,
    find_terms_in_collection,
    find_terms_in_project,
    get_all_projects,
)
from esgvoc.api.universe import (
    find_data_descriptors_in_universe,
    find_items_in_universe,
    find_terms_in_data_descriptor,
    find_terms_in_universe,
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


def handle_universe(expression: str, data_descriptor_id: str | None, term_id: str | None, options=None):
    _LOGGER.debug(f"Handling universe with data_descriptor_id={data_descriptor_id}, term_id={term_id}")

    if data_descriptor_id:
        return find_terms_in_data_descriptor(expression, data_descriptor_id)
        # BaseModel|dict[str: BaseModel]|None:

    else:
        return find_terms_in_universe(expression)
        # dict[str, dict]:


def handle_project(expression: str, project_id: str, collection_id: str | None, term_id: str | None, options=None):
    _LOGGER.debug(f"Handling project {project_id} with Y={collection_id}, Z={term_id}, options = {options}")

    if project_id == "all":
        return find_terms_in_all_projects(expression)

    elif collection_id:
        return find_terms_in_collection(expression, project_id, collection_id)
        # dict[str, BaseModel]|None:

    else:
        res = find_terms_in_project(expression, project_id)
        if res is None:
            return None
        else:
            return res
        # dict[str, dict]:


def handle_unknown(x: str | None, y: str | None, z: str | None):
    print(f"Something wrong in X,Y or Z : X={x}, Y={y}, Z={z}")


def display(data: Any):
    if isinstance(data, BaseModel):
        # Pydantic Model
        console.print(JSON.from_data(data.model_dump()))
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
def find(expression: str, keys: list[str] = typer.Argument(..., help="List of keys in XXXX:YYYY:ZZZZ format")):
    """
    Retrieve a specific value from the database system.\n
    This command allows you to fetch a value by specifying the universe/project, data_descriptor/collection,
    and term in a structured format.\n
    \n

    Usage:\n
        `find <expression> <project>:<collection>:<term>`\n
    \n
    Arguments:\n
        <expression>\t The full text search expression.
        <project>\tThe project id to query. like `cmip6plus`\n
        <collection>\tThe collection id in the specified database.\n
        <term>\t\tThe term id within the specified collection.\n
    \n
    Example:
    \n
    Notes:\n
        - Ensure data exist in your system before using this command (use `esgvoc status` command to see whats available).\n
        - Use a colon (`:`) to separate the parts of the argument.  \n
        - if more than one argument is given i.e get X:Y:Z A:B:C the 2 results are appended. \n
    \n
    """
    known_projects = get_all_projects()
    _LOGGER.debug(f"Processed expression: {expression}")

    # Validate and process each key
    for key in keys:
        validated_key = validate_key_format(key)
        _LOGGER.debug(f"Processed key: {validated_key}")
        where, what, who = validated_key
        what = what if what != "" else None
        who = who if who != "" else None
        if where == "" or where == "universe":
            res = handle_universe(expression, what, who)
        elif where in known_projects:
            res = handle_project(expression, where, what, who, None)
        else:
            res = handle_unknown(where, what, who)

        display(res)

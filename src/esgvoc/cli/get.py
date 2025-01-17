
from typing import Any
from esgvoc.api.projects import find_terms_in_collection, find_terms_in_project, get_all_collections_in_project, get_all_projects, get_all_terms_in_collection
from esgvoc.api.universe import find_terms_in_data_descriptor, find_terms_in_universe, get_all_data_descriptors_in_universe, get_all_terms_in_data_descriptor
from pydantic import BaseModel
from requests import logging
from rich.table import Table
import typer
import re
from rich.json import JSON
from rich.console import Console

app = typer.Typer()
console = Console()

_LOGGER = logging.getLogger(__name__)

def validate_key_format(key: str):
    """
    Validate if the key matches the XXXX:YYYY:ZZZZ format.
    """
    if not re.match(r"^[a-zA-Z0-9\/_]*:[a-zA-Z0-9\/_]*:[a-zA-Z0-9\/_]*$", key):
        raise typer.BadParameter(f"Invalid key format: {key}. Must be XXXX:YYYY:ZZZZ.")
    return key.split(":")


def handle_universe(data_descriptor_id:str|None,term_id:str|None, options=None):
    _LOGGER.debug(f"Handling universe with data_descriptor_id={data_descriptor_id}, term_id={term_id}") 

    if data_descriptor_id and term_id:
        return find_terms_in_data_descriptor(data_descriptor_id,term_id,options)
        # BaseModel|dict[str: BaseModel]|None:

    elif term_id:
        return find_terms_in_universe(term_id,options)
        # dict[str, BaseModel] | dict[str, dict[str, BaseModel]] | None:


    elif data_descriptor_id:
        return get_all_terms_in_data_descriptor(data_descriptor_id)
        # dict[str, BaseModel]|None:

    else:
        return get_all_data_descriptors_in_universe()
        # dict[str, dict]:

def handle_project(project_id:str,collection_id:str|None,term_id:str|None,options=None):
    _LOGGER.debug(f"Handling project {project_id} with Y={collection_id}, Z={term_id}, options = {options}")
    
    if project_id and collection_id and term_id:
        return find_terms_in_collection(project_id,collection_id,term_id)
        # BaseModel|dict[str: BaseModel]|None:

    elif term_id:
        return find_terms_in_project(project_id, term_id,options)
        # dict[str, BaseModel] | dict[str, dict[str, BaseModel]] | None:


    elif collection_id:
        return get_all_terms_in_collection(project_id, collection_id)
        # dict[str, BaseModel]|None:

    else:
        res = get_all_collections_in_project(project_id)
        if res is None:
            return None
        else:
            return res
        # dict[str, dict]:


def handle_unknown(x:str|None,y:str|None,z:str|None):
    print(f"Something wrong in X,Y or Z : X={x}, Y={y}, Z={z}")


def display(data:Any):

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
def get(keys: list[str] = typer.Argument(..., help="List of keys in XXXX:YYYY:ZZZZ format")):
    """
    Retrieve a specific value from the database system.
    This command allows you to fetch a value by specifying the universe/project, data_descriptor/collection, 
    and term in a structured format.

    Usage:
        `get <project>:<collection>:<term>`

    Arguments:
        <project>        The name of the project to query. like `cmip6plus`
        <collection>     The name of the collection in the specified database.
        <term>           The name or term within the specified collection.

    Example:
        To retrieve the value from the "cmip6plus" project, under the "institution_id" column, 
        in the term with the identifier "ipsl", you would use:
            `get cmip6plus:institution_id:ipsl`
        The default project is the universe CV : the argument would be like `universe:institution:ipsl` or `:institution:ipsl`
        - to get list of available term from universe institution `:institution:` 

    Notes:
        - Ensure data exist in your system before using this command (use status command to see whats available).
        - Use a colon (`:`) to separate the parts of the argument.  
        - if more than one argument is given i.e get X:Y:Z A:B:C the 2 results are appended. 

    """ 
    known_projects = get_all_projects()

    # Validate and process each key
    for key in keys:
        validated_key = validate_key_format(key)
        _LOGGER.debug(f"Processed key: {validated_key}")
        where,what,who = validated_key
        what = what if what!="" else None
        who = who if who!="" else None
        if where == "" or where=="universe": 
            res = handle_universe(what,who)
        elif where in known_projects:
            res = handle_project(where,what,who,{})
        else:
            res = handle_unknown(where,what,who)
        
        display(res)



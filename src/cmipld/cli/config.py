
import json
from rich.syntax import Syntax
import typer
from cmipld.core.service.settings import ServiceSettings, UniverseSettings, ProjectSettings
from pathlib import Path
from rich import print
import toml

app = typer.Typer()

SETTINGS_FILE = Path("./src/cmipld/core/service/settings.toml")

def load_settings() -> ServiceSettings:
    """Load the settings from the TOML file."""
    if SETTINGS_FILE.exists():
        return ServiceSettings.load_from_file(str(SETTINGS_FILE))
    else:
        typer.echo("Settings file not found. Creating a new one with defaults.")
        default_settings = ServiceSettings(
        universe=UniverseSettings(
            github_repo="https://github.com/example/universe",
            branch="main",
            local_path="/local/universe",
            db_name="universe.db"
        ),
        Project1=ProjectSettings(
                project_name="Project1",
                github_repo="https://github.com/example/project1",
                branch="main",
                local_path="/local/project1",
                db_name="project1.db"
            )
        
    )

        default_settings.save_to_file(str(SETTINGS_FILE))
        return default_settings

def save_settings(settings: ServiceSettings):
    """Save the settings to the TOML file."""
    settings.save_to_file(str(SETTINGS_FILE))

def get_nested_value(settings_dict: dict, key_path: str):
    """Navigate through nested dictionary keys using dot-separated key paths."""
    keys = key_path.split(".")
    value = settings_dict
    for key in keys:
        value = value[key]
    return value

def set_nested_value(settings_dict: dict, key_path: str, new_value):
    """Set a value in a nested dictionary using a dot-separated key path."""
    keys = key_path.split(".")
    sub_dict = settings_dict
    for key in keys[:-1]:
        sub_dict = sub_dict[key]
    sub_dict[keys[-1]] = new_value
    return settings_dict
    
@app.command()
def config(key: str |None = typer.Argument(None), value: str|None = typer.Argument(None)):
    """
    Manage configuration settings.

    - With no arguments: display all settings.
    - With one argument (key): display the value of the key.
    - With two arguments (key and value): modify the key's value and save.
    """
    
    settings = load_settings()
    if key is None:
        # No key provided, print all settings
        # typer.echo(settings.model_dump())
        syntax = Syntax(toml.dumps(settings.model_dump()), "toml")
        print(syntax) 
        return
    if value is None:
        # Key provided but no value, print the specific key's value
        try:
            selected_value = get_nested_value(json.loads(settings.model_dump_json()),key)
            typer.echo(selected_value)
        except KeyError:
            try: 
                selected_value = get_nested_value(json.loads(settings.model_dump_json()),"projects."+key)
                typer.echo(selected_value)
                return 
            except KeyError:
                pass
            typer.echo(f"Key '{key}' not found in settings.")
        return

    # Modify the key's value
    try :
        selected_value = get_nested_value(json.loads(settings.model_dump_json()),key)
    except Exception:
        key = "projects."+key
    try : 
        selected_value = get_nested_value(json.loads(settings.model_dump_json()),key)
        if selected_value:
            new_settings_dict = set_nested_value(json.loads(settings.model_dump_json()),key, value )
            new_settings = ServiceSettings(**new_settings_dict)
            save_settings(new_settings)
            typer.echo(f"New settings {new_settings.model_dump_json(indent=4)}")
            typer.echo(f"Updated '{key}' to '{value}'.")
        else:
            typer.echo(f"Key '{key}' not found in settings.")
    except Exception as e:
        typer.echo(f"Error updating settings: {e}")


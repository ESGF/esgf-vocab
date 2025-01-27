from esgvoc.core import service
from rich.table import Table
import typer
from rich.console import Console

app = typer.Typer()
console = Console()


def display(table):
    console = Console(record=True,width=200)
    console.print(table)



@app.command()
def status():
    """
    Command to display status 
    i.e summary of version of usable ressources (between remote/cached)  
    
    """

    service.state_service.get_state_summary()
    #display(service.state_service.table())


    table = Table(show_header=False, show_lines=True)

    table.add_row("","Remote github repo","Local repository","Cache Database", style = "bright_green")
    table.add_row("Universe path",service.state_service.universe.github_repo,service.state_service.universe.local_path,service.state_service.universe.db_path, style = "white")
    table.add_row("Version",service.state_service.universe.github_version,service.state_service.universe.local_version,service.state_service.universe.db_version, style="bright_blue")
    for proj_name,proj in service.state_service.projects.items():
        table.add_row(f"{proj_name} path",proj.github_repo,proj.local_path,proj.db_path, style="white")
        table.add_row("Version",proj.github_version,proj.local_version,proj.db_version,style ="bright_blue")
    display(table)

    

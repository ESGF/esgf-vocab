"""
Generation of CMOR tables
"""

import json
from pathlib import Path
from typing import Annotated

import typer

from esgvoc.apps.cmor_tables import generate_cvs_table

app = typer.Typer()


@app.command()
def cmor_export_cvs_table(
    out_path: Annotated[
        Path | None,
        typer.Option(
            help="Path in which to write the output. If not provided, the result is printed instead.",
            dir_okay=False,
            file_okay=True,
        ),
    ] = None,
    project: Annotated[str, typer.Option(help="CMIP project for which to generate the table")] = "CMIP7",
) -> None:
    """
    Export CVs table in the format required by CMOR
    """
    json_dump_settings = dict(indent=2, sort_keys=True)

    cvs_table = generate_cvs_table(project=project.lower())
    cvs_table_json = cvs_table.to_cvs_json()

    if out_path:
        with open(out_path, "w") as fh:
            json.dump(cvs_table_json, fh, **json_dump_settings)

    else:
        print(json.dumps(cvs_table_json, **json_dump_settings))


if __name__ == "__main__":
    app()

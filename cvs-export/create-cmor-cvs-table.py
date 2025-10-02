"""
Prototype for creating a CMOR CVs table from esgvoc

Suggestions:

1. this is translated into an esgvoc app
1. the CMORCVs model/schema and related classes get used/endorsed by CMOR
   so the contract/API we're working to is formally documented/agreed
   (at present it seems not to be so formally described anywhere?)
"""

import json
from pathlib import Path
from typing import Any, TypeAlias

from pydantic import BaseModel

RegularExpressionValidators: TypeAlias = list[str]
"""
List of values which are assumed to be regular expressions

Attribute values provided by teams are then validated
against these regular expressions.
"""

AllowedDict: TypeAlias = dict[str, Any]
"""
Dictionary (key-value pairs). The keys define the allowed values for the given attribute

The values can be anything,
they generally provide extra information about the meaning of the keys.
"""


class CMORCVsTable(BaseModel):
    """
    Representation of the JSON table required by CMOR for CVs

    CMOR also takes in variable tables,
    as well as a user input table.
    This model doesn't consider those tables
    or their interactions with this table at the moment.
    """

    # Switch to DataSpecsVersion when it has attributes we can use
    # data_specs_version: DataSpecsVersion
    data_specs_version: str
    """
    Version of the data specification used to generate the CVs

    Note that the exact meaning of this
    (i.e. what exactly defines the data specs)
    is still fuzzy.
    """
    # Validation(?): must be a version of the form X.Y.Z[.alpha[0-9]*]

    # TODO: switch to using esgvoc's model once it is clear what key we should use for 'value'
    mip_era: str
    """
    MIP era to which the data applies
    """
    # Validation(?): must be equal to CMIP7

    def to_json(self) -> dict[str, dict[str, str, AllowedDict, RegularExpressionValidators]]:
        md = self.model_dump()

        cvs_json = {"CV": md}
        return cvs_json


def main():
    """
    Create the CMOR CVs table
    """
    OUT_FILE = Path(".") / "CMIP7-CV_for-cmor.json"

    cmor_cvs_table = CMORCVsTable(
        data_specs_version="placeholder",
        mip_era="CMIP7",
    )

    cmor_cvs_table_json = cmor_cvs_table.to_json()
    with open(OUT_FILE, "w") as fh:
        json.dump(cmor_cvs_table_json, fh, indent=4, sort_keys=True)

    print(f"Wrote {OUT_FILE}")


if __name__ == "__main__":
    main()

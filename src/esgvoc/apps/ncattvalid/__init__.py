"""
GA — Global Attributes validation for NetCDF files.

Quick start::

    from esgvoc.apps.ga import GAValidator

    validator = GAValidator("cmip6")
    report = validator.validate_ncdump(open("myfile.nc.header").read())

    if not report.is_valid:
        print(report)   # human-readable summary
"""

from .validator import (
    AttributeResult,
    GAReport,
    GAValidator,
    parse_ncdump_global_attributes,
)

__all__ = [
    "GAValidator",
    "GAReport",
    "AttributeResult",
    "parse_ncdump_global_attributes",
]

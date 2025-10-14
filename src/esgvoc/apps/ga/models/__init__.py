"""
GA (Global Attributes) models package.

This package provides Pydantic models for validating NetCDF global attributes
against project specifications using the esgvoc API.
"""

# Import from project_specs for attribute models
from esgvoc.api.project_specs import AttributeProperty, AttributeSpecification

from .netcdf_header import (
    NetCDFDimension,
    NetCDFVariable,
    NetCDFGlobalAttributes as NetCDFGlobalAttributesNew,
    NetCDFHeader,
    NetCDFHeaderParser,
)

from .validator import (
    ValidationSeverity,
    ValidationIssue,
    ValidationReport,
    ESGVocAttributeValidator,
    GlobalAttributeValidator as GlobalAttributeValidatorNew,
    ValidatorFactory,
)


# Build __all__ dynamically based on available modules
__all__ = [
    # Attribute specification models from project_specs
    "AttributeProperty",
    "AttributeSpecification",
    # NetCDF header models
    "NetCDFDimension",
    "NetCDFVariable",
    "NetCDFGlobalAttributesNew",
    "NetCDFHeader",
    "NetCDFHeaderParser",
    # Validation models
    "ValidationSeverity",
    "ValidationIssue",
    "ValidationReport",
    "ESGVocAttributeValidator",
    "GlobalAttributeValidatorNew",
    "ValidatorFactory",
]

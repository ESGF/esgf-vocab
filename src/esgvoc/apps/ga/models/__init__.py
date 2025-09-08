"""
GA (Global Attributes) models package.

This package provides Pydantic models for validating NetCDF global attributes
against project specifications using the esgvoc API.
"""

# New refactored models
from .attribute_spec import (
    GlobalAttributeValueType,
    GlobalAttributeVisitor,
    GlobalAttributeSpecBase,
    GlobalAttributeSpecSpecific,
    GlobalAttributeSpec,
    GlobalAttributeSpecs,
    ValueTypeDefinition,
    ValidationRules,
    AttributeSpecsConfig,
)

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
    # New attribute specification models
    "GlobalAttributeValueType",
    "GlobalAttributeVisitor",
    "GlobalAttributeSpecBase",
    "GlobalAttributeSpecSpecific",
    "GlobalAttributeSpec",
    "GlobalAttributeSpecs",
    "ValueTypeDefinition",
    "ValidationRules",
    "AttributeSpecsConfig",
    # New NetCDF header models
    "NetCDFDimension",
    "NetCDFVariable",
    "NetCDFGlobalAttributesNew",
    "NetCDFHeader",
    "NetCDFHeaderParser",
    # New validation models
    "ValidationSeverity",
    "ValidationIssue",
    "ValidationReport",
    "ESGVocAttributeValidator",
    "GlobalAttributeValidatorNew",
    "ValidatorFactory",
]

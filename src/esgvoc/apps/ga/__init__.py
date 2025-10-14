"""GA application for global attributes validation for netCDF files.

This package provides tools for validating NetCDF global attributes against
project specifications (like CMIP6, CMIP7) using controlled vocabularies
from the esgvoc API.

Key Features:
- YAML-based configuration for attribute specifications
- Integration with esgvoc controlled vocabularies
- NetCDF header parsing from ncdump output
- Comprehensive validation reporting
- Support for different project specifications

Example Usage:
```python
from esgvoc.apps.ga import GAValidator, validate_netcdf_attributes

# Quick validation from ncdump output
report = validate_netcdf_attributes(
    ncdump_output=ncdump_text,
    project_id="cmip6",
    filename="my_file.nc"
)

print(f"Validation result: {'PASS' if report.is_valid else 'FAIL'}")
print(f"Errors: {report.error_count}, Warnings: {report.warning_count}")

# Or use the full validator class
validator = GAValidator(project_id="cmip6")
report = validator.validate_from_ncdump(ncdump_text)

# Get detailed validation summary
from esgvoc.apps.ga import create_validation_summary
print(create_validation_summary(report))
```

Advanced Usage:
```python
from esgvoc.apps.ga.models import NetCDFHeader, NetCDFHeaderParser

# Parse NetCDF header from ncdump output
ncdump_output = '''
netcdf test_file {
// global attributes:
        :Conventions = "CF-1.7 CMIP-6.2" ;
        :activity_id = "CMIP" ;
        :experiment_id = "historical" ;
}
'''

header = NetCDFHeaderParser.parse_from_ncdump(ncdump_output)
print(f"File: {header.filename}")
print(f"Attributes: {header.global_attributes.list_attributes()}")
```
"""

# Main GA validator interface
from .validator import (
    GAValidator,
    GAValidatorFactory,
    validate_netcdf_attributes,
    create_validation_summary
)

# Core models
from .models import (
    # Models for advanced usage
    NetCDFHeader,
    NetCDFHeaderParser,
    ValidationReport,
    ValidationSeverity,
    ValidationIssue,

    # Validator models
    ESGVocAttributeValidator,
    ValidatorFactory,

    # Import AttributeProperty from project_specs
    AttributeProperty,
    AttributeSpecification,
)

__all__ = [
    # Main interface
    "GAValidator",
    "GAValidatorFactory",
    "validate_netcdf_attributes",
    "create_validation_summary",

    # Models
    "NetCDFHeader",
    "NetCDFHeaderParser",
    "ValidationReport",
    "ValidationSeverity",
    "ValidationIssue",

    # Attribute specifications from project_specs
    "AttributeProperty",
    "AttributeSpecification",

    # Validators
    "ESGVocAttributeValidator",
    "ValidatorFactory",
]
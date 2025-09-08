"""
Main validator interface for NetCDF global attributes.

This module provides the high-level API for validating NetCDF global attributes
against project specifications using YAML configuration files and the esgvoc API.
"""

import os
import yaml
from pathlib import Path
from typing import Optional, Dict, Any, List

from .models import (
    AttributeSpecsConfig,
    GlobalAttributeSpecs,
    NetCDFHeader,
    NetCDFHeaderParser,
    ValidationReport,
    ValidationSeverity,
)
from .models.validator import GlobalAttributeValidator


class GAValidator:
    """
    Main validator class for the GA (Global Attributes) application.

    This class provides a high-level interface for validating NetCDF global
    attributes against project specifications defined in YAML files.
    """

    def __init__(self, config_path: Optional[str] = None, project_id: str = "cmip6"):
        """
        Initialize the GA validator.

        :param config_path: Path to YAML configuration file. If None, uses default.
        :param project_id: Project identifier for validation
        """
        self.project_id = project_id
        self.config_path = config_path or self._get_default_config_path()

        # Load configuration
        self.config = self._load_config()
        self.attribute_specs = self.config.to_global_attribute_specs()

        # Initialize the validator
        self.validator = GlobalAttributeValidator(self.attribute_specs, project_id)

    def _get_default_config_path(self) -> str:
        """Get the default configuration file path."""
        current_dir = Path(__file__).parent
        return str(current_dir / "attributes_specs.yaml")

    def _load_config(self) -> AttributeSpecsConfig:
        """Load and parse the YAML configuration file."""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f)

        return AttributeSpecsConfig(**yaml_data)

    def validate_from_ncdump(self, ncdump_output: str, filename: Optional[str] = None) -> ValidationReport:
        """
        Validate global attributes from ncdump command output.

        :param ncdump_output: Output from ncdump -h command
        :param filename: Optional filename for reporting
        :return: Validation report
        """
        # Parse the NetCDF header
        try:
            header = NetCDFHeaderParser.parse_from_ncdump(ncdump_output)
        except Exception as e:
            # Return error report if parsing fails
            report = ValidationReport(filename=filename, project_id=self.project_id, is_valid=False)
            report.add_issue(
                {
                    "attribute_name": "parse_error",
                    "severity": ValidationSeverity.ERROR,
                    "message": f"Failed to parse ncdump output: {str(e)}",
                    "actual_value": None,
                    "expected_value": None,
                    "source_collection": None,
                }
            )
            return report

        # Set filename if provided
        if filename:
            header.filename = filename

        # Validate global attributes
        return self.validator.validate(header.global_attributes, header.filename)

    def validate_from_attributes_dict(
        self, attributes: Dict[str, Any], filename: Optional[str] = None
    ) -> ValidationReport:
        """
        Validate global attributes from a dictionary.

        :param attributes: Dictionary of global attributes
        :param filename: Optional filename for reporting
        :return: Validation report
        """
        from .models.netcdf_header import NetCDFGlobalAttributes

        global_attrs = NetCDFGlobalAttributes(attributes=attributes)
        return self.validator.validate(global_attrs, filename)


    def get_required_attributes(self) -> List[str]:
        """
        Get list of required attribute names.

        :return: List of required attribute names
        """
        return [attr_name for attr_name, spec in self.attribute_specs.items() if spec.required]

    def get_optional_attributes(self) -> List[str]:
        """
        Get list of optional attribute names.

        :return: List of optional attribute names
        """
        return [attr_name for attr_name, spec in self.attribute_specs.items() if not spec.required]

    def get_attribute_info(self, attribute_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific attribute.

        :param attribute_name: Name of the attribute
        :return: Attribute information dictionary or None if not found
        """
        if attribute_name not in self.attribute_specs:
            return None

        spec = self.attribute_specs[attribute_name]
        return {
            "name": attribute_name,
            "source_collection": spec.source_collection,
            "value_type": spec.value_type,
            "required": spec.required,
            "description": getattr(spec, "description", None),
            "default_value": getattr(spec, "default_value", None),
            "specific_key": getattr(spec, "specific_key", None),
        }

    def list_attributes(self) -> List[str]:
        """
        Get list of all defined attribute names.

        :return: List of all attribute names
        """
        return list(self.attribute_specs.keys())

    def reload_config(self, config_path: Optional[str] = None) -> None:
        """
        Reload configuration from file.

        :param config_path: Optional new config path. If None, uses current path.
        """
        if config_path:
            self.config_path = config_path

        self.config = self._load_config()
        self.attribute_specs = self.config.to_global_attribute_specs()
        self.validator = GlobalAttributeValidator(self.attribute_specs, self.project_id)


class GAValidatorFactory:
    """
    Factory for creating GA validators with different configurations.
    """

    @staticmethod
    def create_cmip6_validator() -> GAValidator:
        """
        Create a validator configured for CMIP6.

        :return: GAValidator instance for CMIP6
        """
        return GAValidator(project_id="cmip6")

    @staticmethod
    def create_cmip7_validator() -> GAValidator:
        """
        Create a validator configured for CMIP7.

        :return: GAValidator instance for CMIP7
        """
        return GAValidator(project_id="cmip7")

    @staticmethod
    def create_custom_validator(config_path: str, project_id: str = "custom") -> GAValidator:
        """
        Create a validator with custom configuration.

        :param config_path: Path to custom YAML configuration file
        :param project_id: Project identifier
        :return: GAValidator instance with custom configuration
        """
        return GAValidator(config_path=config_path, project_id=project_id)


def validate_netcdf_attributes(
    ncdump_output: str, config_path: Optional[str] = None, project_id: str = "cmip6", filename: Optional[str] = None
) -> ValidationReport:
    """
    Convenience function to validate NetCDF global attributes.

    :param ncdump_output: Output from ncdump -h command
    :param config_path: Optional path to YAML configuration file
    :param project_id: Project identifier for validation
    :param filename: Optional filename for reporting
    :return: Validation report
    """
    validator = GAValidator(config_path, project_id)
    return validator.validate_from_ncdump(ncdump_output, filename)


def create_validation_summary(report: ValidationReport) -> str:
    """
    Create a human-readable summary of a validation report.

    :param report: Validation report to summarize
    :return: Formatted summary string
    """
    lines = []
    lines.append("=" * 60)
    lines.append("NetCDF Global Attributes Validation Report")
    lines.append("=" * 60)

    if report.filename:
        lines.append(f"File: {report.filename}")
    lines.append(f"Project: {report.project_id}")
    lines.append(f"Status: {'VALID' if report.is_valid else 'INVALID'}")
    lines.append("")

    # Summary statistics
    lines.append("Summary:")
    lines.append(f"  • Errors: {report.error_count}")
    lines.append(f"  • Warnings: {report.warning_count}")
    lines.append(f"  • Info messages: {report.info_count}")
    lines.append(f"  • Validated attributes: {len(report.validated_attributes)}")
    lines.append(f"  • Missing required attributes: {len(report.missing_attributes)}")
    lines.append(f"  • Extra attributes: {len(report.extra_attributes)}")
    lines.append("")

    # Issues by severity
    if report.issues:
        lines.append("Issues:")
        lines.append("")

        for severity in [ValidationSeverity.ERROR, ValidationSeverity.WARNING, ValidationSeverity.INFO]:
            severity_issues = report.get_issues_by_severity(severity)
            if severity_issues:
                lines.append(f"{severity.value.upper()}S:")
                for i, issue in enumerate(severity_issues):
                    lines.append(f"  • {issue.attribute_name}: {issue.message}")
                    if issue.expected_value is not None:
                        lines.append(f"    Expected: {issue.expected_value}")
                    if issue.actual_value is not None:
                        lines.append(f"    Actual: {issue.actual_value}")

                    # Add separator between errors (except for the last one)
                    if i < len(severity_issues) - 1:
                        lines.append("    " + "-" * 50)
                        lines.append("")
                lines.append("")

    # Missing attributes
    if report.missing_attributes:
        lines.append("Missing Required Attributes:")
        for attr in report.missing_attributes:
            lines.append(f"  • {attr}")
        lines.append("")

    # Extra attributes
    if report.extra_attributes:
        lines.append("Extra Attributes (not in specification):")
        for attr in report.extra_attributes:
            lines.append(f"  • {attr}")
        lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)

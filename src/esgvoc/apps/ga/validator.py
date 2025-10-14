"""
Main validator interface for NetCDF global attributes.

This module provides the high-level API for validating NetCDF global attributes
against project specifications loaded from the esgvoc database.
"""

from typing import Optional, Dict, Any, List

import esgvoc.api.projects as projects
from esgvoc.api.project_specs import AttributeSpecification
from esgvoc.core.exceptions import EsgvocNotFoundError
from .models import (
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
    attributes against project specifications loaded from the esgvoc database.
    """

    def __init__(self, project_id: str = "cmip6"):
        """
        Initialize the GA validator.

        :param project_id: Project identifier for validation
        """
        self.project_id = project_id

        # Load attribute specifications from database
        self.attribute_specs = self._load_from_database()

        # Initialize the validator
        self.validator = GlobalAttributeValidator(self.attribute_specs, project_id)

    def _load_from_database(self) -> AttributeSpecification:
        """Load attribute specifications from the esgvoc database."""
        project = projects.get_project(self.project_id)

        if project is None:
            raise EsgvocNotFoundError(f"Project '{self.project_id}' not found in database")

        if project.attr_specs is None:
            raise ValueError(f"Project '{self.project_id}' has no attribute specifications")

        return project.attr_specs

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
        return [
            spec.field_name or spec.source_collection
            for spec in self.attribute_specs
            if spec.is_required
        ]

    def get_optional_attributes(self) -> List[str]:
        """
        Get list of optional attribute names.

        :return: List of optional attribute names
        """
        return [
            spec.field_name or spec.source_collection
            for spec in self.attribute_specs
            if not spec.is_required
        ]

    def get_attribute_info(self, attribute_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific attribute.

        :param attribute_name: Name of the attribute
        :return: Attribute information dictionary or None if not found
        """
        spec = None
        for s in self.attribute_specs:
            field_name = s.field_name or s.source_collection
            if field_name == attribute_name:
                spec = s
                break

        if spec is None:
            return None

        return {
            "name": attribute_name,
            "source_collection": spec.source_collection,
            "value_type": spec.value_type,
            "required": spec.is_required,
            "default_value": spec.default_value,
            "specific_key": spec.specific_key,
        }

    def list_attributes(self) -> List[str]:
        """
        Get list of all defined attribute names.

        :return: List of all attribute names
        """
        return [spec.field_name or spec.source_collection for spec in self.attribute_specs]

    def reload_config(self) -> None:
        """
        Reload attribute specifications from the database.
        """
        self.attribute_specs = self._load_from_database()
        self.validator = GlobalAttributeValidator(self.attribute_specs, self.project_id)


class GAValidatorFactory:
    """
    Factory for creating GA validators for different projects.
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


def validate_netcdf_attributes(
    ncdump_output: str, project_id: str = "cmip6", filename: Optional[str] = None
) -> ValidationReport:
    """
    Convenience function to validate NetCDF global attributes.

    Loads attribute specifications from the esgvoc database for the specified project.

    :param ncdump_output: Output from ncdump -h command
    :param project_id: Project identifier for validation
    :param filename: Optional filename for reporting
    :return: Validation report
    """
    validator = GAValidator(project_id)
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

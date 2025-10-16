"""
Validation models and logic for NetCDF global attributes.

This module provides the core validation functionality for verifying
NetCDF global attributes against project specifications using the esgvoc API.
"""

from typing import Any, Dict, List, Optional, Union
from enum import Enum
from pydantic import BaseModel, Field

import esgvoc.api.projects as projects
import esgvoc.api.search as search
from esgvoc.api.data_descriptors.data_descriptor import ConfiguredBaseModel
from esgvoc.api.project_specs import AttributeProperty, AttributeSpecification
from esgvoc.api.report import ValidationReport as EsgvocValidationReport
from esgvoc.core.exceptions import EsgvocNotFoundError, EsgvocDbError
from .netcdf_header import NetCDFGlobalAttributes


class ValidationSeverity(str, Enum):
    """Severity levels for validation issues."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationIssue(ConfiguredBaseModel):
    """
    Represents a validation issue found during attribute validation.
    """

    attribute_name: str = Field(..., description="Name of the attribute with the issue")
    severity: ValidationSeverity = Field(..., description="Severity level of the issue")
    message: str = Field(..., description="Human-readable description of the issue")
    expected_value: Optional[Any] = Field(default=None, description="Expected value if applicable")
    actual_value: Optional[Any] = Field(default=None, description="Actual value found")
    source_collection: Optional[str] = Field(default=None, description="Source collection for the attribute")


class ValidationReport(ConfiguredBaseModel):
    """
    Complete validation report for a NetCDF file's global attributes.
    """

    filename: Optional[str] = Field(default=None, description="NetCDF filename")
    project_id: str = Field(..., description="Project ID used for validation")
    is_valid: bool = Field(..., description="Overall validation status")
    issues: List[ValidationIssue] = Field(default_factory=list, description="List of validation issues")
    validated_attributes: Dict[str, Any] = Field(default_factory=dict, description="Successfully validated attributes")
    mapping_used: Dict[str, str] = Field(default_factory=dict, description="Mapping of attribute names to validated term values")
    missing_attributes: List[str] = Field(default_factory=list, description="Required attributes that are missing")
    extra_attributes: List[str] = Field(default_factory=list, description="Extra attributes not in specification")

    @property
    def error_count(self) -> int:
        """Number of error-level issues."""
        return len([issue for issue in self.issues if issue.severity == ValidationSeverity.ERROR])

    @property
    def warning_count(self) -> int:
        """Number of warning-level issues."""
        return len([issue for issue in self.issues if issue.severity == ValidationSeverity.WARNING])

    @property
    def info_count(self) -> int:
        """Number of info-level issues."""
        return len([issue for issue in self.issues if issue.severity == ValidationSeverity.INFO])

    def add_issue(self, issue: ValidationIssue) -> None:
        """Add a validation issue to the report."""
        self.issues.append(issue)
        if issue.severity == ValidationSeverity.ERROR:
            self.is_valid = False

    def get_issues_by_severity(self, severity: ValidationSeverity) -> List[ValidationIssue]:
        """Get all issues of a specific severity level."""
        return [issue for issue in self.issues if issue.severity == severity]

    def summary(self) -> str:
        """Get a summary of the validation report."""
        status = "VALID" if self.is_valid else "INVALID"
        return (
            f"Validation {status}: {self.error_count} errors, "
            f"{self.warning_count} warnings, {self.info_count} info messages"
        )


class ESGVocAttributeValidator:
    """
    Validator to validate attributes against ESGVOC controlled vocabularies.
    """

    def __init__(self, project_id: str = "cmip6"):
        """
        Initialize the validator.

        :param project_id: Project identifier for ESGVOC queries
        """
        self.project_id = project_id
        self.validation_results = {}

    def visit_base_attribute(
        self, attribute_name: str, attribute: AttributeProperty, attribute_value: Any
    ) -> Dict[str, Any]:
        """
        Validate a base global attribute against ESGVOC using proper validation logic.

        :param attribute_name: Name of the attribute
        :param attribute: Attribute specification
        :param attribute_value: The actual attribute value to validate
        :return: Validation result
        """
        try:
            # Convert value to string for validation
            value_str = str(attribute_value).strip()

            # Use esgvoc's proper validation function that handles Plain, Pattern, and Composite terms
            matching_terms = projects.valid_term_in_collection(
                value=value_str, project_id=self.project_id, collection_id=attribute.source_collection
            )

            # Validation is successful if we have any matching terms
            is_valid = len(matching_terms) > 0

            # Get available terms for error reporting if validation failed
            available_examples = []
            available_terms_full = []
            if not is_valid:
                try:
                    # Get some example terms from the collection for error reporting
                    all_terms = projects.get_all_terms_in_collection(
                        project_id=self.project_id,
                        collection_id=attribute.source_collection,
                        selected_term_fields=None,
                    )
                    available_examples = [term.id for term in all_terms[:3]]  # Just IDs for quick reference
                    available_terms_full = [term.model_dump() for term in all_terms[:3]]  # Full term objects
                except:
                    available_examples = []
                    available_terms_full = []

            return {
                "attribute_name": attribute_name,
                "source_collection": attribute.source_collection,
                "value_type": attribute.value_type,
                "validation_method": "esgvoc_validation",
                "is_valid": is_valid,
                "actual_value": value_str,
                "matching_terms": [
                    {"project_id": term.project_id, "collection_id": term.collection_id, "term_id": term.term_id}
                    for term in matching_terms
                ],
                "available_examples": available_examples,
                "available_terms_full": available_terms_full,
                "total_matches": len(matching_terms),
            }

        except (EsgvocNotFoundError, EsgvocDbError) as e:
            return {
                "attribute_name": attribute_name,
                "source_collection": attribute.source_collection,
                "validation_method": "esgvoc_validation",
                "is_valid": False,
                "error": str(e),
                "error_type": type(e).__name__,
            }

    def visit_specific_attribute(
        self, attribute_name: str, attribute: AttributeProperty, attribute_value: Any
    ) -> Dict[str, Any]:
        """
        Validate a specific key attribute against ESGVOC.

        For specific_key attributes, we need to validate the value against the specific field
        of terms in the collection (e.g., validate experiment description against experiment_id collection).

        :param attribute_name: Name of the attribute
        :param attribute: Attribute specification with specific_key
        :param attribute_value: The actual attribute value to validate
        :return: Validation result
        """
        try:
            specific_key = getattr(attribute, "specific_key", None)
            if not specific_key:
                return {
                    "attribute_name": attribute_name,
                    "validation_method": "specific_key_lookup",
                    "is_valid": False,
                    "error": "No specific_key defined in attribute specification",
                }

            value_str = str(attribute_value).strip()

            # Get all terms from the source collection
            all_terms = projects.get_all_terms_in_collection(
                project_id=self.project_id,
                collection_id=attribute.source_collection,
                selected_term_fields=None,
            )

            # Check if the value matches the specific_key field of any term
            found_match = False
            matched_terms = []
            available_values = []
            available_terms_full = []

            for term in all_terms:
                # Access the specific field from the term
                term_dict = term.model_dump()
                specific_value = term_dict.get(specific_key)

                if specific_value:
                    available_values.append(str(specific_value))
                    # Check if the specific value matches our attribute value
                    if str(specific_value).strip() == value_str:
                        found_match = True
                        matched_terms.append({"term_id": term.id, "specific_value": specific_value})

            # Get a few full term examples for error reporting
            if not found_match and all_terms:
                available_terms_full = [term.model_dump() for term in all_terms[:3]]

            return {
                "attribute_name": attribute_name,
                "source_collection": attribute.source_collection,
                "specific_key": specific_key,
                "value_type": attribute.value_type,
                "validation_method": "specific_key_lookup",
                "is_valid": found_match,
                "actual_value": value_str,
                "matching_terms": matched_terms,
                "available_examples": list(set(available_values))[:3],  # Unique values, limited to 3
                "available_terms_full": available_terms_full,
                "total_available": len(set(available_values)),
            }

        except (EsgvocNotFoundError, EsgvocDbError) as e:
            return {
                "attribute_name": attribute_name,
                "source_collection": attribute.source_collection,
                "specific_key": getattr(attribute, "specific_key", None),
                "validation_method": "specific_key_lookup",
                "is_valid": False,
                "error": str(e),
                "error_type": type(e).__name__,
            }


class GlobalAttributeValidator:
    """
    Main validator class for NetCDF global attributes.
    """

    def __init__(self, attribute_specs: AttributeSpecification, project_id: str = "cmip6"):
        """
        Initialize the validator with attribute specifications.

        :param attribute_specs: Global attribute specifications (list of AttributeProperty)
        :param project_id: Project identifier
        """
        self.attribute_specs = attribute_specs
        self.project_id = project_id
        self.esgvoc_validator = ESGVocAttributeValidator(project_id)

    def _get_field_name(self, spec: AttributeProperty) -> str:
        """Get the effective field name for an AttributeProperty."""
        return spec.field_name or spec.source_collection

    def _get_spec_by_field_name(self, field_name: str) -> Optional[AttributeProperty]:
        """Find an AttributeProperty by its field name."""
        for spec in self.attribute_specs:
            if self._get_field_name(spec) == field_name:
                return spec
        return None

    def validate(self, global_attributes: NetCDFGlobalAttributes, filename: Optional[str] = None) -> ValidationReport:
        """
        Validate global attributes against specifications.

        :param global_attributes: NetCDF global attributes to validate
        :param filename: Optional filename for reporting
        :return: Validation report
        """
        report = ValidationReport(filename=filename, project_id=self.project_id, is_valid=True)

        # Check for missing required attributes
        self._check_missing_attributes(global_attributes, report)

        # Validate present attributes
        self._validate_present_attributes(global_attributes, report)

        # Check for extra attributes
        self._check_extra_attributes(global_attributes, report)

        return report

    def _check_missing_attributes(self, global_attributes: NetCDFGlobalAttributes, report: ValidationReport) -> None:
        """Check for missing required attributes."""
        for spec in self.attribute_specs:
            field_name = self._get_field_name(spec)
            if spec.is_required and not global_attributes.has_attribute(field_name):
                report.missing_attributes.append(field_name)
                report.add_issue(
                    ValidationIssue(
                        attribute_name=field_name,
                        severity=ValidationSeverity.ERROR,
                        message=f"Required attribute '{field_name}' is missing",
                        source_collection=spec.source_collection,
                    )
                )

    def _validate_present_attributes(self, global_attributes: NetCDFGlobalAttributes, report: ValidationReport) -> None:
        """Validate attributes that are present."""
        for attr_name in global_attributes.list_attributes():
            spec = self._get_spec_by_field_name(attr_name)
            if spec is not None:
                attr_value = global_attributes.get_attribute(attr_name)

                # Validate value type
                self._validate_value_type(attr_name, attr_value, spec, report)

                # Use visitor pattern for ESGVOC validation
                if spec.specific_key is not None:
                    validation_result = self.esgvoc_validator.visit_specific_attribute(attr_name, spec, attr_value)
                else:
                    validation_result = self.esgvoc_validator.visit_base_attribute(attr_name, spec, attr_value)

                # Process validation result and add any issues to report
                self._process_esgvoc_validation_result(validation_result, report)

                # If validation passes, add to validated attributes
                if not any(
                    issue.attribute_name == attr_name and issue.severity == ValidationSeverity.ERROR
                    for issue in report.issues
                ):
                    report.validated_attributes[attr_name] = attr_value
                    report.mapping_used[attr_name] = str(attr_value)

    def _check_extra_attributes(self, global_attributes: NetCDFGlobalAttributes, report: ValidationReport) -> None:
        """Check for extra attributes not in specifications."""
        for attr_name in global_attributes.list_attributes():
            if self._get_spec_by_field_name(attr_name) is None:
                report.extra_attributes.append(attr_name)
                report.add_issue(
                    ValidationIssue(
                        attribute_name=attr_name,
                        severity=ValidationSeverity.INFO,
                        message=f"Extra attribute '{attr_name}' not defined in specifications",
                        actual_value=global_attributes.get_attribute(attr_name),
                    )
                )

    def _validate_value_type(
        self, attr_name: str, value: Any, spec: AttributeProperty, report: ValidationReport
    ) -> None:
        """Validate the type of an attribute value."""
        expected_type = spec.value_type

        # Type validation logic
        type_valid = False

        if expected_type == "string":
            type_valid = isinstance(value, str)
        elif expected_type == "integer":
            type_valid = isinstance(value, int)
        elif expected_type == "float":
            type_valid = isinstance(value, (int, float))

        if not type_valid:
            report.add_issue(
                ValidationIssue(
                    attribute_name=attr_name,
                    severity=ValidationSeverity.ERROR,
                    message=f"Attribute '{attr_name}' has incorrect type. Expected {expected_type}, got {type(value).__name__}",
                    expected_value=expected_type,
                    actual_value=type(value).__name__,
                    source_collection=spec.source_collection,
                )
            )

    def _process_esgvoc_validation_result(self, validation_result: Dict[str, Any], report: ValidationReport) -> None:
        """Process the result from ESGVOC validation and add issues to report."""
        attr_name = validation_result.get("attribute_name")
        is_valid = validation_result.get("is_valid", False)

        if not is_valid:
            severity = ValidationSeverity.ERROR
            error_msg = validation_result.get("error")
            actual_value = validation_result.get("actual_value", "N/A")

            if error_msg:
                # Error during validation (e.g., collection not found)
                error_type = validation_result.get("error_type", "ValidationError")
                message = f"ESGVOC validation failed for '{attr_name}' (value: '{actual_value}'): {error_msg}"
            else:
                # Value not found in controlled vocabulary
                source_collection = validation_result.get("source_collection")
                validation_method = validation_result.get("validation_method")

                if validation_method == "specific_key_lookup":
                    specific_key = validation_result.get("specific_key")
                    message = (
                        f"Value '{actual_value}' not found in controlled vocabulary. "
                        f"Looking for '{specific_key}' field in collection '{source_collection}'"
                    )
                else:
                    message = f"Value '{actual_value}' not found in controlled vocabulary '{source_collection}'"

                # Add available examples with full term information
                available_terms_full = validation_result.get("available_terms_full", [])
                if available_terms_full:
                    message += f"\n\nExample valid terms (showing {len(available_terms_full)}):"
                    for i, term in enumerate(available_terms_full, 1):
                        term_id = term.get("id", "N/A")
                        term_type = term.get("type", "N/A")
                        message += f"\n  {i}. ID: '{term_id}' (type: {term_type})"

                        # Show relevant fields based on validation method
                        if validation_method == "specific_key_lookup":
                            specific_key = validation_result.get("specific_key")
                            specific_value = term.get(specific_key, "N/A")
                            message += f"\n     {specific_key}: '{specific_value}'"

                        # Show a few other useful fields
                        for field in ["drs_name", "description", "name"]:
                            if field in term and term[field]:
                                message += f"\n     {field}: '{term[field]}'"
                        message += "\n"

            report.add_issue(
                ValidationIssue(
                    attribute_name=attr_name,
                    severity=severity,
                    message=message,
                    expected_value=validation_result.get("available_examples"),
                    actual_value=actual_value,
                    source_collection=validation_result.get("source_collection"),
                )
            )


class ValidatorFactory:
    """
    Factory class for creating validators with different configurations.
    """

    @staticmethod
    def create_from_yaml_file(yaml_file_path: str, project_id: str = "cmip6") -> GlobalAttributeValidator:
        """
        Create validator from YAML configuration file.

        :param yaml_file_path: Path to YAML configuration file
        :param project_id: Project identifier
        :return: Configured GlobalAttributeValidator
        """
        import yaml

        with open(yaml_file_path, "r") as f:
            yaml_data = yaml.safe_load(f)

        # Parse YAML data into list of AttributeProperty
        if isinstance(yaml_data, list):
            attribute_specs = [AttributeProperty(**item) for item in yaml_data]
        elif isinstance(yaml_data, dict) and "specs" in yaml_data:
            # Legacy dict format support
            if isinstance(yaml_data["specs"], list):
                attribute_specs = [AttributeProperty(**item) for item in yaml_data["specs"]]
            else:
                # Old dict-based format - convert to list
                specs_list = []
                for attr_name, attr_config in yaml_data["specs"].items():
                    spec_data = {
                        "source_collection": attr_config.get("source_collection"),
                        "is_required": attr_config.get("required", True),
                        "value_type": attr_config.get("value_type", "string"),
                    }
                    if attr_name != attr_config.get("source_collection"):
                        spec_data["field_name"] = attr_name
                    if "specific_key" in attr_config:
                        spec_data["specific_key"] = attr_config["specific_key"]
                    if "default_value" in attr_config:
                        spec_data["default_value"] = attr_config["default_value"]
                    specs_list.append(AttributeProperty(**spec_data))
                attribute_specs = specs_list
        else:
            raise ValueError(f"Unsupported YAML format: {type(yaml_data)}")

        return GlobalAttributeValidator(attribute_specs, project_id)


"""
Pydantic models for global attribute specifications.

This module defines the models used to represent and validate global attribute
specifications loaded from YAML configuration files.
"""

from enum import Enum
from typing import Any, Optional, Protocol
from pydantic import Field

from esgvoc.api.data_descriptors.data_descriptor import ConfiguredBaseModel


class GlobalAttributeValueType(str, Enum):
    """
    The types of global attribute values.
    """

    STRING = "string"
    """String value type."""
    INTEGER = "integer"
    """Integer value type."""
    FLOAT = "float"
    """Float value type."""


class GlobalAttributeVisitor(Protocol):
    """
    Specifications for a global attribute visitor.
    """

    def visit_base_attribute(self, attribute_name: str, attribute: "GlobalAttributeSpecBase") -> Any:
        """Visit a base global attribute."""
        pass

    def visit_specific_attribute(self, attribute_name: str, attribute: "GlobalAttributeSpecSpecific") -> Any:
        """Visit a specific global attribute."""
        pass


class GlobalAttributeSpecBase(ConfiguredBaseModel):
    """
    Specification for a global attribute.
    """

    source_collection: str = Field(..., description="The source_collection to get the term from")
    value_type: GlobalAttributeValueType = Field(..., description="The expected value type")
    required: bool = Field(default=True, description="Whether this attribute is required")
    description: Optional[str] = Field(default=None, description="Description of the attribute")
    default_value: Optional[str] = Field(default=None, description="Default value if not provided")

    def accept(self, attribute_name: str, visitor: GlobalAttributeVisitor) -> Any:
        return visitor.visit_base_attribute(attribute_name, self)


class GlobalAttributeSpecSpecific(GlobalAttributeSpecBase):
    """
    Specification for a global attribute with a specific key.

    This is used when the validation is for the value of a specific key,
    for instance 'description' or 'ui-label' from a controlled vocabulary term.
    """

    specific_key: str = Field(..., description="The specific key to extract from the term")

    def accept(self, attribute_name: str, visitor: GlobalAttributeVisitor) -> Any:
        """
        Accept a global attribute visitor.

        :param attribute_name: The attribute name.
        :param visitor: The global attribute visitor.
        :type visitor: GlobalAttributeVisitor
        :return: Depending on the visitor.
        :rtype: Any
        """
        return visitor.visit_specific_attribute(attribute_name, self)


# Union type for any global attribute spec
GlobalAttributeSpec = GlobalAttributeSpecSpecific | GlobalAttributeSpecBase


class GlobalAttributeSpecs(ConfiguredBaseModel):
    """
    Container for global attribute specifications.
    """

    specs: dict[str, GlobalAttributeSpec] = Field(default_factory=dict)
    """The global attributes specifications dictionary."""

    def __str__(self) -> str:
        """Return all keys when printing."""
        return str(list(self.specs.keys()))

    def __repr__(self) -> str:
        """Return all keys when using repr."""
        return f"GlobalAttributeSpecs(keys={list(self.specs.keys())})"

    # Dictionary-like access methods
    def __getitem__(self, key: str) -> GlobalAttributeSpec:
        return self.specs[key]

    def __setitem__(self, key: str, value: GlobalAttributeSpec) -> None:
        self.specs[key] = value

    def __contains__(self, key: str) -> bool:
        return key in self.specs

    def keys(self):
        return self.specs.keys()

    def values(self):
        return self.specs.values()

    def items(self):
        return self.specs.items()

    @classmethod
    def from_yaml_dict(cls, yaml_data: dict[str, Any]) -> "GlobalAttributeSpecs":
        """
        Create GlobalAttributeSpecs from YAML configuration data.

        :param yaml_data: Dictionary loaded from YAML file
        :return: GlobalAttributeSpecs instance
        """
        specs_dict = {}

        for attr_name, attr_config in yaml_data.get("specs", {}).items():
            # Check if this is a specific key attribute
            if "specific_key" in attr_config:
                spec = GlobalAttributeSpecSpecific(**attr_config)
            else:
                spec = GlobalAttributeSpecBase(**attr_config)

            specs_dict[attr_name] = spec

        return cls(specs=specs_dict)


class ValueTypeDefinition(ConfiguredBaseModel):
    """
    Definition for a value type.
    """

    description: str = Field(..., description="Description of the value type")
    validation: str = Field(..., description="Validation method for this type")


class ValidationRules(ConfiguredBaseModel):
    """
    Validation rules for global attributes.
    """

    required_attributes: list[str] = Field(default_factory=list, description="List of required attributes")
    optional_attributes: list[str] = Field(default_factory=list, description="List of optional attributes")
    specific_key_attributes: list[str] = Field(default_factory=list, description="Attributes using specific_key lookup")


class AttributeSpecsConfig(ConfiguredBaseModel):
    """
    Complete configuration model for attribute specifications.
    """

    project_id: str = Field(..., description="Project identifier")
    description: str = Field(..., description="Configuration description")
    specs: dict[str, dict[str, Any]] = Field(..., description="Attribute specifications")
    value_types: dict[str, ValueTypeDefinition] = Field(default_factory=dict)
    validation_rules: ValidationRules = Field(default_factory=ValidationRules)
    patterns: dict[str, str] = Field(default_factory=dict, description="Regex patterns for validation")

    def to_global_attribute_specs(self) -> GlobalAttributeSpecs:
        """Convert to GlobalAttributeSpecs object."""
        return GlobalAttributeSpecs.from_yaml_dict({"specs": self.specs})


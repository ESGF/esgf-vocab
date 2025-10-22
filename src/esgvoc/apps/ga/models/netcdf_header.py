"""
Models for parsing and validating NetCDF headers.

This module provides Pydantic models to parse NetCDF header information
and validate global attributes against project specifications.
"""

import re
from typing import Any, Union, Optional, Dict, List
from pydantic import BaseModel, Field, field_validator, ValidationError

from esgvoc.api.data_descriptors.data_descriptor import ConfiguredBaseModel


class NetCDFDimension(ConfiguredBaseModel):
    """
    Represents a NetCDF dimension.
    """

    name: str = Field(..., description="Dimension name")
    size: Union[int, str] = Field(..., description="Dimension size (int or 'UNLIMITED')")
    is_unlimited: bool = Field(default=False, description="Whether this is an unlimited dimension")

    @field_validator("is_unlimited", mode="before")
    @classmethod
    def check_unlimited(cls, v, info):
        """Check if dimension is unlimited based on size."""
        if info.data.get("size") == "UNLIMITED":
            return True
        return v


class NetCDFVariable(ConfiguredBaseModel):
    """
    Represents a NetCDF variable with its attributes.
    """

    name: str = Field(..., description="Variable name")
    dimensions: List[str] = Field(default_factory=list, description="Variable dimensions")
    data_type: str = Field(..., description="Variable data type (e.g., float, double)")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Variable attributes")


class NetCDFGlobalAttributes(ConfiguredBaseModel):
    """
    Container for NetCDF global attributes.
    """

    attributes: Dict[str, Union[str, int, float, List[Any]]] = Field(
        default_factory=dict, description="Dictionary of global attributes"
    )

    def get_attribute(self, name: str) -> Optional[Any]:
        """
        Get a global attribute by name.

        :param name: Attribute name
        :return: Attribute value or None if not found
        """
        return self.attributes.get(name)

    def get_string_attribute(self, name: str) -> Optional[str]:
        """
        Get a global attribute as string.

        :param name: Attribute name
        :return: Attribute value as string or None if not found
        """
        value = self.get_attribute(name)
        return str(value) if value is not None else None

    def has_attribute(self, name: str) -> bool:
        """
        Check if global attribute exists.

        :param name: Attribute name
        :return: True if attribute exists
        """
        return name in self.attributes

    def list_attributes(self) -> List[str]:
        """
        List all global attribute names.

        :return: List of attribute names
        """
        return list(self.attributes.keys())


class NetCDFHeader(ConfiguredBaseModel):
    """
    Complete NetCDF header information including dimensions, variables, and global attributes.
    """

    filename: Optional[str] = Field(default=None, description="NetCDF filename")
    dimensions: Dict[str, NetCDFDimension] = Field(default_factory=dict, description="File dimensions")
    variables: Dict[str, NetCDFVariable] = Field(default_factory=dict, description="File variables")
    global_attributes: NetCDFGlobalAttributes = Field(
        default_factory=NetCDFGlobalAttributes, description="Global attributes"
    )

    @classmethod
    def from_ncdump_output(cls, ncdump_output: str) -> "NetCDFHeader":
        """
        Parse NetCDF header from ncdump command output.

        :param ncdump_output: Output from ncdump -h command
        :return: NetCDFHeader instance
        """
        lines = ncdump_output.strip().split("\n")

        # Extract filename from first line (e.g., "netcdf tas_Amon_CanESM5_historical_r11i1p1f1_gn_185001-201412 {")
        filename_match = re.match(r"netcdf\s+(.+?)\s*\{", lines[0])
        filename = filename_match.group(1) if filename_match else None

        dimensions = {}
        variables = {}
        global_attributes = {}

        current_section = None
        current_variable = None
        current_variable_info = {}

        for line in lines[1:]:
            line = line.strip()

            if not line or line == "}":
                continue

            # Section headers
            if line.startswith("dimensions:"):
                current_section = "dimensions"
                continue
            elif line.startswith("variables:"):
                current_section = "variables"
                continue
            elif line.startswith("// global attributes:"):
                current_section = "global_attributes"
                continue
            elif line.startswith("data:"):
                break  # We don't need data section

            # Parse based on current section
            if current_section == "dimensions":
                cls._parse_dimension_line(line, dimensions)
            elif current_section == "variables":
                result = cls._parse_variable_line(line, variables, current_variable, current_variable_info)
                if result:
                    current_variable, current_variable_info = result
            elif current_section == "global_attributes":
                cls._parse_global_attribute_line(line, global_attributes)

        return cls(
            filename=filename,
            dimensions=dimensions,
            variables=variables,
            global_attributes=NetCDFGlobalAttributes(attributes=global_attributes),
        )

    @staticmethod
    def _parse_dimension_line(line: str, dimensions: Dict[str, NetCDFDimension]):
        """Parse a dimension line from ncdump output."""
        # e.g., "time = UNLIMITED ; // (1980 currently)"
        # e.g., "lat = 64 ;"
        match = re.match(r"\s*(\w+)\s*=\s*(.+?)\s*;", line)
        if match:
            dim_name = match.group(1)
            dim_size_str = match.group(2).split("//")[0].strip()

            if dim_size_str == "UNLIMITED":
                dimensions[dim_name] = NetCDFDimension(name=dim_name, size="UNLIMITED", is_unlimited=True)
            else:
                try:
                    size = int(dim_size_str)
                    dimensions[dim_name] = NetCDFDimension(name=dim_name, size=size)
                except ValueError:
                    pass  # Skip malformed dimension lines

    @staticmethod
    def _parse_variable_line(
        line: str, variables: Dict[str, NetCDFVariable], current_variable: Optional[str], current_variable_info: Dict
    ) -> Optional[tuple]:
        """Parse a variable line from ncdump output."""
        # Variable declaration: "double time(time) ;"
        var_decl_match = re.match(r"\s*(\w+)\s+(\w+)\s*\(([^)]*)\)\s*;", line)
        if var_decl_match:
            data_type = var_decl_match.group(1)
            var_name = var_decl_match.group(2)
            dimensions_str = var_decl_match.group(3)

            dimensions_list = [d.strip() for d in dimensions_str.split(",") if d.strip()]

            variables[var_name] = NetCDFVariable(
                name=var_name, data_type=data_type, dimensions=dimensions_list, attributes={}
            )

            return var_name, {}

        # Variable attribute: "time:units = "days since 1850-01-01 0:0:0.0" ;"
        attr_match = re.match(r"\s*(\w+):(\w+)\s*=\s*(.+?)\s*;", line)
        if attr_match and current_variable:
            var_name = attr_match.group(1)
            attr_name = attr_match.group(2)
            attr_value = attr_match.group(3).strip()

            # Remove quotes if present
            if attr_value.startswith('"') and attr_value.endswith('"'):
                attr_value = attr_value[1:-1]

            # Try to convert to appropriate type
            try:
                if "." in attr_value or "e" in attr_value.lower():
                    attr_value = float(attr_value)
                elif attr_value.isdigit() or (attr_value.startswith("-") and attr_value[1:].isdigit()):
                    attr_value = int(attr_value)
            except ValueError:
                pass  # Keep as string

            if var_name in variables:
                variables[var_name].attributes[attr_name] = attr_value

        return current_variable, current_variable_info

    @staticmethod
    def _parse_global_attribute_line(line: str, global_attributes: Dict[str, Any]):
        """Parse a global attribute line from ncdump output."""
        # e.g., ':Conventions = "CF-1.7 CMIP-6.2" ;'
        # e.g., ':forcing_index = 1 ;'
        match = re.match(r"\s*:(\w+)\s*=\s*(.+?)\s*;", line)
        if match:
            attr_name = match.group(1)
            attr_value = match.group(2).strip()

            # Handle multiline strings
            if attr_value.startswith('"') and not attr_value.endswith('"'):
                # This is a multiline string, we'd need to handle continuation
                attr_value = attr_value[1:]  # Remove starting quote
            elif attr_value.startswith('"') and attr_value.endswith('"'):
                attr_value = attr_value[1:-1]  # Remove both quotes

            # Try to convert to appropriate type
            try:
                if (
                    attr_value.replace(".", "")
                    .replace("-", "")
                    .replace("e", "")
                    .replace("E", "")
                    .replace("+", "")
                    .isdigit()
                ):
                    if "." in attr_value or "e" in attr_value.lower() or "E" in attr_value:
                        attr_value = float(attr_value)
                    else:
                        attr_value = int(attr_value)
            except (ValueError, AttributeError):
                pass  # Keep as string

            global_attributes[attr_name] = attr_value


class NetCDFHeaderParser:
    """
    Utility class for parsing NetCDF headers from various sources.
    """

    @staticmethod
    def parse_from_ncdump(ncdump_output: str) -> NetCDFHeader:
        """
        Parse NetCDF header from ncdump command output.

        :param ncdump_output: Output from ncdump -h command
        :return: NetCDFHeader instance
        """
        return NetCDFHeader.from_ncdump_output(ncdump_output)

    @staticmethod
    def parse_from_file(filepath: str) -> NetCDFHeader:
        """
        Parse NetCDF header directly from file using netCDF4 library.

        Note: This is a placeholder for future implementation.
        """
        raise NotImplementedError("Direct NetCDF file parsing not yet implemented")

    @staticmethod
    def validate_ncdump_format(ncdump_output: str) -> bool:
        """
        Validate that the input looks like valid ncdump output.

        :param ncdump_output: String to validate
        :return: True if format looks valid
        """
        lines = ncdump_output.strip().split("\n")
        if not lines:
            return False

        # Check for netcdf header
        if not lines[0].strip().startswith("netcdf "):
            return False

        # Check for required sections
        has_dimensions = any("dimensions:" in line for line in lines)
        has_global_attrs = any("// global attributes:" in line for line in lines)

        return has_dimensions or has_global_attrs


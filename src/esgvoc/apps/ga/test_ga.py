"""
Tests for the GA (Global Attributes) validator.

Run with: python -m pytest src/esgvoc/apps/ga/test_ga.py
"""

import pytest

from esgvoc.api.project_specs import AttributeProperty, AttributeSpecification
from .models import (
    NetCDFHeaderParser,
    ValidationSeverity,
)
from .validator import GAValidator


class TestNetCDFHeaderParser:
    """Test the NetCDF header parser."""

    def test_parse_simple_header(self):
        """Test parsing a simple NetCDF header."""
        ncdump_output = """netcdf test_file {
dimensions:
    time = UNLIMITED ; // (12 currently)
    lat = 180 ;
    lon = 360 ;
variables:
    double time(time) ;
        time:units = "days since 1850-01-01" ;
        time:calendar = "gregorian" ;

// global attributes:
        :Conventions = "CF-1.7" ;
        :title = "Test NetCDF file" ;
        :institution = "Test Institution" ;
}"""

        header = NetCDFHeaderParser.parse_from_ncdump(ncdump_output)

        assert header.filename == "test_file"
        assert len(header.dimensions) == 3
        assert "time" in header.dimensions
        assert header.dimensions["time"].is_unlimited
        assert header.dimensions["lat"].size == 180

        assert len(header.variables) == 1
        assert "time" in header.variables
        assert header.variables["time"].data_type == "double"

        assert len(header.global_attributes.attributes) == 3
        assert header.global_attributes.get_attribute("Conventions") == "CF-1.7"
        assert header.global_attributes.get_attribute("title") == "Test NetCDF file"
        assert header.global_attributes.has_attribute("institution")


class TestGAValidator:
    """Test the GA validator."""

    def test_validator_initialization(self):
        """Test validator initialization from database."""
        validator = GAValidator(project_id="cmip6")
        assert validator.project_id == "cmip6"
        assert validator.attribute_specs is not None

    def test_validation_with_simple_attributes(self):
        """Test validation with a simple attributes dictionary."""
        validator = GAValidator(project_id="cmip6")

        # Test with minimal required attributes
        attributes = {
            "Conventions": "CF-1.7 CMIP-6.2",
            "activity_id": "CMIP",
            "creation_date": "2019-04-30T17:44:13Z",
            "data_specs_version": "01.00.29",
            "experiment_id": "historical",
            "forcing_index": 1,
            "frequency": "mon",
            "grid_label": "gn",
            "initialization_index": 1,
            "institution_id": "CCCma",
            "mip_era": "CMIP6",
            "nominal_resolution": "500 km",
            "physics_index": 1,
            "realization_index": 11,
            "source_id": "CanESM5",
            "table_id": "Amon",
            "tracking_id": "hdl:21.14100/3a32f67e-ae59-40d8-ae4a-2e03e922fe8e",
            "variable_id": "tas",
            "variant_label": "r11i1p1f1",
        }

        report = validator.validate_from_attributes_dict(attributes, "test.nc")

        # Basic checks
        assert report is not None
        assert report.project_id == "cmip6"
        assert report.filename == "test.nc"
        assert isinstance(report.is_valid, bool)
        assert isinstance(report.issues, list)
        assert isinstance(report.error_count, int)
        assert isinstance(report.warning_count, int)

    def test_get_required_attributes(self):
        """Test getting required attributes list."""
        validator = GAValidator(project_id="cmip6")
        required_attrs = validator.get_required_attributes()

        assert isinstance(required_attrs, list)
        assert len(required_attrs) > 0

        # Should include some standard CMIP6 required attributes
        expected_attrs = ["Conventions", "activity_id", "experiment_id", "variable_id"]
        for attr in expected_attrs:
            if attr in validator.list_attributes():
                # Only check if the attribute is defined in the specs
                info = validator.get_attribute_info(attr)
                if info and info.get("required"):
                    assert attr in required_attrs

    def test_attribute_info(self):
        """Test getting attribute information."""
        validator = GAValidator(project_id="cmip6")

        # Test with a common attribute
        if "activity_id" in validator.list_attributes():
            info = validator.get_attribute_info("activity_id")
            assert info is not None
            assert "name" in info
            assert "source_collection" in info
            assert "value_type" in info
            assert "required" in info

        # Test with non-existent attribute
        info = validator.get_attribute_info("non_existent_attribute")
        assert info is None


if __name__ == "__main__":
    # Run basic tests when executed directly
    print("Running basic GA validator tests...")

    # Test 1: Parse NetCDF header
    print("Test 1: NetCDF header parsing")
    test = TestNetCDFHeaderParser()
    try:
        test.test_parse_simple_header()
        print("  ✓ PASSED")
    except Exception as e:
        print(f"  ✗ FAILED: {e}")

    # Test 2: Validator initialization
    print("Test 2: Validator initialization")
    test_validator = TestGAValidator()
    try:
        test_validator.test_validator_initialization()
        print("  ✓ PASSED")
    except Exception as e:
        print(f"  ✗ FAILED: {e}")

    print("Basic tests completed!")


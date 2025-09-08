"""
Tests for the GA (Global Attributes) validator.

Run with: python -m pytest src/esgvoc/apps/ga/test_ga.py
"""

import pytest
from pathlib import Path

from .models import (
    NetCDFHeaderParser,
    ValidationSeverity,
    AttributeSpecsConfig,
    GlobalAttributeSpecs,
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


class TestAttributeSpecsConfig:
    """Test the attribute specifications configuration."""

    def test_load_default_config(self):
        """Test loading the default YAML configuration."""
        config_path = Path(__file__).parent / "attributes_specs.yaml"

        if config_path.exists():
            import yaml

            with open(config_path, "r") as f:
                yaml_data = yaml.safe_load(f)

            config = AttributeSpecsConfig(**yaml_data)
            assert config.project_id == "cmip6"
            assert "specs" in yaml_data
            assert len(config.specs) > 0

            # Test conversion to GlobalAttributeSpecs
            ga_specs = config.to_global_attribute_specs()
            assert isinstance(ga_specs, GlobalAttributeSpecs)
            assert len(ga_specs.specs) > 0
        else:
            pytest.skip("Configuration file not found")


class TestGAValidator:
    """Test the GA validator."""

    def test_validator_initialization(self):
        """Test validator initialization with default config."""
        try:
            validator = GAValidator(project_id="cmip6")
            assert validator.project_id == "cmip6"
            assert validator.attribute_specs is not None
        except FileNotFoundError:
            pytest.skip("Default configuration file not found")

    def test_validation_with_simple_attributes(self):
        """Test validation with a simple attributes dictionary."""
        try:
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

        except FileNotFoundError:
            pytest.skip("Default configuration file not found")

    def test_get_required_attributes(self):
        """Test getting required attributes list."""
        try:
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

        except FileNotFoundError:
            pytest.skip("Default configuration file not found")

    def test_attribute_info(self):
        """Test getting attribute information."""
        try:
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

        except FileNotFoundError:
            pytest.skip("Default configuration file not found")


def test_yaml_config_syntax():
    """Test that the YAML configuration file has valid syntax."""
    config_path = Path(__file__).parent / "attributes_specs.yaml"

    if config_path.exists():
        import yaml

        with open(config_path, "r") as f:
            yaml_data = yaml.safe_load(f)

        # Basic structure checks
        assert isinstance(yaml_data, dict)
        assert "project_id" in yaml_data
        assert "specs" in yaml_data
        assert isinstance(yaml_data["specs"], dict)

        # Check that each spec has required fields
        for attr_name, attr_spec in yaml_data["specs"].items():
            assert isinstance(attr_name, str)
            assert isinstance(attr_spec, dict)
            assert "source_collection" in attr_spec
            assert "value_type" in attr_spec
            assert attr_spec["value_type"] in ["string", "integer", "float"]

    else:
        pytest.skip("Configuration file not found")


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

    # Test 2: YAML config
    print("Test 2: YAML configuration")
    try:
        test_yaml_config_syntax()
        print("  ✓ PASSED")
    except Exception as e:
        print(f"  ✗ FAILED: {e}")

    # Test 3: Validator initialization
    print("Test 3: Validator initialization")
    test_validator = TestGAValidator()
    try:
        test_validator.test_validator_initialization()
        print("  ✓ PASSED")
    except Exception as e:
        print(f"  ✗ FAILED: {e}")

    print("Basic tests completed!")


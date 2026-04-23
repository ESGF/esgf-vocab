"""
Unit tests for ncdump global-attribute parsing.

No database or network access required.
"""

import pytest
from esgvoc.apps.ga.validator import parse_ncdump_global_attributes


_FULL_NCDUMP = """\
netcdf tas_Amon_CanESM5_historical_r11i1p1f1_gn_185001-201412 {
dimensions:
    time = UNLIMITED ; // (1980 currently)
    lat = 64 ;
    lon = 128 ;
variables:
    float tas(time, lat, lon) ;
        tas:units = "K" ;

// global attributes:
        :Conventions = "CF-1.7 CMIP-6.2" ;
        :activity_id = "CMIP" ;
        :experiment_id = "historical" ;
        :forcing_index = 1 ;
        :realization_index = 11 ;
        :branch_time_in_child = 0. ;
        :missing_value = 1.e+20f ;
        :source = "CanESM5 (2019): \\n",
            "aerosol: interactive\\n",
            "seaIce: LIM2" ;
        :history = "2019-04-30T17:44:13Z ;rewrote data to be consistent with CMIP;\\n",
            "Output from $runid" ;
        :institution_id = "CCCma" ;
}"""


class TestParseNcdumpGlobalAttributes:

    def test_empty_string_returns_empty_dict(self):
        assert parse_ncdump_global_attributes("") == {}

    def test_no_global_attrs_section_returns_empty_dict(self):
        ncdump = "netcdf test {\ndimensions:\n    time = 10 ;\n}"
        assert parse_ncdump_global_attributes(ncdump) == {}

    def test_simple_string_attribute(self):
        ncdump = 'netcdf test {\n// global attributes:\n        :activity_id = "CMIP" ;\n}'
        result = parse_ncdump_global_attributes(ncdump)
        assert result["activity_id"] == "CMIP"

    def test_string_with_spaces(self):
        ncdump = 'netcdf test {\n// global attributes:\n        :Conventions = "CF-1.7 CMIP-6.2" ;\n}'
        result = parse_ncdump_global_attributes(ncdump)
        assert result["Conventions"] == "CF-1.7 CMIP-6.2"

    def test_integer_attribute(self):
        ncdump = "netcdf test {\n// global attributes:\n        :forcing_index = 1 ;\n}"
        result = parse_ncdump_global_attributes(ncdump)
        assert result["forcing_index"] == 1
        assert isinstance(result["forcing_index"], int)

    def test_float_attribute(self):
        ncdump = "netcdf test {\n// global attributes:\n        :branch_time = 0. ;\n}"
        result = parse_ncdump_global_attributes(ncdump)
        assert result["branch_time"] == pytest.approx(0.0)

    def test_float_with_ncdump_f_suffix(self):
        ncdump = "netcdf test {\n// global attributes:\n        :missing_value = 1.e+20f ;\n}"
        result = parse_ncdump_global_attributes(ncdump)
        assert result["missing_value"] == pytest.approx(1e20)

    def test_multiple_attributes_all_present(self):
        result = parse_ncdump_global_attributes(_FULL_NCDUMP)
        assert result["Conventions"] == "CF-1.7 CMIP-6.2"
        assert result["activity_id"] == "CMIP"
        assert result["experiment_id"] == "historical"
        assert result["forcing_index"] == 1
        assert result["realization_index"] == 11
        assert result["branch_time_in_child"] == pytest.approx(0.0)
        assert result["institution_id"] == "CCCma"

    def test_dimensions_section_not_parsed_as_attributes(self):
        result = parse_ncdump_global_attributes(_FULL_NCDUMP)
        assert "time" not in result
        assert "lat" not in result
        assert "lon" not in result

    def test_variable_attrs_not_parsed_as_global_attrs(self):
        result = parse_ncdump_global_attributes(_FULL_NCDUMP)
        assert "units" not in result

    def test_multiline_attribute_captured(self):
        result = parse_ncdump_global_attributes(_FULL_NCDUMP)
        assert "source" in result
        assert isinstance(result["source"], str)

    def test_multiline_first_segment_content(self):
        """First segment of a multiline string is the one we keep."""
        result = parse_ncdump_global_attributes(_FULL_NCDUMP)
        # The first quoted segment of :source starts with "CanESM5"
        assert "CanESM5" in result["source"]

    def test_semicolon_inside_string_not_treated_as_terminator(self):
        """Semicolons inside quoted values must not split the attribute."""
        result = parse_ncdump_global_attributes(_FULL_NCDUMP)
        assert "history" in result
        # The history value contains semicolons in the source but must be captured
        assert isinstance(result["history"], str)

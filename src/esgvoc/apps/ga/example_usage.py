"""
Example usage of the GA (Global Attributes) validator.

This script demonstrates how to use the GA validator to validate NetCDF global attributes
against CMIP project specifications using the esgvoc API.
"""

import os
from pathlib import Path

from esgvoc.apps.ga.validator import GAValidator, validate_netcdf_attributes, create_validation_summary
from esgvoc.apps.ga.models import NetCDFHeaderParser


def example_validate_ncdump():
    """
    Example: Validate NetCDF global attributes from ncdump output.
    """
    # Sample ncdump output from the provided example
    ncdump_output = """netcdf tas_Amon_CanESM5_historical_r11i1p1f1_gn_185001-201412 {
dimensions:
    time = UNLIMITED ; // (1980 currently)
    bnds = 2 ;
    lat = 64 ;
    lon = 128 ;
variables:
    double time(time) ;
        time:bounds = "time_bnds" ;
        time:units = "days since 1850-01-01 0:0:0.0" ;
        time:calendar = "365_day" ;
        time:axis = "T" ;
        time:long_name = "time" ;
        time:standard_name = "time" ;
    double time_bnds(time, bnds) ;
    double lat(lat) ;
        lat:bounds = "lat_bnds" ;
        lat:units = "degrees_north" ;
        lat:axis = "Y" ;
        lat:long_name = "Latitude" ;
        lat:standard_name = "latitude" ;
    double lat_bnds(lat, bnds) ;
    double lon(lon) ;
        lon:bounds = "lon_bnds" ;
        lon:units = "degrees_east" ;
        lon:axis = "X" ;
        lon:long_name = "Longitude" ;
        lon:standard_name = "longitude" ;
    double lon_bnds(lon, bnds) ;
    double height ;
        height:units = "m" ;
        height:axis = "Z" ;
        height:positive = "up" ;
        height:long_name = "height" ;
        height:standard_name = "height" ;
    float tas(time, lat, lon) ;
        tas:standard_name = "air_temperature" ;
        tas:long_name = "Near-Surface Air Temperature" ;
        tas:comment = "ST+273.16, CMIP_table_comment: near-surface (usually, 2 meter) air temperature" ;
        tas:units = "K" ;
        tas:original_name = "ST" ;
        tas:history = "degctok 2019-04-30T17:44:13Z altered by CMOR: Treated scalar dimension: 'height'. 2019-04-30T17:44:13Z altered by CMOR: Reordered dimensions, original order: lat lon time. 2019-04-30T17:44:13Z altered by CMOR: replaced missing value flag (1e+38) with standard missing value (1e+20)." ;
        tas:cell_methods = "area: time: mean" ;
        tas:cell_measures = "area: areacella" ;
        tas:coordinates = "height" ;
        tas:missing_value = 1.e+20f ;
        tas:_FillValue = 1.e+20f ;

// global attributes:
        :CCCma_model_hash = "7e8e715f3f2ce47e1bab830db971c362ca329419" ;
        :CCCma_parent_runid = "rc3.1-pictrl" ;
        :CCCma_pycmor_hash = "33c30511acc319a98240633965a04ca99c26427e" ;
        :CCCma_runid = "rc3.1-his11" ;
        :Conventions = "CF-1.7 CMIP-6.2" ;
        :YMDH_branch_time_in_child = "1850:01:01:00" ;
        :YMDH_branch_time_in_parent = "5701:01:01:00" ;
        :activity_id = "CMIP" ;
        :branch_method = "Spin-up documentation" ;
        :branch_time_in_child = 0. ;
        :branch_time_in_parent = 1405615. ;
        :contact = "ec.cccma.info-info.ccmac.ec@canada.ca" ;
        :creation_date = "2019-04-30T17:44:13Z" ;
        :data_specs_version = "01.00.29" ;
        :experiment = "all-forcing simulation of the recent past" ;
        :experiment_id = "historical" ;
        :external_variables = "areacella" ;
        :forcing_index = 1 ;
        :frequency = "mon" ;
        :further_info_url = "https://furtherinfo.es-doc.org/CMIP6.CCCma.CanESM5.historical.none.r11i1p1f1" ;
        :grid = "T63L49 native atmosphere, T63 Linear Gaussian Grid; 128 x 64 longitude/latitude; 49 levels; top level 1 hPa" ;
        :grid_label = "gn" ;
        :history = "2019-04-30T17:44:13Z ;rewrote data to be consistent with CMIP for variable tas found in table Amon.;\n",
            "Output from $runid" ;
        :initialization_index = 1 ;
        :institution = "Canadian Centre for Climate Modelling and Analysis, Environment and Climate Change Canada, Victoria, BC V8P 5C2, Canada" ;
        :institution_id = "CCCma" ;
        :mip_era = "CMIP6" ;
        :nominal_resolution = "500 km" ;
        :parent_activity_id = "CMIP" ;
        :parent_experiment_id = "piControl" ;
        :parent_mip_era = "CMIP6" ;
        :parent_source_id = "CanESM5" ;
        :parent_time_units = "days since 1850-01-01 0:0:0.0" ;
        :parent_variant_label = "r1i1p1f1" ;
        :physics_index = 1 ;
        :product = "model-output" ;
        :realization_index = 11 ;
        :realm = "atmos" ;
        :references = "Geophysical Model Development Special issue on CanESM5 (https://www.geosci-model-dev.net/special_issues.html)" ;
        :source = "CanESM5 (2019): \\n",
            "aerosol: interactive\\n",
            "atmos: CanAM5 (T63L49 native atmosphere, T63 Linear Gaussian Grid; 128 x 64 longitude/latitude; 49 levels; top level 1 hPa)\\n",
            "atmosChem: specified oxidants for aerosols\\n",
            "land: CLASS3.6/CTEM1.2\\n",
            "landIce: specified ice sheets\\n",
            "ocean: NEMO3.4.1 (ORCA1 tripolar grid, 1 deg with refinement to 1/3 deg within 20 degrees of the equator; 361 x 290 longitude/latitude; 45 vertical levels; top grid cell 0-6.19 m)\\n",
            "ocnBgchem: Canadian Model of Ocean Carbon (CMOC); NPZD ecosystem with OMIP prescribed carbonate chemistry\\n",
            "seaIce: LIM2" ;
        :source_id = "CanESM5" ;
        :source_type = "AOGCM" ;
        :sub_experiment = "none" ;
        :sub_experiment_id = "none" ;
        :table_id = "Amon" ;
        :table_info = "Creation Date:(20 February 2019) MD5:374fbe5a2bcca535c40f7f23da271e49" ;
        :title = "CanESM5 output prepared for CMIP6" ;
        :tracking_id = "hdl:21.14100/3a32f67e-ae59-40d8-ae4a-2e03e922fe8e" ;
        :variable_id = "tas" ;
        :variant_label = "r11i1p1f1" ;
        :version = "v20190429" ;
        :license = "CMIP6 model data produced by The Government of Canada (Canadian Centre for Climate Modelling and Analysis, Environment and Climate Change Canada) is licensed under a Creative Commons Attribution ShareAlike 4.0 International License (https://creativecommons.org/licenses). Consult https://pcmdi.llnl.gov/CMIP6/TermsOfUse for terms of use governing CMIP6 output, including citation requirements and proper acknowledgment. Further information about this data, including some limitations, can be found via the further_info_url (recorded as a global attribute in this file) and at https:///pcmdi.llnl.gov/. The data producers and data providers make no warranty, either express or implied, including, but not limited to, warranties of merchantability and fitness for a particular purpose. All liabilities arising from the supply of the information (including any liability arising in negligence) are excluded to the fullest extent permitted by law." ;
        :cmor_version = "3.4.0" ;
}"""

    print("=== Example: Validating NetCDF Global Attributes ===")
    print()

    # Method 1: Using the convenience function
    print("Method 1: Using convenience function")
    report = validate_netcdf_attributes(
        ncdump_output=ncdump_output,
        project_id="cmip6",
        filename="tas_Amon_CanESM5_historical_r11i1p1f1_gn_185001-201412.nc",
    )

    print(create_validation_summary(report))
    print()

    # Method 2: Using the GAValidator class directly
    print("Method 2: Using GAValidator class")
    validator = GAValidator(project_id="cmip6")

    # List required attributes
    print("Required attributes for CMIP6:")
    for attr in validator.get_required_attributes():
        print(f"  • {attr}")
    print()

    # Get info about specific attributes
    print("Information about 'activity_id' attribute:")
    activity_info = validator.get_attribute_info("activity_id")
    if activity_info:
        for key, value in activity_info.items():
            print(f"  {key}: {value}")
    print()

    # Validate with detailed reporting
    report2 = validator.validate_from_ncdump(ncdump_output, "example_file.nc")
    print(f"Validation result: {report2.summary()}")

    return report, report2


def example_validate_attributes_dict():
    """
    Example: Validate global attributes from a dictionary.
    """
    print("=== Example: Validating from Attributes Dictionary ===")
    print()

    # Sample attributes dictionary
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
        # Missing some required attributes to test validation
        # "license": "...", # Optional attribute
    }

    validator = GAValidator(project_id="cmip6")
    report = validator.validate_from_attributes_dict(attributes, "test_attributes.nc")

    print(create_validation_summary(report))

    return report


def example_parse_netcdf_header():
    """
    Example: Parse NetCDF header information.
    """
    print("=== Example: Parsing NetCDF Header ===")
    print()

    # Simple ncdump output for parsing
    simple_ncdump = """netcdf test_file {
dimensions:
    time = UNLIMITED ; // (12 currently)
    lat = 180 ;
    lon = 360 ;
variables:
    double time(time) ;
        time:units = "days since 1850-01-01" ;
        time:calendar = "gregorian" ;
    float temperature(time, lat, lon) ;
        temperature:units = "K" ;
        temperature:long_name = "Temperature" ;

// global attributes:
        :Conventions = "CF-1.7" ;
        :title = "Test NetCDF file" ;
        :institution = "Test Institution" ;
        :source = "Test Model" ;
        :history = "Created for testing" ;
        :comment = "This is a test file" ;
}"""

    # Parse the header
    header = NetCDFHeaderParser.parse_from_ncdump(simple_ncdump)

    print(f"Filename: {header.filename}")
    print(f"Dimensions: {len(header.dimensions)}")
    for dim_name, dim in header.dimensions.items():
        print(f"  • {dim_name}: {dim.size} {'(unlimited)' if dim.is_unlimited else ''}")

    print(f"Variables: {len(header.variables)}")
    for var_name, var in header.variables.items():
        print(f"  • {var_name} ({var.data_type}): dims={var.dimensions}, attrs={len(var.attributes)}")

    print(f"Global attributes: {len(header.global_attributes.attributes)}")
    for attr_name, attr_value in header.global_attributes.attributes.items():
        print(f"  • {attr_name}: {attr_value}")

    return header


def example_custom_config():
    """
    Example: Using custom YAML configuration.
    """
    print("=== Example: Custom Configuration ===")
    print()

    # Get the default config path
    current_dir = Path(__file__).parent
    config_path = current_dir / "attributes_specs.yaml"

    print(f"Using configuration file: {config_path}")

    if config_path.exists():
        validator = GAValidator(config_path=str(config_path), project_id="cmip6")

        print(f"Loaded {len(validator.list_attributes())} attribute specifications")
        print("Attribute names:")
        for attr in sorted(validator.list_attributes()):
            info = validator.get_attribute_info(attr)
            required = "required" if info and info.get("required") else "optional"
            print(f"  • {attr} ({required})")

        return validator
    else:
        print(f"Configuration file not found: {config_path}")
        return None


def main():
    """
    Run all examples.
    """
    try:
        print("NetCDF Global Attributes Validator - Examples")
        print("=" * 50)
        print()

        # Example 1: Validate from ncdump output
        report1, report2 = example_validate_ncdump()

        print()
        print("=" * 50)
        print("Examples completed successfully!")

    except Exception as e:
        print(f"Error running examples: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()


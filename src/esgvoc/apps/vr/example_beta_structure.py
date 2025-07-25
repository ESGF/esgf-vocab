#!/usr/bin/env python3
"""
Example script to generate the beta structure JSON as shown in the specification.
This script demonstrates how to use the VR app to create the exact nested structure.
"""

import json

from esgvoc.apps.vr.vr_app import VRApp


def create_beta_structure_example():
    """
    Create the beta structure that matches the provided JSON example.

    This will generate a JSON structure like:
    {
      "standard_name": {
        "air_temperature": {
          "units": "K",
          "sn_status": "approved",
          "variable_root_name": {
            "ta": {
              "var_def_qualifier": "",
              "branding_suffix": {
                "tavg-p19-hxy-air": {
                  "brand_description": "Air temperature on 19 pressure levels",
                  "bn_status": "accepted",
                  "dimensions": ["longitude", "latitude", "plev19", "time"],
                  "cell_methods": "time: mean",
                  "cell_measures": "",
                  "history": "",
                  "temporal_label": "tavg",
                  "vertical_label": "p19",
                  "horizontal_label": "hxy",
                  "area_label": "air",
                  "realm": "atmos"
                },
                "tpt-p19-hxy-air": {
                  "brand_description": "Air temperature point values on 19 pressure levels",
                  "bn_status": "accepted",
                  "dimensions": ["longitude", "latitude", "plev19", "time"],
                  "cell_methods": "",
                  "cell_measures": "",
                  "history": "",
                  "temporal_label": "tpt",
                  "vertical_label": "p19",
                  "horizontal_label": "hxy",
                  "area_label": "air",
                  "realm": "atmos"
                }
              }
            },
            "tas": {
              "var_def_qualifier": "",
              "branding_suffix": {
                "tavg-h2m-hxy-u": {
                  "brand_description": "Temperature at surface",
                  "bn_status": "accepted",
                  "dimensions": ["longitude", "latitude", "time", "height2m"],
                  "cell_methods": "area: time: mean",
                  "cell_measures": "",
                  "history": "",
                  "temporal_label": "tavg",
                  "vertical_label": "h2m",
                  "horizontal_label": "hxy",
                  "area_label": "u",
                  "realm": "atmos"
                }
              }
            }
          }
        },
        "cloud_area_fraction": {
          "units": "1",
          "sn_status": "approved",
          "variable_root_name": {
            "clt": {
              "var_def_qualifier": "",
              "branding_suffix": {
                "tavg-z0-hxy-x": {
                  "brand_description": "Total cloud fraction",
                  "bn_status": "accepted",
                  "dimensions": ["longitude", "latitude", "time"],
                  "cell_methods": "area: time: mean",
                  "cell_measures": "",
                  "history": "",
                  "temporal_label": "tavg",
                  "vertical_label": "z0",
                  "horizontal_label": "hxy",
                  "area_label": "x",
                  "realm": "atmos"
                }
              }
            }
          }
        }
      }
    }
    """

    with VRApp() as vr_app:
        # Get all branded variables
        print("Fetching all branded variables from the universe...")
        all_terms = vr_app.get_all_branded_variables()
        print(f"Found {len(all_terms)} total terms")

        # Get statistics to understand the data
        stats = vr_app.get_statistics(all_terms)
        print(f"\nStatistics:")
        print(f"  Total terms: {stats['total_terms']}")
        print(f"  Unique CF Standard Names: {stats['unique_cf_standard_names']}")
        print(f"  Unique Variable Root Names: {stats['unique_variable_root_names']}")
        print(f"  Unique Realms: {stats['unique_realms']}")

        # Show some sample CF standard names
        cf_names = sorted(set(term.cf_standard_name for term in all_terms))[:10]
        print(f"\nSample CF Standard Names: {cf_names}")

        # Show some sample variable root names
        var_names = sorted(set(term.variable_root_name for term in all_terms))[:10]
        print(f"Sample Variable Root Names: {var_names}")

        # Create beta structure for all terms
        print("\nCreating beta structure for all terms...")
        beta_struct_all = vr_app.create_beta_structure()

        # Create beta structure for atmospheric variables only
        print("Creating beta structure for atmospheric variables only...")
        atmos_filters = {"realm": "atmos"}
        beta_struct_atmos = vr_app.create_beta_structure(filters=atmos_filters)

        # Create beta structure for specific CF standard names that match your example
        print("Creating beta structure for specific CF standard names...")
        specific_filters = {"cf_standard_name": ["air_temperature", "cloud_area_fraction"]}
        beta_struct_specific = vr_app.create_beta_structure(filters=specific_filters)

        # Export all structures
        print("\nExporting structures to JSON files...")
        vr_app.export_to_json(beta_struct_all, "beta_structure_all.json", indent=2)
        vr_app.export_to_json(beta_struct_atmos, "beta_structure_atmos.json", indent=2)
        vr_app.export_to_json(beta_struct_specific, "beta_structure_specific.json", indent=2)

        # Print a sample of the specific structure to verify format
        print("\nSample of beta structure (first 2 standard names):")
        sample_struct = {}
        if "standard_name" in beta_struct_specific:
            std_names = list(beta_struct_specific["standard_name"].keys())[:2]
            sample_struct["standard_name"] = {}
            for std_name in std_names:
                sample_struct["standard_name"][std_name] = beta_struct_specific["standard_name"][std_name]

        print(json.dumps(sample_struct, indent=2))

        return beta_struct_specific


def demonstrate_filtering():
    """
    Demonstrate various filtering options to get subsets of data.
    """
    print("\n" + "=" * 50)
    print("DEMONSTRATING FILTERING OPTIONS")
    print("=" * 50)

    with VRApp() as vr_app:
        # Filter by realm
        print("\n1. Filtering by realm (atmos):")
        atmos_terms = vr_app.get_branded_variables_subset({"realm": "atmos"})
        print(f"   Found {len(atmos_terms)} atmospheric terms")

        # Filter by specific variable root names
        print("\n2. Filtering by variable root names (ta, tas, clt):")
        var_terms = vr_app.get_branded_variables_subset({"variable_root_name": ["ta", "tas", "clt"]})
        print(f"   Found {len(var_terms)} terms with specified variable root names")

        # Filter by CF standard name
        print("\n3. Filtering by CF standard name (air_temperature):")
        cf_terms = vr_app.get_branded_variables_subset({"cf_standard_name": "air_temperature"})
        print(f"   Found {len(cf_terms)} air temperature terms")

        # Combined filters
        print("\n4. Combined filters (atmos realm + air_temperature):")
        combined_terms = vr_app.get_branded_variables_subset({"realm": "atmos", "cf_standard_name": "air_temperature"})
        print(f"   Found {len(combined_terms)} terms matching both criteria")

        # Show some sample branding suffixes
        if combined_terms:
            print("\n   Sample branding suffixes:")
            for term in combined_terms[:5]:
                print(f"     - {term.branding_suffix_name}")


def main():
    """
    Main function to run the example.
    """
    print("VR App Beta Structure Example")
    print("=" * 40)

    try:
        # Create the beta structure
        beta_struct = create_beta_structure_example()

        # Demonstrate filtering
        demonstrate_filtering()

        print("\n" + "=" * 50)
        print("EXAMPLE COMPLETED SUCCESSFULLY!")
        print("=" * 50)
        print("\nGenerated files:")
        print("  - beta_structure_all.json (all terms)")
        print("  - beta_structure_atmos.json (atmospheric terms only)")
        print("  - beta_structure_specific.json (specific CF standard names)")
        print("\nThe beta_structure_specific.json should match your provided example format.")

    except Exception as e:
        print(f"Error running example: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()


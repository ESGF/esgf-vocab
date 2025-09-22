#!/usr/bin/env python3
"""
Simple example showing how to use the VR App.
This demonstrates basic usage patterns for the Variable Registry application.
"""

from vr_app import VRApp


def main():
    """
    Example usage of the VR App showing common operations.
    """
    print("VR App Usage Example")
    print("=" * 20)

    # Initialize the app using context manager for proper cleanup
    with VRApp() as vr_app:
        # 1. Get basic statistics
        print("\n1. Getting statistics...")
        stats = vr_app.get_statistics()
        print(f"   Total terms: {stats['total_terms']}")
        print(f"   Unique CF Standard Names: {stats['unique_cf_standard_names']}")
        print(f"   Unique Variable Root Names: {stats['unique_variable_root_names']}")

        # 2. Create variable registry for atmospheric variables
        print("\n2. Creating variable registry for atmospheric variables...")
        atmos_registry = vr_app.create_variable_registry(filters={"realm": "atmos"})
        vr_app.export_to_json(atmos_registry, "example_atmos_registry.json")
        print("   Exported to: example_atmos_registry.json")

        # 3. Create custom nested structure
        print("\n3. Creating custom structure grouped by realm and CF standard name...")
        custom_structure = vr_app.create_custom_nested_structure(
            group_by_keys=["realm", "cf_standard_name"], metadata_config={0: ["cf_units"], 1: ["cf_sn_status"]}
        )
        vr_app.export_to_json(custom_structure, "example_custom_structure.json")
        print("   Exported to: example_custom_structure.json")

        # 4. Filter by specific variables
        print("\n4. Filtering specific variables...")
        filtered_terms = vr_app.get_branded_variables_subset({"cf_standard_name": "air_temperature", "realm": "atmos"})
        print(f"   Found {len(filtered_terms)} air temperature terms in atmosphere")

        # Show some sample branding suffixes
        if filtered_terms:
            print("   Sample branding suffixes:")
            for term in filtered_terms[:3]:
                print(f"     - {term.branding_suffix_name}")

    print("\n" + "=" * 40)
    print("Example completed successfully!")
    print("Generated files:")
    print("  - example_atmos_registry.json")
    print("  - example_custom_structure.json")


if __name__ == "__main__":
    main()


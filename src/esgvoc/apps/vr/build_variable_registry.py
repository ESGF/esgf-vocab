#!/usr/bin/env python3
"""
Script to build the variable registry structure from branded variables.
This creates the nested JSON structure organized by CF Standard Name and Variable Root Name.
"""

import json
from vr_app import VRApp


def build_variable_registry():
    """
    Build the complete variable registry structure.

    This creates a comprehensive JSON structure with all branded variables
    organized by CF Standard Name and Variable Root Name.
    """
    print("Building Variable Registry...")
    print("=" * 40)

    with VRApp() as vr_app:
        # Get all branded variables
        print("Fetching all branded variables from the universe...")
        all_terms = vr_app.get_all_branded_variables()
        print(f"Found {len(all_terms)} total terms")

        # Get statistics
        stats = vr_app.get_statistics(all_terms)
        print(f"\nStatistics:")
        print(f"  Total terms: {stats['total_terms']}")
        print(f"  Unique CF Standard Names: {stats['unique_cf_standard_names']}")
        print(f"  Unique Variable Root Names: {stats['unique_variable_root_names']}")
        print(f"  Unique Realms: {stats['unique_realms']}")

        # Create complete variable registry
        print("\nCreating complete variable registry...")
        registry_all = vr_app.create_variable_registry()

        # Create atmospheric variables registry
        print("Creating atmospheric variables registry...")
        registry_atmos = vr_app.create_variable_registry(filters={"realm": "atmos"})

        # Export structures
        print("\nExporting registry structures...")
        vr_app.export_to_json(registry_all, "variable_registry_complete.json", indent=2)
        vr_app.export_to_json(registry_atmos, "variable_registry_atmos.json", indent=2)

        print("\n" + "=" * 50)
        print("VARIABLE REGISTRY BUILD COMPLETED!")
        print("=" * 50)
        print("\nGenerated files:")
        print("  - variable_registry_complete.json (all terms)")
        print("  - variable_registry_atmos.json (atmospheric terms only)")

        # Show sample structure
        print(f"\nRegistry contains {len(registry_all.get('standard_name', {}))} CF Standard Names")
        sample_names = list(registry_all.get("standard_name", {}).keys())[:5]
        print(f"Sample CF Standard Names: {sample_names}")

        return registry_all


if __name__ == "__main__":
    try:
        build_variable_registry()
    except Exception as e:
        print(f"Error building variable registry: {e}")
        import traceback

        traceback.print_exc()


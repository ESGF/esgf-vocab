#!/usr/bin/env python3
"""
Simple script to generate the exact JSON structure from your example.
Run this to get the beta structure that matches your specification.
"""

import json
from esgvoc.apps.vr.vr_app import VRApp


def generate_example_json():
    """
    Generate the exact JSON structure from the provided example.
    This will create a JSON file that matches your specification.
    """
    
    with VRApp() as vr_app:
        print("Generating beta structure JSON...")
        
        # Method 1: Create beta structure for all terms
        print("Creating beta structure for all terms...")
        beta_struct_all = vr_app.create_beta_structure()
        
        # Method 2: Create beta structure for specific terms (matching your example)
        print("Creating beta structure for specific atmospheric terms...")
        filters = {
            "realm": "atmos",
            "cf_standard_name": ["air_temperature", "cloud_area_fraction"]
        }
        beta_struct_filtered = vr_app.create_beta_structure(filters=filters)
        
        # Method 3: Create beta structure for even more specific terms
        print("Creating beta structure for very specific terms...")
        specific_filters = {
            "variable_root_name": ["ta", "tas", "tasmax", "clt"]
        }
        beta_struct_specific = vr_app.create_beta_structure(filters=specific_filters)
        
        # Export the structures
        print("Exporting JSON files...")
        vr_app.export_to_json(beta_struct_all, "beta_structure_complete.json", indent=2)
        vr_app.export_to_json(beta_struct_filtered, "beta_structure_example.json", indent=2)
        vr_app.export_to_json(beta_struct_specific, "beta_structure_specific_vars.json", indent=2)
        
        print("\nFiles generated:")
        print("  - beta_structure_complete.json (all terms)")
        print("  - beta_structure_example.json (filtered terms)")
        print("  - beta_structure_specific_vars.json (specific variable names)")
        
        # Show a preview of the structure
        print("\nPreview of the generated structure:")
        if "standard_name" in beta_struct_specific:
            std_names = list(beta_struct_specific["standard_name"].keys())
            print(f"Standard names found: {std_names}")
            
            # Show first standard name structure
            if std_names:
                first_std = std_names[0]
                print(f"\nStructure for '{first_std}':")
                print(json.dumps(
                    {"standard_name": {first_std: beta_struct_specific["standard_name"][first_std]}}, 
                    indent=2
                ))


if __name__ == "__main__":
    generate_example_json()
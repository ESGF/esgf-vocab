"""
Variable Registry (VR) App - A simplified tool for creating nested structures from branded variables.

This module provides:
- VRApp: Main application class for querying and structuring branded variables
- create_nested_structure: Generic function for creating nested structures
- variable_registry_structure: Function for creating the standard variable registry format
"""

from .vr_app import VRApp, create_nested_structure, variable_registry_structure

__all__ = ["VRApp", "create_nested_structure", "variable_registry_structure"]
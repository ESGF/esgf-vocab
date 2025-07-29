import json
from collections import defaultdict
from typing import Any, Dict, List, Optional, Union

from esgvoc import api
from esgvoc.api import search
from esgvoc.api.data_descriptors.data_descriptor import DataDescriptor
from esgvoc.api.data_descriptors.known_branded_variable import KnownBrandedVariable


def create_nested_structure(
    terms: List[KnownBrandedVariable], group_by_keys: List[str], metadata_config: Optional[Dict[str, List[str]]] = None
) -> Dict[str, Any]:
    """
    Create a nested structure from a list of terms using ordered grouping keys.

    Args:
        terms: List of KnownBrandedVariable terms
        group_by_keys: Ordered list of field names to group by
        metadata_config: Optional dict mapping group levels to metadata field names
                        Format: {level_index: [field_names]}

    Returns:
        Nested dictionary structure
    """
    if not terms or not group_by_keys:
        return {}

    metadata_config = metadata_config or {}

    def _build_nested_dict(
        current_terms: List[KnownBrandedVariable], remaining_keys: List[str], level: int
    ) -> Dict[str, Any]:
        if not remaining_keys:
            return [term.model_dump() for term in current_terms]

        current_key = remaining_keys[0]
        remaining_keys = remaining_keys[1:]

        grouped = defaultdict(list)
        metadata_by_group = {}

        for term in current_terms:
            group_value = getattr(term, current_key, None)
            if group_value is not None:
                grouped[group_value].append(term)

                if level in metadata_config and group_value not in metadata_by_group:
                    metadata_by_group[group_value] = {}
                    for meta_field in metadata_config[level]:
                        metadata_by_group[group_value][meta_field] = getattr(term, meta_field, None)

        result = {}
        for group_value, group_terms in grouped.items():
            if level in metadata_config:
                result[group_value] = metadata_by_group[group_value].copy()

                if remaining_keys:
                    nested_result = _build_nested_dict(group_terms, remaining_keys.copy(), level + 1)
                    result[group_value].update(nested_result)
                else:
                    result[group_value]["items"] = [term.model_dump() for term in group_terms]
            else:
                result[group_value] = _build_nested_dict(group_terms, remaining_keys.copy(), level + 1)

        return result

    return _build_nested_dict(terms, group_by_keys.copy(), 0)


def variable_registry_structure(terms: List[KnownBrandedVariable]) -> Dict[str, Any]:
    """
    Create the variable registry structure with CF Standard Name and VariableRootName grouping.

    Args:
        terms: List of KnownBrandedVariable terms

    Returns:
        Nested dictionary with the variable registry structure format
    """
    metadata_config = {
        0: ["cf_units", "cf_sn_status"],  # CF Standard Name level
        1: ["var_def_qualifier"],  # Variable Root Name level
    }

    group_by_keys = ["cf_standard_name", "variable_root_name"]

    nested_data = create_nested_structure(terms, group_by_keys, metadata_config)

    def _transform_to_registry_format(data: Dict[str, Any]) -> Dict[str, Any]:
        result = {"standard_name": {}}

        for std_name, std_data in data.items():
            if isinstance(std_data, dict):
                result["standard_name"][std_name] = {
                    "units": std_data.get("cf_units", ""),
                    "sn_status": std_data.get("cf_sn_status", ""),
                    "variable_root_name": {},
                }

                for var_name, var_data in std_data.items():
                    if var_name in ["cf_units", "cf_sn_status"]:
                        continue

                    if isinstance(var_data, dict):
                        result["standard_name"][std_name]["variable_root_name"][var_name] = {
                            "var_def_qualifier": var_data.get("var_def_qualifier", ""),
                            "branding_suffix": {},
                        }

                        for suffix_name, suffix_data in var_data.items():
                            if suffix_name == "var_def_qualifier":
                                continue

                            if isinstance(suffix_data, list):
                                for term_data in suffix_data:
                                    if isinstance(term_data, dict):
                                        suffix_key = term_data.get("branding_suffix_name", "")
                                        if suffix_key:
                                            result["standard_name"][std_name]["variable_root_name"][var_name][
                                                "branding_suffix"
                                            ][suffix_key] = {
                                                "brand_description": term_data.get("description", ""),
                                                "bn_status": term_data.get("bn_status", ""),
                                                "dimensions": term_data.get("dimensions", []),
                                                "cell_methods": term_data.get("cell_methods", ""),
                                                "cell_measures": term_data.get("cell_measures", ""),
                                                "history": term_data.get("history", ""),
                                                "temporal_label": term_data.get("temporal_label", ""),
                                                "vertical_label": term_data.get("vertical_label", ""),
                                                "horizontal_label": term_data.get("horizontal_label", ""),
                                                "area_label": term_data.get("area_label", ""),
                                                "realm": term_data.get("realm", ""),
                                            }

        return result

    return _transform_to_registry_format(nested_data)


class VRApp:
    """
    Variable Restructuring (VR) App for creating nested structures from branded variables.

    This app allows querying known_branded_variable terms from the universe and
    transforming them into nested JSON structures with customizable grouping.
    """

    def __init__(self):
        self.universe_session = search.get_universe_session()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.universe_session:
            self.universe_session.close()

    def get_all_branded_variables(self) -> List[DataDescriptor]:
        """
        Get all known_branded_variable terms from the universe.

        Returns:
            List of KnownBrandedVariable terms
        """
        try:
            terms = api.get_all_terms_in_data_descriptor("known_branded_variable")
            return terms
        except Exception as e:
            print(f"Error fetching branded variables: {e}")
            return []

    def get_branded_variables_subset(self, filters: Dict[str, Any]) -> List[KnownBrandedVariable]:
        """
        Get a subset of known_branded_variable terms based on filters.

        Args:
            filters: Dictionary of field names and values to filter by

        Returns:
            List of filtered KnownBrandedVariable terms
        """
        all_terms = self.get_all_branded_variables()
        filtered_terms = []

        for term in all_terms:
            match = True
            for field, value in filters.items():
                term_value = getattr(term, field, None)
                if isinstance(value, list):
                    if term_value not in value:
                        match = False
                        break
                elif term_value != value:
                    match = False
                    break

            if match:
                filtered_terms.append(term)

        return filtered_terms

    def create_custom_nested_structure(
        self,
        terms: Optional[List[KnownBrandedVariable]] = None,
        group_by_keys: List[str] = None,
        metadata_config: Optional[Dict[str, List[str]]] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a custom nested structure.

        Args:
            terms: Optional list of terms. If None, fetches all terms
            group_by_keys: List of field names to group by
            metadata_config: Optional metadata configuration
            filters: Optional filters to apply when fetching terms

        Returns:
            Nested dictionary structure
        """
        if terms is None:
            if filters:
                terms = self.get_branded_variables_subset(filters)
            else:
                terms = self.get_all_branded_variables()

        if not group_by_keys:
            group_by_keys = ["cf_standard_name", "variable_root_name"]

        return create_nested_structure(terms, group_by_keys, metadata_config)

    def create_variable_registry(
        self, terms: Optional[List[KnownBrandedVariable]] = None, filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create the variable registry structure with CF Standard Name and VariableRootName grouping.

        Args:
            terms: Optional list of terms. If None, fetches all terms
            filters: Optional filters to apply when fetching terms

        Returns:
            Nested dictionary with the variable registry structure format
        """
        if terms is None:
            if filters:
                terms = self.get_branded_variables_subset(filters)
            else:
                terms = self.get_all_branded_variables()

        return variable_registry_structure(terms)

    def export_to_json(self, structure: Dict[str, Any], filename: str, indent: int = 2) -> None:
        """
        Export a nested structure to a JSON file.

        Args:
            structure: The nested dictionary structure to export
            filename: Output filename
            indent: JSON indentation level
        """
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(structure, f, indent=indent, ensure_ascii=False)
            print(f"Structure exported to {filename}")
        except Exception as e:
            print(f"Error exporting to JSON: {e}")

    def get_statistics(self, terms: Optional[List[KnownBrandedVariable]] = None) -> Dict[str, Any]:
        """
        Get statistics about the branded variables.

        Args:
            terms: Optional list of terms. If None, fetches all terms

        Returns:
            Dictionary with statistics
        """
        if terms is None:
            terms = self.get_all_branded_variables()

        stats = {
            "total_terms": len(terms),
            "unique_cf_standard_names": len(set(term.cf_standard_name for term in terms)),
            "unique_variable_root_names": len(set(term.variable_root_name for term in terms)),
            "unique_realms": len(set(term.realm for term in terms)),
            "status_distribution": {},
            "realm_distribution": {},
        }

        # Status distribution
        for term in terms:
            status = term.bn_status
            stats["status_distribution"][status] = stats["status_distribution"].get(status, 0) + 1

        # Realm distribution
        for term in terms:
            realm = term.realm
            stats["realm_distribution"][realm] = stats["realm_distribution"].get(realm, 0) + 1

        return stats


def main():
    """
    Example usage of the VR App.
    """
    with VRApp() as vr_app:
        # Get statistics
        stats = vr_app.get_statistics()
        print(f"Total terms: {stats['total_terms']}")
        print(f"Unique CF Standard Names: {stats['unique_cf_standard_names']}")
        print(f"Unique Variable Root Names: {stats['unique_variable_root_names']}")

        # Create variable registry for a subset
        filters = {"realm": "atmos"}
        registry_struct = vr_app.create_variable_registry(filters=filters)

        # Export to JSON
        vr_app.export_to_json(registry_struct, "variable_registry_atmos.json")

        # Create custom structure
        custom_struct = vr_app.create_custom_nested_structure(
            group_by_keys=["realm", "cf_standard_name"],
            metadata_config={0: ["bn_status"], 1: ["cf_units", "cf_sn_status"]},
        )

        vr_app.export_to_json(custom_struct, "custom_structure.json")


if __name__ == "__main__":
    main()

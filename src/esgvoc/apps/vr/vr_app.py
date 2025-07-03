import json
from typing import Any, Dict, List, Optional, Union

from esgvoc import api
from esgvoc.api import search
from esgvoc.api.data_descriptors.data_descriptor import DataDescriptor
from esgvoc.api.data_descriptors.known_branded_variable import KnownBrandedVariable
from esgvoc.apps.vr.nested_structure import beta_structure, create_nested_structure


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

    def create_beta_structure(
        self, terms: Optional[List[KnownBrandedVariable]] = None, filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create the beta structure with CF Standard Name and VariableRootName grouping.

        Args:
            terms: Optional list of terms. If None, fetches all terms
            filters: Optional filters to apply when fetching terms

        Returns:
            Nested dictionary with the beta structure format
        """
        if terms is None:
            if filters:
                terms = self.get_branded_variables_subset(filters)
            else:
                terms = self.get_all_branded_variables()

        return beta_structure(terms)

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

        # Create beta structure for a subset
        filters = {"realm": "atmos"}
        beta_struct = vr_app.create_beta_structure(filters=filters)

        # Export to JSON
        vr_app.export_to_json(beta_struct, "beta_structure_atmos.json")

        # Create custom structure
        custom_struct = vr_app.create_custom_nested_structure(
            group_by_keys=["realm", "cf_standard_name"],
            metadata_config={0: ["bn_status"], 1: ["cf_units", "cf_sn_status"]},
        )

        vr_app.export_to_json(custom_struct, "custom_structure.json")


if __name__ == "__main__":
    main()


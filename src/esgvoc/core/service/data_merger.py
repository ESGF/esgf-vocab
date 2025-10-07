from typing import Dict, List, Set
from esgvoc.core.data_handler import JsonLdResource
import logging

logger = logging.getLogger(__name__)


def merge_dicts(original: list, custom: list) -> dict:
    """Shallow merge: Overwrites original data with custom data."""
    b = original[0]
    a = custom[0]
    merged = {
        **{k: v for k, v in a.items() if k != "@id"},
        **{k: v for k, v in b.items() if k != "@id"},
    }
    return merged


def merge(uri: str) -> Dict:
    mdm = DataMerger(data=JsonLdResource(uri=uri))
    return mdm.merge_linked_json()[-1]


def resolve_nested_ids_in_dict(data: dict, merger: "DataMerger") -> dict:
    """
    Resolve all nested @id references in a dictionary using a DataMerger instance.

    Args:
        data: The dictionary containing potential @id references
        merger: The DataMerger instance to use for resolution

    Returns:
        Dictionary with all @id references resolved to full objects
    """
    return merger.resolve_nested_ids(data)


class DataMerger:
    def __init__(
        self,
        data: JsonLdResource,
        allowed_base_uris: Set[str] = {
            "https://espri-mod.github.io/mip-cmor-tables"},
        locally_available: dict = {},
    ):
        self.data = data
        self.allowed_base_uris = allowed_base_uris
        self.locally_available = locally_available

    def _should_resolve(self, uri: str) -> bool:
        """Check if a given URI should be resolved based on allowed URIs."""
        return any(uri.startswith(base) for base in self.allowed_base_uris)

    def _get_next_id(self, data: dict) -> str | None:
        """Extract the next @id from the data if it is a valid customization reference."""
        if isinstance(data, list):
            data = data[0]
        if "@id" in data and self._should_resolve(data["@id"]):
            return data["@id"] + ".json"
        return None

    def merge_linked_json(self) -> List[Dict]:
        """Fetch and merge data recursively, returning a list of progressively merged Data json instances."""
        # Start with the original json object
        result_list = [self.data.json_dict]
        visited = set(self.data.uri)  # Track visited URIs to prevent cycles
        current_data = self.data

        while True:
            next_id = self._get_next_id(current_data.expanded[0])
            if not next_id or next_id in visited or not self._should_resolve(next_id):
                break
            visited.add(next_id)
            # Fetch and merge the next customization
            # do we have it in local ? if so use it instead of remote
            for local_repo in self.locally_available.keys():
                if next_id.startswith(local_repo):
                    next_id = next_id.replace(
                        local_repo, self.locally_available[local_repo])
            next_data_instance = JsonLdResource(uri=next_id)
            merged_json_data = merge_dicts([current_data.json_dict], [
                                           next_data_instance.json_dict])

            next_data_instance.json_dict = merged_json_data

            # Add the merged instance to the result list
            result_list.append(merged_json_data)
            current_data = next_data_instance
        return result_list

    def resolve_nested_ids(self, data, expanded_data=None, visited: Set[str] = None) -> dict | list:
        """
        Recursively resolve all @id references in nested structures.

        Uses the expanded JSON-LD to find full URIs, fetches referenced terms,
        and replaces references with full objects.

        Args:
            data: The compact JSON data to process (dict, list, or primitive)
            expanded_data: The expanded JSON-LD version (with full URIs)
            visited: Set of URIs already visited to prevent circular references

        Returns:
            The data structure with all @id references resolved
        """
        if visited is None:
            visited = set()

        # On first call (when visited is empty), get the expanded data
        # But NOT when we're resolving a fetched term recursively
        if expanded_data is None and len(visited) == 0:
            expanded_data = self.data.expanded
            if isinstance(expanded_data, list) and len(expanded_data) > 0:
                expanded_data = expanded_data[0]

        # Handle the case where expanded_data is a list with a single dict
        if isinstance(expanded_data, list) and len(expanded_data) == 1:
            expanded_data = expanded_data[0]

        if isinstance(data, dict):
            # Check if this dict is a simple @id reference (like {"@id": "hadgem3_gc31_atmos_100km"})
            if "@id" in data and len(data) == 1:
                id_value = data["@id"]

                try:
                    # The expanded_data should have the full URI
                    uri = expanded_data.get("@id", id_value) if isinstance(expanded_data, dict) else id_value

                    # Only resolve if it's in our allowed URIs
                    if not self._should_resolve(uri):
                        return data

                    # Ensure it has .json extension
                    if not uri.endswith(".json"):
                        uri += ".json"

                    # Prevent circular references (only within the current resolution chain)
                    if uri in visited:
                        logger.warning(f"Circular reference detected: {uri}")
                        return data

                    # Add to visited for this branch only
                    new_visited = visited.copy()
                    new_visited.add(uri)

                    # Convert remote URI to local path
                    local_uri = uri
                    for local_repo, local_path in self.locally_available.items():
                        if uri.startswith(local_repo):
                            local_uri = uri.replace(local_repo, local_path)
                            break

                    # Fetch the referenced term (raw JSON)
                    resolved = self._fetch_referenced_term(uri)

                    # Create a temporary resource to get proper expansion for this term
                    # Use the local path so it can find the context file
                    temp_resource = JsonLdResource(uri=local_uri)
                    temp_expanded = temp_resource.expanded
                    if isinstance(temp_expanded, list) and len(temp_expanded) > 0:
                        temp_expanded = temp_expanded[0]

                    # Recursively resolve any nested references in the resolved data
                    # Pass the expanded data for this specific term
                    return self.resolve_nested_ids(resolved, temp_expanded, new_visited)

                except Exception as e:
                    logger.error(f"Failed to resolve reference {id_value}: {e}")
                    return data

            # Otherwise, recursively process all values in the dict
            result = {}
            for key, value in data.items():
                # Find corresponding expanded value
                # Map compact key to expanded key (e.g., "model_components" -> "http://schema.org/model_components")
                expanded_key = key
                if isinstance(expanded_data, dict):
                    # Try to find the key in expanded data
                    # It might be under a full URI
                    for exp_key in expanded_data.keys():
                        if exp_key.endswith("/" + key) or exp_key.endswith("#" + key) or exp_key == key:
                            expanded_key = exp_key
                            break

                expanded_value = expanded_data.get(expanded_key) if isinstance(expanded_data, dict) else None
                result[key] = self.resolve_nested_ids(value, expanded_value, visited)
            return result

        elif isinstance(data, list) and isinstance(expanded_data, list):
            # Recursively process each item in the list with corresponding expanded item
            # Each list item gets its own visited set to allow reusing the same references
            result = []
            for i, item in enumerate(data):
                expanded_item = expanded_data[i] if i < len(expanded_data) else None
                # Create a fresh visited set for each list item
                result.append(self.resolve_nested_ids(item, expanded_item, set()))
            return result

        elif isinstance(data, list):
            # List but no corresponding expanded list, process without expanded data
            # Each list item gets its own visited set
            return [self.resolve_nested_ids(item, None, set()) for item in data]

        else:
            # Primitive values are returned as-is
            return data

    def _fetch_referenced_term(self, uri: str) -> dict:
        """
        Fetch a term from URI and return its data.
        Tries multiple paths if the direct path doesn't exist.

        IMPORTANT: This method reads the JSON file directly without creating
        a JsonLdResource to avoid triggering expansion which could cause
        infinite recursion during nested ID resolution.
        """
        import os
        import json
        from pathlib import Path

        # Check locally_available for path substitution
        resolved_uri = uri
        for local_repo, local_path in self.locally_available.items():
            if uri.startswith(local_repo):
                resolved_uri = uri.replace(local_repo, local_path)
                break

        # Try to read the file directly
        if os.path.exists(resolved_uri):
            with open(resolved_uri, 'r') as f:
                return json.load(f)

        # File doesn't exist at the expanded path
        # Try to find it in other data descriptor directories
        filename = Path(resolved_uri).name
        parts = Path(resolved_uri).parts
        if len(parts) >= 3:
            base_dir = Path(*parts[:-2])  # Remove data_descriptor and filename

            # Try common data descriptor directories for grids
            alternate_dirs = ['horizontal_grid', 'vertical_grid', 'grid']
            for alt_dir in alternate_dirs:
                alt_path = base_dir / alt_dir / filename
                if os.path.exists(alt_path):
                    with open(alt_path, 'r') as f:
                        return json.load(f)

        # If still not found, try the original URI (might be remote)
        if os.path.exists(resolved_uri):
            with open(resolved_uri, 'r') as f:
                return json.load(f)
        else:
            # Last resort: try to fetch remotely
            import requests
            response = requests.get(uri, headers={"accept": "application/json"}, verify=False)
            if response.status_code == 200:
                return response.json()
            else:
                raise FileNotFoundError(f"Could not find or fetch term at {uri}")


if __name__ == "__main__":
    import warnings

    warnings.simplefilter("ignore")

    # test from institution_id ipsl exapnd and merge with institution ipsl
    # proj_ipsl = JsonLdResource(uri = "https://espri-mod.github.io/CMIP6Plus_CVs/institution_id/ipsl.json")
    # allowed_uris = {"https://espri-mod.github.io/CMIP6Plus_CVs/","https://espri-mod.github.io/mip-cmor-tables/"}
    # mdm = DataMerger(data =proj_ipsl, allowed_base_uris = allowed_uris)
    #     json_list = mdm.merge_linked_json()
    #
    # pprint([res for res in json_list])

    # a = JsonLdResource(uri = ".cache/repos/CMIP6Plus_CVs/institution_id/ipsl.json")
    # mdm = DataMerger(data=a)
    # print(mdm.merge_linked_json())
    #
    #

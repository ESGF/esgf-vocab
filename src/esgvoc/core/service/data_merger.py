import logging
from typing import Dict, List, Set

from esgvoc.core.data_handler import JsonLdResource
from esgvoc.core.service.resolver_config import ResolverConfig
from esgvoc.core.service.string_heuristics import StringHeuristics
from esgvoc.core.service.term_cache import TermCache
from esgvoc.core.service.uri_resolver import URIResolver

logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)


def merge_dicts(base: list, override: list) -> dict:
    """
    Merge two JSON-LD dictionaries, with override taking precedence.

    This performs a shallow merge where:
    1. Start with override data (custom/project-specific)
    2. Overlay with base data (parent/universe defaults)
    3. Skip @id field from both (handled separately in JSON-LD)

    Args:
        base: List containing the base/parent dictionary (expects [dict])
        override: List containing the override/child dictionary (expects [dict])

    Returns:
        Merged dictionary with override values taking precedence

    Example:
        >>> base = [{"name": "Base", "value": 1}]
        >>> override = [{"value": 2, "new": "field"}]
        >>> merge_dicts(base, override)
        {'value': 2, 'new': 'field', 'name': 'Base'}

    Note:
        Takes lists for backward compatibility with JSON-LD processing,
        but only uses the first element of each.
    """
    base_data = base[0]
    override_data = override[0]

    # Merge strategy: override first, then base (so base fills in missing fields)
    merged = {
        **{k: v for k, v in override_data.items() if k != "@id"},
        **{k: v for k, v in base_data.items() if k != "@id"},
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
    """
    Merge and resolve JSON-LD data with support for @id references.

    This class handles:
    1. Merging linked JSON-LD documents (following @id chains)
    2. Resolving nested @id references to full objects
    3. Converting between remote URIs and local paths
    """

    def __init__(
        self,
        data: JsonLdResource,
        allowed_base_uris: Set[str] | None = None,
        locally_available: Dict[str, str] | None = None,
        config: ResolverConfig | None = None,
    ):
        """
        Initialize the DataMerger.

        Args:
            data: The JSON-LD resource to process
            allowed_base_uris: Set of base URIs that are allowed to be resolved.
                              Defaults to {"https://espri-mod.github.io/mip-cmor-tables"}
                              for backward compatibility.
            locally_available: Mapping from remote base URIs to local directory paths.
                             Defaults to empty dict for backward compatibility.
            config: Configuration for resolution behavior. If None, uses defaults.
        """
        self.data = data

        # Backward compatibility: use default CMIP URI if none provided
        if allowed_base_uris is None:
            allowed_base_uris = {"https://espri-mod.github.io/mip-cmor-tables"}
        self.allowed_base_uris = allowed_base_uris

        # Fix mutable default anti-pattern
        if locally_available is None:
            locally_available = {}
        self.locally_available = locally_available

        # Initialize configuration and helpers
        self.config = config or ResolverConfig()
        self.uri_resolver = URIResolver(self.locally_available)
        self.string_heuristics = StringHeuristics(
            max_length=self.config.max_string_length, exclude_patterns=self.config.exclude_patterns
        )
        self.term_cache = TermCache(max_size=self.config.cache_size, enabled=self.config.enable_caching)

    def _should_resolve(self, uri: str) -> bool:
        """Check if a given URI should be resolved based on allowed URIs."""
        return any(uri.startswith(base) for base in self.allowed_base_uris)

    def _get_resolve_mode(self, key: str) -> str:
        """
        Get the resolve mode for a field from the context.

        Args:
            key: The field name to check

        Returns:
            "full" (default), "shallow", or "reference"
        """
        if not hasattr(self.data, "context"):
            return "full"

        context = self.data.context

        # Check for esgvoc_resolve_modes at the root level (outside @context)
        if isinstance(context, dict) and "esgvoc_resolve_modes" in context:
            resolve_modes = context["esgvoc_resolve_modes"]
            if isinstance(resolve_modes, dict) and key in resolve_modes:
                return resolve_modes[key]

        return "full"  # Default: full resolution

    def _get_next_id(self, data: dict, current_uri: str = None) -> str | None:
        """
        Extract the next @id from the data if it is a valid customization reference.

        Args:
            data: The expanded JSON-LD data
            current_uri: The URI of the current resource (to avoid self-reference)

        Returns:
            The next URI to fetch and merge, or None if no valid reference exists
        """
        if isinstance(data, list):
            data = data[0]
        if "@id" in data and self._should_resolve(data["@id"]):
            result = self.uri_resolver.ensure_json_extension(data["@id"])

            # Don't follow the reference if it points to the same resource
            if current_uri and result == current_uri:
                return None

            return result
        return None

    def merge_linked_json(self) -> List[Dict]:
        """Fetch and merge data recursively, returning a list of progressively merged Data json instances."""
        # Start with the original json object
        result_list = [self.data.json_dict]
        visited = set()  # Track visited URIs (remote URIs) to prevent cycles
        current_expanded = self.data.expanded[0]
        current_json = self.data.json_dict
        current_remote_uri = None  # Track the remote URI of the current resource

        while True:
            # Get the next @id to follow, passing the current remote URI to avoid self-reference
            next_id = self._get_next_id(current_expanded, current_remote_uri)
            if not next_id or next_id in visited or not self._should_resolve(next_id):
                break
            visited.add(next_id)
            current_remote_uri = next_id  # Save for next iteration

            # Fetch and merge the next customization
            # Convert remote URI to local path if available
            next_id_local = self.uri_resolver.to_local_path(next_id)

            next_data_instance = JsonLdResource(uri=next_id_local)
            merged_json_data = merge_dicts([current_json], [next_data_instance.json_dict])

            # Add the merged instance to the result list
            result_list.append(merged_json_data)

            # For the next iteration, use the expanded data from the newly loaded resource
            # (NOT from the merged data, as merge is about overlaying, not chaining references)
            current_expanded = next_data_instance.expanded[0]
            current_json = merged_json_data
        return result_list

    def resolve_nested_ids(
        self,
        data,
        expanded_data=None,
        visited: Set[str] = None,
        _is_root_call: bool = True,
        resolve_mode: str = "full",
        _current_property: str | None = None,
    ) -> dict | list:
        """
        Recursively resolve all @id references in nested structures.

        Uses the expanded JSON-LD to find full URIs, fetches referenced terms,
        and replaces references with full objects.

        Args:
            data: The compact JSON data to process (dict, list, or primitive)
            expanded_data: The expanded JSON-LD version (with full URIs)
            visited: Set of URIs already visited to prevent circular references
            _is_root_call: Internal flag to detect the top-level call
            resolve_mode: Resolution mode - "full", "shallow", or "reference"
                         - "full": Resolve and recurse (default)
                         - "shallow": Resolve but don't recurse into resolved object
                         - "reference": Keep as string, validate it exists
            _current_property: Internal tracking of which property is being resolved (for better error messages)

        Returns:
            The data structure with all @id references resolved
        """
        if visited is None:
            visited = set()

        # On first call only, get the expanded data if not provided
        if expanded_data is None and _is_root_call:
            expanded_data = self.data.expanded
            if isinstance(expanded_data, list) and len(expanded_data) > 0:
                expanded_data = expanded_data[0]

        # Handle the case where expanded_data is a list with a single dict
        # ONLY on the root call - not for nested list processing!
        if _is_root_call and isinstance(expanded_data, list) and len(expanded_data) == 1:
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
                    uri = self.uri_resolver.ensure_json_extension(uri)

                    # Prevent circular references (only within the current resolution chain)
                    if uri in visited:
                        logger.warning(f"Circular reference detected: {uri}")
                        return data

                    # Add to visited for this branch only
                    new_visited = visited.copy()
                    new_visited.add(uri)

                    # Convert remote URI to local path
                    local_uri = self.uri_resolver.to_local_path(uri)

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
                    return self.resolve_nested_ids(resolved, temp_expanded, new_visited, _is_root_call=False)

                except Exception as e:
                    logger.error(f"Failed to resolve reference {id_value}: {e}")
                    return data

            # Otherwise, recursively process all values in the dict
            result = {}
            for key, value in data.items():
                # Find corresponding expanded value
                # Map compact key to expanded key (e.g., "model_components" -> "http://schema.org/model_components")
                # Also handle JSON-LD keywords: "id" -> "@id", "type" -> "@type"
                expanded_key = key
                if isinstance(expanded_data, dict):
                    # First check for JSON-LD keyword mappings
                    if key == "id":
                        expanded_key = "@id"
                    elif key == "type":
                        expanded_key = "@type"
                    else:
                        # Try to find the key in expanded data
                        # It might be under a full URI
                        for exp_key in expanded_data.keys():
                            # Check for exact match or if the URI contains the key
                            # URIs may have trailing slashes: https://.../activity/
                            if (
                                exp_key == key
                                or exp_key.endswith("/" + key)
                                or exp_key.endswith("/" + key + "/")
                                or exp_key.endswith("#" + key)
                            ):
                                expanded_key = exp_key
                                break

                        # If not found, check the context to see if this key has a different @id
                        # (e.g., required_model_components has @id of source_type/)
                        if expanded_key == key and hasattr(self.data, "context"):
                            context = self.data.context
                            if isinstance(context, dict) and "@context" in context:
                                context = context["@context"]
                            if isinstance(context, dict) and key in context:
                                term_def = context[key]
                                if isinstance(term_def, dict) and "@id" in term_def:
                                    # The @id value should match a key in expanded_data
                                    id_value = term_def["@id"]
                                    # Try with and without trailing slash
                                    if id_value in expanded_data:
                                        expanded_key = id_value
                                    elif id_value.rstrip("/") + "/" in expanded_data:
                                        expanded_key = id_value.rstrip("/") + "/"
                                    elif id_value.rstrip("/") in expanded_data:
                                        expanded_key = id_value.rstrip("/")

                expanded_value = expanded_data.get(expanded_key) if isinstance(expanded_data, dict) else None

                # Check if this field has a @resolve mode in the context
                field_resolve_mode = self._get_resolve_mode(key)

                resolved = self.resolve_nested_ids(
                    value,
                    expanded_value,
                    visited,
                    _is_root_call=False,
                    resolve_mode=field_resolve_mode,
                    _current_property=key,
                )
                result[key] = resolved
            return result

        elif isinstance(data, list) and isinstance(expanded_data, list):
            # Recursively process each item in the list with corresponding expanded item
            result = []
            for i, item in enumerate(data):
                expanded_item = expanded_data[i] if i < len(expanded_data) else None
                # Pass visited set and resolve_mode to prevent circular references across list items
                resolved_item = self.resolve_nested_ids(
                    item,
                    expanded_item,
                    visited,
                    _is_root_call=False,
                    resolve_mode=resolve_mode,
                    _current_property=_current_property,
                )
                result.append(resolved_item)
            return result

        elif isinstance(data, list):
            # List but no corresponding expanded list, process without expanded data
            # Each list item gets its own visited set
            return [
                self.resolve_nested_ids(
                    item,
                    None,
                    set(),
                    _is_root_call=False,
                    resolve_mode=resolve_mode,
                    _current_property=_current_property,
                )
                for item in data
            ]

        else:
            # Primitive values - but check if they're ID references
            # If the compact form is a string but expanded form is {"@id": "..."},
            # it's an ID reference that needs resolving

            # JSON-LD expansion often wraps values in arrays, unwrap single-element arrays
            if isinstance(expanded_data, list) and len(expanded_data) == 1:
                expanded_data = expanded_data[0]

            if isinstance(data, str) and isinstance(expanded_data, dict):
                # Skip if it's a @value (literal string, not a reference)
                if self.string_heuristics.should_skip_literal(expanded_data):
                    return data

                if not self.string_heuristics.has_id_in_expanded(expanded_data):
                    return data

                uri = expanded_data["@id"]

                # Check resolve_mode FIRST before any expensive operations
                if resolve_mode == "reference":
                    # "reference" mode: just validate the ID exists, keep as string
                    uri_to_check = self.uri_resolver.ensure_json_extension(uri)
                    if not self.uri_resolver.exists(uri_to_check):
                        property_msg = f" in property '{_current_property}'" if _current_property else ""
                        logger.warning(
                            f"Reference validation failed: ID '{data}' does not exist at {uri_to_check}{property_msg}"
                        )
                    return data  # Keep as string regardless

                # Use string heuristics to determine if this should be resolved
                if not self.string_heuristics.is_resolvable(data):
                    return data

                # Only resolve if it's in our allowed URIs
                if not self._should_resolve(uri):
                    return data

                # Check if recursion depth is too deep (prevent infinite loops)
                if len(visited) > self.config.max_depth:
                    if self.config.log_depth_warnings:
                        logger.warning(
                            f"Max depth ({self.config.max_depth}) exceeded. Visited {len(visited)} URIs. Current: {uri}"
                        )
                    return data

                # Ensure it has .json extension
                uri = self.uri_resolver.ensure_json_extension(uri)

                # Prevent circular references
                if uri in visited:
                    logger.debug(f"Circular reference detected: {uri}")
                    return data

                # Check if the file exists before trying to resolve
                # Don't resolve strings that are just enum values or simple identifiers
                # Only resolve if it looks like a real component/grid reference
                try:
                    # Convert remote URI to local path
                    local_uri = self.uri_resolver.to_local_path(uri)

                    # Check if file exists - if not, it's probably not a resolvable reference
                    if not self.uri_resolver.exists(uri):
                        property_msg = f"  Property: '{_current_property}'\n" if _current_property else ""
                        logger.warning(
                            f"Cannot resolve ID reference: File not found\n"
                            f"  Current term: {self.data.uri}\n"
                            f"{property_msg}"
                            f"  String value: '{data}'\n"
                            f"  Expected URI: {uri}\n"
                            f"  Local path tried: {local_uri}\n"
                            f"  → Keeping as unresolved string"
                        )
                        return data
                except (OSError, IOError) as e:
                    property_msg = f"  Property: '{_current_property}'\n" if _current_property else ""
                    logger.warning(
                        f"Cannot resolve ID reference: Error checking file existence\n"
                        f"  Current term: {self.data.uri}\n"
                        f"{property_msg}"
                        f"  String value: '{data}'\n"
                        f"  Expected URI: {uri}\n"
                        f"  Error: {e}\n"
                        f"  → Keeping as unresolved string"
                    )
                    return data

                # Add to visited for this branch only
                new_visited = visited.copy()
                new_visited.add(uri)

                try:
                    # Fetch the referenced term
                    resolved = self._fetch_referenced_term(uri)

                    logger.info(
                        f"Successfully resolved ID reference\n"
                        f"  Current term: {self.data.uri}\n"
                        f"  String value: '{data}'\n"
                        f"  Resolved to: {uri}\n"
                        f"  Mode: {resolve_mode}\n"
                        f"  → Replacing with {'shallow' if resolve_mode == 'shallow' else 'full'} object"
                    )

                    # Create a temporary resource to get proper expansion for this term
                    temp_resource = JsonLdResource(uri=local_uri)
                    temp_expanded = temp_resource.expanded
                    if isinstance(temp_expanded, list) and len(temp_expanded) > 0:
                        temp_expanded = temp_expanded[0]

                    # Handle resolution based on mode
                    if resolve_mode == "shallow":
                        if "historical" in local_uri:
                            # TODO: remove hack
                            local_uri_project = local_uri.replace("WCRP-universe", "cmip7")
                            json_resource = JsonLdResource(uri=str(local_uri_project))

                            merger = DataMerger(
                                data=json_resource,
                                locally_available=self.locally_available,
                            )
                            merger_result = merger.merge_linked_json()
                            temp_expanded = merger_result[-1]

                        # "shallow" mode: return the object but DON'T resolve its nested IDs
                        # Just return the raw data without any resolution
                        return resolved
                    else:  # "full"
                        # "full" mode: recursively resolve any nested references in the resolved data
                        # Create a new DataMerger with the nested object's context to properly
                        # apply its resolve modes
                        nested_merger = DataMerger(
                            data=temp_resource,
                            allowed_base_uris=self.allowed_base_uris,
                            locally_available=self.locally_available,
                            config=self.config,
                        )
                        return nested_merger.resolve_nested_ids(
                            resolved, temp_expanded, new_visited, _is_root_call=False, resolve_mode="full"
                        )

                except Exception as e:
                    property_msg = f"  Property: '{_current_property}'\n" if _current_property else ""
                    logger.warning(
                        f"Cannot resolve ID reference: Exception during resolution\n"
                        f"  Current term: {self.data.uri}\n"
                        f"{property_msg}"
                        f"  String value: '{data}'\n"
                        f"  Expected URI: {uri}\n"
                        f"  Error: {e}\n"
                        f"  → Keeping as unresolved string"
                    )
                    return data

            # Regular primitive values are returned as-is
            return data

    def resolve_merged_ids(self, merged_data: dict, context_base_path: str | None = None) -> dict:
        """
        Resolve nested IDs in merged data by re-expanding it with proper context.

        This is needed because merged data may contain fields from the parent term
        that aren't in the original term's context.

        Args:
            merged_data: The merged dictionary from merge_linked_json()
            context_base_path: Base path containing context directories. If None,
                              attempts to infer from locally_available mappings.

        Returns:
            Dictionary with all nested IDs resolved to full objects
        """
        import json
        import tempfile
        from pathlib import Path

        # Determine the base path for context
        if context_base_path is None:
            # Try to infer from locally_available - use first available path
            # Preferring the CMIP tables path for backward compatibility
            if "https://espri-mod.github.io/mip-cmor-tables" in self.locally_available:
                context_base_path = self.locally_available["https://espri-mod.github.io/mip-cmor-tables"]
            elif self.locally_available:
                # Use first available local path
                context_base_path = next(iter(self.locally_available.values()))
            else:
                # No local paths available, fallback to regular resolution
                return self.resolve_nested_ids(merged_data)

        # Find the data descriptor directory from merged_data type
        data_descriptor = merged_data.get("type", "")
        if not data_descriptor:
            return self.resolve_nested_ids(merged_data)

        context_dir = Path(context_base_path) / data_descriptor

        if not context_dir.exists():
            # Fallback if directory doesn't exist
            return self.resolve_nested_ids(merged_data)

        # Create temp file in the universe data descriptor directory
        # This ensures JsonLdResource picks up the correct context
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, dir=str(context_dir)) as tmp:
            json.dump(merged_data, tmp)
            tmp_path = tmp.name

        try:
            # Create new resource with proper context expansion
            merged_resource = JsonLdResource(uri=tmp_path)
            merged_expanded = merged_resource.expanded
            if isinstance(merged_expanded, list) and len(merged_expanded) > 0:
                merged_expanded = merged_expanded[0]

            # Resolve with correct expansion
            return self.resolve_nested_ids(merged_data, expanded_data=merged_expanded)
        finally:
            Path(tmp_path).unlink()

    def _fetch_referenced_term(self, uri: str) -> dict:
        """
        Fetch a term from URI and return its data.

        This method:
        1. Checks the cache first
        2. Tries the direct local path
        3. Tries alternate directories (for grid files)
        4. Falls back to remote fetch if needed

        IMPORTANT: This method reads the JSON file directly without creating
        a JsonLdResource to avoid triggering expansion which could cause
        infinite recursion during nested ID resolution.

        Args:
            uri: The URI of the term to fetch

        Returns:
            The term data as a dictionary

        Raises:
            FileNotFoundError: If the term cannot be found locally or remotely
        """
        import json
        import os
        from pathlib import Path

        # Check cache first
        cached = self.term_cache.get(uri)
        if cached is not None:
            return cached

        # Convert to local path
        resolved_uri = self.uri_resolver.to_local_path(uri)

        # Try to read the file directly
        if os.path.exists(resolved_uri):
            with open(resolved_uri, "r") as f:
                data = json.load(f)
                self.term_cache.put(uri, data)
                return data

        # File doesn't exist at the expanded path
        # Try to find it in other data descriptor directories
        filename = self.uri_resolver.get_filename(resolved_uri)
        parts = Path(resolved_uri).parts
        if len(parts) >= self.config.min_path_parts:
            base_dir = Path(*parts[:-2])  # Remove data_descriptor and filename

            # Try common data descriptor directories for grids
            for alt_dir in self.config.fallback_dirs:
                alt_path = base_dir / alt_dir / filename
                if os.path.exists(alt_path):
                    with open(alt_path, "r") as f:
                        data = json.load(f)
                        self.term_cache.put(uri, data)
                        return data

        # Last resort: try to fetch remotely
        try:
            import requests

            response = requests.get(uri, headers={"accept": "application/json"}, verify=self.config.verify_ssl)
            if response.status_code == 200:
                data = response.json()
                self.term_cache.put(uri, data)
                return data
            else:
                raise FileNotFoundError(f"Could not find term at {uri}. HTTP status: {response.status_code}")
        except Exception as e:
            raise FileNotFoundError(
                f"Could not find or fetch term at {uri}. Tried local path: {resolved_uri}. Error: {e}"
            ) from e


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

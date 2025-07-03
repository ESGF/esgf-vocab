from typing import Any, Dict, List, Optional, Union
from collections import defaultdict
from esgvoc.api.data_descriptors.known_branded_variable import KnownBrandedVariable


def create_nested_structure(
    terms: List[KnownBrandedVariable], 
    group_by_keys: List[str],
    metadata_config: Optional[Dict[str, List[str]]] = None
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
    
    def _build_nested_dict(current_terms: List[KnownBrandedVariable], 
                          remaining_keys: List[str], 
                          level: int) -> Dict[str, Any]:
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
                    result[group_value]['items'] = [term.model_dump() for term in group_terms]
            else:
                result[group_value] = _build_nested_dict(group_terms, remaining_keys.copy(), level + 1)
        
        return result
    
    return _build_nested_dict(terms, group_by_keys.copy(), 0)


def beta_structure(terms: List[KnownBrandedVariable]) -> Dict[str, Any]:
    """
    Create the beta structure with CF Standard Name and VariableRootName grouping.
    
    Args:
        terms: List of KnownBrandedVariable terms
        
    Returns:
        Nested dictionary with the beta structure format
    """
    metadata_config = {
        0: ['cf_units', 'cf_sn_status'],  # CF Standard Name level
        1: ['var_def_qualifier']          # Variable Root Name level
    }
    
    group_by_keys = ['cf_standard_name', 'variable_root_name']
    
    nested_data = create_nested_structure(terms, group_by_keys, metadata_config)
    
    def _transform_to_beta_format(data: Dict[str, Any]) -> Dict[str, Any]:
        result = {"standard_name": {}}
        
        for std_name, std_data in data.items():
            if isinstance(std_data, dict):
                result["standard_name"][std_name] = {
                    "units": std_data.get("cf_units", ""),
                    "sn_status": std_data.get("cf_sn_status", ""),
                    "variable_root_name": {}
                }
                
                for var_name, var_data in std_data.items():
                    if var_name in ["cf_units", "cf_sn_status"]:
                        continue
                        
                    if isinstance(var_data, dict):
                        result["standard_name"][std_name]["variable_root_name"][var_name] = {
                            "var_def_qualifier": var_data.get("var_def_qualifier", ""),
                            "branding_suffix": {}
                        }
                        
                        for suffix_name, suffix_data in var_data.items():
                            if suffix_name == "var_def_qualifier":
                                continue
                                
                            if isinstance(suffix_data, list):
                                for term_data in suffix_data:
                                    if isinstance(term_data, dict):
                                        suffix_key = term_data.get("branding_suffix_name", "")
                                        if suffix_key:
                                            result["standard_name"][std_name]["variable_root_name"][var_name]["branding_suffix"][suffix_key] = {
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
                                                "realm": term_data.get("realm", "")
                                            }
        
        return result
    
    return _transform_to_beta_format(nested_data)
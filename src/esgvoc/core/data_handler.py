import os
import json
import logging
from functools import cached_property
from typing import Any, Optional, Dict
import requests
from pyld import jsonld
from pydantic import BaseModel, model_validator, ConfigDict

from esgvoc.api.data_descriptors import DATA_DESCRIPTOR_CLASS_MAPPING

# Configure logging
_LOGGER = logging.getLogger(__name__)

mapping = DATA_DESCRIPTOR_CLASS_MAPPING


def unified_document_loader(uri: str) -> Dict:
    """Load a document from a local file or a remote URI."""
    if uri.startswith(("http://", "https://")):
        response = requests.get(uri, headers={"accept": "application/json"}, verify=False)
        if response.status_code == 200:
            return response.json()
        else:
            _LOGGER.error(f"Failed to fetch remote document: {response.status_code} - {response.text}")
            return {}
    else:
        with open(uri, "r") as f:
            return json.load(f)


class JsonLdResource(BaseModel):
    uri: str
    local_path: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @model_validator(mode="before")
    @classmethod
    def set_local_path(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Set the local path to an absolute path if provided."""
        local_path = values.get("local_path")
        if local_path:
            values["local_path"] = os.path.abspath(local_path) + "/"
        jsonld.set_document_loader(
            lambda uri, options: {
                "contextUrl": None,  # No special context URL
                "documentUrl": uri,  # The document's actual URL
                # The parsed JSON-LD document
                "document": unified_document_loader(uri),
            }
        )
        return values

    @cached_property
    def json_dict(self) -> Dict:
        """Fetch the original JSON data."""
        _LOGGER.debug(f"Fetching JSON data from {self.uri}")
        return unified_document_loader(self.uri)

    def _preprocess_nested_contexts(self, data: dict, context: dict) -> dict:
        """
        Pre-process data to resolve @base in nested @context definitions.
        This works around pyld's limitation with scoped contexts.

        Args:
            data: The JSON-LD data to preprocess
            context: The @context dictionary

        Returns:
            Preprocessed data with resolved nested contexts
        """
        if not isinstance(data, dict):
            return data

        result = {}

        for key, value in data.items():
            if key == "@context":
                result[key] = value
                continue

            # Check if this term has a nested @context with @base
            term_def = context.get(key, {})
            if isinstance(term_def, dict) and "@context" in term_def:
                nested_context = term_def["@context"]
                base_url = nested_context.get("@base", "")

                # If the value is a string and we have a @base, prepend it
                if isinstance(value, str) and base_url and term_def.get("@type") == "@id":
                    # Don't prepend if it's already an absolute URL
                    if not value.startswith("http://") and not value.startswith("https://"):
                        # Return as {"@id": "full_url"} to preserve @id semantics
                        result[key] = {"@id": base_url + value}
                    else:
                        result[key] = {"@id": value}
                elif isinstance(value, list):
                    # Process each item in the list
                    result[key] = []
                    for item in value:
                        if isinstance(item, dict):
                            result[key].append(self._preprocess_nested_contexts(item, context))
                        else:
                            result[key].append(item)
                elif isinstance(value, dict):
                    result[key] = self._preprocess_nested_contexts(value, context)
                else:
                    result[key] = value
            elif isinstance(value, list):
                # Process each item in the list
                result[key] = []
                for item in value:
                    if isinstance(item, dict):
                        result[key].append(self._preprocess_nested_contexts(item, context))
                    else:
                        result[key].append(item)
            elif isinstance(value, dict):
                result[key] = self._preprocess_nested_contexts(value, context)
            else:
                result[key] = value

        return result

    @cached_property
    def expanded(self) -> Any:
        """Expand the JSON-LD data with preprocessing for nested contexts."""
        _LOGGER.debug(f"Expanding JSON-LD data for {self.uri}")

        # Get the data and context
        data = self.json_dict

        # Get the context - it should already be the inner dictionary
        context_dict = self.context
        if isinstance(context_dict, dict) and "@context" in context_dict:
            context_dict = context_dict["@context"]

        # Preprocess to handle nested contexts with @base
        preprocessed = self._preprocess_nested_contexts(data, context_dict)

        # Add the context back if it was in the original data
        if "@context" in data:
            preprocessed["@context"] = data["@context"]

        # Expand the preprocessed data
        return jsonld.expand(preprocessed, options={"base": self.uri})

    @cached_property
    def context(self) -> Dict:
        """Fetch and return the JSON content of the '@context'."""

        context_data = JsonLdResource(uri="/".join(self.uri.split("/")[:-1]) + "/" + self.json_dict["@context"])
        # Works only in relative path declaration

        context_value = context_data.json_dict
        if isinstance(context_value, str):
            # It's a URI, fetch it
            _LOGGER.info(f"Fetching context from URI: {context_value}")
            return unified_document_loader(context_value)
        elif isinstance(context_value, dict):
            # Embedded context
            _LOGGER.info("Using embedded context.")
            return context_value
        else:
            _LOGGER.warning("No valid '@context' found.")
            return {}

    @cached_property
    def normalized(self) -> str:
        """Normalize the JSON-LD data."""
        _LOGGER.info(f"Normalizing JSON-LD data for {self.uri}")
        return jsonld.normalize(self.uri, options={"algorithm": "URDNA2015", "format": "application/n-quads"})

    @cached_property
    def python(self) -> Optional[Any]:
        """Map the data to a Pydantic model based on URI."""
        _LOGGER.info(f"Mapping data to a Pydantic model for {self.uri}")
        model_key = self._extract_model_key(self.uri)
        if model_key and model_key in mapping:
            model = mapping[model_key]
            return model(**self.json_dict)
        _LOGGER.warning(f"No matching model found for key: {model_key}")
        return None

    def _extract_model_key(self, uri: str) -> Optional[str]:
        """Extract a model key from the URI."""
        parts = uri.strip("/").split("/")
        if len(parts) >= 2:
            return parts[-2]
        return None

    @property
    def info(self) -> str:
        """Return a detailed summary of the data."""
        res = f"{'#' * 100}\n"
        res += f"###   {self.uri.split('/')[-1]}   ###\n"
        res += f"JSON Version:\n {json.dumps(self.json_dict, indent=2)}\n"
        res += f"URI: {self.uri}\n"
        res += f"JSON Version:\n {json.dumps(self.json_dict, indent=2)}\n"
        res += f"Expanded Version:\n {json.dumps(self.expanded, indent=2)}\n"
        res += f"Normalized Version:\n {self.normalized}\n"
        res += f"Pydantic Model Instance:\n {self.python}\n"
        return res


if __name__ == "__main__":
    # For Universe
    # online
    # d = Data(uri = "https://espri-mod.github.io/mip-cmor-tables/activity/cmip.json")
    # print(d.info)
    # offline
    # print(Data(uri = ".cache/repos/mip-cmor-tables/activity/cmip.json").info)
    # for Project
    # d = Data(uri = "https://espri-mod.github.io/CMIP6Plus_CVs/activity_id/cmip.json")
    # print(d.info)
    # offline
    print(JsonLdResource(uri=".cache/repos/CMIP6Plus_CVs/activity_id/cmip.json").info)

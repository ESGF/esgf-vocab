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
                "document": unified_document_loader(uri),  # The parsed JSON-LD document
            }
        )
        return values

    @cached_property
    def json_dict(self) -> Dict:
        """Fetch the original JSON data."""
        _LOGGER.debug(f"Fetching JSON data from {self.uri}")
        return unified_document_loader(self.uri)

    @cached_property
    def expanded(self) -> Any:
        """Expand the JSON-LD data."""
        _LOGGER.debug(f"Expanding JSON-LD data for {self.uri}")
        return jsonld.expand(self.uri, options={"base": self.uri})

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
    ## For Universe
    # online
    # d = Data(uri = "https://espri-mod.github.io/mip-cmor-tables/activity/cmip.json")
    # print(d.info)
    # offline
    # print(Data(uri = ".cache/repos/mip-cmor-tables/activity/cmip.json").info)
    ## for Project
    # d = Data(uri = "https://espri-mod.github.io/CMIP6Plus_CVs/activity_id/cmip.json")
    # print(d.info)
    # offline
    print(JsonLdResource(uri=".cache/repos/CMIP6Plus_CVs/activity_id/cmip.json").info)

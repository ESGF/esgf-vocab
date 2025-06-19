import logging
from typing import Dict, List, Set

from esgvoc.core.data_handler import JsonLdResource

logger = logging.getLogger(__name__)


def merge_dicts(original: list, custom: list) -> dict:
    """Shallow merge: Overwrites original data with custom data."""
    b = original[0]
    a = custom[0]
    merged = {**{k: v for k, v in a.items() if k != "@id"}, **{k: v for k, v in b.items() if k != "@id"}}
    return merged


def merge(uri: str) -> Dict:
    mdm = DataMerger(data=JsonLdResource(uri=uri))
    return mdm.merge_linked_json()[-1]


class DataMerger:
    def __init__(
        self,
        data: JsonLdResource,
        allowed_base_uris: Set[str] = {"https://espri-mod.github.io/mip-cmor-tables"},
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
        try:
            """Fetch and merge data recursively, returning a list of progressively merged Data json instances."""
            result_list = [self.data.json_dict]  # Start with the original json object
            visited = set(self.data.uri)  # Track visited URIs to prevent cycles
            current_data = self.data
            # print(current_data.expanded)
            while True:
                next_id = self._get_next_id(current_data.expanded[0])

                if not next_id or next_id in visited or not self._should_resolve(next_id):
                    break

                visited.add(next_id)

                # Fetch and merge the next customization
                # do we have it in local ? if so use it instead of remote
                for local_repo in self.locally_available.keys():
                    if next_id.startswith(local_repo):
                        next_id = next_id.replace(local_repo, self.locally_available[local_repo])

                next_data_instance = JsonLdResource(uri=next_id)
                merged_json_data = merge_dicts([current_data.json_dict], [next_data_instance.json_dict])
                next_data_instance.json_dict = merged_json_data

                # Add the merged instance to the result list
                result_list.append(merged_json_data)
                current_data = next_data_instance
            return result_list
        except Exception as e:
            print(self.data)
            print(e)


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

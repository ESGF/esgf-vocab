"""URI resolution and path normalization for JSON-LD references."""

import os
from pathlib import Path
from typing import Dict


class URIResolver:
    """
    Handles URI normalization and conversion between remote URLs and local paths.

    This class centralizes all URI-related operations, making it easy to:
    - Convert remote URIs to local file paths
    - Normalize URIs (e.g., ensure .json extension)
    - Check if resolved paths exist
    """

    def __init__(self, locally_available: Dict[str, str]):
        """
        Initialize the URI resolver.

        Args:
            locally_available: Mapping from remote base URIs to local directory paths.
                               Example: {"https://example.com/data": "/local/cache/data"}
        """
        self.locally_available = locally_available

    def to_local_path(self, uri: str) -> str:
        """
        Convert a remote URI to a local file path if a mapping exists.

        Args:
            uri: The URI to resolve (remote or already local)

        Returns:
            Local file path if a mapping exists, otherwise the original URI

        Example:
            >>> resolver = URIResolver({"https://example.com": "/local/cache"})
            >>> resolver.to_local_path("https://example.com/data/term.json")
            '/local/cache/data/term.json'
        """
        for remote_base, local_base in self.locally_available.items():
            if uri.startswith(remote_base):
                return uri.replace(remote_base, local_base)
        return uri

    def ensure_json_extension(self, uri: str) -> str:
        """
        Ensure the URI ends with .json extension.

        Args:
            uri: The URI to normalize

        Returns:
            URI with .json extension

        Example:
            >>> resolver = URIResolver({})
            >>> resolver.ensure_json_extension("https://example.com/term")
            'https://example.com/term.json'
        """
        return uri if uri.endswith(".json") else f"{uri}.json"

    def normalize(self, uri: str) -> str:
        """
        Fully normalize a URI: convert to local path and ensure .json extension.

        Args:
            uri: The URI to normalize

        Returns:
            Normalized local path with .json extension

        Example:
            >>> resolver = URIResolver({"https://example.com": "/local"})
            >>> resolver.normalize("https://example.com/term")
            '/local/term.json'
        """
        uri = self.ensure_json_extension(uri)
        return self.to_local_path(uri)

    def exists(self, uri: str) -> bool:
        """
        Check if a URI resolves to an existing local file.

        Args:
            uri: The URI to check

        Returns:
            True if the resolved path exists as a file

        Example:
            >>> resolver = URIResolver({"https://example.com": "/tmp"})
            >>> resolver.exists("https://example.com/nonexistent")
            False
        """
        local_path = self.normalize(uri)
        return os.path.isfile(local_path)

    def get_filename(self, uri: str) -> str:
        """
        Extract the filename from a URI.

        Args:
            uri: The URI to extract from

        Returns:
            The filename component

        Example:
            >>> resolver = URIResolver({})
            >>> resolver.get_filename("https://example.com/data/term.json")
            'term.json'
        """
        return Path(uri).name

    def get_parent_dir(self, uri: str) -> Path:
        """
        Get the parent directory of a URI's resolved path.

        Args:
            uri: The URI to extract from

        Returns:
            Path object representing the parent directory

        Example:
            >>> resolver = URIResolver({})
            >>> resolver.get_parent_dir("/local/data/term.json")
            PosixPath('/local/data')
        """
        return Path(self.to_local_path(uri)).parent

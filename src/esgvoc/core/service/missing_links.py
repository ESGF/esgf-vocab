"""Tracker for missing @id references during database ingestion."""

from dataclasses import dataclass, field
from typing import List, Optional

from esgvoc.core.exceptions import EsgvocMissingLinksError


@dataclass
class MissingLinkInfo:
    """Information about a missing @id reference."""

    ingestion_context: str
    """Context where the missing link was found (e.g., 'universe' or 'project:cmip7')"""

    current_term: str
    """The URI/path of the term being processed when the missing link was found"""

    string_value: str
    """The string value that could not be resolved"""

    expected_uri: str
    """The full URI that was expected to exist"""

    local_path: str
    """The local path that was tried"""

    property_name: Optional[str] = None
    """The property name where the missing link was found (if available)"""


@dataclass
class MissingLinksTracker:
    """
    Tracks missing @id references during database ingestion.

    When fail_on_missing_links is enabled, this tracker collects all missing
    links encountered during ingestion and prints a summary at the end.
    """

    missing_links: List[MissingLinkInfo] = field(default_factory=list)
    """List of all missing links found during ingestion"""

    def add(self, link: MissingLinkInfo) -> None:
        """Add a missing link to the tracker."""
        self.missing_links.append(link)

    def add_from_params(
        self,
        ingestion_context: str,
        current_term: str,
        string_value: str,
        expected_uri: str,
        local_path: str,
        property_name: Optional[str] = None,
    ) -> None:
        """Add a missing link using individual parameters."""
        self.add(
            MissingLinkInfo(
                ingestion_context=ingestion_context,
                current_term=current_term,
                string_value=string_value,
                expected_uri=expected_uri,
                local_path=local_path,
                property_name=property_name,
            )
        )

    def has_missing_links(self) -> bool:
        """Check if any missing links have been recorded."""
        return len(self.missing_links) > 0

    def check_and_raise(self) -> None:
        """Raise EsgvocMissingLinksError if any missing links were found."""
        if self.has_missing_links():
            raise EsgvocMissingLinksError(self.missing_links)

    def print_summary(self) -> bool:
        """Print a summary of missing links and return True if any were found."""
        if not self.has_missing_links():
            return False

        print(f"\nFound {len(self.missing_links)} unresolved @id reference(s):")
        for link in self.missing_links:
            print(f"  - Context: {link.ingestion_context}")
            print(f"    Term: {link.current_term}")
            if link.property_name:
                print(f"    Property: {link.property_name}")
            print(f"    Missing ID: {link.string_value}")
            print(f"    Expected URI: {link.expected_uri}")
            print()
        return True

    def clear(self) -> None:
        """Clear all recorded missing links."""
        self.missing_links.clear()

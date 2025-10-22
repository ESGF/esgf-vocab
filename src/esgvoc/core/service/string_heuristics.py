"""Heuristics for determining if strings should be resolved as ID references."""

from typing import List


class StringHeuristics:
    """
    Determine if a string value should be resolved as an ID reference.

    Uses configurable heuristics to distinguish between:
    - ID references (e.g., "hadgem3_gc31_atmosphere") - should resolve
    - Literal strings (e.g., "A long description...") - should not resolve
    - URLs (e.g., "https://doi.org/...") - should not resolve
    """

    def __init__(self, max_length: int = 100, exclude_patterns: List[str] | None = None):
        """
        Initialize string heuristics.

        Args:
            max_length: Maximum length for strings to be considered as ID references.
                       Longer strings are assumed to be content, not references.
            exclude_patterns: Patterns that disqualify a string from being an ID reference.
                            Defaults to [" ", ".", "http", "/", "@"] which filter out
                            descriptions, URLs, DOIs, paths, and emails.
        """
        self.max_length = max_length
        self.exclude_patterns = exclude_patterns or [" ", ".", "http", "/", "@"]

    def is_resolvable(self, value: str) -> bool:
        """
        Check if a string looks like an ID reference that should be resolved.

        Args:
            value: The string to evaluate

        Returns:
            True if the string appears to be an ID reference, False otherwise

        Example:
            >>> heuristics = StringHeuristics()
            >>> heuristics.is_resolvable("hadgem3_gc31_atmosphere")
            True
            >>> heuristics.is_resolvable("This is a long description text")
            False
            >>> heuristics.is_resolvable("https://doi.org/10.5194/gmd")
            False
        """
        # Check length
        if len(value) > self.max_length:
            return False

        # Check for exclude patterns
        for pattern in self.exclude_patterns:
            if pattern in value:
                return False

        return True

    def should_skip_literal(self, expanded_data: dict) -> bool:
        """
        Check if the expanded data indicates this is a literal value (not a reference).

        In JSON-LD, literal values are marked with @value in expanded form.

        Args:
            expanded_data: The expanded JSON-LD data

        Returns:
            True if this is a literal value that should not be resolved

        Example:
            >>> heuristics = StringHeuristics()
            >>> heuristics.should_skip_literal({"@value": "some text"})
            True
            >>> heuristics.should_skip_literal({"@id": "some_term"})
            False
        """
        return isinstance(expanded_data, dict) and "@value" in expanded_data

    def has_id_in_expanded(self, expanded_data: dict) -> bool:
        """
        Check if the expanded data contains an @id, indicating it's a reference.

        Args:
            expanded_data: The expanded JSON-LD data

        Returns:
            True if the expanded data has an @id field

        Example:
            >>> heuristics = StringHeuristics()
            >>> heuristics.has_id_in_expanded({"@id": "https://example.com/term"})
            True
            >>> heuristics.has_id_in_expanded({"@value": "literal"})
            False
        """
        return isinstance(expanded_data, dict) and "@id" in expanded_data

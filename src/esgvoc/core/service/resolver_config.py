"""Configuration for JSON-LD reference resolution behavior."""

from dataclasses import dataclass, field
from typing import List


@dataclass
class ResolverConfig:
    """
    Configuration for controlling JSON-LD ID reference resolution behavior.

    This class provides fine-grained control over how the DataMerger resolves
    nested @id references, including depth limits, string filtering, and
    file resolution strategies.
    """

    # Recursion control
    max_depth: int = 5
    """Maximum recursion depth when resolving nested references"""

    # String filtering for primitive resolution
    max_string_length: int = 100
    """Maximum length for strings to be considered as ID references"""

    exclude_patterns: List[str] = field(default_factory=lambda: [" ", ".", "http", "/", "@"])
    """Patterns that disqualify a string from being resolved as an ID reference"""

    # File resolution strategies
    fallback_dirs: List[str] = field(default_factory=lambda: ["horizontal_grid", "vertical_grid", "grid"])
    """Alternative directories to search when a term file is not found"""

    min_path_parts: int = 3
    """Minimum number of path components required for alternate directory search"""

    # Network and I/O
    verify_ssl: bool = True
    """Whether to verify SSL certificates when fetching remote resources"""

    enable_caching: bool = True
    """Whether to cache fetched terms to improve performance"""

    cache_size: int = 128
    """Maximum number of terms to cache (when caching is enabled)"""

    # Logging and debugging
    log_depth_warnings: bool = True
    """Whether to log warnings when max_depth is exceeded"""

    def __post_init__(self):
        """Validate configuration values."""
        if self.max_depth < 1:
            raise ValueError("max_depth must be at least 1")
        if self.max_string_length < 1:
            raise ValueError("max_string_length must be at least 1")
        if self.cache_size < 1:
            raise ValueError("cache_size must be at least 1")

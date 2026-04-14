"""
DBArtifact: metadata model for a pre-built versioned database artifact.

This model represents the information fetched from a GitHub Release for a
CV project (cmip7, cmip6, etc.). It is used by DBFetcher to describe what
is available for download and to verify compatibility.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DBArtifact(BaseModel):
    """Metadata for a downloadable pre-built project database."""

    project_id: str
    """e.g. 'cmip7'"""

    version: str
    """Semantic version tag, e.g. 'v2.1.0' or 'dev-latest'"""

    universe_version: Optional[str] = None
    """Universe version embedded in this DB, e.g. 'v1.2.0'"""

    esgvoc_min_version: Optional[str] = None
    """Minimum esgvoc version required to use this DB."""

    esgvoc_max_version: Optional[str] = None
    """Maximum esgvoc version compatible with this DB (None = no upper bound)."""

    published_at: Optional[datetime] = None
    """When this release was published on GitHub."""

    size_bytes: Optional[int] = None
    """File size in bytes."""

    checksum_sha256: Optional[str] = None
    """SHA-256 checksum of the database file."""

    download_url: str
    """Direct download URL for the database file."""

    release_notes: Optional[str] = None
    """Release notes / changelog from the manifest."""

    commit_sha: Optional[str] = None
    """Source commit SHA embedded in the DB (for dev builds)."""

    is_prerelease: bool = False
    """True for dev-latest and other pre-release builds."""

    def is_dev_build(self) -> bool:
        return self.version == "dev-latest" or self.is_prerelease

    def db_filename(self) -> str:
        """Canonical filename for this artifact on disk."""
        return f"{self.project_id}-{self.version}.db"

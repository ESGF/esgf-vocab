"""
GitHub registry: maps project IDs to the esgvoc_dbs artifact repository.

The registry is a single `esgvoc_dbs` GitHub repo that holds:
  - Per-project JSON index files on `main` branch  (fetched via raw content URL)
  - GitHub Releases with `.db` + `.sha256` assets   (one tag per project@version)

Tag format: `{project_id}.{version}`  (e.g. `cmip7.v1.2.7`)

The raw index URL for a project is:
  {REGISTRY_BASE_URL}/{project_id}.json

Default REGISTRY_BASE_URL: https://raw.githubusercontent.com/WCRP-CMIP/esgvoc_dbs/main
Override via env var: ESGVOC_REGISTRY_BASE_URL

Custom/private projects can be registered at runtime via register_project().
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

# ---------------------------------------------------------------------------
# Registry base URL (overridable via env var for testing / enterprise)
# ---------------------------------------------------------------------------

_DEFAULT_REGISTRY_BASE = "https://raw.githubusercontent.com/WCRP-CMIP/esgvoc_dbs/main"
_REGISTRY_REPO = "WCRP-CMIP/esgvoc_dbs"

REGISTRY_BASE_URL: str = os.environ.get("ESGVOC_REGISTRY_BASE_URL", _DEFAULT_REGISTRY_BASE)
"""Base URL for fetching per-project JSON index files.

Set ESGVOC_REGISTRY_BASE_URL to override (e.g. for a test repo or enterprise fork).
"""


def get_registry_base_url() -> str:
    """Return the current registry base URL (reads env var at call time)."""
    return os.environ.get("ESGVOC_REGISTRY_BASE_URL", _DEFAULT_REGISTRY_BASE)


# ---------------------------------------------------------------------------
# ProjectInfo
# ---------------------------------------------------------------------------

@dataclass
class ProjectInfo:
    """Metadata for a known esgvoc project."""

    project_id: str
    """Short identifier, e.g. 'cmip7'"""

    name: str = ""
    """Human-readable name."""

    @property
    def raw_index_url(self) -> str:
        """URL to the per-project JSON index file on the registry repo main branch."""
        base = get_registry_base_url()
        return f"{base.rstrip('/')}/{self.project_id}.json"

    def release_tag(self, version: str) -> str:
        """Canonical release tag for a project+version: `{project_id}.{version}`."""
        return f"{self.project_id}.{version}"


# ---------------------------------------------------------------------------
# Official project registry
# ---------------------------------------------------------------------------

_REGISTRY: dict[str, ProjectInfo] = {
    p.project_id: p
    for p in [
        ProjectInfo("universe", "WCRP Universe"),
        ProjectInfo("cmip7", "CMIP7 Controlled Vocabulary"),
        ProjectInfo("cmip6", "CMIP6 Controlled Vocabulary"),
        ProjectInfo("cmip6plus", "CMIP6Plus Controlled Vocabulary"),
        ProjectInfo("input4mips", "input4MIPs Controlled Vocabulary"),
        ProjectInfo("obs4ref", "obs4REF Controlled Vocabulary"),
        ProjectInfo("cordex-cmip6", "CORDEX-CMIP6 Controlled Vocabulary"),
        ProjectInfo("cordex-cmip5", "CORDEX-CMIP5 Controlled Vocabulary"),
        ProjectInfo("emd", "EMD Controlled Vocabulary"),
    ]
}


def get_project(project_id: str) -> Optional[ProjectInfo]:
    """Return project info or None if unknown."""
    return _REGISTRY.get(project_id)


def get_all_projects() -> list[ProjectInfo]:
    """Return all registered projects."""
    return list(_REGISTRY.values())


def register_project(
    project_id: str,
    name: str = "",
) -> None:
    """Register a custom or private project at runtime."""
    _REGISTRY[project_id] = ProjectInfo(
        project_id=project_id,
        name=name,
    )


def known_project_ids() -> list[str]:
    """Return all registered project IDs."""
    return list(_REGISTRY.keys())

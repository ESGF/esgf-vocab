"""
Project registry: maps project IDs to their GitHub repositories.

This is the single source of truth for known projects. DBFetcher uses this
to know where to look for GitHub Releases.

Custom/private projects can be registered at runtime via register_project().
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ProjectInfo:
    """Metadata for a known esgvoc project."""

    project_id: str
    """Short identifier, e.g. 'cmip7'"""

    github_repo: str
    """Owner/repo, e.g. 'WCRP-CMIP/CMIP7-CVs'"""

    name: str = ""
    """Human-readable name."""

    github_base_url: str = "https://github.com"
    """Base URL (override for GitHub Enterprise)."""

    @property
    def api_base(self) -> str:
        """Base URL for the GitHub REST API for this repo."""
        if self.github_base_url == "https://github.com":
            return f"https://api.github.com/repos/{self.github_repo}"
        # GitHub Enterprise: replace domain with api.domain
        domain = self.github_base_url.removeprefix("https://")
        return f"https://{domain}/api/v3/repos/{self.github_repo}"


# Official project registry
_REGISTRY: dict[str, ProjectInfo] = {
    p.project_id: p
    for p in [
        ProjectInfo("universe", "WCRP-CMIP/WCRP-universe", "WCRP Universe"),
        ProjectInfo("cmip7", "WCRP-CMIP/CMIP7-CVs", "CMIP7 Controlled Vocabulary"),
        ProjectInfo("cmip6", "WCRP-CMIP/CMIP6_CVs", "CMIP6 Controlled Vocabulary"),
        ProjectInfo("cmip6plus", "WCRP-CMIP/CMIP6Plus_CVs", "CMIP6Plus Controlled Vocabulary"),
        ProjectInfo("input4mips", "PCMDI/input4MIPs_CVs", "input4MIPs Controlled Vocabulary"),
        ProjectInfo("obs4ref", "Climate-REF/Obs4REF_CVs", "obs4REF Controlled Vocabulary"),
        ProjectInfo("cordex-cmip6", "WCRP-CORDEX/cordex-cmip6-cv", "CORDEX-CMIP6 Controlled Vocabulary"),
        ProjectInfo("cordex-cmip5", "WCRP-CORDEX/cordex-cmip5", "CORDEX-CMIP5 Controlled Vocabulary"),
        ProjectInfo("emd", "WCRP-CMIP/Essential-Model-Documentation", "EMD Controlled Vocabulary"),
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
    github_repo: str,
    name: str = "",
    github_base_url: str = "https://github.com",
) -> None:
    """Register a custom or private project at runtime."""
    _REGISTRY[project_id] = ProjectInfo(
        project_id=project_id,
        github_repo=github_repo,
        name=name,
        github_base_url=github_base_url,
    )


def known_project_ids() -> list[str]:
    return list(_REGISTRY.keys())

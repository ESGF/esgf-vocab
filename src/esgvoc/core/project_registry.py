"""
Backward-compatibility shim.

project_registry has been renamed to github_registry.
Import from esgvoc.core.github_registry directly.
"""
from esgvoc.core.github_registry import (  # noqa: F401
    ProjectInfo,
    get_project,
    get_all_projects,
    register_project,
    known_project_ids,
    get_registry_base_url,
    REGISTRY_BASE_URL,
)

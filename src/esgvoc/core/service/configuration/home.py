"""
EsgvocHome: manages the root directory for all esgvoc data.

Resolution order:
1. ESGVOC_HOME environment variable (absolute or relative path)
2. PlatformDirs default (~/.local/share/esgvoc/ on Linux)

Storage layout:
    {home}/
    ├── dbs/
    │   ├── cmip7/              # per-project DB subdir
    │   │   ├── v2.1.0.db       # registry download
    │   │   ├── v2.0.0.db       # registry download
    │   │   └── my-exp.db       # local build
    │   ├── cmip7.active.json   # pointer file  {"active": "v2.1.0", "source": "registry", ...}
    │   ├── cmip6/
    │   └── cmip6.active.json
    ├── admin/                  # Admin: build artifacts
    │   └── builds/
    └── dev/                    # Dev: source-based configs (legacy, kept for admin build)
        └── {config_name}/
            ├── dbs/
            └── repos/

Cache (separate XDG location):
    ~/.cache/esgvoc/
        registry_cmip7.json     # transient, safely deletable

Usage:
    from esgvoc.core.service.configuration.home import EsgvocHome
    home = EsgvocHome.resolve()
    home.dbs_dir                        # Path to all DBs root
    home.dbs_project_dir("cmip7")       # Path to cmip7 DB subdir
    home.dbs_pointer_file("cmip7")      # Path to cmip7.active.json
    home.registry_cache_dir             # Path to registry cache (~/.cache/esgvoc/)
"""

import os
from pathlib import Path

from platformdirs import PlatformDirs

ENV_VAR = "ESGVOC_HOME"
_APP_NAME = "esgvoc"
_APP_AUTHOR = "ipsl"


class EsgvocHome:
    """Root directory manager for all esgvoc data.

    All paths are absolute and created on first access.
    """

    def __init__(self, root: Path):
        self.root = root.resolve()

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def resolve(cls) -> "EsgvocHome":
        """Resolve the home directory from ESGVOC_HOME env var or PlatformDirs."""
        env = os.environ.get(ENV_VAR)
        if env:
            root = Path(env)
            if not root.is_absolute():
                root = Path.cwd() / root
        else:
            dirs = PlatformDirs(_APP_NAME, _APP_AUTHOR)
            root = Path(dirs.user_data_path)

        return cls(root)

    # ------------------------------------------------------------------
    # New-style DB paths (per-project subdirs + pointer files)
    # ------------------------------------------------------------------

    @property
    def dbs_dir(self) -> Path:
        """Root directory for all project DBs: {home}/dbs/"""
        p = self.root / "dbs"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def dbs_project_dir(self, project_id: str) -> Path:
        """Per-project DB directory: {home}/dbs/{project_id}/"""
        p = self.dbs_dir / project_id
        p.mkdir(parents=True, exist_ok=True)
        return p

    def dbs_pointer_file(self, project_id: str) -> Path:
        """Active-version pointer file: {home}/dbs/{project_id}.active.json"""
        return self.dbs_dir / f"{project_id}.active.json"

    # ------------------------------------------------------------------
    # Registry cache (XDG cache directory)
    # ------------------------------------------------------------------

    @property
    def registry_cache_dir(self) -> Path:
        """Registry JSON cache directory (XDG cache: ~/.cache/esgvoc/)."""
        dirs = PlatformDirs(_APP_NAME, _APP_AUTHOR)
        p = Path(dirs.user_cache_path)
        p.mkdir(parents=True, exist_ok=True)
        return p

    # ------------------------------------------------------------------
    # Backward-compat aliases (user_dbs_dir, user_cache_dir, user_state_file)
    # These point to the new locations so existing code still resolves
    # to useful paths, but callers should migrate to the new properties above.
    # ------------------------------------------------------------------

    @property
    def user_dbs_dir(self) -> Path:
        """Deprecated alias → dbs_dir. Use dbs_project_dir(project_id) instead."""
        return self.dbs_dir

    @property
    def user_state_file(self) -> Path:
        """Deprecated: no single state.json in the new model.
        Returns a path for backward compat only — file is never written by new code."""
        return self.dbs_dir / "_state_legacy.json"

    @property
    def user_cache_dir(self) -> Path:
        """Deprecated alias → registry_cache_dir."""
        return self.registry_cache_dir

    @property
    def user_dir(self) -> Path:
        """Deprecated alias → root (the user-tier is now the root itself)."""
        return self.root

    # ------------------------------------------------------------------
    # Admin Tier paths
    # ------------------------------------------------------------------

    @property
    def admin_dir(self) -> Path:
        p = self.root / "admin"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def admin_builds_dir(self) -> Path:
        p = self.admin_dir / "builds"
        p.mkdir(parents=True, exist_ok=True)
        return p

    # ------------------------------------------------------------------
    # Dev Tier paths (kept for admin build / legacy source-based installs)
    # ------------------------------------------------------------------

    @property
    def dev_dir(self) -> Path:
        p = self.root / "dev"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def dev_config_dir(self, config_name: str) -> Path:
        """Isolated data directory for a named dev config."""
        p = self.dev_dir / config_name
        p.mkdir(parents=True, exist_ok=True)
        return p

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"EsgvocHome(root={self.root})"

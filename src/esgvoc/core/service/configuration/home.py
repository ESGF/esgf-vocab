"""
EsgvocHome: manages the root directory for all esgvoc data.

Resolution order:
1. ESGVOC_HOME environment variable (absolute or relative path)
2. PlatformDirs default (~/.local/share/esgvoc/ on Linux)

Structure inside the home directory:
    {home}/
    ├── user/           # User Tier: pre-built versioned databases
    │   ├── dbs/        # cmip7-v2.1.0.db, cmip6-v6.5.0.db, ...
    │   ├── state.json  # active version per project
    │   └── cache/      # registry_cache.json (GitHub API cache)
    ├── admin/          # Admin Tier: build artifacts, manifests
    │   └── builds/     # temporary build outputs
    └── dev/            # Dev Tier: source-based configs (current system)
        ├── config_registry.toml
        ├── default_setting.toml
        └── {config_name}/
            ├── dbs/
            └── repos/

Usage:
    from esgvoc.core.service.configuration.home import EsgvocHome
    home = EsgvocHome.resolve()
    home.user_dbs_dir  # Path to user tier DBs
    home.dev_dir       # Path to dev tier configs
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
    # User Tier paths
    # ------------------------------------------------------------------

    @property
    def user_dir(self) -> Path:
        p = self.root / "user"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def user_dbs_dir(self) -> Path:
        p = self.user_dir / "dbs"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def user_state_file(self) -> Path:
        return self.user_dir / "state.json"

    @property
    def user_cache_dir(self) -> Path:
        p = self.user_dir / "cache"
        p.mkdir(parents=True, exist_ok=True)
        return p

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
    # Dev Tier paths (current config system)
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

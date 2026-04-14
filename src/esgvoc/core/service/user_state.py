"""
UserState: manages state.json for the User Tier.

state.json tracks which database version is "active" for each project and
which versions are installed on disk.

File location is resolved via EsgvocHome (respects ESGVOC_HOME and
ESGVOC_STATE_FILE env vars).

Example state.json:
{
  "active_versions": {
    "cmip7": "v2.1.0",
    "cmip6": "v6.5.0"
  },
  "installed": {
    "cmip7": ["v2.1.0", "v2.0.0"],
    "cmip6": ["v6.5.0"]
  }
}
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from esgvoc.core.service.configuration.home import EsgvocHome


def _state_file_path() -> Path:
    """Resolve state.json path: ESGVOC_STATE_FILE env var or EsgvocHome default."""
    env = os.environ.get("ESGVOC_STATE_FILE")
    if env:
        return Path(env).resolve()
    return EsgvocHome.resolve().user_state_file


def _dbs_dir() -> Path:
    """Resolve dbs directory: ESGVOC_DB_DIR env var or EsgvocHome default."""
    env = os.environ.get("ESGVOC_DB_DIR")
    if env:
        p = Path(env).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p
    return EsgvocHome.resolve().user_dbs_dir


class UserState:
    """
    Manages the User Tier state.json — active version per project and installed list.

    Usage:
        state = UserState.load()
        state.set_active("cmip7", "v2.1.0")
        state.add_installed("cmip7", "v2.1.0")
        state.save()
    """

    def __init__(self, state_file: Path):
        self._path = state_file
        self._data: dict = {"active_versions": {}, "installed": {}}

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def load(cls) -> "UserState":
        """Load state from disk (creates empty state if file doesn't exist)."""
        path = _state_file_path()
        obj = cls(path)
        if path.exists():
            try:
                obj._data = json.loads(path.read_text())
            except (json.JSONDecodeError, OSError) as e:
                import logging
                logging.getLogger(__name__).warning(f"Could not read state.json: {e}")
        return obj

    # ------------------------------------------------------------------
    # Active versions
    # ------------------------------------------------------------------

    def get_active(self, project_id: str) -> Optional[str]:
        """Return the active version for *project_id*, or None."""
        return self._data.get("active_versions", {}).get(project_id)

    def set_active(self, project_id: str, version: str) -> None:
        self._data.setdefault("active_versions", {})[project_id] = version

    def remove_active(self, project_id: str) -> None:
        self._data.get("active_versions", {}).pop(project_id, None)

    # ------------------------------------------------------------------
    # Installed versions
    # ------------------------------------------------------------------

    def get_installed(self, project_id: str) -> list[str]:
        return list(self._data.get("installed", {}).get(project_id, []))

    def add_installed(self, project_id: str, version: str) -> None:
        installed = self._data.setdefault("installed", {}).setdefault(project_id, [])
        if version not in installed:
            installed.append(version)

    def remove_installed(self, project_id: str, version: str) -> None:
        installed = self._data.get("installed", {}).get(project_id, [])
        if version in installed:
            installed.remove(version)
        if not installed:
            self._data.get("installed", {}).pop(project_id, None)

    def all_project_ids(self) -> list[str]:
        """Return project IDs that have at least one installed version."""
        return list(self._data.get("installed", {}).keys())

    # ------------------------------------------------------------------
    # DB paths
    # ------------------------------------------------------------------

    @staticmethod
    def db_path(project_id: str, version: str) -> Path:
        """Return the expected filesystem path for a given project/version."""
        return _dbs_dir() / f"{project_id}-{version}.db"

    @staticmethod
    def dbs_dir() -> Path:
        return _dbs_dir()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self) -> None:
        """Write state to disk atomically."""
        import tempfile, shutil
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", dir=self._path.parent, suffix=".tmp", delete=False
        ) as tmp:
            json.dump(self._data, tmp, indent=2)
            tmp_path = Path(tmp.name)
        shutil.move(str(tmp_path), str(self._path))

    def dump(self) -> dict:
        """Return a copy of the raw state dict."""
        return dict(self._data)

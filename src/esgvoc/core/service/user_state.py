"""
UserState: manages per-project active state via pointer files.

Each project has:
  - A directory:     {dbs_dir}/{project_id}/
  - A pointer file:  {dbs_dir}/{project_id}.active.json

Pointer file format:
  {
    "active": "v2.1.0",           # name of the active DB (without .db extension)
    "source": "registry",         # "registry" | "local"
    "checksum": "abc123..."       # SHA-256 of the active DB (optional)
  }

DB files sit at:  {dbs_dir}/{project_id}/{name}.db

Name patterns:
  vX.X.X           — registry download  (e.g. v2.1.0)
  latest            — registry download  (special keyword)
  dev-latest        — registry download  (pre-release keyword)
  anything else     — local build         (e.g. my-experiment, local, fix-42)

"Installed" is defined purely by filesystem presence: if
{dbs_dir}/{project_id}/{name}.db exists, the name is installed.

There is no separate install tracking file — the file IS the registration.
add_installed() and remove_installed() are kept for API compatibility
but their semantics change:
  - add_installed(): no-op (file creation IS the install)
  - remove_installed(): deletes the .db file from disk
  - get_installed(): scans the project subdir for *.db files
  - all_project_ids(): scans dbs_dir for subdirs that contain *.db files

Environment variables honoured:
    ESGVOC_HOME     Override esgvoc home directory (EsgvocHome.resolve())
    ESGVOC_DB_DIR   Override the dbs root directory directly
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from esgvoc.core.service.configuration.home import EsgvocHome

_LOGGER = logging.getLogger(__name__)


def _dbs_dir() -> Path:
    """Resolve dbs directory: ESGVOC_DB_DIR env var or EsgvocHome default."""
    env = os.environ.get("ESGVOC_DB_DIR")
    if env:
        p = Path(env).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p
    return EsgvocHome.resolve().dbs_dir


def _project_dir(project_id: str) -> Path:
    """Return (and create) the per-project DB subdirectory."""
    p = _dbs_dir() / project_id
    p.mkdir(parents=True, exist_ok=True)
    return p


def _pointer_file(project_id: str) -> Path:
    """Return the path to the project's active pointer file."""
    return _dbs_dir() / f"{project_id}.active.json"


def _atomic_write(path: Path, content: str) -> None:
    """Write *content* to *path* atomically via a temp file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, suffix=".tmp", delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    shutil.move(str(tmp_path), str(path))


# ---------------------------------------------------------------------------
# UserState
# ---------------------------------------------------------------------------


class UserState:
    """
    Manages per-project active state via pointer files.

    The new model writes state directly to per-project pointer files on every
    mutation — there is no in-memory buffer and no explicit save() step.
    The load() factory and save() method are retained for API compatibility
    with existing callers; both are effectively no-ops.

    Usage:
        state = UserState.load()
        state.set_active("cmip7", "v2.1.0")          # writes pointer file
        state.add_installed("cmip7", "v2.1.0")        # no-op
        # state.save() is a no-op — mutations are already persisted
    """

    @classmethod
    def load(cls) -> "UserState":
        """Return a UserState instance. Mutations are written directly to disk."""
        return cls()

    def save(self) -> None:
        """No-op: mutations are written to disk immediately via pointer files."""
        pass

    def dump(self) -> dict:
        """
        Return a summary dict for all known projects (reads pointer files).

        Note: this is not a serialisable state blob — it's for debugging / display.
        """
        dbs = _dbs_dir()
        result: dict = {"active_versions": {}, "installed": {}}
        if not dbs.exists():
            return result
        for subdir in sorted(dbs.iterdir()):
            if not subdir.is_dir():
                continue
            pid = subdir.name
            installed = [p.stem for p in sorted(subdir.glob("*.db"))]
            if installed:
                result["installed"][pid] = installed
            active = self.get_active(pid)
            if active:
                result["active_versions"][pid] = active
        return result

    # ------------------------------------------------------------------
    # Active versions
    # ------------------------------------------------------------------

    def get_active(self, project_id: str) -> Optional[str]:
        """Return the active name (e.g. 'v2.1.0', 'my-experiment') or None."""
        pointer = _pointer_file(project_id)
        if not pointer.exists():
            return None
        try:
            data = json.loads(pointer.read_text())
            return data.get("active")
        except Exception as e:
            _LOGGER.warning("Corrupt pointer file %s: %s", pointer, e)
            return None

    def get_active_source(self, project_id: str) -> Optional[str]:
        """Return 'registry' or 'local' for the active version, or None."""
        pointer = _pointer_file(project_id)
        if not pointer.exists():
            return None
        try:
            data = json.loads(pointer.read_text())
            return data.get("source")
        except Exception as e:
            _LOGGER.warning("Corrupt pointer file %s: %s", pointer, e)
            return None

    def get_active_checksum(self, project_id: str) -> Optional[str]:
        """Return the stored checksum for the active version, or None."""
        pointer = _pointer_file(project_id)
        if not pointer.exists():
            return None
        try:
            data = json.loads(pointer.read_text())
            return data.get("checksum")
        except Exception as e:
            _LOGGER.warning("Corrupt pointer file %s: %s", pointer, e)
            return None

    def set_active(
        self,
        project_id: str,
        name: str,
        source: str = "registry",
        checksum: Optional[str] = None,
    ) -> None:
        """Write the pointer file for *project_id*."""
        pointer = _pointer_file(project_id)
        data: dict = {"active": name, "source": source}
        if checksum:
            data["checksum"] = checksum
        _atomic_write(pointer, json.dumps(data, indent=2))

    def remove_active(self, project_id: str) -> None:
        """Delete the pointer file for *project_id* (no active version)."""
        _pointer_file(project_id).unlink(missing_ok=True)

    # ------------------------------------------------------------------
    # Installed versions (filesystem-driven)
    # ------------------------------------------------------------------

    def get_installed(self, project_id: str) -> list[str]:
        """Return installed names by scanning the project subdir for *.db files."""
        proj_dir = _dbs_dir() / project_id
        if not proj_dir.exists():
            return []
        return [p.stem for p in sorted(proj_dir.glob("*.db"))]

    def add_installed(self, project_id: str, name: str) -> None:
        """
        No-op: file presence IS the installation.

        The project subdir is created as a side effect so that subsequent
        filesystem scans return the correct directory.
        """
        _project_dir(project_id)  # ensure directory exists

    def remove_installed(self, project_id: str, name: str) -> None:
        """Delete the DB file from disk.  Also clears the pointer if it was active."""
        db = self.db_path(project_id, name)
        if db.exists():
            db.unlink()
        # Clear pointer if this was the active version
        if self.get_active(project_id) == name:
            self.remove_active(project_id)

    def all_project_ids(self) -> list[str]:
        """Return project IDs that have at least one installed DB (filesystem scan)."""
        dbs = _dbs_dir()
        if not dbs.exists():
            return []
        return [p.name for p in sorted(dbs.iterdir()) if p.is_dir() and any(p.glob("*.db"))]

    # ------------------------------------------------------------------
    # DB paths
    # ------------------------------------------------------------------

    @staticmethod
    def db_path(project_id: str, name: str) -> Path:
        """Return the expected filesystem path for a project+name combination."""
        return _dbs_dir() / project_id / f"{name}.db"

    @staticmethod
    def dbs_dir() -> Path:
        return _dbs_dir()

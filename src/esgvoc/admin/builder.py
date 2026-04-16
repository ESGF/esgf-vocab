"""
DBBuilder: build pre-built versioned SQLite databases from CV repositories.

Two modes:
  Local  — project repo already checked out, only universe is cloned
  Remote — both repos are cloned at the given ref

The build pipeline:
  1. Resolve/clone repos
  2. Build universe DB (create schema + ingest)
  3. Build project DB (create schema + ingest, universe path injected)
  4. Embed build metadata in _esgvoc_metadata table
  5. Compute SHA-256 checksum of the final file
  6. Return BuildResult

Service-state injection:
  The existing ingestion code reads `service.current_state.universe.local_path`
  to resolve JSON-LD @id references. The `_admin_context` context manager
  temporarily overrides the global service state so ingestion can run outside
  of a full esgvoc installation.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Optional

import esgvoc
from esgvoc.admin.manifest import Manifest
from esgvoc.core.service.missing_links import MissingLinksTracker


@dataclass
class BuildResult:
    """Result of a successful admin build."""

    output_path: Path
    project_id: str
    cv_version: str
    universe_version: str
    commit_sha: Optional[str]
    universe_commit_sha: Optional[str]
    build_date: datetime
    esgvoc_version: str
    checksum_sha256: str
    size_bytes: int

    def summary(self) -> str:
        mb = self.size_bytes / 1_048_576
        lines = [
            f"Build successful: {self.output_path.name} ({mb:.1f} MB)",
            f"  Project:           {self.project_id} @ {self.cv_version}",
            f"  Universe:          {self.universe_version}",
            f"  Commit:            {self.commit_sha or 'unknown'}",
            f"  Universe commit:   {self.universe_commit_sha or 'unknown'}",
            f"  Built with:        esgvoc {self.esgvoc_version}",
            f"  SHA-256:           {self.checksum_sha256}",
        ]
        return "\n".join(lines)


class DBBuilder:
    """
    Builds pre-built versioned SQLite databases from CV repositories.

    Parameters
    ----------
    work_dir:
        Directory for temporary clones. If None, uses a fresh tempdir per build.
    fail_on_missing_links:
        If True, raise an error when @id references cannot be resolved.
    verbose:
        If True, print progress to stdout.
    """

    def __init__(
        self,
        work_dir: Optional[Path] = None,
        fail_on_missing_links: bool = False,
        verbose: bool = True,
    ):
        self.work_dir = work_dir
        self.fail_on_missing_links = fail_on_missing_links
        self.verbose = verbose

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_dev(
        self,
        project_path: Path,
        universe_path: Path,
        output_path: Path,
        manifest_overrides: Optional[dict] = None,
        validate: bool = False,
    ) -> BuildResult:
        """
        Fully local build: both repos already on disk, no git clone needed.

        This is the recommended mode during development when:
        - Repos are not yet tagged (only branches exist)
        - No esgvoc_manifest.yaml exists yet in the repo
        - You want to test local CV changes before committing

        Parameters
        ----------
        project_path:
            Root of the locally checked-out project CV repo.
        universe_path:
            Root of the locally checked-out universe repo.
        output_path:
            Where to write the final .db file.
        manifest_overrides:
            Dict of manifest field overrides (project_id, cv_version,
            universe_version, esgvoc_min_version, esgvoc_max_version).
            These take precedence over esgvoc_manifest.yaml if present.
        validate:
            If True, run DBValidator.validate() on the result.
        """
        project_path = project_path.resolve()
        universe_path = universe_path.resolve()

        if not project_path.exists():
            raise FileNotFoundError(f"Project path not found: {project_path}")
        if not universe_path.exists():
            raise FileNotFoundError(f"Universe path not found: {universe_path}")

        self._log(f"Project path:  {project_path}")
        self._log(f"Universe path: {universe_path}")

        with self._temp_workspace() as tmp:
            result = self._run_build(
                project_path=project_path,
                universe_path=universe_path,
                project_sha=self._git_sha(project_path),
                universe_sha=self._git_sha(universe_path),
                output_path=output_path,
                tmp=tmp,
                manifest_overrides=manifest_overrides,
            )

        if validate:
            from esgvoc.admin.validator import DBValidator
            DBValidator().validate(output_path, full=True)

        return result

    def build_local(
        self,
        project_path: Path,
        universe_repo: str,
        universe_ref: str,
        output_path: Path,
        manifest_overrides: Optional[dict] = None,
        validate: bool = False,
    ) -> BuildResult:
        """
        Build from a locally checked-out project + a cloned universe.

        Parameters
        ----------
        project_path:
            Root of the project CV repo (already checked out).
        universe_repo:
            owner/repo or full URL of the universe GitHub repository.
        universe_ref:
            Branch or tag to clone universe at.
        output_path:
            Where to write the final .db file.
        manifest_overrides:
            Dict of manifest field overrides (project_id, cv_version, …).
        validate:
            If True, run DBValidator.validate() on the result.
        """
        project_path = project_path.resolve()
        if not project_path.exists():
            raise FileNotFoundError(f"Project path not found: {project_path}")
        with self._temp_workspace() as tmp:
            universe_path = tmp / "universe"
            self._log(f"Cloning universe {universe_repo} @ {universe_ref}…")
            self._clone(universe_repo, universe_ref, universe_path)
            universe_sha = self._git_sha(universe_path)
            project_sha = self._git_sha(project_path)

            result = self._run_build(
                project_path=project_path,
                universe_path=universe_path,
                project_sha=project_sha,
                universe_sha=universe_sha,
                output_path=output_path,
                tmp=tmp,
                manifest_overrides=manifest_overrides,
            )

        if validate:
            from esgvoc.admin.validator import DBValidator
            DBValidator().validate(output_path, full=True)

        return result

    def build_remote(
        self,
        project_repo: str,
        project_ref: str,
        universe_repo: str,
        universe_ref: str,
        output_path: Path,
        manifest_overrides: Optional[dict] = None,
        validate: bool = False,
    ) -> BuildResult:
        """
        Build by cloning both project and universe repos.

        Parameters
        ----------
        project_repo:
            owner/repo or full URL of the project CV repository.
        project_ref:
            Branch, tag, or commit ref to clone project at.
        manifest_overrides:
            Dict of manifest field overrides (project_id, cv_version, …).
        """
        with self._temp_workspace() as tmp:
            project_path = tmp / "project"
            universe_path = tmp / "universe"

            self._log(f"Cloning project {project_repo} @ {project_ref}…")
            self._clone(project_repo, project_ref, project_path)
            self._log(f"Cloning universe {universe_repo} @ {universe_ref}…")
            self._clone(universe_repo, universe_ref, universe_path)

            project_sha = self._git_sha(project_path)
            universe_sha = self._git_sha(universe_path)

            result = self._run_build(
                project_path=project_path,
                universe_path=universe_path,
                project_sha=project_sha,
                universe_sha=universe_sha,
                output_path=output_path,
                tmp=tmp,
                manifest_overrides=manifest_overrides,
            )

        if validate:
            from esgvoc.admin.validator import DBValidator
            DBValidator().validate(output_path, full=True)

        return result

    def build_universe(
        self,
        universe_repo: str,
        universe_ref: str,
        output_path: Path,
    ) -> BuildResult:
        """Build a standalone universe-only database."""
        with self._temp_workspace() as tmp:
            universe_path = tmp / "universe"
            self._log(f"Cloning universe {universe_repo} @ {universe_ref}…")
            self._clone(universe_repo, universe_ref, universe_path)
            universe_sha = self._git_sha(universe_path)

            universe_db = tmp / "universe.db"
            self._log("Building universe DB…")
            self._build_universe_db(universe_path, universe_db, universe_sha)

            output_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(universe_db), str(output_path))

            metadata = {
                "project_id": "universe",
                "cv_version": "n/a",
                "universe_version": "standalone",
                "commit_sha": universe_sha or "unknown",
                "universe_commit_sha": universe_sha or "unknown",
                "build_date": datetime.now(timezone.utc).isoformat(),
                "esgvoc_version": getattr(esgvoc, "__version__", "unknown"),
                "esgvoc_min_version": "",
                "esgvoc_max_version": "",
            }
            self._embed_metadata(output_path, metadata)
            checksum = _sha256(output_path)
            self._log(f"SHA-256: {checksum}")

            return BuildResult(
                output_path=output_path,
                project_id="universe",
                cv_version="n/a",
                universe_version="standalone",
                commit_sha=universe_sha,
                universe_commit_sha=universe_sha,
                build_date=datetime.now(timezone.utc),
                esgvoc_version=getattr(esgvoc, "__version__", "unknown"),
                checksum_sha256=checksum,
                size_bytes=output_path.stat().st_size,
            )

    # ------------------------------------------------------------------
    # Core build pipeline
    # ------------------------------------------------------------------

    def _run_build(
        self,
        project_path: Path,
        universe_path: Path,
        project_sha: Optional[str],
        universe_sha: Optional[str],
        output_path: Path,
        tmp: Path,
        manifest_overrides: Optional[dict] = None,
    ) -> BuildResult:
        """Build universe DB + project DB, merge, embed metadata, compute checksum."""
        manifest = Manifest.load_or_default(
            project_path,
            project_id=project_path.name,
        )
        # Apply overrides on top of whatever was loaded (or defaulted)
        if manifest_overrides:
            if "project_id" in manifest_overrides:
                manifest.project.id = manifest_overrides["project_id"]
            if "cv_version" in manifest_overrides:
                manifest.cv_version = manifest_overrides["cv_version"]
            if "universe_version" in manifest_overrides:
                manifest.universe_version = manifest_overrides["universe_version"]
            if "esgvoc_min_version" in manifest_overrides:
                manifest.esgvoc.min_version = manifest_overrides["esgvoc_min_version"]
            if "esgvoc_max_version" in manifest_overrides:
                manifest.esgvoc.max_version = manifest_overrides["esgvoc_max_version"]
        self._log(f"Project: {manifest.project.id} cv_version={manifest.cv_version}")

        universe_db = tmp / "universe.db"
        project_db = tmp / "project.db"

        # 1. Build universe
        self._log("Building universe DB…")
        self._build_universe_db(universe_path, universe_db, universe_sha)

        # 2. Build project (with universe path injected into service context)
        self._log(f"Building project DB ({manifest.project.id})…")
        self._build_project_db(
            project_path=project_path,
            universe_path=universe_path,
            universe_db=universe_db,
            project_db=project_db,
            project_sha=project_sha,
        )

        # 3. Copy project DB to output
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(project_db), str(output_path))

        # 4. Embed metadata
        build_date = datetime.now(timezone.utc)
        esgvoc_version = getattr(esgvoc, "__version__", "unknown")
        metadata = {
            "project_id": manifest.project.id,
            "cv_version": manifest.cv_version,
            "universe_version": manifest.universe_version,
            "commit_sha": project_sha or "unknown",
            "universe_commit_sha": universe_sha or "unknown",
            "build_date": build_date.isoformat(),
            "esgvoc_version": esgvoc_version,
            "esgvoc_min_version": manifest.esgvoc.min_version or "",
            "esgvoc_max_version": manifest.esgvoc.max_version or "",
        }
        self._embed_metadata(output_path, metadata)

        # 5. Compute checksum of the final file
        checksum = _sha256(output_path)
        self._log(f"SHA-256: {checksum}")

        return BuildResult(
            output_path=output_path,
            project_id=manifest.project.id,
            cv_version=manifest.cv_version,
            universe_version=manifest.universe_version,
            commit_sha=project_sha,
            universe_commit_sha=universe_sha,
            build_date=build_date,
            esgvoc_version=esgvoc_version,
            checksum_sha256=checksum,
            size_bytes=output_path.stat().st_size,
        )

    def _build_universe_db(
        self, universe_path: Path, universe_db: Path, universe_sha: Optional[str]
    ) -> None:
        from esgvoc.core.db.models.universe import universe_create_db
        from esgvoc.core.db.connection import DBConnection
        from esgvoc.core.db.universe_ingestion import ingest_metadata_universe, ingest_universe

        if universe_db.exists():
            universe_db.unlink()
        universe_db.parent.mkdir(parents=True, exist_ok=True)

        universe_create_db(universe_db)
        conn = DBConnection(db_file_path=universe_db)
        ingest_metadata_universe(conn, universe_sha or "unknown")

        tracker = MissingLinksTracker() if self.fail_on_missing_links else None
        with _admin_context(universe_local_path=str(universe_path)):
            ingest_universe(universe_path, universe_db, tracker)

        if tracker and tracker.has_missing_links():
            tracker.print_summary()
            tracker.check_and_raise()

    def _build_project_db(
        self,
        project_path: Path,
        universe_path: Path,
        universe_db: Path,
        project_db: Path,
        project_sha: Optional[str],
    ) -> None:
        from esgvoc.core.db.models.project import project_create_db
        from esgvoc.core.db.project_ingestion import ingest_project

        if project_db.exists():
            project_db.unlink()
        project_db.parent.mkdir(parents=True, exist_ok=True)

        project_create_db(project_db)
        # NOTE: do NOT call ingest_metadata_project here.  That function creates
        # a placeholder Project row (id = file stem, no collections) at pk=1.
        # ingest_project already creates the real Project row (id = actual project
        # ID from esgvoc_project.yaml, with all collections) at pk=1 when there
        # is no prior row — which is what the API expects (SQLITE_FIRST_PK = 1).

        tracker = MissingLinksTracker() if self.fail_on_missing_links else None
        with _admin_context(
            universe_local_path=str(universe_path),
            universe_db_path=str(universe_db),
        ):
            ingest_project(project_path, project_db, project_sha or "unknown", tracker)

        if tracker and tracker.has_missing_links():
            tracker.print_summary()
            tracker.check_and_raise()

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    @staticmethod
    def _embed_metadata(db_path: Path, metadata: dict) -> None:
        """Write key-value build metadata into _esgvoc_metadata table."""
        import sqlite3

        with sqlite3.connect(str(db_path)) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS _esgvoc_metadata "
                "(key TEXT PRIMARY KEY NOT NULL, value TEXT)"
            )
            conn.executemany(
                "INSERT OR REPLACE INTO _esgvoc_metadata (key, value) VALUES (?, ?)",
                list(metadata.items()),
            )
            conn.commit()

    # ------------------------------------------------------------------
    # Git helpers
    # ------------------------------------------------------------------

    def _clone(self, repo: str, ref: str, dest: Path) -> None:
        """Clone *repo* at *ref* (branch, tag) to *dest*."""
        url = _resolve_repo_url(repo)
        dest.parent.mkdir(parents=True, exist_ok=True)
        cmd = ["git", "clone", "--depth", "1", "--branch", ref, url, str(dest)]
        try:
            subprocess.run(
                cmd,
                check=True,
                capture_output=not self.verbose,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Failed to clone {url} @ {ref}: {e.stderr.decode() if e.stderr else e}"
            ) from e

    @staticmethod
    def _git_sha(repo_path: Path) -> Optional[str]:
        """Return the current HEAD commit SHA of a local repo, or None."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Workspace
    # ------------------------------------------------------------------

    @contextmanager
    def _temp_workspace(self):
        """Provide a temporary working directory, cleaned up on exit."""
        if self.work_dir:
            self.work_dir.mkdir(parents=True, exist_ok=True)
            yield self.work_dir
        else:
            with tempfile.TemporaryDirectory(prefix="esgvoc_admin_") as tmp:
                yield Path(tmp)

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(msg)


# ------------------------------------------------------------------
# Service-state injection context manager
# ------------------------------------------------------------------

@contextmanager
def _admin_context(
    universe_local_path: str,
    universe_db_path: Optional[str] = None,
):
    """
    Temporarily override service.current_state so ingestion functions
    can access universe.local_path without a full esgvoc installation.

    This is necessary because universe_ingestion.py and project_ingestion.py
    read `service.current_state.universe.local_path` to resolve JSON-LD @id
    references during ingestion.
    """
    import esgvoc.core.service as svc

    original = svc.current_state

    fake_universe = SimpleNamespace(local_path=universe_local_path)
    fake_state = SimpleNamespace(universe=fake_universe)

    svc.current_state = fake_state
    try:
        yield
    finally:
        svc.current_state = original


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _resolve_repo_url(repo: str) -> str:
    """Accept 'owner/repo' shorthand or full URL."""
    if repo.startswith("http://") or repo.startswith("https://"):
        return repo
    if "/" in repo and not repo.startswith("/"):
        return f"https://github.com/{repo}.git"
    raise ValueError(f"Cannot resolve repo URL from: {repo!r}")

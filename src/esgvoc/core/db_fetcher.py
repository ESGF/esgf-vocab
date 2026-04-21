"""
DBFetcher: downloads pre-built versioned database artifacts.

Version discovery uses a single raw HTTP GET per project:
  GET {REGISTRY_BASE_URL}/{project_id}.json

The index file lives on the main branch of the `esgvoc_dbs` repository and
is served via raw GitHub content — no API quota consumed, no authentication,
no pagination required.

Per-project index file format:
  {
    "project_id": "cmip7",
    "releases": [
      {
        "version": "v1.2.7",
        "tag": "cmip7.v1.2.7",
        "checksum_sha256": "abc123...",
        "url": "https://github.com/.../releases/download/.../cmip7.v1.2.7.db",
        "size_bytes": 80000000,
        "is_prerelease": false,
        "published_at": "2026-04-17T10:00:00Z"
      }
    ]
  }

Environment variables honoured:
    ESGVOC_REGISTRY_BASE_URL  Override the registry base URL (for testing / forks)
    GITHUB_TOKEN              Optional — no longer needed for version discovery,
                              but still used to authenticate downloads if needed
    ESGVOC_OFFLINE            If 'true', all network operations raise OfflineError
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import requests

from esgvoc.core.db_artifact import DBArtifact
from esgvoc.core.github_registry import ProjectInfo, get_project, known_project_ids

logger = logging.getLogger(__name__)

# How long to cache the project index before re-fetching
_CACHE_TTL_HOURS = 1
_DB_ASSET_SUFFIX = ".db"
_FETCH_TIMEOUT = 10   # seconds — small JSON file
_DOWNLOAD_TIMEOUT = 300   # seconds (5 min for large files)
_MAX_RETRIES = 3


class EsgvocNetworkError(RuntimeError):
    """Raised when a network operation fails."""
    exit_code = 2


class EsgvocOfflineError(EsgvocNetworkError):
    """Raised when a network operation is attempted in offline mode."""


class EsgvocVersionNotFoundError(LookupError):
    """Raised when the requested version does not exist."""
    exit_code = 3


class EsgvocChecksumError(RuntimeError):
    """Raised when a downloaded file fails checksum verification."""
    exit_code = 5


class DBFetcher:
    """
    Fetches pre-built database artifacts from the esgvoc_dbs registry.

    Parameters
    ----------
    cache_dir:
        Directory for caching the per-project JSON index files.
    offline:
        If True, all network operations raise EsgvocOfflineError.
    """

    def __init__(self, cache_dir: Path, offline: bool = False):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.offline = offline or os.environ.get("ESGVOC_OFFLINE", "").lower() == "true"
        self._session = self._build_session()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_versions(self, project_id: str, include_prerelease: bool = False) -> list[str]:
        """
        Return available version tags for a project, newest first.

        Parameters
        ----------
        project_id:
            e.g. 'cmip7'
        include_prerelease:
            If True, include dev-latest and other pre-release tags.
        """
        artifacts = self._fetch_releases(project_id)
        if not include_prerelease:
            artifacts = [a for a in artifacts if not a.is_prerelease]
        return [a.version for a in artifacts]

    def get_artifact(self, project_id: str, version: str = "latest") -> DBArtifact:
        """
        Return the artifact metadata for a specific version.

        Parameters
        ----------
        project_id:
            e.g. 'cmip7'
        version:
            Semver tag ('v2.1.0'), 'latest', or 'dev-latest'.
        """
        artifacts = self._fetch_releases(project_id)

        if version == "latest":
            stable = [a for a in artifacts if not a.is_prerelease]
            if not stable:
                raise EsgvocVersionNotFoundError(
                    f"No stable releases found for '{project_id}'."
                )
            return stable[0]

        for artifact in artifacts:
            if artifact.version == version:
                return artifact

        available = [a.version for a in artifacts]
        raise EsgvocVersionNotFoundError(
            f"Version '{version}' not found for project '{project_id}'.\n"
            f"Available: {', '.join(available) or 'none'}"
        )

    def download_db(
        self,
        artifact: DBArtifact,
        target: Path,
        show_progress: bool = True,
    ) -> Path:
        """
        Download a DB artifact to *target* atomically.

        If *target* already exists and the checksum matches, the download is
        skipped and the existing file is returned.

        Returns the final path (always *target*).
        """
        self._check_online("download database")

        # Check if already present and valid
        if target.exists() and artifact.checksum_sha256:
            if _sha256(target) == artifact.checksum_sha256:
                logger.debug(f"Already up-to-date: {target}")
                return target

        target.parent.mkdir(parents=True, exist_ok=True)

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                self._download_atomic(artifact, target, show_progress)
                break
            except EsgvocChecksumError:
                if attempt == _MAX_RETRIES:
                    raise
                logger.warning(f"Checksum mismatch, retrying ({attempt}/{_MAX_RETRIES})…")

        return target

    def check_compatibility(self, artifact: DBArtifact) -> tuple[bool, str]:
        """
        Check whether *artifact* is compatible with the installed esgvoc version.

        Returns (compatible, message). If compatible is False, message explains why.
        """
        import esgvoc
        installed_str = getattr(esgvoc, "__version__", None)
        installed = _parse_version(installed_str)
        if installed is None:
            return True, ""  # Cannot determine — allow

        if artifact.esgvoc_min_version:
            min_v = _parse_version(artifact.esgvoc_min_version)
            if min_v is not None and installed < min_v:
                return False, (
                    f"{artifact.project_id}@{artifact.version} requires esgvoc >= {artifact.esgvoc_min_version}.\n"
                    f"You have esgvoc {installed_str}.\n"
                    f"Run: pip install --upgrade esgvoc"
                )

        if artifact.esgvoc_max_version:
            max_v = _parse_version(artifact.esgvoc_max_version)
            if max_v is not None and installed >= max_v:
                return False, (
                    f"Warning: {artifact.project_id}@{artifact.version} was built for esgvoc < {artifact.esgvoc_max_version}.\n"
                    f"You have esgvoc {installed_str}. Some features may not work correctly."
                )

        return True, ""

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _check_online(self, action: str) -> None:
        if self.offline:
            raise EsgvocOfflineError(
                f"Cannot {action}: offline mode is active (ESGVOC_OFFLINE=true)."
            )

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        token = os.environ.get("GITHUB_TOKEN")
        if token:
            session.headers["Authorization"] = f"Bearer {token}"
        session.headers["Accept"] = "application/json"
        return session

    def _cache_path(self, project_id: str) -> Path:
        return self.cache_dir / f"registry_{project_id}.json"

    def _fetch_releases(self, project_id: str) -> list[DBArtifact]:
        """Fetch (with cache) the release index for a project."""
        info = get_project(project_id)
        if info is None:
            raise EsgvocVersionNotFoundError(
                f"Unknown project '{project_id}'.\n"
                f"Available: {', '.join(known_project_ids())}"
            )

        cache_file = self._cache_path(project_id)
        cached = self._load_cache(cache_file)
        if cached is not None:
            return cached

        self._check_online(f"fetch index for '{project_id}'")
        artifacts = self._fetch_raw_index(info)
        self._save_cache(cache_file, artifacts)
        return artifacts

    def _load_cache(self, cache_file: Path) -> Optional[list[DBArtifact]]:
        """Return cached artifacts if fresh, else None."""
        if not cache_file.exists():
            return None
        try:
            data = json.loads(cache_file.read_text())
            fetched_at = datetime.fromisoformat(data["fetched_at"])
            if datetime.now(timezone.utc) - fetched_at > timedelta(hours=_CACHE_TTL_HOURS):
                return None
            return [DBArtifact(**a) for a in data["artifacts"]]
        except Exception as e:
            logger.debug(f"Cache miss ({cache_file}): {e}")
            return None

    def _save_cache(self, cache_file: Path, artifacts: list[DBArtifact]) -> None:
        data = {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "artifacts": [a.model_dump(mode="json") for a in artifacts],
        }
        cache_file.write_text(json.dumps(data, indent=2))

    def _fetch_raw_index(self, info: ProjectInfo) -> list[DBArtifact]:
        """Fetch the per-project JSON index from the registry raw content URL."""
        url = info.raw_index_url
        logger.debug(f"Fetching registry index: {url}")
        try:
            resp = self._session.get(url, timeout=_FETCH_TIMEOUT)
            if resp.status_code == 404:
                raise EsgvocVersionNotFoundError(
                    f"No registry index found for '{info.project_id}' at {url}.\n"
                    f"The project may not have any published releases yet."
                )
            resp.raise_for_status()
        except requests.exceptions.ConnectionError as e:
            raise EsgvocNetworkError(f"Cannot reach registry at {url}: {e}") from e
        except requests.exceptions.HTTPError as e:
            raise EsgvocNetworkError(f"Registry fetch error: {e}") from e

        try:
            index = resp.json()
        except Exception as e:
            raise EsgvocNetworkError(f"Invalid JSON in registry index for '{info.project_id}': {e}") from e

        artifacts: list[DBArtifact] = []
        for release in index.get("releases", []):
            version = release.get("version", "")
            if not version:
                continue
            try:
                published_at = None
                if release.get("published_at"):
                    published_at = datetime.fromisoformat(
                        release["published_at"].replace("Z", "+00:00")
                    )
                artifacts.append(DBArtifact(
                    project_id=info.project_id,
                    version=version,
                    download_url=release["url"],
                    size_bytes=release.get("size_bytes"),
                    checksum_sha256=release.get("checksum_sha256"),
                    published_at=published_at,
                    is_prerelease=release.get("is_prerelease", False),
                    universe_version=release.get("universe_version"),
                    esgvoc_min_version=release.get("esgvoc_min_version"),
                    esgvoc_max_version=release.get("esgvoc_max_version"),
                ))
            except Exception as e:
                logger.warning(f"Skipping malformed release entry for '{info.project_id}': {e}")

        # Sort: stable releases newest first, then pre-releases
        def sort_key(a: DBArtifact):
            v = _parse_version(a.version) or (0, 0, 0, 0)
            return (0 if not a.is_prerelease else 1, v)

        artifacts.sort(key=sort_key, reverse=True)
        return artifacts

    def _download_atomic(
        self,
        artifact: DBArtifact,
        target: Path,
        show_progress: bool,
    ) -> None:
        """Download to a temp file, verify checksum, then rename to target."""
        with tempfile.NamedTemporaryFile(
            dir=target.parent, suffix=".tmp", delete=False
        ) as tmp:
            tmp_path = Path(tmp.name)

        try:
            self._stream_download(artifact, tmp_path, show_progress)
            if artifact.checksum_sha256:
                actual = _sha256(tmp_path)
                if actual != artifact.checksum_sha256:
                    raise EsgvocChecksumError(
                        f"Checksum mismatch for {artifact.db_filename()}!\n"
                        f"  Expected: {artifact.checksum_sha256}\n"
                        f"  Got:      {actual}"
                    )
            shutil.move(str(tmp_path), str(target))
        except Exception:
            tmp_path.unlink(missing_ok=True)
            raise

    def _stream_download(
        self,
        artifact: DBArtifact,
        dest: Path,
        show_progress: bool,
    ) -> None:
        try:
            resp = self._session.get(
                artifact.download_url, stream=True, timeout=_DOWNLOAD_TIMEOUT
            )
            resp.raise_for_status()
        except requests.exceptions.ConnectionError as e:
            raise EsgvocNetworkError(f"Download failed: {e}") from e

        total = int(resp.headers.get("content-length", 0))
        downloaded = 0
        chunk_size = 1024 * 64  # 64 KB

        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if show_progress and total:
                        _print_progress(downloaded, total, artifact.db_filename())

        if show_progress and total:
            print()  # newline after progress bar


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


_SEMVER_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(.*)$")


def _parse_version(version_str: Optional[str]) -> Optional[tuple]:
    """Parse 'vX.Y.Z[suffix]' into a comparable tuple, or None on failure."""
    if not version_str:
        return None
    m = _SEMVER_RE.match(version_str.strip())
    if not m:
        return None
    major, minor, patch, suffix = int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4)
    # Pre-release suffixes sort before the release: treat "" as highest
    pre = 0 if not suffix else -1
    return (major, minor, patch, pre)


def _is_prerelease(version: str) -> bool:
    if version == "dev-latest":
        return True
    m = _SEMVER_RE.match(version.strip())
    if not m:
        return False
    return bool(m.group(4))  # any suffix (alpha, beta, rc) = prerelease


def _print_progress(downloaded: int, total: int, name: str) -> None:
    pct = downloaded / total
    bar_len = 30
    filled = int(bar_len * pct)
    bar = "█" * filled + "░" * (bar_len - filled)
    mb_done = downloaded / 1_048_576
    mb_total = total / 1_048_576
    print(
        f"\r  [{bar}] {pct:5.1%}  {mb_done:.1f}/{mb_total:.1f} MB  {name}",
        end="",
        flush=True,
    )

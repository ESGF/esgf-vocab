"""
DBPublisher: publishes a pre-built database to a GitHub Release.

Workflow
--------
1. Read build metadata from the DB's _esgvoc_metadata table.
2. Compute SHA-256 checksum.
3. Resolve the target GitHub Release (create or update).
4. Upload the .db file as a release asset.

Environment variables honoured:
    GITHUB_TOKEN   - required for authentication (write:packages scope)
"""

from __future__ import annotations

import hashlib
import logging
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests

_LOGGER = logging.getLogger(__name__)


class PublishError(RuntimeError):
    """Raised when publishing fails."""
    exit_code = 4


class PublishAuthError(PublishError):
    """Raised when GITHUB_TOKEN is missing or lacks permission."""
    exit_code = 4


class PublishConflictError(PublishError):
    """Raised when a release already exists and --update-if-exists is False."""
    exit_code = 4


_API_TIMEOUT = 30
_UPLOAD_TIMEOUT = 600  # 10 min for large DB files


@dataclass
class PublishResult:
    """Result of a successful publish operation."""
    project_id: str
    tag: str
    release_url: str
    asset_name: str
    checksum_sha256: str
    dry_run: bool

    def summary(self) -> str:
        if self.dry_run:
            return (
                f"[DRY RUN] Would publish {self.project_id}@{self.tag}\n"
                f"  Asset:    {self.asset_name}\n"
                f"  Checksum: {self.checksum_sha256}"
            )
        return (
            f"Published {self.project_id}@{self.tag}\n"
            f"  Release:  {self.release_url}\n"
            f"  Asset:    {self.asset_name}\n"
            f"  Checksum: {self.checksum_sha256}"
        )


class DBPublisher:
    """
    Publishes a pre-built database snapshot to a GitHub Release.

    Parameters
    ----------
    github_token:
        Personal access token with ``repo`` or ``write:packages`` scope.
        Falls back to GITHUB_TOKEN environment variable if not provided.
    github_base_url:
        Override for GitHub Enterprise (default: https://github.com).
    """

    def __init__(
        self,
        github_token: Optional[str] = None,
        github_base_url: str = "https://github.com",
    ):
        token = github_token or os.environ.get("GITHUB_TOKEN", "")
        if not token:
            raise PublishAuthError(
                "GITHUB_TOKEN is required to publish releases.\n"
                "Set it as an environment variable or pass --github-token."
            )
        self._token = token
        self._api_base = self._resolve_api_base(github_base_url)
        self._upload_base = self._resolve_upload_base(github_base_url)
        self._session = self._build_session(token)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def publish(
        self,
        db_path: Path,
        repo: str,
        tag: str,
        *,
        prerelease: bool = False,
        draft: bool = False,
        release_notes: str = "",
        update_if_exists: bool = True,
        dry_run: bool = False,
    ) -> PublishResult:
        """
        Publish *db_path* to a GitHub Release tagged *tag* in *repo*.

        Parameters
        ----------
        db_path:
            Local path to the built .db file.
        repo:
            GitHub repository in ``owner/repo`` format.
        tag:
            Release tag (e.g. 'v2.1.0' or 'dev-latest').
        prerelease:
            Mark the release as a pre-release.
        draft:
            Create as a draft (not publicly visible until published).
        release_notes:
            Optional extra text appended to the auto-generated release body.
        update_if_exists:
            If True and a release with *tag* already exists, replace its .db
            asset.  If False, raise PublishConflictError.
        dry_run:
            Build the release payload and print it without making any API calls.
        """
        if not db_path.exists():
            raise PublishError(f"DB file not found: {db_path}")

        # Read metadata embedded in the DB
        meta = _read_db_metadata(db_path)
        project_id = meta.get("project_id", db_path.stem)

        # Compute checksum
        checksum = _sha256(db_path)
        asset_name = f"{project_id}.db"

        # Build release body
        body = _build_release_body(meta, checksum, tag, release_notes)

        if dry_run:
            return PublishResult(
                project_id=project_id,
                tag=tag,
                release_url=f"https://github.com/{repo}/releases/tag/{tag}",
                asset_name=asset_name,
                checksum_sha256=checksum,
                dry_run=True,
            )

        # Resolve or create the GitHub Release
        release = self._get_or_create_release(
            repo=repo,
            tag=tag,
            name=f"{project_id} {tag}",
            body=body,
            prerelease=prerelease,
            draft=draft,
            update_if_exists=update_if_exists,
        )

        release_url = release.get("html_url", "")
        upload_url = release.get("upload_url", "").split("{")[0]  # strip template part

        # Remove any existing .db asset from this release (idempotent re-publish)
        for asset in release.get("assets", []):
            if asset["name"].endswith(".db"):
                self._delete_asset(repo, asset["id"])

        # Upload the DB file
        self._upload_asset(upload_url, db_path, asset_name)

        return PublishResult(
            project_id=project_id,
            tag=tag,
            release_url=release_url,
            asset_name=asset_name,
            checksum_sha256=checksum,
            dry_run=False,
        )

    # ------------------------------------------------------------------
    # GitHub API helpers
    # ------------------------------------------------------------------

    def _get_or_create_release(
        self,
        repo: str,
        tag: str,
        name: str,
        body: str,
        prerelease: bool,
        draft: bool,
        update_if_exists: bool,
    ) -> dict:
        """Return the release dict, creating it if it does not exist yet."""
        existing = self._get_release_by_tag(repo, tag)

        if existing is not None:
            if not update_if_exists:
                raise PublishConflictError(
                    f"Release '{tag}' already exists in {repo}. "
                    "Use --update-if-exists to replace the asset."
                )
            # Update release metadata (body, prerelease flag)
            updated = self._update_release(
                repo, existing["id"],
                body=body,
                prerelease=prerelease,
                draft=draft,
            )
            # Carry over assets list from the existing release so we can delete old DBs
            updated["assets"] = existing.get("assets", [])
            return updated

        return self._create_release(
            repo=repo,
            tag=tag,
            name=name,
            body=body,
            prerelease=prerelease,
            draft=draft,
        )

    def _get_release_by_tag(self, repo: str, tag: str) -> Optional[dict]:
        url = f"{self._api_base}/repos/{repo}/releases/tags/{tag}"
        resp = self._session.get(url, timeout=_API_TIMEOUT)
        if resp.status_code == 404:
            return None
        self._raise_for_status(resp, f"fetch release '{tag}'")
        return resp.json()

    def _create_release(
        self,
        repo: str,
        tag: str,
        name: str,
        body: str,
        prerelease: bool,
        draft: bool,
    ) -> dict:
        url = f"{self._api_base}/repos/{repo}/releases"
        payload = {
            "tag_name": tag,
            "name": name,
            "body": body,
            "prerelease": prerelease,
            "draft": draft,
        }
        resp = self._session.post(url, json=payload, timeout=_API_TIMEOUT)
        self._raise_for_status(resp, f"create release '{tag}'")
        return resp.json()

    def _update_release(
        self,
        repo: str,
        release_id: int,
        body: str,
        prerelease: bool,
        draft: bool,
    ) -> dict:
        url = f"{self._api_base}/repos/{repo}/releases/{release_id}"
        payload = {"body": body, "prerelease": prerelease, "draft": draft}
        resp = self._session.patch(url, json=payload, timeout=_API_TIMEOUT)
        self._raise_for_status(resp, f"update release {release_id}")
        return resp.json()

    def _delete_asset(self, repo: str, asset_id: int) -> None:
        url = f"{self._api_base}/repos/{repo}/releases/assets/{asset_id}"
        resp = self._session.delete(url, timeout=_API_TIMEOUT)
        if resp.status_code not in (204, 404):
            self._raise_for_status(resp, f"delete asset {asset_id}")

    def _upload_asset(self, upload_url: str, db_path: Path, asset_name: str) -> dict:
        headers = {
            "Content-Type": "application/octet-stream",
            "Content-Length": str(db_path.stat().st_size),
        }
        with open(db_path, "rb") as fh:
            resp = self._session.post(
                upload_url,
                params={"name": asset_name},
                data=fh,
                headers=headers,
                timeout=_UPLOAD_TIMEOUT,
            )
        self._raise_for_status(resp, f"upload asset '{asset_name}'")
        return resp.json()

    def _raise_for_status(self, resp: requests.Response, action: str) -> None:
        if resp.ok:
            return
        if resp.status_code == 401:
            raise PublishAuthError(
                f"GitHub authentication failed while trying to {action}.\n"
                "Check that GITHUB_TOKEN is valid and has 'repo' scope."
            )
        if resp.status_code == 403:
            raise PublishAuthError(
                f"GitHub permission denied while trying to {action}.\n"
                "Ensure the token has write access to the repository."
            )
        try:
            detail = resp.json().get("message", resp.text)
        except Exception:
            detail = resp.text
        raise PublishError(
            f"GitHub API error ({resp.status_code}) while trying to {action}: {detail}"
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_api_base(github_base_url: str) -> str:
        if github_base_url.rstrip("/") == "https://github.com":
            return "https://api.github.com"
        domain = github_base_url.removeprefix("https://").rstrip("/")
        return f"https://{domain}/api/v3"

    @staticmethod
    def _resolve_upload_base(github_base_url: str) -> str:
        if github_base_url.rstrip("/") == "https://github.com":
            return "https://uploads.github.com"
        domain = github_base_url.removeprefix("https://").rstrip("/")
        return f"https://{domain}/api/v3"

    @staticmethod
    def _build_session(token: str) -> requests.Session:
        session = requests.Session()
        session.headers.update({
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })
        return session


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------

def _read_db_metadata(db_path: Path) -> dict[str, str]:
    """Read key-value rows from _esgvoc_metadata table."""
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        rows = conn.execute("SELECT key, value FROM _esgvoc_metadata").fetchall()
        conn.close()
        return dict(rows)
    except Exception as e:
        _LOGGER.debug("Could not read metadata from %s: %s", db_path, e)
        return {}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _build_release_body(
    meta: dict[str, str],
    checksum: str,
    tag: str,
    extra_notes: str = "",
) -> str:
    project_id = meta.get("project_id", "unknown")
    universe_version = meta.get("universe_version", "unknown")
    esgvoc_version = meta.get("esgvoc_version", "unknown")
    build_date = meta.get("build_date", "unknown")
    commit_sha = meta.get("commit_sha", "")

    lines = [
        f"## {project_id} {tag}",
        "",
        f"**Universe version**: {universe_version}",
        f"**Built with esgvoc**: {esgvoc_version}",
        f"**Build date**: {build_date}",
    ]
    if commit_sha:
        lines.append(f"**Commit**: `{commit_sha}`")

    lines += [
        f"**Checksum (SHA256)**: `{checksum}`",
        "",
        "### Installation",
        "```bash",
        f"esgvoc install {project_id}@{tag}",
        "```",
    ]

    if extra_notes:
        lines += ["", "### Release Notes", extra_notes]

    return "\n".join(lines)

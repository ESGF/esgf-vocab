"""
Version checking system for esgvoc.

This module provides functionality to check for newer versions of esgvoc
on PyPI and notify users when updates are available.
"""

import json
import logging
import sys
import threading
import warnings
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple

import requests

logger = logging.getLogger(__name__)


class EsgvocVersionWarning(UserWarning):
    """Warning issued when a newer version of esgvoc is available."""

    pass


class VersionChecker:
    """
    Handles version checking against PyPI and user notifications.

    Attributes:
        cache_dir: Directory for storing version check cache
        cache_file: Path to the JSON cache file
        pypi_url: URL for PyPI JSON API
        timeout: Network request timeout in seconds
    """

    PYPI_URL = "https://pypi.org/pypi/esgvoc/json"
    CACHE_FILENAME = "version_check_cache.json"
    DEFAULT_TIMEOUT = 3  # seconds

    def __init__(
        self,
        cache_dir: Path,
        check_interval_hours: int = 12,
        reminder_interval_hours: int = 72,
        enabled: bool = True,
    ):
        import os

        from esgvoc import __version__

        self.cache_dir = cache_dir
        self.cache_file = cache_dir / self.CACHE_FILENAME
        self.check_interval = timedelta(hours=check_interval_hours)
        self.reminder_interval = timedelta(hours=reminder_interval_hours)
        self.enabled = enabled
        # Allow overriding version for testing: ESGVOC_FAKE_VERSION=1.0.0
        self.current_version = os.environ.get("ESGVOC_FAKE_VERSION", __version__)
        self._check_thread: Optional[threading.Thread] = None
        self._check_complete = threading.Event()

    def _load_cache(self) -> dict:
        """Load cached version check data."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.debug(f"Failed to load version cache: {e}")
        return {}

    def _save_cache(self, data: dict) -> None:
        """Save version check data to cache."""
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, "w") as f:
                json.dump(data, f, indent=2)
        except IOError as e:
            logger.debug(f"Failed to save version cache: {e}")

    def _fetch_latest_version(self) -> Optional[str]:
        """
        Fetch the latest version from PyPI.

        Returns:
            Latest version string or None if fetch failed.
        """
        try:
            response = requests.get(self.PYPI_URL, timeout=self.DEFAULT_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            return data.get("info", {}).get("version")
        except requests.RequestException as e:
            logger.debug(f"Failed to fetch version from PyPI: {e}")
            return None
        except (json.JSONDecodeError, KeyError) as e:
            logger.debug(f"Failed to parse PyPI response: {e}")
            return None

    def _should_check(self, cache: dict) -> bool:
        """Determine if we should check PyPI based on cache."""
        last_check = cache.get("check_timestamp")
        if not last_check:
            return True

        try:
            last_check_time = datetime.fromisoformat(last_check)
            return datetime.now() - last_check_time > self.check_interval
        except (ValueError, TypeError):
            return True

    def _should_warn(self, cache: dict, latest_version: str) -> bool:
        """Determine if we should warn the user about the new version."""
        if not self._is_newer_version(latest_version):
            return False

        last_warned = cache.get("last_warned_timestamp")
        warned_version = cache.get("current_version_warned")

        # Always warn if this is a different newer version than last time
        if warned_version != self.current_version:
            return True

        if not last_warned:
            return True

        try:
            last_warned_time = datetime.fromisoformat(last_warned)
            return datetime.now() - last_warned_time > self.reminder_interval
        except (ValueError, TypeError):
            return True

    def _is_newer_version(self, latest_version: str) -> bool:
        """Compare versions to determine if latest is newer."""
        try:
            from packaging.version import Version

            return Version(latest_version) > Version(self.current_version)
        except ImportError:
            # Fallback: simple string comparison for semver
            return self._simple_version_compare(latest_version)
        except Exception:
            return False

    def _simple_version_compare(self, latest_version: str) -> bool:
        """Simple semver comparison without packaging library."""
        try:
            current_parts = [int(x) for x in self.current_version.split(".")]
            latest_parts = [int(x) for x in latest_version.split(".")]

            # Pad shorter version with zeros
            max_len = max(len(current_parts), len(latest_parts))
            current_parts.extend([0] * (max_len - len(current_parts)))
            latest_parts.extend([0] * (max_len - len(latest_parts)))

            return latest_parts > current_parts
        except (ValueError, AttributeError):
            return False

    def _format_warning_message(self, latest_version: str) -> str:
        """Format the version update warning message."""
        return (
            f"\n{'='*60}\n"
            f"A newer version of esgvoc is available!\n"
            f"  Current version: {self.current_version}\n"
            f"  Latest version:  {latest_version}\n"
            f"\n"
            f"Update using one of:\n"
            f"  pip install --upgrade esgvoc\n"
            f"  uv pip install --upgrade esgvoc\n"
            f"  conda update esgvoc\n"
            f"\n"
            f"After updating, reinstall vocabularies with:\n"
            f"  esgvoc install\n"
            f"{'='*60}\n"
        )

    def _display_warning(self, latest_version: str) -> None:
        """Display the version warning using appropriate method."""
        message = self._format_warning_message(latest_version)

        # Try Rich console first (works in TTY contexts)
        if sys.stdout.isatty():
            try:
                from rich.console import Console

                console = Console(stderr=True)
                console.print(f"[yellow]{message}[/yellow]")
                return
            except ImportError:
                pass

        # Fallback: print to stdout (visible in jupyter, scripts, etc.)
        print(message)

    def _do_check(self) -> Tuple[Optional[str], bool]:
        """
        Perform the version check.

        Returns:
            Tuple of (latest_version, should_warn)
        """
        cache = self._load_cache()
        latest_version = None
        should_warn = False

        if self._should_check(cache):
            latest_version = self._fetch_latest_version()
            if latest_version:
                cache["latest_version"] = latest_version
                cache["check_timestamp"] = datetime.now().isoformat()
                self._save_cache(cache)
            else:
                # Fallback to cached version if fetch failed
                latest_version = cache.get("latest_version")
        else:
            latest_version = cache.get("latest_version")

        if latest_version and self._should_warn(cache, latest_version):
            should_warn = True
            cache["last_warned_timestamp"] = datetime.now().isoformat()
            cache["current_version_warned"] = self.current_version
            self._save_cache(cache)

        return latest_version, should_warn

    def check_async(self) -> None:
        """Start version check in background thread."""
        if not self.enabled:
            return

        def _check_wrapper():
            try:
                latest_version, should_warn = self._do_check()
                if should_warn and latest_version:
                    self._display_warning(latest_version)
            except Exception as e:
                logger.debug(f"Version check failed: {e}")
            finally:
                self._check_complete.set()

        self._check_thread = threading.Thread(
            target=_check_wrapper, daemon=True, name="esgvoc-version-check"
        )
        self._check_thread.start()

    def check_sync(self) -> Optional[str]:
        """
        Perform synchronous version check.

        Returns:
            Latest version if newer, None otherwise.
        """
        if not self.enabled:
            return None

        try:
            latest_version, should_warn = self._do_check()
            if should_warn and latest_version:
                self._display_warning(latest_version)
                return latest_version
        except Exception as e:
            logger.debug(f"Version check failed: {e}")
        return None

    def check_now(self) -> dict:
        """
        Force an immediate version check, bypassing cache intervals.

        Returns:
            Dictionary with version details including fresh data.
        """
        latest_version = self._fetch_latest_version()
        cache = self._load_cache()
        if latest_version:
            cache["latest_version"] = latest_version
            cache["check_timestamp"] = datetime.now().isoformat()
            self._save_cache(cache)

        return {
            "current_version": self.current_version,
            "latest_version": latest_version or cache.get("latest_version"),
            "last_checked": cache.get("check_timestamp"),
            "update_available": self._is_newer_version(
                latest_version or cache.get("latest_version", self.current_version)
            ),
        }

    def get_version_info(self) -> dict:
        """
        Get version information without displaying warnings.

        Returns:
            Dictionary with version details.
        """
        cache = self._load_cache()
        cached_version = cache.get("latest_version", self.current_version)
        return {
            "current_version": self.current_version,
            "latest_version": cache.get("latest_version"),
            "last_checked": cache.get("check_timestamp"),
            "update_available": self._is_newer_version(cached_version),
        }

    def reset_reminder(self) -> None:
        """Reset the reminder timer so warning shows again."""
        cache = self._load_cache()
        cache.pop("last_warned_timestamp", None)
        cache.pop("current_version_warned", None)
        self._save_cache(cache)


# Module-level singleton for easy access
_version_checker: Optional[VersionChecker] = None


def get_version_checker() -> Optional[VersionChecker]:
    """Get the global version checker instance."""
    return _version_checker


def initialize_version_checker(
    cache_dir: Path,
    check_interval_hours: int = 12,
    reminder_interval_hours: int = 72,
    enabled: bool = True,
) -> VersionChecker:
    """
    Initialize the global version checker.

    Args:
        cache_dir: Directory for cache storage
        check_interval_hours: Hours between PyPI checks
        reminder_interval_hours: Hours between showing warnings
        enabled: Whether version checking is enabled

    Returns:
        The initialized VersionChecker instance.
    """
    global _version_checker
    _version_checker = VersionChecker(
        cache_dir=cache_dir,
        check_interval_hours=check_interval_hours,
        reminder_interval_hours=reminder_interval_hours,
        enabled=enabled,
    )
    return _version_checker

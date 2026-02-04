"""
Tests for the version checking system.

These tests verify that the version checker correctly:
- Fetches versions from PyPI
- Compares versions correctly
- Caches results appropriately
- Respects check/reminder intervals
- Handles errors gracefully
"""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from esgvoc.core.version_checker import VersionChecker, EsgvocVersionWarning


class TestVersionComparison:
    """Test version comparison logic."""

    @pytest.fixture
    def checker(self, tmp_path):
        """Create a VersionChecker with a known 'old' version."""
        checker = VersionChecker(
            cache_dir=tmp_path,
            check_interval_hours=12,
            reminder_interval_hours=72,
            enabled=True,
        )
        # Override current_version to simulate an "old" version
        checker.current_version = "1.0.0"
        return checker

    def test_newer_version_detected(self, checker):
        """Test that a newer version is correctly detected."""
        assert checker._is_newer_version("1.0.1") is True
        assert checker._is_newer_version("1.1.0") is True
        assert checker._is_newer_version("2.0.0") is True

    def test_same_version_not_newer(self, checker):
        """Test that the same version is not considered newer."""
        assert checker._is_newer_version("1.0.0") is False

    def test_older_version_not_newer(self, checker):
        """Test that an older version is not considered newer."""
        assert checker._is_newer_version("0.9.0") is False
        assert checker._is_newer_version("0.9.9") is False

    def test_simple_version_compare(self, checker):
        """Test the fallback simple version comparison."""
        assert checker._simple_version_compare("1.0.1") is True
        assert checker._simple_version_compare("2.0.0") is True
        assert checker._simple_version_compare("1.0.0") is False
        assert checker._simple_version_compare("0.9.0") is False

    def test_version_with_different_lengths(self, checker):
        """Test version comparison with different segment counts."""
        checker.current_version = "1.0"
        assert checker._is_newer_version("1.0.1") is True
        assert checker._is_newer_version("1.1") is True

        checker.current_version = "1.0.0.0"
        assert checker._is_newer_version("1.0.0.1") is True
        assert checker._is_newer_version("1.0.1") is True

    def test_invalid_version_handling(self, checker):
        """Test that invalid versions don't crash."""
        assert checker._is_newer_version("not.a.version") is False
        assert checker._is_newer_version("") is False
        assert checker._simple_version_compare("invalid") is False


class TestPyPIFetch:
    """Test PyPI version fetching."""

    @pytest.fixture
    def checker(self, tmp_path):
        """Create a VersionChecker instance."""
        checker = VersionChecker(cache_dir=tmp_path, enabled=True)
        checker.current_version = "1.0.0"
        return checker

    def test_fetch_latest_version_success(self, checker):
        """Test successful version fetch from PyPI."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"info": {"version": "2.0.0"}}
        mock_response.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_response) as mock_get:
            version = checker._fetch_latest_version()
            assert version == "2.0.0"
            mock_get.assert_called_once_with("https://pypi.org/pypi/esgvoc/json", timeout=3)

    def test_fetch_latest_version_network_error(self, checker):
        """Test graceful handling of network errors."""
        import requests

        with patch("requests.get", side_effect=requests.RequestException("Network error")):
            version = checker._fetch_latest_version()
            assert version is None

    def test_fetch_latest_version_timeout(self, checker):
        """Test graceful handling of timeout."""
        import requests

        with patch("requests.get", side_effect=requests.Timeout("Timeout")):
            version = checker._fetch_latest_version()
            assert version is None

    def test_fetch_latest_version_invalid_json(self, checker):
        """Test graceful handling of invalid JSON response."""
        mock_response = MagicMock()
        mock_response.json.side_effect = json.JSONDecodeError("Invalid", "", 0)
        mock_response.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_response):
            version = checker._fetch_latest_version()
            assert version is None

    def test_fetch_latest_version_missing_info(self, checker):
        """Test handling of response missing expected fields."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"other": "data"}
        mock_response.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_response):
            version = checker._fetch_latest_version()
            assert version is None


class TestCaching:
    """Test cache functionality."""

    @pytest.fixture
    def checker(self, tmp_path):
        """Create a VersionChecker instance."""
        checker = VersionChecker(
            cache_dir=tmp_path,
            check_interval_hours=12,
            reminder_interval_hours=72,
            enabled=True,
        )
        checker.current_version = "1.0.0"
        return checker

    def test_cache_save_and_load(self, checker):
        """Test that cache is correctly saved and loaded."""
        test_data = {
            "latest_version": "2.0.0",
            "check_timestamp": datetime.now().isoformat(),
        }
        checker._save_cache(test_data)

        loaded = checker._load_cache()
        assert loaded["latest_version"] == "2.0.0"
        assert "check_timestamp" in loaded

    def test_load_empty_cache(self, checker):
        """Test loading when no cache exists."""
        cache = checker._load_cache()
        assert cache == {}

    def test_load_corrupted_cache(self, checker):
        """Test handling of corrupted cache file."""
        # Write invalid JSON
        checker.cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(checker.cache_file, "w") as f:
            f.write("not valid json {{{")

        cache = checker._load_cache()
        assert cache == {}

    def test_should_check_no_cache(self, checker):
        """Test that check is needed when no cache exists."""
        assert checker._should_check({}) is True

    def test_should_check_recent_check(self, checker):
        """Test that check is not needed if recently checked."""
        cache = {"check_timestamp": datetime.now().isoformat()}
        assert checker._should_check(cache) is False

    def test_should_check_old_check(self, checker):
        """Test that check is needed if check is old."""
        old_time = datetime.now() - timedelta(hours=24)
        cache = {"check_timestamp": old_time.isoformat()}
        assert checker._should_check(cache) is True

    def test_should_check_invalid_timestamp(self, checker):
        """Test handling of invalid timestamp in cache."""
        cache = {"check_timestamp": "not-a-timestamp"}
        assert checker._should_check(cache) is True


class TestWarningLogic:
    """Test warning display logic."""

    @pytest.fixture
    def checker(self, tmp_path):
        """Create a VersionChecker instance."""
        checker = VersionChecker(
            cache_dir=tmp_path,
            check_interval_hours=12,
            reminder_interval_hours=72,
            enabled=True,
        )
        checker.current_version = "1.0.0"
        return checker

    def test_should_warn_newer_version_no_previous_warning(self, checker):
        """Test warning is shown for newer version without prior warning."""
        cache = {}
        assert checker._should_warn(cache, "2.0.0") is True

    def test_should_warn_same_version(self, checker):
        """Test no warning for same version."""
        cache = {}
        assert checker._should_warn(cache, "1.0.0") is False

    def test_should_warn_older_version(self, checker):
        """Test no warning for older version."""
        cache = {}
        assert checker._should_warn(cache, "0.9.0") is False

    def test_should_warn_recent_warning(self, checker):
        """Test no warning if recently warned for same current version."""
        cache = {
            "last_warned_timestamp": datetime.now().isoformat(),
            "current_version_warned": "1.0.0",
        }
        assert checker._should_warn(cache, "2.0.0") is False

    def test_should_warn_old_warning(self, checker):
        """Test warning shown if last warning was long ago."""
        old_time = datetime.now() - timedelta(hours=100)  # > 72 hours
        cache = {
            "last_warned_timestamp": old_time.isoformat(),
            "current_version_warned": "1.0.0",
        }
        assert checker._should_warn(cache, "2.0.0") is True

    def test_should_warn_different_current_version(self, checker):
        """Test warning shown if user has upgraded but not to latest."""
        # User was on 0.9.0, warned about 2.0.0, now on 1.0.0
        cache = {
            "last_warned_timestamp": datetime.now().isoformat(),
            "current_version_warned": "0.9.0",  # Different from current 1.0.0
        }
        assert checker._should_warn(cache, "2.0.0") is True


class TestFullCheckFlow:
    """Test the complete version check flow."""

    @pytest.fixture
    def checker(self, tmp_path):
        """Create a VersionChecker instance."""
        checker = VersionChecker(
            cache_dir=tmp_path,
            check_interval_hours=12,
            reminder_interval_hours=72,
            enabled=True,
        )
        checker.current_version = "1.0.0"
        return checker

    def test_do_check_new_version_available(self, checker):
        """Test full check flow when new version is available."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"info": {"version": "2.0.0"}}
        mock_response.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_response):
            latest, should_warn = checker._do_check()
            assert latest == "2.0.0"
            assert should_warn is True

        # Verify cache was updated
        cache = checker._load_cache()
        assert cache["latest_version"] == "2.0.0"
        assert "check_timestamp" in cache
        assert "last_warned_timestamp" in cache

    def test_do_check_no_new_version(self, checker):
        """Test full check flow when no new version is available."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"info": {"version": "1.0.0"}}
        mock_response.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_response):
            latest, should_warn = checker._do_check()
            assert latest == "1.0.0"
            assert should_warn is False

    def test_do_check_uses_cache_if_recent(self, checker):
        """Test that recent cache is used instead of fetching."""
        # Pre-populate cache
        cache = {
            "latest_version": "2.0.0",
            "check_timestamp": datetime.now().isoformat(),
        }
        checker._save_cache(cache)

        with patch("requests.get") as mock_get:
            latest, should_warn = checker._do_check()
            # Should not call PyPI
            mock_get.assert_not_called()
            assert latest == "2.0.0"
            assert should_warn is True

    def test_do_check_network_failure_uses_cache(self, checker):
        """Test that cache is used when network fails."""
        import requests

        # Pre-populate cache with old timestamp to force check
        old_time = datetime.now() - timedelta(hours=24)
        cache = {
            "latest_version": "1.5.0",
            "check_timestamp": old_time.isoformat(),
        }
        checker._save_cache(cache)

        with patch("requests.get", side_effect=requests.RequestException("Network error")):
            latest, should_warn = checker._do_check()
            # Should fall back to cached version
            assert latest == "1.5.0"
            assert should_warn is True


class TestCheckNow:
    """Test the check_now() forced check method."""

    @pytest.fixture
    def checker(self, tmp_path):
        """Create a VersionChecker instance."""
        checker = VersionChecker(
            cache_dir=tmp_path,
            check_interval_hours=12,
            reminder_interval_hours=72,
            enabled=True,
        )
        checker.current_version = "1.0.0"
        return checker

    def test_check_now_updates_cache(self, checker):
        """Test that check_now always fetches and updates cache."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"info": {"version": "2.0.0"}}
        mock_response.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_response):
            info = checker.check_now()

        assert info["current_version"] == "1.0.0"
        assert info["latest_version"] == "2.0.0"
        assert info["update_available"] is True
        assert info["last_checked"] is not None

        # Verify cache was updated
        cache = checker._load_cache()
        assert cache["latest_version"] == "2.0.0"
        assert "check_timestamp" in cache

    def test_check_now_bypasses_interval(self, checker):
        """Test that check_now ignores the check interval."""
        # Pre-populate cache with recent timestamp
        cache = {
            "latest_version": "1.5.0",
            "check_timestamp": datetime.now().isoformat(),
        }
        checker._save_cache(cache)

        mock_response = MagicMock()
        mock_response.json.return_value = {"info": {"version": "2.0.0"}}
        mock_response.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_response) as mock_get:
            info = checker.check_now()
            # Should call PyPI even though cache is recent
            mock_get.assert_called_once()
            assert info["latest_version"] == "2.0.0"

    def test_check_now_network_failure(self, checker):
        """Test check_now falls back to cache on network failure."""
        import requests

        cache = {
            "latest_version": "1.5.0",
            "check_timestamp": "2026-01-20T12:00:00",
        }
        checker._save_cache(cache)

        with patch("requests.get", side_effect=requests.RequestException("fail")):
            info = checker.check_now()
            assert info["latest_version"] == "1.5.0"
            assert info["update_available"] is True


class TestDisabledChecker:
    """Test behavior when checker is disabled."""

    def test_check_async_disabled(self, tmp_path):
        """Test that async check does nothing when disabled."""
        checker = VersionChecker(cache_dir=tmp_path, enabled=False)

        with patch("requests.get") as mock_get:
            checker.check_async()
            # Should not start any network request
            mock_get.assert_not_called()

    def test_check_sync_disabled(self, tmp_path):
        """Test that sync check returns None when disabled."""
        checker = VersionChecker(cache_dir=tmp_path, enabled=False)

        with patch("requests.get") as mock_get:
            result = checker.check_sync()
            assert result is None
            mock_get.assert_not_called()


class TestWarningDisplay:
    """Test warning message formatting and display."""

    @pytest.fixture
    def checker(self, tmp_path):
        """Create a VersionChecker instance."""
        checker = VersionChecker(cache_dir=tmp_path, enabled=True)
        checker.current_version = "1.0.0"
        return checker

    def test_format_warning_message(self, checker):
        """Test warning message contains expected information."""
        message = checker._format_warning_message("2.0.0")

        assert "1.0.0" in message  # Current version
        assert "2.0.0" in message  # Latest version
        assert "pip install --upgrade esgvoc" in message
        assert "uv pip install --upgrade esgvoc" in message
        assert "conda update esgvoc" in message
        assert "esgvoc install" in message

    def test_display_warning_non_tty(self, checker):
        """Test warning display falls back to stdout print for non-TTY."""
        with patch("sys.stdout.isatty", return_value=False):
            with patch("builtins.print") as mock_print:
                checker._display_warning("2.0.0")
                mock_print.assert_called_once()
                call_args = mock_print.call_args
                assert "2.0.0" in call_args[0][0]


class TestResetReminder:
    """Test reminder reset functionality."""

    def test_reset_reminder(self, tmp_path):
        """Test that reset_reminder clears warning timestamps."""
        checker = VersionChecker(cache_dir=tmp_path, enabled=True)

        # Pre-populate cache with warning data
        cache = {
            "latest_version": "2.0.0",
            "check_timestamp": datetime.now().isoformat(),
            "last_warned_timestamp": datetime.now().isoformat(),
            "current_version_warned": "1.0.0",
        }
        checker._save_cache(cache)

        # Reset reminder
        checker.reset_reminder()

        # Verify warning data is cleared but version data remains
        new_cache = checker._load_cache()
        assert "latest_version" in new_cache
        assert "check_timestamp" in new_cache
        assert "last_warned_timestamp" not in new_cache
        assert "current_version_warned" not in new_cache


class TestGetVersionInfo:
    """Test version info retrieval."""

    def test_get_version_info(self, tmp_path):
        """Test get_version_info returns correct data."""
        checker = VersionChecker(cache_dir=tmp_path, enabled=True)
        checker.current_version = "1.0.0"

        # Pre-populate cache
        cache = {
            "latest_version": "2.0.0",
            "check_timestamp": "2026-01-22T12:00:00",
        }
        checker._save_cache(cache)

        info = checker.get_version_info()

        assert info["current_version"] == "1.0.0"
        assert info["latest_version"] == "2.0.0"
        assert info["last_checked"] == "2026-01-22T12:00:00"
        assert info["update_available"] is True

    def test_get_version_info_no_cache(self, tmp_path):
        """Test get_version_info with empty cache."""
        checker = VersionChecker(cache_dir=tmp_path, enabled=True)
        checker.current_version = "1.0.0"

        info = checker.get_version_info()

        assert info["current_version"] == "1.0.0"
        assert info["latest_version"] is None
        assert info["last_checked"] is None
        assert info["update_available"] is False

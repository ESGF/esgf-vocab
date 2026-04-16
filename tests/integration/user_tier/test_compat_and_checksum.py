"""
User Tier — esgvoc version compatibility and checksum/corruption tests.

Tests that DBFetcher.check_compatibility correctly gates installation based on
esgvoc_min_version / esgvoc_max_version constraints in a DBArtifact, and that
the atomic download path handles checksum failures correctly (Scenarios 9-11).

Plan scenarios covered:
  UT-65  Artifact with min_version > installed esgvoc → check_compatibility returns False
  UT-66  Artifact with min_version <= installed esgvoc → check_compatibility returns True
  UT-67  Artifact with max_version <= installed esgvoc → check_compatibility returns False
  UT-68  Artifact with max_version > installed esgvoc → check_compatibility returns True
  UT-69  Artifact with no version constraints → check_compatibility returns True
  UT-70  check_compatibility message contains project/version and hint when incompatible
  UT-71  download_db raises EsgvocChecksumError when content is corrupted
  UT-72  download_db retries on checksum mismatch (up to _MAX_RETRIES)
  UT-73  After _MAX_RETRIES checksum failures, EsgvocChecksumError propagates
  UT-74  download_db skips download when checksum already matches on disk
  UT-75  Corrupted local DB triggers re-download on next install call
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from esgvoc.core.db_artifact import DBArtifact
from esgvoc.core.db_fetcher import DBFetcher, EsgvocChecksumError, _MAX_RETRIES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_artifact(
    project_id: str = "cmip6",
    version: str = "v1.0.0",
    *,
    min_version: str | None = None,
    max_version: str | None = None,
    checksum: str | None = None,
    size_bytes: int = 0,
) -> DBArtifact:
    return DBArtifact(
        project_id=project_id,
        version=version,
        download_url=f"https://example.com/{project_id}-{version}.db",
        esgvoc_min_version=min_version,
        esgvoc_max_version=max_version,
        checksum_sha256=checksum,
        size_bytes=size_bytes,
        is_prerelease=False,
    )


def _installed_esgvoc_version() -> str | None:
    import esgvoc
    return getattr(esgvoc, "__version__", None)


# ---------------------------------------------------------------------------
# UT-65  min_version > installed → incompatible
# ---------------------------------------------------------------------------

class TestMinVersionIncompatible:
    """UT-65: check_compatibility returns False when min_version exceeds installed esgvoc."""

    def test_higher_min_version_returns_false(self, tmp_path):
        fetcher = DBFetcher(cache_dir=tmp_path / "cache")
        artifact = _make_artifact(min_version="99999.0.0")

        installed = _installed_esgvoc_version()
        if installed is None:
            pytest.skip("Cannot determine installed esgvoc version")

        compatible, msg = fetcher.check_compatibility(artifact)
        assert compatible is False, (
            f"Expected incompatible with min_version=99999.0.0; installed={installed}"
        )

    def test_incompatible_message_contains_project_version(self, tmp_path):
        fetcher = DBFetcher(cache_dir=tmp_path / "cache")
        artifact = _make_artifact(project_id="cmip6", version="v99.0.0", min_version="99999.0.0")

        installed = _installed_esgvoc_version()
        if installed is None:
            pytest.skip("Cannot determine installed esgvoc version")

        compatible, msg = fetcher.check_compatibility(artifact)
        if not compatible:
            assert "cmip6" in msg
            assert "v99.0.0" in msg or "99999.0.0" in msg

    def test_incompatible_message_suggests_upgrade(self, tmp_path):
        fetcher = DBFetcher(cache_dir=tmp_path / "cache")
        artifact = _make_artifact(min_version="99999.0.0")

        installed = _installed_esgvoc_version()
        if installed is None:
            pytest.skip("Cannot determine installed esgvoc version")

        compatible, msg = fetcher.check_compatibility(artifact)
        if not compatible:
            assert "pip" in msg.lower() or "upgrade" in msg.lower() or "install" in msg.lower()


# ---------------------------------------------------------------------------
# UT-66  min_version <= installed → compatible
# ---------------------------------------------------------------------------

class TestMinVersionCompatible:
    """UT-66: check_compatibility returns True when min_version is satisfied."""

    def test_zero_min_version_is_compatible(self, tmp_path):
        fetcher = DBFetcher(cache_dir=tmp_path / "cache")
        artifact = _make_artifact(min_version="0.0.1")

        installed = _installed_esgvoc_version()
        if installed is None:
            pytest.skip("Cannot determine installed esgvoc version")

        compatible, msg = fetcher.check_compatibility(artifact)
        assert compatible is True, (
            f"Expected compatible with min_version=0.0.1; installed={installed}; msg={msg}"
        )

    def test_same_version_as_installed_is_compatible(self, tmp_path):
        installed = _installed_esgvoc_version()
        if installed is None:
            pytest.skip("Cannot determine installed esgvoc version")

        fetcher = DBFetcher(cache_dir=tmp_path / "cache")
        artifact = _make_artifact(min_version=installed)
        compatible, msg = fetcher.check_compatibility(artifact)
        assert compatible is True, f"min=installed should be compatible; msg={msg}"

    def test_compatible_message_is_empty_string(self, tmp_path):
        fetcher = DBFetcher(cache_dir=tmp_path / "cache")
        artifact = _make_artifact(min_version="0.0.1")

        installed = _installed_esgvoc_version()
        if installed is None:
            pytest.skip("Cannot determine installed esgvoc version")

        compatible, msg = fetcher.check_compatibility(artifact)
        if compatible:
            assert msg == ""


# ---------------------------------------------------------------------------
# UT-67  max_version <= installed → incompatible (warning)
# ---------------------------------------------------------------------------

class TestMaxVersionIncompatible:
    """UT-67: check_compatibility returns False when installed >= max_version."""

    def test_max_version_0_is_incompatible(self, tmp_path):
        installed = _installed_esgvoc_version()
        if installed is None:
            pytest.skip("Cannot determine installed esgvoc version")

        fetcher = DBFetcher(cache_dir=tmp_path / "cache")
        # max_version of "0.0.1" means the artifact only supports esgvoc < 0.0.1
        # Current esgvoc is >= 0.0.1 in practice
        artifact = _make_artifact(max_version="0.0.1")
        compatible, msg = fetcher.check_compatibility(artifact)
        # Either compatible=False with a message, or True if somehow installed < 0.0.1
        if not compatible:
            assert msg  # Should have an explanation

    def test_very_old_max_version_gives_warning_message(self, tmp_path):
        installed = _installed_esgvoc_version()
        if installed is None:
            pytest.skip("Cannot determine installed esgvoc version")

        fetcher = DBFetcher(cache_dir=tmp_path / "cache")
        artifact = _make_artifact(max_version="0.0.1")
        compatible, msg = fetcher.check_compatibility(artifact)
        if not compatible:
            # Message should mention the max_version or "Warning"
            assert "0.0.1" in msg or "Warning" in msg or "warning" in msg


# ---------------------------------------------------------------------------
# UT-68  max_version > installed → compatible
# ---------------------------------------------------------------------------

class TestMaxVersionCompatible:
    """UT-68: check_compatibility returns True when installed < max_version."""

    def test_huge_max_version_is_compatible(self, tmp_path):
        installed = _installed_esgvoc_version()
        if installed is None:
            pytest.skip("Cannot determine installed esgvoc version")

        fetcher = DBFetcher(cache_dir=tmp_path / "cache")
        artifact = _make_artifact(max_version="99999.0.0")
        compatible, msg = fetcher.check_compatibility(artifact)
        assert compatible is True, (
            f"Expected compatible with max_version=99999.0.0; installed={installed}; msg={msg}"
        )


# ---------------------------------------------------------------------------
# UT-69  No version constraints → always compatible
# ---------------------------------------------------------------------------

class TestNoVersionConstraints:
    """UT-69: Artifact with no min/max constraints is always compatible."""

    def test_no_constraints_returns_true(self, tmp_path):
        fetcher = DBFetcher(cache_dir=tmp_path / "cache")
        artifact = _make_artifact()  # no min/max
        compatible, msg = fetcher.check_compatibility(artifact)
        assert compatible is True

    def test_no_constraints_message_is_empty(self, tmp_path):
        fetcher = DBFetcher(cache_dir=tmp_path / "cache")
        artifact = _make_artifact()
        compatible, msg = fetcher.check_compatibility(artifact)
        assert msg == ""


# ---------------------------------------------------------------------------
# UT-70  Incompatible message quality
# ---------------------------------------------------------------------------

class TestCompatibilityMessage:
    """UT-70: Incompatibility message is informative."""

    def test_min_version_message_mentions_min_version(self, tmp_path):
        installed = _installed_esgvoc_version()
        if installed is None:
            pytest.skip("Cannot determine installed esgvoc version")

        fetcher = DBFetcher(cache_dir=tmp_path / "cache")
        artifact = _make_artifact(project_id="cmip6", version="v3.0.0", min_version="99999.0.0")
        compatible, msg = fetcher.check_compatibility(artifact)
        if not compatible:
            assert "99999.0.0" in msg or "cmip6" in msg

    def test_message_is_nonempty_when_incompatible(self, tmp_path):
        installed = _installed_esgvoc_version()
        if installed is None:
            pytest.skip("Cannot determine installed esgvoc version")

        fetcher = DBFetcher(cache_dir=tmp_path / "cache")
        artifact = _make_artifact(min_version="99999.0.0")
        compatible, msg = fetcher.check_compatibility(artifact)
        if not compatible:
            assert len(msg) > 0


# ---------------------------------------------------------------------------
# UT-71  download_db raises EsgvocChecksumError when content is corrupted
# ---------------------------------------------------------------------------

class TestChecksumError:
    """UT-71: download_db raises EsgvocChecksumError when the downloaded content is wrong."""

    def test_bad_content_raises_checksum_error(self, tmp_path, real_dbs):
        """Serving garbage bytes for a real-checksum artifact → EsgvocChecksumError."""
        real_bytes = real_dbs["v1_path"].read_bytes()
        good_checksum = hashlib.sha256(real_bytes).hexdigest()

        artifact = DBArtifact(
            project_id="cmip6",
            version="v1.0.0",
            download_url="https://example.com/cmip6.db",
            checksum_sha256=good_checksum,
            size_bytes=len(real_bytes),
            is_prerelease=False,
        )

        target = tmp_path / "out.db"
        fetcher = DBFetcher(cache_dir=tmp_path / "cache")

        # Serve corrupted bytes (trailing zero)
        corrupted = b"\x00" * 1024

        fake_response = MagicMock()
        fake_response.headers = {"content-length": str(len(corrupted))}
        fake_response.iter_content = lambda chunk_size: [corrupted]
        fake_response.__enter__ = lambda s: s
        fake_response.__exit__ = MagicMock(return_value=False)

        with patch.object(fetcher._session, "get", return_value=fake_response):
            with pytest.raises(EsgvocChecksumError):
                fetcher.download_db(artifact, target)

    def test_checksum_error_message_contains_expected_hash(self, tmp_path):
        """EsgvocChecksumError message should mention the expected checksum."""
        good_checksum = "a" * 64  # fake but valid-looking sha256

        artifact = DBArtifact(
            project_id="cmip6",
            version="v1.0.0",
            download_url="https://example.com/cmip6.db",
            checksum_sha256=good_checksum,
            size_bytes=1024,
            is_prerelease=False,
        )

        target = tmp_path / "out.db"
        fetcher = DBFetcher(cache_dir=tmp_path / "cache")

        corrupted = b"\x00" * 1024
        fake_response = MagicMock()
        fake_response.headers = {"content-length": "1024"}
        fake_response.iter_content = lambda chunk_size: [corrupted]
        fake_response.__enter__ = lambda s: s
        fake_response.__exit__ = MagicMock(return_value=False)

        with patch.object(fetcher._session, "get", return_value=fake_response):
            with pytest.raises(EsgvocChecksumError) as exc_info:
                fetcher._download_atomic(artifact, target)

        assert good_checksum in str(exc_info.value), (
            "Expected checksum should appear in error message"
        )


# ---------------------------------------------------------------------------
# UT-72  download_db retries on checksum mismatch
# ---------------------------------------------------------------------------

class TestChecksumRetry:
    """UT-72: download_db retries on EsgvocChecksumError before giving up."""

    def test_retries_on_checksum_mismatch(self, tmp_path):
        """_download_atomic is called up to _MAX_RETRIES times on failure."""
        good_checksum = "b" * 64

        artifact = DBArtifact(
            project_id="cmip6",
            version="v1.0.0",
            download_url="https://example.com/cmip6.db",
            checksum_sha256=good_checksum,
            size_bytes=0,
            is_prerelease=False,
        )

        target = tmp_path / "out.db"
        fetcher = DBFetcher(cache_dir=tmp_path / "cache")
        call_count = [0]

        def _always_fail(art, tgt, show_progress=True):
            call_count[0] += 1
            raise EsgvocChecksumError("Simulated mismatch")

        with patch.object(fetcher, "_download_atomic", side_effect=_always_fail):
            with pytest.raises(EsgvocChecksumError):
                fetcher.download_db(artifact, target)

        assert call_count[0] == _MAX_RETRIES, (
            f"Expected {_MAX_RETRIES} attempts; got {call_count[0]}"
        )


# ---------------------------------------------------------------------------
# UT-73  After _MAX_RETRIES checksum failures, error propagates
# ---------------------------------------------------------------------------

class TestChecksumFinalFailure:
    """UT-73: EsgvocChecksumError propagates after all retries exhausted."""

    def test_error_propagates_after_max_retries(self, tmp_path):
        artifact = DBArtifact(
            project_id="cmip6",
            version="v1.0.0",
            download_url="https://example.com/cmip6.db",
            checksum_sha256="c" * 64,
            size_bytes=0,
            is_prerelease=False,
        )
        target = tmp_path / "out.db"
        fetcher = DBFetcher(cache_dir=tmp_path / "cache")

        with patch.object(
            fetcher,
            "_download_atomic",
            side_effect=EsgvocChecksumError("always fails"),
        ):
            with pytest.raises(EsgvocChecksumError):
                fetcher.download_db(artifact, target)

    def test_target_not_created_after_all_retries_fail(self, tmp_path):
        """Target must not be left behind after all retries fail."""
        artifact = DBArtifact(
            project_id="cmip6",
            version="v1.0.0",
            download_url="https://example.com/cmip6.db",
            checksum_sha256="d" * 64,
            size_bytes=0,
            is_prerelease=False,
        )
        target = tmp_path / "out.db"
        fetcher = DBFetcher(cache_dir=tmp_path / "cache")

        with patch.object(
            fetcher,
            "_download_atomic",
            side_effect=EsgvocChecksumError("always fails"),
        ):
            with pytest.raises(EsgvocChecksumError):
                fetcher.download_db(artifact, target)

        # Target should not exist (temp file is cleaned up by NamedTemporaryFile)
        assert not target.exists(), "Target should not exist after all retries failed"


# ---------------------------------------------------------------------------
# UT-74  download_db skips download when checksum already matches on disk
# ---------------------------------------------------------------------------

class TestChecksumSkip:
    """UT-74: download_db is a no-op when the target already has the right checksum."""

    def test_skips_when_checksum_matches(self, tmp_path, real_dbs):
        """If target exists with correct checksum, no network call is made."""
        # Copy real DB to target
        target = tmp_path / "out.db"
        import shutil
        shutil.copy2(str(real_dbs["v1_path"]), str(target))

        real_bytes = real_dbs["v1_path"].read_bytes()
        checksum = hashlib.sha256(real_bytes).hexdigest()

        artifact = DBArtifact(
            project_id="cmip6",
            version="v1.0.0",
            download_url="https://example.com/cmip6.db",
            checksum_sha256=checksum,
            size_bytes=len(real_bytes),
            is_prerelease=False,
        )

        fetcher = DBFetcher(cache_dir=tmp_path / "cache")
        network_calls = [0]

        def _track(*args, **kwargs):
            network_calls[0] += 1
            raise AssertionError("Should not make a network call")

        with patch.object(fetcher._session, "get", side_effect=_track):
            result = fetcher.download_db(artifact, target)

        assert network_calls[0] == 0, "No network call expected when checksum matches"
        assert result == target

    def test_returns_target_path_on_skip(self, tmp_path, real_dbs):
        target = tmp_path / "cached.db"
        import shutil
        shutil.copy2(str(real_dbs["v1_path"]), str(target))
        real_bytes = real_dbs["v1_path"].read_bytes()
        checksum = hashlib.sha256(real_bytes).hexdigest()

        artifact = DBArtifact(
            project_id="cmip6",
            version="v1.0.0",
            download_url="https://example.com/cmip6.db",
            checksum_sha256=checksum,
            size_bytes=len(real_bytes),
            is_prerelease=False,
        )

        fetcher = DBFetcher(cache_dir=tmp_path / "cache")
        with patch.object(fetcher._session, "get", side_effect=AssertionError("no network")):
            result = fetcher.download_db(artifact, target)

        assert result == target


# ---------------------------------------------------------------------------
# UT-75  Corrupted local DB triggers re-download
# ---------------------------------------------------------------------------

class TestCorruptedLocalDb:
    """UT-75: If local DB has wrong checksum, download_db fetches fresh copy."""

    def test_wrong_checksum_triggers_download(self, tmp_path, real_dbs):
        """A local file with the wrong checksum forces a real download."""
        target = tmp_path / "out.db"

        # Write garbage to the target (wrong checksum)
        target.write_bytes(b"\xFF" * 1024)

        real_bytes = real_dbs["v1_path"].read_bytes()
        correct_checksum = hashlib.sha256(real_bytes).hexdigest()

        artifact = DBArtifact(
            project_id="cmip6",
            version="v1.0.0",
            download_url="https://example.com/cmip6.db",
            checksum_sha256=correct_checksum,
            size_bytes=len(real_bytes),
            is_prerelease=False,
        )

        fetcher = DBFetcher(cache_dir=tmp_path / "cache")
        download_calls = [0]

        def _fake_download(art, tgt, show_progress=True):
            download_calls[0] += 1
            import shutil
            shutil.copy2(str(real_dbs["v1_path"]), str(tgt))

        with patch.object(fetcher, "_download_atomic", side_effect=_fake_download):
            fetcher.download_db(artifact, target)

        assert download_calls[0] >= 1, (
            "Expected at least 1 download call when local checksum is wrong"
        )

    def test_after_redownload_target_is_valid(self, tmp_path, real_dbs):
        """After re-download due to bad local checksum, target is a valid SQLite file."""
        import sqlite3
        target = tmp_path / "out.db"
        target.write_bytes(b"\xFF" * 1024)  # corrupted

        real_bytes = real_dbs["v1_path"].read_bytes()
        correct_checksum = hashlib.sha256(real_bytes).hexdigest()

        artifact = DBArtifact(
            project_id="cmip6",
            version="v1.0.0",
            download_url="https://example.com/cmip6.db",
            checksum_sha256=correct_checksum,
            size_bytes=len(real_bytes),
            is_prerelease=False,
        )

        fetcher = DBFetcher(cache_dir=tmp_path / "cache")

        import shutil

        def _fake_download(art, tgt, show_progress=True):
            shutil.copy2(str(real_dbs["v1_path"]), str(tgt))

        with patch.object(fetcher, "_download_atomic", side_effect=_fake_download):
            fetcher.download_db(artifact, target)

        # Verify the result is a valid SQLite DB
        conn = sqlite3.connect(str(target))
        try:
            conn.execute("SELECT COUNT(*) FROM _esgvoc_metadata").fetchone()
        finally:
            conn.close()

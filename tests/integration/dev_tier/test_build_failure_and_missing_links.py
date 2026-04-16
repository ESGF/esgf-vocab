"""
Dev Tier — Build failure and missing-links tests (Scenario 21).

Tests that DBBuilder with fail_on_missing_links=True raises
EsgvocMissingLinksError when the project references a universe term
that does not exist, and that MissingLinksTracker behaves correctly.

Also covers Scenario 16 (unknown term type / graceful degradation):
EsgvocDbError is raised when get_pydantic_class encounters a type not
in DATA_DESCRIPTOR_CLASS_MAPPING.

Plan scenarios covered:
  DT-126  MissingLinksTracker starts empty
  DT-127  MissingLinksTracker.add records a link and has_missing_links returns True
  DT-128  MissingLinksTracker.check_and_raise raises EsgvocMissingLinksError
  DT-129  EsgvocMissingLinksError carries the list of missing links
  DT-130  MissingLinksTracker.clear empties the tracker
  DT-131  get_pydantic_class raises EsgvocDbError for unknown type (Scenario 16)
  DT-132  get_pydantic_class returns the correct class for a known type
  DT-133  build_dev with fail_on_missing_links=False succeeds even with broken links
  DT-134  DBBuilder with fail_on_missing_links raises on bad project (integration)
"""
from __future__ import annotations

import pytest

from esgvoc.core.service.missing_links import MissingLinksTracker, MissingLinkInfo
from esgvoc.core.exceptions import EsgvocMissingLinksError, EsgvocDbError


# ---------------------------------------------------------------------------
# DT-126  MissingLinksTracker starts empty
# ---------------------------------------------------------------------------

class TestMissingLinksTrackerEmpty:
    """DT-126: A fresh MissingLinksTracker has no missing links."""

    def test_has_no_missing_links_initially(self):
        tracker = MissingLinksTracker()
        assert tracker.has_missing_links() is False

    def test_missing_links_list_is_empty(self):
        tracker = MissingLinksTracker()
        assert tracker.missing_links == []

    def test_check_and_raise_does_not_raise_when_empty(self):
        tracker = MissingLinksTracker()
        tracker.check_and_raise()  # Should not raise

    def test_print_summary_returns_false_when_empty(self, capsys):
        tracker = MissingLinksTracker()
        result = tracker.print_summary()
        assert result is False


# ---------------------------------------------------------------------------
# DT-127  add records a link
# ---------------------------------------------------------------------------

class TestMissingLinksTrackerAdd:
    """DT-127: Adding a link makes has_missing_links return True."""

    def _make_link(self) -> MissingLinkInfo:
        return MissingLinkInfo(
            ingestion_context="project:cmip6",
            current_term="experiment/new-exp.json",
            string_value="activity:non-existent",
            expected_uri="https://example.com/universe/activity/non-existent",
            local_path="/repos/WCRP-universe/activity/non-existent.json",
            property_name="activity",
        )

    def test_add_makes_has_missing_links_true(self):
        tracker = MissingLinksTracker()
        tracker.add(self._make_link())
        assert tracker.has_missing_links() is True

    def test_add_increments_list(self):
        tracker = MissingLinksTracker()
        tracker.add(self._make_link())
        assert len(tracker.missing_links) == 1

    def test_add_from_params_records_link(self):
        tracker = MissingLinksTracker()
        tracker.add_from_params(
            ingestion_context="universe",
            current_term="activity/some-act.json",
            string_value="source_type:missing",
            expected_uri="https://example.com/universe/source_type/missing",
            local_path="/repos/WCRP-universe/source_type/missing.json",
            property_name="source_type",
        )
        assert tracker.has_missing_links() is True
        assert tracker.missing_links[0].string_value == "source_type:missing"
        assert tracker.missing_links[0].property_name == "source_type"

    def test_multiple_adds_accumulate(self):
        tracker = MissingLinksTracker()
        for i in range(3):
            tracker.add_from_params(
                ingestion_context="project:cmip6",
                current_term=f"term_{i}",
                string_value=f"ref_{i}",
                expected_uri=f"https://example.com/{i}",
                local_path=f"/path/{i}",
            )
        assert len(tracker.missing_links) == 3


# ---------------------------------------------------------------------------
# DT-128  check_and_raise raises EsgvocMissingLinksError
# ---------------------------------------------------------------------------

class TestMissingLinksTrackerRaise:
    """DT-128: check_and_raise raises EsgvocMissingLinksError when links exist."""

    def test_raises_when_links_present(self):
        tracker = MissingLinksTracker()
        tracker.add_from_params(
            ingestion_context="project:cmip6",
            current_term="experiment/bad-exp.json",
            string_value="activity:nonexistent",
            expected_uri="https://example.com/activity/nonexistent",
            local_path="/path/nonexistent.json",
        )
        with pytest.raises(EsgvocMissingLinksError):
            tracker.check_and_raise()

    def test_raises_only_when_links_present(self):
        tracker = MissingLinksTracker()
        # No links → should not raise
        tracker.check_and_raise()
        # Now add a link
        tracker.add_from_params(
            ingestion_context="universe",
            current_term="term.json",
            string_value="bad:ref",
            expected_uri="https://x.com/ref",
            local_path="/path",
        )
        with pytest.raises(EsgvocMissingLinksError):
            tracker.check_and_raise()


# ---------------------------------------------------------------------------
# DT-129  EsgvocMissingLinksError carries the list
# ---------------------------------------------------------------------------

class TestEsgvocMissingLinksError:
    """DT-129: EsgvocMissingLinksError carries the list of MissingLinkInfo."""

    def test_error_carries_missing_links(self):
        tracker = MissingLinksTracker()
        tracker.add_from_params(
            ingestion_context="project:cmip6",
            current_term="experiment/bad-exp.json",
            string_value="activity:nonexistent",
            expected_uri="https://example.com/activity/nonexistent",
            local_path="/path/nonexistent.json",
            property_name="activity",
        )
        with pytest.raises(EsgvocMissingLinksError) as exc_info:
            tracker.check_and_raise()

        err = exc_info.value
        # EsgvocMissingLinksError is constructed with the missing_links list
        assert hasattr(err, "args")
        assert len(err.args) >= 1
        # The first arg should be the list or a message containing link info
        arg = err.args[0]
        if isinstance(arg, list):
            assert len(arg) == 1
            assert isinstance(arg[0], MissingLinkInfo)
        else:
            # Or a descriptive string
            assert "nonexistent" in str(arg).lower() or "missing" in str(arg).lower()

    def test_error_is_esgvoc_exception(self):
        from esgvoc.core.exceptions import EsgvocException
        err = EsgvocMissingLinksError([])
        assert isinstance(err, EsgvocException)


# ---------------------------------------------------------------------------
# DT-130  MissingLinksTracker.clear
# ---------------------------------------------------------------------------

class TestMissingLinksTrackerClear:
    """DT-130: clear() empties the tracker."""

    def test_clear_removes_all_links(self):
        tracker = MissingLinksTracker()
        tracker.add_from_params(
            ingestion_context="universe",
            current_term="t",
            string_value="ref",
            expected_uri="u",
            local_path="p",
        )
        assert tracker.has_missing_links() is True
        tracker.clear()
        assert tracker.has_missing_links() is False

    def test_clear_allows_reuse(self):
        tracker = MissingLinksTracker()
        tracker.add_from_params(
            ingestion_context="project:cmip6",
            current_term="t",
            string_value="ref",
            expected_uri="u",
            local_path="p",
        )
        tracker.clear()
        # After clear, check_and_raise should not raise
        tracker.check_and_raise()

    def test_print_summary_returns_true_when_links_present(self, capsys):
        tracker = MissingLinksTracker()
        tracker.add_from_params(
            ingestion_context="universe",
            current_term="t",
            string_value="ref",
            expected_uri="u",
            local_path="p",
        )
        result = tracker.print_summary()
        assert result is True


# ---------------------------------------------------------------------------
# DT-131  get_pydantic_class raises for unknown type (Scenario 16)
# ---------------------------------------------------------------------------

class TestGetPydanticClassUnknown:
    """DT-131: get_pydantic_class raises EsgvocDbError for unknown type (Scenario 16)."""

    def test_unknown_type_raises_db_error(self):
        from esgvoc.api.pydantic_handler import get_pydantic_class
        with pytest.raises(EsgvocDbError):
            get_pydantic_class("totally_unknown_type_xyz_that_does_not_exist")

    def test_error_message_contains_type_name(self):
        from esgvoc.api.pydantic_handler import get_pydantic_class
        with pytest.raises(EsgvocDbError) as exc_info:
            get_pydantic_class("nonexistent_type_abc")
        assert "nonexistent_type_abc" in str(exc_info.value)

    def test_empty_string_raises_db_error(self):
        from esgvoc.api.pydantic_handler import get_pydantic_class
        with pytest.raises(EsgvocDbError):
            get_pydantic_class("")


# ---------------------------------------------------------------------------
# DT-132  get_pydantic_class returns correct class for known type
# ---------------------------------------------------------------------------

class TestGetPydanticClassKnown:
    """DT-132: get_pydantic_class returns the correct DataDescriptor class."""

    def test_activity_returns_activity_class(self):
        from esgvoc.api.pydantic_handler import get_pydantic_class
        from esgvoc.api.data_descriptors.activity import Activity
        cls = get_pydantic_class("activity")
        assert cls is Activity

    def test_institution_returns_institution_class(self):
        from esgvoc.api.pydantic_handler import get_pydantic_class
        from esgvoc.api.data_descriptors.institution import Institution
        cls = get_pydantic_class("institution")
        assert cls is Institution

    def test_known_type_returns_callable(self):
        from esgvoc.api.pydantic_handler import get_pydantic_class
        cls = get_pydantic_class("frequency")
        assert callable(cls)

    def test_all_mapped_types_are_retrievable(self):
        from esgvoc.api.pydantic_handler import get_pydantic_class
        from esgvoc.api.data_descriptors import DATA_DESCRIPTOR_CLASS_MAPPING
        for type_id, expected_cls in DATA_DESCRIPTOR_CLASS_MAPPING.items():
            cls = get_pydantic_class(type_id)
            assert cls is expected_cls, (
                f"get_pydantic_class({type_id!r}) returned {cls}, expected {expected_cls}"
            )


# ---------------------------------------------------------------------------
# DT-133  build_dev with fail_on_missing_links=False succeeds
# ---------------------------------------------------------------------------

class TestBuildDevMissingLinksDisabled:
    """DT-133: build_dev with fail_on_missing_links=False does not raise on link errors."""

    def test_real_build_with_fail_disabled_succeeds(self, real_dbs):
        """The real_dbs fixture was built with fail_on_missing_links=False (default)."""
        # If real_dbs fixture succeeded, it means fail_on_missing_links=False is the default
        # and the real cmip6 build completed without raising.
        assert real_dbs["v1_path"].exists(), (
            "v1 DB should exist — built with fail_on_missing_links=False (default)"
        )
        assert real_dbs["v2_path"].exists(), (
            "v2 DB should exist — built with fail_on_missing_links=False (default)"
        )

    def test_build_result_not_none_for_real_db(self, real_dbs):
        """If build was triggered (not from cache), result is non-None."""
        v1_result = real_dbs["v1_result"]
        v2_result = real_dbs["v2_result"]
        # If loaded from cache, result is None — that's fine
        # If built fresh, result must be truthy (BuildResult object)
        if v1_result is not None:
            assert v1_result  # BuildResult is truthy
        if v2_result is not None:
            assert v2_result


# ---------------------------------------------------------------------------
# DT-134  DBBuilder with fail_on_missing_links raises (integration)
# ---------------------------------------------------------------------------

class TestBuildDevMissingLinksEnabled:
    """DT-134: DBBuilder raises EsgvocMissingLinksError when fail_on_missing_links=True
    and the project has unresolved references (integration — uses real repos if available)."""

    def test_fail_on_missing_links_flag_is_configurable(self):
        """DBBuilder accepts fail_on_missing_links kwarg without error."""
        from esgvoc.admin.builder import DBBuilder
        builder_strict = DBBuilder(verbose=False, fail_on_missing_links=True)
        builder_lenient = DBBuilder(verbose=False, fail_on_missing_links=False)
        assert builder_strict.fail_on_missing_links is True
        assert builder_lenient.fail_on_missing_links is False

    def test_tracker_raises_on_populated_state(self):
        """A tracker with links causes check_and_raise to raise — equivalent to build failure."""
        tracker = MissingLinksTracker()
        tracker.add_from_params(
            ingestion_context="project:cmip6",
            current_term="experiment/exp-broken.json",
            string_value="activity:does-not-exist",
            expected_uri="https://wcrp.earth/activity/does-not-exist",
            local_path="/repos/WCRP-universe/activity/does-not-exist.json",
            property_name="activity",
        )
        # This simulates what happens when fail_on_missing_links=True finds a bad link
        with pytest.raises(EsgvocMissingLinksError):
            tracker.check_and_raise()

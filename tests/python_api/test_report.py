"""
Unit tests for esgvoc.api.report — no DB required.
"""

from __future__ import annotations

from esgvoc.api.report import ProjectTermError, UniverseTermError, ValidationReport
from esgvoc.core.db.models.mixins import TermKind

_TERM_SPECS = {"id": "some-term", "type": "activity"}


class TestUniverseTermError:
    def _make(self, value="bad-value"):
        return UniverseTermError(
            value=value,
            term=_TERM_SPECS,
            term_kind=TermKind.PLAIN,
            data_descriptor_id="activity",
        )

    def test_str_contains_term_id(self):
        err = self._make()
        assert "some-term" in str(err)

    def test_str_contains_data_descriptor(self):
        err = self._make()
        assert "activity" in str(err)

    def test_str_contains_value(self):
        err = self._make(value="my-bad-value")
        assert "my-bad-value" in str(err)

    def test_repr_equals_str(self):
        err = self._make()
        assert repr(err) == str(err)

    def test_accept_calls_visitor(self):
        err = self._make()
        called = []

        class V:
            def visit_universe_term_error(self, e):
                called.append(e)
                return "ok"

        result = err.accept(V())
        assert result == "ok"
        assert called[0] is err


class TestProjectTermError:
    def _make(self, value="bad-value"):
        return ProjectTermError(
            value=value,
            term=_TERM_SPECS,
            term_kind=TermKind.PLAIN,
            collection_id="activity",
        )

    def test_str_contains_term_id(self):
        err = self._make()
        assert "some-term" in str(err)

    def test_str_contains_collection_id(self):
        err = self._make()
        assert "activity" in str(err)

    def test_str_contains_value(self):
        err = self._make(value="my-bad-value")
        assert "my-bad-value" in str(err)

    def test_repr_equals_str(self):
        err = self._make()
        assert repr(err) == str(err)

    def test_accept_calls_visitor(self):
        err = self._make()
        called = []

        class V:
            def visit_project_term_error(self, e):
                called.append(e)
                return "ok"

        result = err.accept(V())
        assert result == "ok"
        assert called[0] is err


class TestValidationReport:
    def _make_empty(self):
        return ValidationReport(expression="test-value", errors=[])

    def _make_with_errors(self):
        err = ProjectTermError(
            value="bad",
            term=_TERM_SPECS,
            term_kind=TermKind.PLAIN,
            collection_id="activity",
        )
        return ValidationReport(expression="bad", errors=[err])

    def test_nb_errors_zero_when_no_errors(self):
        r = self._make_empty()
        assert r.nb_errors == 0

    def test_nb_errors_nonzero_with_errors(self):
        r = self._make_with_errors()
        assert r.nb_errors == 1

    def test_validated_true_when_no_errors(self):
        r = self._make_empty()
        assert r.validated is True

    def test_validated_false_when_errors(self):
        r = self._make_with_errors()
        assert r.validated is False

    def test_len_equals_nb_errors(self):
        r = self._make_with_errors()
        assert len(r) == r.nb_errors

    def test_bool_true_when_valid(self):
        r = self._make_empty()
        assert bool(r) is True

    def test_bool_false_when_invalid(self):
        r = self._make_with_errors()
        assert bool(r) is False

    def test_str_contains_expression(self):
        r = self._make_empty()
        assert "test-value" in str(r)

    def test_repr_equals_str(self):
        r = self._make_empty()
        assert repr(r) == str(r)

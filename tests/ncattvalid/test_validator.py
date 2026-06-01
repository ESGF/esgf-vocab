"""
Tests for GAValidator.

Unit tests use injected specs + mocked API calls — no database required.
Integration tests (marked ``needs_db``) exercise the full stack.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from esgvoc.api.project_specs import AttributeProperty
from esgvoc.api.search import MatchingTerm
from esgvoc.apps.ncattvalid.exceptions import InvalidNcdumpError
from esgvoc.apps.ncattvalid.validator import AttributeResult, GAReport, GAValidator

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def specs_basic():
    """Two required CV-backed attributes + one optional free-text."""
    return [
        AttributeProperty(
            source_collection="activity_id",
            is_required=True,
            attr_field_value_type="string",
        ),
        AttributeProperty(
            source_collection="experiment_id",
            is_required=True,
            attr_field_value_type="string",
        ),
        AttributeProperty(
            source_collection=None,
            is_required=False,
            attr_field_value_type="string",
            attr_field_name="free_text",
        ),
    ]


@pytest.fixture
def valid_match():
    """Return value for mocked valid_term_in_collection when a value is valid."""
    return [MatchingTerm(project_id="p", collection_id="activity_id", term_id="CMIP")]


def _make_validator(specs):
    """Build a GAValidator with injected specs (no DB required)."""
    return GAValidator("testproject", specs=specs)


# ---------------------------------------------------------------------------
# GAReport
# ---------------------------------------------------------------------------

class TestGAReport:

    def test_is_valid_when_no_errors_no_missing(self):
        report = GAReport(
            project_id="p",
            filename=None,
            results=[AttributeResult(name="a", is_valid=True, message="valid")],
            missing=[],
            extra=[],
        )
        assert report.is_valid

    def test_is_invalid_when_error(self):
        report = GAReport(
            project_id="p",
            filename=None,
            results=[AttributeResult(name="a", is_valid=False, message="bad")],
            missing=[],
            extra=[],
        )
        assert not report.is_valid

    def test_is_invalid_when_missing(self):
        report = GAReport(
            project_id="p",
            filename=None,
            results=[],
            missing=["required_attr"],
            extra=[],
        )
        assert not report.is_valid

    def test_errors_property_filters_failed(self):
        report = GAReport(
            project_id="p",
            filename=None,
            results=[
                AttributeResult(name="ok", is_valid=True, message="valid"),
                AttributeResult(name="bad", is_valid=False, message="wrong"),
            ],
            missing=[],
            extra=[],
        )
        assert len(report.errors) == 1
        assert report.errors[0].name == "bad"

    def test_str_contains_status(self):
        report = GAReport(project_id="p", filename="f.nc", results=[], missing=[], extra=[])
        s = str(report)
        assert "VALID" in s
        assert "p" in s
        assert "f.nc" in s

    def test_str_invalid_shows_errors(self):
        report = GAReport(
            project_id="p",
            filename=None,
            results=[AttributeResult(name="x", is_valid=False, message="not found", value="bad")],
            missing=["y"],
            extra=["z"],
        )
        s = str(report)
        assert "INVALID" in s
        assert "x" in s
        assert "y" in s
        assert "z" in s


# ---------------------------------------------------------------------------
# GAValidator — loading
# ---------------------------------------------------------------------------

class TestGAValidatorLoading:

    def test_raises_if_project_not_found(self):
        with patch("esgvoc.apps.ncattvalid.validator.projects.get_project", return_value=None):
            with pytest.raises(Exception, match="testproject"):
                GAValidator("testproject")

    def test_raises_if_no_attr_specs(self):
        mock_proj = MagicMock()
        mock_proj.attr_specs = None
        with patch("esgvoc.apps.ncattvalid.validator.projects.get_project", return_value=mock_proj):
            with pytest.raises(ValueError, match="no attribute specifications"):
                GAValidator("testproject")

    def test_injected_specs_skips_db(self, specs_basic):
        # No patch needed — DB is never called when specs are injected
        v = _make_validator(specs_basic)
        assert len(v._specs) == len(specs_basic)


# ---------------------------------------------------------------------------
# GAValidator — missing / extra detection
# ---------------------------------------------------------------------------

class TestMissingAndExtra:

    def test_missing_required_attributes(self, specs_basic):
        v = _make_validator(specs_basic)
        report = v.validate({})
        assert "activity_id" in report.missing
        assert "experiment_id" in report.missing

    def test_optional_not_in_missing(self, specs_basic):
        v = _make_validator(specs_basic)
        with patch("esgvoc.apps.ncattvalid.validator.projects.valid_term_in_collection", return_value=[MagicMock()]):
            report = v.validate({"activity_id": "CMIP", "experiment_id": "historical"})
        assert "free_text" not in report.missing

    def test_extra_attribute_recorded(self, specs_basic, valid_match):
        v = _make_validator(specs_basic)
        with patch("esgvoc.apps.ncattvalid.validator.projects.valid_term_in_collection", return_value=valid_match):
            report = v.validate({
                "activity_id": "CMIP",
                "experiment_id": "historical",
                "unknown_attr": "whatever",
            })
        assert "unknown_attr" in report.extra

    def test_extra_not_in_results(self, specs_basic, valid_match):
        v = _make_validator(specs_basic)
        with patch("esgvoc.apps.ncattvalid.validator.projects.valid_term_in_collection", return_value=valid_match):
            report = v.validate({
                "activity_id": "CMIP",
                "experiment_id": "historical",
                "unknown_attr": "whatever",
            })
        result_names = {r.name for r in report.results}
        assert "unknown_attr" not in result_names


# ---------------------------------------------------------------------------
# GAValidator — attribute validation
# ---------------------------------------------------------------------------

class TestAttributeValidation:

    def test_valid_value_produces_valid_result(self, specs_basic, valid_match):
        v = _make_validator(specs_basic)
        with patch("esgvoc.apps.ncattvalid.validator.projects.valid_term_in_collection", return_value=valid_match):
            report = v.validate({"activity_id": "CMIP", "experiment_id": "historical"})
        for r in report.results:
            assert r.is_valid, f"{r.name}: {r.message}"

    def test_invalid_value_produces_error(self, specs_basic):
        v = _make_validator(specs_basic)
        with patch("esgvoc.apps.ncattvalid.validator.projects.valid_term_in_collection", return_value=[]):
            report = v.validate({"activity_id": "NOPE", "experiment_id": "historical"})
        errors_by_name = {r.name: r for r in report.errors}
        assert "activity_id" in errors_by_name
        assert "NOPE" in errors_by_name["activity_id"].message

    def test_collection_not_found_produces_error(self, specs_basic):
        from esgvoc.core.exceptions import EsgvocNotFoundError

        v = _make_validator(specs_basic)
        with patch(
            "esgvoc.apps.ncattvalid.validator.projects.valid_term_in_collection",
            side_effect=EsgvocNotFoundError("collection 'activity_id' not found"),
        ):
            report = v.validate({"activity_id": "CMIP", "experiment_id": "historical"})
        errors_by_name = {r.name: r for r in report.errors}
        assert "activity_id" in errors_by_name
        assert "not found" in errors_by_name["activity_id"].message

    def test_free_text_attribute_is_valid(self, specs_basic):
        v = _make_validator(specs_basic)

        report = v.validate({
            "activity_id": "CMIP",
            "experiment_id": "historical",
            "free_text": "any text",
        })

        free_results = [r for r in report.results if r.name == "free_text"]

        assert free_results[0].is_valid
        assert "free-text" in free_results[0].message

    def test_na_value_is_accepted(self):
        specs = [
            AttributeProperty(
                source_collection="sub_experiment_id",
                is_required=False,
                attr_field_value_type="string",
                attr_field_name="sub_experiment",
                attr_field_na_value="none",
            )
        ]
        v = _make_validator(specs)
        # No API call should be made — NA value check short-circuits
        with patch(
            "esgvoc.apps.ncattvalid.validator.projects.valid_term_in_collection"
        ) as mock_valid:
            report = v.validate({"sub_experiment": "none"})
        mock_valid.assert_not_called()
        assert report.results[0].is_valid

    def test_integer_value_converted_to_string_for_cv(self, specs_basic):
        """Numeric values from ncdump must be coerced to str for CV lookup."""
        v = _make_validator(specs_basic)
        captured_args = []

        def capture(*args, **kwargs):
            captured_args.append(args)
            return [MagicMock()]

        with patch("esgvoc.apps.ncattvalid.validator.projects.valid_term_in_collection", side_effect=capture):
            v.validate({"activity_id": "CMIP", "experiment_id": "historical"})

        # The value passed to valid_term_in_collection must be a str
        for call_args in captured_args:
            assert isinstance(call_args[0], str)

    def test_validate_one_unknown_attribute(self, specs_basic):
        v = _make_validator(specs_basic)

        result = v.validate_one("unknown", "value")

        assert not result.is_valid
        assert "Unknown NetCDF attribute" in result.message

    def test_validate_one_free_text_attribute(self):
        specs = [
            AttributeProperty(
                source_collection=None,
                is_required=False,
                attr_field_name="comment",
                attr_field_value_type="string",
            )
        ]

        v = _make_validator(specs)

        result = v.validate_one(
            "comment",
            "hello world",
        )

        assert result.is_valid


# ---------------------------------------------------------------------------
# GAValidator — source_collection_key
# ---------------------------------------------------------------------------

class TestSpecificKey:

    @pytest.fixture
    def specific_key_specs(self):
        return [
            AttributeProperty(
                source_collection="experiment_id",
                is_required=False,
                attr_field_value_type="string",
                attr_field_name="experiment",
                source_collection_key="description",
            )
        ]

    def test_specific_key_valid(self, specific_key_specs):
        v = _make_validator(specific_key_specs)
        with patch(
            "esgvoc.apps.ncattvalid.validator.projects.get_terms_in_collection_by_key_value",
            return_value=[MagicMock()],
        ):
            report = v.validate({"experiment": "all-forcing simulation of the recent past"})
        assert not report.errors

    def test_specific_key_invalid(self, specific_key_specs):
        v = _make_validator(specific_key_specs)
        with patch(
            "esgvoc.apps.ncattvalid.validator.projects.get_terms_in_collection_by_key_value",
            return_value=[],
        ):
            report = v.validate({"experiment": "nonsense description"})
        assert len(report.errors) == 1
        assert "description" in report.errors[0].message
        assert "experiment_id" in report.errors[0].message

    def test_specific_key_calls_correct_api(self, specific_key_specs):
        v = _make_validator(specific_key_specs)
        with patch(
            "esgvoc.apps.ncattvalid.validator.projects.get_terms_in_collection_by_key_value",
            return_value=[MagicMock()],
        ) as mock_api:
            v.validate({"experiment": "some description"})
        mock_api.assert_called_once_with(
            "testproject", "experiment_id", "description", "some description"
        )


# ---------------------------------------------------------------------------
# GAValidator — validate_ncdump
# ---------------------------------------------------------------------------

class TestValidateNcdump:

    _NCDUMP = """\
netcdf myfile {
// global attributes:
        :activity_id = "CMIP" ;
        :experiment_id = "historical" ;
}"""

    def test_filename_extracted_from_header(self, specs_basic, valid_match):
        v = _make_validator(specs_basic)
        with patch("esgvoc.apps.ncattvalid.validator.projects.valid_term_in_collection", return_value=valid_match):
            report = v.validate_ncdump(self._NCDUMP)
        assert report.filename == "myfile"

    def test_explicit_filename_overrides_header(self, specs_basic, valid_match):
        v = _make_validator(specs_basic)
        with patch("esgvoc.apps.ncattvalid.validator.projects.valid_term_in_collection", return_value=valid_match):
            report = v.validate_ncdump(self._NCDUMP, filename="explicit.nc")
        assert report.filename == "explicit.nc"

    def test_attributes_are_parsed_and_validated(self, specs_basic, valid_match):
        v = _make_validator(specs_basic)
        with patch("esgvoc.apps.ncattvalid.validator.projects.valid_term_in_collection", return_value=valid_match):
            report = v.validate_ncdump(self._NCDUMP)
        validated_names = {r.name for r in report.results}
        assert "activity_id" in validated_names
        assert "experiment_id" in validated_names

    def test_validate_ncdump_invalid_input_raises(self, specs_basic):
        v = _make_validator(specs_basic)

        with pytest.raises(InvalidNcdumpError):
            v.validate_ncdump("not an ncdump")


# ---------------------------------------------------------------------------
# GAValidator — integration (needs real DB)
# ---------------------------------------------------------------------------

@pytest.mark.needs_db
class TestGAValidatorIntegration:

    def test_instantiation_for_project_with_specs(self, project_with_attr_specs):
        pid, _ = project_with_attr_specs
        validator = GAValidator(pid)
        assert len(validator._specs) > 0

    def test_validate_empty_dict_returns_report(self, project_with_attr_specs):
        pid, _ = project_with_attr_specs
        validator = GAValidator(pid)
        report = validator.validate({})
        assert isinstance(report, GAReport)
        assert report.project_id == pid
        # All required attributes should be missing
        assert len(report.missing) > 0

    def test_validate_ncdump_with_empty_header(self, project_with_attr_specs):
        pid, _ = project_with_attr_specs
        validator = GAValidator(pid)
        report = validator.validate_ncdump("netcdf empty {\n// global attributes:\n}")
        assert isinstance(report, GAReport)
        assert not report.is_valid   # required attributes will be missing

    def test_str_report_is_readable(self, project_with_attr_specs):
        pid, _ = project_with_attr_specs
        validator = GAValidator(pid)
        report = validator.validate({})
        summary = str(report)
        assert pid in summary
        assert "VALID" in summary or "INVALID" in summary

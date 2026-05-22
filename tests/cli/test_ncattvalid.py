"""Tests for `esgvoc ncattvalid` command."""

from pathlib import Path
from unittest.mock import patch

from esgvoc.apps.ncattvalid.validator import AttributeResult, GAReport
from esgvoc.cli.ncattvalid import app

from .conftest import runner


class TestNcAttValidCommand:
    @patch("esgvoc.cli.ncattvalid.GAValidator")
    def test_validate_single_attribute_valid(self, mock_validator):
        validator = mock_validator.return_value

        validator.validate_one.return_value = AttributeResult(
            name="activity_id",
            is_valid=True,
            message="valid",
            value="CMIP",
        )

        result = runner.invoke(
            app,
            ["cmip6", "activity_id", "CMIP"],
        )
        assert result.exit_code == 0
        assert "activity_id" in result.output
        assert "CMIP" in result.output
        assert "✅" in result.output

    @patch("esgvoc.cli.ncattvalid.GAValidator")
    def test_validate_single_attribute_invalid(self, mock_validator):
        validator = mock_validator.return_value

        validator.validate_one.return_value = AttributeResult(
            name="activity_id",
            is_valid=False,
            message="invalid value",
            value="WRONG",
        )

        result = runner.invoke(
            app,
            ["cmip6", "activity_id", "WRONG"],
        )

        assert result.exit_code == 1
        assert "activity_id" in result.output
        assert "invalid value" in result.output
        assert "❌" in result.output

    @patch("esgvoc.cli.ncattvalid.GAValidator")
    def test_validate_missing_attribute_value(self, mock_validator):
        result = runner.invoke(
            app,
            ["cmip6", "activity_id"],
        )

        assert result.exit_code == 1
        assert "Error: expected either:\n  • ATTRIBUTE_NAME ATTRIBUTE_VALUE\n  • --file HEADER_FILE\n  • stdin via pipe\n" in result.output

    @patch("esgvoc.cli.ncattvalid.GAValidator")
    def test_validate_ncdump_from_file_valid(self, mock_validator, tmp_path):
        validator = mock_validator.return_value

        validator.validate_ncdump.return_value = GAReport(
            project_id="cmip6",
            filename="test.nc",
            results=[],
            missing=[],
            extra=[],
        )

        header_file = tmp_path / "header.txt"
        header_file.write_text(
"""
netcdf test.nc {
dimensions:
    time = UNLIMITED ;

// global attributes:
    :activity_id = "CMIP" ;
}
"""
        )

        result = runner.invoke(
            app,
            [
                "cmip6",
                "--file",
                str(header_file),
            ],
        )

        assert result.exit_code == 0
        assert "Validation successful" in result.output

    @patch("esgvoc.cli.ncattvalid.GAValidator")
    def test_validate_ncdump_file_not_found(self, mock_validator):
        result = runner.invoke(
            app,
            [
                "cmip6",
                "--file",
                "/does/not/exist.txt",
            ],
        )

        assert result.exit_code == 1
        assert "File not found" in result.output

    @patch("esgvoc.cli.ncattvalid.GAValidator")
    def test_validate_ncdump_from_stdin(self, mock_validator):
        validator = mock_validator.return_value

        validator.validate_ncdump.return_value = GAReport(
            project_id="cmip6",
            filename="test.nc",
            results=[],
            missing=[],
            extra=[],
        )

        result = runner.invoke(
            app,
            ["cmip6"],
            input="""
netcdf test.nc {
dimensions:
    time = UNLIMITED ;

// global attributes:
    :activity_id = "CMIP" ;
}
""",
        )

        assert result.exit_code == 0
        assert "Validation successful" in result.output

    @patch("esgvoc.cli.ncattvalid.GAValidator")
    def test_validate_ncdump_no_stdin_input(self, mock_validator):
        result = runner.invoke(
            app,
            ["cmip6"],
            input="",
        )

        assert result.exit_code == 1
        assert "No ncdump input received from stdin" in result.output

    @patch("esgvoc.cli.ncattvalid.GAValidator")
    def test_validate_ncdump_verbose(self, mock_validator, tmp_path):
        validator = mock_validator.return_value

        validator.validate_ncdump.return_value = GAReport(
            project_id="cmip6",
            filename="test.nc",
            results=[
                AttributeResult(
                    name="activity_id",
                    is_valid=True,
                    message="valid",
                    value="CMIP",
                ),
            ],
            missing=[],
            extra=[],
        )

        header_file = tmp_path / "header.txt"
        header_file.write_text("dummy")

        result = runner.invoke(
            app,
            [
                "cmip6",
                "--file",
                str(header_file),
                "--verbose",
            ],
        )

        assert result.exit_code == 0
        assert "Valid attributes" in result.output
        assert "activity_id" in result.output

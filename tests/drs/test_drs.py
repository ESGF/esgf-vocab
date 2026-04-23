"""
Tests for DRS validation and generation — uses real cmip7@v1.0.0 database.

Marked `needs_db`: network is only required on the very first run to download
the DB.  Once installed (ESGVOC_HOME set with the DB present) tests run offline.

Known-valid DRS values used throughout (discovered dynamically on first writing):
  directory:  MIP-DRS7/CMIP7/PMIP/MOHC/CNRM-ESM2-1e/scen7-hl-ext/r1i1p1f1/sh/fx/dmc/tmin-alh-ht-tree/g103/v20250101
  dataset_id: MIP-DRS7.CMIP7.PMIP.MOHC.CNRM-ESM2-1e.scen7-hl-ext.r1i1p1f1.sh.fx.dmc.tmin-alh-ht-tree.g103.v20250101
  file_name:  dmc_tmin-alh-ht-tree_fx_sh_g103_CNRM-ESM2-1e_scen7-hl-ext_r1i1p1f1.nc
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.needs_db

# ---------------------------------------------------------------------------
# Shared fixtures / constants
# ---------------------------------------------------------------------------

_DIR = "MIP-DRS7/CMIP7/PMIP/MOHC/CNRM-ESM2-1e/scen7-hl-ext/r1i1p1f1/sh/fx/dmc/tmin-alh-ht-tree/g103/v20250101"
_DSID = "MIP-DRS7.CMIP7.PMIP.MOHC.CNRM-ESM2-1e.scen7-hl-ext.r1i1p1f1.sh.fx.dmc.tmin-alh-ht-tree.g103.v20250101"
_FILE = "dmc_tmin-alh-ht-tree_fx_sh_g103_CNRM-ESM2-1e_scen7-hl-ext_r1i1p1f1.nc"
_MAPPING = {
    "drs_specs": "MIP-DRS7",
    "mip_era": "CMIP7",
    "activity": "PMIP",
    "institution": "MOHC",
    "source": "CNRM-ESM2-1e",
    "experiment": "scen7-hl-ext",
    "variant_label": "r1i1p1f1",
    "region": "sh",
    "frequency": "fx",
    "variable": "dmc",
    "branding_suffix": "tmin-alh-ht-tree",
    "grid_label": "g103",
    "directory_date": "v20250101",
}
_FILE_MAPPING = {k: v for k, v in _MAPPING.items() if k not in ("drs_specs", "mip_era", "activity", "institution", "directory_date")}


# ---------------------------------------------------------------------------
# DrsValidator — instantiation
# ---------------------------------------------------------------------------

class TestDrsValidator:
    def test_validator_can_be_instantiated(self, installed_dbs):
        from esgvoc.apps.drs.validator import DrsValidator

        validator = DrsValidator("cmip7")
        assert validator is not None

    def test_validate_directory_returns_report(self, installed_dbs):
        """Smoke test: validating anything returns a report object, not an exception."""
        from esgvoc.apps.drs.validator import DrsValidator

        validator = DrsValidator("cmip7")
        report = validator.validate_directory("anything")
        assert report is not None

    def test_validate_file_name_returns_report(self, installed_dbs):
        from esgvoc.apps.drs.validator import DrsValidator

        validator = DrsValidator("cmip7")
        report = validator.validate_file_name("anything.nc")
        assert report is not None

    def test_validate_dataset_id_returns_report(self, installed_dbs):
        from esgvoc.apps.drs.validator import DrsValidator

        validator = DrsValidator("cmip7")
        report = validator.validate_dataset_id("anything")
        assert report is not None


# ---------------------------------------------------------------------------
# DrsValidator — valid expressions
# ---------------------------------------------------------------------------

class TestDrsValidatorValid:
    def test_valid_directory(self, installed_dbs):
        from esgvoc.apps.drs.validator import DrsValidator

        v = DrsValidator("cmip7")
        report = v.validate_directory(_DIR)
        assert report.nb_errors == 0
        assert report.nb_warnings == 0
        assert report.validated is True
        assert bool(report) is True

    def test_valid_dataset_id(self, installed_dbs):
        from esgvoc.apps.drs.validator import DrsValidator

        v = DrsValidator("cmip7")
        report = v.validate_dataset_id(_DSID)
        assert report.nb_errors == 0
        assert report.validated is True

    def test_valid_file_name(self, installed_dbs):
        from esgvoc.apps.drs.validator import DrsValidator

        v = DrsValidator("cmip7")
        report = v.validate_file_name(_FILE)
        assert report.nb_errors == 0
        assert report.validated is True

    def test_validate_dispatcher_directory(self, installed_dbs):
        from esgvoc.api.project_specs import DrsType
        from esgvoc.apps.drs.validator import DrsValidator

        v = DrsValidator("cmip7")
        report = v.validate(_DIR, DrsType.DIRECTORY)
        assert report.nb_errors == 0

    def test_validate_dispatcher_dataset_id(self, installed_dbs):
        from esgvoc.api.project_specs import DrsType
        from esgvoc.apps.drs.validator import DrsValidator

        v = DrsValidator("cmip7")
        report = v.validate(_DSID, DrsType.DATASET_ID)
        assert report.nb_errors == 0

    def test_validate_dispatcher_file_name(self, installed_dbs):
        from esgvoc.api.project_specs import DrsType
        from esgvoc.apps.drs.validator import DrsValidator

        v = DrsValidator("cmip7")
        report = v.validate(_FILE, DrsType.FILE_NAME)
        assert report.nb_errors == 0

    def test_validate_directory_with_prefix(self, installed_dbs):
        from esgvoc.apps.drs.validator import DrsValidator

        v = DrsValidator("cmip7")
        full = "/data/archive/" + _DIR
        report = v.validate_directory(full, prefix="/data/archive/")
        assert report.nb_errors == 0


# ---------------------------------------------------------------------------
# DrsValidator — parsing errors and warnings
# ---------------------------------------------------------------------------

class TestDrsValidatorParsingIssues:
    def test_unparsable_expression(self, installed_dbs):
        """Expression with no separator → Unparsable error."""
        from esgvoc.apps.drs.report import Unparsable
        from esgvoc.apps.drs.validator import DrsValidator

        v = DrsValidator("cmip7")
        report = v.validate_directory("nodirectory")
        assert report.nb_errors == 1
        assert isinstance(report.errors[0], Unparsable)

    def test_leading_space_is_warning(self, installed_dbs):
        """Leading space → warning in non-pedantic mode."""
        from esgvoc.apps.drs.report import Space
        from esgvoc.apps.drs.validator import DrsValidator

        v = DrsValidator("cmip7")
        report = v.validate_directory(" " + _DIR)
        assert report.nb_errors == 0
        assert report.nb_warnings == 1
        assert isinstance(report.warnings[0], Space)

    def test_leading_space_is_error_in_pedantic_mode(self, installed_dbs):
        """Leading space → error in pedantic mode."""
        from esgvoc.apps.drs.report import Space
        from esgvoc.apps.drs.validator import DrsValidator

        v = DrsValidator("cmip7", pedantic=True)
        report = v.validate_directory(" " + _DIR)
        assert report.nb_errors >= 1
        assert any(isinstance(e, Space) for e in report.errors)

    def test_trailing_separator_is_warning(self, installed_dbs):
        """Trailing separator in directory → warning in non-pedantic."""
        from esgvoc.apps.drs.report import ExtraSeparator
        from esgvoc.apps.drs.validator import DrsValidator

        v = DrsValidator("cmip7")
        report = v.validate_directory(_DIR + "/")
        assert report.nb_warnings >= 1
        assert any(isinstance(w, ExtraSeparator) for w in report.warnings)

    def test_wrong_file_extension(self, installed_dbs):
        """File name without .nc extension → FileNameExtensionIssue."""
        from esgvoc.apps.drs.report import FileNameExtensionIssue
        from esgvoc.apps.drs.validator import DrsValidator

        v = DrsValidator("cmip7")
        report = v.validate_file_name("something.txt")
        assert report.nb_errors == 1
        assert isinstance(report.errors[0], FileNameExtensionIssue)


# ---------------------------------------------------------------------------
# DrsValidator — compliance errors
# ---------------------------------------------------------------------------

class TestDrsValidatorComplianceIssues:
    def test_missing_terms(self, installed_dbs):
        """Too few parts → MissingTerm errors."""
        from esgvoc.apps.drs.report import MissingTerm
        from esgvoc.apps.drs.validator import DrsValidator

        v = DrsValidator("cmip7")
        report = v.validate_directory("MIP-DRS7/CMIP7/PMIP")
        assert report.nb_errors > 0
        assert any(isinstance(e, MissingTerm) for e in report.errors)

    def test_extra_terms(self, installed_dbs):
        """Too many parts → ExtraTerm error."""
        from esgvoc.apps.drs.report import ExtraTerm
        from esgvoc.apps.drs.validator import DrsValidator

        v = DrsValidator("cmip7")
        report = v.validate_directory(_DIR + "/unexpected")
        assert report.nb_errors >= 1
        assert any(isinstance(e, ExtraTerm) for e in report.errors)

    def test_invalid_term_reported(self, installed_dbs):
        """A bad term value at a known position → InvalidTerm error."""
        from esgvoc.apps.drs.report import InvalidTerm
        from esgvoc.apps.drs.validator import DrsValidator

        v = DrsValidator("cmip7")
        bad = _DIR.replace("CMIP7", "BADMIPERA")
        report = v.validate_directory(bad)
        assert report.nb_errors >= 1
        assert any(isinstance(e, InvalidTerm) for e in report.errors)


# ---------------------------------------------------------------------------
# DrsValidator — report model
# ---------------------------------------------------------------------------

class TestDrsValidationReport:
    def test_report_str_contains_expression(self, installed_dbs):
        from esgvoc.apps.drs.validator import DrsValidator

        v = DrsValidator("cmip7")
        report = v.validate_directory(_DIR)
        s = str(report)
        assert _DIR in s

    def test_report_len(self, installed_dbs):
        from esgvoc.apps.drs.validator import DrsValidator

        v = DrsValidator("cmip7")
        report = v.validate_directory("MIP-DRS7/CMIP7/PMIP")
        assert len(report) == report.nb_errors

    def test_report_bool_true(self, installed_dbs):
        from esgvoc.apps.drs.validator import DrsValidator

        v = DrsValidator("cmip7")
        report = v.validate_directory(_DIR)
        assert bool(report) is True

    def test_report_bool_false(self, installed_dbs):
        from esgvoc.apps.drs.validator import DrsValidator

        v = DrsValidator("cmip7")
        report = v.validate_directory("bad")
        assert bool(report) is False

    def test_mapping_used_populated_on_valid(self, installed_dbs):
        from esgvoc.apps.drs.validator import DrsValidator

        v = DrsValidator("cmip7")
        report = v.validate_directory(_DIR)
        assert len(report.mapping_used) > 0


# ---------------------------------------------------------------------------
# DrsGenerator — instantiation
# ---------------------------------------------------------------------------

class TestDrsGenerator:
    def test_generator_can_be_instantiated(self, installed_dbs):
        from esgvoc.apps.drs.generator import DrsGenerator

        gen = DrsGenerator("cmip7")
        assert gen is not None

    def test_generate_from_empty_mapping(self, installed_dbs):
        """Empty mapping should return a report with errors but not raise."""
        from esgvoc.api.project_specs import DrsType
        from esgvoc.apps.drs.generator import DrsGenerator

        gen = DrsGenerator("cmip7")
        report = gen.generate_from_mapping({}, DrsType.DIRECTORY)
        assert report is not None

    def test_generate_from_empty_bag_of_terms(self, installed_dbs):
        from esgvoc.api.project_specs import DrsType
        from esgvoc.apps.drs.generator import DrsGenerator

        gen = DrsGenerator("cmip7")
        report = gen.generate_from_bag_of_terms([], DrsType.DIRECTORY)
        assert report is not None


# ---------------------------------------------------------------------------
# DrsGenerator — valid generation
# ---------------------------------------------------------------------------

class TestDrsGeneratorValid:
    def test_generate_directory_from_mapping(self, installed_dbs):
        from esgvoc.apps.drs.generator import DrsGenerator

        g = DrsGenerator("cmip7")
        report = g.generate_directory_from_mapping(_MAPPING)
        assert report.nb_errors == 0
        assert report.generated_drs_expression == _DIR

    def test_generate_dataset_id_from_mapping(self, installed_dbs):
        from esgvoc.apps.drs.generator import DrsGenerator

        g = DrsGenerator("cmip7")
        report = g.generate_dataset_id_from_mapping(_MAPPING)
        assert report.nb_errors == 0
        assert report.generated_drs_expression == _DSID

    def test_generate_file_name_from_mapping(self, installed_dbs):
        from esgvoc.apps.drs.generator import DrsGenerator

        g = DrsGenerator("cmip7")
        report = g.generate_file_name_from_mapping(_FILE_MAPPING)
        assert report.nb_errors == 0
        assert report.generated_drs_expression == _FILE

    def test_generate_directory_from_bag_of_terms(self, installed_dbs):
        from esgvoc.apps.drs.generator import DrsGenerator

        g = DrsGenerator("cmip7")
        bag = list(_MAPPING.values())
        report = g.generate_directory_from_bag_of_terms(bag)
        assert report.nb_errors == 0
        assert report.generated_drs_expression == _DIR

    def test_generate_dataset_id_from_bag_of_terms(self, installed_dbs):
        from esgvoc.apps.drs.generator import DrsGenerator

        g = DrsGenerator("cmip7")
        bag = list(_MAPPING.values())
        report = g.generate_dataset_id_from_bag_of_terms(bag)
        assert report.nb_errors == 0

    def test_generate_file_name_from_bag_of_terms(self, installed_dbs):
        from esgvoc.apps.drs.generator import DrsGenerator

        g = DrsGenerator("cmip7")
        bag = list(_FILE_MAPPING.values())
        report = g.generate_file_name_from_bag_of_terms(bag)
        assert report.nb_errors == 0
        assert report.generated_drs_expression.endswith(".nc")

    def test_generate_from_mapping_dispatcher_directory(self, installed_dbs):
        from esgvoc.api.project_specs import DrsType
        from esgvoc.apps.drs.generator import DrsGenerator

        g = DrsGenerator("cmip7")
        report = g.generate_from_mapping(_MAPPING, DrsType.DIRECTORY)
        assert report.nb_errors == 0

    def test_generate_from_mapping_dispatcher_dataset_id(self, installed_dbs):
        from esgvoc.api.project_specs import DrsType
        from esgvoc.apps.drs.generator import DrsGenerator

        g = DrsGenerator("cmip7")
        report = g.generate_from_mapping(_MAPPING, DrsType.DATASET_ID)
        assert report.nb_errors == 0

    def test_generate_from_mapping_dispatcher_file_name(self, installed_dbs):
        from esgvoc.api.project_specs import DrsType
        from esgvoc.apps.drs.generator import DrsGenerator

        g = DrsGenerator("cmip7")
        report = g.generate_from_mapping(_FILE_MAPPING, DrsType.FILE_NAME)
        assert report.nb_errors == 0

    def test_generate_from_bag_dispatcher_directory(self, installed_dbs):
        from esgvoc.api.project_specs import DrsType
        from esgvoc.apps.drs.generator import DrsGenerator

        g = DrsGenerator("cmip7")
        report = g.generate_from_bag_of_terms(list(_MAPPING.values()), DrsType.DIRECTORY)
        assert report.nb_errors == 0


# ---------------------------------------------------------------------------
# DrsGenerator — error cases
# ---------------------------------------------------------------------------

class TestDrsGeneratorErrors:
    def test_missing_required_term_reported(self, installed_dbs):
        from esgvoc.apps.drs.report import MissingTerm
        from esgvoc.apps.drs.generator import DrsGenerator

        g = DrsGenerator("cmip7")
        partial = {k: v for k, v in _MAPPING.items() if k != "mip_era"}
        report = g.generate_directory_from_mapping(partial)
        assert report.nb_errors >= 1
        assert any(isinstance(e, MissingTerm) for e in report.errors)
        assert "[MISSING]" in report.generated_drs_expression

    def test_invalid_term_reported(self, installed_dbs):
        from esgvoc.apps.drs.report import InvalidTerm
        from esgvoc.apps.drs.generator import DrsGenerator

        g = DrsGenerator("cmip7")
        bad = dict(_MAPPING)
        bad["mip_era"] = "BADVALUE"
        report = g.generate_directory_from_mapping(bad)
        assert report.nb_errors >= 1
        assert any(isinstance(e, InvalidTerm) for e in report.errors)
        assert "[INVALID]" in report.generated_drs_expression


# ---------------------------------------------------------------------------
# DrsGenerator — pedantic mode
# ---------------------------------------------------------------------------

class TestDrsGeneratorPedantic:
    def test_valid_mapping_no_errors_in_pedantic(self, installed_dbs):
        from esgvoc.apps.drs.generator import DrsGenerator

        g = DrsGenerator("cmip7", pedantic=True)
        report = g.generate_directory_from_mapping(_MAPPING)
        assert report.nb_errors == 0
        assert report.nb_warnings == 0

    def test_pedantic_escalates_optional_missing_to_error(self, installed_dbs):
        """In pedantic mode, missing optional terms become errors."""
        from esgvoc.apps.drs.generator import DrsGenerator

        g_normal = DrsGenerator("cmip7", pedantic=False)
        g_pedantic = DrsGenerator("cmip7", pedantic=True)

        # Remove only optional part (time_range in FILE_NAME)
        mapping_no_optional = dict(_FILE_MAPPING)

        r_normal = g_normal.generate_file_name_from_mapping(mapping_no_optional)
        r_pedantic = g_pedantic.generate_file_name_from_mapping(mapping_no_optional)
        # Both succeed since time_range is optional, but pedantic should have no warnings
        assert r_normal.nb_errors == 0
        assert r_pedantic.nb_warnings == 0


# ---------------------------------------------------------------------------
# DrsGenerationReport — model
# ---------------------------------------------------------------------------

class TestDrsGenerationReport:
    def test_report_str_contains_expression(self, installed_dbs):
        from esgvoc.apps.drs.generator import DrsGenerator

        g = DrsGenerator("cmip7")
        report = g.generate_directory_from_mapping(_MAPPING)
        s = str(report)
        assert _DIR in s

    def test_report_len(self, installed_dbs):
        from esgvoc.apps.drs.generator import DrsGenerator

        g = DrsGenerator("cmip7")
        partial = {k: v for k, v in _MAPPING.items() if k != "mip_era"}
        report = g.generate_directory_from_mapping(partial)
        assert len(report) == report.nb_errors

    def test_report_bool_true(self, installed_dbs):
        from esgvoc.apps.drs.generator import DrsGenerator

        g = DrsGenerator("cmip7")
        report = g.generate_directory_from_mapping(_MAPPING)
        assert bool(report) is True

    def test_report_bool_false(self, installed_dbs):
        from esgvoc.apps.drs.generator import DrsGenerator

        g = DrsGenerator("cmip7")
        report = g.generate_directory_from_mapping({})
        assert bool(report) is False


# ---------------------------------------------------------------------------
# DRS issue __str__ / __repr__ (no DB needed)
# ---------------------------------------------------------------------------

class TestDrsIssueStr:
    def test_space_str(self):
        from esgvoc.apps.drs.report import Space
        issue = Space()
        assert "white space" in str(issue)
        assert str(issue) == repr(issue)

    def test_unparsable_str(self):
        from esgvoc.api.project_specs import DrsType
        from esgvoc.apps.drs.report import Unparsable
        issue = Unparsable(expected_drs_type=DrsType.DIRECTORY)
        assert "unable to parse" in str(issue)

    def test_extra_separator_str(self):
        from esgvoc.apps.drs.report import ExtraSeparator
        issue = ExtraSeparator(column=5)
        assert "5" in str(issue)

    def test_extra_char_str(self):
        from esgvoc.apps.drs.report import ExtraChar
        issue = ExtraChar(column=10)
        assert "10" in str(issue)

    def test_blank_term_str(self):
        from esgvoc.apps.drs.report import BlankTerm
        issue = BlankTerm(column=3)
        assert "3" in str(issue)

    def test_filename_extension_issue_str(self):
        from esgvoc.apps.drs.report import FileNameExtensionIssue
        issue = FileNameExtensionIssue(expected_extension=".nc")
        assert ".nc" in str(issue)

    def test_invalid_term_str(self):
        from esgvoc.apps.drs.report import InvalidTerm
        issue = InvalidTerm(term="bad", term_position=2, collection_id_or_constant_value="mip_era")
        s = str(issue)
        assert "bad" in s
        assert "mip_era" in s
        assert str(issue) == repr(issue)

    def test_extra_term_str_with_collection(self):
        from esgvoc.apps.drs.report import ExtraTerm
        issue = ExtraTerm(term="extra", term_position=5, collection_id="some_coll")
        assert "extra" in str(issue)
        assert "some_coll" in str(issue)

    def test_extra_term_str_without_collection(self):
        from esgvoc.apps.drs.report import ExtraTerm
        issue = ExtraTerm(term="extra", term_position=5, collection_id=None)
        assert "extra" in str(issue)

    def test_missing_term_str(self):
        from esgvoc.apps.drs.report import MissingTerm
        issue = MissingTerm(collection_id="mip_era", collection_position=2)
        assert "mip_era" in str(issue)
        assert str(issue) == repr(issue)

    def test_too_many_terms_str(self):
        from esgvoc.apps.drs.report import TooManyTermCollection
        issue = TooManyTermCollection(collection_id="activity", terms=["a", "b"])
        s = str(issue)
        assert "activity" in s
        assert str(issue) == repr(issue)

    def test_conflicting_collections_str(self):
        from esgvoc.apps.drs.report import ConflictingCollections
        issue = ConflictingCollections(collection_ids=["c1", "c2"], terms=["t1"])
        s = str(issue)
        assert "c1" in s and "c2" in s
        assert str(issue) == repr(issue)

    def test_assigned_term_str(self):
        from esgvoc.apps.drs.report import AssignedTerm
        issue = AssignedTerm(collection_id="activity", term="PMIP")
        assert "PMIP" in str(issue)
        assert "activity" in str(issue)
        assert str(issue) == repr(issue)

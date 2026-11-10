"""
obs4MIPs end-to-end checks on a synthetic ODS 2.6.1 file header (tests/fixtures/obs4mips).

The fixtures are ``ncdump -h`` outputs derived from the AVISO zos obs4MIPs file:
  - ``*_ods2.6.1.cdl``: the header rewritten with ODS 2.6.1 global attributes, must be valid.
  - ``*_legacy.cdl``: the original CMIP5-era header (ODSv2.1), must be rejected.

obs4mips has no registry release yet: these tests run on a locally built DB only,
and are skipped otherwise:

    uv run python tests/build_test_dbs.py /tmp/test_dbs --projects obs4mips --repos-dir ..
    ESGVOC_TEST_DBS_DIR=/tmp/test_dbs uv run pytest tests/ncattvalid/test_obs4mips.py
"""

from __future__ import annotations

from pathlib import Path

import pytest

from esgvoc.apps.drs.validator import DrsValidator
from esgvoc.apps.ncattvalid.validator import GAValidator

pytestmark = pytest.mark.needs_db

PROJECT_ID = "obs4mips"
FIXTURES_DIR = Path(__file__).parents[1] / "fixtures" / "obs4mips"
ODS_HEADER = FIXTURES_DIR / "zos_mon_AVISO-1-0_BE_gn_ods2.6.1.cdl"
LEGACY_HEADER = FIXTURES_DIR / "zos_mon_AVISO-1-0_BE_gn_legacy.cdl"

_DIR = "obs4MIPs/NASA-JPL/AVISO-1-0/mon/zos/gn/v20261110"
_DSID = "obs4MIPs.NASA-JPL.AVISO-1-0.mon.zos.gn.v20261110"
_FILE = "zos_mon_AVISO-1-0_BE_gn_199210-201012.nc"


@pytest.fixture(scope="module")
def obs4mips_db(local_test_dbs):
    if not local_test_dbs or PROJECT_ID not in local_test_dbs:
        pytest.skip(f"no locally built {PROJECT_ID} DB: see the module docstring to build one")
    return local_test_dbs[PROJECT_ID]


class TestObs4mipsGlobalAttributes:
    def test_ods_header_is_valid(self, obs4mips_db):
        report = GAValidator(PROJECT_ID).validate_ncdump(ODS_HEADER.read_text())
        assert report.is_valid, str(report)
        assert report.filename == "zos_mon_AVISO-1-0_BE_gn_199210-201012"

    def test_free_text_attributes_are_not_cv_validated(self, obs4mips_db):
        report = GAValidator(PROJECT_ID).validate_ncdump(ODS_HEADER.read_text())
        results = {r.name: r for r in report.results}
        for name in ("history", "source_version_number"):
            assert results[name].is_valid
            assert "free-text" in results[name].message

    def test_specific_key_attributes_are_checked(self, obs4mips_db):
        validator = GAValidator(PROJECT_ID)
        assert validator.validate_one("institution", "NASA Jet Propulsion Laboratory, Pasadena, CA 91109, USA")[0].is_valid
        assert not validator.validate_one("institution", "NASA-JPL")[0].is_valid

    def test_legacy_header_is_invalid(self, obs4mips_db):
        report = GAValidator(PROJECT_ID).validate_ncdump(LEGACY_HEADER.read_text())
        assert not report.is_valid
        errors = {r.name for r in report.errors}
        assert {"nominal_resolution", "tracking_id", "Conventions"} <= errors
        assert {"activity_id", "institution_id", "variable_id", "license"} <= set(report.missing)


class TestObs4mipsDrs:
    def test_valid_directory(self, obs4mips_db):
        report = DrsValidator(PROJECT_ID).validate_directory(_DIR)
        assert report.nb_errors == 0, str(report)

    def test_valid_dataset_id(self, obs4mips_db):
        report = DrsValidator(PROJECT_ID).validate_dataset_id(_DSID)
        assert report.nb_errors == 0, str(report)

    def test_valid_file_name(self, obs4mips_db):
        report = DrsValidator(PROJECT_ID).validate_file_name(_FILE)
        assert report.nb_errors == 0, str(report)

    def test_version_without_v_is_invalid(self, obs4mips_db):
        validator = DrsValidator(PROJECT_ID)
        assert validator.validate_directory(_DIR.replace("/v2026", "/2026")).nb_errors > 0
        assert validator.validate_dataset_id(_DSID.replace(".v2026", ".2026")).nb_errors > 0

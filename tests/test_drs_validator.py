import pytest

from typing import Generator

from esgvoc.apps.drs.validator import DrsValidator

_SOME_DIRECTORY_EXPRESSIONS = {"cmip6plus": [
"CMIP6Plus/CMIP/NCC/MIROC6/amip/r2i2p1f2/ACmon/od550aer/gn/v20190923"]}


_SOME_DIRECTORY_EXPRESSIONS_TYPO_WARNINGS = {"cmip6plus": [
"CMIP6Plus/CMIP/NCC/MIROC6/amip//r2i2p1f2/ACmon/od550aer/gn/v20190923",
"CMIP6Plus/CMIP/NCC/MIROC6/amip/r2i2p1f2/ACmon/od550aer/gn/v20190923/",
"CMIP6Plus/CMIP/NCC/MIROC6/amip/r2i2p1f2/ACmon/od550aer/gn/v20190923//",
" CMIP6Plus/CMIP/NCC/MIROC6/amip/r2i2p1f2/ACmon/od550aer/gn/v20190923//"]}

_SOME_DIRECTORY_EXPRESSIONS_TYPO_ERRORS = {"cmip6plus": [
"CMIP6Plus/CMIP/NCC/MIROC6/amip/ /r2i2p1f2/ACmon/od550aer/gn/v20190923",
"CMIP6Plus/CMIP/NCC/MIROC6/amip/r2i2p1f2/ACmon/od550aer/gn/v20190923/ /",
"CMIP6Plus/CMIP/NCC/MIROC6/amip/r2i2p1f2/ACmon/od550aer/gn/v20190923/ // "]}


_SOME_FILE_NAME_EXPRESSIONS = {"cmip6plus": [
    "od550aer_ACmon_MIROC6_amip_r2i2p1f2_gn_201211-201212.nc"]}


_SOME_FILE_NAME_EXPRESSION_WARNINGS = {"cmip6plus": [
"od550aer_ACmon_MIROC6_amip_r2i2p1f2_gn.nc"]}


_SOME_FILE_NAME_EXPRESSION_EXTENSION_ERRORS = {"cmip6plus": [
    "od550aer_ACmon_MIROC6_amip_r2i2p1f2_gn",
    "od550aer_ACmon_MIROC6_amip_r2i2p1f2_gn.md",
    "od550aer_ACmon_MIROC6_amip_r2i2p1f2_gn.n",
    "od550aer_ACmon_MIROC6_amip_r2i2p1f2_gn.n c"]}


_SOME_FILE_NAME_EXPRESSION_EXTRA_TOKEN_ERRORS = {"cmip6plus": [
    "od550aer_ACmon_MIROC6_amip_r2i2p1f2_gn_201211-20121.nc",
    "od550aer_ACmon_MIROC6_amip_r2i2p1f2_gn_201211- 20121.nc",
    "od550aer_ACmon_MIROC6_amip_r2i2p1f2_gn_201211-201212_hello.nc"]}


_SOME_DATASET_ID_EXPRESSIONS = {"cmip6plus": [
"CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn"]}


_SOME_DATASET_ID_EXPRESSION_TYPO_WARNINGS = {"cmip6plus": [
    " CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn",
    "  CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn"
    "CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn ",
    "CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn  "]}


_SOME_DATASET_ID_EXPRESSION_TOKEN_ERRORS = {"cmip6plus": [
    "CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer",
    "CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon",
    "CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn.hello",
    "CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn.hello.world"]}


_SOME_DATASET_ID_EXPRESSION_ERRORS = {"cmip6plus": [
    "CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.world",
    "CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.hello.world",
    "Hello.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn"]}


_SOME_DATASET_ID_EXPRESSION_TYPO_WARNINGS = {"cmip6plus": [
"CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn ",
" CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn"]}


_SOME_DATASET_ID_EXPRESSION_TYPO_ERRORS = {"cmip6plus": [
    "CMIP6Plus_CMIP_IPSL_MIROC6_amip_r2i2p1f2_ACmon_od550aer_gn",
    "CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn.",
    "CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn..",
    "CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn.. ",
    "CMIP6Plus.CMIP.IPSL..MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn. ..",
    ".CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn",
    "..CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn",
    " ..CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn",
    "CMIP6Plus.CMIP.IPSL..MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn",
    "CMIP6Plus.CMIP.IPSL. MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn",
    "CMIP6Plus.CMIP.IPSL.  MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn",
    "CMIP6Plus.CMIP.IPSL. .MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn",
    ".CMIP6Plus.CMIP.IPSL.  .MIROC6.amip..r2i2p1f2.ACmon.od550aer.gn. ..",
    ".CMIP6Plus.CMIP.IPSL.  .MIROC6.amip..r2i2p1f2.ACmon.od550aer. ..gn",
    "CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer-gn",
    "CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer/gn"]}


def _provide_directory_expressions() -> Generator:
    for drs_expression in _SOME_DIRECTORY_EXPRESSIONS.items():
        yield drs_expression


@pytest.fixture(params=_provide_directory_expressions())
def directory_expressions(request) -> tuple[str, list[str]]:
    return request.param


def test_directory_validation(directory_expressions):
    project_id, expressions = directory_expressions
    validator = DrsValidator(project_id)
    for expression in expressions:
        validator.validate_directory(expression)


def _provide_dataset_id_expressions() -> Generator:
    for drs_expression in _SOME_DATASET_ID_EXPRESSIONS.items():
        yield drs_expression


@pytest.fixture(params=_provide_dataset_id_expressions())
def dataset_id_expressions(request) -> tuple[str, list[str]]:
    return request.param


def test_dataset_id_validation(dataset_id_expressions):
    project_id, expressions = dataset_id_expressions
    validator = DrsValidator(project_id)
    for expression in expressions:
        validator.validate_dataset_id(expression)


def _provide_file_name_expressions() -> Generator:
    for drs_expression in _SOME_FILE_NAME_EXPRESSIONS.items():
        yield drs_expression


@pytest.fixture(params=_provide_file_name_expressions())
def file_name_expressions(request) -> tuple[str, list[str]]:
    return request.param


def test_file_name_validation(file_name_expressions):
    project_id, expressions = file_name_expressions
    validator = DrsValidator(project_id)
    for expression in expressions:
        validator.validate_file_name(expression)
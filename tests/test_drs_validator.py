import pytest

from typing import Generator

from esgvoc.apps.drs.validator import DrsValidator

_SOME_DIRECTORY_EXPRESSIONS = {"cmip6plus": [
"CMIP6Plus/CMIP/NCC/MIROC6/amip/r2i2p1f2/ACmon/od550aer/gn/v20190923",
" CMIP6Plus/CMIP/NCC/MIROC6/amip/r2i2p1f2/ACmon/od550aer/gn/v20190923  ",
"CMIP6Plus/CMIP/NCC/MIROC6/amip/r2i2p1f2/ACmon/od550aer/gn/v20190923/",
"/CMIP6Plus/CMIP/NCC/MIROC6/amip/r2i2p1f2/ACmon/od550aer/gn/v20190923/",
"//CMIP6Plus/CMIP/NCC/MIROC6/amip/r2i2p1f2/ACmon/od550aer/gn/v20190923//"]}


_SOME_DATASET_ID_EXPRESSIONS = {"cmip6plus": [
"CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn",
"CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn.",
" CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn"]}


def _provide_directory_expressions() -> Generator:
    for drs_expression in _SOME_DIRECTORY_EXPRESSIONS.items():
        yield drs_expression


@pytest.fixture(params=_provide_directory_expressions())
def directory_expressions(request) -> tuple[str, list[str]]:
    return request.param


def _provide_dataset_id_expressions() -> Generator:
    for drs_expression in _SOME_DATASET_ID_EXPRESSIONS.items():
        yield drs_expression


@pytest.fixture(params=_provide_dataset_id_expressions())
def dataset_id_expressions(request) -> tuple[str, list[str]]:
    return request.param


def test_directory_validation(directory_expressions):
    project_id, expressions = directory_expressions
    validator = DrsValidator(project_id)
    for expression in expressions:
        validator.validate_directory(expression)


def test_dataset_id_validation(dataset_id_expressions):
    project_id, expressions = dataset_id_expressions
    validator = DrsValidator(project_id)
    for expression in expressions:
        validator.validate_dataset_id(expression)
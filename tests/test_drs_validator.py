import pytest

from typing import Generator, Callable, cast, Any

from esgvoc.apps.drs.validator import DrsValidator
from esgvoc.apps.drs.validation_report import (DrsIssue,
                                               ParserIssue,
                                               Token,
                                               Space,
                                               Unparsable,
                                               ExtraSeparator,
                                               ExtraChar,
                                               BlankToken,
                                               UnMatchedToken,
                                               ExtraToken,
                                               MissingToken,
                                               FileNameExtensionIssue)


def _check_issue(issue: DrsIssue, expected_result: tuple[type, Any]):
    assert isinstance(issue, expected_result[0])
    if issubclass(type(issue), ParserIssue):
        assert cast(ExtraSeparator, issue).column == expected_result[1]
    elif issubclass(type(issue), Token):
        issue = cast(Token, issue)
        assert issue.token == expected_result[1]
        assert issue.token_position == expected_result[2]
        if issue.part:
            assert str(issue.part) == expected_result[3]
        else:
            assert issue.part is None
    elif issubclass(type(issue), MissingToken):
        issue = cast(MissingToken, issue)
        assert str(issue.part) == expected_result[1]
        assert issue.part_position == expected_result[2]
    elif issubclass(type(issue), FileNameExtensionIssue):
        pass # Nothing to do.
    else:
        raise TypeError(f"unsupported type {expected_result[0]}")


def _check_expression(expression: str,
                      errors: list[tuple],
                      warnings: list[tuple],
                      validating_method: Callable):
    report = validating_method(expression)
    assert report.nb_errors == len(errors)
    assert report.nb_warnings == len(warnings)
    for index in range(0, len(errors)):
        _check_issue(report.errors[index], errors[index])
    for index in range(0, len(warnings)):
        _check_issue(report.warnings[index], warnings[index])


_SOME_DIRECTORY_EXPRESSIONS = [
    ("cmip6plus", "CMIP6Plus/CMIP/NCC/MIROC6/amip/r2i2p1f2/ACmon/od550aer/gn/v20190923")
]
def _provide_directory_expressions() -> Generator:
    for dir_expression in _SOME_DIRECTORY_EXPRESSIONS:
        yield dir_expression
@pytest.fixture(params=_provide_directory_expressions())
def directory_expression(request) -> tuple[str, str]:
    return request.param
def test_directory_validation(directory_expression):
    project_id, expression = directory_expression
    validator = DrsValidator(project_id)
    report = validator.validate_directory(expression)
    assert report and report.nb_warnings == 0


_SOME_FILE_NAME_EXPRESSIONS = [
    ("cmip6plus", "od550aer_ACmon_MIROC6_amip_r2i2p1f2_gn_201211-201212.nc")
]
def _provide_file_name_expressions() -> Generator:
    for drs_expression in _SOME_FILE_NAME_EXPRESSIONS:
        yield drs_expression
@pytest.fixture(params=_provide_file_name_expressions())
def file_name_expression(request) -> tuple[str, str]:
    return request.param
def test_file_name_validation(file_name_expression):
    project_id, expression = file_name_expression
    validator = DrsValidator(project_id)
    report = validator.validate_file_name(expression)
    assert report and report.nb_warnings == 0


_SOME_DATASET_ID_EXPRESSIONS = [
    ("cmip6plus", "CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn")
]
def _provide_dataset_id_expressions() -> Generator:
    for drs_expression in _SOME_DATASET_ID_EXPRESSIONS:
        yield drs_expression
@pytest.fixture(params=_provide_dataset_id_expressions())
def dataset_id_expression(request) -> tuple[str, str]:
    return request.param
def test_dataset_id_validation(dataset_id_expression):
    project_id, expression = dataset_id_expression
    validator = DrsValidator(project_id)
    report = validator.validate_dataset_id(expression)
    assert report and report.nb_warnings == 0


_SOME_DIRECTORY_EXPRESSION_TYPO_WARNINGS = [
    ("cmip6plus", 
        ("CMIP6Plus/CMIP/NCC/MIROC6/amip//r2i2p1f2/ACmon/od550aer/gn/v20190923",
         [], [(ExtraSeparator, 32)])),
    ("cmip6plus",
        ("CMIP6Plus/CMIP/NCC/MIROC6/amip/r2i2p1f2/ACmon/od550aer/gn/v20190923/",
         [], [(ExtraSeparator, 68)])),
    ("cmip6plus",
        ("CMIP6Plus/CMIP/NCC/MIROC6/amip/r2i2p1f2/ACmon/od550aer/gn/v20190923//",
         [], [(ExtraSeparator, 68)])),
    ("cmip6plus",
        (" CMIP6Plus/CMIP/NCC/MIROC6/amip/r2i2p1f2/ACmon/od550aer/gn/v20190923//",
         [], [(Space, None), (ExtraSeparator, 69)]))
]
def _provide_directory_expression_typo_warnings() -> Generator:
    for drs_expression in _SOME_DIRECTORY_EXPRESSION_TYPO_WARNINGS:
        yield drs_expression
@pytest.fixture(params=_provide_directory_expression_typo_warnings())
def directory_expression_typo_warning(request) -> tuple[str, tuple[str, list, list]]:
    return request.param
def test_directory_expression_typo_warning(directory_expression_typo_warning):
    project_id, expression_and_expected = directory_expression_typo_warning
    expression, errors, warnings = expression_and_expected
    validator = DrsValidator(project_id)
    _check_expression(expression, errors, warnings, validator.validate_directory)


_SOME_DIRECTORY_EXPRESSIONS_TYPO_ERRORS = [
    ("cmip6plus",
        ("CMIP6Plus/CMIP/NCC/MIROC6/amip/ /r2i2p1f2/ACmon/od550aer/gn/v20190923",
         [(BlankToken, 32)], [])),
    ("cmip6plus",
        ("CMIP6Plus/CMIP/NCC/MIROC6/amip/r2i2p1f2/ACmon/od550aer/gn/v20190923/ /",
         [(ExtraChar, 68)], [])),
    ("cmip6plus",
        ("  CMIP6Plus/CMIP/NCC/MIROC6/amip/  /r2i2p1f2/ACmon/od550aer/gn/v20190923/ // ",
         [(ExtraChar, 73), (BlankToken, 34)], [(Space, None)]))
]
def _provide_directory_expression_typo_errors() -> Generator:
    for drs_expression in _SOME_DIRECTORY_EXPRESSIONS_TYPO_ERRORS:
        yield drs_expression
@pytest.fixture(params=_provide_directory_expression_typo_errors())
def directory_expression_typo_error(request) -> tuple[str, tuple[str, list, list]]:
    return request.param
def test_directory_expression_typo_error(directory_expression_typo_error):
    project_id, expression_and_expected = directory_expression_typo_error
    expression, errors, warnings = expression_and_expected
    validator = DrsValidator(project_id)
    _check_expression(expression, errors, warnings, validator.validate_directory)


_SOME_FILE_NAME_EXPRESSION_WARNINGS = [
    ("cmip6plus",
        ("od550aer_ACmon_MIROC6_amip_r2i2p1f2_gn.nc",
         [], [(MissingToken, "time_range", 7)]))
]
def _provide_filename_expression_warnings() -> Generator:
    for drs_expression in _SOME_FILE_NAME_EXPRESSION_WARNINGS:
        yield drs_expression
@pytest.fixture(params=_provide_filename_expression_warnings())
def filename_expression_warning(request) -> tuple[str, tuple[str, list, list]]:
    return request.param
def test_filename_expression_warning(filename_expression_warning):
    project_id, expression_and_expected = filename_expression_warning
    expression, errors, warnings = expression_and_expected
    validator = DrsValidator(project_id)
    _check_expression(expression, errors, warnings, validator.validate_file_name)


_SOME_FILE_NAME_EXTENSION_ERRORS = [
    ("cmip6plus",
        ("od550aer_ACmon_MIROC6_amip_r2i2p1f2_gn",
         [(FileNameExtensionIssue, None)], [])),
    ("cmip6plus",
        ("od550aer_ACmon_MIROC6_amip_r2i2p1f2_gn.md",
         [(FileNameExtensionIssue, None)], [])),
    ("cmip6plus",
        ("od550aer_ACmon_MIROC6_amip_r2i2p1f2_gn.n",
         [(FileNameExtensionIssue, None)], [])),
    ("cmip6plus",
        ("od550aer_ACmon_MIROC6_amip_r2i2p1f2_gn.n c",
         [(FileNameExtensionIssue, None)], []))
]
def _provide_filename_extension_errors() -> Generator:
    for drs_expression in _SOME_FILE_NAME_EXTENSION_ERRORS:
        yield drs_expression
@pytest.fixture(params=_provide_filename_extension_errors())
def filename_extension_error(request) -> tuple[str, tuple[str]]:
    return request.param
def test_filename_extension_error(filename_extension_error):
    project_id, expression_and_expected = filename_extension_error
    expression, errors, warnings = expression_and_expected
    validator = DrsValidator(project_id)
    _check_expression(expression, errors, warnings, validator.validate_file_name)


_SOME_FILE_NAME_EXPRESSION_EXTRA_TOKEN_ERRORS = [
    ("cmip6plus",
        ("od550aer_ACmon_MIROC6_amip_r2i2p1f2_gn_201211-20121.nc",
         [(ExtraToken, "201211-20121", 6, "time_range")], [])),
    ("cmip6plus",
        ("od550aer_ACmon_MIROC6_amip_r2i2p1f2_gn_201211- 20121.nc",
         [(ExtraToken, "201211- 20121", 6, "time_range")], [])),
    ("cmip6plus",
        ("od550aer_ACmon_MIROC6_amip_r2i2p1f2_gn_201211-201212_hello.nc",
         [(ExtraToken, "hello", 7, None)], []))
]
def _provide_filename_expression_extra_token_errors() -> Generator:
    for drs_expression in _SOME_FILE_NAME_EXPRESSION_EXTRA_TOKEN_ERRORS:
        yield drs_expression
@pytest.fixture(params=_provide_filename_expression_extra_token_errors())
def filename_expression_extra_token_error(request) -> tuple[str, tuple]:
    return request.param
def test_filename_expression_extra_token_error(filename_expression_extra_token_error):
    project_id, expression_and_expected = filename_expression_extra_token_error
    expression, errors, warnings = expression_and_expected
    validator = DrsValidator(project_id)
    _check_expression(expression, errors, warnings, validator.validate_file_name)


_SOME_DATASET_ID_EXPRESSION_TYPO_WARNINGS = [
    ("cmip6plus",
        (" CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn",
         [], [(Space, None)])),
    ("cmip6plus",
        ("  CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn",
         [], [(Space, None)])),
    ("cmip6plus",
        ("CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn ",
         [], [(Space, None)])),
    ("cmip6plus",
        ("CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn  ",
        [], [(Space, None)])),
]
def _provide_dataset_id_expression_typo_warnings() -> Generator:
    for drs_expression in _SOME_DATASET_ID_EXPRESSION_TYPO_WARNINGS:
        yield drs_expression
@pytest.fixture(params=_provide_dataset_id_expression_typo_warnings())
def dataset_id_expression_typo_warning(request) -> tuple[str, tuple]:
    return request.param
def test_dataset_id_expression_typo_warning(dataset_id_expression_typo_warning):
    project_id, expression_and_expected = dataset_id_expression_typo_warning
    expression, errors, warnings = expression_and_expected
    validator = DrsValidator(project_id)
    _check_expression(expression, errors, warnings, validator.validate_dataset_id)


_SOME_DATASET_ID_EXPRESSION_TYPO_ERRORS = [
    ("cmip6plus",
        ("CMIP6Plus_CMIP_IPSL_MIROC6_amip_r2i2p1f2_ACmon_od550aer_gn",
         [(Unparsable, None)], [])),
    ("cmip6plus",
        ("CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn.",
         [(ExtraChar, 59)], [])),
    ("cmip6plus",
        ("CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn..",
         [(ExtraChar, 59)], [])),
    ("cmip6plus",
        ("CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn.. ",
         [(ExtraChar, 59)], [(Space, None)])),
    ("cmip6plus",
        ("CMIP6Plus.CMIP.IPSL..MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn. ..",
         [(ExtraChar, 60), (ExtraSeparator, 21)], [])),
    ("cmip6plus",
        (".CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn",
         [(ExtraSeparator, 1)], [])),
    ("cmip6plus",
        ("..CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn",
         [(ExtraSeparator, 2), (ExtraSeparator, 1)], [])),
    ("cmip6plus",
        (" ..CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn",
         [(ExtraSeparator, 3), (ExtraSeparator, 2)], [(Space, None)])),
    ("cmip6plus",
        ("CMIP6Plus.CMIP.IPSL..MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn",
         [(ExtraSeparator, 21)], [])),
    ("cmip6plus",
        ("CMIP6Plus.CMIP.IPSL. MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn",
         [(UnMatchedToken, " MIROC6", 4, "source_id")], [])),
    ("cmip6plus",
        ("CMIP6Plus.CMIP.IPSL.  MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn",
         [(UnMatchedToken, "  MIROC6", 4, "source_id")], [])),
    ("cmip6plus",
        ("CMIP6Plus.CMIP.IPSL. .MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn",
         [(BlankToken, 21)], [])),
    ("cmip6plus",
        (".CMIP6Plus.CMIP.IPSL.  .MIROC6.amip..r2i2p1f2.ACmon.od550aer.gn. ..",
         [(ExtraChar, 64), (ExtraSeparator, 37), (BlankToken, 22), (ExtraSeparator, 1)], [])),
    ("cmip6plus",
        (".CMIP6Plus.CMIP.IPSL.  .MIROC6.amip..r2i2p1f2.ACmon.od550aer. ..gn",
         [(ExtraSeparator, 64),
          (BlankToken, 62),
          (ExtraSeparator, 37),
          (BlankToken, 22),
          (ExtraSeparator, 1)], [])),
    ("cmip6plus",
        (" .CMIP6Plus.CMIP.IPSL.  .MIROC6.amip..r2i2p1f2.ACmon.od550aer. ..gn",
         [(ExtraSeparator, 65),
          (BlankToken, 63),
          (ExtraSeparator, 38),
          (BlankToken, 23),
          (ExtraSeparator, 2)], [(Space, None)])),
    ("cmip6plus",
        ("CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer-gn",
         [(UnMatchedToken, "od550aer-gn", 8, "variable_id"),
          (MissingToken, "grid_label", 9)], [])),
    ("cmip6plus",
        ("CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer/gn",
         [(UnMatchedToken, "od550aer/gn", 8, "variable_id"),
          (MissingToken, "grid_label", 9)], [])),
]
def _provide_dataset_id_expression_typo_errors() -> Generator:
    for drs_expression in _SOME_DATASET_ID_EXPRESSION_TYPO_ERRORS:
        yield drs_expression
@pytest.fixture(params=_provide_dataset_id_expression_typo_errors())
def dataset_id_expression_typo_error(request) -> tuple[str, tuple]:
    return request.param
def test_dataset_id_expression_typo_error(dataset_id_expression_typo_error):
    project_id, expression_and_expected = dataset_id_expression_typo_error
    expression, errors, warnings = expression_and_expected
    validator = DrsValidator(project_id)
    _check_expression(expression, errors, warnings, validator.validate_dataset_id)



_SOME_DATASET_ID_EXPRESSION_TOKEN_ERRORS = [
    ("cmip6plus",
        ("CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer",
         [(MissingToken, "grid_label", 9)], [])),
    ("cmip6plus",
        ("CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon",
         [(MissingToken, "variable_id", 8), (MissingToken, "grid_label", 9)], [])),
    ("cmip6plus",
        ("CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn.hello",
         [(ExtraToken, "hello", 9)], [])),
    ("cmip6plus",
        ("CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn.hello.world",
         [(ExtraToken, "hello", 9), (ExtraToken, "world", 10)], []))
]
def _provide_dataset_id_expression_token_errors() -> Generator:
    for drs_expression in _SOME_DATASET_ID_EXPRESSION_TOKEN_ERRORS:
        yield drs_expression
@pytest.fixture(params=_provide_dataset_id_expression_token_errors())
def dataset_id_expression_token_error(request) -> tuple[str, tuple]:
    return request.param
def test_dataset_id_expression_token_error(dataset_id_expression_token_error):
    project_id, expression_and_expected = dataset_id_expression_token_error
    expression, errors, warnings = expression_and_expected
    validator = DrsValidator(project_id)
    _check_expression(expression, errors, warnings, validator.validate_dataset_id)


_SOME_DATASET_ID_EXPRESSION_ERRORS = [
    ("cmip6plus",
        ("CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.world",
         [(UnMatchedToken, "world", 9, "grid_label")], [])),
    ("cmip6plus",
        ("CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.hello.world",
         [(UnMatchedToken, "hello", 8, "variable_id"), (UnMatchedToken, "world", 9, "grid_label")], [])),
    ("cmip6plus",
        ("Hello.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn",
         [(UnMatchedToken, "Hello", 1, "mip_era")], [])),
]
def _provide_dataset_id_expression_errors() -> Generator:
    for drs_expression in _SOME_DATASET_ID_EXPRESSION_ERRORS:
        yield drs_expression
@pytest.fixture(params=_provide_dataset_id_expression_errors())
def dataset_id_expression_error(request) -> tuple[str, tuple]:
    return request.param
def test_dataset_id_expression_error(dataset_id_expression_error):
    project_id, expression_and_expected = dataset_id_expression_error
    expression, errors, warnings = expression_and_expected
    validator = DrsValidator(project_id)
    _check_expression(expression, errors, warnings, validator.validate_dataset_id)
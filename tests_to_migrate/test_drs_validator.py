from esgvoc.api.project_specs import DrsType
from esgvoc.apps.drs.validator import DrsValidator
from tests.api_inputs import (  # noqa: F401
    check_drs_validation_expression,
    drs_validation_dataset_id_error,
    drs_validation_dataset_id_token_error,
    drs_validation_dataset_id_typo_error,
    drs_validation_dataset_id_typo_warning,
    drs_validation_directory_typo_error,
    drs_validation_directory_typo_warnings,
    drs_validation_error_less_query,
    drs_validation_file_name_extension_error,
    drs_validation_file_name_extra_token_error,
    drs_validation_file_name_warning,
)


def test_directory_validation(drs_validation_error_less_query) -> None:
    validator = DrsValidator(drs_validation_error_less_query.project_id)
    match drs_validation_error_less_query.drs_type:
        case DrsType.DIRECTORY:
            method = validator.validate_directory
        case DrsType.FILE_NAME:
            method = validator.validate_file_name  # type: ignore
        case DrsType.DATASET_ID:
            method = validator.validate_dataset_id  # type: ignore
        case _:
            raise TypeError(f"unsupported type {drs_validation_error_less_query.type}")
    report = method(drs_validation_error_less_query.expression)
    assert report and report.nb_warnings == 0


def test_validate(drs_validation_error_less_query) -> None:
    validator = DrsValidator(drs_validation_error_less_query.project_id)
    report = validator.validate(drs_validation_error_less_query.expression,
                                drs_validation_error_less_query.drs_type)
    assert report and report.nb_warnings == 0


def test_directory_expression_typo_warning(drs_validation_directory_typo_warnings) -> None:
    validator = DrsValidator(drs_validation_directory_typo_warnings.project_id)
    report = validator.validate_directory(drs_validation_directory_typo_warnings.expression)
    check_drs_validation_expression(drs_validation_directory_typo_warnings, report)


def test_directory_expression_typo_error(drs_validation_directory_typo_error) -> None:
    validator = DrsValidator(drs_validation_directory_typo_error.project_id)
    report = validator.validate_directory(drs_validation_directory_typo_error.expression)
    check_drs_validation_expression(drs_validation_directory_typo_error, report)


def test_filename_expression_warning(drs_validation_file_name_warning) -> None:
    validator = DrsValidator(drs_validation_file_name_warning.project_id)
    report = validator.validate_file_name(drs_validation_file_name_warning.expression)
    check_drs_validation_expression(drs_validation_file_name_warning, report)


def test_filename_extension_error(drs_validation_file_name_extension_error) -> None:
    validator = DrsValidator(drs_validation_file_name_extension_error.project_id)
    report = validator.validate_file_name(drs_validation_file_name_extension_error.expression)
    check_drs_validation_expression(drs_validation_file_name_extension_error, report)


def test_filename_expression_extra_token_error(drs_validation_file_name_extra_token_error) -> None:
    validator = DrsValidator(drs_validation_file_name_extra_token_error.project_id)
    report = validator.validate_file_name(drs_validation_file_name_extra_token_error.expression)
    check_drs_validation_expression(drs_validation_file_name_extra_token_error, report)


def test_dataset_id_expression_typo_warning(drs_validation_dataset_id_typo_warning) -> None:
    validator = DrsValidator(drs_validation_dataset_id_typo_warning.project_id)
    report = validator.validate_dataset_id(drs_validation_dataset_id_typo_warning.expression)
    check_drs_validation_expression(drs_validation_dataset_id_typo_warning, report)


def test_dataset_id_expression_typo_error(drs_validation_dataset_id_typo_error) -> None:
    validator = DrsValidator(drs_validation_dataset_id_typo_error.project_id)
    report = validator.validate_dataset_id(drs_validation_dataset_id_typo_error.expression)
    check_drs_validation_expression(drs_validation_dataset_id_typo_error, report)


def test_dataset_id_expression_token_error(drs_validation_dataset_id_token_error) -> None:
    validator = DrsValidator(drs_validation_dataset_id_token_error.project_id)
    report = validator.validate_dataset_id(drs_validation_dataset_id_token_error.expression)
    check_drs_validation_expression(drs_validation_dataset_id_token_error, report)


def test_dataset_id_expression_error(drs_validation_dataset_id_error) -> None:
    validator = DrsValidator(drs_validation_dataset_id_error.project_id)
    report = validator.validate_dataset_id(drs_validation_dataset_id_error.expression)
    check_drs_validation_expression(drs_validation_dataset_id_error, report)


def test_pedantic(drs_validation_directory_typo_warnings) -> None:
    validator = DrsValidator(drs_validation_directory_typo_warnings.project_id, pedantic=True)
    drs_validation_directory_typo_warnings.errors.extend(drs_validation_directory_typo_warnings.warnings)
    drs_validation_directory_typo_warnings.warnings = list()
    report = validator.validate_directory(drs_validation_directory_typo_warnings.expression)
    check_drs_validation_expression(drs_validation_directory_typo_warnings, report)


def test_directory_prefix(drs_validation_error_less_query) -> None:
    if drs_validation_error_less_query.drs_type == DrsType.DIRECTORY:
        prefix = '/hello/world/'
        drs_validation_error_less_query.expression = prefix + drs_validation_error_less_query.expression
        validator = DrsValidator(drs_validation_error_less_query.project_id)
        report = validator.validate_directory(drs_validation_error_less_query.expression,
                                              prefix=prefix)
        assert report and report.nb_warnings == 0
    else:
        pass

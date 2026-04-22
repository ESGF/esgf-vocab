from typing import Generator

import pytest

from esgvoc.api.project_specs import DrsType
from esgvoc.apps.drs.generator import DrsGenerator
from esgvoc.apps.drs.report import AssignedTerm, ConflictingCollections, DrsGenerationReport, TooManyTermCollection
from tests.api_inputs import DrsGenerationIssue  # noqa: F401
from tests.api_inputs import (
    DrsMappingGeneratorExpression,
    DrsTermsGeneratorExpression,
    GenerationIssueChecker,
    check_drs_generated_expression,
    drs_generation_expression,
)


def _generate_generic_call(
    expression: DrsMappingGeneratorExpression | DrsTermsGeneratorExpression, generator: DrsGenerator
) -> DrsGenerationReport:
    if isinstance(expression, DrsMappingGeneratorExpression):
        report = generator.generate_from_mapping(expression.mapping, expression.drs_type)
    else:
        report = generator.generate_from_bag_of_terms(expression.terms, expression.drs_type)
    return report


def _generate_explicit_call(
    expression: DrsMappingGeneratorExpression | DrsTermsGeneratorExpression, generator: DrsGenerator
) -> DrsGenerationReport:
    match expression.drs_type:
        case DrsType.DIRECTORY:
            if isinstance(expression, DrsMappingGeneratorExpression):
                report = generator.generate_directory_from_mapping(expression.mapping)
            else:
                report = generator.generate_directory_from_bag_of_terms(expression.terms)
        case DrsType.FILE_NAME:
            if isinstance(expression, DrsMappingGeneratorExpression):
                report = generator.generate_file_name_from_mapping(expression.mapping)
            else:
                report = generator.generate_file_name_from_bag_of_terms(expression.terms)
        case DrsType.DATASET_ID:
            if isinstance(expression, DrsMappingGeneratorExpression):
                report = generator.generate_dataset_id_from_mapping(expression.mapping)
            else:
                report = generator.generate_dataset_id_from_bag_of_terms(expression.terms)
        case _:
            raise TypeError(f"unsupported type {expression.drs_type}")
    return report


# TODO: refactor into data class.
_SOME_CONFLICTS = [
    (
        {"c0": {"w0"}, "c1": {"w1"}},
        [],
        {"c0": {"w0"}, "c1": {"w1"}},
    ),
    (
        {"c0": {"w0"}, "c1": {"w0"}, "c2": {"w1"}, "c3": {"w1"}},
        [],
        {"c0": {"w0"}, "c1": {"w0"}, "c2": {"w1"}, "c3": {"w1"}},
    ),
    (
        {"c0": {"w0", "w1"}, "c1": {"w1"}},
        [
            DrsGenerationIssue(AssignedTerm, parts="w1", collection_ids="c1"),
            DrsGenerationIssue(AssignedTerm, parts="w0", collection_ids="c0"),
        ],
        {"c0": {"w0"}, "c1": {"w1"}},
    ),
    (
        {"c0": {"w0", "w1", "w2"}, "c1": {"w0", "w1"}},
        [DrsGenerationIssue(AssignedTerm, parts="w2", collection_ids="c0")],
        {"c0": {"w2"}, "c1": {"w0", "w1"}},
    ),
    (
        {"c0": {"w0"}, "c1": {"w0", "w1"}, "c2": {"w1"}},
        [
            DrsGenerationIssue(AssignedTerm, parts="w0", collection_ids="c0"),
            DrsGenerationIssue(AssignedTerm, parts="w1", collection_ids="c2"),
        ],
        {"c0": {"w0"}, "c1": set(), "c2": {"w1"}},
    ),
    (
        {"c0": {"w0"}, "c1": {"w0"}, "c2": {"w0", "w1"}, "c3": {"w0", "w1", "w2"}},
        [
            DrsGenerationIssue(AssignedTerm, parts="w1", collection_ids="c2"),
            DrsGenerationIssue(AssignedTerm, parts="w2", collection_ids="c3"),
        ],
        {"c0": {"w0"}, "c1": {"w0"}, "c2": {"w1"}, "c3": {"w2"}},
    ),
    ({"c0": {"w0"}, "c1": {"w0"}, "c2": {"w0"}}, [], {"c0": {"w0"}, "c1": {"w0"}, "c2": {"w0"}}),
    ({"c0": {"w0", "w1"}, "c1": {"w0", "w1"}}, [], {"c0": {"w0", "w1"}, "c1": {"w0", "w1"}}),
    (
        {
            "c0": {"w0"},
            "c1": {"w0"},
            "c2": {"w0", "w1"},
            "c3": {"w0", "w1", "w2"},
            "c4": {"w3", "w4", "w5"},
            "c5": {"w3", "w4"},
            "c6": {"w6", "w7"},
            "c7": {"w8"},
        },
        [
            DrsGenerationIssue(AssignedTerm, parts="w1", collection_ids="c2"),
            DrsGenerationIssue(AssignedTerm, parts="w2", collection_ids="c3"),
            DrsGenerationIssue(AssignedTerm, parts="w5", collection_ids="c4"),
        ],
        {
            "c0": {"w0"},
            "c1": {"w0"},
            "c2": {"w1"},
            "c3": {"w2"},
            "c4": {"w5"},
            "c5": {"w3", "w4"},
            "c6": {"w7", "w6"},
            "c7": {"w8"},
        },  # noqa: E501
    ),
    (
        {"c0": {"w0"}, "c1": {"w0"}, "c2": {"w0"}, "c3": {"w1", "w2"}, "c4": {"w1", "w2"}, "c5": {"w1", "w2", "w3"}},
        [DrsGenerationIssue(AssignedTerm, parts="w3", collection_ids="c5")],
        {"c0": {"w0"}, "c1": {"w0"}, "c2": {"w0"}, "c3": {"w2", "w1"}, "c4": {"w2", "w1"}, "c5": {"w3"}},
    ),
]


def _provide_conflicts() -> Generator:
    for conflict in _SOME_CONFLICTS:
        yield conflict


@pytest.fixture(params=_provide_conflicts())
def conflict(request) -> tuple:
    return request.param


def test_resolve_conflicts(conflict) -> None:
    _in, expected_warnings, _out = conflict
    result_mapping, result_warnings = DrsGenerator._resolve_conflicts(_in)
    assert _out == result_mapping
    assert len(expected_warnings) == len(result_warnings)
    for index in range(0, len(expected_warnings)):
        checker = GenerationIssueChecker(expected_warnings[index])
        result_warnings[index].accept(checker)


_SOME_MAPPINGS = [
    ({"c0": {"w0"}, "c1": {"w1"}}, [], {"c0": "w0", "c1": "w1"}),
    (
        {"c0": {"w0"}, "c1": {"w0"}, "c2": {"w1"}, "c3": {"w2"}},
        [DrsGenerationIssue(ConflictingCollections, collection_ids=["c0", "c1"], parts=["w0"])],
        {"c2": "w1", "c3": "w2"},
    ),
    ({"c0": {"w0"}, "c1": set(), "c2": {"w1"}}, [], {"c0": "w0", "c2": "w1"}),
    (
        {"c0": {"w0"}, "c1": {"w0"}, "c2": {"w0"}},
        [DrsGenerationIssue(ConflictingCollections, collection_ids=["c0", "c1", "c2"], parts=["w0"])],
        {},
    ),
    (
        {"c0": {"w0", "w1"}, "c1": {"w0", "w1"}},
        [DrsGenerationIssue(ConflictingCollections, collection_ids=["c0", "c1"], parts=["w0", "w1"])],
        {},
    ),
    (
        {
            "c0": {"w0"},
            "c1": {"w0"},
            "c2": {"w1"},
            "c3": {"w2"},
            "c4": {"w5"},
            "c5": {"w3", "w4"},
            "c6": {"w7", "w6"},
            "c7": {"w8"},
        },  # noqa: E501
        [
            DrsGenerationIssue(ConflictingCollections, collection_ids=["c0", "c1"], parts=["w0"]),
            DrsGenerationIssue(TooManyTermCollection, collection_ids="c5", parts=["w3", "w4"]),
            DrsGenerationIssue(TooManyTermCollection, collection_ids="c6", parts=["w6", "w7"]),
        ],
        {"c2": "w1", "c3": "w2", "c4": "w5", "c7": "w8"},
    ),
    (
        {"c0": {"w0"}, "c1": {"w0"}, "c2": {"w0"}, "c3": {"w2", "w1"}, "c4": {"w2", "w1"}, "c5": {"w3"}},
        [
            DrsGenerationIssue(ConflictingCollections, collection_ids=["c0", "c1", "c2"], parts=["w0"]),
            DrsGenerationIssue(ConflictingCollections, collection_ids=["c3", "c4"], parts=["w1", "w2"]),
        ],
        {"c5": "w3"},
    ),
]


def _provide_collection_terms_mappings() -> Generator:
    for mapping in _SOME_MAPPINGS:
        yield mapping


@pytest.fixture(params=_provide_collection_terms_mappings())
def collection_terms_mapping(request) -> tuple:
    return request.param


def test_check_collection_terms_mapping(collection_terms_mapping) -> None:
    _in, expected_errors, _out = collection_terms_mapping
    result_mapping, result_errors = DrsGenerator._check_collection_terms_mapping(_in)
    assert _out == result_mapping
    assert len(expected_errors) == len(result_errors)
    for index in range(0, len(expected_errors)):
        checker = GenerationIssueChecker(expected_errors[index])
        result_errors[index].accept(checker)


def test_generate_dataset_id_from_mapping(drs_generation_expression) -> None:
    generator = DrsGenerator(drs_generation_expression.project_id)
    report = _generate_explicit_call(drs_generation_expression, generator)
    check_drs_generated_expression(drs_generation_expression, report)
    report = _generate_generic_call(drs_generation_expression, generator)
    check_drs_generated_expression(drs_generation_expression, report)


def test_pedantic() -> None:
    mapping = {
        "member_id": "r2i2p1f2",
        "activity_id": "CMIP",
        "source_id": "MIROC6",
        "mip_era": "CMIP6Plus",
        "experiment_id": "amip",
        "variable_id": "od550aer",
        "table_id": "ACmon",
        "grid_label": "gn",
        "institution_id": "IPSL",
    }
    generator = DrsGenerator("cmip6plus", pedantic=True)
    report = generator.generate_file_name_from_mapping(mapping)
    assert report.nb_errors == 1

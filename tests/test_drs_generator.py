from typing import Any, Generator
import pytest
from esgvoc.apps.drs.generator import DrsGenerator
from esgvoc.apps.drs.report import (DrsGeneratorReport, GeneratorIssue, AssignedToken, MissingToken, 
                                    InvalidToken, TooManyTokensCollection, ConflictingCollections)


class IssueChecker:
    
    def __init__(self, expected_result: tuple[type, Any]) -> None:
        self.expected_result = expected_result
    
    def _check_type(self, issue: GeneratorIssue) -> None:
        assert isinstance(issue, self.expected_result[0])

    def visit_invalid_token_issue(self, issue: InvalidToken) -> Any:
        self._check_type(issue)
        assert self.expected_result[1] == issue.token
        assert self.expected_result[2] == issue.collection_id_or_constant_value
        assert self.expected_result[3] == issue.token_position

    def visit_missing_token_issue(self, issue: MissingToken) -> Any:
        self._check_type(issue)
        assert self.expected_result[1] == issue.collection_id
        assert self.expected_result[2] == issue.collection_position
    
    def visit_too_many_tokens_collection_issue(self, issue: TooManyTokensCollection) -> Any:
        self._check_type(issue)
        assert self.expected_result[1] == issue.collection_id
        assert self.expected_result[2] == issue.tokens
    
    def visit_conflicting_collections_issue(self, issue: ConflictingCollections) -> Any:
        self._check_type(issue)
        assert self.expected_result[1] == issue.collection_ids
        assert self.expected_result[2] == issue.tokens
    
    def visit_assign_token_issue(self, issue: AssignedToken) -> Any:
        self._check_type(issue)
        self.expected_result[1] == issue.token
        self.expected_result[2] == issue.collection_id


def _generate_expression_and_check(test: tuple) -> None:
    project_id, method_name, _in, expected_errors, expected_warnings, _out = test
    generator = DrsGenerator(project_id)
    method = getattr(generator, method_name)
    report: DrsGeneratorReport = method(_in)
    assert _out == report.generated_drs_expression
    assert len(expected_errors) == report.nb_errors
    assert len(expected_warnings) == report.nb_warnings
    for index in range(0, len(expected_errors)):
        checker = IssueChecker(expected_errors[index])
        report.errors[index].accept(checker)
    for index in range(0, len(expected_warnings)):
        checker = IssueChecker(expected_warnings[index])
        report.warnings[index].accept(checker)


_SOME_CONFLICTS = [
    (
        {"c0": {"w0"}, "c1": {"w1"}},
        [],
        {'c0': {'w0'}, 'c1': {'w1'}},
    ),
    (
        {"c0": {"w0"}, "c1": {"w0"}, "c2": {"w1"}, "c3": {"w1"}},
        [],
        {'c0': {'w0'}, 'c1': {'w0'}, 'c2': {'w1'}, 'c3': {'w1'}}
    ),
    (
        {"c0": {"w0", "w1"}, "c1": {"w1"}},
        [(AssignedToken, "w1", "c1"), (AssignedToken, "w0", "c0")],
        {'c0': {'w0'}, 'c1': {'w1'}}
    ),
    (
        {"c0": {"w0", "w1", "w2"}, "c1": {"w0", "w1"}},
        [(AssignedToken, "w2", "c0")],
        {'c0': {'w2'}, 'c1': {'w0', 'w1'}}
    ),
    (
        {"c0": {"w0"}, "c1": {"w0", "w1"}, "c2": {"w1"}},
        [(AssignedToken, "w0", "c0"), (AssignedToken, "w1", "c2")],
        {'c0': {'w0'}, 'c1': set(), 'c2': {'w1'}}
    ),
    (
        {"c0": {"w0"}, "c1": {"w0"}, "c2": {"w0", "w1"}, "c3": {"w0", "w1", "w2"}},
        [(AssignedToken, "w1", "c2"), (AssignedToken, "w2", "c3")],
        {'c0': {'w0'}, 'c1': {'w0'}, 'c2': {'w1'}, 'c3': {'w2'}}
    ),
    (
        {"c0": {"w0"}, "c1": {"w0"}, "c2": {"w0"}},
        [],
        {"c0": {"w0"}, "c1": {"w0"}, "c2": {"w0"}}
    ),
    (
        {"c0": {"w0", "w1"}, "c1": {"w0", "w1"}},
        [],
        {'c0': {'w0', 'w1'}, 'c1': {'w0', 'w1'}}
    ),
    (
        {"c0": {"w0"}, "c1": {"w0"}, "c2": {"w0", "w1"}, "c3": {"w0", "w1", "w2"},
         "c4": {"w3", "w4", "w5"}, "c5": {"w3", "w4"}, "c6": {"w6", "w7"}, "c7": {"w8"}},
        [(AssignedToken, "w1", "c2"), (AssignedToken, "w2", "c3"), (AssignedToken, "w5", "c4")],
        {'c0': {'w0'}, 'c1': {'w0'}, 'c2': {'w1'}, 'c3': {'w2'}, 'c4': {'w5'}, 'c5': {'w3', 'w4'}, 'c6': {'w7', 'w6'}, 'c7': {'w8'}}
    ),
    (
        {"c0": {"w0"}, "c1": {"w0"}, "c2": {"w0"}, "c3": {"w1", "w2"}, "c4": {"w1", "w2"}, "c5": {"w1", "w2", "w3"}},
        [(AssignedToken, "w3", "c5")],
        {'c0': {'w0'}, 'c1': {'w0'}, 'c2': {'w0'}, 'c3': {'w2', 'w1'}, 'c4': {'w2', 'w1'}, 'c5': {'w3'}}
    )
]
def _provide_conflicts() -> Generator:
    for conflict in _SOME_CONFLICTS:
        yield conflict
@pytest.fixture(params=_provide_conflicts())
def conflict(request) -> tuple[str, str]:
    return request.param
def test_resolve_conflicts(conflict):
    _in, expected_warnings, _out = conflict
    result_mapping,  result_warnings = DrsGenerator._resolve_conflicts(_in)
    assert _out == result_mapping
    assert len(expected_warnings) == len(result_warnings)
    for index in range(0, len(expected_warnings)):
        checker = IssueChecker(expected_warnings[index])
        result_warnings[index].accept(checker)


_SOME_MAPPINGS = [
    (
        {'c0': {'w0'}, 'c1': {'w1'}},
        [],
        {'c0': 'w0', 'c1': 'w1'}
    ),
    (
        {'c0': {'w0'}, 'c1': {'w0'}, 'c2': {'w1'}, 'c3': {'w2'}},
        [(ConflictingCollections, ["c0", "c1"], ["w0"])],
        {'c2': 'w1', 'c3': 'w2'}
    ),
    (
        {'c0': {'w0'}, 'c1': set(), 'c2': {'w1'}},
        [],
        {'c0': 'w0', 'c2': 'w1'}
    ),
    (
        {"c0": {"w0"}, "c1": {"w0"}, "c2": {"w0"}},
        [(ConflictingCollections, ["c0", "c1", "c2"], ["w0"])],
        {}
    ),
    (
        {'c0': {'w0', 'w1'}, 'c1': {'w0', 'w1'}},
        [(ConflictingCollections, ["c0", "c1"], ["w0", "w1"])],
        {}
    ),
    (
        {'c0': {'w0'}, 'c1': {'w0'}, 'c2': {'w1'}, 'c3': {'w2'}, 'c4': {'w5'}, 'c5': {'w3', 'w4'}, 'c6': {'w7', 'w6'}, 'c7': {'w8'}},
        [
            (ConflictingCollections, ["c0", "c1"], ["w0"]),
            (TooManyTokensCollection, "c5", ["w3", "w4"]),
            (TooManyTokensCollection, "c6", ["w6", "w7"])
        ],
        {'c2': 'w1', 'c3': 'w2', 'c4': 'w5', 'c7': 'w8'}
    ),
    (
        {'c0': {'w0'}, 'c1': {'w0'}, 'c2': {'w0'}, 'c3': {'w2', 'w1'}, 'c4': {'w2', 'w1'}, 'c5': {'w3'}},
        [
            (ConflictingCollections, ["c0", "c1", "c2"], ["w0"]),
            (ConflictingCollections, ["c3", "c4"], ["w1", "w2"])
        ],
        {'c5': 'w3'}
    )
]
def _provide_collection_tokens_mappings() -> Generator:
    for mapping in _SOME_MAPPINGS:
        yield mapping
@pytest.fixture(params=_provide_collection_tokens_mappings())
def collection_tokens_mapping(request) -> tuple[str, str]:
    return request.param
def test_check_collection_tokens_mapping(collection_tokens_mapping):
    _in, expected_errors, _out = collection_tokens_mapping
    result_mapping,  result_errors = DrsGenerator._check_collection_tokens_mapping(_in)
    assert _out == result_mapping
    assert len(expected_errors) == len(result_errors)
    for index in range(0, len(expected_errors)):
        checker = IssueChecker(expected_errors[index])
        result_errors[index].accept(checker)


_SOME_MAPPINGS = [
    (
        "cmip6plus",
        "generate_dataset_id_from_mapping",
        {
            'member_id': 'r2i2p1f2',
            'activity_id': 'CMIP',
            'source_id': 'MIROC6',
            'mip_era': 'CMIP6Plus',
            'experiment_id': 'amip',
            'variable_id': 'od550aer',
            'table_id': 'ACmon',
            'grid_label': 'gn',
            'institution_id': 'IPSL'
        },
        [],
        [],
        "CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn"
    ),
    (   
        "cmip6plus",
        "generate_dataset_id_from_mapping",
        {
            'member_id': 'r2i2p1f2',
            'activity_id': 'CMIP',
            'source_id': 'MIROC',
            'mip_era': 'CMIP6Plus',
            'variable_id': 'od550aer',
            'table_id': 'ACmon',
            'grid_label': 'gn',
            'institution_id': 'IPSL'
        },
        [
            (InvalidToken, 'MIROC', 'source_id', 4),
            (MissingToken, 'experiment_id', 5)
        ],
        [],
        "CMIP6Plus.CMIP.IPSL.[INVALID].[MISSING].r2i2p1f2.ACmon.od550aer.gn"
    ),
    (
        "cmip6plus",
        "generate_file_name_from_mapping",
        {
            'member_id': 'r2i2p1f2',
            'activity_id': 'CMIP',
            'source_id': 'MIROC6',
            'mip_era': 'CMIP6Plus',
            'experiment_id': 'amip',
            'variable_id': 'od550aer',
            'table_id': 'ACmon',
            'grid_label': 'gn',
            'institution_id': 'IPSL',
        },
        [],
        [(MissingToken, "time_range", 7)],
        "od550aer_ACmon_MIROC6_amip_r2i2p1f2_gn.nc"
    ),
    (
        "cmip6plus",
        "generate_dataset_id_from_bag_of_tokens",
        {
            'r2i2p1f2',
            'CMIP',
            'MIROC6',
            'CMIP6Plus',
            'amip',
            'od550aer',
            'ACmon',
            'gn',
            'IPSL',
        },
        [],
        [],
        "CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn"
    ),
    (
        "cmip6plus",
        "generate_file_name_from_bag_of_tokens",
        {
            'r2i2p1f2',
            'CMIP',
            'MIROC6',
            'CMIP6Plus',
            'amip',
            'od550aer',
            'ACmon',
            '201611-201712',
            'gn',
            'IPSL',
        },
        [],
        [],
        "od550aer_ACmon_MIROC6_amip_r2i2p1f2_gn_201611-201712.nc"
    )
]
def _provide_mappings() -> Generator:
    for mapping in _SOME_MAPPINGS:
        yield mapping
@pytest.fixture(params=_provide_mappings())
def mapping(request) -> tuple[str, str]:
    return request.param
def test_generate_dataset_id_from_mapping(mapping):
    _generate_expression_and_check(mapping)
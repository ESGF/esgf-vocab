from typing import Any, Generator
import pytest
from esgvoc.apps.drs.generator import DrsGenerator
from esgvoc.apps.drs.report import (AssignedWord, MissingToken, InvalidToken,
                                    TooManyWordsCollection, ConflictingCollections)

_SOME_BOWS = [
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
        [(AssignedWord, "w1", "c1"), (AssignedWord, "w0", "c0")],
        {'c0': {'w0'}, 'c1': {'w1'}}
    ),
    (
        {"c0": {"w0", "w1", "w2"}, "c1": {"w0", "w1"}},
        [(AssignedWord, "w2", "c0")],
        {'c0': {'w2'}, 'c1': {'w0', 'w1'}}
    ),
    (
        {"c0": {"w0"}, "c1": {"w0", "w1"}, "c2": {"w1"}},
        [(AssignedWord, "w0", "c0"), (AssignedWord, "w1", "c2")],
        {'c0': {'w0'}, 'c1': set(), 'c2': {'w1'}}
    ),
    (
        {"c0": {"w0"}, "c1": {"w0"}, "c2": {"w0", "w1"}, "c3": {"w0", "w1", "w2"}},
        [(AssignedWord, "w1", "c2"), (AssignedWord, "w2", "c3")],
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
        [(AssignedWord, "w1", "c2"), (AssignedWord, "w2", "c3"), (AssignedWord, "w5", "c4")],
        {'c0': {'w0'}, 'c1': {'w0'}, 'c2': {'w1'}, 'c3': {'w2'}, 'c4': {'w5'}, 'c5': {'w3', 'w4'}, 'c6': {'w7', 'w6'}, 'c7': {'w8'}}
    ),
    (
        {"c0": {"w0"}, "c1": {"w0"}, "c2": {"w0"}, "c3": {"w1", "w2"}, "c4": {"w1", "w2"}, "c5": {"w1", "w2", "w3"}},
        [(AssignedWord, "w3", "c5")],
        {'c0': {'w0'}, 'c1': {'w0'}, 'c2': {'w0'}, 'c3': {'w2', 'w1'}, 'c4': {'w2', 'w1'}, 'c5': {'w3'}}
    )
]


class IssueChecker:
    
    def __init__(self, expected_result: tuple[type, Any]) -> None:
        self.expected_result = expected_result
    
    def visit_invalid_token_issue(self, issue: InvalidToken) -> Any: ...
    def visit_missing_token_issue(self, issue: MissingToken) -> Any: ...
    def visit_too_many_words_collection_issue(self, issue: TooManyWordsCollection) -> Any: ...
    def visit_conflicting_collections_issue(self, issue: ConflictingCollections) -> Any: ...
    
    def visit_assign_word_issue(self, issue: AssignedWord) -> Any:
        assert isinstance(issue, self.expected_result[0])
        self.expected_result[1] == issue.word
        self.expected_result[2] == issue.collection_id


def _provide_bows() -> Generator:
    for bow in _SOME_BOWS:
        yield bow
@pytest.fixture(params=_provide_bows())
def bow(request) -> tuple[str, str]:
    return request.param
def test_resolution(bow):
    _in, expected_warnings, _out = bow
    result_mapping,  result_warnings = DrsGenerator._resolve_conflicts(_in)
    assert _out == result_mapping
    assert len(expected_warnings) == len(result_warnings)
    for index in range(0, len(expected_warnings)):
        checker = IssueChecker(expected_warnings[index])
        result_warnings[index].accept(checker)
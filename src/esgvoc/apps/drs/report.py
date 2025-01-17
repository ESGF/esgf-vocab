from abc import ABC, abstractmethod
from typing import Any, Mapping, Iterable
from esgvoc.api.models import DrsType, DrsPart


class ParserIssueVisitor(ABC):
    def visit_space_issue(self, issue: "Space") -> Any: ...
    def visit_unparsable_issue(self, issue: "Unparsable") -> Any: ...
    def visit_extra_separator_issue(self, issue: "ExtraSeparator") -> Any: ...
    def visit_extra_char_issue(self, issue: "ExtraChar") -> Any: ...
    def visit_blank_token_issue(self, issue: "BlankToken") -> Any: ...


class ValidationIssueVisitor(ABC):
    def visit_filename_extension_issue(self, issue: "FileNameExtensionIssue") -> Any: ...
    def visit_unmatched_token_issue(self, issue: "UnMatchedToken") -> Any: ...
    def visit_extra_token_issue(self, issue: "ExtraToken") -> Any: ...
    def visit_missing_token_issue(self, issue: "MissingToken") -> Any: ...


class DrsIssueVisitor(ParserIssueVisitor, ValidationIssueVisitor): ...


class DrsIssue(ABC):
    @abstractmethod
    def accept(self, visitor: DrsIssueVisitor) -> Any: ...


class ParserIssue(DrsIssue):
    def __init__(self, column: int|None = None) -> None:
        super().__init__()
        self.column: int|None = column


class Space(ParserIssue):
    def __init__(self) -> None:
        super().__init__()
    def accept(self, visitor: DrsIssueVisitor) -> Any:
        return visitor.visit_space_issue(self)
    def __repr__(self):
        return "expression is surrounded by white space[s]"


class Unparsable(ParserIssue):
    def __init__(self, expected_drs_type: DrsType) -> None:
        super().__init__()
        self.expected_drs_type = expected_drs_type
    def accept(self, visitor: DrsIssueVisitor) -> Any:
        return visitor.visit_unparsable_issue(self)
    def __repr__(self):
        return "unable to parse this expression"


class ExtraSeparator(ParserIssue):
    def __init__(self, column: int) -> None:
        super().__init__(column)
    def accept(self, visitor: DrsIssueVisitor) -> Any:
        return visitor.visit_extra_separator_issue(self)
    def __repr__(self):
        return f"extra separator(s) at column {self.column}"


class ExtraChar(ParserIssue):
    def __init__(self, column: int) -> None:
        super().__init__(column)
    def accept(self, visitor: DrsIssueVisitor) -> Any:
        return visitor.visit_extra_char_issue(self)
    def __repr__(self):
        return f"extra character(s) at column {self.column}"


class BlankToken(ParserIssue):
    def __init__(self, column: int) -> None:
        super().__init__(column)
    def accept(self, visitor: DrsIssueVisitor) -> Any:
        return visitor.visit_blank_token_issue(self)
    def __repr__(self):
        return f"blank token at column {self.column}"


class ValidationIssue(DrsIssue): ...


class FileNameExtensionIssue(ValidationIssue):
    def __init__(self, expected_extension: str) -> None:
        super().__init__()
        self.expected_extension = expected_extension
    def accept(self, visitor: DrsIssueVisitor) -> Any:
        return visitor.visit_filename_extension_issue(self)
    def __repr__(self):
        return f"filename extension missing or not compliant with '{self.expected_extension}'"
    

class Token(ValidationIssue):
    def __init__(self, token: str, token_position: int, part: DrsPart|None) -> None:
        super().__init__()
        self.token: str = token
        self.token_position: int = token_position
        self.part = part


class UnMatchedToken(Token):
    def __init__(self, token: str, token_position: int, part: DrsPart) -> None:
        super().__init__(token, token_position, part)
    def accept(self, visitor: DrsIssueVisitor) -> Any:
        return visitor.visit_unmatched_token_issue(self)
    def __repr__(self):
        return f"token '{self.token}' not compliant with {self.part} at position {self.token_position}"


class ExtraToken(Token):
    def __init__(self, token: str, token_position: int, part: DrsPart|None = None) -> None:
        super().__init__(token, token_position, part)
    def accept(self, visitor: DrsIssueVisitor) -> Any:
        return visitor.visit_extra_token_issue(self)
    def __repr__(self):
        repr = f"extra token {self.token}"
        if self.part:
            repr += f" invalidated by the optional collection {self.part}"
        return repr + f" at position {self.token_position}"


class MissingToken(ValidationIssue):
    def __init__(self, part: DrsPart, part_position: int) -> None:
        super().__init__()
        self.part: DrsPart = part
        self.part_position: int = part_position
    def accept(self, visitor: DrsIssueVisitor) -> Any:
        return visitor.visit_missing_token_issue(self)
    def __repr__(self):
        return f'missing token for {self.part} at position {self.part_position}'
    

class DrsReport:
    def __init__(self,
                 errors: list[DrsIssue],
                 warnings: list[DrsIssue]):
        self.errors: list[DrsIssue] = errors
        self.warnings: list[DrsIssue] = warnings
        self.nb_errors = len(self.errors) if self.errors else 0
        self.nb_warnings = len(self.warnings) if self.warnings else 0
        self.validated: bool = False if errors else True
    def __len__(self) -> int:
        return self.nb_errors
    def __bool__(self) -> bool:
        return self.validated


class DrsValidationReport(DrsReport):
    def __init__(self,
                 given_expression: str,
                 errors: list[DrsIssue],
                 warnings: list[DrsIssue]):
        super().__init__(errors, warnings)
        self.expression: str = given_expression
        self.message = f"'{self.expression}' has {self.nb_errors} error(s) and " + \
                       f"{self.nb_warnings} warning(s)"
    def __repr__(self) -> str:
        return self.message


class DrsGeneratorReport(DrsReport):
    MISSING_TAG: str = '[MISSING]'
    INVALID_TAG: str = '[INVALID]'
    
    def __init__(self,
                 given_mapping_or_bag_of_words: Mapping|Iterable,
                 mapping_used: Mapping,
                 errors: list[DrsIssue],
                 warnings: list[DrsIssue]):
        super().__init__(errors, warnings)
        self.given_mapping_or_bag_of_words: Mapping|Iterable = given_mapping_or_bag_of_words
        self.mapping_used: Mapping = mapping_used
        self.message = f"'{self.given_mapping_or_bag_of_words}' has {self.nb_errors} error(s) and " + \
                       f"{self.nb_warnings} warning(s)"
    def __repr__(self) -> str:
        return self.message
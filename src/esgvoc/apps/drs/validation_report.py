from abc import ABC, abstract_method
from typing import Any

class ParserIssueVisitor(ABC):
    pass


class ValidationIssueVisitor(ABC):
    pass


class DrsIssueVisitor(ParserIssueVisitor, ValidationIssueVisitor):
    pass


class DrsIssue(ABC):
    @abstract_method
    def accept(self, visitor: DrsIssueVisitor) -> Any:
        pass


class ParserIssue(DrsIssue):
    def __init__(self, column: int|None = None) -> None:
        super().__init__()
        self.column: int|None = column


class Space(ParserIssue):
    def __init__(self) -> None:
        super().__init__()
    def accept(self, visitor: DrsIssueVisitor) -> Any:
        return visitor.visit_space_issue(self)


class Unparsable(ParserIssue):
    def __init__(self) -> None:
        super().__init__()
    def accept(self, visitor: DrsIssueVisitor) -> Any:
        pass


class ExtraSeparator(ParserIssue):
    def __init__(self, column: int|None = None) -> None:
        super().__init__(column)
    def accept(self, visitor: DrsIssueVisitor) -> Any:
        pass

class ExtraChar(ParserIssue):
    def __init__(self, column: int|None = None) -> None:
        super().__init__(column)
    def accept(self, visitor: DrsIssueVisitor) -> Any:
        pass


class BlankToken(ParserIssue):
    def __init__(self, column: int|None = None) -> None:
        super().__init__(column)
    def accept(self, visitor: DrsIssueVisitor) -> Any:
        pass


class ValidationIssue(DrsIssue):
    pass


class Token(ValidationIssue):
    def __init__(self, token: str, token_position: int) -> None:
        super().__init__()
        self.token: str = token
        self.token_position: int = token_position


class UnMatchingToken(Token):
    def __init__(self, token: str, token_position: int) -> None:
        super().__init__(token, token_position)
    def accept(self, visitor: DrsIssueVisitor) -> Any:
        pass


class ExtraToken(Token):
    def __init__(self, token: str, token_position: int, invalidated_by_optional_collection: bool) -> None:
        super().__init__(token, token_position)
        self.invalidated_by_optional_collection: bool = invalidated_by_optional_collection
    def accept(self, visitor: DrsIssueVisitor) -> Any:
        pass


class MissingToken(ValidationIssue):
    def __init__(self, collection_id: str, collection_position: int) -> None:
        super().__init__()
        self.collection_id: str = collection_id
        self.collection_position: int = collection_position
    def accept(self, visitor: DrsIssueVisitor) -> Any:
        pass


class DrsValidationReport:
    def __init__(self,
                 given_expression: str,
                 errors: list[DrsIssue],
                 warnings: list[DrsIssue]):
        self.expression: str = given_expression
        self.errors: list[DrsIssue] = errors
        self.warnings: list[DrsIssue] = warnings
        self.nb_errors = len(self.errors) if self.errors else 0
        self.nb_warnings = len(self.warnings) if self.warnings else 0
        self.validated: bool = False if errors else True
        self.message = f"'{self.expression}' has {self.nb_errors} error(s) and {self.nb_warnings} warning(s)"
    def __len__(self) -> int:
        return self.nb_errors
    def __bool__(self) -> bool:
        return self.validated
    def __repr__(self) -> str:
        return self.message
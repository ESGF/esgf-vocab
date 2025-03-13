from abc import ABC, abstractmethod
from typing import Any, Protocol

from pydantic import BaseModel, computed_field

import esgvoc.core.constants as api_settings
from esgvoc.core.db.models.mixins import TermKind


class ValidationErrorVisitor(Protocol):
    """
    Specifications for a term validation error visitor.
    """
    def visit_universe_term_error(self, error: "UniverseTermError") -> Any:
        """Visit a universe term error."""
        pass

    def visit_project_term_error(self, error: "ProjectTermError") -> Any:
        """Visit a project term error."""
        pass


class ValidationError(BaseModel, ABC):
    """
    Generic class for the term validation error.
    """
    value: str
    """The given value that is invalid."""
    term: dict
    """JSON specification of the term."""
    term_kind: TermKind
    """The kind of term."""
    @computed_field  # type: ignore
    @property
    def class_name(self) -> str:
        """The class name of the issue for JSON serialization."""
        return self.__class__.__name__

    @abstractmethod
    def accept(self, visitor: ValidationErrorVisitor) -> Any:
        """
        Accept a validation error visitor.

        :param visitor: The validation error visitor.
        :type visitor: ValidationErrorVisitor
        :return: Depending on the visitor.
        :rtype: Any
        """
        pass


class UniverseTermError(ValidationError):
    """
    A validation error on a term from the universe.
    """

    data_descriptor_id: str
    """The data descriptor that the term belongs."""

    def accept(self, visitor: ValidationErrorVisitor) -> Any:
        return visitor.visit_universe_term_error(self)

    def __str__(self) -> str:
        term_id = self.term[api_settings.TERM_ID_JSON_KEY]
        result = f"The term {term_id} from the data descriptor {self.data_descriptor_id} " + \
                 f"does not validate the given value '{self.value}'"
        return result

    def __repr__(self) -> str:
        return self.__str__()


class ProjectTermError(ValidationError):
    """
    A validation error on a term from a project.
    """

    collection_id: str
    """The collection id that the term belongs"""

    def accept(self, visitor: ValidationErrorVisitor) -> Any:
        return visitor.visit_project_term_error(self)

    def __str__(self) -> str:
        term_id = self.term[api_settings.TERM_ID_JSON_KEY]
        result = f"The term {term_id} from the collection {self.collection_id} " + \
                 f"does not validate the given value '{self.value}'"
        return result

    def __repr__(self) -> str:
        return self.__str__()


class ValidationReport(BaseModel):
    """
    Term validation report.
    """

    expression: str
    """The given expression."""

    errors: list[UniverseTermError | ProjectTermError]
    """The validation errors."""

    @computed_field  # type: ignore
    @property
    def nb_errors(self) -> int:
        """The number of validation errors."""
        return len(self.errors) if self.errors else 0

    @computed_field  # type: ignore
    @property
    def validated(self) -> bool:
        """The expression is validated or not."""
        return False if self.errors else True

    def __len__(self) -> int:
        return self.nb_errors

    def __bool__(self) -> bool:
        return self.validated

    def __str__(self) -> str:
        return f"'{self.expression}' has {self.nb_errors} error(s)"

    def __repr__(self) -> str:
        return self.__str__()

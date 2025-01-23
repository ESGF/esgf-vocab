from pydantic import BaseModel, computed_field
from abc import ABC, abstractmethod
from typing import Any

import esgvoc.core.constants as api_settings
from esgvoc.core.db.models.mixins import TermKind


class ValidationErrorVisitor(ABC):
    """
    Specifications for a term validation error visitor.
    """
    @abstractmethod
    def visit_universe_term_error(self, error: "UniverseTermError") -> Any:
        """Visit a universe term error."""
        pass

    @abstractmethod
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
    
    def __repr__(self) -> str:
        term_id = self.term[api_settings.TERM_ID_JSON_KEY]
        result = f"The term {term_id} from the data descriptor {self.data_descriptor_id} "+\
                 f"does not validate the given value '{self.value}'"
        return result


class ProjectTermError(ValidationError):
    """
    A validation error on a term from a project.
    """
    
    collection_id: str
    """The collection id that the term belongs"""

    def accept(self, visitor: ValidationErrorVisitor) -> Any:
        return visitor.visit_project_term_error(self)
    
    def __repr__(self) -> str:
        term_id = self.term[api_settings.TERM_ID_JSON_KEY]
        result = f"The term {term_id} from the collection {self.collection_id} "+\
                 f"does not validate the given value '{self.value}'"
        return result


class ValidationReport(BaseModel):
    """
    Term validation report.
    """
    expression: str
    """The given expression."""
    errors: list[ValidationError]
    """The validation errors."""
    @computed_field
    @property
    def nb_errors(self) -> int:
        """The number of validation errors."""
        return len(self.errors) if self.errors else 0
    @computed_field
    @property
    def validated(self) -> bool:
        """The expression is validated or not."""
        return False if self.errors else True
        
   
    def __len__(self) -> int:
        return self.nb_errors
    
    def __bool__(self) -> bool:
        return self.validated
    
    def __repr__(self) -> str:
        return f"'{self.expression}' has {self.nb_errors} error(s)"
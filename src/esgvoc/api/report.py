from abc import ABC, abstractmethod
from typing import Any

import esgvoc.core.constants as api_settings
from esgvoc.core.db.models.mixins import TermKind
from esgvoc.core.db.models.project import PTerm
from esgvoc.core.db.models.universe import UTerm


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


class ValidationError(ABC):
    """
    Generic class for the term validation error.
    """
    def __init__(self,
                 value: str,
                 term_specs: dict,
                 term_kind: TermKind):
        self.value: str = value
        """The given value that is invalid."""
        self.term: dict = term_specs
        """JSON specification of the term."""
        self.term_kind: TermKind = term_kind
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
    def __init__(self,
                 value: str,
                 term: UTerm):
        super().__init__(value, term.specs, term.kind)
        self.data_descriptor_id: str = term.data_descriptor.id
        """The data descriptor that the term belongs."""

    def accept(self, visitor: ValidationErrorVisitor) -> Any:
        return visitor.visit_universe_term_error(self)
    
    def __repr__(self) -> str:
        term_id = self.term[api_settings.TERM_ID_JSON_KEY]
        result = f"The term {term_id} from the data descriptor {self.data_descriptor_id} "+\
                 f"does not validate the given value '{self.value}'"
        return result


class ProjectTermError(ValidationError):
    def __init__(self,
                 value: str,
                 term: PTerm):
        super().__init__(value, term.specs, term.kind)
        self.collection_id: str = term.collection.id
        """The collection id that the term belongs"""

    def accept(self, visitor: ValidationErrorVisitor) -> Any:
        return visitor.visit_project_term_error(self)
    
    def __repr__(self) -> str:
        term_id = self.term[api_settings.TERM_ID_JSON_KEY]
        result = f"The term {term_id} from the collection {self.collection_id} "+\
                 f"does not validate the given value '{self.value}'"
        return result


class ValidationReport:
    def __init__(self,
                 given_expression: str,
                 errors: list[ValidationError]):
        self.expression: str = given_expression
        self.errors: list[ValidationError] = errors
        self.nb_errors = len(self.errors) if self.errors else 0
        self.validated: bool = False if errors else True
        self.message = f"'{self.expression}' has {self.nb_errors} error(s)"
   
    def __len__(self) -> int:
        return self.nb_errors
    
    def __bool__(self) -> bool:
        return self.validated
    
    def __repr__(self) -> str:
        return self.message
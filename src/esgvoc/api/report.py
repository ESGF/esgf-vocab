from abc import ABC, abstractmethod
from typing import Any

import esgvoc.core.constants as api_settings
from esgvoc.core.db.models.mixins import TermKind
from esgvoc.core.db.models.project import PTerm
from esgvoc.core.db.models.universe import UTerm


class ValidationErrorVisitor(ABC):
    @abstractmethod
    def visit_universe_term_error(self, error: "UniverseTermError") -> Any:
        pass

    @abstractmethod
    def visit_project_term_error(self, error: "ProjectTermError") -> Any:
        pass


class ValidationError(ABC):
    def __init__(self,
                 value: str):
        self.value: str = value
    
    @abstractmethod
    def accept(self, visitor: ValidationErrorVisitor) -> Any:
        pass

class UniverseTermError(ValidationError):
    def __init__(self,
                 value: str,
                 term: UTerm):
        super().__init__(value)
        self.term: dict = term.specs
        self.term_kind: TermKind = term.kind
        self.data_descriptor_id: str = term.data_descriptor.id

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
        super().__init__(value)
        self.term: dict = term.specs
        self.term_kind: TermKind = term.kind
        self.collection_id: str = term.collection.id

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
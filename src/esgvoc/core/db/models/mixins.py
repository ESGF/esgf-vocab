from enum import Enum

from sqlmodel import Field


class TermKind(Enum):
    """
    The kinds of term.
    """
    PLAIN = "plain"
    """End written term."""
    PATTERN = "pattern"
    """Regex based terms"""
    COMPOSITE = "composite"
    """Term composed of terms."""
    MIXED = 'mixed'
    """To be defined."""


class PkMixin:
    pk: int | None = Field(default=None, primary_key=True)


class IdMixin:
    id: str = Field(index=True)

"""
Term-level comparison of two project database files.

A project DB stores each term with the universe data it links to already
merged into it, so a change in a linked universe term (even a nested one,
e.g. an organisation listed in an institution's ``members``) shows up as a
change of the project term. Comparing a published DB with a rebuild of the
same project sources against a newer universe therefore tells whether the
project is affected by that universe release, and which terms changed.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_TERMS_QUERY = "SELECT c.id, t.id, t.kind, t.specs FROM pterms t JOIN pcollections c ON t.collection_pk = c.pk"
_COLLECTIONS_QUERY = "SELECT id, term_kind, context FROM pcollections"


@dataclass
class ModifiedTerm:
    """A term present in both DBs, with the top-level fields that differ."""

    term_id: str
    fields: list[str]


@dataclass
class CollectionTermDiff:
    """Term changes of one collection."""

    collection_id: str
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    modified: list[ModifiedTerm] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.removed or self.modified)

    def summary(self) -> str:
        """``"2 added, 6 modified"``, in the format of the manifest release notes."""
        parts = [
            f"{len(items)} {label}"
            for label, items in (("added", self.added), ("modified", self.modified), ("removed", self.removed))
            if items
        ]
        return ", ".join(parts)


@dataclass
class TermDiff:
    """Term changes between a baseline and an updated project DB."""

    collections_added: list[str] = field(default_factory=list)
    collections_removed: list[str] = field(default_factory=list)
    collections_modified: list[str] = field(default_factory=list)
    """Collections present in both DBs whose term kind or context differs."""
    collections: list[CollectionTermDiff] = field(default_factory=list)
    """Collections with term changes, sorted by id."""

    @property
    def has_changes(self) -> bool:
        return bool(
            self.collections_added
            or self.collections_removed
            or self.collections_modified
            or any(c.has_changes for c in self.collections)
        )

    def changelog(self) -> list[str]:
        """Release-note lines, e.g. ``"- institution_id: 6 modified"``."""
        lines = [f"- {c}: new collection" for c in self.collections_added]
        lines += [f"- {c}: collection removed" for c in self.collections_removed]
        lines += [f"- {c}: updated collection model" for c in self.collections_modified]
        whole = set(self.collections_added) | set(self.collections_removed)
        lines += [f"- {c.collection_id}: {c.summary()}" for c in self.collections if c.collection_id not in whole]
        return lines

    def to_dict(self) -> dict[str, Any]:
        return {
            "has_changes": self.has_changes,
            "collections_added": self.collections_added,
            "collections_removed": self.collections_removed,
            "collections_modified": self.collections_modified,
            "collections": {
                c.collection_id: {
                    "added": c.added,
                    "removed": c.removed,
                    "modified": {m.term_id: m.fields for m in c.modified},
                }
                for c in self.collections
            },
            "changelog": self.changelog(),
        }


def _connect(db_path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)


def _load_collections(db_path: Path) -> dict[str, tuple[Any, Any]]:
    with _connect(db_path) as conn:
        return {row[0]: (row[1], json.loads(row[2]) if row[2] else None) for row in conn.execute(_COLLECTIONS_QUERY)}


def _load_terms(db_path: Path) -> dict[str, dict[str, tuple[Any, dict]]]:
    terms: dict[str, dict[str, tuple[Any, dict]]] = {}
    with _connect(db_path) as conn:
        for collection_id, term_id, kind, specs in conn.execute(_TERMS_QUERY):
            terms.setdefault(collection_id, {})[term_id] = (kind, json.loads(specs) if specs else {})
    return terms


def _changed_fields(baseline: tuple[Any, dict], updated: tuple[Any, dict]) -> list[str]:
    (kind_a, specs_a), (kind_b, specs_b) = baseline, updated
    fields = sorted(key for key in specs_a.keys() | specs_b.keys() if specs_a.get(key) != specs_b.get(key))
    if kind_a != kind_b:
        fields.insert(0, "kind")
    return fields


def diff_project_terms(baseline: Path, updated: Path) -> TermDiff:
    """
    Compare the project terms of two project DB files.

    Terms are matched by ``(collection id, term id)`` and compared on their
    stored specs (which include the merged universe data) and kind.
    """
    collections_a, collections_b = _load_collections(baseline), _load_collections(updated)
    terms_a, terms_b = _load_terms(baseline), _load_terms(updated)

    result = TermDiff(
        collections_added=sorted(collections_b.keys() - collections_a.keys()),
        collections_removed=sorted(collections_a.keys() - collections_b.keys()),
        collections_modified=sorted(
            c for c in collections_a.keys() & collections_b.keys() if collections_a[c] != collections_b[c]
        ),
    )
    for collection_id in sorted(terms_a.keys() | terms_b.keys()):
        a, b = terms_a.get(collection_id, {}), terms_b.get(collection_id, {})
        change = CollectionTermDiff(
            collection_id=collection_id,
            added=sorted(b.keys() - a.keys()),
            removed=sorted(a.keys() - b.keys()),
            modified=[
                ModifiedTerm(term_id, _changed_fields(a[term_id], b[term_id]))
                for term_id in sorted(a.keys() & b.keys())
                if a[term_id] != b[term_id]
            ],
        )
        if change.has_changes:
            result.collections.append(change)
    return result

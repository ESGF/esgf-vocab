"""
Tests for esgvoc.api.search.process_expression: the user expression turned into an SQLite FTS5
query. Checked on an in-memory FTS5 table (no DB needed).
"""

import sqlite3

import pytest

from esgvoc.api.search import process_expression

IDS = ["cf-1.11", "cf-1.10", "p-int", "g/m2", "a.b.c", "tas", "tasmax", "pr", "sea_ice", "été"]


@pytest.fixture(scope="module")
def fts5():
    db = sqlite3.connect(":memory:")
    db.execute("CREATE VIRTUAL TABLE terms USING fts5(id)")
    db.executemany("INSERT INTO terms VALUES (?)", [(term_id,) for term_id in IDS])
    yield db
    db.close()


def _find(db, expression: str) -> list[str]:
    rows = db.execute("SELECT id FROM terms WHERE terms MATCH ?", (process_expression(expression),))
    return sorted(row[0] for row in rows)


class TestProcessExpression:
    @pytest.mark.parametrize(
        ("expression", "expected"),
        [
            ("tas", "tas*"),
            ("tas*", "tas*"),
            ("cf-1", 'cf"-"1*'),
            ("cf-1.11", 'cf"-"1"."11*'),
            ("g/m2", 'g"/"m2*'),
            ("tas OR pr", "tas OR pr"),
            ("x:y (z)", 'x":"y "("z")"'),
            ("'quoted'", "quoted*"),
            ('"quoted"', "quoted*"),
            ("sea_ice", "sea_ice*"),
            ("été", "été*"),
        ],
    )
    def test_output(self, expression, expected):
        assert process_expression(expression) == expected


class TestSearch:
    @pytest.mark.parametrize(
        ("expression", "expected"),
        [
            ("cf-1.11", ["cf-1.11"]),
            ("cf-1.1", ["cf-1.10", "cf-1.11"]),
            ("cf-1", ["cf-1.10", "cf-1.11"]),
            ("g/m2", ["g/m2"]),
            ("a.b", ["a.b.c"]),
            ("p-int", ["p-int"]),
            ("tas", ["tas", "tasmax"]),
            ("tas OR pr", ["pr", "tas"]),
            ("tas NOT tasmax", ["tas"]),
            ("sea_ice", ["sea_ice"]),
            ("été", ["été"]),
        ],
    )
    def test_finds(self, fts5, expression, expected):
        assert _find(fts5, expression) == expected

    @pytest.mark.parametrize(
        "expression", ["a[b]=c@d", "x:y (z)", "100%", "a;b", "a|b", "a\\b", "a$b", "a#b", "a!b", "a?b", "a<b>c", "a&b"]
    )
    def test_special_characters_never_break_the_query(self, fts5, expression):
        # Characters not allowed in FTS5 barewords used to raise "fts5: syntax error".
        _find(fts5, expression)

    def test_no_match(self, fts5):
        assert _find(fts5, "zzzzxqjk") == []

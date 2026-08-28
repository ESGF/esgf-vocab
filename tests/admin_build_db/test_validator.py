"""
Tests for DBValidator — validating pre-built database artifacts.

Unit tests use minimal SQLite files with injected metadata — no real CV repos needed.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from esgvoc.admin.validator import DBValidator, ValidationResult
from esgvoc.api.data_descriptors.area_label import AreaLabel
from esgvoc.api.data_descriptors.coordinate import DataCoordinate
from esgvoc.api.data_descriptors.coordinate_type import CoordinateType
from esgvoc.api.data_descriptors.formula_term import FormulaTerm
from esgvoc.api.data_descriptors.frequency import Frequency
from esgvoc.api.data_descriptors.grid_axis import GridAxis
from esgvoc.api.data_descriptors.grid_variable import GridVariable
from esgvoc.api.data_descriptors.horizontal_label import HorizontalLabel
from esgvoc.api.data_descriptors.known_branded_variable import KnownBrandedVariable
from esgvoc.api.data_descriptors.model_level_coordinate import ModelLevelCoordinate
from esgvoc.api.data_descriptors.realm import Realm
from esgvoc.api.data_descriptors.table import Table
from esgvoc.api.data_descriptors.temporal_label import TemporalLabel
from esgvoc.api.data_descriptors.variable import Variable
from esgvoc.api.data_descriptors.vertical_label import VerticalLabel

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_db(path: Path, metadata: dict | None = None, tables: dict[str, int] | None = None) -> Path:
    """Create a minimal SQLite DB with optional metadata and table stubs."""
    conn = sqlite3.connect(str(path))
    conn.execute("CREATE TABLE IF NOT EXISTS _esgvoc_metadata (key TEXT PRIMARY KEY, value TEXT)")
    if metadata:
        for k, v in metadata.items():
            conn.execute(
                "INSERT OR REPLACE INTO _esgvoc_metadata (key, value) VALUES (?, ?)",
                (k, v),
            )
    if tables:
        for table_name, row_count in tables.items():
            conn.execute(f"CREATE TABLE IF NOT EXISTS {table_name} (id TEXT)")
            for i in range(row_count):
                conn.execute(f"INSERT INTO {table_name} (id) VALUES (?)", (f"row_{i}",)) # noqa
    conn.commit()
    conn.close()
    return path


_BASE_META = {
    "project_id": "testproject",
    "cv_version": "1.0.0",
    "build_date": "2025-01-01T00:00:00+00:00",
    "esgvoc_version": "4.0.1",
}

_UNIVERSE_META = {
    "project_id": "universe",
    "cv_version": "1.0.0",
    "build_date": "2025-01-01T00:00:00+00:00",
    "esgvoc_version": "4.0.1",
}


# ---------------------------------------------------------------------------
# ValidationResult
# ---------------------------------------------------------------------------


class TestValidationResult:
    def test_starts_passed(self):
        r = ValidationResult()
        assert r.passed

    def test_add_ok_stays_passed(self):
        r = ValidationResult()
        r.add("check1", True, "good")
        assert r.passed

    def test_add_fail_sets_failed(self):
        r = ValidationResult()
        r.add("check1", False, "bad")
        assert not r.passed

    def test_summary_contains_check_names(self):
        r = ValidationResult()
        r.add("alpha", True, "ok")
        r.add("beta", False, "nope")
        s = r.summary()
        assert "alpha" in s
        assert "beta" in s
        assert "FAILED" in s

    def test_summary_passed_when_all_ok(self):
        r = ValidationResult()
        r.add("only_check", True)
        assert "PASSED" in r.summary()


# ---------------------------------------------------------------------------
# DBValidator.validate — basic checks
# ---------------------------------------------------------------------------


class TestValidateBasic:
    def test_missing_file_fails(self, tmp_path):
        v = DBValidator()
        result = v.validate(tmp_path / "nonexistent.db")
        assert not result.passed

    def test_non_sqlite_file_fails(self, tmp_path):
        bad = tmp_path / "bad.db"
        bad.write_text("not a sqlite file")
        v = DBValidator()
        result = v.validate(bad)
        assert not result.passed

    def test_valid_project_db_passes(self, tmp_path):
        db = _make_db(
            tmp_path / "test.db",
            metadata=_BASE_META,
            tables={"pcollections": 2, "pterms": 5},
        )
        v = DBValidator()
        with patch.object(DBValidator, "_check_all_terms_via_api"):
            result = v.validate(db)
        assert result.passed

    def test_valid_universe_db_passes(self, tmp_path):
        db = _make_db(
            tmp_path / "universe.db",
            metadata=_UNIVERSE_META,
            tables={"universes": 1, "udata_descriptors": 3, "uterms": 10},
        )
        v = DBValidator()
        with patch.object(DBValidator, "_check_all_terms_via_api"):
            result = v.validate(db)
        assert result.passed

    def test_missing_metadata_key_fails(self, tmp_path):
        incomplete_meta = {k: v for k, v in _BASE_META.items() if k != "cv_version"}
        db = _make_db(
            tmp_path / "test.db",
            metadata=incomplete_meta,
            tables={"pcollections": 1, "pterms": 1},
        )
        v = DBValidator()
        with patch.object(DBValidator, "_check_all_terms_via_api"):
            result = v.validate(db)
        assert not result.passed

    def test_empty_table_fails(self, tmp_path):
        db = _make_db(
            tmp_path / "test.db",
            metadata=_BASE_META,
            tables={"pcollections": 0, "pterms": 5},
        )
        v = DBValidator()
        with patch.object(DBValidator, "_check_all_terms_via_api"):
            result = v.validate(db)
        assert not result.passed


# ---------------------------------------------------------------------------
# DBValidator.validate — ingestion_errors metadata check
# ---------------------------------------------------------------------------


class TestIngestionErrorsCheck:
    def test_zero_errors_passes(self, tmp_path):
        meta = {**_BASE_META, "ingestion_errors": "0"}
        db = _make_db(tmp_path / "test.db", metadata=meta, tables={"pcollections": 1, "pterms": 1})
        v = DBValidator()
        with patch.object(DBValidator, "_check_all_terms_via_api"):
            result = v.validate(db)
        assert result.passed
        check_names = [c[0] for c in result.checks]
        assert "ingestion_errors" in check_names

    def test_nonzero_errors_fails(self, tmp_path):
        meta = {**_BASE_META, "ingestion_errors": "3"}
        db = _make_db(tmp_path / "test.db", metadata=meta, tables={"pcollections": 1, "pterms": 1})
        v = DBValidator()
        with patch.object(DBValidator, "_check_all_terms_via_api"):
            result = v.validate(db)
        assert not result.passed
        err_check = [c for c in result.checks if c[0] == "ingestion_errors"]
        assert len(err_check) == 1
        assert not err_check[0][1]  # failed
        assert "3 term(s) failed" in err_check[0][2]

    def test_missing_ingestion_errors_key_is_ok(self, tmp_path):
        """If the key is absent (older DB), skip the check — don't fail."""
        db = _make_db(tmp_path / "test.db", metadata=_BASE_META, tables={"pcollections": 1, "pterms": 1})
        v = DBValidator()
        with patch.object(DBValidator, "_check_all_terms_via_api"):
            result = v.validate(db)
        assert result.passed
        check_names = [c[0] for c in result.checks]
        assert "ingestion_errors" not in check_names


# ---------------------------------------------------------------------------
# DBValidator._check_all_terms_via_api
# ---------------------------------------------------------------------------


class TestCheckAllTermsViaApi:
    def _run(
        self,
        tmp_path,
        project_id,
        result,
        *,
        is_universe=False,
        previous_active=None,
        collections=None,
        terms_side_effect=None,
        universe_terms=None,
    ):
        """Helper to run _check_all_terms_via_api with mocked UserState + API."""
        db = _make_db(tmp_path / "test.db")
        mock_state = MagicMock()
        mock_state.get_active.return_value = previous_active

        mock_user_state_cls = MagicMock()
        mock_user_state_cls.load.return_value = mock_state
        mock_user_state_cls.db_path.return_value = tmp_path / "dbs" / project_id / "_validate_temp.db"

        patches = [
            patch("esgvoc.core.service.user_state.UserState", mock_user_state_cls),
        ]
        if is_universe:
            patches.append(patch("esgvoc.api.get_all_terms_in_universe", return_value=universe_terms or []))
        else:
            patches.append(patch("esgvoc.api.get_all_collections_in_project", return_value=collections or []))
            if terms_side_effect is not None:
                patches.append(patch("esgvoc.api.get_all_terms_in_collection", side_effect=terms_side_effect))

        for p in patches:
            p.start()
        try:
            DBValidator._check_all_terms_via_api(db, project_id, result, is_universe=is_universe)
        finally:
            for p in patches:
                p.stop()

        return mock_state

    def test_project_all_collections_ok(self, tmp_path):
        result = ValidationResult()
        self._run(
            tmp_path,
            "testproject",
            result,
            collections=["coll_a", "coll_b"],
            terms_side_effect=[
                [MagicMock(), MagicMock()],  # coll_a: 2 terms
                [MagicMock()],  # coll_b: 1 term
            ],
        )
        assert result.passed
        api_check = [c for c in result.checks if c[0] == "API term instantiation"]
        assert len(api_check) == 1
        assert "3 terms across 2 collections" in api_check[0][2]

    def test_project_collection_failure(self, tmp_path):
        result = ValidationResult()
        self._run(
            tmp_path,
            "testproject",
            result,
            collections=["good", "bad"],
            terms_side_effect=[
                [MagicMock()],
                RuntimeError("parse error"),
            ],
        )
        assert not result.passed
        api_check = [c for c in result.checks if c[0] == "API term instantiation"]
        assert "1 collection(s) failed" in api_check[0][2]

    def test_universe_terms_ok(self, tmp_path):
        result = ValidationResult()
        with patch.object(DBValidator, "_check_project_required_metadata") as check:
            self._run(
                tmp_path,
                "universe",
                result,
                is_universe=True,
                universe_terms=[MagicMock()] * 50,
            )
        check.assert_not_called()
        assert result.passed
        api_check = [c for c in result.checks if c[0] == "API term instantiation"]
        assert "50 universe terms OK" in api_check[0][2]

    def test_project_checks_required_metadata(self, tmp_path):
        result = ValidationResult()
        terms = [MagicMock(), MagicMock()]

        with patch.object(DBValidator, "_check_project_required_metadata") as check:
            self._run(
                tmp_path,
                "testproject",
                result,
                collections=["variables"],
                terms_side_effect=[terms],
            )

        check.assert_called_once()
        assert check.call_args.args[0] == terms

    def test_restores_previous_active_state(self, tmp_path):
        result = ValidationResult()
        mock_state = self._run(
            tmp_path,
            "proj",
            result,
            previous_active="v1.0.0",
            collections=[],
        )
        # Should restore the previous active version
        mock_state.set_active.assert_called_with("proj", "v1.0.0", source="local")

    def test_removes_active_if_none_previously(self, tmp_path):
        result = ValidationResult()
        mock_state = self._run(
            tmp_path,
            "proj",
            result,
            previous_active=None,
            collections=[],
        )
        mock_state.remove_active.assert_called_once_with("proj")


def _resolved_coordinate(*, is_generic=True):
    coordinate_type = CoordinateType.model_construct(id="standard_1d")
    return DataCoordinate.model_construct(
        id="alevel",
        coordinate_type=coordinate_type,
        is_generic_model_level_coordinate=is_generic,
    )


def _resolved_labels():
    return (
        TemporalLabel.model_construct(id="tavg", drs_name="tavg"),
        VerticalLabel.model_construct(id="p19", drs_name="p19"),
        HorizontalLabel.model_construct(id="hxy", drs_name="hxy"),
        AreaLabel.model_construct(id="air", drs_name="air"),
    )


def _resolved_branded_variable(**updates):
    temporal, vertical, horizontal, area = _resolved_labels()
    fields = {
        "id": "ta_tavg-p19-hxy-air",
        "drs_name": "Ta_tavg-p19-hxy-air",
        "variable_root_name": Variable.model_construct(
            id="ta",
            drs_name="Ta",
            standard_name="air_temperature",
            units="K",
        ),
        "branding_suffix_name": "tavg-p19-hxy-air",
        "out_name": "Ta",
        "cf_standard_name": "air_temperature",
        "units": "K",
        "dimensions": [_resolved_coordinate()],
        "temporal_label": temporal,
        "vertical_label": vertical,
        "horizontal_label": horizontal,
        "area_label": area,
        "realm": Realm.model_construct(id="atmos"),
        "table_id": [Table.model_construct(id="Amon")],
        "frequency": [Frequency.model_construct(id="mon")],
    }
    fields.update(updates)
    return KnownBrandedVariable.model_construct(**fields)


class TestResolvedReferences:
    @pytest.mark.parametrize(
        ("term", "path"),
        [
            (
                DataCoordinate.model_construct(id="time", coordinate_type="standard_1d"),
                "coordinate_type",
            ),
            (
                FormulaTerm.model_construct(id="ap", dimensions=["time"]),
                "dimensions[0]",
            ),
            (
                GridVariable.model_construct(id="lat", dimensions=["x"]),
                "dimensions[0]",
            ),
            (
                ModelLevelCoordinate.model_construct(
                    id="lev",
                    generic_level_name="alevel",
                ),
                "generic_level_name",
            ),
            (
                ModelLevelCoordinate.model_construct(id="lev", z_factors=["ap"]),
                "z_factors[0]",
            ),
            (
                ModelLevelCoordinate.model_construct(
                    id="lev",
                    z_bounds_factors=["ap_bnds"],
                ),
                "z_bounds_factors[0]",
            ),
            (
                KnownBrandedVariable.model_construct(
                    id="ta_tavg",
                    variable_root_name="ta",
                ),
                "variable_root_name",
            ),
            (
                KnownBrandedVariable.model_construct(id="ta_tavg", dimensions=["time"]),
                "dimensions[0]",
            ),
            (
                KnownBrandedVariable.model_construct(id="ta_tavg", temporal_label="tavg"),
                "temporal_label",
            ),
            (
                KnownBrandedVariable.model_construct(id="ta_tavg", vertical_label="p19"),
                "vertical_label",
            ),
            (
                KnownBrandedVariable.model_construct(id="ta_tavg", horizontal_label="hxy"),
                "horizontal_label",
            ),
            (
                KnownBrandedVariable.model_construct(id="ta_tavg", area_label="air"),
                "area_label",
            ),
            (
                KnownBrandedVariable.model_construct(id="ta_tavg", realm="atmos"),
                "realm",
            ),
            (
                KnownBrandedVariable.model_construct(id="ta_tavg", table_id=["Amon"]),
                "table_id[0]",
            ),
            (
                KnownBrandedVariable.model_construct(id="ta_tavg", frequency=["mon"]),
                "frequency[0]",
            ),
        ],
    )
    def test_unresolved_reference_fails(self, term, path):
        result = ValidationResult()

        DBValidator._check_resolved_references([term], result)

        assert not result.passed
        assert path in result.checks[0][2]

    def test_recursively_resolved_references_pass(self):
        coordinate = _resolved_coordinate()
        formula_term = FormulaTerm.model_construct(
            id="ap",
            dimensions=[coordinate],
        )
        model_level = ModelLevelCoordinate.model_construct(
            id="lev",
            generic_level_name=coordinate,
            z_factors=[formula_term],
            z_bounds_factors=[formula_term],
        )
        branded_variable = _resolved_branded_variable(dimensions=[coordinate])
        result = ValidationResult()

        DBValidator._check_resolved_references(
            [model_level, branded_variable],
            result,
        )

        assert result.passed
        assert result.checks[0][0] == ("Resolved coordinate and branded-variable references")


class TestResolvedModelRelationships:
    def test_matching_relationships_pass(self):
        model_level = ModelLevelCoordinate.model_construct(
            id="lev",
            generic_level_name=_resolved_coordinate(),
        )
        result = ValidationResult()

        DBValidator._check_resolved_model_relationships(
            [model_level, _resolved_branded_variable()],
            result,
        )

        assert result.passed
        assert result.checks == [
            (
                "Resolved coordinate and branded-variable relationships",
                True,
                "2 term(s) checked",
            )
        ]

    def test_non_generic_model_level_reference_fails(self):
        model_level = ModelLevelCoordinate.model_construct(
            id="lev",
            generic_level_name=_resolved_coordinate(is_generic=False),
        )
        result = ValidationResult()

        DBValidator._check_resolved_model_relationships([model_level], result)

        assert not result.passed
        assert "does not reference a generic model-level DataCoordinate" in result.checks[0][2]

    @pytest.mark.parametrize(
        ("updates", "error"),
        [
            ({"variable_root_name": "ta"}, "variable_root_name is unresolved"),
            ({"drs_name": "wrong"}, "drs_name 'wrong' does not equal"),
            ({"branding_suffix_name": "wrong"}, "branding_suffix_name 'wrong' does not equal"),
            ({"temporal_label": "tavg"}, "one or more branding labels are unresolved"),
        ],
    )
    def test_inconsistent_branded_variable_relationship_fails(self, updates, error):
        result = ValidationResult()

        DBValidator._check_resolved_model_relationships(
            [_resolved_branded_variable(**updates)],
            result,
        )

        assert not result.passed
        assert error in result.checks[0][2]

    def test_project_metadata_may_differ_from_resolved_root(self):
        result = ValidationResult()

        DBValidator._check_resolved_model_relationships(
            [
                _resolved_branded_variable(
                    out_name="historicalTa",
                    cf_standard_name="project_specific_air_temperature",
                    units="degC",
                )
            ],
            result,
        )

        assert result.passed


class TestProjectRequiredMetadata:
    @pytest.mark.parametrize(
        "term",
        [
            DataCoordinate.model_construct(id="time"),
            FormulaTerm.model_construct(id="ap"),
            GridAxis.model_construct(id="i", axis="X"),
            ModelLevelCoordinate.model_construct(id="lev"),
            KnownBrandedVariable.model_construct(id="ta_tavg"),
        ],
    )
    def test_missing_long_name_fails(self, term):
        result = ValidationResult()

        DBValidator._check_project_required_metadata([term], result)

        assert not result.passed
        expected = (
            f"GridAxis[{term.id}].long_name and cf_standard_name are missing"
            if isinstance(term, GridAxis)
            else f"{type(term).__name__}[{term.id}].long_name is missing"
        )
        assert expected in result.checks[0][2]

    def test_populated_long_names_pass(self):
        terms = [
            DataCoordinate.model_construct(id="time", long_name="time"),
            FormulaTerm.model_construct(id="ap", long_name="formula term: ap"),
            GridAxis.model_construct(id="i", long_name="first grid index"),
            ModelLevelCoordinate.model_construct(id="lev", long_name="model level"),
            KnownBrandedVariable.model_construct(id="ta_tavg", long_name="Air Temperature"),
        ]
        result = ValidationResult()

        DBValidator._check_project_required_metadata(terms, result)

        assert result.passed
        assert result.checks == [
            (
                "Resolved project required metadata",
                True,
                "5 term(s) checked",
            )
        ]

    def test_grid_axis_standard_name_satisfies_name_requirement(self):
        result = ValidationResult()
        term = GridAxis.model_construct(id="i", axis="X", cf_standard_name="projection_x_coordinate")

        DBValidator._check_project_required_metadata([term], result)

        assert result.passed

    def test_base_only_grid_axis_does_not_require_a_name(self):
        result = ValidationResult()
        term = GridAxis.model_construct(id="vertices")

        DBValidator._check_project_required_metadata([term], result)

        assert result.passed

    def test_nested_coordinate_is_checked(self):
        grid_variable = GridVariable.model_construct(
            id="latitude",
            dimensions=[DataCoordinate.model_construct(id="latitude")],
        )
        result = ValidationResult()

        DBValidator._check_project_required_metadata([grid_variable], result)

        assert not result.passed
        assert "DataCoordinate[latitude].long_name is missing" in result.checks[0][2]

    def test_nested_universe_term_uses_matching_project_term_metadata(self):
        universe_formula_term = FormulaTerm.model_construct(id="p0", long_name=None)
        model_level = ModelLevelCoordinate.model_construct(
            id="standard_hybrid_sigma",
            long_name="hybrid sigma pressure coordinate",
            z_factors=[universe_formula_term],
        )
        project_formula_term = FormulaTerm.model_construct(
            id="p0",
            long_name="vertical coordinate formula term: reference pressure",
        )
        result = ValidationResult()

        # Keep the model level first to reproduce collection traversal finding
        # its nested Universe reference before the project FormulaTerm.
        DBValidator._check_project_required_metadata(
            [model_level, project_formula_term],
            result,
        )

        assert result.passed
        assert result.checks == [
            (
                "Resolved project required metadata",
                True,
                "2 term(s) checked",
            )
        ]

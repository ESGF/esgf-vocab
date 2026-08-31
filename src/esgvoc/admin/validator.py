"""
DBValidator: validate pre-built database artifacts.

Validation levels:
  basic  — DB opens, metadata table present, counts > 0
  full   — basic + FTS index functional + sample term queries succeed
  schema — validate JSON files in a project directory (no DB needed)
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class ValidationResult:
    passed: bool = True
    checks: list[tuple[str, bool, str]] = field(default_factory=list)
    """Each check: (check_name, passed, message)"""

    def add(self, name: str, ok: bool, msg: str = "") -> None:
        self.checks.append((name, ok, msg))
        if not ok:
            self.passed = False

    def summary(self) -> str:
        lines = []
        for name, ok, msg in self.checks:
            icon = "✓" if ok else "✗"
            line = f"  {icon} {name}"
            if msg:
                line += f": {msg}"
            lines.append(line)
        status = "PASSED" if self.passed else "FAILED"
        lines.append(f"\nValidation {status}.")
        return "\n".join(lines)


class DBValidator:
    """Validate pre-built SQLite database artifacts."""

    def validate(self, db_path: Path, full: bool = False) -> ValidationResult:
        """
        Run validation checks on a database file.

        Parameters
        ----------
        db_path:
            Path to the .db file to validate.
        full:
            If True, run extended checks (FTS index, sample queries).
        """
        result = ValidationResult()

        # 1. File exists
        result.add("File exists", db_path.exists(), str(db_path))
        if not db_path.exists():
            return result

        # 2. File is a valid SQLite database
        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            conn.execute("SELECT 1")
            result.add("Opens as SQLite", True)
        except Exception as e:
            result.add("Opens as SQLite", False, str(e))
            return result

        # 3. Metadata table present
        try:
            rows = conn.execute("SELECT key, value FROM _esgvoc_metadata").fetchall()
            metadata = dict(rows)
            result.add("_esgvoc_metadata table", True, f"{len(metadata)} entries")
        except Exception as e:
            result.add("_esgvoc_metadata table", False, str(e))
            metadata = {}

        # 4. Key metadata fields
        for key in ("project_id", "cv_version", "build_date", "esgvoc_version"):
            val = metadata.get(key, "")
            result.add(f"metadata.{key}", bool(val), val or "missing")

        # 5. Ingestion errors — if tracked, must be zero
        ingestion_errors = metadata.get("ingestion_errors", "")
        if ingestion_errors:
            error_count = int(ingestion_errors)
            result.add(
                "ingestion_errors",
                error_count == 0,
                f"{error_count} term(s) failed to ingest" if error_count > 0 else "0",
            )

        # 6. Core tables have data — checked based on DB type
        is_universe = metadata.get("project_id", "") == "universe"
        if is_universe:
            core_tables = [
                ("universes", "SELECT COUNT(*) FROM universes"),
                ("udata_descriptors", "SELECT COUNT(*) FROM udata_descriptors"),
                ("uterms", "SELECT COUNT(*) FROM uterms"),
            ]
        else:
            core_tables = [
                ("pcollections", "SELECT COUNT(*) FROM pcollections"),
                ("pterms", "SELECT COUNT(*) FROM pterms"),
            ]

        for table, count_query in core_tables:
            try:
                count = conn.execute(count_query).fetchone()[0]
                result.add(f"{table} not empty", count > 0, f"{count} rows")
            except Exception as e:
                result.add(f"{table} exists", False, str(e))

        if full:
            self._check_fts(conn, result, is_universe=is_universe)
            if not is_universe:
                self._check_sample_query(conn, result)

        conn.close()

        # 7. API term instantiation — try to instantiate every term through the public API
        project_id = metadata.get("project_id", "")
        if project_id:
            self._check_all_terms_via_api(db_path, project_id, result, is_universe=is_universe)

        return result

    def validate_schema(self, project_path: Path) -> ValidationResult:
        """
        Validate JSON/YAML files in a project directory (no DB required).

        Checks:
        - esgvoc_manifest.yaml parses correctly
        - All .json files in collection dirs parse as valid JSON
        """
        result = ValidationResult()

        # Manifest
        manifest_file = project_path / "esgvoc_manifest.yaml"
        if manifest_file.exists():
            try:
                with open(manifest_file) as f:
                    data = yaml.safe_load(f)
                required = ("project", "cv_version", "universe_version")
                missing = [k for k in required if k not in data]
                if missing:
                    result.add("esgvoc_manifest.yaml", False, f"missing keys: {missing}")
                else:
                    result.add("esgvoc_manifest.yaml", True, f"cv_version={data['cv_version']}")
            except Exception as e:
                result.add("esgvoc_manifest.yaml", False, str(e))
        else:
            result.add("esgvoc_manifest.yaml", False, "not found (optional but recommended)")

        # JSON files
        import json

        json_files = list(project_path.rglob("*.json"))
        errors = []
        for jf in json_files:
            try:
                with open(jf) as f:
                    json.load(f)
            except Exception as e:
                errors.append(f"{jf.relative_to(project_path)}: {e}")

        if errors:
            result.add("JSON files valid", False, f"{len(errors)} error(s): " + "; ".join(errors[:3]))
        else:
            result.add("JSON files valid", True, f"{len(json_files)} files checked")

        return result

    # ------------------------------------------------------------------
    # Extended checks
    # ------------------------------------------------------------------

    @staticmethod
    def _check_fts(conn: sqlite3.Connection, result: ValidationResult, *, is_universe: bool = False) -> None:
        """Verify that the FTS5 full-text-search index is functional."""
        fts_tables = ("uterms_fts5", "udata_descriptors_fts5") if is_universe else ("pterms_fts5", "pcollections_fts5")
        for table in fts_tables:
            try:
                count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] # noqa
                result.add(f"FTS index {table}", count > 0, f"{count} rows")
            except Exception as e:
                result.add(f"FTS index {table}", False, str(e))

    @staticmethod
    def _check_all_terms_via_api(
        db_path: Path, project_id: str, result: ValidationResult, *, is_universe: bool = False
    ) -> None:
        """Temporarily install the DB and try to instantiate every term via the public API."""
        import shutil

        from esgvoc.core.service.user_state import UserState

        _VALIDATE_VERSION = "_validate_temp"

        state = UserState.load()
        previous_active = state.get_active(project_id)

        target = UserState.db_path(project_id, _VALIDATE_VERSION)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(db_path), str(target))
        state.set_active(project_id, _VALIDATE_VERSION, source="local")

        try:
            import esgvoc.api as ev

            if is_universe:
                try:
                    terms = ev.get_all_terms_in_universe()
                    result.add("API term instantiation", True, f"{len(terms)} universe terms OK")
                    DBValidator._check_resolved_references(terms, result)
                    DBValidator._check_resolved_model_relationships(terms, result)
                except Exception as exc:
                    result.add("API term instantiation", False, str(exc))
            else:
                collections = ev.get_all_collections_in_project(project_id)
                total = 0
                all_terms = []
                failed_collections: list[str] = []
                for coll_name in collections:
                    try:
                        terms = ev.get_all_terms_in_collection(project_id, coll_name)
                        total += len(terms)
                        all_terms.extend(terms)
                    except Exception as exc:
                        failed_collections.append(f"{coll_name}: {exc}")

                if failed_collections:
                    msg = f"{len(failed_collections)} collection(s) failed: " + "; ".join(failed_collections[:3])
                    result.add("API term instantiation", False, msg)
                else:
                    result.add(
                        "API term instantiation", True, f"{total} terms across {len(collections)} collections OK"
                    )
                DBValidator._check_resolved_references(all_terms, result)
                DBValidator._check_resolved_model_relationships(all_terms, result)
                DBValidator._check_project_required_metadata(all_terms, result)
        finally:
            # Restore previous state
            if previous_active:
                state.set_active(project_id, previous_active, source="local")
            else:
                state.remove_active(project_id)
            target.unlink(missing_ok=True)
            try:
                target.parent.rmdir()
            except OSError:
                pass

    @staticmethod
    def _check_resolved_references(terms: list, result: ValidationResult) -> None:
        """Require reference fields in coordinate and branded-variable models to be resolved."""
        from esgvoc.api.data_descriptors.coordinate import DataCoordinate
        from esgvoc.api.data_descriptors.formula_term import FormulaTerm
        from esgvoc.api.data_descriptors.grid_variable import GridVariable
        from esgvoc.api.data_descriptors.known_branded_variable import KnownBrandedVariable
        from esgvoc.api.data_descriptors.model_level_coordinate import ModelLevelCoordinate

        reference_fields = (
            (DataCoordinate, ("coordinate_type",)),
            (FormulaTerm, ("dimensions",)),
            (GridVariable, ("dimensions",)),
            (
                ModelLevelCoordinate,
                ("generic_level_name", "z_factors", "z_bounds_factors"),
            ),
            (
                KnownBrandedVariable,
                (
                    "variable_root_name",
                    "dimensions",
                    "temporal_label",
                    "vertical_label",
                    "horizontal_label",
                    "area_label",
                    "realm",
                    "table_id",
                    "frequency",
                ),
            ),
        )
        errors = []
        checked_references = 0

        def audit_model(value, path: str) -> None:
            for model_class, fields in reference_fields:
                if isinstance(value, model_class):
                    for field_name in fields:
                        audit_value(getattr(value, field_name, None), f"{path}.{field_name}")
                    return

        def audit_value(value, path: str) -> None:
            nonlocal checked_references
            if value is None:
                return
            if isinstance(value, str):
                checked_references += 1
                errors.append(f"{path}: unresolved reference {value!r}")
                return
            if isinstance(value, (list, tuple)):
                for index, item in enumerate(value):
                    audit_value(item, f"{path}[{index}]")
                return
            checked_references += 1
            audit_model(value, path)

        for term in terms:
            audit_model(term, f"{type(term).__name__}[{getattr(term, 'id', '?')}]")

        if errors:
            result.add(
                "Resolved coordinate and branded-variable references",
                False,
                f"{len(errors)} unresolved reference(s): " + "; ".join(errors[:3]),
            )
        elif checked_references:
            result.add(
                "Resolved coordinate and branded-variable references",
                True,
                f"{checked_references} reference(s) checked",
            )

    @staticmethod
    def _check_resolved_model_relationships(terms: list, result: ValidationResult) -> None:
        """Check semantic relationships that require fully resolved references."""
        from esgvoc.api.data_descriptors.area_label import AreaLabel
        from esgvoc.api.data_descriptors.coordinate import DataCoordinate
        from esgvoc.api.data_descriptors.horizontal_label import HorizontalLabel
        from esgvoc.api.data_descriptors.known_branded_variable import KnownBrandedVariable
        from esgvoc.api.data_descriptors.model_level_coordinate import ModelLevelCoordinate
        from esgvoc.api.data_descriptors.temporal_label import TemporalLabel
        from esgvoc.api.data_descriptors.variable import Variable
        from esgvoc.api.data_descriptors.vertical_label import VerticalLabel

        branded_variables = [term for term in terms if isinstance(term, KnownBrandedVariable)]
        model_level_coordinates = [term for term in terms if isinstance(term, ModelLevelCoordinate)]
        if not branded_variables and not model_level_coordinates:
            return

        errors = []
        for term in model_level_coordinates:
            if not isinstance(term.generic_level_name, DataCoordinate):
                errors.append(f"{term.id}: generic_level_name is unresolved")
            elif not term.generic_level_name.is_generic_model_level_coordinate:
                errors.append(f"{term.id}: generic_level_name does not reference a generic model-level DataCoordinate")

        for term in branded_variables:
            if not isinstance(term.variable_root_name, Variable):
                errors.append(f"{term.id}: variable_root_name is unresolved")
            else:
                root = term.variable_root_name
                expected_drs_name = f"{root.drs_name}_{term.branding_suffix_name}"
                if term.drs_name != expected_drs_name:
                    errors.append(f"{term.id}: drs_name {term.drs_name!r} does not equal {expected_drs_name!r}")

            labels = (
                term.temporal_label,
                term.vertical_label,
                term.horizontal_label,
                term.area_label,
            )
            label_classes = (TemporalLabel, VerticalLabel, HorizontalLabel, AreaLabel)
            if all(isinstance(label, label_class) for label, label_class in zip(labels, label_classes, strict=True)):
                expected_suffix = (
                    f"{term.temporal_label.drs_name}-{term.vertical_label.drs_name}-"
                    f"{term.horizontal_label.drs_name}-{term.area_label.drs_name}"
                )
                if term.branding_suffix_name != expected_suffix:
                    errors.append(
                        f"{term.id}: branding_suffix_name {term.branding_suffix_name!r} "
                        f"does not equal {expected_suffix!r}"
                    )
            else:
                errors.append(f"{term.id}: one or more branding labels are unresolved")

        if errors:
            result.add(
                "Resolved coordinate and branded-variable relationships",
                False,
                f"{len(errors)} error(s): " + "; ".join(errors[:3]),
            )
        else:
            result.add(
                "Resolved coordinate and branded-variable relationships",
                True,
                f"{len(model_level_coordinates) + len(branded_variables)} term(s) checked",
            )

    @staticmethod
    def _check_project_required_metadata(terms: list, result: ValidationResult) -> None:
        """Require project-specific metadata after Universe and project terms are resolved."""
        from esgvoc.api.data_descriptors.coordinate import DataCoordinate
        from esgvoc.api.data_descriptors.formula_term import FormulaTerm
        from esgvoc.api.data_descriptors.grid_axis import GridAxis
        from esgvoc.api.data_descriptors.grid_variable import GridVariable
        from esgvoc.api.data_descriptors.known_branded_variable import KnownBrandedVariable
        from esgvoc.api.data_descriptors.model_level_coordinate import ModelLevelCoordinate

        relevant_types = (
            DataCoordinate,
            FormulaTerm,
            GridAxis,
            ModelLevelCoordinate,
            KnownBrandedVariable,
        )
        reference_fields = (
            (DataCoordinate, ()),
            (FormulaTerm, ("dimensions",)),
            (GridAxis, ()),
            (GridVariable, ("dimensions",)),
            (
                ModelLevelCoordinate,
                ("generic_level_name", "z_factors", "z_bounds_factors"),
            ),
            (KnownBrandedVariable, ("dimensions",)),
        )
        # Nested references can currently contain the Universe version of a
        # term even when the project defines an overlay for the same ID. Build
        # an index first so required project metadata is checked on that fully
        # resolved top-level term. If no project term exists, the nested
        # Universe term is retained and missing metadata is still reported.
        project_terms = {(type(term), term.id): term for term in terms if isinstance(term, relevant_types)}
        relevant_terms = []
        seen_terms = set()

        def collect(value) -> None:
            if value is None or isinstance(value, str):
                return
            if isinstance(value, (list, tuple)):
                for item in value:
                    collect(item)
                return
            for model_class, fields in reference_fields:
                if isinstance(value, model_class):
                    if isinstance(value, relevant_types):
                        term_key = (type(value), value.id)
                        if term_key in seen_terms:
                            return
                        seen_terms.add(term_key)
                        value = project_terms.get(term_key, value)
                        relevant_terms.append(value)
                    for field_name in fields:
                        collect(getattr(value, field_name, None))
                    return

        for term in terms:
            collect(term)

        if not relevant_terms:
            return

        errors = [
            f"{type(term).__name__}[{term.id}].long_name is missing"
            for term in relevant_terms
            if not isinstance(term, GridAxis) and (not isinstance(term.long_name, str) or not term.long_name.strip())
        ]
        for term in relevant_terms:
            if not isinstance(term, GridAxis):
                continue
            has_name = any(
                isinstance(value, str) and value.strip() for value in (term.long_name, term.cf_standard_name)
            )
            axis_metadata = (
                term.axis,
                term.data_type,
                term.out_name,
                term.units,
            )
            if not has_name and any(value is not None for value in axis_metadata):
                errors.append(f"GridAxis[{term.id}].long_name and cf_standard_name are missing")
        if errors:
            result.add(
                "Resolved project required metadata",
                False,
                f"{len(errors)} error(s): " + "; ".join(errors[:3]),
            )
        else:
            result.add(
                "Resolved project required metadata",
                True,
                f"{len(relevant_terms)} term(s) checked",
            )

    @staticmethod
    def _check_sample_query(conn: sqlite3.Connection, result: ValidationResult) -> None:
        """Run a representative query that exercises joins (project DB only)."""
        try:
            row = conn.execute(
                "SELECT t.id FROM pterms t JOIN pcollections c ON t.collection_pk = c.pk LIMIT 1"
            ).fetchone()
            result.add("Sample join query", row is not None, row[0] if row else "no rows")
        except Exception as e:
            result.add("Sample join query", False, str(e))

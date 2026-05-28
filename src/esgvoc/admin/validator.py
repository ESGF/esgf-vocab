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
            rows = conn.execute(
                "SELECT key, value FROM _esgvoc_metadata"
            ).fetchall()
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
        fts_tables = (
            ("uterms_fts5", "udata_descriptors_fts5") if is_universe
            else ("pterms_fts5", "pcollections_fts5")
        )
        for table in fts_tables:
            try:
                count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
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
                except Exception as exc:
                    result.add("API term instantiation", False, str(exc))
            else:
                collections = ev.get_all_collections_in_project(project_id)
                total = 0
                failed_collections: list[str] = []
                for coll_name in collections:
                    try:
                        terms = ev.get_all_terms_in_collection(project_id, coll_name)
                        total += len(terms)
                    except Exception as exc:
                        failed_collections.append(f"{coll_name}: {exc}")

                if failed_collections:
                    msg = f"{len(failed_collections)} collection(s) failed: " + "; ".join(failed_collections[:3])
                    result.add("API term instantiation", False, msg)
                else:
                    result.add("API term instantiation", True, f"{total} terms across {len(collections)} collections OK")
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
    def _check_sample_query(conn: sqlite3.Connection, result: ValidationResult) -> None:
        """Run a representative query that exercises joins (project DB only)."""
        try:
            row = conn.execute(
                "SELECT t.id FROM pterms t "
                "JOIN pcollections c ON t.collection_pk = c.pk "
                "LIMIT 1"
            ).fetchone()
            result.add("Sample join query", row is not None, row[0] if row else "no rows")
        except Exception as e:
            result.add("Sample join query", False, str(e))

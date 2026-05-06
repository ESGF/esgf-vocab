"""
GA — Global Attributes validator for NetCDF files.

Validates each attribute in a NetCDF file against the controlled vocabulary
specifications stored in the esgvoc project database.

Public API
----------
    parse_ncdump_global_attributes(ncdump_output) -> dict[str, Any]
    GAValidator(project_id, specs=None)
        .validate(attributes, filename=None)    -> GAReport
        .validate_ncdump(ncdump_output, ...)    -> GAReport
    GAReport          — result dataclass with .is_valid, .errors, .missing, .extra
    AttributeResult   — per-attribute validation outcome
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import esgvoc.api.projects as projects
from esgvoc.api.project_specs import AttributeProperty, AttributeSpecification
from esgvoc.core.exceptions import EsgvocNotFoundError

# ---------------------------------------------------------------------------
# ncdump parser
# ---------------------------------------------------------------------------


def parse_ncdump_global_attributes(ncdump_output: str) -> dict[str, Any]:
    """
    Extract global attributes from ``ncdump -h`` output.

    Returns a dict of ``{attribute_name: value}`` where value is ``str``,
    ``int``, or ``float`` as determined by the ncdump representation.
    Multiline string values (comma-continued lines) are collapsed to their
    first segment — sufficient for CV-validated attributes which are always
    single values.
    """
    attrs: dict[str, Any] = {}
    in_globals = False
    pending_name: str | None = None
    pending_parts: list[str] = []

    for raw_line in ncdump_output.splitlines():
        line = raw_line.strip()

        if line == "// global attributes:":
            in_globals = True
            continue

        if not in_globals:
            continue

        # End of file or section boundary (non-attribute line that doesn't
        # continue a pending attribute)
        if (not line or line == "}") and pending_name is None:
            break

        if line.startswith(":"):
            # Flush any pending multiline attribute
            if pending_name is not None:
                attrs[pending_name] = _join_and_parse(pending_parts)
                pending_name, pending_parts = None, []

            m = re.match(r":(\w+)\s*=\s*(.*)", line)
            if not m:
                continue
            name = m.group(1)
            rest = m.group(2)

            if line.endswith(";"):
                attrs[name] = _parse_attr_value(rest.rstrip(";").strip())
            else:
                # Multiline: collect continuation lines
                pending_name = name
                pending_parts = [rest.rstrip(",").strip()]

        elif pending_name is not None:
            part = line.rstrip(";").rstrip(",").strip()
            pending_parts.append(part)
            if line.endswith(";"):
                attrs[pending_name] = _join_and_parse(pending_parts)
                pending_name, pending_parts = None, []

    if pending_name is not None:
        attrs[pending_name] = _join_and_parse(pending_parts)

    return attrs


def _join_and_parse(parts: list[str]) -> Any:
    """Collapse multiline ncdump value parts and parse the first segment."""
    joined = " ".join(parts)
    return _parse_attr_value(joined)


def _parse_attr_value(raw: str) -> Any:
    """Convert a raw ncdump value string to a Python scalar."""
    raw = raw.strip()

    if raw.startswith('"'):
        # Quoted string — extract first complete quoted segment
        m = re.match(r'"((?:[^"\\]|\\.)*)"', raw)
        if m:
            return m.group(1).replace("\\n", "\n").replace('\\"', '"')
        return raw.lstrip('"')

    # Numeric — ncdump uses trailing 'f' suffix for single-precision floats
    clean = raw.rstrip("f")
    try:
        return int(clean)
    except ValueError:
        pass
    try:
        return float(clean)
    except ValueError:
        pass
    return raw


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class AttributeResult:
    """Outcome of validating one global attribute."""

    name: str
    """NetCDF attribute name."""
    valid: bool
    """True when the value was accepted."""
    message: str
    """Human-readable explanation (short)."""
    value: Any = None
    """The actual value found in the file."""
    collection: str | None = None
    """Collection used for validation, if any."""


@dataclass
class GAReport:
    """Validation report for the global attributes of a NetCDF file."""

    project_id: str
    filename: str | None
    results: list[AttributeResult] = field(default_factory=list)
    """One entry per attribute that has a spec entry."""
    missing: list[str] = field(default_factory=list)
    """Required attributes that were absent from the file."""
    extra: list[str] = field(default_factory=list)
    """Attributes present in the file but not in the project spec."""

    @property
    def is_valid(self) -> bool:
        return not self.missing and all(r.valid for r in self.results)

    @property
    def errors(self) -> list[AttributeResult]:
        """Validated attributes that failed."""
        return [r for r in self.results if not r.valid]

    def __str__(self) -> str:
        header = f"GA Validation — project={self.project_id}"
        if self.filename:
            header += f"  file={self.filename}"
        status = "VALID" if self.is_valid else "INVALID"
        counts = f"{len(self.errors)} error(s), {len(self.missing)} missing, {len(self.extra)} extra"
        lines = [header, f"Status: {status}  ({counts})"]

        if self.errors:
            lines.append("\nErrors:")
            for r in self.errors:
                lines.append(f"  • {r.name} = {r.value!r}: {r.message}")

        if self.missing:
            lines.append("\nMissing required attributes:")
            for a in self.missing:
                lines.append(f"  • {a}")

        if self.extra:
            lines.append(f"\nExtra attributes ({len(self.extra)}): {', '.join(self.extra)}")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------


class GAValidator:
    """
    Validate NetCDF global attributes against a project's controlled vocabulary.

    Parameters
    ----------
    project_id:
        esgvoc project identifier (e.g. ``"cmip6"``, ``"cmip7"``).
    specs:
        Pre-loaded attribute specifications.  When ``None`` (default) the
        specs are loaded from the active database for *project_id*.
        Passing specs explicitly is useful for testing without a database.

    Raises
    ------
    EsgvocNotFoundError
        If *project_id* is not found in the database (only when *specs* is None).
    ValueError
        If the project exists but has no ``attr_specs`` defined.
    """

    def __init__(self, project_id: str, specs: AttributeSpecification | None = None):
        self.project_id = project_id
        self._specs: AttributeSpecification = specs if specs is not None else self._load_specs()

    def _load_specs(self) -> AttributeSpecification:
        project = projects.get_project(self.project_id)
        if project is None:
            raise EsgvocNotFoundError(f"project '{self.project_id}' not found")
        if project.attr_specs is None:
            raise ValueError(f"project '{self.project_id}' has no attribute specifications (attr_specs)")
        return project.attr_specs

    # ------------------------------------------------------------------
    # Public validation entry-points
    # ------------------------------------------------------------------

    def validate(
        self,
        attributes: dict[str, Any],
        filename: str | None = None,
    ) -> GAReport:
        """
        Validate a dictionary of global attributes.

        Parameters
        ----------
        attributes:
            ``{attr_name: value}`` as extracted from the NetCDF file.
        filename:
            Optional filename for reporting purposes.
        """
        spec_by_name = self._build_spec_index()

        results: list[AttributeResult] = []
        missing: list[str] = []
        extra: list[str] = []

        for name, spec in spec_by_name.items():
            if spec.is_required and name not in attributes:
                missing.append(name)

        for attr_name, attr_value in attributes.items():
            if attr_name not in spec_by_name:
                extra.append(attr_name)
                continue
            results.append(self._validate_one(attr_name, attr_value, spec_by_name[attr_name]))

        return GAReport(
            project_id=self.project_id,
            filename=filename,
            results=results,
            missing=missing,
            extra=extra,
        )

    def validate_ncdump(
        self,
        ncdump_output: str,
        filename: str | None = None,
    ) -> GAReport:
        """
        Parse ``ncdump -h`` output and validate the global attributes.

        If *filename* is not provided it is extracted from the ncdump header.
        """
        attrs = parse_ncdump_global_attributes(ncdump_output)
        if filename is None:
            m = re.match(r"netcdf\s+(.+?)\s*\{", ncdump_output.lstrip())
            if m:
                filename = m.group(1)
        return self.validate(attrs, filename)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_spec_index(self) -> dict[str, AttributeProperty]:
        """Map each effective attribute name to its AttributeProperty."""
        index: dict[str, AttributeProperty] = {}
        for spec in self._specs:
            name = spec.attr_field_name or spec.source_collection
            if name is not None:
                index[name] = spec
        return index

    def _validate_one(self, name: str, value: Any, spec: AttributeProperty) -> AttributeResult:
        """Validate a single attribute value against its spec."""
        if spec.source_collection is None:
            # Free-text attribute — no controlled vocabulary to check against
            return AttributeResult(name=name, valid=True, message="no collection constraint", value=value)

        str_value = str(value).strip()

        # Honour the NA / not-applicable value if defined
        if spec.attr_field_na_value is not None and str_value == spec.attr_field_na_value:
            return AttributeResult(
                name=name,
                valid=True,
                message=f"matches NA value ({str_value!r})",
                value=value,
                collection=spec.source_collection,
            )

        if spec.specific_key is not None:
            return self._validate_specific_key(name, str_value, value, spec)

        return self._validate_in_collection(name, str_value, value, spec)

    def _validate_specific_key(
        self,
        name: str,
        str_value: str,
        raw_value: Any,
        spec: AttributeProperty,
    ) -> AttributeResult:
        """Validate that value matches ``spec.specific_key`` field of some term."""
        matching = projects.get_terms_in_collection_by_key_value(
            self.project_id, spec.source_collection, spec.specific_key, str_value
        )
        if matching:
            return AttributeResult(
                name=name,
                valid=True,
                message="valid",
                value=raw_value,
                collection=spec.source_collection,
            )
        return AttributeResult(
            name=name,
            valid=False,
            message=(
                f"{str_value!r} not found in field '{spec.specific_key}' of collection '{spec.source_collection}'"
            ),
            value=raw_value,
            collection=spec.source_collection,
        )

    def _validate_in_collection(
        self,
        name: str,
        str_value: str,
        raw_value: Any,
        spec: AttributeProperty,
    ) -> AttributeResult:
        """Validate that value matches a term in the collection."""
        try:
            matches = projects.valid_term_in_collection(str_value, self.project_id, spec.source_collection)
        except EsgvocNotFoundError as exc:
            return AttributeResult(
                name=name,
                valid=False,
                message=f"collection '{spec.source_collection}' not found: {exc}",
                value=raw_value,
                collection=spec.source_collection,
            )

        if matches:
            return AttributeResult(
                name=name,
                valid=True,
                message="valid",
                value=raw_value,
                collection=spec.source_collection,
            )
        return AttributeResult(
            name=name,
            valid=False,
            message=f"{str_value!r} not found in collection '{spec.source_collection}'",
            value=raw_value,
            collection=spec.source_collection,
        )

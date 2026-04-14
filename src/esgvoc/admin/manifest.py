"""
Manifest: reads esgvoc_manifest.yaml from a CV repository.

This is the SOURCE manifest committed by CV maintainers.  It declares the
cv_version, universe_version, and esgvoc compatibility bounds.

Example esgvoc_manifest.yaml:
    schema_version: "1"
    project:
      id: "cmip7"
      name: "CMIP7 Controlled Vocabulary"
    cv_version: "2.1.0"
    universe_version: "1.2.0"
    esgvoc:
      min_version: "1.5.0"
      max_version: null
    release_notes: |
      - Added new institution: EXAMPLE-ORG
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field

MANIFEST_FILENAME = "esgvoc_manifest.yaml"


class ProjectMeta(BaseModel):
    id: str
    name: str = ""


class EsgvocCompat(BaseModel):
    min_version: Optional[str] = None
    max_version: Optional[str] = None


class Manifest(BaseModel):
    schema_version: str = "1"
    project: ProjectMeta
    cv_version: str
    universe_version: str
    esgvoc: EsgvocCompat = Field(default_factory=EsgvocCompat)
    release_notes: Optional[str] = None

    @classmethod
    def load(cls, project_path: Path) -> "Manifest":
        """Load manifest from a project directory."""
        manifest_file = project_path / MANIFEST_FILENAME
        if not manifest_file.exists():
            raise FileNotFoundError(
                f"Manifest not found: {manifest_file}\n"
                f"Expected '{MANIFEST_FILENAME}' in the project root."
            )
        with open(manifest_file) as f:
            data = yaml.safe_load(f)
        return cls.model_validate(data)

    @classmethod
    def load_or_default(cls, project_path: Path, project_id: str) -> "Manifest":
        """
        Load manifest if present, otherwise return a minimal default.

        Useful for building from repos that haven't added a manifest yet.
        """
        try:
            return cls.load(project_path)
        except FileNotFoundError:
            return cls(
                project=ProjectMeta(id=project_id),
                cv_version="0.0.0-unknown",
                universe_version="unknown",
            )

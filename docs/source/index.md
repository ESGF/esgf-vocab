# ESGF-VOCAB Library

ESGF-VOCAB is a Python library designed to simplify interaction with controlled vocabularies (CVs) used in climate data projects. It supports querying, caching, and validating terms across various CV repositories like the Universe and project-specific repositories (e.g., CMIP6Plus).

---

## Features

- **Query controlled vocabularies**:
  - Retrieve terms, collections, or descriptors.
  - Perform cross-validation and search operations.

- **Caching**:
  - Download CVs to a local database for offline use.
  - Keep the local cache up-to-date.

- **Validation**:
  - Validate strings against CV terms and templates.
  - Supports case-sensitive, wildcard, and approximate matching.

```{toctree}
:caption: Guides
:hidden:

guides/get_started.md
guides/basic_cli.md
guides/basics_esgvoc.ipynb
```

```{toctree}
:caption: API documentation
:hidden:

api_documentation/universe.md
api_documentation/projects.md
api_documentation/project_specs.md
api_documentation/drs.md
```
# ESGVOC Library

ESGVOC is a Python library designed to simplify interaction with controlled vocabularies (CVs) used in WCRP climate data projects. It supports querying, caching, and validating terms across various CV repositories like the [universe](https://github.com/WCRP-CMIP/WCRP-universe/tree/esgvoc) and project-specific repositories (e.g., [CMIP6Plus](https://github.com/WCRP-CMIP/CMIP6Plus_CVs/tree/esgvoc), [CMIP6](https://github.com/WCRP-CMIP/CMIP6_CVs/tree/esgvoc), etc.).

Full documentation is available at [https://esgf.github.io/esgf-vocab/](https://esgf.github.io/esgf-vocab/).

---

## Features

- **Query controlled vocabularies**:
  - Retrieve terms, collections, or descriptors.
  - Perform cross-validation and search operations.
  - Supports case-sensitive, wildcard, and approximate matching.

- **Caching**:
  - Download CVs to a local database for offline use.
  - Keep the local cache up-to-date.

- **Validation**:
  - Validate strings against CV terms and templates.

---

## Installation

ESGVOC is available on PyPI. Install it with pip:

```bash
pip install esgvoc
```

Following this command to install or update the latest CVs.


```bash
esgvoc install
```

## How to contribute

* Pip

```bash
pip install -e .
pip install pre-commit
pre-commit install
```

* UV

```bash
uv sync
uv run pre-commit install
```

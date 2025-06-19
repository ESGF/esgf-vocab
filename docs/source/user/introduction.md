
# Introduction 

`ESGVOC` is a Python library designed to streamline the management of controlled vocabularies (CV) used by the climate modelling community publishing datasets related to WCRP-ESMO (https://www.wcrp-esmo.org) activities on the ESGF (https://esgf.llnl.gov). By harmonizing vocabulary terms and providing both a Python API and a CLI for easy access, `ESGVOC` resolves common issues like inconsistencies, errors, and inefficiencies associated with managing controlled vocabularies.

## Why ESGVOC?


Previously, controlled vocabularies were stored in multiple locations and formats, requiring various software implementations to query and interpret data. This approach introduced challenges, including:

- Errors and inconsistencies across systems.
- Misuse of metadata and data.
- Difficulty in maintaining and updating vocabularies.

`ESGVOC` improves controlled vocabulary management through two main ideas:

1. **Harmonization terms through a unified CV source**  
   A single, centralized repository — referred to as the "Universe CV" — hosts all controlled vocabularies. Specialized vocabularies for specific projects reference the Universe CV via streamlined lists of IDs. This ensures consistency and eliminates duplication.

2. **Providing both pythin api and a CLI**  
   `ESGVOC` provides a dedicated service for interacting with controlled vocabularies. It enables developers, administrators, and software systems to access vocabularies seamlessly via:
   - A Python API for programmatic interaction.
   - A CLI powered by [Typer](https://typer.tiangolo.com/) for command-line use.

## Installation

You can install `ESGVOC` using recent Python packaging tools. It is only available in pypi.org (not in anaconda.org). We recommend the following methods:

### Using UV (preferred)

[UV](https://docs.astral.sh/uv/) is recommended for managing dependencies and isolating the library:

```bash
uv add esgvoc
```

This ensures all dependencies are installed, and cached repositories and databases will be stored in the `.cache` directory alongside the `.venv` folder. This approach simplifies updates and uninstallation.

### Using pip in a virtual environment
Alternatively, you can use a virtual environment:

```bash
python -m venv myenv
source myenv/bin/activate
pip install esgvoc
```

## Fetching vocabulary data

Once installed esgvoc need to clone the following WCRP CV repositories and cache them into an SQLite database:  


`ESGVOC` primarily uses the following repositories for controlled vocabulary data:

- **Universe CV**: [GitHub Repository](https://github.com/WCRP-CMIP/WCRP-universe/tree/esgvoc)
- **CMIP6 CVs**: [GitHub Repository](https://github.com/WCRP-CMIP/CMIP6_CVs/tree/esgvoc)
- **CMIP6Plus CVs**: [GitHub Repository](https://github.com/WCRP-CMIP/CMIP6Plus_CVs/tree/esgvoc)


```{eval-rst}
.. warning::
   To be accurate, ESGVOC uses the specific branch "esgvoc" in those repositories.
```

those are configured by default !

```bash
esgvoc install
```

This command performs the following actions:
- Clones the official repositories.
- Builds a cached SQLite database from the cloned data.

### Offline use
If there is no internet access, it is still possible to use the library: copy the repositories into `.cache/repos` and then issue `esgvoc install`. The library will check the `.cache/repos` directory for existing repositories.

## Official controlled vocabulary repositories

### Flexibility for other repositories
While designed for these repositories, `ESGVOC` can use other repositories if they are structured correctly.

## Requirements

- **Python Version**: 3.12 or higher.
- **No additional system dependencies**: interaction with the library is entirely Python-based, with no other external dependencies like SQLite.

---

This introduction covers the general purpose and installation of `ESGVOC`. In the next sections, we will dive deeper into its functionality, including the Python API and CLI usage.

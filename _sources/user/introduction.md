
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

2. **Providing both a Python API and a CLI**  
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

This ensures all dependencies are installed. Vocabulary databases are stored in the platform data directory (e.g. `~/.local/share/esgvoc/` on Linux), independently of the virtual environment.

### Using pip in a virtual environment
Alternatively, you can use a virtual environment:

```bash
python -m venv myenv
source myenv/bin/activate
pip install esgvoc
```

## Fetching vocabulary data

Once installed, `ESGVOC` needs to download pre-built SQLite databases for the projects
you want to work with. Databases are served from the official registry
([WCRP-CMIP/esgvoc_registry](https://github.com/WCRP-CMIP/esgvoc_registry)) and are
versioned independently of the library itself.

### Downloading a vocabulary

Use the `esgvoc use` command to download and activate a project database:

```bash
# Download and activate the latest stable universe vocabulary
esgvoc use universe@latest

# Download and activate the latest CMIP7 vocabulary
esgvoc use cmip7@latest

# Download and activate a specific version
esgvoc use cmip6@v1.3.0
```

Available projects include: `universe`, `cmip7`, `cmip6`, `cmip6plus`, `input4mips`,
`obs4ref`, `cordex-cmip6`, `cordex-cmip5`, `emd`.

### Checking what is installed

```bash
esgvoc status
```

### Keeping vocabularies up to date

```bash
# Check for newer versions (no download)
esgvoc update --check

# Download and activate the latest for all installed projects
esgvoc update
```

### Offline use

If you have no internet access, you can still activate any version that has already
been downloaded:

```bash
# List locally installed versions (no network needed)
esgvoc list cmip7

# Activate one
esgvoc use cmip7@v2.0.0
```

## Requirements

- **Python Version**: 3.12 or higher.
- **No additional system dependencies**: interaction with the library is entirely Python-based, with no other external dependencies like SQLite.

---

This introduction covers the general purpose and installation of `ESGVOC`. In the next sections, we will dive deeper into its functionality, including the Python API and CLI usage.

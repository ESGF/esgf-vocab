
# Introduction 

`ESGVOC` is a Python library designed to streamline and improve the management of controlled vocabularies used by the Earth System Grid Federation (ESGF) and related projects. By harmonizing data sources and providing both a Python API and a CLI for easy access, `ESGVOC` resolves common issues like inconsistencies, errors, and inefficiencies associated with managing controlled vocabularies.

## Why ESGVOC?


Previously, controlled vocabularies were stored in multiple locations and formats, requiring various software implementations to query and interpret data. This approach introduced challenges, including:

- Errors and inconsistencies across systems.
- Misuse of metadata and data.
- Difficulty in maintaining and updating vocabularies.

`ESGVOC` improves controlled vocabulary management through two main ideas:

1. **Harmonization through a Unified Source**  
   A single, centralized repository — referred to as the "Universe CV" — hosts all controlled vocabularies. Specialized vocabularies for specific projects reference the Universe CV via streamlined lists of IDs. This ensures consistency and eliminates duplication.

2. **A Controlled Vocabulary Library**  
   `ESGVOC` provides a dedicated service for interacting with controlled vocabularies. It enables developers, administrators, and software systems to access vocabularies seamlessly via:
   - A Python API for programmatic interaction.
   - A CLI powered by [Typer](https://typer.tiangolo.com/) for command-line use.

## Installation

You can install `ESGVOC` using modern Python packaging tools or in a virtual environment. Below are the recommended methods:

### Using Rye (preferred)

[Rye](https://rye-up.com/) is recommended for managing dependencies and isolating the library:

```bash
rye add esgvoc
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

Once installed, you can fetch controlled vocabulary data using the following command:

```bash
esgvoc install
```

This command performs the following actions:
- Clones the official repositories.
- Builds a cached SQLite database from the cloned data.

### Offline Use
If there is no internet access, `esgvoc install` will check the `.cache` directory for existing repositories. You can manually copy the repositories into `.cache` to use the library offline.

## Official Controlled Vocabulary repositories

`ESGVOC` primarily uses the following repositories for controlled vocabulary data:

- **Universe CV**: [GitHub Repository](https://github.com/WCRP-CMIP/WCRP-universe/tree/esgvoc)
- **CMIP6 CVs**: [GitHub Repository](https://github.com/WCRP-CMIP/CMIP6_CVs/tree/esgvoc)
- **CMIP6Plus CVs**: [GitHub Repository](https://github.com/WCRP-CMIP/CMIP6Plus_CVs/tree/esgvoc)


```{eval-rst}
.. note::
   the exact data witch is read by ESGVOC is in a specific branch "esgvoc" in those repositories.
```

### Flexibility for other repositories
While designed for these repositories, `ESGVOC` can use other repositories if they are structured correctly.

## Requirements

- **Python Version**: 3.12 or higher.
- **No Additional System Dependencies**: Interaction with the library is entirely Python-based, with no external SQLite dependencies.

---

This introduction covers the general purpose and installation of `ESGVOC`. In the next sections, we will dive deeper into its functionality, including the Python API and CLI usage.

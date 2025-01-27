# ESGVOC Library

ESGVOC is a Python library designed to simplify interaction with controlled vocabularies (CVs) used in climate data projects. It supports querying, caching, and validating terms across various CV repositories like the [Universe](https://github.com/WCRP-CMIP/WCRP-universe/tree/esgvoc) and project-specific repositories (e.g., [CMIP6Plus](https://github.com/WCRP-CMIP/CMIP6Plus_CVs/tree/esgvoc), [CMIP6](https://github.com/WCRP-CMIP/CMIP6_CVs/tree/esgvoc), etc.).

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
  - Validate string values against CV terms (DRS).

---

## Use cases 

The ESGVOC library supports a wide range of use cases, including:

* Caching:
    - Usage without internet access.
    - Downloading CVs to a local archive or database.
    - Updating the local cache.
    - Performing consistency checks between the local cache and remote CV repositories.

* Listing:
    - All data descriptors from the Universe.  
    - All terms of one data descriptor from the Universe.  
    - All available projects.  
    - All collections from a project.  
    - All terms from a project.  
    - All terms of a collection from a project.  

* Searching:
    - Data descriptors in the Universe.
    - Terms in the Universe or Data descriptors.
    - Collections in projects.
    - Terms in collections of projects.

Searching is based on the term id and not its regex nor DRS name. It may be case-sensitive or not, supports wildcards (`%`) and regex.

* DRS Validation:  
    - Terms of a project.  
    - Terms of a collection from a project.  

The validation of a string value is against 


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
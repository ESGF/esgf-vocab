# ESGVOC Library

ESGVOC is a Python library designed to simplify interaction with controlled vocabularies (CVs) used in WCRP climate data projects. It supports querying, caching, and validating terms across various CV repositories like the [universe](https://github.com/WCRP-CMIP/WCRP-universe/tree/esgvoc) and project-specific repositories (e.g., [CMIP6Plus](https://github.com/WCRP-CMIP/CMIP6Plus_CVs/tree/esgvoc), [CMIP6](https://github.com/WCRP-CMIP/CMIP6_CVs/tree/esgvoc), etc.)

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

### Caching

- Usage without internet access.
- Downloading CVs to a local archive or database.
- Updating the local cache.
- Performing consistency checks between the local cache and remote CV repositories.

### Listing

- All data descriptors from the universe.  
- All terms of one data descriptor from the universe.  
- All available projects.  
- All collections from a project.  
- All terms from a project.  
- All terms of a collection from a project.  

### Searching

- Data descriptors in the universe.
- Terms in the universe or data descriptors.
- Collections in projects.
- Terms in collections of projects.

```{eval-rst}
.. note::
  Searching is based on the term id and not its regex nor DRS name. It may be case-sensitive or not, supports wildcards (%) and regex.
```

### DRS validation

- Terms of a project.  
- Terms of a collection from a project.  
- Terms from all projects (cross-validation).

DRS validation is a feature that validates a character string against a vocabulary term. This feature is based on the DRS semantics of the terms, i.e. :
- The drs_name field of a plain term
- Or the regex field of a pattern term.

For composite terms, each part of the term is validated one by one and falls under one or other of the validation conditions described above.

```{eval-rst}
.. note::
  Don't confuse the term identifier (id) with its DRS semantics.
```

### DRS applications

The DRS applications are based on the functionalities described above. They provide
convenient way to check DRS expressions of a project (directory, dataset id and file name)
and also generate expressions from mappings of collections and terms or an
unordered bag of terms.

=======

```{toctree}
:caption: Welcome


user/introduction.md
user/terms.md
user/cached_database.md
user/api.md
user/cli.md
```
```{toctree}
:caption: How to 

how_to/get.rst
how_to/valid.rst
how_to/validate_drs.rst
how_to/generate_drs.rst
```

```{toctree}
:caption: Guides

guides/basics_esgvoc.ipynb
guides/basics_drs.ipynb
```

```{toctree}
:caption: API documentation
:hidden:

api_documentation/universe.md
api_documentation/projects.md
api_documentation/project_specs.md
api_documentation/data_descriptors.md
api_documentation/drs.md
api_documentation/jsg.md
api_documentation/miscellaneous.md
```

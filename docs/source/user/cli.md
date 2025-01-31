
# Command Line Interface (CLI)

## Overview

The `ESGVOC` CLI provides a command-line interface for querying and validating controlled vocabularies. It serves as an alternative to the Python API, offering a simple and readable way to access the library's functionality directly from the terminal.

## Installation and access

- The CLI is included as part of the `ESGVOC` Python library. Once the library is installed, the CLI becomes available.
- To view available commands and usage information, use the help command:

```bash
esgvoc --help
```

## Command syntax

The CLI uses a structured syntax based on a colon-separated format to define queries. For example:

```bash
esgvoc get cmip6plus:institution_id:ipsl
```

### Understanding `::`
- A double colon `::` represents "universe" as the first empty string (`""`) and "all" for subsequent entries. For example:
  - `esgvoc get ::` retrieves all data descriptors in the universe CV.
  - `esgvoc get cmip6plus::` retrieves all collections for the project `cmip6plus`.

### Case Sensitivity
- **Term IDs are case-sensitive.** For example:
  - `ipsl` (lowercase) refers to the term's ID.
  - `IPSL` (capitalized) refers to the term's `drs_name` (a standardized representation).


- **What can be queried**:
  - You can query `ID` attributes directly, such as `ipsl` or `cmip6plus`.
  - The CLI does not support direct queries for non-ID attributes like `drs_name` (e.g., `IPSL`). These attributes are available in the returned data for informational and validating purposes but cannot be used as query keys.

## Basic commands

### Querying data

The `get` command retrieves data from the vocabulary database, examples:

```bash
# Retrieve all data descriptors in the universe CV
esgvoc get ::

# Retrieve all terms in the "institution" data descriptor
esgvoc get universe:institution:

# Retrieve a specific term in the "institution" data descriptor
esgvoc get universe:institution:ipsl

# Retrieve all collections in a project
esgvoc get cmip6plus::

# Retrieve a specific term in a collection
esgvoc get cmip6plus:institution_id:ipsl

# Retrieve multiple terms
esgvoc get cmip6plus:institution_id:ipsl cmip6plus:institution_id:llnl
```

### Validating data

The `valid` command checks if a string comply with the `drs_name` of a term vocabulary rules, examples:

```bash
# Validate a term in the universe CV
esgvoc valid IPSL ::

# Validate a term in a specific project
esgvoc valid IPSL cmip6plus::

# Validate a term in a specific collection
esgvoc valid IPSL cmip6plus:institution_id:

# Validate multiple terms
esgvoc valid IPSL cmip6plus:institution_id:ipsl
```

## Features and limitations

### Filtering and querying
- **Wildcard patterns and regular expressions**: not currently supported in the CLI but available in the Python API.
- **Attribute-based Filtering**: planned for future releases if required.

### Error handling
- If a term does not exist or is invalid, the CLI provides a clear error or warning in the output table.

### Batch operations
- The CLI supports batch validation or querying by specifying multiple terms in a single command.

## Advanced use cases

- **Scripting and automation**:
  - The CLI supports automation and can be integrated into shell scripts (supports standard input).
  - Results can be piped to other commands or saved to files for further processing.

- **Integration with CI/CD**:
  - The CLI can be included in pipelines to validate terms or verify controlled vocabulary compliance automatically.

## Summary

The `esgvoc` CLI is a lightweight, flexible tool for interacting with controlled vocabularies. It complements the Python API by providing:
- A simple interface for quick queries and validations.
- Readable output for immediate consumption or integration.

For more advanced queries or functionality, the Python API is recommended.

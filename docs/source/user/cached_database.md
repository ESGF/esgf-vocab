
# Database management

## Overview

`ESGVOC` works with **pre-built SQLite databases** served from the official registry
([WCRP-CMIP/esgvoc_registry](https://github.com/WCRP-CMIP/esgvoc_registry)).
Each project (e.g. `cmip7`, `cmip6`, `universe`) has independently versioned databases
following semantic versioning (e.g. `v2.1.0`).

Multiple versions of a project database can coexist on disk. The currently active
version is tracked via a lightweight pointer file per project.

## Storage layout

Databases are stored under the esgvoc home directory:

| Platform | Default location |
|---|---|
| Linux   | `~/.local/share/esgvoc/` |
| macOS   | `~/Library/Application Support/esgvoc/` |
| Windows | `%LOCALAPPDATA%\ipsl\esgvoc\` |

Inside the home directory:

```
~/.local/share/esgvoc/
└── dbs/
    ├── cmip7/
    │   ├── v2.1.0.db          ← downloaded from registry
    │   └── v2.0.0.db          ← older version kept on disk
    ├── cmip7.active.json      ← pointer: {"active": "v2.1.0", "source": "registry"}
    ├── cmip6/
    │   └── v1.3.0.db
    └── cmip6.active.json
```

Set the `ESGVOC_HOME` environment variable to override the home directory, or
`ESGVOC_DB_DIR` to override only the database root.

## Versioning model

Each database file is tagged with a **semantic version** that matches the corresponding
release in the registry. A database file named `v2.1.0.db` contains the vocabulary
as published at that release.

The registry also provides two special aliases:

| Alias | Meaning |
|---|---|
| `latest` | Latest stable release (resolves to a concrete version at download time) |
| `dev-latest` | Latest pre-release / development snapshot |

## Checking installed versions

```bash
# Show active version and source for every installed project
esgvoc status

# Include full filesystem paths
esgvoc status --paths

# List all installed versions for a project
esgvoc list cmip7

# Compare with what the registry offers
esgvoc list cmip7 --available

# Show full registry metadata (size, publish date, compatibility)
esgvoc list-remote cmip7
```

## Updating vocabularies

The `esgvoc update` command checks the registry for a newer stable version and
downloads it if one is available:

```bash
# Check for updates without downloading anything
esgvoc update --check

# Download and activate the latest for all installed projects
esgvoc update

# Update a specific project only
esgvoc update cmip7

# Download but keep the current active version unchanged
esgvoc update cmip7 --no-activate
```

## Removing old versions

Old database files can be removed to reclaim disk space:

```bash
# Remove a specific version
esgvoc remove cmip7@v2.0.0

# Remove all versions for a project
esgvoc remove cmip7 --all
```

## Offline use

All queries (get, valid, DRS) run entirely against the local SQLite database — no
network access is required once a version has been downloaded.

To work offline, activate any already-downloaded version:

```bash
# List what is available locally
esgvoc list cmip7

# Activate a local version (no network)
esgvoc use cmip7@v2.0.0
```

---

The intended purpose of these databases is to provide an efficient and rapid query
system, accessible exclusively through the API or the CLI.

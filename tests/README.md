# Test Suite

## Repos directory (for build tests)

Build tests (`admin_build_db/`) need locally cloned CV repositories.
By default they are looked up in the **parent directory of the project root**
(i.e. the folder that contains `esgf-vocab/` alongside `WCRP-universe/`, `CMIP6_CVs/`, …).
Override with `ESGVOC_REPOS_DIR` if your layout differs.

**bash / zsh**
```bash
export ESGVOC_REPOS_DIR=/path/to/your/repos
```

**fish**
```fish
set -x ESGVOC_REPOS_DIR /path/to/your/repos
```

Tests in that suite are skipped automatically when the repos are not found.

---

## Registry setup (temporary)

The production registry is not yet live. Point to the test registry before running
any test that downloads databases.

**bash / zsh**
```bash
export ESGVOC_REGISTRY_BASE_URL=https://raw.githubusercontent.com/ltroussellier/test_esgvoc_dbs/main
```

**fish**
```fish
set -x ESGVOC_REGISTRY_BASE_URL https://raw.githubusercontent.com/ltroussellier/test_esgvoc_dbs/main
```

Once the production registry is in place this variable will no longer be needed.

---

## Quick reference

```bash
# Default run — fast tests only (slow/build tests excluded)
uv run pytest tests/

# Pure unit tests — no network, no DB required (~1 s)
uv run pytest tests/ -m "not needs_network and not needs_db and not slow"

# All non-slow tests including DB/network (~10 s, downloads DBs on first run)
uv run pytest tests/ -m "not slow"

# DB tests offline — requires DBs pre-installed (see section below)
ESGVOC_OFFLINE=true uv run pytest tests/ -m needs_db

# Slow build tests only (local repos in tests_to_migrate/integration/data_test/repos/)
uv run pytest tests/ -m slow --override-ini="addopts="

# Live network tests only (always hits the registry)
uv run pytest tests/ -m needs_network

# Everything (slow + network + db)
uv run pytest tests/ --override-ini="addopts="

# Coverage report
uv run pytest tests/ --cov=esgvoc --cov-report=term-missing
```

## Markers

| Marker | Meaning | Default |
|---|---|---|
| `needs_db` | Needs project DB files. Downloads on first run; runs offline once installed. | included |
| `needs_network` | Always contacts a live server (registry HTTP, git clone). | included |
| `slow` | Time-expensive — full DB builds, large ingestion (~15 s+ per test). | **excluded** |
| `cvtest` | Legacy CV repo tests. | **excluded** |

## Structure

```
tests/
├── jsonld_handler/     JSON-LD loading, pydantic union models         (no DB)
├── user_fetch_db/      EsgvocHome, UserState, DBFetcher, esgvoc use   (mocked / needs_network x3)
├── admin_build_db/     DBBuilder.build_dev() and build_universe()     (slow / needs_network x1)
├── cli/                esgvoc status, list, remove                    (mocked)
├── python_api/         api.universe, api.projects                     (needs_db)
├── drs/                DRS validator + generator smoke tests          (needs_db)
└── EMD/                EMD model validators                           (no DB)
```

## Pre-installing DBs for offline development

DBs are stored in the default home (`~/.local/share/esgvoc/` on Linux, or
`ESGVOC_HOME` if you have set it).  Install once and the tests pick them up
automatically on every subsequent run — no env var needed.

```bash
# Install once into the default home
uv run esgvoc use universe@v1.0.0
uv run esgvoc use cmip7@v1.0.0

# From now on, needs_db tests run with no network at all
uv run pytest tests/ -m needs_db

# Confirm nothing touches the network
ESGVOC_OFFLINE=true uv run pytest tests/ -m needs_db
```

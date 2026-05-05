Vocabulary Management
#####################

ESGVoc works with **pre-built SQLite databases** downloaded from the official registry
(`WCRP-CMIP/esgvoc_registry <https://github.com/WCRP-CMIP/esgvoc_registry>`_).
Each project database is versioned (e.g. ``v2.1.0``) and can be downloaded, switched,
or removed independently.

Available Projects
==================

The following projects are available in the registry:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - ID
     - Description
   * - ``universe``
     - WCRP Universe (shared vocabulary)
   * - ``cmip7``
     - CMIP7 Controlled Vocabulary
   * - ``cmip6``
     - CMIP6 Controlled Vocabulary
   * - ``cmip6plus``
     - CMIP6Plus Controlled Vocabulary
   * - ``input4mips``
     - input4MIPs Controlled Vocabulary
   * - ``obs4ref``
     - obs4REF Controlled Vocabulary
   * - ``cordex-cmip6``
     - CORDEX-CMIP6 Controlled Vocabulary
   * - ``cordex-cmip5``
     - CORDEX-CMIP5 Controlled Vocabulary
   * - ``emd``
     - EMD Controlled Vocabulary

Downloading and Activating a Version
=====================================

The ``esgvoc use`` command downloads a project database from the registry (if not
already on disk) and activates it:

.. code-block:: bash

   # Download and activate the latest stable version
   esgvoc use cmip7@latest

   # Download and activate a specific version
   esgvoc use cmip7@v2.1.0

   # Download and activate the latest pre-release
   esgvoc use cmip7@dev-latest

   # Activate a version that is already downloaded (no network needed)
   esgvoc use cmip7@v2.0.0

   # Activate the newest installed version (no name required)
   esgvoc use cmip7

Version name resolution:

- ``@latest`` — latest stable release (auto-download)
- ``@dev-latest`` — latest pre-release (auto-download)
- ``@vX.Y.Z`` — exact registry version (auto-download if not present)
- ``@<custom>`` — locally built database (must be installed first via ``esgvoc admin install``)

Checking Current Status
=======================

.. code-block:: bash

   # Show installed projects and active versions
   esgvoc status

   # Show full filesystem paths as well
   esgvoc status --paths

The output lists each project, its active version, how it was sourced (``registry`` or
``local``), and all installed versions.

Listing Installed and Available Versions
========================================

.. code-block:: bash

   # List all installed versions across all projects
   esgvoc list

   # List installed versions for a specific project
   esgvoc list cmip7

   # Also show versions available for download (requires network)
   esgvoc list cmip7 --available

   # Include pre-release versions in the remote listing
   esgvoc list cmip7 --available --pre

   # Show full registry metadata for all known projects
   esgvoc list-remote

   # Show full registry metadata for a specific project
   esgvoc list-remote cmip7

   # Include pre-release versions in the remote listing
   esgvoc list-remote cmip7 --pre

Updating to a Newer Version
============================

.. code-block:: bash

   # Update a specific project to the latest stable version
   esgvoc update cmip7

   # Update all installed projects
   esgvoc update

   # Check for updates without downloading
   esgvoc update --check

   # Download but do not switch the active version
   esgvoc update cmip7 --no-activate

   # Include pre-release versions when checking for updates
   esgvoc update cmip7 --pre

Removing Installed Databases
=============================

.. code-block:: bash

   # Remove a specific version
   esgvoc remove cmip7@v2.0.0

   # Remove all installed versions for a project
   esgvoc remove cmip7 --all

   # Remove without a confirmation prompt
   esgvoc remove cmip7@v2.0.0 --yes

.. warning::
   Removing the active version deactivates the project. Run
   ``esgvoc use <project>@<version>`` afterwards to re-activate another version.

Checking for ESGVoc Software Updates
=====================================

.. code-block:: bash

   # Show the installed esgvoc version
   esgvoc version

   # Check PyPI for a newer esgvoc release
   esgvoc version --check

   # Reset the update-reminder timer
   esgvoc version --reset-reminder

Data Storage Locations
=======================

All project databases are stored under the **esgvoc home directory**:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Platform
     - Default home
   * - Linux
     - ``~/.local/share/esgvoc/``
   * - macOS
     - ``~/Library/Application Support/esgvoc/``
   * - Windows
     - ``%LOCALAPPDATA%\ipsl\esgvoc\``

Inside the home directory:

.. code-block:: text

   ~/.local/share/esgvoc/
   └── dbs/
       ├── cmip7/
       │   ├── v2.1.0.db          ← registry download
       │   └── v2.0.0.db          ← registry download
       ├── cmip7.active.json      ← pointer to the active version
       ├── cmip6/
       │   └── v1.3.0.db
       └── cmip6.active.json

The registry JSON cache (safely deletable) lives in:

- **Linux**: ``~/.cache/esgvoc/``
- **macOS**: ``~/Library/Caches/esgvoc/``
- **Windows**: ``%LOCALAPPDATA%\ipsl\esgvoc\Cache\``

Overriding the Home Directory
------------------------------

Set the ``ESGVOC_HOME`` environment variable to use a custom location:

.. code-block:: bash

   export ESGVOC_HOME=/data/esgvoc
   esgvoc use cmip7@latest

Set ``ESGVOC_DB_DIR`` to override only the database root (leaving the rest of the
home directory at its default location):

.. code-block:: bash

   export ESGVOC_DB_DIR=/fast-disk/esgvoc/dbs
   esgvoc status

Common Workflows
================

First-Time Setup
----------------

.. code-block:: bash

   # Download and activate the vocabulary sets you need
   esgvoc use universe@latest
   esgvoc use cmip7@latest
   esgvoc use cmip6@latest

   # Verify everything is in order
   esgvoc status

Working with Multiple Versions
-------------------------------

.. code-block:: bash

   # Download two versions of cmip7
   esgvoc use cmip7@v2.0.0
   esgvoc use cmip7@v2.1.0

   # List what is installed
   esgvoc list cmip7

   # Switch between them
   esgvoc use cmip7@v2.0.0
   esgvoc use cmip7@v2.1.0

Keeping Vocabularies Up to Date
---------------------------------

.. code-block:: bash

   # Check whether updates are available (no download)
   esgvoc update --check

   # Download and activate the latest for all installed projects
   esgvoc update

Cleaning Up Old Versions
-------------------------

.. code-block:: bash

   # List what is installed
   esgvoc list cmip7

   # Remove a version you no longer need
   esgvoc remove cmip7@v2.0.0

   # Remove all versions and start fresh
   esgvoc remove cmip7 --all --yes
   esgvoc use cmip7@latest

Advanced: Using Locally Built Databases
========================================

CV maintainers and developers can build their own databases and install them locally.
See the ``esgvoc admin`` subcommand group:

.. code-block:: bash

   # Build a project database from local repos (dev mode)
   esgvoc admin build \
       --project-path ./CMIP7-CVs \
       --universe-path ./WCRP-universe \
       --project-id cmip7 \
       --cv-version dev \
       --universe-version dev \
       --output cmip7.db

   # Install the locally built database
   esgvoc admin install cmip7 ./cmip7.db --name my-experiment

   # Activate it
   esgvoc use cmip7@my-experiment

   # Validate a database file
   esgvoc admin validate cmip7.db

   # Compare two database files
   esgvoc admin diff v2.0.0.db v2.1.0.db

For the full ``esgvoc admin`` reference run ``esgvoc admin --help``.

Troubleshooting
===============

No Projects Installed
---------------------

.. code-block:: bash

   esgvoc status
   # "No projects installed."

   # Fix: download at least one project
   esgvoc use cmip7@latest

Version Not Found
-----------------

.. code-block:: bash

   # Check what versions exist in the registry
   esgvoc list-remote cmip7

   # Or list what is already installed
   esgvoc list cmip7

Network Errors
--------------

If you cannot reach the registry, activate an already-downloaded version:

.. code-block:: bash

   # List locally installed versions (no network needed)
   esgvoc list cmip7

   # Activate one
   esgvoc use cmip7@v2.0.0

Overriding the Registry URL
----------------------------

For testing or enterprise setups, override the registry base URL:

.. code-block:: bash

   export ESGVOC_REGISTRY_BASE_URL=https://raw.githubusercontent.com/my-org/my-registry/main
   esgvoc use cmip7@latest

Configuration
#############

The configuration system allows you to manage different project setups and easily switch between them. Each configuration defines which projects are active and where their repositories and databases are stored.

Understanding Configurations
============================

A configuration contains:

- **Universe settings**: Global WCRP vocabulary repository settings
- **Project settings**: Individual project repositories (CMIP6, Input4MIPs, etc.)

Default Projects Available
==========================

ESGVoc comes with several pre-configured projects that can be easily added:

- **cmip6**: CMIP6 Controlled Vocabularies
- **cmip6plus**: CMIP6Plus Controlled Vocabularies  
- **input4mip**: Input4MIPs Controlled Vocabularies
- **obs4mip**: Obs4MIPs Controlled Vocabularies
- **cordex-cmip6**: CORDEX-CMIP6 Controlled Vocabularies

Basic Configuration Commands
============================

Viewing Available Projects
--------------------------

.. code-block:: bash

   # Show all available projects and their status in current config
   esgvoc config avail

   # Check projects in a specific configuration
   esgvoc config avail --config my_config

This displays a table showing which projects are active (✓) and which are available to add (○).

Creating Empty Configurations
-----------------------------

.. code-block:: bash

   # Create empty configuration and switch to it
   esgvoc config init minimal_setup

   # Create empty configuration but stay on current one
   esgvoc config init test_config --no-switch

An empty configuration contains only universe settings with no projects, allowing you to add projects selectively.

Adding Projects
---------------

.. code-block:: bash

   # Add single project to current configuration
   esgvoc config add input4mip

   # Add multiple projects at once
   esgvoc config add input4mip obs4mip cordex-cmip6

   # Add projects to specific configuration
   esgvoc config add cmip6 --config production

When you add projects:

1. The project is added to the configuration using default settings
2. The project's controlled vocabularies are automatically downloaded
3. Local repositories and databases are set up

.. note::
   Projects that already exist in the configuration will be skipped with a warning.

Removing Projects
-----------------

.. code-block:: bash

   # Remove single project (with confirmation)
   esgvoc config rm input4mip

   # Remove multiple projects at once
   esgvoc config rm input4mip obs4mip cordex-cmip6

   # Remove without confirmation prompt
   esgvoc config rm input4mip --force

   # Remove from configuration but keep local files
   esgvoc config rm input4mip --keep-files

When you remove projects:

1. The project is removed from the configuration
2. Local repository directory is deleted (unless ``--keep-files``)
3. Database file is deleted (unless ``--keep-files``)

.. warning::
   By default, removing a project deletes all its local files. Use ``--keep-files`` if you want to preserve the downloaded data.

Advanced Configuration Management
=================================

Listing Configurations
----------------------

.. code-block:: bash

   # List all available configurations
   esgvoc config list

   # Show current configuration content
   esgvoc config show

   # Show specific configuration content
   esgvoc config show my_config

Creating New Configurations
---------------------------

.. code-block:: bash

   # Create configuration based on default settings
   esgvoc config create production

   # Create configuration based on existing one
   esgvoc config create test --base production

   # Create and immediately switch to it
   esgvoc config create development --switch

Switching Configurations
------------------------

.. code-block:: bash

   # Switch to different configuration
   esgvoc config switch production

   # Check which configuration is currently active
   esgvoc config list

Managing Project Settings
-------------------------

.. code-block:: bash

   # List projects in current configuration
   esgvoc config list-projects

   # List projects in specific configuration
   esgvoc config list-projects --config production

   # Update project repository URL
   esgvoc config update-project cmip6 --repo https://github.com/new/repo

   # Update project branch
   esgvoc config update-project cmip6 --branch new_branch

   # Update multiple settings at once
   esgvoc config update-project cmip6 --repo https://github.com/new/repo --branch main

Manual Configuration Editing
-----------------------------

.. code-block:: bash

   # Edit current configuration in default editor
   esgvoc config edit

   # Edit specific configuration
   esgvoc config edit production

   # Use specific editor
   esgvoc config edit --editor nano

   # Modify settings via command line
   esgvoc config set 'universe:branch=esgvoc_dev'
   esgvoc config set 'cmip6:github_repo=https://github.com/new/cmip6'

Removing Configurations
-----------------------

.. code-block:: bash

   # Remove configuration (with confirmation)
   esgvoc config remove test_config

.. note::
   You cannot remove the "default" configuration, and removing the active configuration will automatically switch you to the default one.

Configuration Workflows
========================

Setting Up a Development Environment
------------------------------------

.. code-block:: bash

   # Create empty development configuration
   esgvoc config init dev

   # Add only the projects you need
   esgvoc config add cmip6 input4mip

   # Check what's active
   esgvoc config avail

Setting Up Multiple Project Environments
----------------------------------------

.. code-block:: bash

   # Create minimal configuration for CMIP6 only
   esgvoc config init cmip6_only
   esgvoc config add cmip6

   # Create full configuration with all projects
   esgvoc config init full_setup
   esgvoc config add cmip6 cmip6plus input4mip obs4mip cordex-cmip6

   # Switch between them as needed
   esgvoc config switch cmip6_only
   esgvoc config switch full_setup

Cleaning Up Old Projects
------------------------

.. code-block:: bash

   # Check what projects are currently active
   esgvoc config avail

   # Remove projects no longer needed (keeps files)
   esgvoc config rm obs4mip cordex-cmip6 --keep-files

   # Or remove completely including files
   esgvoc config rm obs4mip cordex-cmip6

Configuration File Location
===========================

Configuration files are stored in platform-specific directories:

- **Linux**: ``~/.config/esgvoc/``
- **macOS**: ``~/Library/Application Support/esgvoc/``  
- **Windows**: ``%APPDATA%\\esgvoc\\``

The main registry file (``config_registry.toml``) tracks all configurations and which one is active.

Troubleshooting
===============

Configuration Not Found
-----------------------

If you get "Configuration not found" errors:

.. code-block:: bash

   # List available configurations
   esgvoc config list

   # Switch to default if needed
   esgvoc config switch default

Project Already Exists
----------------------

When adding projects that already exist:

.. code-block:: bash

   # Check current projects
   esgvoc config list-projects

   # Check all available projects and their status
   esgvoc config avail

Reset to Clean State
--------------------

To start fresh:

.. code-block:: bash

   # Create new empty configuration
   esgvoc config init fresh --no-switch

   # Remove old configuration
   esgvoc config remove old_config

   # Switch to clean setup
   esgvoc config switch fresh
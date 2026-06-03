Valid Global Attributes
#######################

The ``ncattvalid`` application validates NetCDF global attributes against ESGVOC controlled vocabularies and project specifications.

It can validate:

* a single attribute/value pair
* a full NetCDF header

This helps ensure that NetCDF files comply with CMIP metadata conventions and ESGVOC project specifications.

One Attribute
=============

.. tabs::

    .. tab:: Command line interface

        .. code-block:: bash

            esgvoc ncattvalid cmip6 activity_id CMIP
        
        .. code-block:: bash
        
            esgvoc ncattvalid cmip6 experiment_id historical

        .. image:: ../_static/CLI_Valid_attr_one.png

        .. note::

            This mode validates a single NetCDF global attribute value
            against the project's controlled vocabulary.

    .. tab:: API as python lib

        .. code-block:: python

            from esgvoc.apps.ncattvalid.validator import GAValidator

            validator = GAValidator(project_id="cmip6")

            result = validator.validate_one(
                "activity_id",
                "CMIP",
            )

        .. image:: ../_static/API_Valid_attr_one.png

        .. note::

            ``validate_one`` returns an ``AttributeResult`` object.

Validate a Full NetCDF Header
=============================

.. tabs::

    .. tab:: Command line interface

        Validate from stdin:

        .. code-block:: bash

            ncdump -h file.nc | esgvoc ncattvalid cmip6

        Validate from a file:

        .. code-block:: bash

            esgvoc ncattvalid cmip6 --file header.txt

        Verbose mode:

        .. code-block:: bash

            esgvoc ncattvalid cmip6 --file header.txt --verbose

        .. image:: ../_static/CLI_Valid_attr_header.png

        .. note::

            The input must be the output of:

            .. code-block:: bash

                ncdump -h file.nc
    
            and contain a ``// global attributes:`` section to be parsed.

    .. tab:: API as python lib

        .. code-block:: python

            from esgvoc.apps.ncattvalid.validator import GAValidator

            validator = GAValidator(project_id="cmip6")

            with open("header.txt") as f:
                report = validator.validate_ncdump(f.read())

        .. image:: ../_static/API_Valid_attr_header.png

        .. note::

            ``validate_ncdump`` returns a ``GAReport`` object.

Validation Report
=================

The validation report may contain:

* ✅ valid attributes
* ❌ invalid attributes
* ❓ missing required attributes
* ➕ extra attributes not defined in the project specification

Example output:

.. code-block:: text

    ───────────────── Validation failed ─────────────────

    File: test.nc
    Project: cmip6

    ╭─ Invalid attributes ──────────────────────────────╮
    │ ❌ activity_id='WRONG'                            │
    │    'WRONG' not found in collection 'activity_id'  │
    ╰───────────────────────────────────────────────────╯

    ╭─ Missing required attributes ─────────────────────╮
    │ ❓ experiment_id                                  │
    ╰───────────────────────────────────────────────────╯

Error Handling
==============

Invalid or incomplete ``ncdump`` input raises an error.

Possible errors include:

* missing ``// global attributes:`` section
* malformed attribute definitions
* unknown NetCDF attributes
* invalid controlled vocabulary values

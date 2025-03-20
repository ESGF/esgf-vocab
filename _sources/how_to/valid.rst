Valid
#####

The command valid check if a string input correspond to a term drs_name attribute or not. This feature can be use in CLI and API.

Knowing the term id:
====================

.. tabs::

   .. group-tab:: Command line interface

      .. code-block:: bash

        esgvoc valid IPSL cmip6:institution_id:ipsl

      .. image:: ../_static/CLI_Valid_term.png


      .. note::
         `IPSL` is the drs_name of the term with id `ipsl` therefore the valid command return "True".

   .. group-tab:: API as python lib

      .. code-block:: python

         import esgvoc.api as ev

         ev.valid_term("IPSL","cmip6","institution_id","ipsl")

      .. image:: ../_static/API_Valid_Term.png

      .. note::
         The API returns a DrsValidationReport Object. The __str__ dunder function reports errors if any. The __bool__ dunder function permits to use result in if statement.


Knowing the only the collection id:
===================================


.. tabs::

   .. group-tab:: Command line interface

      .. code-block:: bash

        esgvoc valid IPSL cmip6:institution_id:

      .. image:: ../_static/CLI_Valid_collection.png


      .. note::
         This command looks for the drs_name in every term in the specified collection.

   .. group-tab:: API as python lib

      .. code-block:: python

         import esgvoc.api as ev

         ev.valid_term_collection("IPSL","cmip6","institution_id")

      .. image:: ../_static/API_Valid_collection.png

      .. note::
         The function `ev.valid_term_collection` returns a list of MatchingTerm.


Knowing the only the project id:
================================


.. tabs::

   .. group-tab:: Command line interface

      .. code-block:: bash

        esgvoc valid IPSL cmip6::

      .. image:: ../_static/CLI_Valid_project.png

      .. note::
         This command looks for the drs_name in every term in the specified project. Therefore, it could be pretty long compared to the above functions.

   .. group-tab:: API as python lib

      .. code-block:: python

         import esgvoc.api as ev

         ev.valid_term_project("IPSL","cmip6")

      .. image:: ../_static/API_Valid_project.png

      .. note::
         The function `ev.valid_term_project` returns a list of MatchingTerm.

Find it in all known projects
=============================


.. tabs::

   .. group-tab:: Command line interface

      .. code-block:: bash

        esgvoc valid IPSL ::

      .. image:: ../_static/CLI_Valid_all_project.png

      .. note::
         This command looks for the drs_name in every project. Therefore, it could be pretty long compared to the above functions.

   .. group-tab:: API as python lib

      .. code-block:: python

         import esgvoc.api as ev

         ev.valid_term_in_all_projects("IPSL")

      .. image:: ../_static/API_Valid_all_project.png

      .. note::
         The function `ev.valid_term_in_all_projects` returns a list of MatchingTerm.

Describe
########

Model of a universe data descriptor
====================================

.. tabs::

   .. group-tab:: Command line interface

      .. code-block:: bash

        esgvoc describe source

      This shows all variants of the ``source`` data descriptor (e.g. ``SourceCMIP7``, ``SourceLegacy``)
      with their fields, types, and docstrings.

      .. code-block:: bash

        esgvoc describe frequency

      For data descriptors with a single model, shows that model directly.

   .. group-tab:: API as python lib

      .. code-block:: python

         import esgvoc.api as ev

         # Returns the pydantic class (or union type for multi-variant descriptors)
         model = ev.get_model_from_data_descriptor("source")
         print(model)  # Source (union of SourceCMIP7, SourceLegacy)

         model = ev.get_model_from_data_descriptor("frequency")
         print(model)  # <class 'Frequency'>
         print(model.__doc__)
         print(model.model_fields)


Model of a project collection
==============================

.. tabs::

   .. group-tab:: Command line interface

      .. code-block:: bash

        esgvoc describe cmip7 experiment

      This returns the concrete variant used by the project (e.g. ``ExperimentCMIP7``),
      not the union type.

   .. group-tab:: API as python lib

      .. code-block:: python

         import esgvoc.api as ev

         # Returns the concrete pydantic class for this project's collection
         model = ev.get_model_from_collection("cmip7", "experiment")
         print(model)           # <class 'ExperimentCMIP7'>
         print(model.__doc__)   # docstring
         print(model.model_fields)  # field metadata

      .. note::
              For data descriptors with multiple variants (e.g. ``Source`` has ``SourceCMIP7`` and ``SourceLegacy``),
              ``get_model_from_collection`` resolves the specific variant used by the project.
              Use ``get_model_from_data_descriptor`` on the universe side to get the union type.


All models for a project
=========================

.. tabs::

   .. group-tab:: Command line interface

      .. code-block:: bash

        esgvoc describe cmip7

      Lists every collection in the project alongside the pydantic model it resolves to.

   .. group-tab:: API as python lib

      .. code-block:: python

         import esgvoc.api as ev

         collections = ev.get_all_collections_in_project("cmip7")
         for coll in collections:
             model = ev.get_model_from_collection("cmip7", coll)
             print(f"{coll} -> {model.__name__ if model else 'unresolved'}")

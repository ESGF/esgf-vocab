Get
###

One term
========

.. tabs::

   .. group-tab:: Command line interface

      .. code-block:: bash

        esgvoc get universe:institution:ipsl

      .. image:: ../_static/one_term.png
        
      
      .. note::
        it is possible to ask multiple term with the same command : 
        `esgvoc get universe:institution:llnl`
        

   .. group-tab:: API as python lib

      .. code-block:: python

         import esgvoc.api as ev
            
         ev.find_terms_in_data_descriptor(data_descriptor_id="institution", term_id="ipsl")
         ev.find_terms_in_universe(term_id="ipsl") # same result but slower (still fast)
      .. image:: ../_static/Jup_one_term.png
        

All terms from one datadescriptor/collection
===========================================


.. tabs::

   .. group-tab:: Command line interface

        .. code-block:: bash

                esgvoc get universe:institution:

        .. image:: ../_static/all_term_from_one_collection.png
        
      
        .. note::
                it is possible to ask multiple term with the same command :

                `esgvoc get universe:institution: cmip6:institution_id: cmip6:grid_label`
        

   .. group-tab:: API as python lib

        .. code-block:: python

                import esgvoc.api as ev
            
                ev.get_all_terms_in_data_descriptor("institution")
                ev.get_all_terms_in_collection("cmip6","institution_id")

        .. image:: ../_static/Jup_terms_from_one_dd.png

        .. image:: ../_static/Jup_terms_from_one_collection.png

        .. note:: 
                a `datadescriptor` is the equivalent collection for the universe.

                the final informations are contained in datadescriptors, collection terms are link to their datadescriptors with optional additionnal information.


A term from a CV 
================

.. tabs::

   .. group-tab:: Command line interface

        .. code-block:: bash

                esgvoc get universe::ipsl
                esgvoc get cmip6::ipsl

        .. image:: ../_static/one_term_from_one_cv.png
        
      
        .. note::
                the term `ipsl` is the same in cmip6 (institution_id) and in universe (institution) since the cmip6 one is a link to the universe one: 

                try the one from cmip6plus : `esgvoc get cmip6plus::ipsl. To showcase the possibility to add information in project CV term. We added a 'myprop' attribute in this term in cmip6plus CV.

   .. group-tab:: API as python lib

        .. code-block:: python

                import esgvoc.api as ev
            
                ev.find_terms_in_universe("ipsl")
                ev.find_terms_in_project("cmip6","ipsl")
                ev.find_terms_in_project("cmip6plus","ipsl")

        .. image:: ../_static/Jup_one_term_from_one_CV.png

        .. note:: 
                the term `ipsl` is the same in cmip6 (institution_id) and in universe (institution) since the cmip6 one is a link to the universe one: 

                try the one from cmip6plus : `esgvoc get cmip6plus::ipsl. To showcase the possibility to add information in project CV term. We added a 'myprop' attribute in this term in cmip6plus CV.





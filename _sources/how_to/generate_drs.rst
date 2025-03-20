Generate DRS
############

The Data Reference Syntax (DRS) of the World Climate Research Programme's (WCRP) Coupled Model Intercomparison Project (CMIP) is a standardized framework for organizing, naming, and accessing climate model output data. It ensures consistency across the distributed CMIP archives, enabling efficient data discovery, citation, and interoperability.


The DRS defines rules for structuring **file_name**, **directory** paths, **dataset** naming and metadata attributes in CMIP datasets.



From mapping collection:term drs_name
=====================================

.. tabs::

   .. group-tab:: Command line interface

      .. code-block:: bash

        Not available with CLI.


   .. group-tab:: API as python lib

      .. code-block:: python

        from esgvoc.apps.drs.generator import DrsGenerator
        generator = DrsGenerator(project_id="cmip6plus")
        m_map = {
            'member_id': 'r2i2p1f2',
            'activity_id': 'CMIP',
            'source_id': 'MIROC6',
            'mip_era': 'CMIP6Plus',
            'experiment_id': 'amip',
            'variable_id': 'od550aer',
            'table_id': 'ACmon',
            'grid_label': 'gn',
            'institution_id': 'IPSL'
        }
        generator.generate_file_name_from_mapping(m_map)
        generator.generate_dataset_id_from_mapping(m_map)
        generator.generate_directory_from_mapping(m_map)


      .. image:: ../_static/API_drsgen_map.png

      .. note::
        Those functions return a DrsGenerationReport object that can be use to know more about the generation.





From a bag of drs_name
======================


.. tabs::

   .. group-tab:: Command line interface

      .. code-block:: bash

        esgvoc drsgen cmip6plus filename 'r2i2p1f2 CMIP MIROC6 CMIP6Plus amip od550aer ACmon gn IPSL'
        esgvoc drsgen cmip6plus directory 'r2i2p1f2 CMIP MIROC6 CMIP6Plus amip od550aer ACmon gn IPSL'
        esgvoc drsgen cmip6plus dataset 'r2i2p1f2 CMIP MIROC6 CMIP6Plus amip od550aer ACmon gn IPSL'

      .. image:: ../_static/CLI_drsgen_frombag.png

      .. note::
        The command `esgvoc drsgen` supports piped and redirected standard input.

   .. group-tab:: API as python lib

      .. code-block:: python

        from esgvoc.apps.drs.generator import DrsGenerator
        generator = DrsGenerator(project_id="cmip6plus")

        m_bag = ['r2i2p1f2','CMIP','MIROC6','CMIP6Plus', 'amip','od550aer', 'ACmon', 'gn','IPSL']
        generator.generate_file_name_from_bag_of_terms(m_bag)
        generator.generate_directory_from_bag_of_terms(m_bag)
        generator.generate_dataset_id_from_bag_of_terms(m_bag)

      .. image:: ../_static/API_drsgen_frombag.png

      .. note::
        Those functions return a DrsGenerationReport object that can be use to know more about the generation.

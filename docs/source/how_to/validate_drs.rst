Valid DRS
#########

The Data Reference Syntax (DRS) of the World Climate Research Programme's (WCRP) Coupled Model Intercomparison Project (CMIP) is a standardized framework for organizing, naming, and accessing climate model output data. It ensures consistency across the distributed CMIP archives, enabling efficient data discovery, citation, and interoperability.


The DRS defines rules for structuring **file_name**, **directory** paths, **dataset** naming and metadata attributes in CMIP datasets.



One DRS
=======

.. tabs::

   .. group-tab:: Command line interface

      .. code-block:: bash

        esgvoc drsvalid cmip6plus directory CMIP6Plus/CMIP/NCC/MIROC6/amip/r2i2p1f2/ACmon/od550aer/gn/v20190923
        esgvoc drsvalid cmip6plus filename od550aer_ACmon_MIROC6_amip_r2i2p1f2_gn.nc
        esgvoc drsvalid cmip6plus dataset CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn

      .. image:: ../_static/CLI_drsvalid_one.png


      .. note::
        Those are basic use of drsvalid.
        More examples are described later in this documentation.

   .. group-tab:: API as python lib

      .. code-block:: python

        from esgvoc.apps.drs.validator import DrsValidator
        validator = DrsValidator(project_id="cmip6plus") #instanciate

        validator.validate_file_name(drs_expression="od550aer_ACmon_MIROC6_amip_r2i2p1f2_gn.nc")
        validator.validate_directory(drs_expression="CMIP6Plus/CMIP/NCC/MIROC6/amip/r2i2p1f2/ACmon/od550aer/gn/v20190923")
        validator.validate_dataset_id(drs_expression="CMIP6Plus.CMIP.IPSL.MIROC6.amip.r2i2p1f2.ACmon.od550aer.gn")

      .. image:: ../_static/API_drsvalid_one.png

      .. note::
        Those functions return a DrsValidationReport object that can be use to know more about the validation.

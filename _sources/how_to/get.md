# Get Feature 


## Get Universe DataDescriptor 



```{eval-rst}
.. tabs::

   .. tab:: Command line interface

      .. code-block:: bash

        esgvoc get universe:institution:ipsl
      
      .. note::
         
        

   .. tab:: API as python lib

      .. code-block:: python

         import esgvoc.api as ev
            
         ev.find_terms_in_data_descriptor(data_descriptor_id="institution", term_id="ipsl")
         ev.find_terms_in_universe(term_id="ipsl") # same result but slower (still fast)
```

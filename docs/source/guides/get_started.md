# Get Started


## ESGF-VOC use cases 


the esgvoc library supports a wide range of use cases, including:
* Caching:
Usage without internet access.
Downloading CVs to a local archive or database.
Updating the local cache.
Performing consistency checks between the local cache and remote CV repositories.

* Listing:
All data descriptors from the Universe.  
All terms of one data descriptor from the Universe.  
All available projects.  
All collections from a project.  
All terms from a project.  
All terms of a collection from a project.  

* Validation:
Validating an input string against:  
All terms of the Universe.  
All terms of a data descriptor from the Universe.  
All terms of a project.  
All terms of a collection from a project.  
All terms from all projects (cross-validation).  
Validation may be case-sensitive or case-insensitive.  
Wildcards can be used in validation queries.  
The system can return one or several valid terms, as well as similar terms if exact matches are not found.

## Installation

### Library

```bash
pip install esgvoc
```

### Vocabularies

Right after ESG-VOC installation, the vocabularies can be installed following this command:

```bash
esgvoc install
```
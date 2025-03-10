# ESGVOC API

## Overview

The ESGVOC Python API provides a powerful and read-only interface to query controlled vocabularies. Users can retrieve, search, and validate vocabulary terms programmatically using a clean and intuitive API.

## Key features

The API offers three main types of functions:

1. **Retrieve functions (`get_*`)**
   - Fetch collections, terms, or data descriptors.
   - Examples:
     - Retrieve all data descriptors in the universe CV.
     - Retrieve all terms within a specific collection or project.

2. **Search functions (`find_*`)**
   - Search for terms based on input strings.
   - Examples:
     - Search for a specific term in a data descriptor.
     - Search for terms within a project or collection.

3. **Validation functions (`valid_*`)**
   - Validate the compliance of an input string with controlled vocabulary rules (i.e., DRS name).
   - Examples:
     - Check if a term is valid within a collection.
     - Check if a term is valid within a project.

## Example usage

Below are some examples of how to use the API. For complete documentation, refer to the API documentation or the [Notebook Guide](https://esgf.github.io/esgf-vocab/guides/basics_esgvoc.html).

```python
import esgvoc.api as ev

# Retrieve Functions
ev.get_all_data_descriptors_in_universe()
ev.get_all_terms_in_data_descriptor(data_descriptor_id="activity")

ev.get_all_projects()
ev.get_all_collections_in_project(project_id="cmip6plus")
ev.get_all_terms_in_collection(project_id="cmip6plus", collection_id="activity_id")

# Search Functions
ev.find_terms_in_data_descriptor(data_descriptor_id="activity", term_id="aerchemmip")
ev.find_terms_in_universe(term_id="aerchemmip")
ev.find_terms_in_collection(project_id="cmip6plus", collection_id="activity_id", term_id="cmip")

# Validation Functions
ev.valid_term_in_collection(value="ipsl", project_id="cmip6plus", collection_id="institution_id")
ev.valid_term_in_project(value="some_term", project_id="cmip6plus")
```

## Structured data with Pydantic models

One of the key benefits of using this library is that the returned terms are Pydantic objects representing the requested terms. This provides several advantages:

### Structured data
Each term is encapsulated in a well-defined Pydantic model, ensuring that the data is structured and adheres to a defined schema.

### Ease of integration
Since Pydantic objects are Python-native and compatible with many frameworks, the terms can be seamlessly integrated into third-party software, such as:
- **Web Frameworks**: Using terms directly in APIs or web applications (e.g., FastAPI, Django).
- **Data Pipelines**: Injecting validated terms into ETL workflows or analytics systems.
- **Configuration Management**: Mapping terms into application configurations or schemas.

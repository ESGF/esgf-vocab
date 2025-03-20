# Controlled vocabulary

## Data Descriptor

Climate modeling data relies on various informational elements to organize, index, and document simulations. Although these metadata may have different names, the latters are grouped according to their consistency. These groups are referred here as Data Descriptors. Each Data Descriptor represents a subset of information with a common definition across all climate simulations. For example, the "experiment" Data Descriptor provides details about the experimental protocol of a numerical simulation. Each Data Descriptor serves as a structured representation of a specific type of information, defining the necessary keys (or attributes) to characterize this information. Each Data Descriptor is implemented as a Pydantic model to ensure compliance across different instances of that model, called terms. For instance, the "experiment" Data Descriptor requires attributes such as an identifier (id), a category (type), an official typographic name (drs_name), a description, etc. The structure of these models varies depending on its semantic.

## Term

A term is a possible word or a element within a Data Descriptor of the vocabulary. Technically, a term corresponds to an instance of a Data Descriptor, adhering to its Pydantic model. Thus, a term is a unique set of key-value pairs within the same Data Descriptor.
There are three categories of terms:
- Plain terms: These are manually defined with a fixed syntax (e.g., institutions, physical variables, etc.) The set of plain terms is finite, as it includes only those explicitly described by the vocabulary authors.
- Pattern-based terms: These terms follow predefined patterns, typically described using regular expressions, and can potentially form infinite sets (e.g., dates, time periods, etc.)
- Composite terms: These are terms constructed from other terms (with possible recursion). They may be decomposable using textual separators (e.g., a period consists of two dates separated by a - symbol).

## Universe

Each term is represented as a JSON file. The JSON files for all terms belonging to the same Data Descriptor are organized within a dedicated folder, hosted on a dedicated WCRP GitHub [repository](https://github.com/WCRP-CMIP/WCRP-universe/tree/esgvoc). This repository, also called "universe", contains the complete set of possible terms. The universe repository serves to structure and harmonize all possible terms independently of specific projects in which they are used. The terms of the universe are in a way factorized for the WCRP projects in order to avoid any divergence and hence the controlled nature of the vocabularies.

## Collection

A Collection is a subset of a Data Descriptor. It is a list that references terms from the same Data Descriptor using their identifiers. Consequently, a collection cannot contain terms from multiple Data Descriptors. Each collection follows the same Pydantic model as the Data Descriptor it corresponds. Additionally, for any referenced term, a collection may override the original information by adding new key-value pairs or modifying existing ones in the JSON structure.


```{eval-rst}
.. note::
  The terms of the universe and the projects are identical. Only any changes introduced by the projects may differentiate them.
```

## Project

A project is defined by a set of collections, where each collection is stored as a JSON file. All collections belonging to the same project are hosted in a dedicated WCRP GitHub repository, separate from the universe one (e.g., [CMIP6](https://github.com/WCRP-CMIP/CMIP6_CVs/tree/esgvoc) and [CMIP6Plus](https://github.com/WCRP-CMIP/CMIP6Plus_CVs/tree/esgvoc)). Each project selects terms from the universe to build an operational vocabulary that is actively used in climate data. A project is also defined by its Data Reference Syntax (DRS), which specifies the file structure, dataset ID templates, and file naming conventions. These syntactic rules are documented in a JSON file located at the root of the project’s GitHub repository.

## ESGVOC

The purpose of the ESGVOC library is to parse json files of terms from the universe and projects, and cache them (SQLite) in order to respond to listing, search and DRS validation queries.

# Controlled vocabulary

## Universe and CMIP projects

### Organization

The terms are organized on two levels: the ‘universe’ terms and the project terms ([CMIP](https://wcrp-cmip.org/) exercises: intercomparison of climate simulations). The terms of the universe are in a way factorized for the projects ([CMIP6](https://github.com/WCRP-CMIP/CMIP6_CVs/tree/esgvoc), [CMIP6Plus](https://github.com/WCRP-CMIP/CMIP6Plus_CVs/tree/esgvoc) and now CMIP7, which is just starting up), in order to avoid any divergence, hence the controlled nature of the vocabularies.

Each project just pick terms from the universe to create an operational vocabulary (i.e. one that is actually used in climate data). They may modify some of them (addition of new json key/value pairs or changes to the json key value, only). As only a handful of experts can modify these terms, the vocabularies/projects remain under control.

### Terms

The terms of the universe are json files, grouped together in directories called data descriptors (DD), in a coherent manner. Examples of DDs: variables (physical), experiments (numerical simulation), etc. Each DD is accompanied by a Pydantic term model, to ensure compliance with a term schema. The models differ depending on the DD. The term ids are unique within the DDs, but not necessarily from one DD to another, and of course from a project to another.

Project terms (CMIP6Plus and CMIP6, which is currently being developed) are grouped together in collections, which have the same semantics as the DDs, except that the names of the collections are generally not the same as those of the DDs, for historical reasons. Collections are also directories that contain terms in the form of json files. These contain just the information needed to reference a term in the universe and any modifications that we call overloading, like in the computer programming.

```{eval-rst}
.. note::
  The terms of the universe and the projects are identical. Only any changes introduced by the projects may differentiate them.
```

### Kind of terms

There are three kinds of terms in the universe and projects:
- The plain terms.
- The pattern terms.
- The composite terms.

Plain terms are terms whose syntax is hand written (e.g. institutions, physical variables, etc.) The set of plain terms is finite, as there are as many as the authors of the vocabularies have been able to describe. In contrast, pattern terms are described by regular expressions which potentially describe non-finite sets (e.g. dates, periods, etc.). Finally, composite terms are terms constructed from other terms (including composite terms). These terms may or may not be decomposed by textual separators (e.g. a period is made up of two dates separated by a `-` symbol).

## ESGVOC

The purpose of the ESGVOC library is to parse json files of terms from the universe and projects, and cache them (SQLite) in order to respond to listing, search and DRS validation queries.

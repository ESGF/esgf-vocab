# CLI commands

## esgvoc --help

## esgvoc install
to get the latest CVs
currently, only CMIP6Plus_CV is supported
## esgvoc status
to see the different CVs version on github, on local, in cached db

![alt text](status_install.png "example")
## esgvoc get
the idea is : 
```bash
esgvoc get <What_CV>:<What_collection>:<What_term>

```
with some shortcuts   
you can try:
```bash
esgvoc get ::
esgvoc get universe::
esgvoc get universe:institution:
esgvoc get universe:institution:IPSL

esgvoc get cmip6plus::
esgvoc get cmip6plus:institution_id:
esgvoc get cmip6plus:institution_id:ipsl

esgvoc get cmip6plus:institution_id:ipsl cmip6plus:institution_id:llnl

```

## esgvoc valid

the idea is to validate the DRS_name against a collection or complete CV    
you can try : 

```bash
esgvoc valid IPSL ::
esgvoc valid ipsl ::


esgvoc valid IPSL cmip6plus::
esgvoc valid IPSL cmip6plus:institution_id:

```
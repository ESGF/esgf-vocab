from pathlib import Path
from esgvoc.core.data_handler import JsonLdResource
from esgvoc.core.service.data_merger import DataMerger, merge
from esgvoc.core.repo_fetcher import RepoFetcher
#
# def test_remote_organisation_ipsl():
#     
#     uri = "https://espri-mod.github.io/WCRP-universe/tree/esgvoc/organisation/ipsl.json"
#     merger = DataMerger(data= JsonLdResource(uri = uri), allowed_base_uris={"https://espri-mod.github.io/mip-cmor-table/"})
#     jsonlist = merger.merge_linked_json()
#     assert jsonlist[-1]["established"]==1991
#
# def test_remote_from_project_ipsl():
#
#     uri =  "https://espri-mod.github.io/CMIP6Plus_CVs/institution_id/ipsl.json"
#     merger = DataMerger(data= JsonLdResource(uri = uri), allowed_base_uris={"https://espri-mod.github.io/WCRP-universe/"})
#     jsonlist = merger.merge_linked_json()
#     assert jsonlist[-1]["established"]==1998 # this is a overcharged value 'from 1991 in ipsl definition in the universe to 1996 in ipsl in cmip6plus_cvs 
#     assert jsonlist[-1]["myprop"]=="42" # a new property definition in the project cv


def test_local_organisation_ipsl():
    from esgvoc.core.service import current_state
    uri_base = current_state.universe.local_path
    assert(uri_base is not None)
    uri = uri_base + "/organisation/ipsl.json"
    merger = DataMerger(data= JsonLdResource(uri = uri), allowed_base_uris={"https://espri-mod.github.io/mip-cmor-tables/"})
    jsonlist = merger.merge_linked_json()
    assert jsonlist[-1]["established"]==1991

def test_local_from_project_ipsl():
    from esgvoc.core.service import current_state
    uri_base = current_state.projects["cmip6plus"].local_path
    assert(uri_base is not None)

    uri = uri_base + "/institution_id/ipsl.json"
    merger = DataMerger(data= JsonLdResource(uri = uri), allowed_base_uris={"https://espri-mod.github.io/WCRP-universe/"})
    jsonlist = merger.merge_linked_json()
    assert jsonlist[-1]["established"]==1998 # this is a overcharged value 'from 1991 in ipsl definition in the universe to 1996 in ipsl in cmip6plus_cvs 
    assert jsonlist[-1]["myprop"]=="42" # a new property definition in the project cv



"""
def test_remote_project_remote_universe():
    rf = RepoFetcher()
    dir_list = rf.list_directory("ESPRI-Mod","CMIP6Plus_CVs","uni_proj_ld")
    res = {}
    nbmax = 10
    for dir in dir_list:
        nb=0
        file_list = rf.list_files("ESPRI-Mod","CMIP6Plus_CVs",dir,"uni_proj_ld")
        if "000_context.jsonld" in file_list:
            for file in file_list:
                if file != "000_context.jsonld":
                    term_uri = "https://espri-mod.github.io/CMIP6Plus_CVs/"+dir+"/"+file
                    print(term_uri)
                    final_term = merge(uri=term_uri)
                    print(final_term)
                    res[term_uri] = final_term 
                    nb=nb+1
                    if nb>nbmax:
                        break
    
    assert(len(res)==59)


def test_remote_project_local_universe():
    rf = RepoFetcher()
    dir_list = rf.list_directory("ESPRI-Mod","CMIP6Plus_CVs","uni_proj_ld")
    res = {}
    nbmax =10
    for dir in dir_list:
        file_list = rf.list_files("ESPRI-Mod","CMIP6Plus_CVs",dir,"uni_proj_ld")
        if "000_context.jsonld" in file_list:
            nb=0
            for file in file_list:
                if file != "000_context.jsonld":
                    
                    term_uri = "https://espri-mod.github.io/CMIP6Plus_CVs/"+dir+"/"+file
                    term = JsonLdResource(uri=str(term_uri))
                    mdm = DataMerger(data= term,
                                     locally_available={"https://espri-mod.github.io/WCRP-universe":".cache/repos/mip-cmor-tables"})
                    res[str(term_uri)]=mdm.merge_linked_json()[-1]
                    print(str(term_uri),res[str(term_uri)])
                    nb=nb+1
                if nb>nbmax:
                    break

    assert(len(res)==59)


def test_local_project_remote_universe():
    repos_dir = Path(".cache/repos/CMIP6Plus_CVs")
    res = {}
    nbmax = 10
    for dir in repos_dir.iterdir():
        
        if dir.is_dir() and dir /"000_context.jsonld" in list(dir.iterdir()):
            nb=0
            for term_uri in dir.iterdir():
                if "000_context" not in term_uri.stem:
                    term = JsonLdResource(uri=str(term_uri))
                    mdm = DataMerger(data= term, allowed_base_uris={"https://espri-mod.github.io/WCRP-universe/"})
                    res[str(term_uri)]=mdm.merge_linked_json()[-1]
                    print(res[str(term_uri)])
                    print("LENGTH ",len(res))
                    nb = nb+1
                    if nb>nbmax:
                        break
    assert len(res)==59
    

def test_local_project_local_universe():
    repos_dir = Path(".cache/repos/CMIP6Plus_CVs") 
    res = {}
    nbmax = 10
    for dir in repos_dir.iterdir():
        if dir.is_dir() and dir /"000_context.jsonld" in list(dir.iterdir()):
            nb = 0
            for term_uri in dir.iterdir():
                if "000_context" not in term_uri.stem:
                    #res[str(term_uri)]=merge(uri= str(term_uri))
                    term = JsonLdResource(uri=str(term_uri))
                    mdm = DataMerger(data= term,
                                     allowed_base_uris={"https://espri-mod.github.io/WCRP-universe/"},
                                     locally_available={"https://espri-mod.github.io/WCRP-universe":".cache/repos/mip-cmor-tables","https://  espri-mod.github.io/CMIP6Plus_CVs":".cache/repos/CMIP6Plus_CVs"})

                    res[term_uri] = mdm.merge_linked_json()[-1]
                    nb=nb+1
                    if nb>nbmax:
                        break
            
    assert len(res)==59 # For now at least .. 


"""

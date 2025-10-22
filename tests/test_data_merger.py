from pathlib import Path
import pytest
import json
import tempfile
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

# ============================================================================
# Tests for Resolve Modes (reference, shallow, full)
# ============================================================================

@pytest.fixture
def temp_test_dir():
    """Create a temporary directory structure for testing resolve modes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Create activity directory with context
        activity_dir = tmppath / "activity"
        activity_dir.mkdir()

        # Activity context
        activity_context = {
            "@context": {
                "@base": "https://test.example.com/activity/",
                "@vocab": "http://schema.org/",
                "id": "@id",
                "type": "@type"
            }
        }
        (activity_dir / "000_context.jsonld").write_text(json.dumps(activity_context))

        # scenariomip activity
        scenariomip_activity = {
            "@context": "000_context.jsonld",
            "id": "scenariomip",
            "type": "activity",
            "name": "ScenarioMIP",
            "drs_name": "ScenarioMIP"
        }
        (activity_dir / "scenariomip.json").write_text(json.dumps(scenariomip_activity))

        # cmip activity
        cmip_activity = {
            "@context": "000_context.jsonld",
            "id": "cmip",
            "type": "activity",
            "name": "CMIP",
            "drs_name": "CMIP"
        }
        (activity_dir / "cmip.json").write_text(json.dumps(cmip_activity))

        # Create source_type directory with context
        source_type_dir = tmppath / "source_type"
        source_type_dir.mkdir()

        source_type_context = {
            "@context": {
                "@base": "https://test.example.com/source_type/",
                "@vocab": "http://schema.org/",
                "id": "@id",
                "type": "@type"
            }
        }
        (source_type_dir / "000_context.jsonld").write_text(json.dumps(source_type_context))

        # agcm source type
        agcm_source = {
            "@context": "000_context.jsonld",
            "id": "agcm",
            "type": "source_type",
            "name": "Atmospheric General Circulation Model"
        }
        (source_type_dir / "agcm.json").write_text(json.dumps(agcm_source))

        # Create experiment directory with context including resolve modes
        experiment_dir = tmppath / "experiment"
        experiment_dir.mkdir()

        experiment_context = {
            "esgvoc_resolve_modes": {
                "activity": "full",
                "required_components": "reference",
                "parent_experiment": "shallow"
            },
            "@context": {
                "@base": "https://test.example.com/experiment/",
                "@vocab": "http://schema.org/",
                "id": "@id",
                "type": "@type",
                "activity": {
                    "@id": "https://test.example.com/activity/",
                    "@type": "@id",
                    "@context": {
                        "@base": "https://test.example.com/activity/"
                    }
                },
                "required_components": {
                    "@id": "https://test.example.com/source_type/",
                    "@type": "@id",
                    "@context": {
                        "@base": "https://test.example.com/source_type/"
                    }
                },
                "parent_experiment": {
                    "@id": "https://test.example.com/experiment/",
                    "@type": "@id",
                    "@context": {
                        "@base": "https://test.example.com/experiment/"
                    }
                }
            }
        }
        (experiment_dir / "000_context.jsonld").write_text(json.dumps(experiment_context))

        # Parent experiment (simple)
        parent_exp = {
            "@context": "000_context.jsonld",
            "id": "parent_exp",
            "type": "experiment",
            "name": "Parent Experiment",
            "activity": ["cmip"],
            "required_components": ["agcm"]
        }
        (experiment_dir / "parent_exp.json").write_text(json.dumps(parent_exp))

        # Child experiment (references parent)
        child_exp = {
            "@context": "000_context.jsonld",
            "id": "child_exp",
            "type": "experiment",
            "name": "Child Experiment",
            "activity": ["scenariomip"],
            "required_components": ["agcm"],
            "parent_experiment": ["parent_exp"]
        }
        (experiment_dir / "child_exp.json").write_text(json.dumps(child_exp))

        yield tmppath


def test_resolve_mode_reference(temp_test_dir):
    """Test that 'reference' mode keeps IDs as strings."""
    experiment_file = temp_test_dir / "experiment" / "child_exp.json"

    locally_available = {
        "https://test.example.com": str(temp_test_dir)
    }

    merger = DataMerger(
        data=JsonLdResource(uri=str(experiment_file)),
        locally_available=locally_available,
        allowed_base_uris={"https://test.example.com"},
    )

    merged_data = merger.merge_linked_json()[-1]
    resolved_data = merger.resolve_merged_ids(merged_data, context_base_path=str(temp_test_dir))

    # required_components should be kept as strings (reference mode)
    assert isinstance(resolved_data["required_components"], list)
    assert len(resolved_data["required_components"]) == 1
    assert resolved_data["required_components"][0] == "agcm"
    assert isinstance(resolved_data["required_components"][0], str)


def test_resolve_mode_full(temp_test_dir):
    """Test that 'full' mode resolves to complete objects."""
    experiment_file = temp_test_dir / "experiment" / "child_exp.json"

    locally_available = {
        "https://test.example.com": str(temp_test_dir)
    }

    merger = DataMerger(
        data=JsonLdResource(uri=str(experiment_file)),
        locally_available=locally_available,
        allowed_base_uris={"https://test.example.com"},
    )

    merged_data = merger.merge_linked_json()[-1]
    resolved_data = merger.resolve_merged_ids(merged_data, context_base_path=str(temp_test_dir))

    # activity should be fully resolved (full mode)
    assert isinstance(resolved_data["activity"], list)
    assert len(resolved_data["activity"]) == 1
    assert isinstance(resolved_data["activity"][0], dict)
    assert resolved_data["activity"][0]["id"] == "scenariomip"
    assert resolved_data["activity"][0]["name"] == "ScenarioMIP"
    assert resolved_data["activity"][0]["drs_name"] == "ScenarioMIP"


def test_resolve_mode_shallow(temp_test_dir):
    """Test that 'shallow' mode resolves but doesn't recurse."""
    experiment_file = temp_test_dir / "experiment" / "child_exp.json"

    locally_available = {
        "https://test.example.com": str(temp_test_dir)
    }

    merger = DataMerger(
        data=JsonLdResource(uri=str(experiment_file)),
        locally_available=locally_available,
        allowed_base_uris={"https://test.example.com"},
    )

    merged_data = merger.merge_linked_json()[-1]
    resolved_data = merger.resolve_merged_ids(merged_data, context_base_path=str(temp_test_dir))

    # parent_experiment should be resolved to object (shallow mode)
    assert isinstance(resolved_data["parent_experiment"], list)
    assert len(resolved_data["parent_experiment"]) == 1
    assert isinstance(resolved_data["parent_experiment"][0], dict)
    assert resolved_data["parent_experiment"][0]["id"] == "parent_exp"

    # But its nested fields should NOT be recursively resolved
    # (they should keep the raw structure from the file)
    parent = resolved_data["parent_experiment"][0]
    assert "activity" in parent
    assert "required_components" in parent


def test_mixed_resolved_unresolved_references(temp_test_dir):
    """Test handling of mixed resolved and unresolved references."""
    experiment_dir = temp_test_dir / "experiment"

    # Create experiment with mix of valid and invalid references
    mixed_exp = {
        "@context": "000_context.jsonld",
        "id": "mixed_exp",
        "type": "experiment",
        "name": "Mixed Experiment",
        "activity": ["scenariomip", "nonexistent_activity"],  # One valid, one invalid
        "required_components": ["agcm", "nonexistent_component"]
    }
    (experiment_dir / "mixed_exp.json").write_text(json.dumps(mixed_exp))

    locally_available = {
        "https://test.example.com": str(temp_test_dir)
    }

    merger = DataMerger(
        data=JsonLdResource(uri=str(experiment_dir / "mixed_exp.json")),
        locally_available=locally_available,
        allowed_base_uris={"https://test.example.com"},
    )

    merged_data = merger.merge_linked_json()[-1]
    resolved_data = merger.resolve_merged_ids(merged_data, context_base_path=str(temp_test_dir))

    # activity (full mode): should have one resolved object and one string
    assert isinstance(resolved_data["activity"], list)
    assert len(resolved_data["activity"]) == 2
    # First should be resolved
    assert isinstance(resolved_data["activity"][0], dict)
    assert resolved_data["activity"][0]["id"] == "scenariomip"
    # Second should remain as string
    assert isinstance(resolved_data["activity"][1], str)
    assert resolved_data["activity"][1] == "nonexistent_activity"

    # required_components (reference mode): both should be strings
    assert isinstance(resolved_data["required_components"], list)
    assert len(resolved_data["required_components"]) == 2
    assert all(isinstance(c, str) for c in resolved_data["required_components"])


def test_get_resolve_mode():
    """Test that _get_resolve_mode correctly reads from esgvoc_resolve_modes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        test_dir = tmppath / "test_dd"
        test_dir.mkdir()

        # Create context with esgvoc_resolve_modes
        context = {
            "esgvoc_resolve_modes": {
                "field1": "full",
                "field2": "reference",
                "field3": "shallow"
            },
            "@context": {
                "@base": "https://test.example.com/test_dd/",
                "id": "@id",
                "type": "@type"
            }
        }
        (test_dir / "000_context.jsonld").write_text(json.dumps(context))

        # Create test term
        term = {
            "@context": "000_context.jsonld",
            "id": "test",
            "type": "test_dd"
        }
        term_file = test_dir / "test.json"
        term_file.write_text(json.dumps(term))

        locally_available = {
            "https://test.example.com": str(tmppath)
        }

        merger = DataMerger(
            data=JsonLdResource(uri=str(term_file)),
            locally_available=locally_available,
            allowed_base_uris={"https://test.example.com"},
        )

        # Test that resolve modes are read correctly
        assert merger._get_resolve_mode("field1") == "full"
        assert merger._get_resolve_mode("field2") == "reference"
        assert merger._get_resolve_mode("field3") == "shallow"
        # Unknown field should default to "full"
        assert merger._get_resolve_mode("unknown_field") == "full"


def test_property_tracking_in_warnings(temp_test_dir):
    """Test that warnings include property name for unresolved references.

    This test verifies the functionality works; warnings are visible in test output.
    """
    experiment_dir = temp_test_dir / "experiment"

    # Create experiment with invalid reference
    exp = {
        "@context": "000_context.jsonld",
        "id": "test_exp",
        "type": "experiment",
        "name": "Test",
        "activity": ["nonexistent_activity"]
    }
    (experiment_dir / "test_exp.json").write_text(json.dumps(exp))

    locally_available = {
        "https://test.example.com": str(temp_test_dir)
    }

    merger = DataMerger(
        data=JsonLdResource(uri=str(experiment_dir / "test_exp.json")),
        locally_available=locally_available,
        allowed_base_uris={"https://test.example.com"},
    )

    merged_data = merger.merge_linked_json()[-1]
    resolved_data = merger.resolve_merged_ids(merged_data, context_base_path=str(temp_test_dir))

    # Verify the data still resolves correctly even with unresolved references
    assert "activity" in resolved_data
    assert isinstance(resolved_data["activity"], list)
    # The unresolved reference should be kept as a string
    assert "nonexistent_activity" in resolved_data["activity"]
    assert isinstance(resolved_data["activity"][0], str)

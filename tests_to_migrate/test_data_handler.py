
from pathlib import Path
import pytest
from unittest.mock import patch
from pydantic import ValidationError
from esgvoc.core.data_handler import JsonLdResource

mock_json_data = {"@context": "http://example.com/context", "name": "Test"}

@pytest.fixture
def data_instance():
    return JsonLdResource(uri="http://example.com/resource")

@patch("esgvoc.core.data_handler.unified_document_loader", return_value=mock_json_data)
def test_json(mock_loader, data_instance):
    assert data_instance.json_dict == mock_json_data
    mock_loader.assert_called_once_with("http://example.com/resource")

def test_invalid_uri():
    with pytest.raises(ValidationError):
        JsonLdResource(uri=123)  # Invalid URI type

def test_local_path():
    data = JsonLdResource(uri="http://example.com/resource", local_path="./data")
    assert data.local_path.endswith("/data/")


# Integration test 

def test_local_project_all_term():
    from esgvoc.core.service import current_state
    repos_dir = Path(current_state.projects["cmip6plus"].local_path) 
    for dir in repos_dir.iterdir():
        if dir.is_dir() and dir /"000_context.jsonld" in list(dir.iterdir()):
             for term_uri in dir.iterdir():
                if "000_context" not in term_uri.stem:
                    term = JsonLdResource(uri=str(term_uri))
                    

 
def test_local_universe_all_term():
    from esgvoc.core.service import current_state
    repos_dir = Path(current_state.universe.local_path) 

    for dir in repos_dir.iterdir():
        
        if dir.is_dir() and dir /"000_context.jsonld" in list(dir.iterdir()):
             for term_uri in dir.iterdir():
                if "000_context" not in term_uri.stem:
                    term = JsonLdResource(uri=str(term_uri))
                    assert term.info
                    
           
    


   

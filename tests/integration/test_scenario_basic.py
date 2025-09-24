
from esgvoc.core import service
import esgvoc.api as ev

def test_install():
    assert(service.config_manager is not None)
    before_test_active = service.config_manager.get_active_config_name()
    service.config_manager._init_registry()
    service.config_manager.switch_config("default")
    current_state = service.get_state()
    assert(current_state is not None)
    current_state.synchronize_all()
    assert(ev.valid_term("IPSL", "cmip6","institution_id","ipsl"))
    service.config_manager.switch_config(before_test_active)
    current_state = service.get_state()


def test_create_new_config():
    assert(service.config_manager is not None)
    before_test_active = service.config_manager.get_active_config_name()
    service.config_manager._init_registry()
    service.config_manager.switch_config("default")
    service.config_manager.save_config(service.config_manager.get_active_config().dump(),"default_test")
    service.config_manager.switch_config("default_test")
    current_state = service.get_state()
    assert(current_state is not None)
    current_state.synchronize_all()
    assert(ev.valid_term("IPSL", "cmip6","institution_id","ipsl"))
    service.config_manager.switch_config(before_test_active)
    current_state = service.get_state()


def test_branch_switching_scenario():
    """Test branch switching from default branch to dev branch"""
    import subprocess
    import os
    import shutil
    from pathlib import Path

    assert(service.config_manager is not None)
    before_test_active = service.config_manager.get_active_config_name()

    # Clean up any existing test data
    test_config_dir = Path.home() / ".local/share/esgvoc/branch_test"
    if test_config_dir.exists():
        shutil.rmtree(test_config_dir)
        print(f"Removed existing test directory: {test_config_dir}")

    # Create a new config for testing
    service.config_manager._init_registry()
    service.config_manager.switch_config("default")
    service.config_manager.save_config(service.config_manager.get_active_config().dump(), "branch_test")
    service.config_manager.switch_config("branch_test")

    # Initial install with default branch
    current_state = service.get_state()
    assert(current_state is not None)
    current_state.synchronize_all()

    # Get the current config and modify branches from esgvoc to esgvoc_dev
    current_config = service.config_manager.get_active_config()
    config_dict = current_config.dump()

    # Change universe branch
    if 'universe' in config_dict and 'branch' in config_dict['universe']:
        original_universe_branch = config_dict['universe']['branch']
        if original_universe_branch == 'esgvoc':
            config_dict['universe']['branch'] = 'esgvoc_dev'

    # Change project branches
    if 'projects' in config_dict:
        if isinstance(config_dict['projects'], dict):
            # Handle dict format
            for project_name, project_config in config_dict['projects'].items():
                if 'branch' in project_config:
                    original_project_branch = project_config['branch']
                    if original_project_branch == 'esgvoc':
                        project_config['branch'] = 'esgvoc_dev'
        elif isinstance(config_dict['projects'], list):
            # Handle list format
            for project_config in config_dict['projects']:
                if 'branch' in project_config:
                    original_project_branch = project_config['branch']
                    if original_project_branch == 'esgvoc':
                        project_config['branch'] = 'esgvoc_dev'

    # Save the modified config
    service.config_manager.save_config(config_dict, "branch_test")

    # Reload the config to pick up changes
    service.config_manager.switch_config("branch_test")

    # Install with the new branch configuration
    updated_state = service.get_state()
    updated_state.synchronize_all()

    # Verify that local repos are now on the esgvoc_dev branch
    # Check universe repository
    if hasattr(updated_state.universe, 'local_path') and updated_state.universe.local_path:
        if os.path.exists(updated_state.universe.local_path):
            result = subprocess.run(
                ["git", "-C", updated_state.universe.local_path, "branch", "--show-current"],
                capture_output=True,
                text=True,
                check=True
            )
            current_branch = result.stdout.strip()
            if updated_state.universe.branch == 'esgvoc_dev':
                assert current_branch == 'esgvoc_dev', f"Universe repo should be on esgvoc_dev branch, got {current_branch}"

    # Check project repositories
    for project_name, project_state in updated_state.projects.items():
        if hasattr(project_state, 'local_path') and project_state.local_path:
            if os.path.exists(project_state.local_path):
                result = subprocess.run(
                    ["git", "-C", project_state.local_path, "branch", "--show-current"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                current_branch = result.stdout.strip()
                if project_state.branch == 'esgvoc_dev':
                    assert current_branch == 'esgvoc_dev', f"Project {project_name} repo should be on esgvoc_dev branch, got {current_branch}"

    # Cleanup - switch back to original config
    service.config_manager.switch_config(before_test_active)
    current_state = service.get_state()





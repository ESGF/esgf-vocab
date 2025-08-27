#!/usr/bin/env python3
"""
CV Testing Application for ESGVoc

This application allows testing of project CVs and Universe CVs with support for:
- Custom repository URLs and branches via CLI options and environment variables
- Universe branch override for testing against different WCRP-universe versions
- Validation of repository structure and content
- Testing esgvoc API integration with CV repositories
- Support for all available default projects: cmip6, cmip6plus, input4mip, obs4mip, cordex-cmip6
- Rich CLI interface integrated with esgvoc CLI
- Environment variable support for CI/CD integration
- Automatic repository path detection for synchronized CVs
"""

import json
import os
import sys
from pathlib import Path
from typing import List

from pydantic import ValidationError
from rich.console import Console

import esgvoc.core.service as service
from esgvoc.core.service.configuration.setting import (
    ServiceSettings,
)
from esgvoc.core.service.state import StateService

console = Console()


def detect_project_name() -> str:
    """
    Try to auto-detect project name from current directory or environment.
    Falls back to a reasonable default for testing.
    """
    # Check environment first
    env_project = os.environ.get("PROJECT_NAME")
    if env_project:
        return env_project.lower()
    
    # Try to detect from current directory name or path
    cwd = Path.cwd()
    dir_name = cwd.name.lower()
    
    # Check if directory name matches any known project patterns
    project_patterns = {
        "obs4mips": ["obs4mips", "obs4mip"],
        "input4mips": ["input4mips", "input4mip"], 
        "cmip6": ["cmip6"],
        "cmip6plus": ["cmip6plus", "cmip6+"],
        "cordex-cmip6": ["cordex-cmip6", "cordex", "cordexcmip6"]
    }
    
    for project, patterns in project_patterns.items():
        if any(pattern in dir_name for pattern in patterns):
            return project
    
    # Check parent directories
    for parent in cwd.parents:
        parent_name = parent.name.lower()
        for project, patterns in project_patterns.items():
            if any(pattern in parent_name for pattern in patterns):
                return project
    
    # Default fallback
    console.print("[yellow]⚠️  Could not auto-detect project, using 'obs4mip' as default[/yellow]")
    return "obs4mip"


class CVTester:
    """Main CV testing class"""

    def __init__(self):
        self.original_config_name = None
        self.test_config_name = "test_cv_temp"
        self.config_manager = None

    def get_available_projects(self) -> List[str]:
        """Get list of all available project CVs"""
        return list(ServiceSettings.DEFAULT_PROJECT_CONFIGS.keys())

    def configure_for_testing(
        self, project_name: str = None, repo_url: str = None, branch: str = None, esgvoc_branch: str = None, universe_branch: str = None
    ) -> bool:
        """
        Configure esgvoc with custom or default CV settings for testing

        Args:
            project_name: Name of the project to test (required)
            repo_url: Custom repository URL (optional - uses default if not provided)
            branch: Custom branch (optional - uses default if not provided)
            esgvoc_branch: ESGVoc library branch (for info only)
            universe_branch: Custom universe branch (optional - uses 'esgvoc' if not provided)

        Returns:
            bool: True if configuration was successful
        """
        try:
            # Get config manager and store original active configuration
            self.config_manager = service.get_config_manager()
            self.original_config_name = self.config_manager.get_active_config_name()

            console.print(f"[blue]Current active configuration: {self.original_config_name}[/blue]")

            # Determine project configuration
            if project_name not in self.get_available_projects():
                available = ", ".join(self.get_available_projects())
                console.print(f"[red]❌ Unknown project '{project_name}'. Available projects: {available}[/red]")
                return False

            # Use custom repo/branch if provided, otherwise use defaults
            if repo_url or branch:
                # Custom configuration
                default_config = ServiceSettings.DEFAULT_PROJECT_CONFIGS[project_name]
                project_config = {
                    "project_name": project_name,
                    "github_repo": repo_url or default_config["github_repo"],
                    "branch": branch or default_config["branch"],
                    "local_path": default_config["local_path"],
                    "db_path": default_config["db_path"],
                }
                console.print(f"[blue]Using custom configuration for {project_name}:[/blue]")
                console.print(f"  Repository: {project_config['github_repo']}")
                console.print(f"  Branch: {project_config['branch']}")
            else:
                # Default configuration
                project_config = ServiceSettings.DEFAULT_PROJECT_CONFIGS[project_name].copy()
                console.print(f"[blue]Using default configuration for {project_name}[/blue]")

            # Create temporary test configuration with universe and single project
            test_config_data = {
                "universe": {
                    "github_repo": "https://github.com/WCRP-CMIP/WCRP-universe",
                    "branch": universe_branch or "esgvoc",
                    "local_path": "repos/WCRP-universe",
                    "db_path": "dbs/universe.sqlite",
                },
                "projects": [project_config],
            }

            # Remove existing test config if it exists
            configs = self.config_manager.list_configs()
            if self.test_config_name in configs:
                console.print(f"[yellow]Removing existing test configuration: {self.test_config_name}[/yellow]")
                self.config_manager.remove_config(self.test_config_name)

            # Create new test configuration
            console.print(f"[blue]Creating temporary test configuration: {self.test_config_name}[/blue]")
            console.print(f"[dim]Debug: Test config data projects: {test_config_data['projects']}[/dim]")
            self.config_manager.add_config(self.test_config_name, test_config_data)

            # Switch to test configuration
            self.config_manager.switch_config(self.test_config_name)
            console.print(f"[green]✅ Switched to test configuration: {self.test_config_name}[/green]")

            # CRITICAL FIX: Update the data_config_dir after switching configurations
            # This is the root cause - data_config_dir is set once and never updated
            self.config_manager.data_config_dir = self.config_manager.data_dir / self.test_config_name
            self.config_manager.data_config_dir.mkdir(parents=True, exist_ok=True)
            console.print(f"[dim]Debug: Updated data_config_dir to: {self.config_manager.data_config_dir}[/dim]")

            # Clear any potential caches in the config manager
            if hasattr(self.config_manager, "_cached_config"):
                self.config_manager._cached_config = None
            if hasattr(self.config_manager, "cache"):
                self.config_manager.cache.clear()

            # Create fresh StateService with the updated configuration and directory
            fresh_config = self.config_manager.get_config(self.test_config_name)
            service.current_state = service.StateService(fresh_config)
            console.print(f"[dim]Debug: Created fresh StateService for {self.test_config_name}[/dim]")

            # Debug: Verify the fix worked
            console.print(f"[dim]Debug: StateService universe base_dir: {service.current_state.universe.base_dir}[/dim]")
            console.print(f"[dim]Debug: StateService universe local_path: {service.current_state.universe.local_path}[/dim]")

            if esgvoc_branch:
                console.print(f"[dim]Using esgvoc library from branch: {esgvoc_branch}[/dim]")

            return True

        except Exception as e:
            console.print(f"[red]❌ Configuration failed: {e}[/red]")
            import traceback

            console.print(traceback.format_exc())
            return False

    def synchronize_cvs(self) -> bool:
        """Synchronize/download the configured CVs"""
        try:
            console.print("[blue]Synchronizing CVs...[/blue]")

            # Force refresh the state service to ensure it uses the correct configuration
            service.current_state = service.get_state()

            # Debug: Show what configuration the state service is using
            config_manager = service.get_config_manager()
            active_config = config_manager.get_active_config_name()
            console.print(f"[dim]Debug: Active config during sync: {active_config}[/dim]")
            console.print(f"[dim]Debug: Expected config: {self.test_config_name}[/dim]")
            console.print(f"[dim]Debug: Data config dir during sync: {config_manager.data_config_dir}[/dim]")

            if active_config != self.test_config_name:
                console.print(
                    f"[yellow]⚠️  Warning: Active config mismatch, forcing switch to {self.test_config_name}[/yellow]"
                )
                config_manager.switch_config(self.test_config_name)

                # Update data_config_dir after forced switch
                config_manager.data_config_dir = config_manager.data_dir / self.test_config_name
                config_manager.data_config_dir.mkdir(parents=True, exist_ok=True)

                # Clear caches again after forced switch
                if hasattr(config_manager, "_cached_config"):
                    config_manager._cached_config = None
                if hasattr(config_manager, "cache"):
                    config_manager.cache.clear()

                # Create fresh StateService with correct configuration
                fresh_config = config_manager.get_config(self.test_config_name)
                service.current_state = StateService(fresh_config)
                console.print(f"[dim]Debug: Recreated StateService for {self.test_config_name}[/dim]")

            service.current_state.synchronize_all()
            console.print("[green]✅ CVs synchronized successfully[/green]")
            return True
        except Exception as e:
            console.print(f"[red]❌ CV synchronization failed: {e}[/red]")
            import traceback

            console.print(traceback.format_exc())
            return False

    def test_repository_structure(self, repo_path: str = ".") -> bool:
        """
        Test repository structure and file requirements

        Args:
            repo_path: Path to the repository to test (default: current directory)

        Returns:
            bool: True if all tests pass
        """
        console.print(f"[blue]🧪 Testing repository structure in: {repo_path}[/blue]")

        repo_dir = Path(repo_path)
        if not repo_dir.exists():
            console.print(f"[red]❌ Repository path does not exist: {repo_path}[/red]")
            return False

        errors = []
        warnings = []

        # Get all directories
        all_directories = [p for p in repo_dir.iterdir() if p.is_dir()]

        # Identify collection directories by presence of .jsonld files
        collection_directories = []
        directories_with_json_but_no_jsonld = []

        for directory in all_directories:
            files_in_dir = list(directory.iterdir())
            jsonld_files = [f for f in files_in_dir if f.name.endswith(".jsonld")]
            json_files = [f for f in files_in_dir if f.name.endswith(".json") and not f.name.endswith(".jsonld")]

            if len(jsonld_files) > 0:
                collection_directories.append(directory)
            elif len(json_files) > 0:
                directories_with_json_but_no_jsonld.append(directory)

        console.print(f"Found {len(collection_directories)} collection directories (with .jsonld files)")

        # Warn about directories that might be missing context files
        for directory in directories_with_json_but_no_jsonld:
            warnings.append(f"⚠️  Directory '{directory.name}' has .json files but no .jsonld context")

        # Test each collection directory
        for directory in collection_directories:
            console.print(f"📁 Testing collection: {directory.name}")
            collection_errors = self._test_collection_directory(directory)
            errors.extend(collection_errors)

        # Test project_specs.json if it exists
        project_specs_file = repo_dir / "project_specs.json"
        if project_specs_file.exists():
            console.print("📄 Testing project_specs.json references...")
            specs_errors = self._test_project_specs(project_specs_file, collection_directories)
            errors.extend(specs_errors)
        else:
            warnings.append("⚠️  project_specs.json not found - skipping reference validation")

        # Display warnings
        if warnings:
            console.print(f"\n[yellow]Warnings ({len(warnings)}):[/yellow]")
            for warning in warnings:
                console.print(f"   {warning}")

        # Summary
        if errors:
            console.print(f"\n[red]❌ Repository structure validation failed with {len(errors)} errors:[/red]")
            for error in errors:
                console.print(f"   {error}")
            return False
        else:
            console.print("\n[green]✅ Repository structure validation passed![/green]")
            console.print(f"✅ Validated {len(collection_directories)} collection directories")
            return True

    def _test_collection_directory(self, directory: Path) -> List[str]:
        """Test a single collection directory"""
        errors = []

        files_in_dir = list(directory.iterdir())
        jsonld_files = [f for f in files_in_dir if f.name.endswith(".jsonld")]
        other_files = [f for f in files_in_dir if not f.name.endswith(".jsonld")]

        # Test directory structure
        if len(jsonld_files) == 0:
            errors.append(f"❌ {directory.name}: No .jsonld context file found")
        elif len(jsonld_files) > 1:
            console.print(f"   [yellow]⚠️  Multiple .jsonld files: {[f.name for f in jsonld_files]}[/yellow]")

        if len(other_files) == 0:
            errors.append(f"❌ {directory.name}: No element files found")

        # Test JSONLD context files
        for jsonld_file in jsonld_files:
            try:
                with open(jsonld_file, "r", encoding="utf-8") as f:
                    jsonld_content = json.load(f)

                if "@context" not in jsonld_content:
                    errors.append(f"❌ {jsonld_file.name}: Missing '@context' field")
                    continue

                context = jsonld_content["@context"]
                if not isinstance(context, dict):
                    errors.append(f"❌ {jsonld_file.name}: '@context' must be a dictionary")
                    continue

                # Check required context fields
                required_fields = ["id", "type", "@base"]
                missing_fields = [field for field in required_fields if field not in context]
                if missing_fields:
                    errors.append(f"❌ {jsonld_file.name}: Missing required fields in @context: {missing_fields}")

            except json.JSONDecodeError as e:
                errors.append(f"❌ {jsonld_file.name}: Invalid JSON syntax - {e}")
            except Exception as e:
                errors.append(f"❌ {jsonld_file.name}: Error reading file - {e}")

        # Test element files
        json_element_files = [f for f in other_files if f.name.endswith(".json")]
        for element_file in json_element_files:
            try:
                with open(element_file, "r", encoding="utf-8") as f:
                    element_content = json.load(f)

                required_fields = ["id", "type", "@context"]
                missing_fields = [field for field in required_fields if field not in element_content]
                if missing_fields:
                    errors.append(f"❌ {element_file.name}: Missing required fields: {missing_fields}")

            except json.JSONDecodeError as e:
                errors.append(f"❌ {element_file.name}: Invalid JSON syntax - {e}")
            except Exception as e:
                errors.append(f"❌ {element_file.name}: Error reading file - {e}")

        if not errors:
            console.print(f"   [green]✅ Collection '{directory.name}' passed validation[/green]")

        return errors

    def _test_project_specs(self, specs_file: Path, collection_directories: List[Path]) -> List[str]:
        """Test project_specs.json references"""
        errors = []

        try:
            with open(specs_file, "r", encoding="utf-8") as f:
                project_specs = json.load(f)

            # Extract source_collection references
            source_collections = set()

            # Check drs_specs collections
            if "drs_specs" in project_specs:
                for drs_spec in project_specs["drs_specs"]:
                    if "parts" in drs_spec:
                        for part in drs_spec["parts"]:
                            if "collection_id" in part:
                                source_collections.add(part["collection_id"])

            # Check global_attributes_specs collections
            if "global_attributes_specs" in project_specs and "specs" in project_specs["global_attributes_specs"]:
                for attr_name, attr_spec in project_specs["global_attributes_specs"]["specs"].items():
                    if "source_collection" in attr_spec:
                        source_collections.add(attr_spec["source_collection"])

            console.print(f"   Found {len(source_collections)} source_collection references")

            # Check if referenced collections exist
            existing_collections = {d.name for d in collection_directories}
            for collection in source_collections:
                if collection not in existing_collections:
                    errors.append(f"❌ project_specs.json references non-existent collection: '{collection}'")
                else:
                    console.print(f"   [green]✅ Reference '{collection}' exists[/green]")

        except json.JSONDecodeError as e:
            errors.append(f"❌ project_specs.json: Invalid JSON syntax - {e}")
        except Exception as e:
            errors.append(f"❌ Error reading project_specs.json: {e}")

        return errors

    def test_esgvoc_api_access(self, project_name: str, repo_path: str = ".") -> bool:
        """
        Test that all repository collections and elements are queryable via esgvoc API

        Args:
            project_name: Name of the project being tested
            repo_path: Path to the repository (default: current directory)

        Returns:
            bool: True if all API tests pass
        """
        console.print(f"[blue]🔍 Testing esgvoc API access for project: {project_name}[/blue]")

        try:
            import esgvoc.api as ev
        except ImportError as e:
            console.print(f"[red]❌ Cannot import esgvoc.api: {e}[/red]")
            return False

        repo_dir = Path(repo_path)
        errors = []

        # Test 1: Verify project exists in esgvoc
        try:
            projects = ev.get_all_projects()
            if project_name not in projects:
                errors.append(f"❌ Project '{project_name}' not found in esgvoc. Available: {projects}")
                return False
            console.print(f"[green]✅ Project '{project_name}' found in esgvoc[/green]")
        except Exception as e:
            errors.append(f"❌ Failed to get projects from esgvoc: {e}")
            return False

        # Get repository collections
        repo_collections = []
        all_directories = [p for p in repo_dir.iterdir() if p.is_dir()]
        for directory in all_directories:
            files_in_dir = list(directory.iterdir())
            jsonld_files = [f for f in files_in_dir if f.name.endswith(".jsonld")]
            if len(jsonld_files) > 0:
                repo_collections.append(directory.name)

        # Test 2: Get collections from esgvoc
        try:
            # Debug: Check active configuration during API test
            current_active = service.get_config_manager().get_active_config_name()
            console.print(f"[dim]Debug: Active config during API test: {current_active}[/dim]")

            esgvoc_collections = ev.get_all_collections_in_project(project_name)
            console.print(
                f"Found {len(esgvoc_collections)} collections in esgvoc, {len(repo_collections)} in repository"
            )
        except ValidationError as e:
            # Enhanced error reporting for Pydantic validation errors
            error_msg = f"❌ Validation error while processing collections for project '{project_name}'"

            # Try to extract more context from the error
            if hasattr(e, 'errors') and e.errors():
                for error in e.errors():
                    if 'input' in error and 'ctx' in error:
                        error_msg += f"\n   • Invalid value: '{error['input']}'"
                        if 'enum_values' in error['ctx']:
                            error_msg += f"\n   • Expected one of: {error['ctx']['enum_values']}"
                        if error.get('type') == 'enum':
                            error_msg += f"\n   • Field: {error.get('loc', 'unknown')}"

            errors.append(error_msg)
            console.print(f"[red]{error_msg}[/red]")
            console.print(f"[dim]Full error details: {str(e)}[/dim]")
            return False
        except ValueError as e:
            # Enhanced error reporting for database validation issues
            error_str = str(e)
            if "collections with empty term_kind" in error_str:
                console.print(f"[red]❌ Database validation error for project '{project_name}':[/red]")
                console.print(f"[red]{error_str}[/red]")
                errors.append(f"❌ Invalid termkind values in database for project '{project_name}'")
            else:
                errors.append(f"❌ Failed to get collections from esgvoc: {e}")
                console.print(f"[red]API Error Details: {e}[/red]")
            return False
        except Exception as e:
            errors.append(f"❌ Failed to get collections from esgvoc: {e}")
            console.print(f"[red]API Error Details: {e}[/red]")
            return False

        # Test 3: Verify each repository collection is queryable
        missing_in_esgvoc = []
        for collection_name in repo_collections:
            if collection_name not in esgvoc_collections:
                missing_in_esgvoc.append(collection_name)
            else:
                console.print(f"   [green]✅ Collection '{collection_name}' found in esgvoc[/green]")

        if missing_in_esgvoc:
            errors.append(f"❌ Collections in repository but not in esgvoc: {missing_in_esgvoc}")

        # Test 4: Test elements in each collection
        for collection_name in repo_collections:
            if collection_name in esgvoc_collections:
                console.print(f"📂 Testing elements in collection: {collection_name}")

                # Get repository elements
                collection_dir = repo_dir / collection_name
                json_files = [
                    f for f in collection_dir.iterdir() if f.name.endswith(".json") and not f.name.endswith(".jsonld")
                ]

                repo_elements = []
                for json_file in json_files:
                    try:
                        with open(json_file, "r", encoding="utf-8") as f:
                            content = json.load(f)
                        element_id = content.get("id", json_file.stem)
                        repo_elements.append(element_id)
                    except:
                        repo_elements.append(json_file.stem)

                # Get esgvoc elements
                try:
                    esgvoc_terms = ev.get_all_terms_in_collection(project_name, collection_name)
                    esgvoc_element_ids = [term.id for term in esgvoc_terms]

                    console.print(f"   Repository: {len(repo_elements)}, ESGVoc: {len(esgvoc_element_ids)} elements")

                    missing_elements = [elem for elem in repo_elements if elem not in esgvoc_element_ids]
                    if missing_elements:
                        errors.append(
                            f"❌ Collection '{collection_name}': Elements missing from esgvoc: {missing_elements}"
                        )
                    else:
                        console.print(f"   [green]✅ All elements in '{collection_name}' are queryable[/green]")

                except Exception as e:
                    errors.append(f"❌ Failed to get terms from collection '{collection_name}': {e}")

        # Test 5: General API functions
        try:
            all_terms = ev.get_all_terms_in_all_projects()
            console.print(f"[blue]📊 ESGVoc API returned {len(all_terms)} total terms across all projects[/blue]")
        except Exception as e:
            errors.append(f"❌ Failed to get all terms from esgvoc: {e}")

        # Summary
        if errors:
            console.print(f"\n[red]❌ ESGVoc API validation failed with {len(errors)} errors:[/red]")
            for error in errors:
                console.print(f"   {error}")
            return False
        else:
            console.print("\n[green]✅ ESGVoc API validation passed![/green]")
            console.print(f"✅ Validated {len(repo_collections)} collections")
            console.print("✅ All repository elements accessible through esgvoc API")
            return True

    def run_complete_test(
        self,
        project_name: str,
        repo_url: str = None,
        branch: str = None,
        repo_path: str = None,
        esgvoc_branch: str = None,
        universe_branch: str = None,
    ) -> bool:
        """
        Run complete CV testing pipeline

        Args:
            project_name: Name of the project to test
            repo_url: Custom repository URL (optional)
            branch: Custom branch (optional)
            repo_path: Path to repository for structure testing (optional - auto-detected if not provided)
            esgvoc_branch: ESGVoc library branch (for info only)
            universe_branch: Custom universe branch (optional)

        Returns:
            bool: True if all tests pass
        """
        console.print(f"[bold blue]🚀 Starting complete CV test for project: {project_name}[/bold blue]")

        success = True

        # Step 1: Configure esgvoc
        if not self.configure_for_testing(project_name, repo_url, branch, esgvoc_branch, universe_branch):
            return False

        # Step 2: Synchronize CVs
        if not self.synchronize_cvs():
            success = False

        # Step 2.5: Determine repository path AFTER synchronization - use downloaded CV repository if not specified
        if repo_path is None:
            # Use the state service to get the actual project path directly
            try:
                current_state = service.get_state()
                if hasattr(current_state, 'projects') and project_name in current_state.projects:
                    project_state = current_state.projects[project_name]
                    if hasattr(project_state, 'local_path') and project_state.local_path:
                        repo_path = str(project_state.local_path)
                        console.print(f"[blue]Using CV repository from state service: {repo_path}[/blue]")
                    else:
                        console.print("[dim]Debug: Project state has no local_path[/dim]")
                else:
                    console.print(f"[dim]Debug: Project {project_name} not found in state service projects[/dim]")
                    console.print(f"[dim]Debug: Available projects in state: {list(current_state.projects.keys()) if hasattr(current_state, 'projects') else 'No projects'}[/dim]")
            except Exception as e:
                console.print(f"[dim]Debug: Error accessing state service: {e}[/dim]")
            
            # Fallback: try to find the repository using the known default local path
            if repo_path is None:
                try:
                    from esgvoc.core.service.configuration.setting import ServiceSettings
                    if project_name in ServiceSettings.DEFAULT_PROJECT_CONFIGS:
                        default_local_path = ServiceSettings.DEFAULT_PROJECT_CONFIGS[project_name]["local_path"]
                        config_manager = service.get_config_manager()
                        
                        # Try different path constructions to find where the repository actually is
                        possible_paths = [
                            config_manager.data_config_dir / default_local_path,
                            config_manager.data_dir / self.test_config_name / default_local_path,
                            config_manager.data_dir / default_local_path,
                        ]
                        
                        # Also check in other configuration directories  
                        if config_manager.data_dir.exists():
                            for config_dir in config_manager.data_dir.iterdir():
                                if config_dir.is_dir():
                                    possible_repo_path = config_dir / default_local_path
                                    if possible_repo_path.exists():
                                        possible_paths.append(possible_repo_path)

                        for path in possible_paths:
                            if path and path.exists():
                                repo_path = str(path)
                                console.print(f"[blue]Found CV repository at: {repo_path}[/blue]")
                                break
                except Exception as e:
                    console.print(f"[dim]Debug: Error in fallback path detection: {e}[/dim]")

            # Final fallback
            if repo_path is None:
                repo_path = "."
                console.print("[yellow]⚠️  Could not determine CV repository path, using current directory[/yellow]")

        # Step 3: Test repository structure
        if not self.test_repository_structure(repo_path):
            success = False

        # Debug: Check what configuration is active before API test
        current_active = service.get_config_manager().get_active_config_name()
        console.print(f"[dim]Debug: Active config before API test: {current_active}[/dim]")

        # Step 4: Test esgvoc API access
        if not self.test_esgvoc_api_access(project_name, repo_path):
            success = False

        # Summary
        if success:
            console.print(f"\n[bold green]🎉 All tests passed for project '{project_name}'![/bold green]")
        else:
            console.print(f"\n[bold red]❌ Some tests failed for project '{project_name}'[/bold red]")

        return success

    def restore_original_configuration(self):
        """Restore the original esgvoc configuration"""
        try:
            if self.config_manager and self.original_config_name:
                # Switch back to original configuration
                console.print(f"[blue]Restoring original configuration: {self.original_config_name}[/blue]")
                self.config_manager.switch_config(self.original_config_name)

                # CRITICAL: Restore the original data_config_dir
                self.config_manager.data_config_dir = self.config_manager.data_dir / self.original_config_name
                self.config_manager.data_config_dir.mkdir(parents=True, exist_ok=True)
                console.print(f"[dim]Debug: Restored data_config_dir to: {self.config_manager.data_config_dir}[/dim]")

                # Reset service state
                service.current_state = service.get_state()

                # Remove temporary test configuration
                configs = self.config_manager.list_configs()
                if self.test_config_name in configs:
                    console.print(f"[blue]Removing temporary test configuration: {self.test_config_name}[/blue]")
                    self.config_manager.remove_config(self.test_config_name)

                console.print(f"[green]✅ Restored original configuration: {self.original_config_name}[/green]")
        except Exception as e:
            console.print(f"[yellow]⚠️  Error restoring original configuration: {e}[/yellow]")

    def cleanup(self):
        """Cleanup resources and restore original configuration"""
        self.restore_original_configuration()


def main():
    """Main CLI interface"""
    if len(sys.argv) < 2:
        print("Usage: cv_tester.py <command> [options]")
        print("\nCommands:")
        print("  list                     - List available projects")
        print("  configure <project>      - Configure esgvoc for testing")
        print("  test <project>           - Run complete test suite")
        print("  structure <path>         - Test repository structure only")
        print("  api <project> <path>     - Test esgvoc API access only")
        print("\nEnvironment variables:")
        print("  TEST_BRANCH             - Custom project branch to test")
        print("  REPO_URL                - Custom repository URL")
        print("  UNIVERSE_BRANCH         - Custom universe branch to test")
        print("  ESGVOC_LIBRARY_BRANCH   - ESGVoc library branch (for info)")
        sys.exit(1)

    command = sys.argv[1]
    tester = CVTester()

    try:
        if command == "list":
            projects = tester.get_available_projects()
            console.print(f"[blue]Available projects ({len(projects)}):[/blue]")
            for project in projects:
                config = ServiceSettings.DEFAULT_PROJECT_CONFIGS[project]
                console.print(f"  [cyan]{project}[/cyan] - {config['github_repo']} (branch: {config['branch']})")

        elif command == "configure":
            if len(sys.argv) < 3:
                console.print("[red]Error: Project name required[/red]")
                sys.exit(1)

            project_name = sys.argv[2]
            repo_url = os.environ.get("REPO_URL")
            branch = os.environ.get("TEST_BRANCH")
            esgvoc_branch = os.environ.get("ESGVOC_LIBRARY_BRANCH")

            if tester.configure_for_testing(project_name, repo_url, branch, esgvoc_branch):
                if tester.synchronize_cvs():
                    console.print("[green]✅ Configuration complete[/green]")
                else:
                    sys.exit(1)
            else:
                sys.exit(1)

        elif command == "test":
            if len(sys.argv) < 3:
                console.print("[red]Error: Project name required[/red]")
                sys.exit(1)

            project_name = sys.argv[2]
            repo_url = os.environ.get("REPO_URL")
            branch = os.environ.get("TEST_BRANCH")
            repo_path = sys.argv[3] if len(sys.argv) > 3 else "."
            esgvoc_branch = os.environ.get("ESGVOC_LIBRARY_BRANCH")

            success = tester.run_complete_test(project_name, repo_url, branch, repo_path, esgvoc_branch)
            sys.exit(0 if success else 1)

        elif command == "structure":
            repo_path = sys.argv[2] if len(sys.argv) > 2 else "."
            success = tester.test_repository_structure(repo_path)
            sys.exit(0 if success else 1)

        elif command == "api":
            if len(sys.argv) < 3:
                console.print("[red]Error: Project name required[/red]")
                sys.exit(1)

            project_name = sys.argv[2]
            repo_path = sys.argv[3] if len(sys.argv) > 3 else "."
            success = tester.test_esgvoc_api_access(project_name, repo_path)
            sys.exit(0 if success else 1)

        else:
            console.print(f"[red]Error: Unknown command '{command}'[/red]")
            sys.exit(1)

    finally:
        tester.cleanup()


if __name__ == "__main__":
    main()

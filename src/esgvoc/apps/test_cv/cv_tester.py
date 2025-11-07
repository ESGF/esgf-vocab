#!/usr/bin/env python3
"""
CV Testing Application for ESGVoc

This application allows testing of project CVs and Universe CVs with support for:
- Custom repository URLs and branches via CLI options and environment variables
- Universe branch override for testing against different WCRP-universe versions
- Validation of repository structure and content
- Testing YAML specification files (project_specs.yaml, drs_specs.yaml, catalog_spec.yaml, attr_specs.yaml)
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
        "cordex-cmip6": ["cordex-cmip6", "cordex", "cordexcmip6"],
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

    def __init__(self, debug_missing_terms: bool = True):
        self.original_config_name = None
        self.test_config_name = "test_cv_temp"
        self.config_manager = None
        self.debug_missing_terms = debug_missing_terms

    def get_available_projects(self) -> List[str]:
        """Get list of all available project CVs"""
        return list(ServiceSettings._get_default_project_configs().keys())

    def configure_for_testing(
        self,
        project_name: str = None,
        repo_url: str = None,
        branch: str = None,
        esgvoc_branch: str = None,
        universe_branch: str = None,
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
                default_config = ServiceSettings._get_default_project_configs()[project_name]
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
                project_config = ServiceSettings._get_default_project_configs()[project_name].copy()
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
            console.print(
                f"[dim]Debug: StateService universe base_dir: {service.current_state.universe.base_dir}[/dim]"
            )
            console.print(
                f"[dim]Debug: StateService universe local_path: {service.current_state.universe.local_path}[/dim]"
            )

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

            # Add context validation warnings (only if collection passed basic validation)
            if not collection_errors:
                context_warnings = self._validate_context_usage(directory, directory.name)
                for warning in context_warnings:
                    console.print(f"   {warning}")

        # Test YAML specification files if they exist
        yaml_specs_errors = self._test_yaml_specs(repo_dir, collection_directories)
        errors.extend(yaml_specs_errors)

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

    def _test_yaml_specs(self, repo_dir: Path, collection_directories: List[Path]) -> List[str]:
        """Test YAML specification files (project_specs.yaml, drs_specs.yaml, catalog_spec.yaml, attr_specs.yaml)"""
        errors = []

        # Add clear section header
        console.print(f"\n[bold blue]📋 Testing YAML Specification Files[/bold blue]")
        console.print(f"[dim]Repository path: {repo_dir}[/dim]")

        # Import constants and YAML handling
        try:
            from esgvoc.core.constants import (
                PROJECT_SPECS_FILENAME,
                DRS_SPECS_FILENAME,
                CATALOG_SPECS_FILENAME,
                ATTRIBUTES_SPECS_FILENAME
            )
        except ImportError as e:
            error_msg = f"❌ Missing required esgvoc constants: {e}"
            errors.append(error_msg)
            console.print(f"[red]{error_msg}[/red]")
            return errors

        try:
            import yaml
        except ImportError:
            error_msg = f"❌ PyYAML not installed. Install with: pip install PyYAML"
            errors.append(error_msg)
            console.print(f"[red]{error_msg}[/red]")
            return errors

        # Get existing collections for validation
        existing_collections = {d.name for d in collection_directories}
        source_collections = set()
        # Track which files contain each collection reference for better error reporting
        collection_file_mapping = {}  # collection_name -> set of files that reference it
        files_tested = 0

        # Test project_specs.yaml
        project_specs_file = repo_dir / PROJECT_SPECS_FILENAME
        if project_specs_file.exists():
            console.print(f"📄 Testing {PROJECT_SPECS_FILENAME}...")
            try:
                with open(project_specs_file, "r", encoding="utf-8") as f:
                    project_specs = yaml.safe_load(f)
                console.print(f"   [green]✅ {PROJECT_SPECS_FILENAME} parsed successfully[/green]")
                files_tested += 1
            except yaml.YAMLError as e:
                error_msg = f"❌ {PROJECT_SPECS_FILENAME}: Invalid YAML syntax - {e}"
                errors.append(error_msg)
                console.print(f"   [red]{error_msg}[/red]")
            except Exception as e:
                error_msg = f"❌ Error reading {PROJECT_SPECS_FILENAME}: {e}"
                errors.append(error_msg)
                console.print(f"   [red]{error_msg}[/red]")
        else:
            error_msg = f"❌ Required file {PROJECT_SPECS_FILENAME} not found"
            errors.append(error_msg)
            console.print(f"📄 [red]{error_msg}[/red]")

        # Test drs_specs.yaml
        drs_specs_file = repo_dir / DRS_SPECS_FILENAME
        if drs_specs_file.exists():
            console.print(f"📄 Testing {DRS_SPECS_FILENAME}...")
            try:
                with open(drs_specs_file, "r", encoding="utf-8") as f:
                    drs_specs = yaml.safe_load(f)

                # Extract collection references from DRS specs
                for drs_name, drs_spec in drs_specs.items():
                    if isinstance(drs_spec, dict) and "parts" in drs_spec:
                        for part in drs_spec["parts"]:
                            if isinstance(part, dict):
                                # Handle both old format (collection_id) and new format (source_collection)
                                collection_ref = part.get("collection_id") or part.get("source_collection")
                                if collection_ref:
                                    source_collections.add(collection_ref)
                                    if collection_ref not in collection_file_mapping:
                                        collection_file_mapping[collection_ref] = set()
                                    collection_file_mapping[collection_ref].add(DRS_SPECS_FILENAME)

                console.print(f"   [green]✅ {DRS_SPECS_FILENAME} parsed successfully[/green]")
                files_tested += 1
            except yaml.YAMLError as e:
                error_msg = f"❌ {DRS_SPECS_FILENAME}: Invalid YAML syntax - {e}"
                errors.append(error_msg)
                console.print(f"   [red]{error_msg}[/red]")
            except Exception as e:
                error_msg = f"❌ Error reading {DRS_SPECS_FILENAME}: {e}"
                errors.append(error_msg)
                console.print(f"   [red]{error_msg}[/red]")
        else:
            error_msg = f"❌ Required file {DRS_SPECS_FILENAME} not found"
            errors.append(error_msg)
            console.print(f"📄 [red]{error_msg}[/red]")

        # Test catalog_spec.yaml (optional)
        catalog_specs_file = repo_dir / CATALOG_SPECS_FILENAME
        if catalog_specs_file.exists():
            console.print(f"📄 Testing {CATALOG_SPECS_FILENAME}...")
            try:
                with open(catalog_specs_file, "r", encoding="utf-8") as f:
                    catalog_specs = yaml.safe_load(f)

                # Extract collection references from catalog specs
                if isinstance(catalog_specs, dict):
                    # Check dataset_properties and file_properties
                    for prop_type in ["dataset_properties", "file_properties"]:
                        if prop_type in catalog_specs and isinstance(catalog_specs[prop_type], list):
                            for prop in catalog_specs[prop_type]:
                                if isinstance(prop, dict) and "source_collection" in prop:
                                    collection_ref = prop["source_collection"]
                                    # Skip None values - collections can now be null in YAML
                                    if collection_ref is not None:
                                        source_collections.add(collection_ref)
                                        if collection_ref not in collection_file_mapping:
                                            collection_file_mapping[collection_ref] = set()
                                        collection_file_mapping[collection_ref].add(CATALOG_SPECS_FILENAME)

                console.print(f"   [green]✅ {CATALOG_SPECS_FILENAME} parsed successfully[/green]")
                files_tested += 1
            except yaml.YAMLError as e:
                error_msg = f"❌ {CATALOG_SPECS_FILENAME}: Invalid YAML syntax - {e}"
                errors.append(error_msg)
                console.print(f"   [red]{error_msg}[/red]")
            except Exception as e:
                error_msg = f"❌ Error reading {CATALOG_SPECS_FILENAME}: {e}"
                errors.append(error_msg)
                console.print(f"   [red]{error_msg}[/red]")
        else:
            console.print(f"   [yellow]⚠️  Optional file {CATALOG_SPECS_FILENAME} not found[/yellow]")

        # Test attr_specs.yaml (now ingested by esgvoc as confirmed by project_ingestion.py updates)
        attr_specs_file = repo_dir / ATTRIBUTES_SPECS_FILENAME
        if attr_specs_file.exists():
            console.print(f"📄 Testing {ATTRIBUTES_SPECS_FILENAME}...")
            try:
                with open(attr_specs_file, "r", encoding="utf-8") as f:
                    attr_specs = yaml.safe_load(f)

                # Extract collection references from attribute specs
                if isinstance(attr_specs, list):
                    # New format: list of AttributeProperty objects
                    for attr_spec in attr_specs:
                        if isinstance(attr_spec, dict) and "source_collection" in attr_spec:
                            collection_ref = attr_spec["source_collection"]
                            # Skip None values - collections can now be null in YAML
                            if collection_ref is not None:
                                source_collections.add(collection_ref)
                                if collection_ref not in collection_file_mapping:
                                    collection_file_mapping[collection_ref] = set()
                                collection_file_mapping[collection_ref].add(ATTRIBUTES_SPECS_FILENAME)
                elif isinstance(attr_specs, dict):
                    # Legacy format: nested structure with "specs" key
                    if "specs" in attr_specs:
                        specs = attr_specs["specs"]
                        if isinstance(specs, dict):
                            for attr_name, attr_spec in specs.items():
                                if isinstance(attr_spec, dict) and "source_collection" in attr_spec:
                                    collection_ref = attr_spec["source_collection"]
                                    # Skip None values - collections can now be null in YAML
                                    if collection_ref is not None:
                                        source_collections.add(collection_ref)
                                        if collection_ref not in collection_file_mapping:
                                            collection_file_mapping[collection_ref] = set()
                                        collection_file_mapping[collection_ref].add(ATTRIBUTES_SPECS_FILENAME)
                        elif isinstance(specs, list):
                            for attr_spec in specs:
                                if isinstance(attr_spec, dict) and "source_collection" in attr_spec:
                                    collection_ref = attr_spec["source_collection"]
                                    # Skip None values - collections can now be null in YAML
                                    if collection_ref is not None:
                                        source_collections.add(collection_ref)
                                        if collection_ref not in collection_file_mapping:
                                            collection_file_mapping[collection_ref] = set()
                                        collection_file_mapping[collection_ref].add(ATTRIBUTES_SPECS_FILENAME)

                console.print(f"   [green]✅ {ATTRIBUTES_SPECS_FILENAME} parsed successfully[/green]")
                files_tested += 1
            except yaml.YAMLError as e:
                error_msg = f"❌ {ATTRIBUTES_SPECS_FILENAME}: Invalid YAML syntax - {e}"
                errors.append(error_msg)
                console.print(f"   [red]{error_msg}[/red]")
            except Exception as e:
                error_msg = f"❌ Error reading {ATTRIBUTES_SPECS_FILENAME}: {e}"
                errors.append(error_msg)
                console.print(f"   [red]{error_msg}[/red]")
        else:
            console.print(f"   [yellow]⚠️  Optional file {ATTRIBUTES_SPECS_FILENAME} not found[/yellow]")

        # Validate collection references
        console.print(f"\n📂 Validating collection references...")
        if source_collections:
            console.print(f"   Found {len(source_collections)} source_collection references")

            for collection in source_collections:
                if collection not in existing_collections:
                    # Enhanced error message showing which files contain the reference
                    referencing_files = collection_file_mapping.get(collection, set())
                    files_list = ", ".join(sorted(referencing_files))
                    error_msg = f"❌ YAML specs reference non-existent collection: '{collection}' (referenced in: {files_list})"
                    errors.append(error_msg)
                    console.print(f"   [red]{error_msg}[/red]")
                else:
                    console.print(f"   [green]✅ Reference '{collection}' exists[/green]")
        else:
            console.print("   [yellow]⚠️  No collection references found in YAML specs[/yellow]")

        # Final YAML validation summary
        console.print(f"\n📊 YAML Validation Summary:")
        if files_tested == 0:
            error_msg = "❌ No YAML specification files found"
            errors.append(error_msg)
            console.print(f"   [red]{error_msg}[/red]")
        else:
            if errors:
                console.print(f"   [red]❌ {len(errors)} errors found in YAML files[/red]")
            else:
                console.print(f"   [green]✅ All {files_tested} YAML specification files are valid[/green]")

            console.print(f"   [blue]Files tested: {files_tested}[/blue]")

        return errors

    def _test_esgvoc_specs_ingestion(self, project_name: str, repo_dir: Path) -> List[str]:
        """Test that YAML specs are properly ingested into esgvoc and accessible via API"""
        errors = []

        try:
            # Import esgvoc API and constants
            import esgvoc.api as ev
            from esgvoc.core.constants import ATTRIBUTES_SPECS_FILENAME
        except ImportError as e:
            errors.append(f"❌ Cannot import esgvoc modules for ingestion testing: {e}")
            return errors

        try:
            import yaml
        except ImportError:
            errors.append(f"❌ PyYAML not installed. Install with: pip install PyYAML")
            return errors

        console.print(f"🔍 Testing esgvoc ingestion compatibility for {project_name}...")

        # Get the project specs from esgvoc
        try:
            project = ev.get_project(project_name)
            console.print(f"   [green]✅ Project '{project_name}' found in esgvoc[/green]")

            if hasattr(project, 'attr_specs') and hasattr(project, 'drs_specs'):
                # Project is properly loaded with specs - convert to dict format for compatibility
                specs = {}
                if hasattr(project, 'attr_specs') and project.attr_specs:
                    specs["attr_specs"] = project.attr_specs
                if hasattr(project, 'drs_specs') and project.drs_specs:
                    specs["drs_specs"] = project.drs_specs
                if hasattr(project, 'catalog_specs') and project.catalog_specs:
                    specs["catalog_specs"] = project.catalog_specs

                console.print(f"   [blue]📊 Project specs loaded with keys: {list(specs.keys())}[/blue]")

                # Test attr_specs ingestion specifically
                attr_specs_file = repo_dir / ATTRIBUTES_SPECS_FILENAME
                if attr_specs_file.exists() and "attr_specs" in specs:
                    console.print(f"   [green]✅ attr_specs found in ingested project data[/green]")

                    # Load the original YAML for comparison
                    with open(attr_specs_file, "r", encoding="utf-8") as f:
                        original_attr_specs = yaml.safe_load(f)

                    ingested_attr_specs = specs["attr_specs"]

                    # Validate structure compatibility
                    if isinstance(original_attr_specs, list) and isinstance(ingested_attr_specs, list):
                        console.print(f"   [green]✅ attr_specs structure matches: {len(original_attr_specs)} items in YAML, {len(ingested_attr_specs)} items ingested[/green]")

                        # Check for source_collection fields
                        yaml_collections = set()
                        ingested_collections = set()

                        for item in original_attr_specs:
                            if isinstance(item, dict) and "source_collection" in item:
                                collection_ref = item["source_collection"]
                                # Skip None values - collections can now be null in YAML
                                if collection_ref is not None:
                                    yaml_collections.add(collection_ref)

                        for item in ingested_attr_specs:
                            if isinstance(item, dict) and "source_collection" in item:
                                collection_ref = item["source_collection"]
                                if collection_ref is not None:
                                    ingested_collections.add(collection_ref)
                            elif hasattr(item, "source_collection"):
                                # Handle Pydantic model objects
                                collection_ref = item.source_collection
                                if collection_ref is not None:
                                    ingested_collections.add(collection_ref)

                        if yaml_collections == ingested_collections:
                            console.print(f"   [green]✅ Collection references preserved: {sorted(yaml_collections)}[/green]")
                        else:
                            errors.append(f"❌ Collection reference mismatch - YAML: {sorted(yaml_collections)}, Ingested: {sorted(ingested_collections)}")
                    else:
                        console.print(f"   [yellow]⚠️  Structure difference: YAML type={type(original_attr_specs)}, Ingested type={type(ingested_attr_specs)}[/yellow]")

                elif attr_specs_file.exists():
                    errors.append(f"❌ attr_specs.yaml exists but not found in ingested project specs")

                # Test drs_specs ingestion
                if "drs_specs" in specs:
                    console.print(f"   [green]✅ drs_specs found in ingested project data[/green]")
                else:
                    errors.append(f"❌ drs_specs not found in ingested project data")

                # Test catalog_specs ingestion
                if "catalog_specs" in specs:
                    console.print(f"   [green]✅ catalog_specs found in ingested project data[/green]")
                else:
                    console.print(f"   [yellow]⚠️  catalog_specs not found in ingested project data (may be optional)[/yellow]")

            else:
                # More detailed error message about missing specs
                expected_specs = ["project_specs", "attr_specs", "drs_specs", "catalog_specs (optional)"]
                if hasattr(project, 'attr_specs') or hasattr(project, 'drs_specs'):
                    missing_specs = []
                    if not hasattr(project, 'attr_specs') or not project.attr_specs:
                        missing_specs.append("attr_specs")
                    if not hasattr(project, 'drs_specs') or not project.drs_specs:
                        missing_specs.append("drs_specs")
                    errors.append(f"❌ Project '{project_name}' missing required specs: {missing_specs}. Expected specs: {', '.join(expected_specs)}")
                else:
                    errors.append(f"❌ Project '{project_name}' has no specs attributes. Expected specs: {', '.join(expected_specs)}")

        except Exception as e:
            errors.append(f"❌ Failed to retrieve project '{project_name}' from esgvoc: {e}")

        return errors

    def _debug_missing_term(self, project_name: str, collection_name: str, term_id: str, repo_path: str = "."):
        """
        Provide detailed debugging information for a missing term.

        Args:
            project_name: Name of the project
            collection_name: Name of the collection
            term_id: ID of the missing term
            repo_path: Path to the repository
        """
        console.print(f"\n[bold yellow]🔍 Debugging missing term: {term_id} in {collection_name}[/bold yellow]")

        repo_dir = Path(repo_path)
        collection_dir = repo_dir / collection_name

        # 1. Check if term exists in project repository
        term_file = collection_dir / f"{term_id}.json"
        console.print(f"\n[blue]📁 Project Repository ({project_name}):[/blue]")

        if term_file.exists():
            try:
                with open(term_file, "r", encoding="utf-8") as f:
                    term_content = json.load(f)
                console.print(f"  [green]✅ Term found in project: {term_file}[/green]")
                console.print("  [dim]Content:[/dim]")
                formatted_json = json.dumps(term_content, indent=2, ensure_ascii=False)
                for line in formatted_json.split("\n"):
                    console.print(f"    {line}")
            except Exception as e:
                console.print(f"  [red]❌ Error reading term file: {e}[/red]")
        else:
            console.print(f"  [red]❌ Term not found in project: {term_file}[/red]")

            # Try to find the term by searching for files that contain this term_id
            console.print(f"  [dim]Searching for files containing term ID '{term_id}'...[/dim]")
            try:
                for json_file in collection_dir.glob("*.json"):
                    if json_file.name.endswith(".jsonld"):
                        continue
                    try:
                        with open(json_file, "r", encoding="utf-8") as f:
                            content = json.load(f)
                        if content.get("id") == term_id:
                            console.print(f"  [yellow]📄 Found term ID '{term_id}' in file: {json_file.name}[/yellow]")
                            console.print(f"  [dim]Note: Filename '{json_file.name}' ≠ expected '{term_id}.json'[/dim]")
                            console.print("  [dim]Content:[/dim]")
                            formatted_json = json.dumps(content, indent=2, ensure_ascii=False)
                            for line in formatted_json.split("\n"):
                                console.print(f"    {line}")
                            break
                    except Exception:
                        continue
                else:
                    console.print(f"  [dim]No file found containing term ID '{term_id}'[/dim]")
            except Exception as e:
                console.print(f"  [dim]Error searching for term: {e}[/dim]")

        # 2. Check if term exists in universe (using DataMerger to resolve links)
        try:
            current_state = service.get_state()
            if hasattr(current_state, "universe") and current_state.universe.local_path:
                universe_dir = Path(current_state.universe.local_path)

                console.print(f"\n[blue]🌌 Universe Repository (resolved via DataMerger):[/blue]")

                # First, try to use DataMerger to resolve the universe term if project term exists
                resolved_universe_term = None
                universe_term_path = None
                project_term_content = None

                if term_file.exists():
                    try:
                        # First, read the project term to see what it links to
                        with open(term_file, "r", encoding="utf-8") as f:
                            project_term_content = json.load(f)

                        from esgvoc.core.data_handler import JsonLdResource
                        from esgvoc.core.service.data_merger import DataMerger

                        # Use DataMerger to resolve the universe term like in project_ingestion.py
                        locally_avail = {
                            "https://espri-mod.github.io/mip-cmor-tables": str(current_state.universe.local_path)
                        }

                        console.print(f"  [dim]Attempting DataMerger resolution...[/dim]")

                        # Check if project term has an @id link
                        if "@id" in project_term_content:
                            console.print(f"  [dim]Project term @id: {project_term_content['@id']}[/dim]")

                            # Calculate expected universe path
                            if "https://espri-mod.github.io/mip-cmor-tables" in project_term_content["@id"]:
                                universe_relative_path = project_term_content["@id"].replace(
                                    "https://espri-mod.github.io/mip-cmor-tables/", ""
                                )
                                if not universe_relative_path.endswith(".json"):
                                    universe_relative_path += ".json"
                                universe_term_path = universe_dir / universe_relative_path
                                console.print(f"  [dim]Expected universe path: {universe_term_path}[/dim]")
                        else:
                            console.print(f"  [dim]Project term has no @id link to universe[/dim]")
                            # Even without @id, try to infer the universe path from context base
                            try:
                                # Read the context file to get the base
                                context_file = term_file.parent / "000_context.jsonld"
                                if context_file.exists():
                                    with open(context_file, "r", encoding="utf-8") as f:
                                        context_content = json.load(f)

                                    base_url = context_content.get("@context", {}).get("@base", "")
                                    if base_url and "https://espri-mod.github.io/mip-cmor-tables" in base_url:
                                        universe_relative_path = (
                                            base_url.replace("https://espri-mod.github.io/mip-cmor-tables/", "")
                                            + f"{term_id}.json"
                                        )
                                        universe_term_path = universe_dir / universe_relative_path
                                        console.print(f"  [dim]Inferred from context @base: {universe_term_path}[/dim]")
                            except Exception as e:
                                console.print(f"  [dim]Could not infer universe path from context: {e}[/dim]")

                        # Debug: Check what the JsonLdResource expansion produces
                        json_resource = JsonLdResource(uri=str(term_file))
                        console.print(f"  [dim]JSON-LD expanded form: {json_resource.expanded}[/dim]")

                        merger_result = DataMerger(
                            data=json_resource,
                            locally_available=locally_avail,
                        ).merge_linked_json()

                        if merger_result and len(merger_result) > 1:
                            # If we have more than one result, the last one is the fully merged term
                            resolved_universe_term = merger_result[-1]

                            console.print(f"  [green]✅ Term resolved via DataMerger (merged from universe)[/green]")
                            if universe_term_path:
                                console.print(f"  [dim]Resolved universe path: {universe_term_path}[/dim]")
                                console.print(
                                    f"  [dim]Universe file exists: {universe_term_path.exists() if universe_term_path else 'N/A'}[/dim]"
                                )
                            console.print("  [dim]Merged content:[/dim]")
                            formatted_json = json.dumps(resolved_universe_term, indent=2, ensure_ascii=False)
                            for line in formatted_json.split("\n"):
                                console.print(f"    {line}")
                        else:
                            console.print(
                                f"  [yellow]⚠️  No universe term linked from project term (merge result length: {len(merger_result) if merger_result else 0})[/yellow]"
                            )

                    except Exception as e:
                        console.print(f"  [red]❌ Error using DataMerger to resolve universe term: {e}[/red]")
                        # Still show what the project term was trying to link to
                        if project_term_content and "@id" in project_term_content:
                            console.print(
                                f"  [dim]Project term was trying to link to: {project_term_content['@id']}[/dim]"
                            )
                            universe_relative_path = project_term_content["@id"].replace(
                                "https://espri-mod.github.io/mip-cmor-tables/", ""
                            )
                            if not universe_relative_path.endswith(".json"):
                                universe_relative_path += ".json"
                            universe_term_path = universe_dir / universe_relative_path
                            console.print(
                                f"  [dim]Expected universe file: {universe_term_path} (exists: {universe_term_path.exists() if universe_term_path else False})[/dim]"
                            )

                # Fallback: also check direct universe path and show resolved universe file if it was calculated
                if not resolved_universe_term:
                    # Show the resolved path from DataMerger if we have it
                    if universe_term_path and universe_term_path.exists():
                        try:
                            with open(universe_term_path, "r", encoding="utf-8") as f:
                                universe_term_content = json.load(f)
                            console.print(
                                f"  [green]✅ Universe file found at resolved path: {universe_term_path}[/green]"
                            )
                            console.print("  [dim]Content:[/dim]")
                            formatted_json = json.dumps(universe_term_content, indent=2, ensure_ascii=False)
                            for line in formatted_json.split("\n"):
                                console.print(f"    {line}")
                        except Exception as e:
                            console.print(f"  [red]❌ Error reading resolved universe file: {e}[/red]")
                    else:
                        # Show detailed path info - don't try direct collection path since it's wrong
                        console.print(f"  [red]❌ Term not found in universe:[/red]")
                        if universe_term_path:
                            console.print(
                                f"    [dim]• DataMerger resolved path: {universe_term_path} (exists: {universe_term_path.exists()})[/dim]"
                            )

                        # Try direct collection-based path as fallback (but note this may be incorrect for project collections vs universe structure)
                        universe_collection_dir = universe_dir / collection_name
                        universe_term_file = universe_collection_dir / f"{term_id}.json"
                        console.print(
                            f"    [dim]• Direct collection path: {universe_term_file} (exists: {universe_term_file.exists()})[/dim]"
                        )

                        # Try to find similar files in the universe to help debugging
                        try:
                            if universe_term_path:
                                parent_dir = universe_term_path.parent
                                if parent_dir.exists():
                                    similar_files = [
                                        f.name
                                        for f in parent_dir.iterdir()
                                        if f.is_file() and f.suffix == ".json" and term_id.lower() in f.name.lower()
                                    ]
                                    if similar_files:
                                        console.print(
                                            f"    [dim]• Similar files in {parent_dir.name}: {similar_files}[/dim]"
                                        )

                                    # Also check if there are files with different casing
                                    all_files = [
                                        f.name for f in parent_dir.iterdir() if f.is_file() and f.suffix == ".json"
                                    ]
                                    casing_matches = [f for f in all_files if f.lower() == f"{term_id.lower()}.json"]
                                    if casing_matches and casing_matches[0] != f"{term_id}.json":
                                        console.print(
                                            f"    [dim]• Case mismatch found: {casing_matches[0]} vs {term_id}.json[/dim]"
                                        )
                        except Exception:
                            pass
            else:
                console.print(f"  [yellow]⚠️  Universe path not available[/yellow]")
        except Exception as e:
            console.print(f"  [red]❌ Error accessing universe: {e}[/red]")

        # 3. Try to query the term via esgvoc API
        console.print(f"\n[blue]🔗 ESGVoc API Query:[/blue]")
        try:
            import esgvoc.api as ev

            # Try to get the term from project
            try:
                project_terms = ev.get_all_terms_in_collection(project_name, collection_name)
                matching_terms = [term for term in project_terms if term.id == term_id]
                if matching_terms:
                    term = matching_terms[0]
                    console.print(f"  [green]✅ Term found in esgvoc project API[/green]")
                    console.print(f"    ID: {term.id}")
                    console.print(f"    Type: {term.type}")
                    console.print(f"    Label: {getattr(term, 'label', 'N/A')}")
                    console.print(f"    Description: {getattr(term, 'description', 'N/A')[:100]}...")
                else:
                    console.print(f"  [red]❌ Term not found in esgvoc project API[/red]")
            except Exception as e:
                console.print(f"  [red]❌ Error querying project API: {e}[/red]")

            # Try to get the term from universe (if available)
            try:
                universe_terms = ev.get_all_terms_in_collection("universe", collection_name)
                matching_universe_terms = [term for term in universe_terms if term.id == term_id]
                if matching_universe_terms:
                    term = matching_universe_terms[0]
                    console.print(f"  [green]✅ Term found in esgvoc universe API[/green]")
                    console.print(f"    ID: {term.id}")
                    console.print(f"    Type: {term.type}")
                    console.print(f"    Label: {getattr(term, 'label', 'N/A')}")
                    console.print(f"    Description: {getattr(term, 'description', 'N/A')[:100]}...")
                else:
                    console.print(f"  [red]❌ Term not found in esgvoc universe API[/red]")
            except Exception as e:
                console.print(f"  [red]❌ Error querying universe API: {e}[/red]")

        except Exception as e:
            console.print(f"  [red]❌ Error importing esgvoc API: {e}[/red]")

    def _validate_context_usage(self, collection_dir: Path, collection_name: str) -> list:
        """
        Validate context usage and detect potential issues.

        Returns:
            list: List of warning messages
        """
        warnings = []

        try:
            context_file = collection_dir / "000_context.jsonld"
            if not context_file.exists():
                return warnings

            # Read context
            with open(context_file, "r", encoding="utf-8") as f:
                context_data = json.load(f)

            context_mappings = context_data.get("@context", {})
            if not isinstance(context_mappings, dict):
                return warnings

            # Get all JSON term files
            term_files = [f for f in collection_dir.glob("*.json") if not f.name.endswith(".jsonld")]

            # Track context key usage
            context_keys_used = set()
            term_properties_used = set()
            terms_using_base_expansion = []

            for term_file in term_files:
                try:
                    with open(term_file, "r", encoding="utf-8") as f:
                        term_content = json.load(f)

                    # Check what properties and values are used in the term
                    for key, value in term_content.items():
                        if key not in ["@context", "@id", "@type"]:
                            term_properties_used.add(key)

                            # Check if this property has a shortcut in context
                            if key in context_mappings:
                                context_keys_used.add(key)

                        # Check if property values use context shortcuts
                        # For example: "type": "source" where context has "source": "https://..."
                        if isinstance(value, str) and value in context_mappings:
                            context_keys_used.add(value)

                    # Check if term relies on @base expansion (has simple id but no explicit @id)
                    term_id = term_content.get("id", term_file.stem)
                    if "id" in term_content and "@id" not in term_content and "@base" in context_mappings:
                        terms_using_base_expansion.append({"file": term_file.name, "id": term_id})

                except Exception as e:
                    continue

            # Check for unused context keys (excluding standard JSON-LD keys)
            standard_keys = {"@base", "@vocab", "@language", "@version", "id", "type"}
            defined_keys = set(context_mappings.keys()) - standard_keys
            unused_keys = defined_keys - context_keys_used

            if unused_keys:
                warnings.append(f"⚠️  Context defines unused keys in '{collection_name}': {sorted(unused_keys)}")

            # Check for properties without shortcuts
            properties_without_shortcuts = term_properties_used - context_keys_used - {"id", "type"}
            if properties_without_shortcuts:
                warnings.append(
                    f"⚠️  Properties used without context shortcuts in '{collection_name}': {sorted(properties_without_shortcuts)}"
                )

            # Check for filename/ID mismatches
            filename_id_mismatches = []
            for term_file in term_files:
                try:
                    with open(term_file, "r", encoding="utf-8") as f:
                        term_content = json.load(f)

                    expected_id = term_file.stem  # filename without .json extension
                    actual_id = term_content.get("id")

                    if actual_id and actual_id != expected_id:
                        filename_id_mismatches.append(
                            {"file": term_file.name, "expected_id": expected_id, "actual_id": actual_id}
                        )
                except Exception:
                    continue

            if filename_id_mismatches:
                warnings.append(f"⚠️  Filename/ID mismatches in '{collection_name}':")
                for mismatch in filename_id_mismatches[:5]:  # Show first 5
                    warnings.append(
                        f"     • {mismatch['file']}: id='{mismatch['actual_id']}' (expected '{mismatch['expected_id']}')"
                    )
                if len(filename_id_mismatches) > 5:
                    warnings.append(f"     • ... and {len(filename_id_mismatches) - 5} more mismatches")

            # Base expansion is normal JSON-LD behavior - only report if there might be issues
            # For now, we'll skip this since @base expansion is the expected pattern

            # Only warn about @base vs shortcuts if they're used for the same purpose
            # @base is for term identity URLs, shortcuts are for property/type values - this is normal
            # We could add more sophisticated conflict detection here if needed

        except Exception as e:
            warnings.append(f"⚠️  Error validating context usage in '{collection_name}': {e}")

        return warnings

    def _validate_universe_warnings(self) -> bool:
        """
        Validate universe repository for potential issues and display warnings.

        Returns:
            bool: True if universe validation completed (warnings don't fail the test)
        """
        try:
            current_state = service.get_state()
            if not hasattr(current_state, "universe") or not current_state.universe.local_path:
                console.print(f"[dim]⚠️  Universe path not available for validation[/dim]")
                return True

            universe_dir = Path(current_state.universe.local_path)
            if not universe_dir.exists():
                console.print(f"[dim]⚠️  Universe directory not found: {universe_dir}[/dim]")
                return True

            console.print(f"[blue]🌌 Validating Universe Repository: {universe_dir.name}[/blue]")

            # Find universe collections (directories with JSON files)
            universe_collections = []
            for item in universe_dir.iterdir():
                if item.is_dir():
                    json_files = list(item.glob("*.json"))
                    jsonld_files = [f for f in json_files if f.name.endswith(".jsonld")]
                    regular_json_files = [f for f in json_files if not f.name.endswith(".jsonld")]

                    if regular_json_files:
                        universe_collections.append(item)

            console.print(f"Found {len(universe_collections)} universe collections to validate")

            total_warnings = 0
            for collection_dir in universe_collections:
                warnings = self._validate_context_usage(collection_dir, collection_dir.name)
                if warnings:
                    console.print(f"📁 Universe collection '{collection_dir.name}':")
                    for warning in warnings:
                        console.print(f"   {warning}")
                        total_warnings += 1

            if total_warnings == 0:
                console.print("✅ No validation warnings found in universe")
            else:
                console.print(f"⚠️  Found {total_warnings} validation warnings in universe")

            console.print("")  # Add spacing before project validation
            return True

        except Exception as e:
            console.print(f"[red]❌ Error validating universe: {e}[/red]")
            return True  # Don't fail the test for universe validation errors

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
            if hasattr(e, "errors") and e.errors():
                for error in e.errors():
                    if "input" in error and "ctx" in error:
                        error_msg += f"\n   • Invalid value: '{error['input']}'"
                        if "enum_values" in error["ctx"]:
                            error_msg += f"\n   • Expected one of: {error['ctx']['enum_values']}"
                        if error.get("type") == "enum":
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
                repo_element_sources = {}  # Track where each ID comes from
                for json_file in json_files:
                    try:
                        with open(json_file, "r", encoding="utf-8") as f:
                            content = json.load(f)
                        element_id = content.get("id", json_file.stem)
                        repo_elements.append(element_id)
                        repo_element_sources[element_id] = {"file": json_file.name, "from_id_field": "id" in content}
                    except:
                        element_id = json_file.stem
                        repo_elements.append(element_id)
                        repo_element_sources[element_id] = {"file": json_file.name, "from_id_field": False}

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

                        # Debug missing elements source tracking
                        if self.debug_missing_terms:
                            console.print(f"   [dim]Missing elements and their sources:[/dim]")
                            for elem in missing_elements:
                                source_info = repo_element_sources.get(
                                    elem, {"file": "unknown", "from_id_field": False}
                                )
                                id_source = "id field" if source_info["from_id_field"] else "filename"
                                console.print(f"   [dim]  • {elem} (from {source_info['file']} {id_source})[/dim]")

                        # Detailed debugging for each missing element (if enabled)
                        if self.debug_missing_terms:
                            console.print(
                                f"\n[bold red]📋 Detailed analysis of missing elements in '{collection_name}':[/bold red]"
                            )
                            for missing_element in missing_elements:
                                self._debug_missing_term(project_name, collection_name, missing_element, repo_path)
                        else:
                            console.print(f"[dim]💡 Use --debug-terms for detailed analysis of missing elements[/dim]")
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

        # Step 2.5: Validate universe for warnings
        self._validate_universe_warnings()

        # Step 3: Determine repository path AFTER synchronization - use downloaded CV repository if not specified
        if repo_path is None:
            # Use the state service to get the actual project path directly
            try:
                current_state = service.get_state()
                if hasattr(current_state, "projects") and project_name in current_state.projects:
                    project_state = current_state.projects[project_name]
                    if hasattr(project_state, "local_path") and project_state.local_path:
                        repo_path = str(project_state.local_path)
                        console.print(f"[blue]Using CV repository from state service: {repo_path}[/blue]")
                    else:
                        console.print("[dim]Debug: Project state has no local_path[/dim]")
                else:
                    console.print(f"[dim]Debug: Project {project_name} not found in state service projects[/dim]")
                    console.print(
                        f"[dim]Debug: Available projects in state: {list(current_state.projects.keys()) if hasattr(current_state, 'projects') else 'No projects'}[/dim]"
                    )
            except Exception as e:
                console.print(f"[dim]Debug: Error accessing state service: {e}[/dim]")

            # Fallback: try to find the repository using the known default local path
            if repo_path is None:
                try:
                    from esgvoc.core.service.configuration.setting import ServiceSettings

                    default_configs = ServiceSettings._get_default_project_configs()
                    if project_name in default_configs:
                        default_local_path = default_configs[project_name]["local_path"]
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
        console.print(f"[dim]Debug: About to test repository structure with path: {repo_path}[/dim]")
        try:
            if not self.test_repository_structure(repo_path):
                success = False
        except Exception as e:
            console.print(f"[red]❌ Repository structure test failed with exception: {e}[/red]")
            success = False

        # Debug: Check what configuration is active before API test
        current_active = service.get_config_manager().get_active_config_name()
        console.print(f"[dim]Debug: Active config before API test: {current_active}[/dim]")

        # Step 4: Test YAML specs ingestion compatibility
        console.print(f"[blue]Testing YAML specs ingestion compatibility...[/blue]")
        ingestion_errors = self._test_esgvoc_specs_ingestion(project_name, Path(repo_path))
        if ingestion_errors:
            console.print(f"[red]❌ YAML specs ingestion test failed with {len(ingestion_errors)} errors:[/red]")
            for error in ingestion_errors:
                console.print(f"   {error}")
            success = False
        else:
            console.print(f"[green]✅ YAML specs ingestion test passed![/green]")

        # Step 5: Test esgvoc API access
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
                config = ServiceSettings._get_default_project_configs()[project]
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

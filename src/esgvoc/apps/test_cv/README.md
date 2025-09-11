# CV Testing Application

This application provides comprehensive testing capabilities for project CVs and Universe CVs, allowing validation of repository structure, content, and esgvoc API integration.

## Features

- **Multiple Testing Modes**: Repository structure validation, esgvoc API integration testing
- **Flexible Configuration**: Support for custom repositories, branches, and projects
- **Universe Branch Override**: Ability to test with custom Universe branches for comprehensive testing
- **CLI Integration**: Integrated with the main esgvoc CLI as `esgvoc test`
- **Rich Output**: Colored console output with progress indicators and detailed reporting

## Available Projects

The application supports testing all configured CV projects:

- **cmip6**: CMIP6 controlled vocabularies
- **cmip6plus**: CMIP6Plus controlled vocabularies  
- **input4mip**: Input4MIP controlled vocabularies
- **obs4mip**: Obs4MIP controlled vocabularies
- **cordex-cmip6**: CORDEX-CMIP6 controlled vocabularies

## Usage

### CLI Commands

```bash
# List available projects
esgvoc test list-projects

# Configure esgvoc for testing a specific project
esgvoc test configure obs4mip
esgvoc test configure cmip6 --branch my-test-branch
esgvoc test configure cmip6 --universe-branch my-universe-branch  
esgvoc test configure custom --repo https://github.com/me/cvs --branch main --universe-branch dev

# Test repository structure only
esgvoc test structure .
esgvoc test structure /path/to/cv/repo

# Test esgvoc API access only  
esgvoc test api obs4mip .
esgvoc test api cmip6 /path/to/repo

# Run complete test suite
esgvoc test run obs4mip .
esgvoc test run cmip6 /path/to/repo --branch my-branch
esgvoc test run input4mip --branch esgvoc --universe-branch esgvoc_dev
esgvoc test run custom . --repo https://github.com/me/cvs --branch main --universe-branch dev

# Environment variable mode
export REPO_URL=https://github.com/me/obs4MIPs_CVs
export TEST_BRANCH=test-branch
export UNIVERSE_BRANCH=esgvoc_dev
esgvoc test env configure
esgvoc test env test
```

### Programmatic Usage

```python
from esgvoc.apps.test_cv.cv_tester import CVTester

# Create tester instance
tester = CVTester()

try:
    # Run complete test suite
    success = tester.run_complete_test(
        project_name="obs4mip",
        repo_url="https://github.com/my-org/obs4MIPs_CVs",  # optional
        branch="test-branch",  # optional
        universe_branch="esgvoc_dev",  # optional - custom universe branch
        repo_path="."
    )
    
    if success:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed")

finally:
    # Always cleanup
    tester.cleanup()
```

### Individual Test Components

```python
from esgvoc.apps.test_cv.cv_tester import CVTester

tester = CVTester()

try:
    # 1. Configure esgvoc with custom universe branch
    tester.configure_for_testing(
        project_name="obs4mip", 
        repo_url="https://...", 
        branch="test",
        universe_branch="esgvoc_dev"  # Custom universe branch
    )
    
    # 2. Synchronize CVs
    tester.synchronize_cvs()
    
    # 3. Test repository structure
    tester.test_repository_structure("/path/to/cv/repo")
    
    # 4. Test esgvoc API access
    tester.test_esgvoc_api_access("obs4mip", "/path/to/cv/repo")

finally:
    tester.cleanup()
```

## Universe Branch Override

The application now supports testing with custom Universe branches, allowing comprehensive testing across different versions of the WCRP-universe repository:

### CLI Usage
```bash
# Test with custom universe branch
esgvoc test run input4mip --branch esgvoc --universe-branch esgvoc_dev

# Configure with custom universe branch
esgvoc test configure obs4mip --universe-branch development --sync

# Environment variable mode with universe branch
export UNIVERSE_BRANCH=esgvoc_dev
esgvoc test env test
```

### Programmatic Usage
```python
# Test with custom universe branch
success = tester.run_complete_test(
    project_name="input4mip",
    branch="esgvoc",  # Project branch
    universe_branch="esgvoc_dev",  # Universe branch
)

# Configure with custom universe branch  
success = tester.configure_for_testing(
    project_name="obs4mip",
    universe_branch="development"
)
```

### Use Cases
- **Development Testing**: Test against development universe branches
- **Feature Validation**: Validate new universe features before merging
- **Regression Testing**: Ensure compatibility across universe versions
- **CI/CD Integration**: Test different universe branches in automated workflows

## Test Components

### Repository Structure Validation

Tests repository structure and file format compliance:

- **Collection Directories**: Validates presence of .jsonld context files
- **Element Files**: Validates JSON element file structure and required fields
- **Context Files**: Validates JSONLD context structure and required fields
- **Project Specs**: Validates project_specs.json references to collections

### ESGVoc API Integration Testing  

Tests that all repository content is accessible via esgvoc API:

- **Project Access**: Verifies project is queryable via esgvoc
- **Collection Access**: Validates all repository collections are accessible
- **Element Access**: Confirms all repository elements are queryable
- **API Functions**: Tests general esgvoc API functionality

## Environment Variables

For CI/CD integration and automated testing:

- `REPO_URL`: Repository URL to test (required for `esgvoc test env` mode)
- `TEST_BRANCH`: Branch to test (required for `esgvoc test env` mode)
- `UNIVERSE_BRANCH`: Universe branch to test (optional)
- `PROJECT_NAME`: Project name (auto-detected if not provided)
- `ESGVOC_LIBRARY_BRANCH`: ESGVoc library branch (informational only)


## Files

- `cv_tester.py`: Main CVTester class with all testing functionality
- `example_usage.py`: Usage examples and demonstrations  
- `../cli/test_cv.py`: CLI integration module
- `README.md`: This documentation file

## Error Handling

The application provides detailed error reporting:

- **Configuration Errors**: Issues with project setup or repository access
- **Structure Errors**: Problems with CV file format or organization  
- **API Errors**: Issues with esgvoc integration or data access
- **Synchronization Errors**: Problems downloading or updating CVs

All errors include context and suggestions for resolution.

## Testing Workflow

Recommended testing workflow for CV development:

1. **Configure**: Set up esgvoc with your test repository/branch
2. **Structure**: Validate repository structure and file formats
3. **Sync**: Download/synchronize CVs with esgvoc
4. **API**: Test that all content is accessible via esgvoc API
5. **Cleanup**: Restore original esgvoc state

This ensures comprehensive validation of both the CV repository itself and its integration with the esgvoc system.
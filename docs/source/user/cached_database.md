
# Database and functionality

## Overview of database management

The `esgvoc install` command is responsible for managing the synchronization process between the controlled vocabulary repositories, the local file system, and the SQLite database. This ensures that the database always reflects the most up-to-date state of the repositories. 

### Synchronization workflow
For each configured controlled vocabulary repository, the synchronization process involves the following steps:

1. **Version check**
   - The software determines the current version of each controlled vocabulary by examining the latest commit in three locations:
     - The remote GitHub repository (if internet access).
     - The locally cloned repository (if it exists).
     - The cached SQLite database (if it exists)
.

2. **Database update process**
   - The goal of the synchronization process is to ensure the database reflects the most recent version of the controlled vocabulary.
   - If the local repository does not exist or is outdated, the software clones or updates the repository from GitHub.
   - The SQLite database is rebuilt or updated as necessary to match the most recent version of the controlled vocabulary.

By automating this process, `ESGVOC` guarantees that users have access to the latest available controlled vocabularies without requiring manual intervention.

### Viewing synchronization status
The `esgvoc status` command provides a detailed summary of the current state of synchronization for each controlled vocabulary repository. Specifically, it shows:
- The latest commit version of the remote GitHub repository.
- The latest commit version of the local repository.
- The version of the cached SQLite database.

This information helps users understand whether any part of the system is outdated and requires synchronization.

---

The intended purpose of these databases is to provide an efficient and rapid query system, accessible exclusively through the API or the CLI.


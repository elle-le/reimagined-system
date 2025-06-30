# Azure Access Role Management Script

## Description
This script is designed to manage role assignments for service principals in Azure Active Directory. It allows you to add or remove roles assigned to a group within a specified service principal. The script uses the Microsoft Graph API to interact with Azure AD and supports processing multiple roles in a single execution.

## Features
- **Add Role Assignments**: Assign one or more roles to a group within a service principal.
- **Remove Role Assignments**: Remove one or more roles assigned to a group within a service principal.
- **Dynamic Input**: Accepts input via a JSON file, including group name, roles, and service principal details.

## Prerequisites

### Azure AD Permissions
Ensure the account or service principal running the script has the following Microsoft Graph API permissions:
- `AppRoleAssignment.ReadWrite.All`
- `Group.Read.All`
- `Application.Read.All`

### Python Environment
- Python 3.x installed.
- Required libraries: `requests`, `argparse`, `json`, `azure.identity`.

## Input File Format
The script requires a JSON file as input. Below is an example format:

```json
{
    "group_name": "DL-NAME",
    "roles": [
        "ROLENAME1-sso,azure-idp",
        "ROLENAME1-sso,azure-idp"
    ],
    "app_name": "SERVICE_PRINCIPALL_FULL_NAME_123456789012"
}
```

The `-sso,azure-idp` must be included at the end of the role name, otherwise it can't find it.
The `app_name` must be full name, only the last digits does not work.

## How to Run the Script

### Install Dependencies
Run the following command to install required Python libraries:

```bash
pip install requests azure-identity
```

### Login to Azure
Login via `az login --tenant <tenant-id>`.
The logged in token will be used via script to run the API calls.


### Run the Script
Use the following command to execute the script:

```bash
python3 azurre-access.py <action> <input_file>
```

- `<action>`: Specify `add` to add roles or `rmv` to remove roles.
- `<input_file>`: Path to the JSON file containing input data.

### Examples

#### Add Roles
```bash
python3 azurre-access.py add input.json
```

#### Remove Roles
```bash
python3 azurre-access.py rmv input.json
```

## Output
The script provides detailed output for each operation, including:
- Application ID, Group Object ID, and Role IDs.
- Success or failure messages for role assignments or removals.

## Notes
- Ensure the JSON file is correctly formatted and contains valid data.
- The script handles multiple roles in a single execution and logs errors for individual roles without stopping the entire process.

import os
import requests
import jwt
import argparse
import json
import urllib.parse
from azure.identity import DefaultAzureCredential

# Set up Azure credentials
credential = DefaultAzureCredential()
token = credential.get_token("https://graph.microsoft.com/.default").token

# Define headers for Microsoft Graph API requests
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}


def fetch_group_object_id(group_name):
    """
    Fetch the object ID of a group by its display name.
    """
    # URL-encode the group name
    encoded_group_name = urllib.parse.quote(group_name)
    url = f"https://graph.microsoft.com/v1.0/groups?$filter=displayName eq '{encoded_group_name}'"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    groups = response.json().get("value", [])
    if groups:
        return groups[0]["id"]
    else:
        raise ValueError(f"Group with name '{group_name}' not found.")

def fetch_application_role_id(app_id, role_name):
    """
    Fetch the role ID of an application role by its name.
    """
    url = f"https://graph.microsoft.com/v1.0/servicePrincipals/{app_id}/appRoles"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    roles = response.json().get("value", [])
    for role in roles:
        if role["displayName"] == role_name:
            return role["id"]
    raise ValueError(f"Role with name '{role_name}' not found in application '{app_id}'.")

def fetch_application_id_by_suffix(app_name):
    """
    Fetch the application ID using the last part of the application's name.
    :param app_name: The suffix of the application's display name.
    :return: The application ID.
    """
    url = f"https://graph.microsoft.com/v1.0/servicePrincipals?$filter=displayName eq '{app_name}'"
    while url:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        applications = response.json().get("value", [])
        for app in applications:
            if app['displayName'] == app_name:
                print(f"Matched Service Principal: {app['displayName']}")  # Debugging output
                return app["id"]
        # Check for pagination
        url = response.json().get("@odata.nextLink", None)
    raise ValueError(f"Application with name ending in '{app_name}' not found.")


def add_group_to_enterprise_app(app_object_id, group_object_id, role_definition_id, role_name):
    """
    Add a group with a specific role to an enterprise application.

    :param app_object_id: The object ID of the enterprise application.
    :param group_object_id: The object ID of the group.
    :param role_definition_id: The ID of the role definition to assign.
    """
    try:
        # Check if the role is already assigned
        if is_group_assigned_with_role(app_object_id, group_object_id, role_definition_id, role_name):
            print("Role is already assigned to the group. Skipping assignment.")
            return

        # Assign the role to the group within the enterprise application
        url = f"https://graph.microsoft.com/v1.0/servicePrincipals/{app_object_id}/appRoleAssignments"
        role_assignment_params = {
            "principalId": group_object_id,
            "appRoleId": role_definition_id,
            "resourceId": app_object_id  # Service principal ID
        }
        response = requests.post(url, headers=headers, json=role_assignment_params)
        response.raise_for_status()
        print(f"Role assigned successfully to group in enterprise app: {response.json()['id']}")
    except Exception as e:
        print(f"Failed to assign role to group in enterprise app: {e}")


def is_group_assigned_with_role(app_object_id, group_object_id, role_definition_id, role_name):
    """
    Check if a group is assigned to a service principal with a specific role.
    :param app_object_id: The object ID of the service principal.
    :param group_object_id: The object ID of the group.
    :param role_definition_id: The ID of the role definition.
    :return: True if the group is assigned with the specified role, False otherwise.
    """
    url = f"https://graph.microsoft.com/v1.0/servicePrincipals/{app_object_id}/appRoleAssignedTo"
    while url:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        assignments = response.json().get("value", [])
        # print(f"Fetched {len(assignments)} assignments.")  # Debugging output

        # Check if the group is assigned with the specified role
        for assignment in assignments:
            if (
                assignment["principalId"] == group_object_id
                and assignment["appRoleId"] == role_definition_id
            ):
                print(f"Group '{assignment['principalDisplayName']}' is assigned with role '{role_name}' in service principal '{assignment['resourceDisplayName']}'.")  # Debugging output
                return True

        # Check for pagination
        url = response.json().get("@odata.nextLink", None)
        if url:
            print("Fetching next page of assignments...")  # Debugging output
    print(f"Group '{group_object_id}' is not assigned with role '{role_name}' in service principal '{app_object_id}'.")  # Debugging output
    return False


def load_input_from_json(file_path):
    """
    Load input data from a JSON file.
    :param file_path: Path to the JSON file.
    :return: Dictionary containing input data.
    """
    try:
        with open(file_path, "r") as file:
            data = json.load(file)
        return data
    except Exception as e:
        print(f"Failed to load input from JSON file: {e}")
        return None


def remove_role_assignment(app_object_id, group_object_id, role_definition_id):
    """
    Remove a role assignment from a service principal.
    :param app_object_id: The object ID of the service principal.
    :param group_object_id: The object ID of the group.
    :param role_definition_id: The ID of the role definition.
    """
    # Fetch role assignments for the service principal
    url = f"https://graph.microsoft.com/v1.0/servicePrincipals/{app_object_id}/appRoleAssignedTo"
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        assignments = response.json().get("value", [])

        # Find the role assignment ID for the group and role
        app_role_assignment_id = None
        for assignment in assignments:
            if (
                assignment["principalId"] == group_object_id
                and assignment["appRoleId"] == role_definition_id
            ):
                app_role_assignment_id = assignment["id"]
                break

        if app_role_assignment_id:
            print(f"Found role assignment ID: {app_role_assignment_id}, proceeding to remove it.")
            delete_url = f"https://graph.microsoft.com/v1.0/servicePrincipals/{app_object_id}/appRoleAssignedTo/{app_role_assignment_id}"
            delete_response = requests.delete(delete_url, headers=headers)
            delete_response.raise_for_status()
            print(f"Role assignment '{app_role_assignment_id}' removed successfully.")
        else:
            print("Role assignment not found. Cannot proceed with removal.")
    except Exception as e:
        print(f"Failed to remove role assignment: {e}")

def fetch_user_object_id_by_email(user_email):
    """
    Fetch the object ID of a user by their email address.
    """
    url = f"https://graph.microsoft.com/v1.0/users/{user_email}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    user = response.json()
    return user["id"]

def get_service_principal_object_id(app_id):
    """
    Get the service principal object ID from the application (client) ID.
    """
    url = f"https://graph.microsoft.com/v1.0/servicePrincipals?$filter=appId eq '{app_id}'"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    sps = response.json().get("value", [])
    if sps:
        return sps[0]["id"]
    else:
        raise ValueError(f"Service principal not found for appId '{app_id}'")

def add_owner_to_application(app_name=None, app_id=None, user_email=None):
    """
    Add a user as an owner to the application (service principal) by email and app name or app id.
    """
    try:
        if app_id:
            target_app_object_id = get_service_principal_object_id(app_id)
        elif app_name:
            target_app_object_id = fetch_application_id_by_suffix(app_name)
        else:
            raise ValueError("Either app_name or app_id must be provided.")
        print(f"Service Principal Object ID: {target_app_object_id}")
        user_id = fetch_user_object_id_by_email(user_email)
        print(f"User Object ID: {user_id}")
        url = f"https://graph.microsoft.com/v1.0/servicePrincipals/{target_app_object_id}/owners/$ref"
        payload = {"@odata.id": f"https://graph.microsoft.com/v1.0/directoryObjects/{user_id}"}
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        print(f"User '{user_email}' added as owner to application '{app_name or app_id}'.")
    except Exception as e:
        print(f"Failed to add owner: {e}")

def list_groups_with_role(app_object_id, role_name):
    """
    List all groups assigned to a specific role in a service principal.
    :param app_object_id: The object ID of the service principal.
    :param role_name: The name of the role to filter by.
    """
    try:
        # Fetch the role ID for the given role name
        role_id = fetch_application_role_id(app_object_id, role_name)
        print(f"Role ID for '{role_name}': {role_id}")
        # Fetch all role assignments for the service principal
        url = f"https://graph.microsoft.com/v1.0/servicePrincipals/{app_object_id}/appRoleAssignedTo"
        groups_with_role = []
        while url:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            assignments = response.json().get("value", [])
            for assignment in assignments:
                if assignment["appRoleId"] == role_id and assignment["principalType"] == "Group":
                    group_id = assignment["principalId"]
                    # Fetch group display name
                    group_url = f"https://graph.microsoft.com/v1.0/groups/{group_id}"
                    group_resp = requests.get(group_url, headers=headers)
                    group_resp.raise_for_status()
                    group_name = group_resp.json().get("displayName", group_id)
                    groups_with_role.append({"id": group_id, "name": group_name})
            url = response.json().get("@odata.nextLink", None)
        if groups_with_role:
            print(f"Groups with role '{role_name}':")
            for group in groups_with_role:
                print(f"- {group['name']} (ID: {group['id']})")
        else:
            print(f"No groups found with role '{role_name}' in application '{app_object_id}'.")
    except Exception as e:
        print(f"Failed to list groups with role '{role_name}': {e}")

def add_owners_to_application(app_name=None, app_id=None, user_emails=None):
    """
    Add multiple users as owners to the application (service principal) by their emails and app name or app id.
    """
    try:
        if app_id:
            target_app_object_id = get_service_principal_object_id(app_id)
        elif app_name:
            target_app_object_id = fetch_application_id_by_suffix(app_name)
        else:
            raise ValueError("Either app_name or app_id must be provided.")
        print(f"Service Principal Object ID: {target_app_object_id}")
        for user_email in user_emails:
            try:
                user_id = fetch_user_object_id_by_email(user_email)
                print(f"User Object ID for {user_email}: {user_id}")
                url = f"https://graph.microsoft.com/v1.0/servicePrincipals/{target_app_object_id}/owners/$ref"
                payload = {"@odata.id": f"https://graph.microsoft.com/v1.0/directoryObjects/{user_id}"}
                response = requests.post(url, headers=headers, json=payload)
                response.raise_for_status()
                print(f"User '{user_email}' added as owner to application '{app_name or app_id}'.")
            except Exception as e:
                print(f"Failed to add owner '{user_email}': {e}")
    except Exception as e:
        print(f"Failed to add owners: {e}")

def print_table(headers, rows):
    """
    Print a table given headers and rows.
    """
    col_widths = [max(len(str(h)), max((len(str(row[i])) for row in rows), default=0)) for i, h in enumerate(headers)]
    header_line = " ".join(f"{h:<{col_widths[i]}}" for i, h in enumerate(headers))
    print(header_line)
    print("-" * (sum(col_widths) + len(col_widths) - 1))
    for row in rows:
        print(" ".join(f"{str(row[i]):<{col_widths[i]}}" for i in range(len(headers))))

def list_owners_of_application(app_name=None, app_id=None):
    """
    List all owners of the application (service principal) by app name or app id.
    """
    global headers
    try:
        if app_id:
            target_app_object_id = get_service_principal_object_id(app_id)
        elif app_name:
            target_app_object_id = fetch_application_id_by_suffix(app_name)
        else:
            raise ValueError("Either app_name or app_id must be provided.")
        print(f"Service Principal Object ID: {target_app_object_id}")
        url = f"https://graph.microsoft.com/v1.0/servicePrincipals/{target_app_object_id}/owners"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        owners = response.json().get("value", [])
        if owners:
            print(f"Owners of application '{app_name or app_id}':")
            headers_tbl = ["Display Name", "Email", "ID"]
            rows = []
            for owner in owners:
                display_name = owner.get('displayName', owner.get('id'))
                email = owner.get('userPrincipalName', owner.get('mail', 'N/A'))
                owner_id = owner['id']
                rows.append([display_name, email, owner_id])
            print_table(headers_tbl, rows)
        else:
            print(f"No owners found for application '{app_name or app_id}'.")
    except Exception as e:
        print(f"Failed to list owners: {e}")

def remove_owners_from_application(app_name=None, app_id=None, user_emails=None):
    """
    Remove multiple users as owners from the application (service principal) by their emails and app name or app id.
    """
    try:
        if app_id:
            target_app_object_id = get_service_principal_object_id(app_id)
        elif app_name:
            target_app_object_id = fetch_application_id_by_suffix(app_name)
        else:
            raise ValueError("Either app_name or app_id must be provided.")
        print(f"Service Principal Object ID: {target_app_object_id}")
        for user_email in user_emails:
            try:
                user_id = fetch_user_object_id_by_email(user_email)
                print(f"User Object ID for {user_email}: {user_id}")
                url = f"https://graph.microsoft.com/v1.0/servicePrincipals/{target_app_object_id}/owners/{user_id}/$ref"
                response = requests.delete(url, headers=headers)
                if response.status_code == 204:
                    print(f"User '{user_email}' removed as owner from application '{app_name or app_id}'.")
                else:
                    print(f"Failed to remove owner '{user_email}': {response.status_code} {response.text}")
            except Exception as e:
                print(f"Failed to remove owner '{user_email}': {e}")
    except Exception as e:
        print(f"Failed to remove owners: {e}")

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Manage role assignments and owners for a service principal.")
    parser.add_argument("action", choices=["add", "rmv", "list", "add-owners", "list-owners", "remove-owners"], help="Action to perform: 'add', 'rmv', 'list', 'add-owners', 'list-owners' or 'remove-owners'")
    parser.add_argument("input_file", nargs="?", help="Path to the JSON input file (required for 'add' and 'rmv')")
    parser.add_argument("--app-object-id", dest="app_object_id", help="Service principal object ID (required for 'list', optional for owner actions)")
    parser.add_argument("--app-id", dest="app_id", help="Azure AD Application (client) ID (used for owner actions)")
    parser.add_argument("--role-name", dest="role_name", help="Role name to list (required for 'list')")
    parser.add_argument("--user-email", dest="user_emails", action="append", help="Email of the user to add as owner (can be specified multiple times for 'add-owners')")
    parser.add_argument("--app-name", dest="app_name_arg", help="Application name (required for owner actions if app-object-id not provided)")

    # Parse arguments
    args = parser.parse_args()
    action = args.action

    if action == "list":
        if not args.app_object_id or not args.role_name:
            print("For 'list' action, you must provide --app-object-id and --role-name.")
            exit(1)
        list_groups_with_role(args.app_object_id, args.role_name)
    elif action == "add-owners":
        if not args.user_emails or (not args.app_name_arg and not args.app_id):
            print("For 'add-owners' action, you must provide one or more --user-email and either --app-name or --app-id.")
            exit(1)
        add_owners_to_application(app_name=args.app_name_arg, app_id=args.app_id, user_emails=args.user_emails)
    elif action == "list-owners":
        if not args.app_name_arg and not args.app_id:
            print("For 'list-owners' action, you must provide either --app-name or --app-id.")
            exit(1)
        list_owners_of_application(app_name=args.app_name_arg, app_id=args.app_id)
    elif action == "remove-owners":
        if not args.user_emails or (not args.app_name_arg and not args.app_id):
            print("For 'remove-owners' action, you must provide one or more --user-email and either --app-name or --app-id.")
            exit(1)
        remove_owners_from_application(app_name=args.app_name_arg, app_id=args.app_id, user_emails=args.user_emails)
    else:
        input_file = args.input_file
        if not input_file:
            print("Input file is required for 'add' and 'rmv' actions.")
            exit(1)
        # Load input data from JSON file
        input_data = load_input_from_json(input_file)
        if not input_data:
            print("Failed to load input data. Exiting.")
            exit(1)
        # Extract values from the JSON file
        group_name = input_data.get("group_name")
        roles = input_data.get("roles", [])  # List of roles
        app_name = input_data.get("app_name")
        try:
            app_id = fetch_application_id_by_suffix(app_name)
            print(f"Application ID: {app_id}")
        except Exception as e:
            print(f"Error: {e}")
            app_id = None
        # Proceed only if app_id is successfully fetched
        if app_id:
            try:
                group_object_id = fetch_group_object_id(group_name)
                print(f"Group Object ID: {group_object_id}")
                for role_name in roles:
                    try:
                        role_id = fetch_application_role_id(app_id, role_name)
                        print(f"Role ID for '{role_name}': {role_id}")
                        if action == "add":
                            add_group_to_enterprise_app(app_id, group_object_id, role_id, role_name)
                        elif action == "rmv":
                            remove_role_assignment(app_id, group_object_id, role_id)
                    except Exception as e:
                        print(f"Error processing role '{role_name}': {e}")
            except Exception as e:
                print(f"Error: {e}")
        else:
            print("Cannot proceed without a valid application ID.")
    print("Script execution completed.")

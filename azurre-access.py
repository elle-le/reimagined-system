import os
import requests
import jwt
import argparse
import json
from azure.identity import DefaultAzureCredential

# Set up Azure credentials
credential = DefaultAzureCredential()
tenant_id = "42f7676c-f455-423c-82f6-dc2d99791af7"
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
    url = f"https://graph.microsoft.com/v1.0/groups?$filter=displayName eq '{group_name}'"
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
        # url = f"https://graph.microsoft.com/v1.0/servicePrincipals/{app_object_id}/appRoleAssignments"
        # role_assignment_params = {
        #     "principalId": group_object_id,
        #     "appRoleId": role_definition_id,
        #     "resourceId": app_object_id  # Service principal ID
        # }
        # response = requests.post(url, headers=headers, json=role_assignment_params)
        # response.raise_for_status()
        # print(f"Role assigned successfully to group in enterprise app: {response.json()['id']}")
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

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Manage role assignments for a service principal.")
    parser.add_argument("action", choices=["add", "rmv"], help="Action to perform: 'add' or 'rmv'")
    parser.add_argument("input_file", help="Path to the JSON input file")

    # Parse arguments
    args = parser.parse_args()
    action = args.action
    input_file = args.input_file

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

"""
Jira CMDB Integration Script
This script connects to a Jira instance (using the REST API) to retrieve and update 
configuration management data for the maritime vessel safety systems project.
"""
import os
import requests
import json

# Configuration: Jira connection details (use environment variables for security)
JIRA_URL = os.getenv("JIRA_URL", "https://your-jira-instance.atlassian.net")
JIRA_USER = os.getenv("JIRA_USER", "user@example.com")
JIRA_TOKEN = os.getenv("JIRA_TOKEN", "your_api_token")  # API token or password

# Jira project and query settings for CMDB
CMDB_PROJECT_KEY = os.getenv("CMDB_PROJECT", "CMDB")  # Example project key for CMDB items
CMDB_ISSUE_TYPE = os.getenv("CMDB_ISSUE_TYPE", "Configuration Item")

# Setup authentication for Jira (Basic Auth with email/API token)
auth = (JIRA_USER, JIRA_TOKEN)
headers = {"Content-Type": "application/json"}

def query_cmdb_items(jql_filter=None):
    """
    Query Jira for CMDB items using JQL filter. If no filter provided, fetches all items in CMDB project.
    Returns list of issues (each as dict with key, summary, and relevant fields).
    """
    jql = jql_filter or f'project = {CMDB_PROJECT_KEY}'
    search_url = f"{JIRA_URL}/rest/api/2/search"
    params = {"jql": jql, "maxResults": 100}
    response = requests.get(search_url, params=params, auth=auth)
    response.raise_for_status()
    data = response.json()
    issues = []
    for issue in data.get("issues", []):
        issues.append({
            "key": issue.get("key"),
            "summary": issue.get("fields", {}).get("summary"),
            # Add more fields as needed, e.g., status, custom fields
            "status": issue.get("fields", {}).get("status", {}).get("name")
        })
    return issues

def update_cmdb_item(issue_key, fields):
    """
    Update the specified Jira issue (CMDB item) with new field values.
    :param issue_key: e.g. "CMDB-123"
    :param fields: dict of fields to update (e.g., {"description": "Updated description"})
    """
    url = f"{JIRA_URL}/rest/api/2/issue/{issue_key}"
    payload = {"fields": fields}
    response = requests.put(url, auth=auth, headers=headers, data=json.dumps(payload))
    response.raise_for_status()
    return response.status_code  # should be 204 if successful

def create_cmdb_item(summary, description, additional_fields=None):
    """
    Create a new CMDB item in Jira.
    :param summary: Summary/title for the new configuration item.
    :param description: Description text.
    :param additional_fields: dict of any additional custom fields for the issue.
    """
    url = f"{JIRA_URL}/rest/api/2/issue"
    fields = {
        "project": {"key": CMDB_PROJECT_KEY},
        "summary": summary,
        "description": description,
        "issuetype": {"name": CMDB_ISSUE_TYPE}
    }
    if additional_fields:
        fields.update(additional_fields)
    payload = {"fields": fields}
    response = requests.post(url, auth=auth, headers=headers, data=json.dumps(payload))
    response.raise_for_status()
    issue_key = response.json().get("key")
    return issue_key

if __name__ == "__main__":
    # Example usage:
    # 1. Query and list all CMDB items
    print(f"Querying CMDB items in Jira project {CMDB_PROJECT_KEY}...")
    items = query_cmdb_items()
    for item in items:
        print(f"{item['key']}: {item['summary']} (Status: {item['status']})")

    # 2. Update a specific item (for example, update description of first item)
    if items:
        first_key = items[0]['key']
        print(f"\nUpdating description of {first_key}...")
        new_desc = "Updated via CMDB integration script on latest system deployment."
        update_cmdb_item(first_key, {"description": new_desc})
        print(f"Issue {first_key} description updated.")

    # 3. Create a new CMDB item (if needed)
    print("\nCreating a new CMDB item...")
    new_key = create_cmdb_item(
        summary="Safety System Software v2.0",
        description="Baseline configuration for Safety System Software version 2.0 deployment",
        additional_fields={"labels": ["automation", "cmdb_sync"]}
    )
    print(f"Created new CMDB item: {new_key}")

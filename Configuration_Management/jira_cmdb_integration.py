"""
Maritime Vessel Safety Systems - Jira CMDB Integration Script

This script uses Jira's REST API to query and update configuration items (CMDB entries) 
for maritime safety system versions and their test records. It will search for an existing 
Jira issue that represents a given system version, create one if it doesn't exist, and update 
it with the latest test results (e.g., pass/fail status of tests linked to requirements).

Assumptions:
- Jira is used as a CMDB. Each safety system version is an issue in a specific Jira project.
- The issue summary (or a field) contains the version identifier (used for lookup).
- Test results are provided in JSON or CSV files (e.g., output from automated tests), containing 
  fields like test_id, requirement_id, result, and details.
- Jira credentials (URL, username, API token) are stored in environment variables for security.

Usage:
  Set the environment variables JIRA_URL, JIRA_USER, JIRA_API_TOKEN (and optionally JIRA_PROJECT, 
  JIRA_ISSUE_TYPE). Then run this script with the --version and --results_path arguments.

Example:
  $ export JIRA_URL="https://your-domain.atlassian.net"
  $ export JIRA_USER="your.email@company.com"
  $ export JIRA_API_TOKEN="<your_api_token>"
  $ export JIRA_PROJECT="SAFETY"
  $ export JIRA_ISSUE_TYPE="Task"
  $ python jira_cmdb_integration.py --version "System v1.2" --results_path "./test_results"
"""
import os
import sys
import json
import logging
import argparse
from datetime import datetime

import requests  # Third-party library for HTTP requests (pip install requests)

# Configure logging to file and console for traceability
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("jira_cmdb_update.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

# Read necessary config from environment
JIRA_URL = os.environ.get("JIRA_URL")
JIRA_USER = os.environ.get("JIRA_USER")
JIRA_TOKEN = os.environ.get("JIRA_API_TOKEN")
JIRA_PROJECT = os.environ.get("JIRA_PROJECT", "CMDB")
JIRA_ISSUE_TYPE = os.environ.get("JIRA_ISSUE_TYPE", "Task")

if not JIRA_URL or not JIRA_USER or not JIRA_TOKEN:
    logging.error("JIRA_URL, JIRA_USER, and JIRA_API_TOKEN must be set as environment variables.")
    sys.exit(1)

def query_issue_by_summary(version_name):
    """Search for a Jira issue in the project with a summary matching the version name."""
    jql = f'project="{JIRA_PROJECT}" AND summary ~ "\\"{version_name}\\""'
    # Construct search URL
    search_url = f"{JIRA_URL}/rest/api/2/search"
    params = {"jql": jql}
    logging.info(f'Searching for Jira issue with summary "{version_name}" in project {JIRA_PROJECT}')
    response = requests.get(search_url, params=params, auth=(JIRA_USER, JIRA_TOKEN))
    if response.status_code != 200:
        logging.error(f"Jira search failed: {response.status_code} - {response.text}")
        return None
    data = response.json()
    issues = data.get("issues", [])
    if not issues:
        logging.info("No existing Jira issue found for this version.")
        return None
    issue = issues[0]
    issue_key = issue.get("key")
    logging.info(f"Found existing Jira issue: {issue_key}")
    return issue  # return full issue data (can extract key or fields as needed)

def create_issue(version_name, description_text):
    """Create a new Jira issue for the given system version with an initial description."""
    create_url = f"{JIRA_URL}/rest/api/2/issue"
    issue_fields = {
        "project": {"key": JIRA_PROJECT},
        "summary": version_name,
        "description": description_text,
        "issuetype": {"name": JIRA_ISSUE_TYPE}
    }
    payload = {"fields": issue_fields}
    logging.info(f"Creating new Jira issue for version: {version_name}")
    response = requests.post(create_url, json=payload, auth=(JIRA_USER, JIRA_TOKEN))
    if response.status_code != 201:  # HTTP 201 Created is expected on success
        logging.error(f"Failed to create Jira issue: {response.status_code} - {response.text}")
        return None
    issue_key = response.json().get("key")
    logging.info(f"Created Jira issue {issue_key} for version {version_name}")
    return issue_key

def add_comment(issue_key, comment_text):
    """Add a comment to an existing Jira issue."""
    comment_url = f"{JIRA_URL}/rest/api/2/issue/{issue_key}/comment"
    payload = {"body": comment_text}
    logging.info(f"Adding comment to Jira issue {issue_key}")
    response = requests.post(comment_url, json=payload, auth=(JIRA_USER, JIRA_TOKEN))
    if response.status_code != 201:
        logging.error(f"Failed to add comment to {issue_key}: {response.status_code} - {response.text}")
        return False
    logging.info(f"Comment added to {issue_key} successfully.")
    return True

def load_test_results(path):
    """Load test result data from a JSON file, CSV file, or directory of JSON files."""
    results = []
    if not path:
        return results
    if os.path.isdir(path):
        # Load all JSON files in the directory
        for fname in os.listdir(path):
            if fname.lower().endswith(".json"):
                file_path = os.path.join(path, fname)
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                except Exception as e:
                    logging.warning(f"Could not read {fname}: {e}")
                    continue
                if isinstance(data, dict) and "test_id" in data:
                    results.append(data)
                elif isinstance(data, list):
                    results.extend([item for item in data if isinstance(item, dict) and "test_id" in item])
    else:
        if path.lower().endswith(".json"):
            with open(path, 'r') as f:
                data = json.load(f)
            if isinstance(data, dict):
                results.append(data)
            elif isinstance(data, list):
                results.extend([item for item in data if isinstance(item, dict)])
        elif path.lower().endswith(".csv"):
            import csv
            with open(path, newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Convert 'result' field to boolean if possible (accept various representations)
                    if "result" in row:
                        val = row["result"]
                        if isinstance(val, str):
                            val_lower = val.strip().lower()
                            if val_lower in ["true", "pass", "passed", "1", "yes", "y"]:
                                row["result"] = True
                            elif val_lower in ["false", "fail", "failed", "0", "no", "n"]:
                                row["result"] = False
                    results.append(row)
    return results

def summarize_results(results):
    """Generate a summary string and list of failed requirement IDs from test results."""
    if not results:
        return None, []
    total = len(results)
    # Count passed tests
    passed_count = 0
    failed_reqs = []
    for res in results:
        res_val = res.get("result")
        passed = False
        if isinstance(res_val, bool):
            passed = res_val
        elif isinstance(res_val, str):
            passed = res_val.strip().lower() in ["true", "pass", "passed", "yes", "y", "1"]
        else:
            passed = bool(res_val)
        if passed:
            passed_count += 1
        else:
            # Collect requirement ID of failed test (if available)
            req_id = res.get("requirement_id") or res.get("requirement") or ""
            if req_id:
                failed_reqs.append(str(req_id))
    failed_count = total - passed_count
    summary_lines = []
    summary_lines.append(f"Total Tests: {total}")
    summary_lines.append(f"Passed: {passed_count}")
    summary_lines.append(f"Failed: {failed_count}")
    if failed_count > 0:
        unique_failed_reqs = sorted(set(failed_reqs))
        if unique_failed_reqs:
            summary_lines.append("Non-compliant requirements: " + ", ".join(unique_failed_reqs))
    # Join summary lines for use in description/comment
    summary_text = "; ".join(summary_lines)
    return summary_text, failed_reqs

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Integrate test results into Jira CMDB (configuration management database).")
    parser.add_argument("--version", required=True, help="Safety system version identifier (used as Jira issue summary).")
    parser.add_argument("--results_path", required=False, help="Path to test results (JSON/CSV file or directory containing JSON files).")
    args = parser.parse_args()

    version_name = args.version
    results_path = args.results_path

    logging.info(f"Starting Jira CMDB integration for version: {version_name}")
    # Load and summarize test results if provided
    results_data = load_test_results(results_path) if results_path else []
    summary_text, failed_reqs = summarize_results(results_data)
    # Prepare content for Jira update
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if summary_text:
        # Build a comment body with summary and basic details per test
        comment_lines = []
        comment_lines.append(f"*Test Results Summary ({current_date})*")
        # Break out the summary lines (replacing '; ' with newlines for readability in Jira comment)
        for line in summary_text.split("; "):
            comment_lines.append(f"- {line}")
        # List individual test outcomes (Test ID and PASS/FAIL)
        if results_data:
            comment_lines.append("\nDetailed Results:")
            for res in results_data:
                tid = res.get("test_id", "UNKNOWN TEST")
                req = res.get("requirement_id") or res.get("requirement") or "N/A"
                res_val = res.get("result")
                if isinstance(res_val, bool):
                    passed = res_val
                elif isinstance(res_val, str):
                    passed = res_val.strip().lower() in ["true", "pass", "passed", "yes", "y", "1"]
                else:
                    passed = bool(res_val)
                status = "PASSED" if passed else "FAILED"
                comment_lines.append(f"- {tid} (Requirement {req}): **{status}**")
        comment_text = "\n".join(comment_lines)
    else:
        comment_text = f"*System version {version_name} added to CMDB on {current_date}*"

    # Search for existing issue
    issue = query_issue_by_summary(version_name)
    if issue:
        issue_key = issue.get("key")
        # Update existing issue: add a comment with the test results summary
        if summary_text:
            add_comment(issue_key, comment_text)
        else:
            logging.info("No test results provided to update the issue.")
    else:
        # Create a new issue for this version
        desc = "Created automatically by safety system script on " + current_date
        if summary_text:
            desc += "\n" + summary_text  # include one-line summary in description
        new_issue_key = create_issue(version_name, desc)
        if new_issue_key and summary_text:
            # Optionally, add the detailed comment on the new issue as well (for full test details)
            add_comment(new_issue_key, comment_text)
    logging.info("Jira CMDB integration script completed.")

#!/usr/bin/env python3
"""Builds n8n/ptg-welcome-email.json from email/welcome.html.

Run after any change to the email:  python3 n8n/build_workflow.py
The workflow polls the private Signups sheet every 2 minutes, sends the welcome
email from the connected Gmail account to each row whose Status is "new", and
writes the result back to the row.
"""
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
SHEET_ID = "1QodevbYpJ7VLTZzdl058YS0sQ1zg99qJ-OioZRi6aDU"
TAB = "Signups"
WORKFLOW_ID = "PtgWelcomeMail01"          # fixed id: `n8n import:workflow` needs one
SENDER_NAME = "D. Antione Dixon"
SUBJECT = "You’re on the list for The Path to Greatness"
UTM = "utm_source=welcome_email&utm_medium=email&utm_campaign=ptg_prelaunch"
SITE = "https://eatmediatv.com/pathtogreatness/"

ROW = "$('Get new sign-ups').item.json"   # the sheet row this email belongs to

html = (ROOT / "email" / "welcome.html").read_text(encoding="utf-8")
assert "{{" not in html.replace("{{SITE_LINK}}", "").replace("{{FIELD_LINK}}", "").replace("{{SHARE_LINK}}", "").replace("{{UNSUB_LINK}}", ""), \
    "welcome.html has a stray {{ that n8n would try to evaluate"
html = (html
        .replace("{{SITE_LINK}}", f"{SITE}?{UTM}&utm_content=header")
        .replace("{{FIELD_LINK}}", f"{SITE}?{UTM}&utm_content=field_work#field-work")
        .replace("{{SHARE_LINK}}", f"{SITE}?{UTM}&utm_content=ps_share")
        .replace("{{UNSUB_LINK}}", "{{ " + ROW + "['Unsubscribe link'] }}"))

doc = {"__rl": True, "value": SHEET_ID, "mode": "id"}
sheet = {"__rl": True, "value": TAB, "mode": "name"}
SHEETS_CRED = {"googleSheetsOAuth2Api": {"id": "PTG_SHEETS_CREDENTIAL", "name": "Google Sheets account"}}
GMAIL_CRED = {"gmailOAuth2": {"id": "PTG_GMAIL_CREDENTIAL", "name": "Gmail account"}}


def col(name):
    return {"id": name, "displayName": name, "required": False, "defaultMatch": False, "display": True,
            "type": "string", "canBeUsedToMatch": True, "removed": False}


def update_node(node_id, name, x, y, values):
    return {
        "id": node_id, "name": name, "type": "n8n-nodes-base.googleSheets", "typeVersion": 4.5,
        "position": [x, y], "credentials": SHEETS_CRED,
        "parameters": {
            "operation": "update", "documentId": doc, "sheetName": sheet,
            "columns": {"mappingMode": "defineBelow", "value": values, "matchingColumns": ["ID"],
                        "schema": [col(k) for k in ["ID", "Status", "Welcome sent", "Notes"]]},
            "options": {},
        },
    }


nodes = [
    {"id": "6b1f3c1e-0001-4c0a-9a51-000000000001", "name": "Every 2 minutes", "type": "n8n-nodes-base.scheduleTrigger",
     "typeVersion": 1.2, "position": [0, 300],
     "parameters": {"rule": {"interval": [{"field": "minutes", "minutesInterval": 2}]}}},
    {"id": "6b1f3c1e-0002-4c0a-9a51-000000000002", "name": "Get new sign-ups", "type": "n8n-nodes-base.googleSheets",
     "typeVersion": 4.5, "position": [220, 300], "credentials": SHEETS_CRED, "alwaysOutputData": False,
     "parameters": {"operation": "read", "documentId": doc, "sheetName": sheet,
                    "filtersUI": {"values": [{"lookupColumn": "Status", "lookupValue": "new"}]},
                    "options": {"returnAllMatches": "returnAllMatches"}}},
    {"id": "6b1f3c1e-0003-4c0a-9a51-000000000003", "name": "At most 20 per run", "type": "n8n-nodes-base.limit",
     "typeVersion": 1, "position": [440, 300], "parameters": {"maxItems": 20}},
    update_node("6b1f3c1e-0004-4c0a-9a51-000000000004", "Mark sending", 660, 300,
                {"ID": "={{ " + ROW + ".ID }}", "Status": "sending"}),
    {"id": "6b1f3c1e-0005-4c0a-9a51-000000000005", "name": "Send welcome email", "type": "n8n-nodes-base.gmail",
     "typeVersion": 2.1, "position": [880, 300], "credentials": GMAIL_CRED, "onError": "continueErrorOutput",
     "parameters": {"resource": "message", "operation": "send", "sendTo": "={{ " + ROW + ".Email }}", "subject": SUBJECT, "emailType": "html",
                    "message": "=" + html,
                    "options": {"appendAttribution": False, "senderName": SENDER_NAME}}},
    update_node("6b1f3c1e-0006-4c0a-9a51-000000000006", "Mark welcomed", 1120, 200,
                {"ID": "={{ " + ROW + ".ID }}", "Status": "welcomed",
                 "Welcome sent": "={{ $now.setZone('America/Los_Angeles').toFormat('yyyy-MM-dd HH:mm') }}"}),
    update_node("6b1f3c1e-0007-4c0a-9a51-000000000007", "Mark error", 1120, 420,
                {"ID": "={{ " + ROW + ".ID }}", "Status": "error",
                 "Notes": "={{ 'Welcome email failed ' + $now.setZone('America/Los_Angeles').toFormat('yyyy-MM-dd HH:mm') + ': ' + ($json.error && $json.error.message ? $json.error.message : 'unknown error') }}"}),
    {"id": "6b1f3c1e-0008-4c0a-9a51-000000000008", "name": "About this workflow", "type": "n8n-nodes-base.stickyNote",
     "typeVersion": 1, "position": [-40, -40],
     "parameters": {"width": 760, "height": 300, "color": 7, "content":
        "## PTG: Welcome email\n"
        "Every 2 minutes this reads the private sheet **The Path to Greatness · First Readers** (tab Signups). "
        "Each row with Status **new** gets the welcome email from the connected Gmail account, then its Status becomes "
        "**welcomed** (or **error**, with the reason in Notes).\n\n"
        "- To resend to someone, set their Status back to **new** in the sheet.\n"
        "- Rows marked **unsubscribed** are never emailed.\n"
        "- The email text lives in `automation/pathtogreatness-signups/email/welcome.html` in ImaginariumOzone; "
        "rebuild this workflow with `n8n/build_workflow.py` after changing it.\n"
        "- Kill switch: switch this workflow off. Sign-ups keep landing in the sheet and will be welcomed when it is back on."}},
]

connections = {
    "Every 2 minutes": {"main": [[{"node": "Get new sign-ups", "type": "main", "index": 0}]]},
    "Get new sign-ups": {"main": [[{"node": "At most 20 per run", "type": "main", "index": 0}]]},
    "At most 20 per run": {"main": [[{"node": "Mark sending", "type": "main", "index": 0}]]},
    "Mark sending": {"main": [[{"node": "Send welcome email", "type": "main", "index": 0}]]},
    "Send welcome email": {"main": [[{"node": "Mark welcomed", "type": "main", "index": 0}],
                                    [{"node": "Mark error", "type": "main", "index": 0}]]},
}

workflow = {
    "id": WORKFLOW_ID,
    "name": "PTG: Welcome email",
    "active": False,
    "nodes": nodes,
    "connections": connections,
    "settings": {"executionOrder": "v1", "timezone": "America/Los_Angeles",
                 "saveDataSuccessExecution": "none", "saveDataErrorExecution": "all",
                 "saveManualExecutions": True, "callerPolicy": "workflowsFromSameOwner"},
    "pinData": {},
    "tags": [],
}

out = HERE / "ptg-welcome-email.json"
out.write_text(json.dumps(workflow, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("wrote", out, out.stat().st_size, "bytes")

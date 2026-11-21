#!/bin/bash
# Installs the "PTG: Welcome email" workflow into the n8n on this Mac.
#
#   bash install.sh            install (or update) the workflow, switched OFF
#
# What it does, in order:
#   1. backs up ~/.n8n/database.sqlite
#   2. finds your Google Sheets and Gmail credentials in n8n (names only, never secrets)
#   3. links them, and your "EAT Hub — Error Alert" workflow, into the workflow file
#   4. imports it with `n8n import:workflow`, switched off
# You then open it in n8n, run it once, and switch it on.

set -euo pipefail

# The workflow file is read from this folder when it is here; otherwise it is downloaded.
# PTG_BRANCH picks the branch to download from (default main).
RAW="https://raw.githubusercontent.com/Dixon8303/ImaginariumOzone/${PTG_BRANCH:-main}/automation/pathtogreatness-signups/n8n/ptg-welcome-email.json"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DB="$HOME/.n8n/database.sqlite"
WF_ID="PtgWelcomeMail01"

say() { printf '%s\n' "$*"; }
die() { printf 'Stopped: %s\n' "$*" >&2; exit 1; }

command -v n8n >/dev/null 2>&1 || die "the n8n command is not available in this Terminal window."
command -v sqlite3 >/dev/null 2>&1 || die "sqlite3 is not installed."
command -v python3 >/dev/null 2>&1 || die "python3 is not installed."
[ -f "$DB" ] || die "no n8n database at $DB."

SRC="$HERE/ptg-welcome-email.json"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/ptg-welcome.XXXXXX")"
if [ ! -f "$SRC" ]; then
  SRC="$WORK/ptg-welcome-email.json"
  curl -fsSL "$RAW" -o "$SRC" || die "could not download the workflow file."
fi

# 1. Backup
mkdir -p "$HOME/.n8n/backups"
BACKUP="$HOME/.n8n/backups/database-$(date +%Y%m%d-%H%M%S)-before-ptg-welcome.sqlite"
sqlite3 "$DB" ".backup '$BACKUP'"
say "1. Backup saved: $BACKUP"

# 2. Credentials and error workflow (ids and names only)
SHEETS="$(sqlite3 -separator '|' "$DB" "select id, name from credentials_entity where type = 'googleSheetsOAuth2Api';" || true)"
GMAIL="$(sqlite3 -separator '|' "$DB" "select id, name from credentials_entity where type = 'gmailOAuth2';" || true)"
ERRWF="$(sqlite3 "$DB" "select id from workflow_entity where name like 'EAT Hub%Error Alert%' limit 1;" || true)"
EXISTS="$(sqlite3 "$DB" "select count(*) from workflow_entity where id = '$WF_ID';" || echo 0)"

OUT="$WORK/ptg-welcome-ready.json"
say "2. Linked to n8n:"
python3 - "$SRC" "$OUT" "$SHEETS" "$GMAIL" "$ERRWF" <<'PY'
import json, re, sys
src, out, sheets, gmail, errwf = sys.argv[1:6]

def choose(rows):
    rows = [r.split('|', 1) for r in rows.strip().splitlines() if '|' in r]
    if len(rows) == 1:
        return rows[0]
    preferred = [r for r in rows if re.search(r'eat|media', r[1], re.I)]
    return preferred[0] if len(preferred) == 1 else None

wf = json.load(open(src, encoding='utf-8'))
s, g = choose(sheets), choose(gmail)
for node in wf['nodes']:
    creds = node.get('credentials', {})
    if s and 'googleSheetsOAuth2Api' in creds:
        creds['googleSheetsOAuth2Api'] = {'id': s[0], 'name': s[1]}
    if g and 'gmailOAuth2' in creds:
        creds['gmailOAuth2'] = {'id': g[0], 'name': g[1]}
if errwf.strip():
    wf['settings']['errorWorkflow'] = errwf.strip()
wf['active'] = False
json.dump(wf, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('   Google Sheets credential: ' + (s[1] if s else 'none chosen (pick one in n8n)'))
print('   Gmail credential (the sender): ' + (g[1] if g else 'none chosen (pick one in n8n)'))
print('   Failures alert through: ' + ('EAT Hub — Error Alert' if errwf.strip() else 'nothing (no error workflow found)'))
PY

# 3. Import (switched off)
n8n import:workflow --input="$OUT" >/dev/null
COUNT="$(sqlite3 "$DB" "select count(*) from workflow_entity where id = '$WF_ID';")"
[ "$COUNT" = "1" ] || die "the import did not create the workflow. Your backup is at $BACKUP."
if [ "$EXISTS" = "1" ]; then say "3. Workflow updated (it was already installed). It is switched off."; else say "3. Workflow installed. It is switched off."; fi

cat <<'NEXT'

Next, in the n8n editor (a few minutes):
  a. Open the workflow "PTG: Welcome email".
  b. Open "Get new sign-ups" and "Send welcome email". If either shows a credential warning,
     pick (or create) the Google account for eatmediatv@gmail.com. The Gmail one decides
     which address the welcome email comes from.
  c. Sign up once on eatmediatv.com/pathtogreatness with an address you can check, then press
     "Execute workflow". The row's Status in the sheet should change to "welcomed" and the
     email should arrive.
  d. Switch the workflow on (the toggle at the top). It then runs every 2 minutes.

To stop it at any time, switch the workflow off. Sign-ups keep landing in the sheet.
NEXT

# Prompt for Claude Cowork: switch on the Path to Greatness sign-ups

Paste everything between the two lines into Claude Cowork on the Mac Studio. It needs the
browser (signed in to GitHub and to Google as eatmediatv@gmail.com) and Terminal.

---

Set up the sign-up system for eatmediatv.com/pathtogreatness. Work through the steps in order.
Stop and ask me whenever a screen does not match what a step describes, before any merge, and
before switching anything on. Never paste a password, token or API key into the chat. Change
nothing beyond what these steps name.

Names used below
- Sheet: https://docs.google.com/spreadsheets/d/1QodevbYpJ7VLTZzdl058YS0sQ1zg99qJ-OioZRi6aDU/edit
- Branch: claude/pathtogreatness-website-upgrade-tadyuv
- Staging pull request: https://github.com/Dixon8303/ImaginariumOzone/pull/200
- Production pull request: https://github.com/Dixon8303/eat.media/pull/4

Step 1. Deploy the sign-up endpoint (Google Apps Script)
1. Open the raw code in a new tab and copy all of it:
   https://raw.githubusercontent.com/Dixon8303/ImaginariumOzone/claude/pathtogreatness-website-upgrade-tadyuv/automation/pathtogreatness-signups/apps-script/Code.gs
2. Open the Sheet. Menu: Extensions > Apps Script. Rename the project to "PTG sign-ups".
3. In Code.gs, select everything, delete it, paste the copied code, and press Save.
4. In the function menu at the top choose "setup" and press Run. Google asks for permission:
   choose eatmediatv@gmail.com. If it says "Google hasn't verified this app", press Advanced,
   then "Go to PTG sign-ups (unsafe)", then Allow. This is my own script. If a permission screen
   needs me, stop and tell me. The execution log must end with "Ready. Signups tab found with the
   expected columns."
5. Deploy > New deployment. Gear icon > Web app. Description: PTG sign-ups. Execute as: Me
   (eatmediatv@gmail.com). Who has access: Anyone. Press Deploy, approve access if asked, and copy
   the Web app URL. It starts with https://script.google.com/macros/s/ and ends with /exec.
6. Project Settings (gear icon on the left) > Script properties > Add script property.
   Property: EXEC_URL. Value: the Web app URL. Save script properties.
7. Open the Web app URL with ?a=health added to the end. It must show "ok":true, "sheet":true
   and "unsubscribe_links":"set". If not, stop and show me.

Step 2. Put the endpoint into the page, in both repositories
1. Open https://github.com/Dixon8303/ImaginariumOzone/edit/claude/pathtogreatness-website-upgrade-tadyuv/eatmedia/pathtogreatness/assets/ptg.js
2. Find the line   FORM_ENDPOINT: "",   and put the Web app URL between the quotes, so it reads
   FORM_ENDPOINT: "https://script.google.com/macros/s/.../exec",   Change nothing else.
3. Commit changes. Message: "Path to Greatness: set the sign-up endpoint". Choose "Commit directly
   to the claude/pathtogreatness-website-upgrade-tadyuv branch".
4. Do the same in the production repository:
   https://github.com/Dixon8303/eat.media/edit/claude/pathtogreatness-website-upgrade-tadyuv/pathtogreatness/assets/ptg.js

Step 3. Merge (ask me first)
1. Open both pull requests. Show me their titles and confirm each one now lists the endpoint
   commit. Wait for my OK.
2. After my OK, on each pull request press "Ready for review", then "Merge pull request", then
   "Confirm merge". Merge the production one (eat.media #4) last.
3. Open the Actions tab of each repository and wait until the newest run is green. If a run fails
   with an artifact or deploy error, press "Re-run failed jobs" once. If it fails again, stop and
   show me the error.

Step 4. Test a sign-up on the live page
1. Ask me which email address to use for the test (one I can open in this browser).
2. Open https://eatmediatv.com/pathtogreatness/?utm_source=setup_test and do a hard refresh
   (Cmd+Shift+R). Scroll to "Be told when it is out". The button must read "Tell me when it's out".
   If it reads "Open my email", the new page is not live yet: wait two minutes and refresh.
3. Enter the test address and press the button. A "You're on the list" window must appear.
4. Open the Sheet, tab Signups. A new row must show the test address, Status "new", UTM source
   "setup_test" and "page form" in "Signed up from".

Step 5. Install the welcome email in n8n
1. In Terminal run:
   mkdir -p ~/ptg-n8n && cd ~/ptg-n8n
   curl -fsSLO https://raw.githubusercontent.com/Dixon8303/ImaginariumOzone/main/automation/pathtogreatness-signups/n8n/install.sh
   curl -fsSLO https://raw.githubusercontent.com/Dixon8303/ImaginariumOzone/main/automation/pathtogreatness-signups/n8n/ptg-welcome-email.json
   bash install.sh
   It backs up the n8n database first and prints the backup path. Copy its output into your report.
   If it stops with an error, do not retry with changes: show me the output.
2. Open the n8n editor (http://localhost:5678) and open the workflow "PTG: Welcome email".
3. Open the node "Get new sign-ups" and the node "Send welcome email". Each must show a
   credential with no warning. The Gmail credential must belong to eatmediatv@gmail.com, because
   it decides the sender. If either is missing or wrong, stop and tell me.
4. Press "Execute workflow" once. In the Sheet the test row must turn to Status "welcomed" with a
   time in "Welcome sent". The welcome email must arrive at the test address from
   eatmediatv@gmail.com (check Promotions and Spam too).

Step 6. Switch it on (ask me first)
1. Tell me the test passed and wait for my OK.
2. After my OK, switch the workflow on with the toggle at the top of the n8n editor. It then
   checks the Sheet every 2 minutes.

Step 7. Test the unsubscribe link
1. In the welcome email, press the unsubscribe link at the bottom. A page opens; press its
   confirm button. It must say the address is unsubscribed.
2. In the Sheet the test row must now show Status "unsubscribed".
3. Ask me whether to delete the test row. Delete it only if I say yes.

Report back with: the Web app URL, links to the two endpoint commits, the merge status of both
pull requests, the Actions results, the install.sh output, and the result of every test above.

---

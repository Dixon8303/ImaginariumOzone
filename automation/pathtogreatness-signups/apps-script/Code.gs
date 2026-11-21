/**
 * The Path to Greatness: first-readers sign-up endpoint.
 *
 * Deployed as a web app (Execute as: Me, Who has access: Anyone).
 * The book site at eatmediatv.com/pathtogreatness posts each sign-up here.
 * This script writes one row per new address to the private "Signups" tab.
 * n8n reads that tab every 2 minutes and sends the welcome email.
 *
 * It also serves the unsubscribe page linked from every email.
 * Everything is in this one file: paste it over Code.gs and deploy.
 * No secrets live in this file: the unsubscribe signing key is created on
 * first use and kept in Script Properties.
 */

var SHEET_ID = '1QodevbYpJ7VLTZzdl058YS0sQ1zg99qJ-OioZRi6aDU';
var TAB = 'Signups';
var SITE = 'https://eatmediatv.com/pathtogreatness/';
var HEADERS = ['ID', 'Signed up', 'Email', 'Status', 'Welcome sent', 'Page', 'UTM source', 'UTM medium',
  'UTM campaign', 'UTM content', 'Referrer', 'Consent', 'Unsubscribe link', 'Notes', 'Signed up from'];
var MAX_NEW_PER_HOUR = 300;       // safety valve against floods
var MIN_FORM_MS = 1500;           // a person takes longer than this to type an address
var CONSENT_DEFAULT = 'News about The Path to Greatness; unsubscribe any time';

/* ---------------------------------------------------------------- sign-up */

function doPost(e) {
  try {
    var data = parseBody_(e);

    // Bots: a filled hidden field, or a form submitted faster than a person can type.
    // They get the same answer as a person so they learn nothing.
    if (data.website) return json_({ ok: true, status: 'added' });
    if (data.elapsed !== undefined && Number(data.elapsed) < MIN_FORM_MS) return json_({ ok: true, status: 'added' });

    var email = String(data.email || '').trim().toLowerCase();
    if (!isEmail_(email)) return json_({ ok: false, error: 'invalid_email' });

    var cache = CacheService.getScriptCache();
    var hourKey = 'n:' + Utilities.formatDate(new Date(), 'Etc/GMT', 'yyyyMMddHH');

    var lock = LockService.getScriptLock();
    if (!lock.tryLock(15000)) return json_({ ok: false, error: 'busy' });
    try {
      var sh = sheet_();
      var found = findRowBy_(sh, 3, email);
      if (found) {
        var status = String(sh.getRange(found, 4).getValue());
        if (status === 'unsubscribed') {
          // They chose to come back: send the welcome again and note it.
          sh.getRange(found, 4).setValue('new');
          sh.getRange(found, 5).setValue('');
          appendNote_(sh, found, 'Signed up again ' + stamp_());
          return json_({ ok: true, status: 'added' });
        }
        if (status === 'error') {
          // The welcome email failed earlier: queue it again.
          sh.getRange(found, 4).setValue('new');
          appendNote_(sh, found, 'Retried after a new sign-up ' + stamp_());
          return json_({ ok: true, status: 'added' });
        }
        return json_({ ok: true, status: 'already' });
      }

      var count = Number(cache.get(hourKey) || 0);
      if (count >= MAX_NEW_PER_HOUR) return json_({ ok: false, error: 'busy' });

      var id = Utilities.getUuid();
      sh.appendRow([
        id,
        new Date(),
        safe_(email),
        'new',
        '',
        safe_(clip_(data.page, 200)),
        safe_(clip_(data.utm_source, 80)),
        safe_(clip_(data.utm_medium, 80)),
        safe_(clip_(data.utm_campaign, 80)),
        safe_(clip_(data.utm_content, 80)),
        safe_(clip_(hostOnly_(data.referrer), 120)),
        safe_(clip_(data.consent || CONSENT_DEFAULT, 160)),
        unsubscribeUrl_(id),
        '',
        safe_(clip_(data.source, 40))
      ]);
      cache.put(hourKey, String(count + 1), 3600);
    } finally {
      lock.releaseLock();
    }
    return json_({ ok: true, status: 'added' });
  } catch (err) {
    console.error(err && err.stack ? err.stack : err);
    return json_({ ok: false, error: 'server' });
  }
}

/* ---------------------------------------------------------------- pages */

function doGet(e) {
  var p = (e && e.parameter) || {};
  if (p.a === 'health') return json_({ ok: true, sheet: !!sheet_(), unsubscribe_links: PropertiesService.getScriptProperties().getProperty('EXEC_URL') ? 'set' : 'EXEC_URL missing' });
  if (p.a === 'unsubscribe') {
    var valid = p.id && p.t && token_(p.id) === p.t;
    return page_(valid ? 'confirm' : 'invalid', p.id || '', p.t || '');
  }
  return page_('about', '', '');
}

/** Called from the confirmation page's button, so a link scanner opening the
 *  URL cannot unsubscribe anyone by itself. */
function confirmUnsubscribe(id, t) {
  if (!id || !t || token_(id) !== t) return { ok: false };
  var lock = LockService.getScriptLock();
  lock.waitLock(15000);
  try {
    var sh = sheet_();
    var row = findRowBy_(sh, 1, String(id));
    if (!row) return { ok: false };
    sh.getRange(row, 4).setValue('unsubscribed');
    appendNote_(sh, row, 'Unsubscribed ' + stamp_());
    return { ok: true };
  } finally {
    lock.releaseLock();
  }
}

/* ---------------------------------------------------------------- setup */

/** Run once from the editor (select setup, press Run) to grant access and
 *  check that the sheet is ready. Safe to run again. */
function setup() {
  var sh = sheet_();
  var head = sh.getRange(1, 1, 1, HEADERS.length).getValues()[0];
  for (var i = 0; i < HEADERS.length; i++) {
    if (String(head[i]) !== HEADERS[i]) throw new Error('Column ' + (i + 1) + ' should be "' + HEADERS[i] + '" but is "' + head[i] + '".');
  }
  secret_();
  console.log('Ready. Signups tab found with the expected columns. Rows so far: ' + Math.max(0, sh.getLastRow() - 1) + '.');
}

/* ---------------------------------------------------------------- helpers */

function sheet_() {
  var sh = SpreadsheetApp.openById(SHEET_ID).getSheetByName(TAB);
  if (!sh) throw new Error('Tab "' + TAB + '" not found.');
  return sh;
}

function parseBody_(e) {
  var out = {};
  if (e && e.postData && e.postData.contents) {
    try { out = JSON.parse(e.postData.contents); } catch (ignore) { out = {}; }
  }
  if (e && e.parameter) {
    Object.keys(e.parameter).forEach(function (k) { if (out[k] === undefined) out[k] = e.parameter[k]; });
  }
  return out;
}

function isEmail_(s) {
  return s.length >= 6 && s.length <= 254 && /^[^\s@<>()[\]\\,;:"]+@[^\s@<>()[\]\\,;:"]+\.[a-z]{2,24}$/i.test(s);
}

function findRowBy_(sh, col, value) {
  var last = sh.getLastRow();
  if (last < 2) return 0;
  var vals = sh.getRange(2, col, last - 1, 1).getValues();
  var want = String(value).toLowerCase();
  for (var i = 0; i < vals.length; i++) {
    if (String(vals[i][0]).replace(/^'/, '').toLowerCase() === want) return i + 2;
  }
  return 0;
}

function appendNote_(sh, row, text) {
  var cell = sh.getRange(row, 14);
  var cur = String(cell.getValue() || '');
  cell.setValue(cur ? cur + '; ' + text : text);
}

function clip_(v, n) { return String(v == null ? '' : v).replace(/[\u0000-\u001f]/g, ' ').trim().slice(0, n); }

/** Text that starts with = + - @ would be read by Sheets as a formula. */
function safe_(v) { return /^[=+\-@]/.test(v) ? "'" + v : v; }

function hostOnly_(url) {
  var m = String(url || '').match(/^https?:\/\/([^\/?#]+)/i);
  return m ? m[1].toLowerCase() : '';
}

function stamp_() { return Utilities.formatDate(new Date(), 'America/Los_Angeles', 'yyyy-MM-dd HH:mm'); }

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

function secret_() {
  var props = PropertiesService.getScriptProperties();
  var s = props.getProperty('UNSUB_SECRET');
  if (!s) {
    s = Utilities.getUuid() + Utilities.getUuid();
    props.setProperty('UNSUB_SECRET', s);
  }
  return s;
}

function token_(id) {
  var bytes = Utilities.computeHmacSha256Signature(String(id), secret_());
  return Utilities.base64EncodeWebSafe(bytes).replace(/=+$/, '').slice(0, 32);
}

function unsubscribeUrl_(id) {
  // EXEC_URL (Project Settings > Script properties) is the deployed /exec address. It is set by
  // hand once after the first deployment, because getUrl() can return the editor-only /dev address.
  var base = PropertiesService.getScriptProperties().getProperty('EXEC_URL') || ScriptApp.getService().getUrl();
  return base + '?a=unsubscribe&id=' + encodeURIComponent(id) + '&t=' + token_(id);
}

function page_(kind, id, t) {
  var tpl = HtmlService.createTemplate(PAGE_HTML);
  tpl.kind = kind;
  tpl.id = id;
  tpl.t = t;
  tpl.site = SITE;
  return tpl.evaluate()
    .setTitle('The Path to Greatness')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.DEFAULT);
}

/* ---------------------------------------------------------------- the page shown for unsubscribe links */

var PAGE_HTML = `<!doctype html>
<html lang="en">
<head>
<base target="_top">
<meta charset="utf-8">
<style>
  :root{--ink:#171a20;--paper:#f6f5f1;--muted:#5c6370;--slate:#919eb2;--rose:#a05561}
  *{box-sizing:border-box}
  html,body{margin:0;min-height:100%}
  body{background:var(--ink);color:#dfe3ea;font:400 18px/1.6 "EB Garamond",Georgia,"Times New Roman",serif;display:grid;place-items:center;padding:24px}
  .card{max-width:520px;width:100%;background:var(--paper);color:#1d2026;padding:44px 36px 36px;text-align:center}
  .mark{width:44px;height:44px;margin:0 auto 18px;display:block}
  .label{font:600 11px/1.4 Georgia,serif;letter-spacing:.3em;text-transform:uppercase;color:var(--muted)}
  h1{font:400 32px/1.15 "Cormorant Garamond",Georgia,serif;margin:14px 0 12px}
  p{margin:0 0 14px;color:#383d47}
  .q{font-style:italic;font-size:20px;line-height:1.45;color:#1d2026;margin:22px 0}
  button{font:600 12px/1 Georgia,serif;letter-spacing:.24em;text-transform:uppercase;background:var(--ink);color:var(--paper);border:0;padding:16px 26px;min-height:48px;cursor:pointer;margin-top:8px}
  button[disabled]{opacity:.6;cursor:default}
  a{color:#1d2026}
  .small{font-size:15px;color:var(--muted);margin-top:22px}
</style>
</head>
<body>
<main class="card">
  <svg class="mark" viewBox="0 0 24 24" fill="none" stroke="#5d6b82" stroke-width="1.4" stroke-linejoin="miter" stroke-linecap="round" aria-hidden="true"><path d="M12 3 21 20.6H3Z"/><path d="M8.7 9.6h6.6"/></svg>
  <p class="label">The Path to Greatness</p>

  <? if (kind === 'confirm') { ?>
    <div id="ask">
      <h1>Leave the list?</h1>
      <p>You will get no more email about The Path to Greatness.</p>
      <button type="button" id="go">Unsubscribe</button>
      <p class="small">Changed your mind? Close this page and nothing happens.</p>
    </div>
    <div id="done" hidden>
      <h1>You are off the list.</h1>
      <p>No more email will come from this list. If you sign up again on the site, you will be added back.</p>
      <p class="q">“You were never under construction. You were under excavation.”</p>
      <p class="small"><a href="<?= site ?>">Back to the book</a></p>
    </div>
    <p id="err" class="small" hidden>That did not go through. Write to eatmediatv@gmail.com and you will be removed by hand.</p>
    <script>
      document.getElementById('go').addEventListener('click', function () {
        var b = this; b.disabled = true; b.textContent = 'One moment';
        google.script.run
          .withSuccessHandler(function (r) {
            if (r && r.ok) { document.getElementById('ask').hidden = true; document.getElementById('done').hidden = false; }
            else { document.getElementById('err').hidden = false; b.disabled = false; b.textContent = 'Unsubscribe'; }
          })
          .withFailureHandler(function () { document.getElementById('err').hidden = false; b.disabled = false; b.textContent = 'Unsubscribe'; })
          .confirmUnsubscribe(<?= id ?>, <?= t ?>);  // inside <script>, printing scriptlets output JavaScript literals
      });
    </script>
  <? } else if (kind === 'invalid') { ?>
    <h1>This link has expired or is incomplete.</h1>
    <p>To leave the list, write to eatmediatv@gmail.com and you will be removed.</p>
    <p class="small"><a href="<?= site ?>">Back to the book</a></p>
  <? } else { ?>
    <h1>The first readers’ list</h1>
    <p>This address receives sign-ups from the book’s site.</p>
    <p class="small"><a href="<?= site ?>">Go to the book</a></p>
  <? } ?>
</main>
</body>
</html>
`;

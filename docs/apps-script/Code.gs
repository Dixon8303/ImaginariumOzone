/**
 * The Genius Index - validation data collector.
 *
 * Receives one anonymized result per assessment and appends it as a row to a
 * Google Sheet you own. No name, email, or account is collected.
 *
 * SETUP (about 10 minutes, one time) -- see docs/data-collection-setup.md:
 *   1. Create a Google Sheet. Note its ID from the URL
 *      (docs.google.com/spreadsheets/d/<THIS_IS_THE_ID>/edit).
 *   2. Paste SHEET_ID below.
 *   3. Deploy this script: Deploy > New deployment > Web app >
 *      Execute as: Me,  Who has access: Anyone.  Copy the Web-App URL.
 *   4. Paste that URL into SUBMIT_URL in docs/index.html and redeploy the site.
 *
 * UPDATING an existing deployment (this file changed after you first set up)?
 * Paste this whole file over your old one, then Deploy > Manage deployments >
 * pick your deployment > pencil icon > Version: New version > Deploy. The
 * Web-App URL does NOT change, so you do not need to touch SUBMIT_URL again.
 */

// Use STRAIGHT quotes ' ' and paste ONLY the ID (the part between /d/ and /edit),
// not the whole spreadsheet URL. Smart/curly quotes here cause a deploy syntax error.
var SHEET_ID = 'PASTE_YOUR_SHEET_ID_HERE';
var SHEET_NAME = 'results';

// The live assessment site. Used to build each row's results_url -- a link
// that reopens that exact submission via the site's #view= archived-result
// mode (see bootFromHash in docs/index.html). Straight quotes only, as above.
var SITE_URL = 'https://dixon8303.github.io/ImaginariumOzone/';

// Manual-recovery path: the results page's "Pilot data" block lets a taker
// copy their raw JSON if the automatic upload silently failed. Paste that
// text into column A of this sheet (any row below the header) and it's
// imported into SHEET_NAME the same way a real submission would be --
// same columns, same results_url. See onEdit_ below.
var PASTE_SHEET_NAME = 'paste_import';

// Original columns, in their original order -- NEVER reorder or rename these.
// Any sheet already collecting data has this exact header row on row 1, and
// reordering would misalign every row already collected.
var HEADERS = [
  'received_at', 'version', 'code', 'consent', 'client_ts', 'minutes',
  'braid', 'braid_tier', 'braid_pair', 'signature', 'adjacent',
  // per-domain composite scores
  'KIN', 'SEN', 'ADP', 'ANL', 'MEM', 'GEN', 'REL', 'EXP', 'PER',
  // flag_latent and flag_diverge are retired (the gap model changed upstream) and
  // stay blank going forward -- kept only so older rows' columns don't shift.
  'flag_sdr', 'flag_latent', 'flag_aspirational', 'flag_diverge', 'rank_overlap',
  'ranks_top', 'ranks_bot',
  'raw_json',
  // Added later -- always append new fields HERE, at the end, never in the
  // middle, so no already-collected row ever shifts columns.
  'event', 'shape', 'reachable', 'flag_unclaimed', 'top_unclaimed',
  // Reopens this exact submission on the live site (blank for 'start' rows,
  // which have no answers yet to show).
  'results_url'
];

// Ensure the header row has every column in HEADERS, appending any that are
// missing (for a sheet that already has the older, shorter header row) without
// touching or reordering columns that already exist.
function ensureHeaders_(sheet) {
  if (sheet.getLastRow() === 0) {
    sheet.appendRow(HEADERS);
    return;
  }
  var lastCol = sheet.getLastColumn();
  var existing = lastCol > 0 ? sheet.getRange(1, 1, 1, lastCol).getValues()[0] : [];
  var missing = HEADERS.filter(function (h) { return existing.indexOf(h) === -1; });
  if (missing.length) {
    sheet.getRange(1, existing.length + 1, 1, missing.length).setValues([missing]);
  }
}

// Builds one results-sheet row's values, keyed by HEADER NAME (not column
// position). Shared by doPost (the automatic path) and onEdit (the
// paste-import recovery path), so both produce identical values.
function buildResultFields_(data) {
  // Rows sent before this update had no "event" field at all -- treat those,
  // and any row that omits it, as a completed submission.
  var event = data.event || 'complete';
  var dom = data.domains || {};
  var s = function (id) { return dom[id] ? dom[id].score : ''; };
  var f = data.flags || {};
  var rawJson = JSON.stringify(data);

  // Only a 'complete' submission has answers worth reopening -- a 'start'
  // ping has no domains yet, so #view= would just show a broken page.
  var resultsUrl = (event === 'complete' && dom && Object.keys(dom).length)
    ? SITE_URL + '#view=' + encodeURIComponent(rawJson)
    : '';

  return {
    received_at: new Date(),
    version: data.v || '',
    code: data.code || '',
    consent: data.consent === false ? 'no' : 'yes',
    client_ts: data.ts || '',
    minutes: data.minutes || '',
    braid: data.braid || '',
    braid_tier: data.braidTier || '',
    braid_pair: (data.braidPair || []).join('-'),
    signature: data.signature || '',
    adjacent: (data.adjacent || []).join(' '),
    KIN: s('KIN'), SEN: s('SEN'), ADP: s('ADP'), ANL: s('ANL'), MEM: s('MEM'),
    GEN: s('GEN'), REL: s('REL'), EXP: s('EXP'), PER: s('PER'),
    flag_sdr: f.sdr ? 'yes' : 'no',
    flag_latent: '', // retired, see HEADERS comment
    flag_aspirational: (f.aspirational || []).join(' '),
    flag_diverge: '', // retired, see HEADERS comment
    rank_overlap: f.rankOverlap != null ? f.rankOverlap : '',
    ranks_top: (data.ranksTop || []).join(' '),
    ranks_bot: (data.ranksBot || []).join(' '),
    raw_json: rawJson,
    event: event,
    shape: data.shape || '',
    reachable: (data.reachable || []).join(' | '),
    flag_unclaimed: (f.unclaimed || []).join(' '),
    top_unclaimed: f.topUnclaimed || '',
    results_url: resultsUrl
  };
}

// Appends one row, placing each field under its header's ACTUAL column in
// the live sheet (looked up by name), never by fixed array position.
// ensureHeaders_ only ever appends missing columns at the end -- it can't
// guarantee no gaps or stray columns exist earlier in the row (e.g. from a
// manual edit in Sheets), and a plain appendRow(array) silently misaligns
// every field after the first drifted column. Looking up each value by its
// header's name is the only way that's immune to that kind of drift.
function appendResultRow_(sheet, data) {
  ensureHeaders_(sheet);
  var lastCol = sheet.getLastColumn();
  var headerRow = sheet.getRange(1, 1, 1, lastCol).getValues()[0];
  var fields = buildResultFields_(data);
  var row = new Array(lastCol).fill('');
  headerRow.forEach(function (h, i) {
    if (h && fields.hasOwnProperty(h)) row[i] = fields[h];
  });
  sheet.appendRow(row);
}

function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    var sheet = SpreadsheetApp.openById(SHEET_ID).getSheetByName(SHEET_NAME)
             || SpreadsheetApp.openById(SHEET_ID).insertSheet(SHEET_NAME);
    appendResultRow_(sheet, data);

    return ContentService.createTextOutput(JSON.stringify({ ok: true }))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ ok: false, error: String(err) }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

// GET with no params: a plain healthcheck you can open in a browser.
// GET with ?stats=1&key=YOUR_SECRET: aggregate-only JSON (counts and averages
// only -- never a raw row, a code, or per-person data) for YOUR EYES ONLY.
// This is not linked from the public site. The key lives in Script Properties
// (Project Settings > Script Properties in the Apps Script editor), never in
// this file, so it never ends up in the public GitHub repo. Without the
// correct key, this behaves exactly like a plain GET -- the feature is
// invisible to anyone who doesn't already have the key.
function doGet(e) {
  var wantsStats = e && e.parameter && e.parameter.stats;
  var suppliedKey = e && e.parameter && e.parameter.key;
  var realKey = PropertiesService.getScriptProperties().getProperty('STATS_KEY');
  if (wantsStats && realKey && suppliedKey === realKey) {
    return ContentService.createTextOutput(JSON.stringify(computeStats_()))
      .setMimeType(ContentService.MimeType.JSON);
  }
  return ContentService.createTextOutput('Genius Index collector is running.');
}

function computeStats_() {
  var empty = {
    totalStarts: 0, totalCompletes: 0, conversionRate: null,
    topBraids: [], shapeCounts: { Tower: 0, Ridge: 0, Anchored: 0, Plateau: 0 },
    avgMinutes: null, updatedAt: new Date().toISOString()
  };
  var sheet = SpreadsheetApp.openById(SHEET_ID).getSheetByName(SHEET_NAME);
  if (!sheet || sheet.getLastRow() < 2) return empty;

  var values = sheet.getDataRange().getValues();
  var headerRow = values[0];
  var col = {};
  headerRow.forEach(function (h, i) { col[h] = i; });

  var totalStarts = 0, totalCompletes = 0, minutesSum = 0, minutesCount = 0;
  var braidCounts = {};
  var shapeCounts = { Tower: 0, Ridge: 0, Anchored: 0, Plateau: 0 };

  for (var r = 1; r < values.length; r++) {
    var row = values[r];
    var event = col.hasOwnProperty('event') ? row[col.event] : '';
    if (event === 'start') { totalStarts++; continue; }
    // 'complete', or blank for rows collected before the event column existed.
    totalCompletes++;
    var braid = col.hasOwnProperty('braid') ? row[col.braid] : '';
    if (braid) braidCounts[braid] = (braidCounts[braid] || 0) + 1;
    var shape = col.hasOwnProperty('shape') ? row[col.shape] : '';
    if (shape && shapeCounts.hasOwnProperty(shape)) shapeCounts[shape]++;
    var minutes = col.hasOwnProperty('minutes') ? row[col.minutes] : '';
    if (typeof minutes === 'number' && minutes > 0) { minutesSum += minutes; minutesCount++; }
  }

  var topBraids = Object.keys(braidCounts)
    .map(function (name) { return { name: name, count: braidCounts[name] }; })
    .sort(function (a, b) { return b.count - a.count; })
    .slice(0, 10);

  return {
    totalStarts: totalStarts,
    totalCompletes: totalCompletes,
    // Meaningful only from the point this feature shipped -- older completions
    // have no matching 'start' row, so conversion undercounts historical data.
    conversionRate: totalStarts > 0 ? Math.round((totalCompletes / totalStarts) * 100) : null,
    topBraids: topBraids,
    shapeCounts: shapeCounts,
    avgMinutes: minutesCount > 0 ? Math.round((minutesSum / minutesCount) * 10) / 10 : null,
    updatedAt: new Date().toISOString()
  };
}

/* ============ Manual recovery: paste-import sheet ============
 * A dedicated tab where you can paste a taker's raw JSON (from the results
 * page's "Pilot data" block) and have it imported automatically -- no manual
 * column-by-column transcription. Column A: paste the JSON. Column B: status,
 * filled in automatically once imported. Leave column B blank to reprocess a
 * row (e.g. if you pasted into the wrong row); a non-blank status is treated
 * as "already handled" and skipped on later edits, so nothing double-imports.
 */

function ensurePasteSheet_(ss) {
  var sheet = ss.getSheetByName(PASTE_SHEET_NAME);
  if (sheet) return sheet;
  sheet = ss.insertSheet(PASTE_SHEET_NAME);
  sheet.getRange(1, 1, 1, 2).setValues([['Paste raw JSON here (one block per row)', 'Status']]);
  sheet.getRange(1, 1, 1, 2).setFontWeight('bold');
  sheet.setColumnWidth(1, 500);
  sheet.setColumnWidth(2, 300);
  return sheet;
}

// Runs automatically when the sheet is opened (a container-bound simple
// trigger -- no separate deployment or authorization step needed). Creates
// the paste-import tab on first open after this update, and adds a menu
// entry so it's easy to find again later.
function onOpen(e) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  ensurePasteSheet_(ss);
  SpreadsheetApp.getUi()
    .createMenu('Genius Index')
    .addItem('Go to paste-import tab', 'showPasteSheet_')
    .addToUi();
}

function showPasteSheet_() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  ss.setActiveSheet(ensurePasteSheet_(ss));
}

// Runs automatically on every edit to this spreadsheet (also a simple
// trigger). Only acts on edits to column A of the paste-import tab, below
// the header row, where that row's status (column B) is still blank.
function onEdit(e) {
  if (!e || !e.range) return;
  var sheet = e.range.getSheet();
  if (sheet.getName() !== PASTE_SHEET_NAME) return;
  if (e.range.getColumn() !== 1 || e.range.getRow() < 2) return;

  var row = e.range.getRow();
  var statusCell = sheet.getRange(row, 2);
  if (String(statusCell.getValue()).trim() !== '') return; // already handled

  var text = String(e.range.getValue()).trim();
  if (!text) return; // cleared the cell -- nothing to do

  try {
    var data = JSON.parse(text);
    if (!data || typeof data !== 'object' || (!data.domains && data.event !== 'start')) {
      statusCell.setValue('Not recognized as a Genius Index result block -- left as-is.');
      return;
    }
    // Simple triggers (onEdit/onOpen) run with limited authorization and
    // cannot call SpreadsheetApp.openById(), even for the same spreadsheet
    // they're bound to -- that requires a broader scope only a full
    // (non-trigger) execution has. e.source / getActiveSpreadsheet() is the
    // one they ARE allowed to use, and since paste_import always lives in
    // the same file as results, that's exactly the right one here.
    var ss = e.source || SpreadsheetApp.getActiveSpreadsheet();
    var resultsSheet = ss.getSheetByName(SHEET_NAME) || ss.insertSheet(SHEET_NAME);
    appendResultRow_(resultsSheet, data);
    statusCell.setValue('Imported ' + new Date().toLocaleString());
  } catch (err) {
    // Most common cause: an incomplete paste (still mid-paste when this fired)
    // or stray characters. Leaving the status blank lets you just paste again.
    statusCell.setValue('Import failed: ' + String(err));
  }
}

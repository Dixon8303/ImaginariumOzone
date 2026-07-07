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
  'event', 'shape', 'reachable', 'flag_unclaimed', 'top_unclaimed'
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

function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    var sheet = SpreadsheetApp.openById(SHEET_ID).getSheetByName(SHEET_NAME)
             || SpreadsheetApp.openById(SHEET_ID).insertSheet(SHEET_NAME);
    ensureHeaders_(sheet);

    // Rows sent before this update had no "event" field at all -- treat those,
    // and any row that omits it, as a completed submission.
    var event = data.event || 'complete';
    var dom = data.domains || {};
    var s = function (id) { return dom[id] ? dom[id].score : ''; };
    var f = data.flags || {};

    sheet.appendRow([
      new Date(),
      data.v || '',
      data.code || '',
      data.consent === false ? 'no' : 'yes',
      data.ts || '',
      data.minutes || '',
      data.braid || '',
      data.braidTier || '',
      (data.braidPair || []).join('-'),
      data.signature || '',
      (data.adjacent || []).join(' '),
      s('KIN'), s('SEN'), s('ADP'), s('ANL'), s('MEM'), s('GEN'), s('REL'), s('EXP'), s('PER'),
      f.sdr ? 'yes' : 'no',
      '', // flag_latent -- retired, see HEADERS comment
      (f.aspirational || []).join(' '),
      '', // flag_diverge -- retired, see HEADERS comment
      f.rankOverlap != null ? f.rankOverlap : '',
      (data.ranksTop || []).join(' '),
      (data.ranksBot || []).join(' '),
      JSON.stringify(data),
      event,
      data.shape || '',
      (data.reachable || []).join(' | '),
      (f.unclaimed || []).join(' '),
      f.topUnclaimed || ''
    ]);

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

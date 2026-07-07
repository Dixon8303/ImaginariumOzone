/**
 * The Genius Index — validation data collector.
 *
 * Receives one anonymized result per assessment and appends it as a row to a
 * Google Sheet you own. No name, email, or account is collected.
 *
 * SETUP (about 10 minutes, one time) — see docs/data-collection-setup.md:
 *   1. Create a Google Sheet. Note its ID from the URL
 *      (docs.google.com/spreadsheets/d/<THIS_IS_THE_ID>/edit).
 *   2. Paste SHEET_ID below.
 *   3. Deploy this script: Deploy > New deployment > Web app >
 *      Execute as: Me,  Who has access: Anyone.  Copy the Web-App URL.
 *   4. Paste that URL into SUBMIT_URL in docs/index.html and redeploy the site.
 */

var SHEET_ID = 'PASTE_YOUR_SHEET_ID_HERE';
var SHEET_NAME = 'results';

// Header written once, on the first submission into an empty sheet.
var HEADERS = [
  'received_at', 'version', 'code', 'consent', 'client_ts', 'minutes',
  'braid', 'braid_tier', 'braid_pair', 'signature', 'adjacent',
  // per-domain composite scores
  'KIN', 'SEN', 'ADP', 'ANL', 'MEM', 'GEN', 'REL', 'EXP', 'PER',
  'flag_sdr', 'flag_latent', 'flag_aspirational', 'flag_diverge', 'rank_overlap',
  'ranks_top', 'ranks_bot',
  'raw_json'
];

function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    var sheet = SpreadsheetApp.openById(SHEET_ID).getSheetByName(SHEET_NAME)
             || SpreadsheetApp.openById(SHEET_ID).insertSheet(SHEET_NAME);
    if (sheet.getLastRow() === 0) sheet.appendRow(HEADERS);

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
      (data.braidPair || []).join('·'),
      data.signature || '',
      (data.adjacent || []).join(' '),
      s('KIN'), s('SEN'), s('ADP'), s('ANL'), s('MEM'), s('GEN'), s('REL'), s('EXP'), s('PER'),
      f.sdr ? 'yes' : 'no',
      (f.latent || []).join(' '),
      (f.aspirational || []).join(' '),
      (f.diverge || []).join(' '),
      f.rankOverlap != null ? f.rankOverlap : '',
      (data.ranksTop || []).join(' '),
      (data.ranksBot || []).join(' '),
      JSON.stringify(data)
    ]);

    return ContentService.createTextOutput(JSON.stringify({ ok: true }))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ ok: false, error: String(err) }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

// Optional: lets you open the Web-App URL in a browser to confirm it's live.
function doGet() {
  return ContentService.createTextOutput('Genius Index collector is running.');
}

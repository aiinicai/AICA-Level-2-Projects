/**
 * ===========================================================================
 *  BALANCE CONFIRMATION BRIDGE  -  Google Apps Script
 * ---------------------------------------------------------------------------
 *  Runs on Google's servers next to your mailbox, so it keeps collecting
 *  confirmation replies while your computer is switched off.
 *
 *  Every ten minutes it:
 *    1. searches Gmail for unread balance-confirmation replies
 *    2. pulls out the reference code, the sender, the body and the text of
 *       every attachment (PDF and Word are read through Drive's converter;
 *       scans and photographs go through Drive's OCR)
 *    3. reads the confirmed figure out of the signed slip
 *    4. writes one row per reply into a Google Sheet
 *    5. labels the message BCG/Processed, or BCG/Needs review, and never
 *       deletes anything
 *
 *  The desktop application then syncs the sheet and produces the reports.
 *
 *  SET-UP  (about ten minutes, once)
 *  ---------------------------------------------------------------------------
 *   1. Open https://script.google.com and create a new project.
 *   2. Delete the sample code and paste this file in.
 *   3. In Services (+), add "Drive API"  (identifier: Drive, version v3).
 *      It is used only to convert attachments to text.
 *   4. Run the function  setUp  once.  Google will ask you to authorise it;
 *      approve the Gmail, Drive and Sheets permissions it lists.  setUp
 *      creates the spreadsheet, the two labels and the ten-minute trigger.
 *   5. Deploy > New deployment > Web app, with
 *         Execute as:      Me
 *         Who has access:  Anyone with the link
 *      "Anyone with the link" is what lets the desktop application read the
 *      feed; the data is guarded by the 40-character key in the address,
 *      which only you hold.  Treat that address as a password.
 *   6. Run the function  feedUrl  and copy what it prints into the
 *      application:  Settings > Gmail bridge > Feed address.
 *
 *  If your Workspace administrator does not allow "Anyone with the link",
 *  deploy it to your domain instead and use the offline route: run
 *  exportFeedToDrive, download the JSON file it writes, and load it with
 *  "Import replies (JSON)" on the Confirmations received page.
 *
 *  Run  resetAccessKey  if the address is ever disclosed: the old one stops
 *  working at once.
 *  To stop collecting, run  tearDown  (removes the trigger, keeps the data).
 *
 *  PERMISSIONS
 *  ---------------------------------------------------------------------------
 *  The accompanying appsscript.json pins the Gmail permission to
 *  gmail.modify: read a message and apply a label.  It is deliberately NOT
 *  the full-mailbox scope that Apps Script would otherwise request, and it
 *  cannot delete mail.  The Drive, Docs and Sheets permissions are for the
 *  spreadsheet this script writes and for the temporary file each attachment
 *  is converted through; that file is deleted the moment its text has been
 *  read.  No password is asked for and none is stored.  Nothing is sent
 *  anywhere outside your own Google account.
 * ===========================================================================
 */

/* ------------------------------------------------------------------ config */
var CONFIG = {
  // Gmail search. Keep "is:unread" so a message is only ever picked up once.
  QUERY: 'is:unread subject:"balance confirmation" newer_than:180d',
  MAX_THREADS: 50,            // per run; Gmail quotas are generous but finite
  SHEET_NAME: 'Replies',
  LOG_SHEET_NAME: 'Audit trail',
  LABEL_DONE: 'BCG/Processed',
  LABEL_REVIEW: 'BCG/Needs review',
  TRIGGER_MINUTES: 10,
  MARK_READ_ON_SUCCESS: true,
  // Confidence below which a reply is sent for review instead of recorded
  MIN_CONFIDENCE: 0.70,
  OCR_LANGUAGE: 'en'
};

var PROP = PropertiesService.getScriptProperties();
var SHEET_ID_KEY = 'BCG_SHEET_ID';
var ACCESS_KEY = 'BCG_ACCESS_KEY';

/* The columns written to the sheet.  The desktop application reads these by
   name, so new columns may be added at the end without breaking it. */
var COLUMNS = [
  'reply_id', 'received_at', 'from_email', 'from_name', 'subject',
  'reference', 'thread_id', 'in_reply_to', 'amount', 'currency', 'stance',
  'confirmed_on', 'signed', 'confidence', 'source', 'bounced', 'body',
  'attachment_names', 'attachment_text', 'message_link', 'status', 'note'
];

/* ========================================================================= */
/*  SET-UP AND TEARDOWN                                                      */
/* ========================================================================= */

function setUp() {
  var sheet = openSheet_();
  ensureLabel_(CONFIG.LABEL_DONE);
  ensureLabel_(CONFIG.LABEL_REVIEW);
  var key = accessKey_();

  var existing = ScriptApp.getProjectTriggers();
  for (var i = 0; i < existing.length; i++) {
    if (existing[i].getHandlerFunction() === 'pollMailbox') {
      ScriptApp.deleteTrigger(existing[i]);
    }
  }
  ScriptApp.newTrigger('pollMailbox')
    .timeBased().everyMinutes(CONFIG.TRIGGER_MINUTES).create();

  var url = SpreadsheetApp.openById(PROP.getProperty(SHEET_ID_KEY)).getUrl();
  Logger.log('Spreadsheet:  ' + url);
  Logger.log('Polling every ' + CONFIG.TRIGGER_MINUTES + ' minutes.');
  Logger.log('Access key:   ' + key);
  Logger.log('Now deploy this project as a Web app, then run  feedUrl  to '
             + 'get the address to paste into the application.');
  return url;
}

/**
 * The address to paste into the application's Settings > Gmail bridge.
 * Run this AFTER deploying the project as a web app.
 */
function feedUrl() {
  var key = encodeURIComponent(accessKey_());
  var base = '';
  try {
    base = ScriptApp.getService().getUrl() || '';
  } catch (error) {
    base = '';
  }
  Logger.log('ACCESS KEY:  ' + key);

  // getUrl() cannot be trusted on the V8 runtime: run from the editor it may
  // hand back the private /dev address, which always demands a browser
  // sign-in and can never be read by the application.  So it is used only
  // when it plainly gives a public /exec address, and the auditor is told
  // where to find that address by hand either way.
  if (base.slice(-5) === '/exec') {
    Logger.log('Paste this into the application:\n' + base + '?key=' + key);
    Logger.log('If the application says the bridge returned a page rather '
               + 'than data, use the address under Deploy > Manage '
               + 'deployments instead, with  ?key=' + key + '  on the end.');
    return base + '?key=' + key;
  }

  Logger.log(base
    ? 'The address this project reports is private (it ends in /dev) and '
      + 'cannot be read by the application.'
    : 'No deployment found. Deploy > New deployment > Web app first.');
  Logger.log('Open  Deploy > Manage deployments, copy the Web app URL - it '
             + 'ends in /exec - and paste it into the application with  ?key='
             + key + '  added to the end, so that it reads:');
  Logger.log('https://script.google.com/macros/s/AKfycb....../exec?key=' + key);
  return '';
}

/** Invalidates the old address and issues a new one. */
function resetAccessKey() {
  PROP.deleteProperty(ACCESS_KEY);
  return feedUrl();
}

/** A 40-character key, created once and kept in the script's properties.
 *  Two random UUIDs, hex digits only: comfortably over 128 bits.  It is the
 *  second secret guarding the feed, after the deployment id itself. */
function accessKey_() {
  var key = PROP.getProperty(ACCESS_KEY);
  if (!key) {
    key = (Utilities.getUuid() + Utilities.getUuid())
            .replace(/-/g, '').slice(0, 40);
    PROP.setProperty(ACCESS_KEY, key);
  }
  return key;
}

function tearDown() {
  var triggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < triggers.length; i++) {
    if (triggers[i].getHandlerFunction() === 'pollMailbox') {
      ScriptApp.deleteTrigger(triggers[i]);
    }
  }
  Logger.log('Polling stopped.  Your spreadsheet and labels are untouched.');
}

/** Reads one message by id and logs what would be recorded - useful while
 *  you are checking the set-up, because it changes nothing. */
function dryRun() {
  var threads = GmailApp.search(CONFIG.QUERY, 0, 1);
  if (!threads.length) {
    Logger.log('No message matches: ' + CONFIG.QUERY);
    return;
  }
  var messages = threads[0].getMessages();
  var record = readMessage_(messages[messages.length - 1]);
  Logger.log(JSON.stringify(record, null, 2));
}

/* ========================================================================= */
/*  THE POLL                                                                 */
/* ========================================================================= */

function pollMailbox() {
  // one run at a time, so a slow run cannot overlap the next trigger
  var lock = LockService.getScriptLock();
  if (!lock.tryLock(10000)) {
    return;
  }
  try {
    var sheet = openSheet_();
    var known = existingIds_(sheet);
    var done = ensureLabel_(CONFIG.LABEL_DONE);
    var review = ensureLabel_(CONFIG.LABEL_REVIEW);
    var threads = GmailApp.search(CONFIG.QUERY, 0, CONFIG.MAX_THREADS);
    var added = 0, flagged = 0;

    for (var t = 0; t < threads.length; t++) {
      var messages = threads[t].getMessages();
      for (var i = 0; i < messages.length; i++) {
        var message = messages[i];
        if (!message.isUnread()) { continue; }
        var id = message.getId();
        if (known[id]) { continue; }        // never recorded twice
        // Our own request is copied to the engagement team, so it arrives in
        // this very mailbox - with a letter that states the client's own
        // figure.  Recorded as a reply it would "agree" the balance by
        // itself, so it is left alone: not recorded, not labelled.
        if (isOwnRequest_(message)) { continue; }

        var record;
        try {
          record = readMessage_(message);
        } catch (error) {
          log_('error', id, String(error));
          threads[t].addLabel(review);
          flagged++;
          continue;
        }

        // An attachment that could not be read is evidence nobody has seen,
        // so the reply goes for review however well the body reads.
        var reasons = [];
        if (record.unread_attachments) {
          reasons.push(record.unread_attachments +
                       ' attachment(s) could not be read');
        }
        if (!record.bounced && record.amount === '') {
          reasons.push('no confirmed figure found');
        }
        if (!record.bounced && record.amount !== '' &&
            record.confidence < CONFIG.MIN_CONFIDENCE) {
          reasons.push('the figure was read with low confidence');
        }
        var ok = record.bounced || reasons.length === 0;
        record.status = ok ? 'recorded' : 'needs review';
        record.note = reasons.join('; ');
        appendRow_(sheet, record);
        known[id] = true;
        added++;

        if (ok) {
          threads[t].addLabel(done);
          if (CONFIG.MARK_READ_ON_SUCCESS) { message.markRead(); }
          log_('recorded', id, record.reference + ' ' + record.currency + ' ' +
                               record.amount);
        } else {
          threads[t].addLabel(review);
          flagged++;
          log_('needs review', id, record.note || 'nothing to record');
        }
      }
    }
    if (added) {
      PROP.setProperty('BCG_LAST_RUN', new Date().toISOString());
    }
    Logger.log('Processed ' + added + ' message(s); ' + flagged +
               ' need review.');
  } finally {
    lock.releaseLock();
  }
}

/* ========================================================================= */
/*  READING ONE MESSAGE                                                      */
/* ========================================================================= */

/** True for the request the application itself sent.  The application marks
 *  every request with an X-BCG-Request header, which no mail program copies
 *  into a reply.  For requests sent before that marker existed, a message
 *  from this mailbox's own address that is not an answer to anything is
 *  treated the same way. */
function isOwnRequest_(message) {
  try {
    if (message.getHeader('X-BCG-Request')) { return true; }
  } catch (ignored) {}
  var me = '';
  try { me = (Session.getEffectiveUser().getEmail() || '').toLowerCase(); }
  catch (ignored) { me = ''; }
  if (me && emailOf_(message.getFrom() || '') === me) {
    var answered = '';
    try { answered = message.getHeader('In-Reply-To') || ''; }
    catch (ignored) { answered = ''; }
    var subject = (message.getSubject() || '').toLowerCase();
    if (!answered && !/^(re|fw|fwd)\s*:/.test(subject)) { return true; }
  }
  return false;
}

function readMessage_(message) {
  var body = message.getPlainBody() || stripHtml_(message.getBody() || '');
  var subject = message.getSubject() || '';
  var from = message.getFrom() || '';
  var raw = message.getRawContent() || '';

  var names = [], texts = [], unreadable = 0;
  var attachments = message.getAttachments({
    includeInlineImages: false, includeAttachments: true
  });
  for (var i = 0; i < attachments.length; i++) {
    var attachment = attachments[i];
    names.push(attachment.getName());
    try {
      var text = attachmentText_(attachment);
      texts.push(text);
      if (!String(text).replace(/\s+/g, '')) { unreadable++; }
    } catch (error) {
      texts.push('');
      unreadable++;
      log_('attachment', message.getId(),
           attachment.getName() + ': ' + String(error));
    }
  }
  var attachmentText = texts.join('\n');
  var bounced = looksLikeBounce_(from, subject, body);
  var extracted = extractAmount_(attachmentText, body);

  return {
    reply_id: message.getId(),
    received_at: formatDate_(message.getDate()),
    from_email: emailOf_(from),
    from_name: nameOf_(from),
    subject: subject,
    reference: findReference_([subject, body, attachmentText]),
    thread_id: message.getThread().getId(),
    in_reply_to: headerOf_(raw, 'In-Reply-To'),
    amount: extracted.amount,
    currency: extracted.currency,
    // the letter itself says "not in agreement", so only the party's own
    // covering words are read for where it stands
    stance: stance_(stripQuoted_(body)),
    confirmed_on: extracted.confirmedOn,
    signed: /\b(signed|signature|authorised signatory|authorized signatory|stamp|seal)\b/i
              .test(body + ' ' + attachmentText),
    confidence: bounced ? 1 : extracted.confidence,
    source: extracted.source,
    bounced: bounced,
    body: clip_(body, 4000),
    attachment_names: names.join('; '),
    attachment_text: clip_(attachmentText, 8000),
    unread_attachments: unreadable,
    message_link: 'https://mail.google.com/mail/u/0/#all/' + message.getId(),
    status: '',
    note: ''
  };
}

/** PDF, Word and images all become text through Drive; nothing is kept. */
function attachmentText_(attachment) {
  var type = (attachment.getContentType() || '').toLowerCase();
  var name = (attachment.getName() || '').toLowerCase();

  if (type.indexOf('text/') === 0 || /\.(txt|csv)$/.test(name)) {
    return attachment.getDataAsString();
  }
  var convertible = type.indexOf('pdf') >= 0 ||
                    type.indexOf('word') >= 0 ||
                    type.indexOf('officedocument') >= 0 ||
                    type.indexOf('image/') === 0 ||
                    /\.(pdf|docx?|png|jpe?g|tiff?|heic)$/.test(name);
  if (!convertible) { return ''; }

  var file = null;
  try {
    // ocr:true also covers a scanned PDF or a photograph of a signed slip
    file = Drive.Files.create(
      { name: 'bcg-temp-' + Utilities.getUuid(), mimeType: 'application/vnd.google-apps.document' },
      attachment.copyBlob(),
      { ocr: true, ocrLanguage: CONFIG.OCR_LANGUAGE, supportsAllDrives: true });
    return DocumentApp.openById(file.id).getBody().getText();
  } finally {
    if (file && file.id) {
      try { Drive.Files.remove(file.id); } catch (ignored) {}
    }
  }
}

/* ------------------------------------------------------- reading the figure */
/* The signed slip reads:
     "We hereby confirm that the amount payable by us to <client>
      as on <date> is <CCY> <amount>"                                        */
var SLIP_RE = new RegExp(
  'we\\s+hereby\\s+confirm[\\s\\S]{0,200}?\\bis\\b\\s*' +
  '(INR|USD|EUR|GBP|AED|SGD|AUD|CAD|JPY|CHF|Rs\\.?|₹|\\$|€|£)?' +
  '\\s*(\\(?-?[0-9][0-9,.\\s]*\\)?)', 'i');
var FALLBACK_RE = new RegExp(
  '(?:balance|amount)[^\\n\\r]{0,60}?(?:is|:)\\s*' +
  '(INR|USD|EUR|GBP|AED|SGD|Rs\\.?|₹|\\$|€|£)?' +
  '\\s*(\\(?-?[0-9][0-9,.\\s]*\\)?)', 'i');

function extractAmount_(attachmentText, body) {
  // The letter itself states the client's figure ("According to our records,
  // the amount due from you ... is INR ...").  When the letter comes back,
  // that sentence is NOT the party's confirmation, so on an attachment only
  // a completed slip is read; the looser pattern is kept for the party's own
  // covering words, with the quoted original removed.
  var candidates = [
    { source: 'attachment', text: attachmentText, loose: false },
    { source: 'email body', text: stripQuoted_(body), loose: true }
  ];
  for (var i = 0; i < candidates.length; i++) {
    var text = (candidates[i].text || '').replace(/[ \t]+/g, ' ');
    if (!text) { continue; }
    var found = SLIP_RE.exec(text);
    var confidence = 0.95;
    if (!found && candidates[i].loose) {
      found = FALLBACK_RE.exec(text);
      confidence = 0.75;
    }
    if (!found) { continue; }

    var value = parseAmount_(found[2]);
    if (value === null) { continue; }
    return {
      amount: value,
      currency: currencyOf_(found[1]),
      confidence: confidence,
      source: candidates[i].source,
      confirmedOn: confirmedOn_(text)
    };
  }
  return { amount: '', currency: '', confidence: 0, source: '', confirmedOn: '' };
}

/** The party's own words: the reply with the quoted original removed. */
function stripQuoted_(text) {
  var value = String(text || '').replace(/\r\n/g, '\n');
  var cut = /^[ \t>]*On\b[^\n]{0,240}(?:\n[^\n]{0,120})?\bwrote:[ \t]*$/im
              .exec(value);
  if (cut) { value = value.slice(0, cut.index); }
  var kept = [];
  var lines = value.split('\n');
  for (var i = 0; i < lines.length; i++) {
    var bare = lines[i].replace(/^\s+|\s+$/g, '');
    if (bare.charAt(0) === '>') { continue; }
    if (/^-{2,}\s*(original|forwarded) message\s*-{2,}/i.test(bare)) { break; }
    if (/^_{10,}$/.test(bare)) { break; }
    if (kept.length && /^from:\s.+/i.test(bare)) { break; }
    kept.push(lines[i]);
  }
  return kept.join('\n');
}

/** Handles 1,25,000.00 and 1,234,567.89 and (5,000) and 1.234.567,89. */
function parseAmount_(raw) {
  if (!raw) { return null; }
  var text = String(raw).trim();
  var negative = /^\(.*\)$/.test(text);
  if (negative) { text = text.slice(1, -1); }
  var body = text.replace(/[^0-9.,-]/g, '');
  if (!body) { return null; }
  if (/^-?\d{1,3}(\.\d{3})+(,\d+)?$/.test(body)) {
    body = body.replace(/\./g, '').replace(',', '.');      // 1.234.567,89
  } else {
    body = body.replace(/,/g, '');                          // 1,25,000.00
  }
  while ((body.match(/\./g) || []).length > 1) {
    body = body.replace('.', '');
  }
  var value = parseFloat(body);
  if (isNaN(value)) { return null; }
  return negative ? -Math.abs(value) : value;
}

function currencyOf_(symbol) {
  if (!symbol) { return ''; }
  var key = String(symbol).toUpperCase().replace(/\.$/, '');
  var map = { 'RS': 'INR', '₹': 'INR', '$': 'USD', '€': 'EUR',
              '£': 'GBP' };
  return map[key] || key;
}

function confirmedOn_(text) {
  var found = /as on\s+(\d{1,2}\s+[A-Za-z]+\s+\d{4}|\d{1,2}[-\/.]\d{1,2}[-\/.]\d{2,4})/i
                .exec(text);
  return found ? found[1] : '';
}

function stance_(text) {
  var blob = (text || '').toLowerCase();
  var disagree = ['not in agreement', 'do not agree', 'does not agree',
                  'disagree', 'difference', 'differs', 'mismatch',
                  'does not tally', 'discrepancy'];
  for (var i = 0; i < disagree.length; i++) {
    if (blob.indexOf(disagree[i]) >= 0) { return 'not in agreement'; }
  }
  // "as per our books" is deliberately absent: it introduces the party's own
  // figure as often as it signals agreement
  var agree = ['in agreement', 'we agree', 'agreed', 'confirmed', 'tallies'];
  for (var j = 0; j < agree.length; j++) {
    if (blob.indexOf(agree[j]) >= 0) { return 'agreed'; }
  }
  return '';
}

function findReference_(texts) {
  for (var i = 0; i < texts.length; i++) {
    var found = /\bBCG-([0-9A-HJ-NP-Z]{6})\b/i.exec(texts[i] || '');
    if (found) { return ('BCG-' + found[1]).toUpperCase(); }
  }
  return '';
}

function looksLikeBounce_(from, subject, body) {
  var blob = (from + ' ' + subject + ' ' + body).toLowerCase();
  var markers = ['mailer-daemon', 'postmaster',
                 'delivery status notification', 'undeliverable',
                 'address not found', 'delivery has failed',
                 'returned to sender'];
  for (var i = 0; i < markers.length; i++) {
    if (blob.indexOf(markers[i]) >= 0) { return true; }
  }
  return false;
}

/* ========================================================================= */
/*  THE SHEET                                                                */
/* ========================================================================= */

function openSheet_() {
  var id = PROP.getProperty(SHEET_ID_KEY);
  var book = null;
  if (id) {
    try { book = SpreadsheetApp.openById(id); } catch (ignored) { book = null; }
  }
  if (!book) {
    book = SpreadsheetApp.create('Balance confirmation replies');
    PROP.setProperty(SHEET_ID_KEY, book.getId());
  }
  var sheet = book.getSheetByName(CONFIG.SHEET_NAME);
  if (!sheet) {
    sheet = book.getSheets()[0];
    sheet.setName(CONFIG.SHEET_NAME);
  }
  if (sheet.getLastRow() === 0) {
    sheet.getRange(1, 1, 1, COLUMNS.length).setValues([COLUMNS])
         .setFontWeight('bold').setBackground('#5F7232')
         .setFontColor('#FFFFFF');
    sheet.setFrozenRows(1);
  }
  if (!book.getSheetByName(CONFIG.LOG_SHEET_NAME)) {
    var log = book.insertSheet(CONFIG.LOG_SHEET_NAME);
    log.getRange(1, 1, 1, 4)
       .setValues([['when', 'what', 'message id', 'detail']])
       .setFontWeight('bold');
    log.setFrozenRows(1);
  }
  return sheet;
}

function existingIds_(sheet) {
  var known = {};
  var rows = sheet.getLastRow() - 1;
  if (rows < 1) { return known; }
  var ids = sheet.getRange(2, 1, rows, 1).getValues();
  for (var i = 0; i < ids.length; i++) {
    if (ids[i][0]) { known[String(ids[i][0])] = true; }
  }
  return known;
}

function appendRow_(sheet, record) {
  var row = [];
  for (var i = 0; i < COLUMNS.length; i++) {
    var value = record[COLUMNS[i]];
    row.push(value === undefined || value === null ? '' : value);
  }
  sheet.appendRow(row);
}

function log_(what, messageId, detail) {
  try {
    var book = SpreadsheetApp.openById(PROP.getProperty(SHEET_ID_KEY));
    var log = book.getSheetByName(CONFIG.LOG_SHEET_NAME);
    if (log) {
      log.appendRow([new Date(), what, messageId || '', clip_(detail, 500)]);
    }
  } catch (ignored) {}
}

function ensureLabel_(name) {
  return GmailApp.getUserLabelByName(name) || GmailApp.createLabel(name);
}

/* ========================================================================= */
/*  THE FEED THE DESKTOP APPLICATION READS                                   */
/* ========================================================================= */

/**
 * GET returns the replies as JSON, in exactly the shape the desktop
 * application's "Import replies" expects:
 *   { "generated_at": ..., "count": n, "replies": [ { ... }, ... ] }
 *
 * Optional query parameters:
 *   ?since=2026-10-01      only replies received on or after this date
 *   ?status=recorded       only rows with that status
 */
function doGet(event) {
  var parameters = (event && event.parameter) || {};
  // The deployment is readable by anyone holding the link, so the key is what
  // keeps the confirmations private.  Run feedUrl() for the address with it.
  if (parameters.key !== accessKey_()) {
    return ContentService
      .createTextOutput(JSON.stringify(
        { error: 'not authorised',
          detail: 'Run feedUrl() in the Apps Script project and paste the '
                  + 'address it prints into the application.' }))
      .setMimeType(ContentService.MimeType.JSON);
  }
  // ?message=<id> hands over that reply's own PDF and image attachments, so
  // the application can read the signed slip for itself.
  var payload = parameters.message ? attachmentPayload_(parameters.message)
                                   : feedPayload_(parameters);
  return ContentService.createTextOutput(JSON.stringify(payload))
    .setMimeType(ContentService.MimeType.JSON);
}

/**
 * The original files attached to one reply, base64-encoded.  Only a message
 * this script has already recorded in the sheet is served, only PDFs and
 * images, and nothing larger than MAX_FILE_BYTES - the feed is for reading
 * confirmation slips, not for emptying the mailbox.
 */
var MAX_FILE_BYTES = 12 * 1024 * 1024;
var MAX_FILES_PER_REPLY = 6;

function attachmentPayload_(messageId) {
  var id = String(messageId || '');
  if (!existingIds_(openSheet_())[id]) {
    return { error: 'unknown message', files: [] };
  }
  var message;
  try {
    message = GmailApp.getMessageById(id);
  } catch (error) {
    return { error: 'the message could not be opened', files: [] };
  }
  if (!message) {
    return { error: 'the message is no longer in the mailbox', files: [] };
  }
  var files = [], skipped = [];
  var attachments = message.getAttachments({
    includeInlineImages: false, includeAttachments: true
  });
  for (var i = 0; i < attachments.length; i++) {
    var attachment = attachments[i];
    var name = attachment.getName() || ('attachment-' + (i + 1));
    var type = (attachment.getContentType() || '').toLowerCase();
    var readable = type.indexOf('pdf') >= 0 || type.indexOf('image/') === 0 ||
                   /\.(pdf|png|jpe?g|tiff?|bmp|webp)$/i.test(name);
    if (!readable) { skipped.push(name + ' (not a PDF or image)'); continue; }
    if (files.length >= MAX_FILES_PER_REPLY) {
      skipped.push(name + ' (too many attachments)');
      continue;
    }
    var bytes = attachment.getBytes();
    if (bytes.length > MAX_FILE_BYTES) {
      skipped.push(name + ' (larger than 12 MB)');
      continue;
    }
    files.push({ index: i, name: name, type: type, size: bytes.length,
                 data: Utilities.base64Encode(bytes) });
  }
  return { message: id, files: files, skipped: skipped };
}

/**
 * Writes the same JSON to a file in Drive, for a Workspace account whose
 * administrator does not allow a web app to be shared outside the domain.
 * Run it, download the file, then use "Import replies (JSON)" in the
 * application.
 */
function exportFeedToDrive() {
  var payload = feedPayload_({});
  var name = 'balance-confirmation-replies.json';
  var existing = DriveApp.getFilesByName(name);
  var blob = Utilities.newBlob(JSON.stringify(payload, null, 2),
                               'application/json', name);
  var file = existing.hasNext() ? existing.next().setContent(blob.getDataAsString())
                                : DriveApp.createFile(blob);
  Logger.log(payload.count + ' replies written to ' + file.getUrl());
  return file.getUrl();
}

function feedPayload_(parameters) {
  var sheet = openSheet_();
  var rows = sheet.getLastRow() - 1;
  var replies = [];

  if (rows > 0) {
    var values = sheet.getRange(2, 1, rows, COLUMNS.length).getValues();
    for (var i = 0; i < values.length; i++) {
      var record = {};
      for (var c = 0; c < COLUMNS.length; c++) {
        record[COLUMNS[c]] = values[i][c];
      }
      if (parameters.status && record.status !== parameters.status) {
        continue;
      }
      if (parameters.since &&
          String(record.received_at) < String(parameters.since)) {
        continue;
      }
      replies.push({
        id: record.reply_id,
        received_at: record.received_at,
        from_email: record.from_email,
        from_name: record.from_name,
        subject: record.subject,
        reference: record.reference,
        thread_id: record.thread_id,
        in_reply_to: record.in_reply_to,
        body: record.body,
        bounced: record.bounced === true || record.bounced === 'TRUE',
        bridge_status: record.status,
        bridge_note: record.note,
        message_link: record.message_link,
        // the names are published even where no text could be read, so
        // the application knows there is a file to fetch and read itself
        files: record.attachment_names
          ? String(record.attachment_names).split('; ') : [],
        attachments: record.attachment_text
          ? [{ name: record.attachment_names || 'attachment',
               text: record.attachment_text }]
          : []
      });
    }
  }

  return {
    generated_at: new Date().toISOString(),
    last_poll: PROP.getProperty('BCG_LAST_RUN') || '',
    count: replies.length,
    replies: replies
  };
}

/* ========================================================================= */
/*  SMALL HELPERS                                                            */
/* ========================================================================= */

function emailOf_(from) {
  var found = /<([^>]+)>/.exec(from || '');
  return (found ? found[1] : (from || '')).trim().toLowerCase();
}

function nameOf_(from) {
  var text = String(from || '').replace(/<[^>]*>/, '').trim();
  return text.replace(/^"|"$/g, '').trim();
}

function headerOf_(raw, header) {
  var found = new RegExp('^' + header + ':\\s*(.+)$', 'im').exec(raw || '');
  return found ? found[1].trim() : '';
}

function stripHtml_(html) {
  return String(html || '')
    .replace(/<style[\s\S]*?<\/style>/gi, ' ')
    .replace(/<script[\s\S]*?<\/script>/gi, ' ')
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<\/p>/gi, '\n')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/gi, ' ')
    .replace(/&amp;/gi, '&')
    .replace(/&lt;/gi, '<')
    .replace(/&gt;/gi, '>')
    .replace(/[ \t]+/g, ' ');
}

function formatDate_(when) {
  return Utilities.formatDate(when, Session.getScriptTimeZone(), 'yyyy-MM-dd');
}

function clip_(text, limit) {
  var value = String(text === undefined || text === null ? '' : text);
  return value.length > limit ? value.slice(0, limit) + ' [truncated]' : value;
}

/*
 * Independent smoke/contract harness for SME GSTAT AppealKit v0.6.2.
 * Usage: node QA/run_v062_qa.js [path-to-v0.6.2-folder]
 * Exit 0 = no blocking contract failure; exit 1 = release-blocking failure.
 *
 * This harness reads production files but never writes to the application.
 */
'use strict';

const fs = require('fs');
const path = require('path');

const explicitRoot = process.argv[2];
const candidates = [
  explicitRoot,
  'SME_GSTAT_AppealKit_v0.6.2',
  'SME_GSTAT_AppealKit_Professional_v0.6.2'
].filter(Boolean).map(p => path.resolve(p));
const root = candidates.find(p => fs.existsSync(path.join(p, 'index.html')));

if (!root) {
  console.error('BLOCKER: v0.6.2 application folder was not found. Pass its path as the first argument.');
  process.exit(1);
}

const htmlPath = path.join(root, 'index.html');
const jsPath = path.join(root, 'app', 'main.js');
const cssPath = path.join(root, 'app', 'styles.css');
const html = fs.readFileSync(htmlPath, 'utf8');
const js = fs.readFileSync(jsPath, 'utf8');
const css = fs.existsSync(cssPath) ? fs.readFileSync(cssPath, 'utf8') : '';
const corpus = `${html}\n${js}\n${css}`;
const results = [];

function result(level, area, ok, detail) {
  results.push({ level, area, ok, detail });
}
function requireOne(area, level, patterns, detail) {
  const ok = patterns.some(p => p.test(corpus));
  result(level, area, ok, detail);
}
function requireAll(area, level, patterns, detail) {
  const missing = patterns.filter(p => !p.test(corpus));
  result(level, area, missing.length === 0, missing.length ? `${detail}; missing ${missing.length} expected marker(s)` : detail);
}

// Baseline safety and regression contracts.
requireAll('Core generator', 'BLOCKER', [/planVolumes\s*\(/, /buildVolume\s*\(/, /paginateIndexEntries\s*\(/],
  'Volume planner, PDF builder and dynamic index paginator are present');
result('BLOCKER', 'Silent truncation', !/\.slice\(\s*0\s*,\s*(?:2|5)\s*\)/.test(js),
  'No known two-line/five-line silent truncation remains');
requireOne('Dynamic index', 'BLOCKER', [/estimatedRowHeight/, /rowHeight[^\n]*(?:wrap|line)/i, /paginateIndexEntries/],
  'Index rows are measured/paginated dynamically');
requireAll('Multi-volume', 'BLOCKER', [/max(?:imum)?\s*pages|maxPages/i, /volumeNo|volume\s+of/i, /sourcePageStart/],
  'Page limit, volume identity and source-page mapping are represented');

// v0.5 feature contracts. Pattern groups intentionally allow sensible naming.
requireOne('Optional page editor', 'MAJOR', [/edit\s*pages/i, /pageEditor/i, /selectedPage(?:s|Indices)|pageOrder/],
  'An optional page-edit entry point exists');
requireOne('Page selection/order', 'BLOCKER', [/selectedPage(?:s|Indices)/, /pageOrder/, /applyPageEdit/, /sourcePageIndices/],
  'Edited range/order is stored explicitly, not inferred only from thumbnails');
requireOne('More document details', 'MAJOR', [/add\s*more\s*details/i, /optionalColumns/i, /documentDate/i],
  'Optional document details can be opened without crowding the default view');
requireAll('Date guidance', 'MINOR', [/DD-MMM-YYYY/i, /26-Nov-2024/i],
  'Plain date format and a concrete example are visible');
requireOne('Editable rows/columns', 'MAJOR', [/add\s*row/i, /delete\s*row/i, /remove\s*row/i],
  'User can add/delete chronology or detail rows');
requireOne('Editable columns', 'MAJOR', [/add\s*column/i, /hide\s*column/i, /optional\s*column/i],
  'Optional columns are user-controlled');
requireOne('Chronology', 'MAJOR', [/create\s*chronology/i, /chronology/i],
  'Chronology is optional and available');
requireOne('Chronology inclusion', 'BLOCKER', [/includeChronology/, /add\s*chronology\s*to/i, /chronologyPages/],
  'Chronology inclusion is an explicit setting used by pagination');
requireOne('Issue tags', 'MINOR', [/issue\s*tag/i, /issueTags/, /issue-wise/i],
  'Optional issue tagging is available');
requireOne('Reference checker', 'MAJOR', [/check\s*annexures/i, /referenceChecker/i, /annexureReferences/i],
  'Optional appeal-to-annexure reference check is available');
requireOne('Reference safety', 'BLOCKER', [/never\s*overwrite/i, /original[^\n]*(?:unchanged|separate)/i, /suggested\s*(?:change|reference)/i],
  'Reference changes are suggestions and the original is protected');
requireOne('Scrollable preview', 'BLOCKER', [/preview[^\n]*(?:generate|paper\s*book)/i, /previewViewer|previewFrame|pdfViewer/i],
  'Preview exists before final generation');
requireOne('Preview navigation', 'MAJOR', [/go\s*to\s*page/i, /pageNumberInput|previewPage/i, /fit\s*width/i],
  'Preview provides page navigation');
requireOne('Preview stale state', 'BLOCKER', [/preview[^\n]*(?:out\s*of\s*date|stale|refresh)/i, /previewDirty/i],
  'Changes after preview are detected');
requireOne('Non-blocking guidance', 'MINOR', [/please\s*check/i, /continue\s*anyway/i, /warning/i],
  'Warnings guide the user without unnecessary blocking');

// v0.6 compact and optional professional tools.
requireAll('Range selection', 'BLOCKER', [/editorPageRange/, /parseEditorPageRange/, /odd/, /even/],
  'Page-range selection supports common and plain-language patterns');
requireAll('Bulk page actions', 'BLOCKER', [/bulkRotateLeft/, /bulkRemovePages/, /bulkMovePagesStart/, /editorSelectedPages/],
  'Multi-page rotation, inclusion and reordering are wired');
requireAll('Preview jump', 'BLOCKER', [/previewJump/, /showSelectedPreviewJump/, /outputFirstPageIndex\s*\+\s*1/],
  'Annexure jump uses the generated physical-page mapping');
requireAll('Draft mode', 'BLOCKER', [/id="outputMode"/, /DRAFT - FOR REVIEW/, /outputMode\s*===\s*['"]draft['"]/],
  'Draft mark is optional and applied only in draft mode');
requireAll('File-size guide', 'MAJOR', [/maxFileSizeMB/, /getFileSizeWarnings/, /record\.bytes/],
  'Actual generated bytes are checked against an editable guide');
requireAll('Portal upload map', 'MAJOR', [/buildPortalUploadMap/, /Portal_Upload_Map\.csv/, /Size \(MB\)/],
  'Final ZIP contains an Excel-ready volume, page, size and hash map');
requireAll('Compact optional UI', 'MAJOR', [/compact-notice/, /compact-drawer/, /overflow-x:auto/],
  'Top information and extra controls stay compact and optional');
requireAll('Cover sizing', 'BLOCKER', [/coverTextSize/, /First-page text size/, /settings\.coverTextSize/],
  'Existing generated cover has Small, Normal and Large text sizing');
requireAll('Smart justified subject', 'BLOCKER', [/drawJustifiedLines/, /safeToJustify/, /proposedGap/, /2\.25/],
  'Cover subject limits expanded word spacing and falls back to natural alignment');
requireAll('Printed date format', 'BLOCKER', [/formatDateForPrint/, /DD-MMM-YYYY/, /months\s*=\s*\['Jan'/],
  'Printed order date is converted to DD-MMM-YYYY');
requireAll('Document drag order', 'BLOCKER', [/draggable="true"/, /bindDocumentDragAndDrop/, /reorderDocumentByDrop/],
  'Documents can be rearranged by drag and drop while arrow controls remain');
requireAll('Two-stage annexures', 'BLOCKER', [/main_then_annexure/, /mainDocumentCount/, /`A\$\{start \+ i - mainCount\}`/],
  'Automatic numbering supports 1, 2, 3 followed by A1, A2, A3');
requireAll('Full annexure reference', 'BLOCKER', [/extractAnnexureReferences/, /Anx\|Exhibit/, /\\d\{1,4\}/],
  'Reference checker captures complete multi-digit references such as Anx12');
result('BLOCKER', 'No finalisation lock', !/finali[sz]ation\s+lock|lockFinal|lockOutput/i.test(corpus),
  'No finalisation lock was introduced');
requireAll('Optional Prepared by', 'BLOCKER', [/id="showPreparedBy"/, /settings\.showPreparedBy\s*&&\s*settings\.preparedBy/, /Show .Prepared by. on first page/],
  'Prepared by is controlled by an explicit option and has no visible fallback');
result('BLOCKER', 'No Prepared by fallback', !/Prepared by:\s*\$\{settings\.preparedBy\s*\|\|/.test(js),
  'Blank Prepared by cannot restore a hard-coded team name');
requireAll('Long-token wrapping', 'BLOCKER', [/splitOverwideToken/, /Array\.from\(token\)/, /widthOfTextAtSize\(candidate/],
  'Unbroken references and IDs are split at measured glyph boundaries');
requireAll('Dynamic case-title reserve', 'BLOCKER', [/caseLines\s*=.*estimateIndexLines\(settings\.caseTitle/, /caseLines\s*\*\s*10/],
  'Master-index pagination reserves height for the wrapped case title');
result('BLOCKER', 'No silent subject omission', !/settings\.caseTitle\s*&&\s*y\s*>\s*115/.test(js),
  'Crowded cover details cannot silently bypass the subject solely because of y position');

// Ensure the current app is genuinely v0.6.2 when used as a release gate.
const versionText = `${path.basename(root)} ${html}`;
result('BLOCKER', 'Release identity', /v?0\.6\.2/i.test(versionText),
  `Target identifies itself as v0.6.2 (actual folder: ${path.basename(root)})`);

const symbols = {
  errors: results.filter(r => !r.ok && r.level === 'BLOCKER').length,
  major: results.filter(r => !r.ok && r.level === 'MAJOR').length,
  minor: results.filter(r => !r.ok && r.level === 'MINOR').length,
  passed: results.filter(r => r.ok).length
};

console.log(`\nSME GSTAT AppealKit v0.6.2 QA — ${root}`);
console.log('='.repeat(78));
for (const r of results) {
  console.log(`${r.ok ? 'PASS' : 'FAIL'}  ${r.level.padEnd(7)} ${r.area.padEnd(24)} ${r.detail}`);
}
console.log('='.repeat(78));
console.log(`Passed ${symbols.passed}; blockers ${symbols.errors}; major gaps ${symbols.major}; minor gaps ${symbols.minor}.`);
console.log('Manual PDF tests remain mandatory; see QA/QA_PLAN_v062.md.');

process.exit(symbols.errors ? 1 : 0);

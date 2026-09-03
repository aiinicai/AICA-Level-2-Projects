/* AuditLens — capstone presentation deck.
   Every slide carries speaker notes with the exact narration and its timing,
   so the deck can be read straight through while recording. */

const pptxgen = require('pptxgenjs');
const path = require('path');

const S = '/tmp/shots';

// Palette taken from the application itself: ledger viridian, marigold for
// what needs attention, and the paper neutral the workpaper is printed on.
const INK = '14201C';
const GREEN = '1E5A4A';
const GREEN_D = '10352C';
const GREEN_S = 'E3EDE7';
const PAPER = 'F3F4F0';
const WHITE = 'FFFFFF';
const GOLD = 'B77515';
const GOLD_S = 'F7ECD9';
const GOLD_TXT = '8A5710';   // small text: 5.5:1 on paper, where GOLD is only 4.0:1
const MUTED = '55635E';
const FAINT = '7C8983';

const SERIF = 'Cambria';
const SANS = 'Calibri';

const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE';           // 13.3 x 7.5
pres.author = 'CA Rajendra Bagade';
pres.company = 'SARC and Associates';
pres.title = 'AuditLens — AICA Level 2 Capstone';

const W = 13.3, H = 7.5, M = 0.7;

/* ---------- shared pieces ---------- */

// The recurring motif: the statutory authority for what the slide shows,
// set as a pill. It is the one visual element every slide has in common.
function authority(slide, text, x, y, colour = GREEN, maxW = 99) {
  const w = Math.min(maxW, Math.max(0.85, 0.155 * text.length + 0.34));
  slide.addShape(pres.ShapeType.roundRect, {
    x, y, w, h: 0.3, rectRadius: 0.15,
    fill: { color: colour === GOLD ? GOLD_S : GREEN_S },
    line: { color: colour, width: 0.75 },
  });
  slide.addText(text, {
    x, y, w, h: 0.3, isTextBox: true, margin: 0,
    align: 'center', valign: 'middle',
    fontFace: SANS, fontSize: 10, bold: true, color: colour, charSpacing: 0.6,
  });
  return w;
}

function title(slide, text, y = 0.55, colour = INK, size = 34) {
  slide.addText(text, {
    x: M, y, w: W - 2 * M, h: 0.85, isTextBox: true, margin: 0,
    fontFace: SERIF, fontSize: size, bold: true, color: colour,
  });
}

function footer(slide, n) {
  slide.addText('AuditLens  ·  AICA Level 2, Module C  ·  CA. Rajendra Bagade', {
    x: M, y: H - 0.72, w: 8, h: 0.3, isTextBox: true, margin: 0,
    fontFace: SANS, fontSize: 9, color: '5D6A64',
  });
  slide.addText(String(n), {
    x: W - M - 0.6, y: H - 0.72, w: 0.6, h: 0.3, isTextBox: true, margin: 0,
    align: 'right', fontFace: SANS, fontSize: 9, color: '5D6A64',
  });
}

function lightSlide(n) {
  const s = pres.addSlide();
  s.background = { color: PAPER };
  if (n) footer(s, n);
  return s;
}

function darkSlide() {
  const s = pres.addSlide();
  s.background = { color: GREEN_D };
  return s;
}

/* A demo slide: instructions on the left, the screenshot on the right as a
   fallback if the live application misbehaves on the day. */
function demoSlide(n, opts) {
  const s = lightSlide(n);
  const IW = 7.04, IH = 4.4, IX = W - M - IW, IY = 1.78;
  const COL = IX - M - 0.5;                  // the left column, 4.36"

  slide_badge(s);
  title(s, opts.heading, 0.76, INK, 24);
  if (opts.authority) authority(s, opts.authority, M, 1.62, opts.gold ? GOLD : GREEN, COL);

  s.addText(opts.say, {
    x: M, y: opts.authority ? 2.12 : 1.7, w: COL, h: 2.55,
    isTextBox: true, margin: 0, valign: 'top',
    fontFace: SANS, fontSize: 13.5, color: INK, lineSpacing: 20,
  });

  s.addText(opts.clicks.map((c, i) => ({
    text: c, options: { bullet: { indent: 14 }, breakLine: i !== opts.clicks.length - 1 },
  })), {
    x: M, y: 4.9, w: COL, h: 1.7, isTextBox: true, margin: 0, valign: 'top',
    fontFace: SANS, fontSize: 11, color: MUTED, paraSpaceAfter: 6,
  });

  s.addShape(pres.ShapeType.rect, {
    x: IX - 0.045, y: IY - 0.045, w: IW + 0.09, h: IH + 0.09,
    fill: { color: WHITE }, line: { color: 'C9D2CC', width: 1 },
    shadow: { type: 'outer', angle: 90, blur: 10, offset: 2, color: '9AA79F', opacity: 0.3 },
  });
  s.addImage({ path: path.join(S, opts.image), x: IX, y: IY, w: IW, h: IH });
  return s;
}

// The "LIVE" marker, so it is obvious which slides are screen-share moments.
function slide_badge(s) {
  s.addShape(pres.ShapeType.roundRect, {
    x: M, y: 0.34, w: 1.42, h: 0.34, rectRadius: 0.17,
    fill: { color: GOLD }, line: { color: GOLD, width: 1 },
  });
  s.addText('LIVE DEMO', {
    x: M, y: 0.34, w: 1.42, h: 0.34, isTextBox: true, margin: 0,
    align: 'center', valign: 'middle',
    fontFace: SANS, fontSize: 10, bold: true, color: WHITE, charSpacing: 1,
  });
}

/* ======================================================================
   1 · Title
   ====================================================================== */
{
  const s = darkSlide();
  s.addText('AuditLens', {
    x: M, y: 2.05, w: 9, h: 1.3, isTextBox: true, margin: 0,
    fontFace: SERIF, fontSize: 60, bold: true, color: WHITE,
  });
  s.addText('Statutory audit analytical review for Indian companies', {
    x: M, y: 3.3, w: 9.4, h: 0.6, isTextBox: true, margin: 0,
    fontFace: SERIF, fontSize: 21, italic: true, color: '9ECFBC',
  });
  s.addText('A trial balance goes in. The face of the Schedule III financial statements, the eleven mandated ratios, SA 240 journal entry testing, an SA 530 sample and the CARO 2020 checklist come out.', {
    x: M, y: 4.15, w: 8.6, h: 1.1, isTextBox: true, margin: 0,
    fontFace: SANS, fontSize: 14, color: 'C9DDD4', lineSpacing: 22,
  });

  let x = M;
  ['Schedule III', 'SA 240', 'SA 320', 'SA 530', 'CARO 2020'].forEach((t) => {
    const w = Math.max(0.9, 0.155 * t.length + 0.4);
    s.addShape(pres.ShapeType.roundRect, {
      x, y: 5.5, w, h: 0.34, rectRadius: 0.17,
      fill: { color: GREEN_D }, line: { color: '4E9E85', width: 0.75 },
    });
    s.addText(t, {
      x, y: 5.5, w, h: 0.34, isTextBox: true, margin: 0,
      align: 'center', valign: 'middle',
      fontFace: SANS, fontSize: 10.5, bold: true, color: '9ECFBC',
    });
    x += w + 0.16;
  });

  s.addText('CA. Rajendra Bagade   ·   Senior Partner, SARC & Associates', {
    x: M, y: 6.32, w: 9, h: 0.32, isTextBox: true, margin: 0,
    fontFace: SANS, fontSize: 13, bold: true, color: WHITE,
  });
  s.addText('AICA Level 2   ·   Module C Capstone Project   ·   Batch 104', {
    x: M, y: 6.68, w: 9, h: 0.32, isTextBox: true, margin: 0,
    fontFace: SANS, fontSize: 11.5, color: '8FB8A9',
  });

  s.addNotes(
`[0:00 - 0:15]  CAMERA FULL FRAME. No screen share yet.

"Good morning. I am CA Rajendra Bagade, Senior Partner at SARC and Associates.
For my AICA Level 2 capstone I have built AuditLens - a statutory audit
analytical review tool for Indian companies."

DELIVERY: Look at the lens, not the screen. Say the name of the project clearly;
this is the only time the evaluator hears it cold.`);
}

/* ======================================================================
   2 · The problem
   ====================================================================== */
{
  const s = lightSlide(2);
  title(s, 'Every statutory audit begins with the same week');

  s.addText('A trial balance is mapped to Schedule III. Eleven ratios that the Ministry of Corporate Affairs made mandatory in 2021 are computed, and any that moved more than 25 per cent must be explained in the notes. Journal entries are tested for management override. Materiality is determined, a sample selected, and twenty-one CARO clauses worked through.', {
    x: M, y: 1.55, w: 6.5, h: 2.4, isTextBox: true, margin: 0,
    fontFace: SANS, fontSize: 14.5, color: INK, lineSpacing: 23,
  });
  s.addText('It is identical across clients. It consumes the opening week of every engagement. And in most firms it is done by hand, in a spreadsheet that is rebuilt each year.', {
    x: M, y: 3.75, w: 6.5, h: 1.15, isTextBox: true, margin: 0,
    fontFace: SERIF, fontSize: 16, italic: true, color: GREEN, lineSpacing: 24,
  });
  s.addShape(pres.ShapeType.rect, {
    x: M, y: 5.15, w: 6.5, h: 1.32, fill: { color: GREEN_S }, line: { color: GREEN, width: 1 },
  });
  s.addText('For the mid-sized manufacturer used in this demonstration, that means sixty-one ledgers to classify, nine hundred and eighteen journal entries to test, and twenty-one clauses to answer — before any audit evidence is looked at.', {
    x: M + 0.3, y: 5.32, w: 5.9, h: 1.0, isTextBox: true, margin: 0,
    fontFace: SANS, fontSize: 12.5, color: INK, lineSpacing: 18,
  });

  const stats = [
    ['11', 'ratios mandated by\nSchedule III since FY 2021-22'],
    ['21', 'CARO 2020 clauses,\nevery one to be answered'],
    ['6', 'journal entry routines\nrequired under SA 240'],
  ];
  stats.forEach(([big, label], i) => {
    const y = 1.55 + i * 1.72;
    s.addShape(pres.ShapeType.rect, {
      x: 7.7, y, w: 4.9, h: 1.5, fill: { color: WHITE }, line: { color: 'D7DCD5', width: 1 },
    });
    s.addText(big, {
      x: 7.95, y: y + 0.18, w: 1.25, h: 1.1, isTextBox: true, margin: 0,
      fontFace: SERIF, fontSize: 46, bold: true, color: GREEN, valign: 'middle',
    });
    s.addText(label, {
      x: 9.25, y: y + 0.3, w: 3.15, h: 0.95, isTextBox: true, margin: 0,
      fontFace: SANS, fontSize: 12, color: MUTED, valign: 'middle', lineSpacing: 16,
    });
  });

  s.addNotes(
`[0:15 - 1:00]  CAMERA FULL FRAME, or this slide with your camera inset.

"Every statutory audit of an Indian company begins with the same work. The trial
balance is mapped to Schedule III. Eleven ratios that MCA made mandatory in 2021
are computed - and any that moved more than twenty-five per cent has to be
explained in the notes. Journal entries are tested for management override under
SA 240. Materiality is set, a sample is selected, and twenty-one CARO clauses are
worked through.

It is identical across clients. It takes the opening week of every engagement.
And in most firms it is still done by hand."

DELIVERY: This is the slide that earns the evaluator's attention, because they
have done this work themselves. Slow down. Let "the opening week of every
engagement" land.`);
}

/* ======================================================================
   3 · What it does
   ====================================================================== */
{
  const s = lightSlide(3);
  title(s, 'What the application does');
  s.addText('Eight modules. Seven of them answer to a provision.', {
    x: M, y: 1.42, w: 8, h: 0.35, isTextBox: true, margin: 0,
    fontFace: SANS, fontSize: 13.5, color: MUTED,
  });

  const items = [
    ['Ingest', 'Trial balance and general ledger in whatever shape the client exported them - aliased headers, Indian number formats, bracketed negatives.', ''],
    ['Map', 'Every ledger to a Division I presentation head, on the account code first and the ledger name second.', 'Schedule III'],
    ['Present', 'The Balance Sheet and Statement of Profit and Loss, with an honest reconciliation when they do not tie.', 'Schedule III'],
    ['Measure', 'The eleven mandated ratios, with every movement beyond 25 per cent flagged for the notes.', 'G.S.R. 207(E)'],
    ['Test', 'Six journal entry routines plus the Benford first-digit test.', 'SA 240'],
    ['Sample', 'Materiality from the auditor’s benchmark, and a monetary unit sample with the seed recorded.', 'SA 320 / SA 530'],
    ['Report', 'Applicability and all twenty-one clauses, pre-populated from what the books evidence.', 'CARO 2020'],
    ['Draft', 'The analytical memorandum, the ratio variance notes, and the enquiry letter to management.', ''],
  ];

  items.forEach(([head, body, auth], i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = M + col * 6.15, y = 1.92 + row * 1.27;
    s.addShape(pres.ShapeType.ellipse, {
      x, y: y + 0.06, w: 0.42, h: 0.42,
      fill: { color: GREEN }, line: { color: GREEN, width: 1 },
    });
    s.addText(String(i + 1), {
      x, y: y + 0.06, w: 0.42, h: 0.42, isTextBox: true, margin: 0,
      align: 'center', valign: 'middle', fontFace: SANS, fontSize: 12, bold: true, color: WHITE,
    });
    s.addText(head, {
      x: x + 0.58, y, w: 1.15, h: 0.3, isTextBox: true, margin: 0, valign: 'top',
      fontFace: SANS, fontSize: 14, bold: true, color: INK,
    });
    if (auth) {
      s.addText(auth, {
        x: x + 1.78, y: y + 0.04, w: 2.3, h: 0.26, isTextBox: true, margin: 0, valign: 'top',
        fontFace: SANS, fontSize: 9.5, bold: true, color: GOLD_TXT, charSpacing: 0.4,
      });
    }
    s.addText(body, {
      x: x + 0.58, y: y + 0.32, w: 5.15, h: 0.85, isTextBox: true, margin: 0, valign: 'top',
      fontFace: SANS, fontSize: 11, color: MUTED, lineSpacing: 15,
    });
  });

  s.addNotes(
`[1:00 - 1:40]  SLIDE ON SCREEN, camera inset.

"The application does seven things, and each one answers to a provision.

It reads the trial balance and the general ledger in whatever shape the client's
system exported them. It maps every ledger to a Schedule III Division I head. It
builds the face of the statements. It computes the eleven ratios. It runs six
journal entry routines under SA 240. It sets materiality and selects a sample
under SA 320 and SA 530. And it works through all twenty-one CARO clauses."

DELIVERY: Do not read all seven descriptions - just the module names and their
authority. The slide carries the detail; you carry the pace. Forty seconds.`);
}

/* ======================================================================
   4 · The governing rule
   ====================================================================== */
{
  const s = darkSlide();
  s.addText('The design decision that matters', {
    x: M, y: 0.85, w: 10, h: 0.5, isTextBox: true, margin: 0,
    fontFace: SANS, fontSize: 14, bold: true, color: '8FB8A9', charSpacing: 0.5,
  });
  s.addText('The engine computes.\nThe model writes prose.\nNothing else.', {
    x: M, y: 1.65, w: 11.5, h: 2.5, isTextBox: true, margin: 0,
    fontFace: SERIF, fontSize: 44, bold: true, color: WHITE, lineSpacing: 54,
  });
  s.addText('Every figure that reaches a workpaper is produced by a pure Python function with a unit test. The language model is asked for two things only — an explanation in words, and correspondence.', {
    x: M, y: 4.35, w: 6.1, h: 1.4, isTextBox: true, margin: 0,
    fontFace: SANS, fontSize: 14, color: 'C9DDD4', lineSpacing: 22,
  });

  ['It never computes a figure.',
   'It never classifies a ledger that reaches the statements.',
   'It never concludes on a CARO clause.'].forEach((t, i) => {
    const y = 4.35 + i * 0.62;
    s.addShape(pres.ShapeType.ellipse, {
      x: 7.35, y: y + 0.07, w: 0.26, h: 0.26,
      fill: { color: GOLD }, line: { color: GOLD, width: 1 },
    });
    s.addText(t, {
      x: 7.78, y, w: 4.9, h: 0.42, isTextBox: true, margin: 0,
      fontFace: SANS, fontSize: 13, color: WHITE, valign: 'middle',
    });
  });
  s.addText('A Chartered Accountant signs the report. Every number in it has to be traceable to a calculation that can be re-performed.', {
    x: M, y: 6.4, w: 11.5, h: 0.6, isTextBox: true, margin: 0,
    fontFace: SERIF, fontSize: 15, italic: true, color: '9ECFBC',
  });

  s.addNotes(
`[1:40 - 2:10]  CAMERA FULL FRAME for the rule, then back to the slide.

"Before I show you the application, one design decision, because everything else
follows from it.

THE ENGINE COMPUTES. THE MODEL WRITES PROSE. NOTHING ELSE.

Every figure that reaches a workpaper comes from a Python function with a unit
test. The language model is asked for exactly two things - to explain a movement
in words, and to draft correspondence. It never computes a figure. It never
classifies a ledger that reaches the face of the statements. And it never
concludes on a CARO clause.

Why? Because a Chartered Accountant signs the report. Every number in it has to
be traceable to a calculation that can be re-performed."

DELIVERY: This is the most important thirty seconds in the video. Say the rule
slowly, in three beats, and pause after it. An evaluator who is a practising CA
will be testing you on exactly this point.`);
}

/* ======================================================================
   5 · Architecture
   ====================================================================== */
{
  const s = lightSlide(5);
  title(s, 'How it is put together');
  s.addText('A thin interface, a deterministic core, and a model layer that only ever reads and writes.', {
    x: M, y: 1.42, w: 10, h: 0.35, isTextBox: true, margin: 0,
    fontFace: SANS, fontSize: 13.5, color: MUTED,
  });

  const stages = [
    ['Ingest', 'Trial balance,\ncomparative,\ngeneral ledger', 'PYTHON', GREEN],
    ['Map', 'Account code first,\nledger name second,\nUNMAPPED otherwise', 'PYTHON', GREEN],
    ['Compute', 'Statements, ratios,\nSA 240 routines,\nmateriality, sample', 'PYTHON', GREEN],
    ['Draft', 'Memorandum,\nratio notes,\nenquiry letter', 'MODEL LAYER', GOLD],
    ['Deliver', 'PWA dashboard,\n11-sheet workpaper,\nn8n automation', 'PYTHON', GREEN],
  ];
  const bw = 2.188, gap = 0.24;
  stages.forEach(([head, body, day, colour], i) => {
    const x = M + i * (bw + gap);
    s.addShape(pres.ShapeType.rect, {
      x, y: 2.05, w: bw, h: 2.02,
      fill: { color: colour === GOLD ? GOLD_S : WHITE },
      line: { color: colour === GOLD ? GOLD : 'D7DCD5', width: colour === GOLD ? 1.5 : 1 },
    });
    s.addText(day, {
      x: x + 0.22, y: 2.22, w: bw - 0.44, h: 0.28, isTextBox: true, margin: 0,
      fontFace: SANS, fontSize: 9.5, bold: true,
      color: colour === GOLD ? GOLD_TXT : colour, charSpacing: 0.8,
    });
    s.addText(head, {
      x: x + 0.22, y: 2.55, w: bw - 0.44, h: 0.4, isTextBox: true, margin: 0,
      fontFace: SERIF, fontSize: 18, bold: true, color: INK,
    });
    s.addText(body, {
      x: x + 0.22, y: 2.98, w: bw - 0.44, h: 1.3, isTextBox: true, margin: 0, valign: 'top',
      fontFace: SANS, fontSize: 11, color: MUTED, lineSpacing: 15,
    });
    if (i < stages.length - 1) {
      s.addText('›', {
        x: x + bw, y: 2.81, w: gap, h: 0.5, isTextBox: true, margin: 0,
        align: 'center', fontFace: SANS, fontSize: 22, bold: true, color: FAINT,
      });
    }
  });

  s.addShape(pres.ShapeType.rect, {
    x: M, y: 4.55, w: W - 2 * M, h: 1.35,
    fill: { color: GREEN_S }, line: { color: GREEN, width: 1 },
  });
  s.addText('Only the fourth stage touches the language model — and it receives figures the engine has already computed. Remove the model entirely and the analytical review is unchanged; only the prose falls back to a template.', {
    x: M + 0.3, y: 4.65, w: W - 2 * M - 0.6, h: 1.15, isTextBox: true, margin: 0,
    fontFace: SANS, fontSize: 13, color: INK, valign: 'middle', lineSpacing: 20,
  });

  s.addNotes(
`[2:10 - 2:40]  SLIDE ON SCREEN.

"Here is the pipeline. Ingest, map, compute, draft, deliver.

Notice that only the fourth stage - drafting - touches the language model, and by
the time it does, every figure has already been computed by Python. You could
remove the model entirely and the analytical review would be identical; only the
prose would fall back to a template. That is not an accident, it is the whole
design."

DELIVERY: Point at the gold box as you say "only the fourth stage". Thirty seconds -
do not linger, the demo is where the marks are.`);
}

/* ======================================================================
   6-12 · Live demo
   ====================================================================== */

demoSlide(6, {
  heading: 'Ingest, and the ledgers it refuses to guess',
  authority: 'Schedule III, Division I',
  image: '05_mapping.png',
  say: 'Fifty-nine of sixty-one ledgers were mapped on the account code, and the engine says nothing about them. Two are in this queue: one it mapped on the ledger name, and one it could not map at all.\n\nIt returned UNMAPPED rather than guessing, because a mis-mapped ledger appears on the face of the financial statements.',
  clicks: [
    'Click "Use the sample client" - say the client is fictitious and no client data is used anywhere',
    'Let the summary tiles land, then open the Mapping queue tab',
    'Point at the suspense account row and the word UNMAPPED',
  ],
}).addNotes(
`[2:40 - 3:20]  SCREEN SHARE BEGINS. Camera stays in the corner.

"Let me run it. I click Use the sample client - and I should say clearly that this
is a fictitious company. No client data is used anywhere in this project.

[wait for the review to run]

Here is the mapping queue. Fifty-nine of the sixty-one ledgers were mapped on the
account code, and the engine says nothing about those. Two are here. One was
mapped on its ledger name, so it is flagged for me to confirm. And this one - a
suspense account - it could not map at all, so it returned UNMAPPED.

It did not guess. A mis-mapped ledger ends up on the face of the financial
statements, so a guess there is worse than an admission."

DELIVERY: Move the cursor deliberately. Do not scroll while talking.`);

demoSlide(7, {
  heading: 'A balance sheet that does not tie — and says so',
  authority: 'The strongest 30 seconds in the demo',
  gold: true,
  image: '04_statements.png',
  say: 'The balance sheet is out by four lakh twenty thousand rupees — exactly the amount sitting in the suspense account the engine refused to classify.\n\nA lesser tool would force that difference to a rounding line and produce statements that tie and are wrong.',
  clicks: [
    'Open the Statements tab',
    'Point at the reconciliation banner and read the figure out loud',
    'Say what a tool that forced the difference would have produced',
  ],
}).addNotes(
`[3:20 - 3:55]  SCREEN SHARE.

"Now look at this banner. The balance sheet does not tie. It is out by four lakh
twenty thousand rupees - and that is exactly the amount sitting in the suspense
account the engine just refused to classify.

I want to be clear about why this matters. A tool that wanted to look finished
would push that difference into a rounding line, and hand me a balance sheet that
ties and is wrong. This one tells me it does not tie, tells me precisely why, and
tells me what to do about it - clear the unmapped queue and the statements will
tie."

DELIVERY: This is the single best moment in the demo. Slow right down. If the
evaluator remembers one thing, make it this.`);

demoSlide(8, {
  heading: 'The eleven ratios Schedule III requires',
  authority: 'G.S.R. 207(E) dated 24 March 2021',
  image: '03_ratios.png',
  say: 'Inserted by MCA notification G.S.R. 207(E) dated 24 March 2021, applicable from FY 2021-22. Four ratios moved beyond twenty-five per cent and must be explained in the notes.\n\nThe movements are shown in neutral colour. Whether a fall in the debt-equity ratio is favourable is the auditor’s judgement, not a colour the tool assigns.',
  clicks: [
    'Open the Ratios tab',
    'Read the citation off the panel heading',
    'Open one flagged card and read its numerator and denominator aloud',
    'Point out that the movement is not coloured green or red',
  ],
}).addNotes(
`[3:55 - 4:40]  SCREEN SHARE.

"These are the eleven ratios, inserted into Schedule III by MCA notification
G.S.R. 207(E) dated 24 March 2021, and applicable from financial year 2021-22.

Four of them moved by more than twenty-five per cent, so under Schedule III each
one has to be explained in the notes. The tool flags them and shows me the
numerator and denominator it used - here, profit after tax over average
shareholders' equity - so I can re-perform it.

One deliberate choice: the movements are not coloured green or red. Whether a fall
in the debt-equity ratio is a good thing is my judgement as the auditor, not a
colour the tool assigns."

DELIVERY: Say the notification number precisely - it is the kind of detail a CA
evaluator checks.`);

demoSlide(9, {
  heading: 'Journal entry testing under SA 240',
  authority: 'SA 240',
  image: '06_je.png',
  say: 'SA 240 requires the auditor to test journal entries, because management override of controls is a risk in every entity. Six routines, and every flag rate is under one per cent — so the output is a work programme, not a haystack.\n\nThe population conforms to Benford, which is what makes the other routines’ findings worth looking at.',
  clicks: [
    'Open the Journal entries tab',
    'Walk the six routines and their flag rates',
    'Point at the Benford chart and read the conclusion',
    'Say: a flag is a selection for examination, not a finding',
  ],
}).addNotes(
`[4:40 - 5:25]  SCREEN SHARE.

"SA 240 requires me to test the appropriateness of journal entries, because
management override of controls is a risk in every entity.

Six routines: round sums, non-working days, material entries at the period end,
back-dated entries, seldom-used account combinations, and infrequent posting
users. Look at the flag rates - every one is under one per cent. That matters. A
routine that flags thirty per cent of the population has given me a haystack, not
a work programme.

And here is the Benford first-digit test. The population conforms - which is
precisely what makes the departures the other six routines found worth looking at.

One sentence I want on the record: a flag is a selection for examination, not a
finding."

DELIVERY: End on that last sentence and pause. It shows professional judgement,
which is what separates this from a script that prints numbers.`);

demoSlide(10, {
  heading: 'When the tool says sampling is the wrong answer',
  authority: 'SA 530 / SA 520',
  gold: true,
  image: '07_sample.png',
  say: 'The sample is arithmetically correct and professionally useless: it covers fifty-one per cent of the population.\n\nSo the tool says so, and points to controls reliance, substantive analytical procedures under SA 520, or stratification instead. The seed and random start are recorded so a reviewer can re-perform the selection exactly.',
  clicks: [
    'Open the Sample tab',
    'Read the warning banner aloud',
    'Point at the seed and the random start',
  ],
}).addNotes(
`[5:25 - 5:50]  SCREEN SHARE.

"Monetary unit sampling under SA 530. The seed and the random start are recorded,
so a reviewer can re-perform this exact selection.

But look at the warning. The computed sample covers fifty-one per cent of the
population. That is arithmetically correct and professionally useless - nobody is
vouching four hundred and sixty-six items. So the tool says so, and points me to
testing controls, or substantive analytical procedures under SA 520, or
stratifying the population.

A tool that handed me that programme without saying this would be worse than no
tool at all."

DELIVERY: Twenty-five seconds. This is a judgement moment, not a feature - land it
and move on.`);

demoSlide(11, {
  heading: 'CARO 2020 — twenty-one clauses, none of them answered',
  authority: 'CARO 2020, paragraph 3',
  image: '08_caro.png',
  say: 'Applicability is tested under paragraph 1(2) first. Then all twenty-one clauses, eight of them pre-populated with what the books actually evidence.\n\nNot one is concluded. Every clause comes back with an empty auditor response, because concluding on a CARO clause is not the tool’s to do.',
  clicks: [
    'Open the CARO 2020 tab',
    'Read the applicability line at the top',
    'Scroll to clause (xvii) or (xix) and show the evidence it pulled from the books',
  ],
}).addNotes(
`[5:50 - 6:10]  SCREEN SHARE.

"CARO 2020. It first tests whether the Order applies at all under paragraph 1(2) -
here it does. Then all twenty-one clauses of paragraph 3, with eight of them
pre-populated from what the books evidence. Clause seventeen knows whether there
was a cash loss. Clause nineteen knows the current ratio.

But look at what it does not do. Not one clause is answered. Every one comes back
with an empty auditor response, because concluding on a CARO clause is my job, not
the tool's."

DELIVERY: Twenty seconds. Keep it brisk - the point is the restraint, not the list.`);

demoSlide(12, {
  heading: 'What the model is actually allowed to do',
  authority: 'Day 1 · Day 2',
  image: '09_drafts.png',
  say: 'The memorandum, the ratio variance notes and the enquiry letter to management — drafted from versioned system instructions held as files in the repository.\n\nNotice the bracketed instruction: management to state the commercial reason. The prompt forbids inventing one.',
  clicks: [
    'Open Drafts and click Generate',
    'Read one ratio note and point at the bracketed instruction',
    'Switch to the repo and open prompts/ — show the four files and a changelog',
  ],
}).addNotes(
`[6:10 - 6:45]  SCREEN SHARE.

"Now the drafting. The memorandum, the notes explaining each ratio movement, and
the enquiry letter to management under SA 240.

Read this ratio note carefully. It states the movement, it says which of the
numerator and denominator drove it - and then it stops, with a bracketed
instruction: management to state the commercial reason. The prompt explicitly
forbids inventing a reason like 'improved operational efficiency'.

[switch to the repository, open prompts/]

These are the four system instructions, versioned, with changelogs. This one
records why version 1.3 banned the words fraud, irregularity, manipulation and
override from the enquiry letter - because an earlier draft called a round-sum
entry 'irregular', and a selection is not an allegation."

DELIVERY: The changelog is your Day 1 evidence. Show it - most participants will
not have versioned their prompts at all.`);

demoSlide(13, {
  heading: 'Automation, deployment, and how it is verified',
  authority: 'Day 4 · Day 5',
  image: '01_setup_crop.png',
  say: 'Two n8n workflows: a quarterly analytical review that emails the engagement partner only when there is something to see, and a journal entry alert.\n\nThe application installs as a progressive web app. And the whole engine is covered by one hundred and twenty-four tests.',
  clicks: [
    'Show the n8n canvas and an execution log',
    'Install the PWA on a phone or from the browser address bar',
    'Run python -m pytest in a second terminal window; let the 124 tests pass on camera',
  ],
}).addNotes(
`[6:45 - 7:10]  SCREEN SHARE.

"Two n8n workflows. The first runs the analytical review every quarter and emails
the engagement partner - but only when there is actually something to see. The
second watches for a new general ledger and alerts the audit manager to the
entries graded elevated.

The application installs as a progressive web app - here it is on my phone.

And finally, the part I would ask you to weigh most heavily. [run pytest] One
hundred and twenty-four tests. Every one of the eleven ratios is checked against a
figure I computed by hand, so a change that would alter a disclosed ratio fails
here, in the test suite, rather than in a client's financial statements."

DELIVERY: Have the terminal already open in a second window. The tests run in about
three seconds - let the green line appear on camera.`);

/* ======================================================================
   14 · Syllabus mapping
   ====================================================================== */
{
  const s = lightSlide(14);
  title(s, 'Where each day of Level 2 appears');

  const rows = [
    ['Day 1', 'Agent architecture, advanced prompting', 'Four versioned system instructions with changelogs', 'prompts/'],
    ['Day 2', 'Gemini API, system instructions, model parameters, local models', 'The drafting layer, with an LM Studio path for confidential engagements', 'narrate.py'],
    ['Day 3', 'Python fundamentals and core libraries', 'The whole engine — thirteen modules', 'src/auditlens/'],
    ['Day 4', 'Full-stack build, PWA, deployment', 'Installable dashboard and workpaper download', 'web/'],
    ['Day 5', 'n8n workflow automation', 'Quarterly review and journal entry alert', 'automation/'],
  ];

  s.addTable(
    [[
      { text: 'Day', options: { bold: true, color: WHITE, fill: { color: GREEN } } },
      { text: 'Learning', options: { bold: true, color: WHITE, fill: { color: GREEN } } },
      { text: 'Where it is used', options: { bold: true, color: WHITE, fill: { color: GREEN } } },
      { text: 'Evidence in the repository', options: { bold: true, color: WHITE, fill: { color: GREEN } } },
    ]].concat(rows.map((r, i) => r.map((c, j) => ({
      text: c,
      options: {
        color: j === 0 ? GREEN : (j === 3 ? GOLD_TXT : INK),
        bold: j === 0,
        fill: { color: i % 2 ? PAPER : WHITE },
        fontFace: j === 3 ? 'Consolas' : SANS,
      },
    })))),
    {
      x: M, y: 1.6, w: W - 2 * M,
      colW: [1.0, 3.9, 4.5, 2.5],
      rowH: 0.62,
      fontFace: SANS, fontSize: 11.5,
      border: { type: 'solid', color: 'D7DCD5', pt: 1 },
      valign: 'middle',
      autoPage: false,
    },
  );

  s.addText('This table is in the README as well, so the evaluator can find each day’s evidence without hunting for it.', {
    x: M, y: 5.5, w: 11.5, h: 0.5, isTextBox: true, margin: 0,
    fontFace: SERIF, fontSize: 15, italic: true, color: GREEN,
  });

  s.addNotes(
`[7:10 - 7:30]  SLIDE ON SCREEN.

"To tie it back to the course. Day one gave me agent architecture and prompting -
that is the prompts folder. Day two, the Gemini API and system instructions - the
drafting layer. Day three, Python - the engine. Day four, the full-stack build and
the PWA. Day five, n8n.

This table is in the README too, so you can find the evidence for each day without
hunting for it."

DELIVERY: Twenty seconds. Do not read the whole table - name the five days and let
the slide do the rest.`);
}

/* ======================================================================
   15 · Limitations
   ====================================================================== */
{
  const s = lightSlide(15);
  title(s, 'What it does not do');
  s.addText('Stated here rather than left for a reviewer to find.', {
    x: M, y: 1.42, w: 8, h: 0.35, isTextBox: true, margin: 0,
    fontFace: SANS, fontSize: 13.5, color: MUTED,
  });

  const limits = [
    ['Division I only', 'Ind AS (Division II) and NBFC presentation (Division III) are not implemented. The head list would be replaced; the engine around it would not.'],
    ['It forms no opinion', 'And concludes on no CARO clause.'],
    ['It does not set materiality', 'It computes it from the benchmark and rate the auditor chooses, and flags a rate outside the customary range.'],
    ['It asserts no reason', 'For any movement in a ratio. The draft carries a bracketed instruction to management instead.'],
    ['It verifies nothing', 'Existence, completeness and valuation remain the auditor’s to establish. It analyses what the books say.'],
    ['No client data', 'Anywhere — not in the repository, the samples or this video. Everything is built on a synthetic company.'],
  ];
  limits.forEach(([head, body], i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = M + col * 6.15, y = 1.95 + row * 1.42;
    s.addShape(pres.ShapeType.rect, {
      x, y, w: 5.75, h: 1.22, fill: { color: WHITE }, line: { color: 'D7DCD5', width: 1 },
    });
    s.addText(head, {
      x: x + 0.28, y: y + 0.14, w: 5.2, h: 0.32, isTextBox: true, margin: 0,
      fontFace: SANS, fontSize: 13, bold: true, color: GREEN,
    });
    s.addText(body, {
      x: x + 0.28, y: y + 0.46, w: 5.2, h: 0.68, isTextBox: true, margin: 0,
      fontFace: SANS, fontSize: 10.5, color: MUTED, lineSpacing: 14,
    });
  });

  s.addNotes(
`[7:30 - 7:50]  CAMERA FULL FRAME, or slide with camera inset.

"Finally, what it does not do - and I would rather say this than have you find it.

Schedule III Division I only; there is no Ind AS. It forms no opinion and concludes
on no CARO clause. It does not determine materiality, it computes it from the
benchmark I choose. It asserts no commercial reason for any ratio movement. And it
verifies nothing - it analyses what the books say; the audit evidence is still mine
to obtain.

And no client data is used anywhere - not in the repository, not in the samples,
not in this video."

DELIVERY: Naming your own limitations unprompted reads as confidence, not weakness.
Say it plainly and do not hedge.`);
}

/* ======================================================================
   16 · Close
   ====================================================================== */
{
  const s = darkSlide();
  s.addText('Thank you', {
    x: M, y: 2.2, w: 9, h: 1, isTextBox: true, margin: 0,
    fontFace: SERIF, fontSize: 48, bold: true, color: WHITE,
  });
  s.addText('AuditLens turns the opening week of a statutory audit into a review the engagement team can start from — without ever putting a figure on the file that a Chartered Accountant cannot re-perform.', {
    x: M, y: 3.4, w: 8.9, h: 1.4, isTextBox: true, margin: 0,
    fontFace: SANS, fontSize: 15.5, color: 'C9DDD4', lineSpacing: 25,
  });

  const facts = [['124', 'tests'], ['11', 'sheets in the workpaper'], ['5', 'days of Level 2 used']];
  facts.forEach(([big, label], i) => {
    const x = M + i * 3.6;
    s.addText(big, {
      x, y: 5.05, w: 1.5, h: 0.7, isTextBox: true, margin: 0,
      fontFace: SERIF, fontSize: 36, bold: true, color: GOLD,
    });
    s.addText(label, {
      x, y: 5.72, w: 3.3, h: 0.4, isTextBox: true, margin: 0,
      fontFace: SANS, fontSize: 12, color: '8FB8A9',
    });
  });

  s.addText('CA. Rajendra Bagade  ·  Senior Partner, SARC & Associates  ·  AICA Level 2, Module C, Batch 104', {
    x: M, y: 6.65, w: 11.5, h: 0.35, isTextBox: true, margin: 0,
    fontFace: SANS, fontSize: 11.5, color: '8FB8A9',
  });

  s.addNotes(
`[7:50 - 8:00]  CAMERA FULL FRAME. Screen share off.

"AuditLens turns the opening week of a statutory audit into a review the engagement
team can start from - without ever putting a figure on the file that a Chartered
Accountant cannot re-perform.

Thank you."

DELIVERY: Stop talking. Hold the frame for two seconds before you stop the
recording, so the cut is clean.

--- BEFORE YOU UPLOAD ---
1. Camera visible throughout? The brief requires face AND technical content.
2. Upload UNLISTED to YouTube, or to Drive set to "Anyone with the link - Viewer".
3. Open the link in an incognito window and confirm it plays.
4. Submit the link through the Google Form.`);
}

pres.writeFile({ fileName: '/home/claude/work/deck/AuditLens_capstone_deck.pptx' })
  .then((f) => console.log('written:', f));

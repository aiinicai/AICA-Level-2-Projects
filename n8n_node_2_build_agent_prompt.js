/**
 * n8n Node: "Build Agent Prompt" (Code node)
 * Workflow: FTA HSN Query
 *
 * Purpose: Assembles the full prompt sent to the LLM agent, combining:
 *   1. An exact HS-code rate lookup from the structured hs_rates_india_uk table
 *   2. A full-text grep of every uploaded document for lines mentioning the
 *      exact HSN code (catches codes buried deep in large tariff tables that
 *      would otherwise be truncated by the character budget)
 *   3. A character-budget-limited excerpt of all matching FTA source documents
 *
 * Runs after: Get HS Rate -> Get Documents For FTA
 * Feeds into: FTA Answer Agent (the LangChain AI Agent node)
 */

const items = $input.all();
const validRows = items.filter(i => i.json && i.json.extracted_text);
const form = $('HSN Query Form').first().json;
const hsnCode = (form['HSN Code (4, 6 or 8 digit)'] || '').trim();

// --- 1. Exact HS-code lookup from the hs_rates_india_uk structured table ---
let hsRateBlock = '';
try {
  const hsRateRows = $('Get HS Rate').all().filter(r => r.json && r.json.hs_code);
  if (hsRateRows.length > 0) {
    const seen = new Set();
    const lines = [];
    for (const r of hsRateRows) {
      const j = r.json;
      const key = `${j.hs_code}|${j.bcd_rate}|${j.aidc_rate}|${j.health_cess_rate}`;
      if (seen.has(key)) continue;
      seen.add(key);
      lines.push(`HS ${j.hs_code}: ${j.description} -- BCD ${j.bcd_rate}%, AIDC ${j.aidc_rate}%, Health Cess ${j.health_cess_rate}% (Source: ${j.notification_no}, FTA: ${j.fta_code})`);
    }
    if (lines.length > 0) {
      hsRateBlock = `\n\nEXACT HS-CODE RATE LOOKUP (structured table match -- authoritative if present):\n${lines.join('\n')}`;
    }
  }
} catch (e) { /* Get HS Rate not available this run */ }

// --- 2. Grep the FULL text of every uploaded document for lines mentioning
//        the exact HSN code, regardless of the character budget below. This
//        catches codes buried deep in large tables (e.g. a full ~11,000-line
//        tariff schedule) that would otherwise be truncated away. ---
let grepBlock = '';
if (hsnCode) {
  const escaped = hsnCode.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const lineRe = new RegExp(`^.*\\b${escaped}\\b.*$`, 'gm');
  const grepHits = [];
  for (const r of validRows) {
    const text = r.json.extracted_text || '';
    const matches = text.match(lineRe);
    if (matches && matches.length > 0) {
      const uniqueMatches = [...new Set(matches)].slice(0, 5);
      grepHits.push(`From ${r.json.doc_type || 'Notification'} ${r.json.notification_no || ''} dated ${r.json.notification_date || 'unknown'}:\n${uniqueMatches.map(m => '  ' + m.trim()).join('\n')}`);
    }
  }
  if (grepHits.length > 0) {
    grepBlock = `\n\nDIRECT TEXT MATCHES FOR HSN ${hsnCode} FOUND IN FULL UPLOADED DOCUMENTS (searched independent of the size-limited excerpt below -- these are exact line matches from the complete source text and should be treated as authoritative):\n${grepHits.join('\n\n')}`;
  }
}

// --- 3. General document excerpt, budget-limited for prompt size ---
// Gemini free-tier caps at 250,000 tokens/minute and ~20 requests/day.
const CHAR_BUDGET = 60000;

let contextBlob;
if (validRows.length === 0) {
  contextBlob = 'NO SOURCE DOCUMENTS ARE ON FILE YET for this FTA in this register. Do not fabricate rates, thresholds, or rules. State plainly that no notification has been uploaded/processed yet for this FTA, and that the answer cannot be sourced from this register until one is added via the Intake form.';
} else {
  const sorted = [...validRows].sort((a, b) => {
    const da = a.json.notification_date || '0000-00-00';
    const db = b.json.notification_date || '0000-00-00';
    return db.localeCompare(da);
  });

  let used = 0;
  const blocks = sorted.map(r => {
    const scope = r.json.change_scope || 'not specified';
    const supersedes = r.json.supersedes_notification_no ? ` -- AMENDS/SUPERSEDES: ${r.json.supersedes_notification_no}` : '';
    const flag = scope === 'Full table / rate replacement' ? ' *** THIS FULLY REPLACES THE RATE TABLE OF THE NOTIFICATION IT AMENDS -- PREFER THIS OVER THAT ONE FOR RATE/EXEMPTION QUESTIONS *** ' : '';
    const header = `--- Source: ${r.json.doc_type || 'Notification'} ${r.json.notification_no || ''} dated ${r.json.notification_date || 'unknown date'} | change scope: ${scope}${supersedes}${flag} | status: ${r.json.status}, human-verified: ${r.json.verified_by_human} ---`;

    const fullText = r.json.extracted_text || '';
    if (used + fullText.length <= CHAR_BUDGET) {
      used += fullText.length;
      return `${header}\n${fullText}`;
    }

    const note = r.json.note || '(no summary note on file -- but see DIRECT TEXT MATCHES section above if this document contains the requested HSN code)';
    return `${header}\n[FULL TEXT OMITTED FOR SIZE -- SUMMARY ONLY: ${note}]`;
  });

  contextBlob = blocks.join('\n\n');
}

const prompt = `QUERY DETAILS\nFTA: ${form['FTA / Trade Agreement']}\nImporting country: ${form['Importing Country']}\nExporting / originating country: ${form['Exporting / Originating Country']}\nDestination country: ${form['Destination Country'] || 'not specified'}\nHSN code: ${form['HSN Code (4, 6 or 8 digit)']}\nQuestion type: ${form['Question Type']}\nAdditional details: ${form['Additional details / specific question'] || 'none'}${hsRateBlock}${grepBlock}\n\nSOURCE DOCUMENTS (multiple documents for the same FTA may amend/supersede one another -- check each source's 'change scope' and 'AMENDS/SUPERSEDES' metadata before deciding which rate is current; a later document flagged as a full table replacement overrides the table in the notification it names, but a narrow amendment (e.g. adding one country to a list) does NOT override rates elsewhere)\n${contextBlob}`;

return [{ json: { agentPrompt: prompt } }];

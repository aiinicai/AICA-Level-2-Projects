// ============================================================================
//  Supabase Edge Function — extract-notice
//
//  Holds the Anthropic API key server-side and proxies one extraction call so
//  the key is never shipped to the browser. Called from the app as:
//     supabase.functions.invoke('extract-notice', { body: { noticeText, pdfDataUrl } })
//
//  Deploy:   supabase functions deploy extract-notice
//  Secret:   supabase secrets set ANTHROPIC_API_KEY=sk-ant-api...
//            (optional) supabase secrets set ANTHROPIC_WORKSPACE_ID=wrkspc_...
//
//  If you never set ANTHROPIC_API_KEY, automatic extraction is simply
//  unavailable and users fall back to the "paste from Claude.ai" flow.
// ============================================================================

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
};

const CLAUDE_MODELS = [
  'claude-opus-5',
  'claude-sonnet-5',
  'claude-3-5-sonnet-20241022',
  'claude-3-haiku-20240307',
];

const EXTRACTION_PROMPT = `You are a Senior Indian Chartered Accountant specializing in GST litigation.

A GST Notice document has been provided. READ IT COMPLETELY AND CAREFULLY — every page, every table, every paragraph.

TASK: Extract ALL of the following information EXACTLY as it appears in the document.
DO NOT guess, hallucinate, or fill in generic values. If something is not in the document, use "" or 0.

EXTRACT:
1. Notice/Reference Number (exact string as printed)
2. Form Type — one of: DRC-01, DRC-01A, DRC-07, ASMT-10, REG-17, ADT-01, RFD-08, MOV-06, SCN
3. Taxpayer GSTIN (15-character alphanumeric)
4. Taxpayer Legal Name
5. Financial Year (format: YYYY-YY)
6. Period covered
7. Notice Date (exact date as printed)
8. Reply/Response Deadline date
9. Personal Hearing date and time (if mentioned)
10. Issuing Officer — name and designation
11. DIN (Document Identification Number)
12. Sections and Rules cited in the notice

FINANCIAL AMOUNTS (read the demand table carefully):
- Principal Tax demanded (IGST + CGST + SGST combined, excluding interest and penalty)
- Interest amount (Section 50)
- Penalty amount
- Total Demand

FOR EACH ISSUE/DISCREPANCY listed in the notice:
- Issue number, short title, the exact allegation text
- Sections and Rules relied on, page/paragraph reference
- Tax / interest / penalty / total for this specific issue
- Why this discrepancy likely arose (probable reason from a CA perspective)
- Where the department got their figures from (which GST portal return/table)
- What documents/data are needed to respond
- What reconciliation is required
- Specific questions to ask the client
- Required documents list
- Defense points available
- Legal position with relevant case laws/circulars [Verify before use]
- Risk level: HIGH / MEDIUM / LOW

FORMATTING RULES for the lists (these feed a Document Tracker and a Client Discussion log):
- "clientQuestions": a newline-separated numbered list, one clear question per line.
- "documentsRequired": a newline-separated list, ONE document or record per line.

OUTPUT FORMAT: Return ONLY a valid JSON object — no explanation, no markdown, no code blocks:
{
  "noticeNumber": "", "formType": "DRC-01", "gstin": "", "taxpayerName": "",
  "financialYear": "", "period": "", "noticeDate": "", "replyDeadline": "",
  "hearingDate": "", "issuingAuthority": "", "sectionsMentioned": "", "din": "",
  "principalTax": 0, "interest": 0, "penalty": 0, "totalDemand": 0,
  "issues": [
    {
      "issueNumber": 1, "title": "", "allegation": "", "sectionRule": "", "pageRef": "",
      "taxAmount": 0, "interestAmount": 0, "penaltyAmount": 0, "totalAmount": 0,
      "probableReason": "", "figureSource": "", "dataRequired": "", "reconciliationRequired": "",
      "clientQuestions": "", "documentsRequired": "", "defensePoints": "",
      "legalPosition": " [Verify before use]", "riskLevel": "HIGH", "factsCategory": ""
    }
  ]
}`;

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: CORS });

  try {
    const apiKey = Deno.env.get('ANTHROPIC_API_KEY');
    if (!apiKey) {
      return json({ error: 'Automatic extraction is not configured. Use the "Paste from Claude.ai" option instead.' }, 400);
    }
    const workspaceId = Deno.env.get('ANTHROPIC_WORKSPACE_ID') || undefined;

    const { noticeText, pdfDataUrl } = await req.json();
    if (!noticeText && !pdfDataUrl) return json({ error: 'No notice content provided.' }, 400);

    const content: unknown[] = [];
    if (pdfDataUrl && String(pdfDataUrl).startsWith('data:')) {
      const comma = pdfDataUrl.indexOf(',');
      const header = pdfDataUrl.substring(0, comma);
      const data = pdfDataUrl.substring(comma + 1);
      if (header.includes('application/pdf')) {
        content.push({ type: 'document', source: { type: 'base64', media_type: 'application/pdf', data } });
      } else {
        let mediaType = 'image/jpeg';
        if (header.includes('image/png')) mediaType = 'image/png';
        else if (header.includes('image/webp')) mediaType = 'image/webp';
        content.push({ type: 'image', source: { type: 'base64', media_type: mediaType, data } });
      }
    }
    if (noticeText && !String(noticeText).startsWith('[Attached Document:')) {
      content.push({ type: 'text', text: `GST Notice Text:\n${noticeText}` });
    }
    content.push({ type: 'text', text: EXTRACTION_PROMPT });

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'x-api-key': apiKey,
      'anthropic-version': '2023-06-01',
    };
    if (workspaceId) headers['anthropic-workspace-id'] = workspaceId;

    let lastError = '';
    for (const model of CLAUDE_MODELS) {
      const resp = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers,
        body: JSON.stringify({ model, max_tokens: 8192, messages: [{ role: 'user', content }] }),
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        lastError = err?.error?.message || `HTTP ${resp.status}`;
        if (resp.status === 404 || resp.status === 529 || /model|overloaded/i.test(lastError)) continue;
        return json({ error: lastError }, resp.status);
      }
      const data = await resp.json();
      const raw = data?.content?.[0]?.text;
      if (!raw) return json({ error: `Model ${model} returned an empty response.` }, 502);

      let jsonStr = String(raw).trim();
      if (jsonStr.startsWith('```')) jsonStr = jsonStr.replace(/^```(?:json)?\s*/i, '').replace(/\s*```\s*$/, '');
      const match = jsonStr.match(/\{[\s\S]*\}/);
      if (!match) return json({ error: `No JSON in the model response: ${jsonStr.slice(0, 200)}` }, 502);

      return json({ parsed: JSON.parse(match[0]) }, 200);
    }
    return json({ error: `All models failed. Last error: ${lastError}` }, 502);
  } catch (e) {
    return json({ error: (e as Error).message || 'Extraction failed.' }, 500);
  }
});

function json(body: unknown, status: number) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...CORS, 'Content-Type': 'application/json' },
  });
}

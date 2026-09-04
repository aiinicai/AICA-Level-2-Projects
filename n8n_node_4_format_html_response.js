/**
 * n8n Node: "Format HTML Response" (Code node)
 * Workflow: FTA HSN Query
 *
 * Purpose: Takes the raw HTML fragment produced by the FTA Answer Agent
 * (h4/p/blockquote/table/ul tags per the agent's system prompt) and injects
 * inline styling so it renders cleanly inside the n8n form's completion page,
 * then wraps it in a styled container div.
 *
 * Runs after: FTA Answer Agent
 * Feeds into: Show Answer (form completion node)
 */

const raw = $json.output || '';
let html = raw
  .replace(/<h4>/g, '<h4 style="color:#1a2238;border-bottom:1px solid #ddd;padding-bottom:4px;margin-top:18px;margin-bottom:6px;font-size:15px;">')
  .replace(/<h3>/g, '<h4 style="color:#1a2238;border-bottom:1px solid #ddd;padding-bottom:4px;margin-top:18px;margin-bottom:6px;font-size:15px;">')
  .replace(/<blockquote>/g, '<blockquote style="background:#f7f5ef;border-left:3px solid #a9793f;padding:6px 10px;margin:6px 0;font-style:italic;font-size:13.5px;">')
  .replace(/<table>/g, '<table style="border-collapse:collapse;width:100%;margin:8px 0;font-size:13.5px;">')
  .replace(/<th>/g, '<th style="border:1px solid #ddd;padding:5px 8px;text-align:left;background:#f0eee6;">')
  .replace(/<td>/g, '<td style="border:1px solid #ddd;padding:5px 8px;text-align:left;">')
  .replace(/<ul>/g, '<ul style="margin:6px 0;padding-left:20px;">')
  .replace(/<p>/g, '<p style="margin:6px 0;">')
  .replace(/class="note"/g, 'style="margin-top:14px;padding:8px 10px;background:#fbeee0;border-left:3px solid #c77d2e;font-size:12.5px;"');

const wrapped = `<div style="font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;max-width:740px;margin:0 auto;color:#1f2430;line-height:1.5;padding:16px;">${html}</div>`;

return [{ json: { html: wrapped } }];

// Adapted from the old Apps Script HTML delegation email (AddTaskToMasterSheetv2.js)
// so the branded look carries over into the new app (Part 4 decision).

export function buildTaskEmailHtml(opts: {
  recipientName: string
  taskNumber: string
  clientName: string
  description: string
  plannedDate: string
  kind: 'created' | 'delegated'
}): string {
  return minifyHtml(buildTaskEmailHtmlRaw(opts))
}

/**
 * denomailer's quoted-printable encoder has a bug: it corrupts trailing
 * whitespace-before-newline runs when wrapping long multi-line input into
 * 74-char chunks (visible as literal "=20" text in the received email).
 * Collapsing to a single line sidesteps the buggy code path entirely rather
 * than working around it inside a third-party dependency.
 */
function minifyHtml(html: string): string {
  return html.replace(/>\s+</g, '><').replace(/\s+/g, ' ').trim()
}

function buildTaskEmailHtmlRaw(opts: {
  recipientName: string
  taskNumber: string
  clientName: string
  description: string
  plannedDate: string
  kind: 'created' | 'delegated'
}): string {
  const heading = opts.kind === 'created' ? 'New Task Delegated' : 'Task Delegated To You'
  const row = (label: string, value: string, bg: string, bold = false) => `
    <tr style="background:${bg};">
      <td style="padding:12px 16px;font-size:13px;font-weight:600;color:#6b7280;
                  width:35%;border-bottom:1px solid #e5e7eb;
                  text-transform:uppercase;letter-spacing:0.5px;">${label}</td>
      <td style="padding:12px 16px;font-size:14px;color:#111827;
                  font-weight:${bold ? 700 : 400};border-bottom:1px solid #e5e7eb;
                  word-break:break-word;">${escapeHtml(value)}</td>
    </tr>`

  return `<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/></head>
<body style="margin:0;padding:0;background:#f4f6f8;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f4f6f8;padding:40px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" border="0"
             style="background:#fff;border-radius:10px;box-shadow:0 2px 8px rgba(0,0,0,0.08);
                    overflow:hidden;max-width:600px;width:100%;">
        <tr>
          <td style="background:linear-gradient(135deg,#6B4226,#4F3019);padding:32px 40px;text-align:center;">
            <p style="margin:0 0 6px;font-size:11px;letter-spacing:2px;text-transform:uppercase;
                       color:rgba(255,255,255,0.75);">Ecoo Global Advisors</p>
            <h1 style="margin:0;font-size:22px;font-weight:700;color:#fff;">${heading}</h1>
            <p style="display:inline-block;margin:16px 0 0;padding:5px 18px;
                       background:rgba(255,255,255,0.18);border-radius:20px;
                       font-size:13px;font-weight:600;color:#fff;">${escapeHtml(opts.taskNumber)}</p>
          </td>
        </tr>
        <tr>
          <td style="padding:32px 40px 8px;">
            <p style="margin:0;font-size:15px;color:#374151;line-height:1.6;">
              Dear <strong>${escapeHtml(opts.recipientName)}</strong>,
            </p>
            <p style="margin:12px 0 0;font-size:15px;color:#374151;line-height:1.6;">
              A task has been ${opts.kind === 'created' ? 'delegated to you' : 'passed to you'}.
              Please review the details below and ensure it is completed by the planned date.
            </p>
          </td>
        </tr>
        <tr>
          <td style="padding:24px 40px;">
            <table width="100%" cellpadding="0" cellspacing="0" border="0"
                   style="border-collapse:collapse;border-radius:8px;overflow:hidden;border:1px solid #e5e7eb;">
              ${row('Task ID', opts.taskNumber, '#f0f7ff', true)}
              ${row('Client', opts.clientName, '#ffffff')}
              ${row('Description', opts.description, '#f9fafb')}
              ${row('Planned Date', opts.plannedDate, '#ffffff')}
            </table>
          </td>
        </tr>
        <tr><td style="padding:0 40px;"><hr style="border:none;border-top:1px solid #e5e7eb;margin:0;"/></td></tr>
        <tr>
          <td style="padding:24px 40px;text-align:center;">
            <p style="margin:0;font-size:13px;color:#9ca3af;">
              This is an automated notification from
              <strong style="color:#6b7280;">Ecoo Global Advisors</strong>. Please do not reply to this email.
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>`
}

function escapeHtml(value: string): string {
  return value.replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

// Triggered by two Supabase Database Webhooks (configured in the Dashboard,
// see webapp/supabase/README.md):
//   1. INSERT on public.tasks            -> "task created" email to the Primary assignee
//   2. UPDATE on public.tasks             -> "delegated" email to the Secondary assignee,
//      only when secondary_assignee_id went from null to a real value
//
// This is the ONLY place emails are sent from (Part 4: exactly these 2 events
// get emailed; revisions/closures do not).

import { createClient } from 'jsr:@supabase/supabase-js@2'
import { SMTPClient } from 'https://deno.land/x/denomailer@1.6.0/mod.ts'
import { buildTaskEmailHtml } from '../_shared/emailTemplate.ts'

const WEBHOOK_SECRET = Deno.env.get('WEBHOOK_SECRET')!
const GMAIL_USER = Deno.env.get('GMAIL_USER')!
const GMAIL_APP_PASSWORD = Deno.env.get('GMAIL_APP_PASSWORD')!

const admin = createClient(Deno.env.get('SUPABASE_URL')!, Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!)

Deno.serve(async (req) => {
  if (req.headers.get('x-webhook-secret') !== WEBHOOK_SECRET) {
    return new Response('Unauthorized', { status: 401 })
  }

  const payload = await req.json()
  const { type, record, old_record } = payload as {
    type: 'INSERT' | 'UPDATE'
    record: Record<string, any>
    old_record: Record<string, any> | null
  }

  let recipientId: string | null = null
  let kind: 'created' | 'delegated' = 'created'

  if (type === 'INSERT') {
    recipientId = record.primary_assignee_id
    kind = 'created'
  } else if (type === 'UPDATE') {
    const gainedSecondary = !old_record?.secondary_assignee_id && record.secondary_assignee_id
    if (!gainedSecondary) return new Response('No email needed', { status: 200 })
    recipientId = record.secondary_assignee_id
    kind = 'delegated'
  }

  if (!recipientId) return new Response('No recipient', { status: 200 })

  const [{ data: recipient }, { data: client }] = await Promise.all([
    admin.from('profiles').select('email, full_name').eq('id', recipientId).single(),
    admin.from('clients').select('name').eq('id', record.client_id).single(),
  ])

  if (!recipient?.email) return new Response('Recipient has no email', { status: 200 })

  const html = buildTaskEmailHtml({
    recipientName: recipient.full_name || recipient.email,
    taskNumber: record.task_number,
    clientName: client?.name ?? '—',
    description: record.description,
    plannedDate: record.planned_date,
    kind,
  })

  const client_ = new SMTPClient({
    connection: {
      hostname: 'smtp.gmail.com',
      port: 465,
      tls: true,
      auth: { username: GMAIL_USER, password: GMAIL_APP_PASSWORD },
    },
  })
  await client_.send({
    from: GMAIL_USER,
    to: recipient.email,
    subject: `New Task Delegated: ${record.task_number}`,
    content: 'This email requires an HTML-capable client.',
    html,
  })
  await client_.close()

  return new Response('Sent', { status: 200 })
})

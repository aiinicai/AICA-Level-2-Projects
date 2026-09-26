-- Expense Settlement Tool — Storage policies for receipt files
-- Run this in the Expenses Settlement Supabase project's SQL Editor,
-- after the main schema. Creates a private bucket and access rules
-- matching the same visibility as claims/claim_lines.

-- Bucket itself: private, not publicly readable by URL guessing.
insert into storage.buckets (id, name, public)
values ('receipts', 'receipts', false)
on conflict (id) do nothing;

-- File path convention expected by the app: receipts/<claim_id>/<line_id>-<filename>
-- This lets policies check the claim_id segment of the path directly,
-- without a join back to claim_lines for every file access check.

-- Upload: an employee may upload a file into their OWN claim's folder,
-- and only while that claim is still in Draft.
create policy "upload_own_draft_receipts" on storage.objects
for insert with check (
  bucket_id = 'receipts'
  and exists (
    select 1 from claims c
    where c.claim_id::text = (storage.foldername(name))[1]
      and c.employee_id = current_employee_id()
      and c.status = 'draft'
  )
);

-- Read: same visibility as the parent claim — owner, their team head/
-- backup, or accounts once approved/settled.
create policy "read_receipts" on storage.objects
for select using (
  bucket_id = 'receipts'
  and exists (
    select 1 from claims c
    where c.claim_id::text = (storage.foldername(name))[1]
      and (
        c.employee_id = current_employee_id()
        or is_head_of_team((select team_id from employees where employee_id = c.employee_id))
        or (is_accounts() and c.status in ('approved', 'settled'))
      )
  )
);

-- Delete: owner only, only while Draft — matches claim_lines' own edit rule.
create policy "delete_own_draft_receipts" on storage.objects
for delete using (
  bucket_id = 'receipts'
  and exists (
    select 1 from claims c
    where c.claim_id::text = (storage.foldername(name))[1]
      and c.employee_id = current_employee_id()
      and c.status = 'draft'
  )
);

-- No update policy: a receipt is replaced by delete + re-upload, not edited in place.

-- Note: accounts' edit-during-unlock exception (claim_lines) does not
-- extend to receipt files in this version — an unlocked correction can
-- change the entered figures, but not silently swap the underlying
-- receipt image. If accounts needs to replace a receipt during an
-- unlock, that should go through the same delete+upload path, which
-- requires the claim to be back in Draft — not currently possible
-- while Approved-with-open-unlock. Flagging as an open question rather
-- than deciding it here: should an open unlock also grant receipt
-- delete/upload rights, same as it does for claim_lines figures?

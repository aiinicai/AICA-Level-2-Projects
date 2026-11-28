# ClaimDesk migration roadmap

- [x] Inspect the source archive and inventory its app, data model, storage, and AI capabilities.
- [x] Rebuild ClaimDesk login, employee submissions, company approvals, vouchers, and reports.
- [x] Move the schema, private receipt storage, and access rules to Lovable Cloud; keep roles in `user_roles`.
- [x] Fix reimbursement voucher submission when a field name overlaps a function variable.
- [ ] Switch receipt reading to Google Gemini with the linked API key and verify the app workflow.
- [x] Check the signed-out routes, build, security grants, and automated tests.
- [ ] Import existing users, profiles, vouchers, expenses, and receipt files — waiting for exports.
- [ ] Verify signed-in workflows and decide production cutover — waiting for imported accounts/data and the source-service decision.
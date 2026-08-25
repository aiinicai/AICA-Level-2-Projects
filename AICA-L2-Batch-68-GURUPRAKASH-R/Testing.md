# AuditFlow Testing Summary

| Test | Expected Result | Status |
|---|---|---|
| Create Client | Client created with CLT reference | Passed |
| Create Engagement | Engagement linked to Client | Passed |
| Advance Engagement status | Only permitted transition allowed | Passed |
| Add Scope | Scope linked to Engagement | Passed |
| Add Procedure | Procedure linked to Scope | Passed |
| Issue Requirement | Submission status changed to Issued | Passed |
| Add Evidence | Evidence linked to Requirement | Passed |
| Raise Clarification | Clarification created with linked evidence | Passed |
| Convert Clarification | Draft OBS reference created | Passed |
| Rate Observation | Calculated and final risk displayed | Passed |
| Submit Management Response | Response linked to Observation | Passed |
| Create Multiple Actions | Multiple actions linked to one Observation | Passed |
| Add Closure Update | Append-only update created | Passed |
| Finalise Report | Selected observations marked Reported | Passed |
| Role Restriction | Auditee cannot finalise observations | Passed |
<!-- Prompt 3 - a reusable Claude skill (AICA Level 2, Day 1: build a reusable skill). Load it into Claude and it runs a DPDP readiness review end to end, starting with five interview questions. -->

---
name: dpdp-readiness-review
description: Run a DPDP readiness review of an Indian school or educational institution - scan the website, assess it against the DPDP Act 2023 and DPDP Rules 2025 obligation catalogue, and produce a scored report with a prioritised remediation plan. Use when asked to check a school's data protection readiness, review a school privacy policy, assess DPDP compliance for an educational institution, or prepare a DPDP gap report.
---

# DPDP readiness review for educational institutions

## When to use this

Someone asks for a data protection readiness check, a DPDP gap analysis, a
privacy policy review, or a compliance report for a school, college, coaching
institute or EdTech provider serving children in India.

## Before you start - five questions

Ask these first. Do not scan until you have the first two.

1. **Institution name and website address.** Required.
2. **Do you have the institution's authorisation to scan this site?** Required.
   If the answer is no, stop. Scanning a third party's site without permission
   is not a compliance activity.
3. Any extra pages worth reading - admission, contact, fee portal, gallery.
4. Any supporting documents - the admission form, the consent slip, CCTV
   signage, a transport app screenshot. These carry most of the risk and the
   website carries almost none of it.
5. Should the AI policy analysis run? It needs an API key and it adds quoted
   evidence; it never changes the score.

## Running it

```
python -m surakshascan.cli scan \
    --name "<institution>" --url "<website>" \
    --extra "<comma separated pages>" \
    --document "<path>" \
    --docx report.docx --xlsx workings.xlsx --html dashboard.html
```

Add `--ai` only when a key is present. Add `--verbose` to watch progress.

## Reading the result

* **The score is not the point.** Report the coverage figure alongside it. A
  score of 80 over 40% of the catalogue is a thin scan, not a good school.
* **Separate what is due now from what is due by 14 May 2027.** Sections 5, 6,
  8 and the accountability duties bind today. Most of the Rules' procedural
  detail commences on 14 May 2027. A school that conflates the two either
  panics or relaxes, and both are wrong.
* **Lead with the children's-data domain.** Everyone below eighteen is a child
  under the Act, so it is the whole student body. This is where a school's
  exposure actually is.
* **Do not overstate the Fourth Schedule exemption.** Rule 12 with Part A
  relieves an educational institution of section 9(1) and section 9(3) for
  academic activities, tracking and behavioural monitoring, and the safety of
  enrolled students - and for nothing else. Marketing, promotional
  photographs, alumni contact and advertising pixels sit outside it.

## What never to do

* Never say a school "is compliant" or "is not compliant". Say what was found
  and against which provision.
* Never report a policy clause the tool did not actually quote. If the AI layer
  rejected a finding because the quotation was not in the policy, that finding
  does not go in the report.
* Never present a not-assessed item as met.
* Never send the report anywhere. Hand it to the person and let them send it.

## Verify before delivering

Check these against the notified text at meity.gov.in before the report goes
out, because they change:

- [ ] the commencement dates of the Rules relied on
- [ ] the Fourth Schedule wording, if the exemption is being relied on
- [ ] any penalty figure quoted
- [ ] the current Data Protection Board complaint route

`references/obligations.md` lists the catalogue and the provision behind each
item.

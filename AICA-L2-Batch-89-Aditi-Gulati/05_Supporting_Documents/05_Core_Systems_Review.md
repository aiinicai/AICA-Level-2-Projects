# Reviewing the ERP, the accounts and the learning platform

## Why this is the important one

The website is a brochure. The social feed is a shop window. The ERP is where
the school's children's data actually lives: date of birth, parent phone
number, address, medical note, transport pickup point, marks, fees — for every
child, going back years.

The school is the **Data Fiduciary**. The ERP vendor, the payment gateway, the
SMS gateway and the learning platform are **Data Processors**. Three
consequences follow that schools routinely miss:

**Section 8(1)** keeps the school responsible for compliance *including where
a processor does the processing on its behalf*. Buying the system does not
transfer the duty.

**Section 8(2)** permits engaging a processor *only under a valid contract*.
Most school ERP arrangements are a purchase order plus the vendor's standard
terms, with no data-processing clauses. That is a gap today, not one that
waits for 14 May 2027.

**If the vendor is breached, the school notifies.** Under section 8(6) and
Rule 7 it is the school that must intimate every affected parent and report to
the Board — not the vendor.

And the Fourth Schedule is a weaker shield here than elsewhere. It only
touches sections 9(1) and 9(3); notice, consent, security, breach, retention,
grievance and the data-principal rights all apply regardless. Teaching and
student safety sit inside the exemption — **fee collection is commercial
administration**, which is harder to call an academic activity.

## What the tool does — and deliberately does not

**It reads the shape of the data, never the data.**

Given an export it reports which columns exist, what category of personal data
each one holds, and how many rows are filled in. A fill rate is a count, not a
value. No cell contents are written to the evidence store, shown in a report,
or sent anywhere. Two tests fail if a child's name, Aadhaar number or address
ever reaches the output.

That constraint is the point. A readiness tool that accumulated a copy of
every school's student database would be a worse problem than the one it was
built to find.

## Running it

**An ERP or fee-software export:**

```powershell
python -m surakshascan.cli scan --name "My School" --url https://myschool.edu.in `
    --system-export students.csv --system-export lms_export.csv --docx report.docx
```

CSV and XLSX both work. In the desktop app, use the **Core systems** tab.

**TallyPrime**, read-only, over its own XML interface on the local machine:

```powershell
python -m surakshascan.cli scan --name "My School" --url https://myschool.edu.in `
    --tally --tally-host localhost --tally-port 9000
```

Open the company in TallyPrime first and enable the XML interface. The request
is an `Export` of a `Collection` marked `ISMODIFY="No"` — a test fails if the
words Import, ALTER, DELETE or CREATE ever appear in it. Use a test company
first, as the Day 5 guidance says: connect read-only, reconcile a small
report, and only then consider anything else.

## What it flags

| Category | Why it matters |
|---|---|
| Government identifier | Aadhaar, PAN, passport — needs a statutory basis and masking at rest |
| Student identifier | APAAR, PEN, UDISE — confirm the basis and who it is shared with |
| Possible caste category | Collected for returns; should not be visible to teachers or exportable with a class list |
| Health | Blood group, allergies, medication, counselling notes |
| Biometric | A child's template, held continuously |
| Credential | A password column in an export is a finding on its own |
| Behavioural note | Free-text remarks about a child — the highest-risk field in any school system, and the least reviewed |
| Location | A pickup point plus a name locates a child at a known time each day |

It also counts **records marked as leavers that are still held in full**, and
reports the **oldest year** appearing in any date column. Columns it cannot
classify are listed for review by hand, because an unclassified column is not
a safe column.

## The accounting point

Schools post fee receipts with the student's name against each receipt, so the
books hold a thin slice of children's data — a name and a payment. Small, but
it raises a problem the ERP does not.

**The books of account must be preserved** for years under the Income-tax and
Companies Act record rules. **Section 8(7) requires erasure** from the student
system once the purpose is served. So a school that "deleted" a leaver has
usually not deleted them.

That is not a failure of the school. Statutory preservation is a lawful basis.
The failures are telling a parent the data is gone when it is not, and never
writing the conflict down. Two things to do:

1. Record both systems and both periods in the retention schedule.
2. Ask whether the ledger needs the child's name at all. A receipt number
   reconciling to the ERP gives the same audit trail in a system fewer people
   can open.

## The obligations this feeds

| Ref | Obligation | Decided by |
|---|---|---|
| S1 | The student records system holds no category without a purpose | The export |
| S2 | Leavers are erased when retention ends | The export and the questionnaire |
| S3 | Student data in the accounts is minimised and the retention conflict recorded | Tally and the questionnaire |
| S4 | The learning platform is governed as a data processor | The export and the questionnaire |

Eight working-paper lines on the **Core Systems** tab cover what no export can
show: whether the vendor has confirmed in writing how a record is erased,
whether the school can produce or delete one named student's record on
request, whether every learning platform in use is actually listed — including
the free ones teachers signed up for themselves — and which ERP integrations
are enabled.

## What to tell the school

- Export the student master and write the purpose beside every column. The
  blank cells in that second column are the finding.
- Ask the ERP vendor, in writing, how a student record is erased. Then run one.
- List the learning platforms by asking the teaching staff, not the IT vendor.
- Check the ERP's integrations page. Each one is a further processor.
- The export itself is the biggest leak: an Excel download on a laptop,
  forwarded. Control who can export, and log it.

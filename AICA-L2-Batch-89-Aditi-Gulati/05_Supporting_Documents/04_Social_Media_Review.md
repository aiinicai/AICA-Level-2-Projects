# Reviewing a school's social media

## Why this exists

A school's website is a brochure it controls and updates twice a year. Its
social feed publishes children's photographs every week, is usually run by
whoever is free, and reaches further. For most schools this is where the real
exposure sits, and a website scan does not reach it at all.

## The legal position

**The Fourth Schedule exemption does not cover it.** Rule 12 read with Part A
relieves an educational institution of section 9(1) and section 9(3) for
academic activities, for tracking and behavioural monitoring, and for the
safety of enrolled students. A promotional post celebrating a result is none
of those, so section 9(1) applies in full: verifiable parental consent, with
Rule 10 due diligence that the consenting adult is identifiable.

Three things make a feed harder than a website:

1. **Withdrawal has to actually work.** Section 6(4) requires withdrawal to be
   as easy as giving consent, and section 12 gives an erasure right. Deleting
   a post does not recall reshares, screenshots or forwards. A school should
   promise only what it can deliver, and say so on the consent form.
2. **The caption is usually worse than the photograph.** A full name plus a
   class identifies a specific child and discloses where that child is every
   weekday morning.
3. **Boosting is a separate act.** Paying a platform to push a post featuring
   children towards a chosen audience moves squarely towards the
   targeted-advertising prohibition in section 9(3).

Also in scope, though harder to see: teachers posting from personal accounts,
and class lists in parent WhatsApp groups. Section 8(1) keeps the school
accountable for school activity whoever's phone it came from.

## What SurakshaScan does — and deliberately does not

**It does not scrape social media.** Scraping public Instagram and Facebook
breaches those platforms' terms, is actively blocked, and — the real
objection — a compliance tool that harvests children's photographs in order to
check whether children's photographs are being over-shared is doing the thing
it audits. There is a test in the suite that fails if scraping code ever
appears in the module.

**It analyses captions and metadata, not faces.** No face recognition is
performed on any child. That would be a greater intrusion than the one under
review, and it is not needed: the caption is where the identification happens.

Three routes, in descending order of confidence:

| Route | How | Confidence |
|---|---|---|
| **Connected page** | The school owns its pages, so it authorises read-only access to its **own** posts with its **own** token | High |
| **Export file** | The school downloads its posts using the platform's own data-export tool and hands over the file | High |
| **Screenshots** | The reviewer supplies screenshots, read by `vision.py` | Sample only, and reported as such |

## Running it

**Connected page** — the token is read from the environment and never stored:

```powershell
$env:SURAKSHASCAN_META_TOKEN = "<the school's own page token>"
python -m surakshascan.cli scan --name "My School" --url https://myschool.edu.in `
    --social-page <the school's page id> --docx report.docx
```

**Export file:**

```powershell
python -m surakshascan.cli scan --name "My School" --url https://myschool.edu.in `
    --social-export posts.json --docx report.docx
```

A CSV works too, with columns `platform, url, posted_at, caption,
media_count, promoted`. `tests/fixtures/social_posts.csv` is a worked example.

**Screenshots:**

```powershell
python -m surakshascan.cli scan --name "My School" --url https://myschool.edu.in `
    --social-screenshot post1.png --social-screenshot post2.png
```

In the desktop app, the page id and export file go on the **Scan** tab and
screenshots on the **Social** tab.

## What it flags

- a full name published together with a class or section
- a roll, admission, APAAR or UDISE number in a caption
- a class or section alone, which narrows the child to a small group
- an individual achievement celebrated by name, which is a promotional purpose
- a boosted or paid post featuring students
- a possible reference to a health or disability characteristic
- a child reference combined with a location detail

Greeting words are stripped before a name is reported, so "Congratulations
Aarav Sharma of Class 5-B" yields *Aarav Sharma*, not *Congratulations Aarav
Sharma of*. A caption of pure congratulation with no name yields nothing —
the tool does not invent a child.

## The obligations this feeds

| Ref | Obligation | Decided by |
|---|---|---|
| C5 | Social media posts do not identify an individual child | The posts |
| C6 | Posts featuring children are not paid for or boosted | The posts and the questionnaire |
| C7 | Media consent is separate, granular and genuinely revocable | Questionnaire |
| C8 | Staff do not publish student data from personal accounts | Questionnaire |

C7 and C8 cannot be seen from a feed, so they are answered on the
**Publication and Social Media** tab of the working paper, alongside the
do-not-publish list and the register of withdrawals.

## What to tell the school

The fix is usually cheap and nobody feels less celebrated:

- a first name alone, or the class without the name — never both together
- never a roll or admission number
- no geotagging
- boost the admissions dates and the facilities, not the children
- media consent on its own form, ticked channel by channel, with a stated
  takedown period
- one written rule: student photographs go out from the school account only

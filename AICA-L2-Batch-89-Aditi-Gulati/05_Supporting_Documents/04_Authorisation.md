# Authorisation

SurakshaScan records the name and designation of the person who authorised
each review. It will not run without one, and it prints it on every report,
so anyone reading a report can see on whose authority it was done.

**Desktop app:** the *Authorised by* field on the Scan tab.

**Command line:**

```
python -m surakshascan.cli scan --name "St. Mary's Convent School" ^
    --url https://stmarys.example.edu.in ^
    --authorised-by "Sr. Anne, Principal" --docx stmarys.docx
```

## Keep the consent itself

The tool records who authorised the review; it does not hold the consent.
Keep each principal's email or letter, and note what they agreed to.

Consent to review a website is not consent to review a school's social media.
A child's photograph posted by a school is still covered by the DPDP Act —
section 3(c)(ii) only exempts data made public by the Data Principal or under
a legal obligation — so review a school's social media only where it has
agreed to that specifically.

## Reports go to the school, and nowhere else

Permission to review is not permission to publish. A report about a real
school goes to that school's principal. Use the fixture school for anything
public — GitHub, a video, or a capstone submission.

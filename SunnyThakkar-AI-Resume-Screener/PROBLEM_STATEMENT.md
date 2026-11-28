# Problem Statement: AI Resume Screener

**AICA Level 2, extra project**

## The problem
A single job post can get hundreds of resumes. Recruiters spend about 6 to 8
seconds on a first look at each one, so good candidates are missed and the
choice depends on who reads the pile and when. Resumes come in different
formats (PDF, Word, scanned paper), and the same skill is written many ways
("ML", "machine learning", "scikit-learn"). Small companies cannot afford a
paid Applicant Tracking System (ATS).

## Objective
Build a free, offline desktop app that:
1. Reads resumes in PDF, Word and scanned (image) PDF format.
2. Compares each resume with a job description.
3. Ranks the candidates with a clear score out of 100.
4. Explains each score: matched skills, missing skills, experience.
5. Exports the shortlist to Excel, with an optional AI review per candidate.

## Approach
1. **Read**: `pypdf` for PDFs, `python-docx` for Word. Scanned pages are
   turned into images (`pypdfium2`) and read with offline OCR (`RapidOCR`);
   OCR words that run together are split again with an English word list.
2. **Extract**: a skill dictionary of about 115 skills and their other
   names finds skills in the job and in each resume. Regular expressions find
   email, phone and years of experience.
3. **Score** (explainable, no black box):
   - 60% skill match: job skills found / job skills asked
   - 30% text match: TF-IDF vectors and cosine similarity (written from scratch)
   - 10% experience: years found / years asked
4. **Rank** and label: Strong (70+), Good (50+), Partial (30+), Weak.
5. **Optional AI**: send one resume and the job to Google Gemini or Groq for
   strengths, gaps and interview questions.

## Scope
- In scope: English resumes, PDF/DOCX/TXT, scanned PDFs, one job at a time,
  CSV export, Windows EXE.
- Out of scope: handwriting, other languages, emailing candidates, storing data online.

## Fairness
The score uses only skills, text and experience. It does not look at name,
gender, age, photo or nationality. It is a shortlisting aid; a person makes
the hiring decision.

## Expected outcome
Shortlisting 50 resumes takes under a minute instead of hours, and every
score can be explained to the hiring manager.

## Tools and technologies
Python, Tkinter (GUI), pypdf, python-docx, RapidOCR + pypdfium2 (OCR),
TF-IDF and cosine similarity (from scratch), regular expressions,
Google Gemini / Groq APIs (optional), PyInstaller (EXE).

# Demonstration video: GST Notice Analyzer

Target length: 3-5 minutes. Show your face and the app screen as required by the course form. Speak in your own words and demonstrate only after you understand the tool. Do not show client notices, account passwords, browser notifications or API keys.

## Before recording

- Complete setup and launch `RUN_WINDOWS.bat`.
- Keep the ASMT-10 sample selected. It is fully fictional.
- Set browser zoom around 90-100% for readable text.
- Use a camera + screen-recording tool of your choice. Check microphone and camera first.
- Course form wording should be checked directly before upload; provide an accessible unlisted YouTube or Drive link as instructed. The software does not upload the video.

## 0:00-0:35 - Introduce the CA problem

Suggested narration:

"I am Dhiraj Dugar. My capstone is GST Notice Analyzer, an offline-first prototype for reviewing GST notices. In practice, the first challenge is to identify the exact allegations, understand the procedure, gather documents and prepare a clear reply. This tool assists that workflow, but the CA remains responsible for every fact and legal conclusion."

Show the title, local URL, sample selector and human-review warning.

## 0:35-1:15 - Extract and verify the notice

Show Notice summary and the form/period/deadline fields.

"This is a fictional ASMT-10 sample. The app extracts searchable PDF text and explicitly labelled details such as GSTIN, reference, period and reply date. I can correct each field. Importantly, it does not invent a reply date from the issue date. If the notice is scanned, OCR is needed first."

Briefly open the extracted-text expander, then close it.

## 1:15-2:10 - Explain the issues and provisions

Click Issues & evidence. Show the two detected topics and one card.

"Here the rules flag an ITC mismatch and a GSTR-1 versus GSTR-3B output liability gap. The app shows the actual source wording with page references, not just a label. It suggests provisions to examine and gives an invoice/return reconciliation and document checklist. A mismatch is only an allegation: it does not prove the credit is ineligible or the tax is unpaid. I must verify the records and the law for the relevant period."

Show that the selected topics can be removed or added. Do not claim a defence is already established.

## 2:10-2:50 - Describe the real AI component honestly

Click AI & audit trail.

"The AI component is a local natural-language classifier. It uses TF-IDF word and bigram features with logistic regression, trained on 60 synthetic labelled examples. It suggests issue categories. Additional suggestions require my confirmation before going into the reply. Legal notes are curated templates, not AI-created legal conclusions. The model is small and not validated for all notices; its scores are not legal confidence. No API key is needed and no notice is sent to an external model."

Point to the model classifications and audit download. If no additional topic appears, say that rules already covered the supported topics; do not pretend that this proves completeness.

## 2:50-3:40 - Produce the working reply

Click Reply draft. Optionally type: "Fictional demonstration only. Actual invoice-wise reconciliation is pending."

"The output is a structured working reply. It includes a factual-background placeholder, issue-by-issue facts to confirm, provisions to examine, documents to gather and a conclusion placeholder. It does not invent admissions, legal citations or payment claims. I can edit it and download Word or Markdown for professional review."

Tick the working-draft acknowledgement and download the Word file. If convenient, show it briefly.

## 3:40-4:25 - Show another notice type and close

Choose DRC-01 in the sidebar. Show the form, two issue labels and procedure note.

"The second sample is a DRC-01 summary for FY 2024-25. It raises reverse charge and blocked credit. The tool reminds me to obtain the full show-cause notice and check section 74A for the period, rather than mechanically using older provisions. DRC-01A is separately treated as a pre-notice intimation."

"The value is a faster, traceable first review with explicit human control. Future work includes OCR, richer labelled data and stronger expert testing. The project includes source code, fictional samples, setup instructions and automated tests. It does not file a reply or decide liability."

## Presentation and declaration checks

- Run all three samples and review the code before recording.
- Acknowledge AI-assisted development as the course requires. Do not claim independent authorship if that would be inaccurate.
- Make your own practical validation visible, including why the suggested documents/provisions matter.
- The video is your demonstration, not evidence that a live notice has been legally resolved.

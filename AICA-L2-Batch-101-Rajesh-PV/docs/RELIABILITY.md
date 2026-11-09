# Reliability - questions the panel may ask

## 1. If the same judgment is summarised twice, will the AI give the same output?

No - not word for word, and the app does not assume it will. Large language models are not perfectly repeatable even on "deterministic" settings. Published studies illustrate this:

- Atil et al., *Non-Determinism of "Deterministic" LLM Settings* (arXiv 2408.04667): with temperature 0 and a fixed seed, outputs were rarely identical across runs and accuracy varied by up to about 15% between runs.
- Blair-Stanek & Van Durme, *LLMs Provide Unstable Answers to Legal Questions* (arXiv 2502.05196): asked to decide the same hard legal question 20 times at temperature 0, models gave inconsistent answers on a substantial share of questions (Gemini 1.5: 50.4%, GPT-4o: 43.0%, Claude 3.5: 10.6%). Our task - summarising a judgment that is already decided - is easier, but the lesson is the same.

What matters is that the **substance** (court, date, AY, sections, issues, outcome, ratio, quotations) is right. The app checks that instead of trusting any single run.

## 2. How does the app make the output reliable?

| Layer | What it checks | How |
|---|---|---|
| Consistency Check | Do two independent AI runs agree on the 14 key facts? | Python comparison; disagreements marked [Uncertain] and must be resolved by the reviewer before emails can be approved |
| Source Check | Are quotations, citations, sections, dates, amounts and para/page references actually in the judgment? | Deterministic text matching - the same answer every time |
| Prompt rules | Use only the document; never invent citations; label court findings vs AI observations; mark uncertainty | System instruction in `prompts.py` |
| Human approval | A named reviewer confirms key facts, approves emails, marks register entries Verified | Recorded in the register and the email audit log (with a content fingerprint) |

## 3. What percentage is it reliable / accurate?

A single universal percentage would not be honest - it depends on the model, the judgment and the question. The app **measures** it on your own test set with `tools/reliability_eval.py`:

- run-to-run agreement on key facts (%),
- accuracy against a human-prepared answer key (%),
- Source Check pass rate (%).

Report the figures from your test run (for example 20 public tribunal / High Court orders, 3 runs each) in the project report and video.

## 4. Why not run each case several times, pick the best output and email that?

- "Best" needs a judge. Using another AI run to judge only moves the problem; the reviewer is the judge.
- Full reports are long; repeating them multiplies time and free-tier quota.
- The app therefore repeats the **short, checkable** part (key facts, a small JSON extraction) and compares runs automatically, verifies the full report against the source text, and leaves judgement to a human.

## 5. Can the team rely on the summary instead of reading the judgment?

The summary is a **map** to the judgment, not a substitute. Each point carries a paragraph reference, the register keeps the original PDF, and only entries marked *Verified* by a reviewer should be used. The team reads the cited paragraphs before relying on a point in an appeal or opinion.

## 6. Why the model's default temperature for Gemini 3?

Google's Gemini 3 developer guide recommends keeping the temperature at its default of 1.0 for Gemini 3 models, warning that lower values can cause looping or degraded performance. Determinism is not achieved by lowering temperature anyway (see 1), so the app follows Google's guidance and relies on the checks above. Confirm the current guidance for the exact model you use.

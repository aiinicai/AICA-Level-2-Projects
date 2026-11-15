# Local model card

## Intended use

A teaching prototype that suggests GST-notice issue labels to a CA. It is not a legal advice model, document authenticity checker or final classifier of liability.

## Model and data

- Scikit-learn pipeline: `TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)` followed by `LogisticRegression(C=6, random_state=42, max_iter=1000)`.
- 60 synthetic English sentences, 10 for each of five issue classes plus `other`.
- Source corpus: `data/training_examples.csv`. Regeneration: `python data/build_training_data.py`.
- No real taxpayers, downloaded model weights, API key or external inference service.
- Model trains locally at first inference and is cached in the process. Uploaded notices are never added to training data.

## How output is used

Each extracted line/sentence with at least seven alphabetic words is classified. The highest-scoring label is retained if it is not `other` and its uncalibrated model score is at least 0.38. The app retains the best evidence snippet per label. This threshold is a prototype heuristic, not a statistical guarantee. Scores are not presented as legal certainty.

Separate evidence rules populate the default issue list. The model's additional suggestions are shown for review; the CA must manually select a topic before it enters the reply skeleton. Curated legal notes and draft prompts are templates, not machine-generated findings or an LLM response.

## Evaluation and known limits

Unit tests confirm that inference actually runs and that a reverse-charge paraphrase is classified as RCM. There is no independent real-world test set or validated accuracy number. Synthetic examples are small and stylistically similar; this model will not generalise reliably to every notice. It may confuse ITC mismatch with blocked ITC, miss unfamiliar wording, fail on negation or lose context across wrapped PDF lines. It has no multilingual training.

Do not call it production-ready or claim a measured precision/accuracy. Improve it only with lawful, de-identified data, an independent labelled test set, appropriate train/test separation and expert evaluation. Retain abstention and review controls.

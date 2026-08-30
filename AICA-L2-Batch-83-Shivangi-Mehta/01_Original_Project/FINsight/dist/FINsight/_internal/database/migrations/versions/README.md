# Initial migration

`0001_initial_schema.py` now exists in this directory, hand-authored
against `app/models/*.py` (all 24 approved tables, post Stage-3-review-
round-2 corrections — including the `exceptions.supporting_file_id`
removal).

**Why hand-authored instead of `--autogenerate`:** this delivery sandbox
could not install SQLAlchemy or Alembic — confirmed via repeated `pip`
and `apt` attempts, both returning `403 Forbidden` from the sandbox's
network proxy on PyPI and the Ubuntu archive. `--autogenerate` needs a
real SQLAlchemy environment to introspect `Base.metadata`, so it could
not be run here.

**What was actually verified here, without real Alembic/SQLAlchemy:**
a custom, clearly-labeled test harness (not part of the delivered app)
executed this file's real `upgrade()` function against a real SQLite
database via a minimal `alembic.op`/`sqlalchemy` compatibility shim,
then cross-checked the resulting live schema against every model file's
declared columns via Python's `ast` module (parsing the source, not
executing it — since the real classes can't be imported without
SQLAlchemy). See the Stage 3 round-2 delivery notes for the full output.
That is a real, automated, line-by-line comparison — not a hand
eyeball-check — but it is still a stand-in for the real thing.

**Before this migration is trusted as final**, on a machine with normal
network access:

```bash
pip install -r requirements.txt
alembic upgrade head
python -m database.seed.seed_reference_data   # reference data only, no rule content
pytest tests/unit/test_migration.py -v         # the real, delivered migration test
```

Then, ideally, also run `alembic revision --autogenerate -m "check drift"`
once against the resulting database — an empty generated diff confirms
this hand-authored file and `app/models/*.py` agree exactly. A non-empty
diff means this file has a mistake relative to the models (the models
are the source of truth) and should be fixed, not the other way round.

# Development Rules

This document outlines the project's engineering constitution.

## Core Principles
1.  **Inspect before editing**: Always review existing code before modifying.
2.  **Preserve working functionality**: Do not break existing features or rewrite modules merely for style.
3.  **Modular architecture**: Maintain a clear separation of concerns (routes, services, database, utils).
4.  **Local-first privacy**: No external data transmission. Processing must remain entirely local.
5.  **No external upload**: Client data (PDFs, bank details) must never be uploaded to external APIs or CDNs.

## Technical Standards
1.  **Dependencies**: Keep dependencies minimal. Justify any new additions. No complex frontend frameworks (React, Angular) or backend task queues (Celery, Redis).
2.  **Paths**: Use `pathlib` for all file system operations.
3.  **Database**: Use parameterized SQL with `sqlite3`. No ORMs.
4.  **Monetary Calculations**: Use `decimal.Decimal` for future monetary calculations to avoid floating-point errors.
5.  **Subprocesses**: Avoid unsafe subprocess shell construction.
6.  **Secrets**: Never store secrets in source control.

## Testing and Git
1.  **Tests required**: All new logic must have corresponding `pytest` coverage. Do not create fake passing tests or suppress failures.
2.  **Controlled Git checkpoints**: Commit frequently with clear messages. Do not rewrite history (`git reset --hard`) without strong justification.
3.  **Scope Control**: Do not progress to later stages of the master project plan automatically.

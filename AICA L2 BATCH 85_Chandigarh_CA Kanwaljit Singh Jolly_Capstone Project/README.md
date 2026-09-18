# Task Checker

## Project overview

Task Checker is an AI-powered workflow validation system that checks completed task outputs against their source files and workflow instructions. It records evidence for each verdict and routes uncertain or failed results to a human-review queue.

The project can be used as a multi-tenant web application powered by Flask, Supabase, OneDrive, and the OpenAI Codex SDK. It also includes a command-line runner for validating task folders stored locally without using the web interface or OneDrive.

## Features

- Create reusable checking agents with predefined workflows, input files, output files, and reference files.
- Connect a tenant-owned Microsoft OneDrive account for accessing task files.
- Connect a tenant-owned ChatGPT account for Codex-powered validation.
- Queue validation jobs and process them with a background worker.
- Generate `PASS`, `FAIL`, or `INDETERMINATE` verdicts with supporting evidence.
- Automatically approve passing results and route other results for human review.
- Track validation progress, retries, model details, token usage, and results.
- Generate downloadable PDF validation reports.
- Provide role-based access for superadmins and assigned admins.
- Run deterministic and AI-assisted checks against local task folders.


# Instructions for Claude Code

This is a desktop application for an audit practice. Read README.md first.

## Rules
- Edit the source parts in `src/parts/`, then run `src/assemble.sh` to rebuild
  `balance_confirmation_generator.py`. Never hand-edit the assembled file.
- Run all test suites before reporting a change as done. Report results honestly,
  including any failure.
- Do not add client data, sample balances from real parties, email addresses of
  real parties, passwords, or access keys to the repository.
- Do not change the bridge's access-key logic or the feed format without saying
  so explicitly, because the desktop app depends on both.
- Make changes on a new branch, never directly on `main`.
- Paths inside the scripts may still point to /home/claude; fix them to relative
  paths before relying on them on this computer.
- Arithmetic and reconciliation logic must be verified with code, not by reasoning.

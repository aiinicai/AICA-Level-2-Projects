# Limitations and honest disclaimers

Not tested in a live environment, because of the capstone time limit. They are designed and automated-tested against mock servers, and should be validated before real use:
1. **Real TallyPrime posting** – the Tally XML was tested against a mock Tally server only.
2. **n8n e-mail workflow** – `docs/n8n_workflow.json` has not been run on a live n8n instance.
3. **SMTP e-mail sending** – without SMTP settings, approved e-mails are saved as .eml files (simulated sending).
4. **Windows EXE build** – `build_exe.bat` has not been run on the author's PC at submission time; the app runs with Python via `run_windows.bat`.
5. **AI skill launcher** – opens Claude/ChatGPT with a pre-filled prompt and copies it to the clipboard; very long prompts may be truncated by the website.

Other points:
- Statutory due dates in the compliance master are configurable defaults and **must be verified by the CA** against current notifications.
- AI features run on built-in rules by default; an OpenAI key is optional.
- Client Portal and Document Vault are planned modules, not built.
- Designed for a single office on one PC/LAN, not for internet exposure.

Planned: client portal, document vault, WhatsApp reminders, quotations and expenses, penalty tracking.

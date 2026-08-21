# Security Policy & Data Privacy

## 🔒 Security Architecture

**GrantSetu** is built as an **offline-first local application**. Understanding the security architecture is critical for non-profits handling sensitive donor, financial, and statutory information:

1. **Zero External Telemetry**:
   - The application does not send financial data, donor information, or voucher records to any remote cloud servers.
   - All state management operates locally inside the user's browser or Electron desktop environment.

2. **Data Storage & Encryption**:
   - Application data is saved to `localStorage` / `IndexedDB` within the browser domain scope.
   - Database backups exported via the application are saved in raw JSON format; users are advised to encrypt backup files prior to external transmission.

3. **No Third-Party Analytics**:
   - No tracking scripts, analytics SDKs, or external trackers are bundled in the application.

## 🛡️ Reporting a Vulnerability

If you discover a security vulnerability or security bug in **GrantSetu**, please report it responsibly:

- **Email**: Create an issue on GitHub marked with `[SECURITY]` in the title or contact the project maintainer directly.
- **Response Time**: Maintainers will acknowledge security reports within 48 hours and work on a prompt patch.

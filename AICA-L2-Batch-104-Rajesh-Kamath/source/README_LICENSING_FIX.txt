DCF VALUATION PROFESSIONAL v3.0.6 - LICENSING FIX

1. This release uses a NEW synchronized Ed25519 keypair.
2. Old v3.0.5 reuse keys will NOT activate v3.0.6.
3. Generate a new key using the v3.0.6 PRIVATE generator.
4. The generator self-verifies every generated key.
5. The application now shows the exact failure reason:
   - malformed key
   - signature mismatch
   - wrong product/version
   - machine-code mismatch
6. The application removes accidental whitespace/newlines from pasted keys.
7. Keep the PRIVATE generator strictly private and never upload it to GitHub.

Workflow:
A. Run DCF Valuation Professional v3.0.6.
B. Copy the displayed Machine Code.
C. Run the v3.0.6 PRIVATE generator.
D. Paste Machine Code -> Generate Reuse Key.
E. Click Verify Generated Key. It must say VALID.
F. Copy Reuse Key.
G. Paste into v3.0.6 activation window.
H. Click Diagnose Key if desired, then Activate.

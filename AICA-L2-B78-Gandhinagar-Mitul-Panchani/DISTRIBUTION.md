# AI Memory Governance — Portable Windows Demo

AI Memory Governance is a capstone demonstration of controls around an AI memory store. It shows provenance, independent write checking, contradiction handling, bounded retrieval, cascading erasure, access control, and a tamper-evident audit trail. The demonstration uses synthetic scenario data. It runs locally and works in deterministic offline mode without an API key or internet connection.

## Run the demo

1. Copy `AIMemoryGovernance.exe` to any folder on a Windows computer.
2. Double-click it. No installation and no Python setup are needed.
3. Keep the console window open. Your browser should open automatically; if it does not, copy the localhost URL shown in the console into a browser.
4. Close the console window or press **Ctrl+C** there when you are finished.

The executable is unsigned. On its first launch, Microsoft Defender SmartScreen may say that Windows protected your PC because the publisher is unknown. If you received the file from a source you trust, choose **More info**, confirm that the app name is `AIMemoryGovernance.exe`, and then choose **Run anyway**. This warning is about the missing commercial code-signing certificate; it is not an installer prompt.

## Try the nine scenarios

In the browser, find **Scripted evidence** and select **Run all 9 scenarios**. Each scenario reports PASS or FAIL and adds visible audit evidence. You can also run scenarios individually, submit your own synthetic conversation turn, start a fresh session, inspect the memory store, verify the audit chain, and try the deliberate tamper test. Use **Reset clean database** to return to a fresh demonstration.

## Optional live AI providers

No API key is required. The default deterministic providers run all scenarios offline.

To use your own provider accounts, open **AI provider settings**, enter your own Gemini and/or Voyage key, check the Gemini model, and choose **Save settings**. Choose **Test connection** only when internet access is available; it makes one small, budgeted request to each configured provider. The panel reports whether a live provider or deterministic provider is resolved. Choose **Clear keys and return to offline** at any time.

Keys are stored in plain text on this computer. This demo is not a credential manager. Do not use a key you are unwilling to store in that form.

## Stored data and complete removal

The executable stores its database, settings, response cache, and daily usage record in:

`%LOCALAPPDATA%\AIMemoryGovernance`

To remove the demo completely:

1. Close the executable.
2. Delete `AIMemoryGovernance.exe` wherever you saved it.
3. In File Explorer, enter `%LOCALAPPDATA%` in the address bar and delete the `AIMemoryGovernance` folder.

This is a capstone demonstration of architectural alignment with DPDP principles. It is **not** a compliance product, certified tool, legal opinion, or substitute for a full privacy and security programme.

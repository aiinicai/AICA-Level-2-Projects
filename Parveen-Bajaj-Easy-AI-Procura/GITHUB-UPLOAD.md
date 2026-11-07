# Upload to the ICAI repository

Based on the supplied Github Repository Upload Guide.

1. Download and extract the ZIP. Keep the single folder `Parveen-Bajaj-Easy-AI-Procura`.
2. Sign in to GitHub and open https://github.com/aiinicai/AICA-Level-2-Projects
3. Click **Fork → Create fork**.
4. In your fork, click **Add file → Upload files**. Drag the extracted project folder, not the ZIP. Preserve its subfolders.
5. GitHub's website uploader accepts up to 100 files per upload. This submission has more than 100 files, so upload in batches, preserving folder paths. One option: first upload root documents/configuration and `public`, `supabase` and `drizzle`; then enter the project folder and upload `src` subfolders in smaller batches. If GitHub flattens a folder or rejects the upload, stop and use GitHub Desktop/local Git with folder-preserving upload instead.
6. Click **Commit changes** for each batch. Suggested message: `Add Parveen Bajaj - Easy AI Procura`.
7. Check that the project README, package.json, src and migration folders are present. Upload hidden `.gitignore`, `.env.example` and formatting configuration files too; the template has no credentials.
8. Click **Contribute → Open pull request**. Base repository: `aiinicai/AICA-Level-2-Projects`; comparison: your fork. Use the default branch shown by GitHub.
9. Title: `AICA Level 2 Project - Parveen Bajaj - Easy AI Procura`. In the description, summarise the LPO → GRN → invoice workflow and include the demo URL.
10. Submit the actual URL of your project folder in your fork to the course form. Add the pull-request URL in notes if available. Do not substitute only the demo app link. Once merged, the official repository's project-folder URL can also be shared.

The GitHub repository owner controls acceptance. No repository has been created or uploaded by preparing this ZIP.

## Note on this trimmed package (v2)

This package has 96 files so it fits GitHub's "under 100 files" upload limit in a single drag-and-drop. Removed files are not needed to run or evaluate the project:

- 37 unused interface component files (the app never imports them)
- 7 automated test files (see TEST-EVIDENCE.md for results)
- Auto-generated files (route tree, lock file) that regenerate on install/run
- Code-formatting config files

To run locally: `bun install` (or `npm install`), then `bun dev`. The route tree file regenerates automatically on first run.

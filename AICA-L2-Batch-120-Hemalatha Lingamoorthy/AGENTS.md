<!-- LOVABLE:BEGIN -->
> [!IMPORTANT]
> This project is connected to [Lovable](https://lovable.dev). Avoid rewriting
> published git history — force pushing, or rebasing/amending/squashing commits
> that are already pushed — as it rewrites history on Lovable's side and the
> user will likely lose their project history.
>
> Commits you push to the connected branch sync back to Lovable and show up in
> the editor, so keep the branch in a working state.
<!-- LOVABLE:END -->

## Project rules
- Speech analysis runs only in the `analyzeSpeech` server function via the Lovable AI Gateway; keys never reach the browser.
- Audio is converted on-device to 16 kHz mono WAV before upload, because iOS records mp4 and the gateway needs a uniform format.
- Sessions and audio live in IndexedDB on the device (src/lib/db.ts); there is no server-side storage by design (privacy).

# Recording the capstone video

Eight minutes, on a Windows 11 laptop, with your face and the technical
content both visible throughout. This is the practical companion to
`video_script.md`, which carries what to say.

---

## What the brief requires

> "Each participant is required to record a video showcasing their Capstone
> Project. This video must include both the Participant's facial expression
> and technical content. The video should be uploaded to YouTube unlisted
> mode or Google Drive, and the video link must be submitted through the same
> Google Form. Please ensure that the link is accessible to anyone."

Three things follow from that, and each one has failed submissions before:

1. **Face and content at the same time**, not a talking head followed by a
   screen recording. You need a camera bubble sitting over the screen capture.
2. **The link must open for a stranger.** Unlisted on YouTube, or
   *Anyone with the link — Viewer* on Drive. Not "restricted".
3. **Test it in an incognito window** before you submit the form.

---

## The one mistake that ruins the take

**Do not use PowerPoint's Presenter View if you are recording your whole
screen.** Presenter View shows your speaker notes — and if you are capturing
the entire screen, the evaluator sees them too. Every note in the deck,
including the delivery coaching.

Three ways round it, in order of preference:

| If you have | Do this |
| --- | --- |
| A second monitor | Presenter View on the laptop screen, slideshow on the second monitor, and record **only the second monitor** |
| One screen | Print the speaker notes, or open them on your phone or tablet, and run the slideshow normally |
| One screen, no printer | In PowerPoint: **Slide Show → Set Up Slide Show → Browsed by an individual (window)**. The slides run in a window; keep your notes in another window off to the side and capture only the slideshow window |

To print the notes: **File → Print → Full Page Slides → Notes Pages**.

---

## Before you press record

Twenty minutes of preparation saves an hour of re-takes.

**The machine**

- Close Outlook, Teams, WhatsApp and anything else that pops up. Turn on
  **Focus assist** (Windows key + N → Focus).
- Set the display to **1920 × 1080**. If your laptop is higher than that,
  drop it for the recording — YouTube compresses detail, and a 4K screen
  scaled down makes the application's figures unreadable.
- Keep display scaling at **125% or 150%**, not 100%. Larger text survives
  compression; small text turns to mush.
- Plug in the power adapter. Battery-saver throttling causes dropped frames.
- Clear your desktop, or set a plain wallpaper. A cluttered desktop is the
  first thing an evaluator sees.

**The application**

- Start AuditLens and **let it finish loading before you record** — either
  with `run-windows.bat`, or, if that file opens in Notepad instead of
  running, by typing `cmd` in the folder's address bar and then
  `.venv\Scripts\activate` followed by `python -m auditlens.launch`.
  The typed route is immune to file-association problems and looks better
  on camera. Click *Use the sample client* once as a rehearsal, then
  refresh the page so you can do it again live.
- Open a **second terminal window** and have `python -m pytest` typed but not
  yet entered, ready for slide 13.
- Open the repository in File Explorer or your editor, at the `prompts/`
  folder, ready for slide 12.
- Have the n8n canvas open in another browser tab.

**You**

- Sit with a window or lamp **in front of you**, not behind. Backlighting
  turns you into a silhouette.
- Camera at eye level. Stack the laptop on a few books if you need to.
- Use a headset or earphones with a microphone if you have one. Laptop
  microphones pick up the fan and the room.
- Do one full read-through out loud before recording. You will find two or
  three sentences that do not sit right in your mouth.

---

## Recording it

### Recommended: Clipchamp (already on your laptop)

Clipchamp ships with Windows 11, records screen and camera together as
picture-in-picture, and edits and exports in the same place — so you never
have to move files between tools.

1. Open **Clipchamp** from the Start menu. Create a new project.
2. Left toolbar → **Record & create** → **Screen and camera**.
3. Choose your microphone and camera. Your camera preview appears as a bubble.
4. Press the red record button, then choose what to capture:
   **Entire screen** for the demo, or a single **window** if you are using the
   windowed-slideshow trick above.
5. Speak. When you finish, **Stop sharing**, then **Save and edit** — the clip
   lands on the timeline.
6. Record the second take the same way. It appears as a second clip.

Recording is capped at 30 minutes per clip, which is ample. There is no limit
on the number of clips.

### If Clipchamp gives trouble: OBS Studio

Free, more control, slightly more setup. Add two **Sources**: *Display
Capture* for the screen and *Video Capture Device* for your webcam, then drag
the webcam small into a corner. Settings → Output → Recording Format **MP4**.
It records to a single file with the bubble already composited.

### If you would rather use something familiar: Zoom

Start a meeting with yourself, turn the camera on, **Share Screen**, then
**Record on this Computer**. Zoom puts your camera in the corner
automatically. Stop the recording and Zoom converts it to MP4 when you leave
the meeting. Check beforehand that
**Settings → Recording → Record video during screen sharing** is ticked.

---

## Record in two takes, not one

Do not attempt eight unbroken minutes. Split at the natural seam:

- **Take 1 — slides 1 to 5** (0:00 to 2:40). You and the deck. If you fluff a
  line, stop, pause for two seconds, and say the sentence again; you will cut
  the fluff out later.
- **Take 2 — slides 6 to 16** (2:40 to 8:00). The live demonstration, then the
  closing slides.

Then join them on the Clipchamp timeline, trim the dead air at the start and
end of each, and export.

If a take goes badly in the middle, do not start over. Pause, clap once (the
spike in the audio waveform makes the cut point obvious on the timeline), and
pick up from the last complete sentence.

---

## Export

- **1080p** is right. 720p makes the application's figures hard to read;
  4K wastes upload time for no gain.
- **MP4**. Do not export to a format that needs a converter.
- Aim for **under 500 MB**. Eight minutes at 1080p lands comfortably below it.
- **Watch it back once, all the way through, before uploading.** Listen for
  audio that drops out, and look for anything on screen you did not intend to
  show.

---

## Uploading and sharing the link

The brief asks for the video "uploaded to YouTube unlisted mode or Google
Drive", and for the link to be "accessible to anyone with the link". On
YouTube those are the same thing: **Unlisted means anyone with the link can
watch, without a Google account and without signing in.** Choosing Unlisted
satisfies both halves of the requirement at once.

### Before you start: which Google account?

**Use a personal `@gmail.com` account, not your firm's Workspace account.**

This matters more than it sounds. Where a Google Workspace domain is
administered — as a firm's own domain normally is — the administrator can
restrict external sharing, so Drive files default to *people in your
organisation only*, and the option to share with anyone outside may be
greyed out or absent entirely. YouTube uploading can also be turned off for
a Workspace account. Either way the evaluator would open your link and be
asked to sign in, which is the same as not submitting it.

If you must use the firm account, test the link in an incognito window
before you rely on it, and be ready to switch.

### Route 1 — YouTube (recommended)

1. Sign in at **youtube.com** with the account you intend to use.
2. **Create → Upload video**, and select your MP4.
3. **Details.** Title it something the evaluator can identify at a glance:
   `AuditLens — AICA Level 2 Capstone — CA Rajendra Bagade`.
4. **Audience.** Choose **"No, it's not made for kids."** This step is
   compulsory; the upload will not proceed without it.
5. **Visibility.** Choose **Unlisted**.
   **Not Private.** A private video is visible only to you and to specific
   email addresses you name one by one — the evaluator opening it would be
   refused. This is the single most common submission failure.
6. **Publish**, then copy the link from the **Share** button — not from your
   browser's address bar, which may carry your own session parameters.

A caution on length: YouTube caps uploads at **15 minutes** until the account
is verified by phone. Your video is around eight minutes, so this will not
bite — but if a take runs long, verify the account first
(**youtube.com/verify**) rather than trimming content you need.

### Route 2 — Google Drive

1. Upload the MP4 to Drive.
2. Right-click the file → **Share** → **Share**.
3. Under **General access**, change *Restricted* to
   **Anyone with the link**.
4. Confirm the role beside it reads **Viewer**.
5. **Copy link**, then **Done**.

If *Anyone with the link* is unavailable or reverts to your organisation, the
domain's administrator has restricted external sharing. Use YouTube instead;
do not spend the evening arguing with the setting.

### Then verify it, every time

Open a **private / incognito window** — `Ctrl + Shift + N` in Chrome or Edge —
paste the link, and watch the first ten seconds.

- It plays without asking anything: correct, submit it.
- It asks you to sign in, or says "Access denied" or "Video unavailable":
  the sharing setting is wrong. Fix it and test again.

Incognito matters because your ordinary browser is already signed in as you,
so a badly-shared video will play perfectly for you and for nobody else.

### Submitting

Paste the tested link into the Google Form, alongside your GitHub repository
URL. Submit the form once, and keep the confirmation.

## Pre-flight checklist

Print this page and tick as you go.

- [ ] Notifications silenced, Focus assist on
- [ ] Display at 1920 × 1080, scaling 125–150%
- [ ] Power adapter connected
- [ ] Desktop tidy
- [ ] AuditLens running, sample client rehearsed once, page refreshed
- [ ] Second terminal open with `python -m pytest` typed, not entered
- [ ] `prompts/` folder open and ready
- [ ] n8n canvas open in a tab
- [ ] Speaker notes printed or on a second device — **not** on the recorded screen
- [ ] Camera at eye level, light in front of you
- [ ] Microphone tested — record ten seconds and play it back
- [ ] Read the script aloud once, end to end

After recording:

- [ ] Watched the whole thing back
- [ ] Face visible throughout
- [ ] No speaker notes, email, or client information visible at any point
- [ ] Exported as 1080p MP4, under 500 MB
- [ ] Uploaded from a personal Google account, not the firm's Workspace account
- [ ] Visibility set to **Unlisted** — not Private — or, on Drive,
      **Anyone with the link · Viewer**
- [ ] Link copied from the **Share** button, not the address bar
- [ ] Link opened and played in an **incognito** window without any sign-in
- [ ] GitHub repository pushed and public
- [ ] ZIP assembled per Annexure D
- [ ] Google Form submitted

---

Sources for the tool guidance:
[Clipchamp — how to screen and camera record](https://clipchamp.com/en/blog/screen-and-camera-record/) ·
[Clipchamp — screen recording on Windows 11](https://clipchamp.com/en/blog/how-to-screen-record-windows/)

# Sync Screen Recorder (Chrome Extension)

Records screen, microphone, and/or camera — any one, two, or all three — and
keeps them synced in a single downloadable .webm file.

## Install (unpacked, for development/testing)

1. Unzip this file.
2. Go to `chrome://extensions`.
3. Turn on "Developer mode" (top-right toggle).
4. Click "Load unpacked" and select the unzipped `screen-recorder-ext` folder.
5. Click the extension icon in the toolbar.

## Use

1. Click the extension icon.
2. Check any combination of Screen, Microphone, Camera.
3. Click "Start Recording" — this opens a new tab where Chrome will ask you
   to grant each permission you selected (screen picker, mic, camera).
4. Recording starts automatically once permissions are granted. Camera (if
   selected) appears as a small picture-in-picture overlay on top of the
   screen recording; if only camera is selected, it fills the whole frame;
   if only mic is selected, it's an audio-only recording.
5. Click "Stop Recording" (or use Chrome's own "Stop sharing" bar) when done.
6. Click "Download Recording" to save the .webm file.

## How sync works

All selected video sources are drawn onto one `<canvas>` inside a single
`requestAnimationFrame` loop, and `canvas.captureStream()` is recorded — so
screen + camera share one video clock. All selected audio sources are
routed through one shared `AudioContext` into a single
`MediaStreamDestination` — so their audio shares one sample clock. Both are
recorded together with a single `MediaRecorder`, which is what keeps
video and audio in sync in the final file.

## Notes

- This is an MV3 unpacked extension meant for local/dev use. To publish it
  on the Chrome Web Store you'd add a privacy policy and go through Google's
  review (screen/mic/camera-capturing extensions get extra scrutiny).
- No data leaves the browser — everything is recorded and saved locally.

## v1.2: Pop Out floating window

The recorder tab now has a **Pop Out (keep visible everywhere)** button.
Click it once (right when the tab opens, or any time after) and the whole
recorder panel — preview canvas, timer, Stop button — moves into a small
always-on-top floating window (the browser's Document Picture-in-Picture
window). That floating window stays visible on top of whatever else you're
doing — other apps, other browser windows, even other virtual
desktops/"Spaces" — so you can keep working while recording continues, and
you can hit Stop from the floating window itself without ever switching
back to the original tab.

Click **Pop back in** (same button) to return the panel to the tab, or just
close the floating window.

Needs Chrome 116+ (or another Chromium browser with the Document
Picture-in-Picture API). If it's not supported, the button is disabled and
recording still works — you'll just want to keep the tab itself visible for
best results in screen+camera mode (see below).

## v1.1 fix: recording used to freeze mid-way

Earlier versions could produce a recording where video froze for a long
stretch (audio kept going fine) if you switched away from the recorder tab
while recording. Cause: the video was drawn onto a canvas inside a
`requestAnimationFrame` loop, and Chrome fully pauses `requestAnimationFrame`
in tabs that are hidden/backgrounded — so the canvas (and the recording)
stopped updating until you switched back.

Fixes in this version:
- If only **one** visual source is selected (screen-only, or camera-only),
  the raw stream is now recorded directly with no canvas and no draw loop
  at all — immune to the freeze.
- If **both** screen and camera are selected, a canvas is still needed (to
  place the camera as a PiP overlay), but the draw loop now runs on
  `setInterval` instead of `requestAnimationFrame`. Chrome throttles
  `setInterval` in background tabs instead of fully pausing it, so frame
  rate can dip but it won't freeze for minutes. The page also shows a
  warning banner if you switch away while in this combined mode, and
  requests a screen wake lock to discourage the tab from being throttled.
- For best results with screen + camera together, keep the recorder tab
  visible (e.g. resized to a corner of your screen, or on a second
  monitor) instead of switching fully away from it.

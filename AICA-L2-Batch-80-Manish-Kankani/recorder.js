const statusEl = document.getElementById('status');
const errorEl = document.getElementById('error');
const hintEl = document.getElementById('hint');
const timerEl = document.getElementById('timer');
const stopBtn = document.getElementById('stopBtn');
const popoutBtn = document.getElementById('popoutBtn');
const downloadBtn = document.getElementById('downloadBtn');
const panelEl = document.getElementById('panel');
const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
const screenVideo = document.getElementById('screenVideo');
const cameraVideo = document.getElementById('cameraVideo');

let mediaRecorder = null;
let recordedChunks = [];
let rafId = null;
let audioContext = null;
let stopAllTracks = () => {};
let startTime = null;
let timerInterval = null;
let wakeLock = null;
let pipWindow = null;

function showVisibilityWarning() {
  setError('This tab is in the background. Click "Pop Out" below to keep the recorder visible on top of other apps/desktops — that avoids the frame-rate drop Chrome applies to hidden tabs.');
}
function hideVisibilityWarning() {
  setError('');
}
function setHint(text) {
  hintEl.textContent = text;
}

// --- Picture-in-Picture pop-out ---
// Uses the Document Picture-in-Picture API to move the whole recorder
// panel (preview canvas, timer, Stop button) into a small always-on-top
// floating window. That window stays visible no matter which app, browser
// tab, or virtual desktop you switch to — which both solves the "recording
// freezes when I switch away" problem and lets you control Stop/Download
// without switching back to this tab at all.
async function togglePopout() {
  if (!('documentPictureInPicture' in window)) {
    setError('This browser does not support popping out a floating window (needs Chrome 116+ or an equivalent Chromium browser). Keep this tab visible instead while recording.');
    return;
  }

  if (pipWindow) {
    pipWindow.close(); // triggers the 'pagehide' handler below to clean up
    return;
  }

  try {
    pipWindow = await documentPictureInPicture.requestWindow({ width: 380, height: 340 });
  } catch (err) {
    setError(`Could not open the floating window: ${err.message}`);
    return;
  }

  // Bring the styling over so the panel renders correctly inside the PiP window.
  const styleClone = document.getElementById('recorderStyles').cloneNode(true);
  pipWindow.document.head.appendChild(styleClone);
  pipWindow.document.body.style.margin = '0';
  pipWindow.document.body.style.background = '#111214';
  pipWindow.document.body.appendChild(panelEl); // moves the live canvas/controls, not a copy

  popoutBtn.textContent = 'Pop back in';
  popoutBtn.classList.add('active');
  hideVisibilityWarning();
  setHint('Floating window is on — it stays on top while you switch apps, windows, or desktops, and recording keeps going.');

  pipWindow.addEventListener('pagehide', () => {
    // Fires whether the user closed the floating window or clicked "Pop back in".
    document.body.appendChild(panelEl);
    pipWindow = null;
    popoutBtn.textContent = 'Pop Out (keep visible everywhere)';
    popoutBtn.classList.remove('active');
    setHint('');
  });
}

popoutBtn.addEventListener('click', togglePopout);
if (!('documentPictureInPicture' in window)) {
  popoutBtn.disabled = true;
  popoutBtn.title = 'Needs Chrome 116+ (or an equivalent Chromium browser)';
} else {
  popoutBtn.disabled = false;
}

async function requestWakeLock() {
  try {
    if ('wakeLock' in navigator) {
      wakeLock = await navigator.wakeLock.request('screen');
    }
  } catch (e) {
    // Non-fatal: wake lock isn't available/granted in every context.
  }
}

function setStatus(text, recording = false) {
  statusEl.textContent = text;
  statusEl.classList.toggle('recording', recording);
}

function setError(text) {
  errorEl.textContent = text;
}

function formatTime(ms) {
  const totalSec = Math.floor(ms / 1000);
  const m = String(Math.floor(totalSec / 60)).padStart(2, '0');
  const s = String(totalSec % 60).padStart(2, '0');
  return `${m}:${s}`;
}

async function main() {
  const { recorderOptions } = await chrome.storage.local.get('recorderOptions');
  const options = recorderOptions || { screen: true, mic: false, camera: false };

  if (!options.screen && !options.mic && !options.camera) {
    setStatus('No sources selected.');
    setError('Go back to the extension popup and pick at least one of Screen, Microphone, or Camera.');
    return;
  }

  let screenStream = null;
  let micStream = null;
  let cameraStream = null;

  try {
    if (options.screen) {
      setStatus('Requesting screen share permission…');
      screenStream = await navigator.mediaDevices.getDisplayMedia({
        video: { frameRate: 30 },
        audio: true // system/tab audio, if the user allows it in the picker
      });
    }

    if (options.camera) {
      setStatus('Requesting camera permission…');
      cameraStream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480 }
      });
    }

    if (options.mic) {
      setStatus('Requesting microphone permission…');
      micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    }
  } catch (err) {
    setStatus('Permission denied or cancelled.');
    setError(`Could not start recording: ${err.message}`);
    return;
  }

  // --- Video handling ---
  // IMPORTANT: requestAnimationFrame is paused by Chrome when this tab is
  // hidden/backgrounded (e.g. the user switches to another window while
  // screen-sharing). That used to freeze the recording for as long as the
  // tab stayed backgrounded, even though audio kept flowing fine. Two fixes:
  //   1. When only ONE visual source is selected (screen-only or
  //      camera-only), skip the canvas entirely and record that raw stream
  //      directly. There is no draw loop at all, so there is nothing to
  //      freeze — this is the common case and is now fully immune to the bug.
  //   2. When BOTH screen + camera are selected, compositing onto a canvas
  //      is unavoidable (to place the camera as a PiP overlay). That loop
  //      now runs on setInterval instead of requestAnimationFrame, because
  //      Chrome throttles setInterval in background tabs (down to ~1/sec)
  //      instead of fully pausing it like rAF — so it degrades gracefully
  //      instead of freezing for minutes. The UI also warns the user to
  //      keep the tab visible for best quality in this combined mode.
  let canvasStream;
  const needsCompositing = Boolean(screenStream && cameraStream);
  const hasVideo = Boolean(screenStream || cameraStream);

  if (needsCompositing) {
    screenVideo.srcObject = screenStream;
    await screenVideo.play().catch(() => {});
    cameraVideo.srcObject = cameraStream;
    await cameraVideo.play().catch(() => {});

    const sizeFromVideo = () => {
      if (screenVideo.videoWidth) {
        canvas.width = screenVideo.videoWidth;
        canvas.height = screenVideo.videoHeight;
      }
    };
    screenVideo.addEventListener('loadedmetadata', sizeFromVideo, { once: true });
    sizeFromVideo();

    const draw = () => {
      ctx.drawImage(screenVideo, 0, 0, canvas.width, canvas.height);
      // Picture-in-picture overlay, bottom-right corner.
      const pipW = Math.round(canvas.width * 0.22);
      const pipH = Math.round(pipW * (cameraVideo.videoHeight / cameraVideo.videoWidth || 0.75));
      const margin = Math.round(canvas.width * 0.02);
      const x = canvas.width - pipW - margin;
      const y = canvas.height - pipH - margin;
      ctx.save();
      ctx.strokeStyle = 'rgba(255,255,255,0.8)';
      ctx.lineWidth = 3;
      ctx.drawImage(cameraVideo, x, y, pipW, pipH);
      ctx.strokeRect(x, y, pipW, pipH);
      ctx.restore();
    };
    rafId = setInterval(draw, 1000 / 30);

    canvasStream = canvas.captureStream(30);

    if (document.hidden) showVisibilityWarning();
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) showVisibilityWarning();
      else hideVisibilityWarning();
    });
  } else if (hasVideo) {
    // Only one visual source selected — record it directly, no canvas.
    const rawStream = screenStream || cameraStream;
    canvasStream = new MediaStream(rawStream.getVideoTracks());
  } else {
    // Audio-only recording (mic only, no screen/camera selected).
    canvasStream = new MediaStream();
  }

  // --- Combine all audio tracks (screen/tab audio + mic) onto one shared
  // AudioContext clock so the audio stays sample-accurate and in sync with
  // itself and with the video draw loop above.
  const audioTracks = [];
  if (screenStream) audioTracks.push(...screenStream.getAudioTracks());
  if (micStream) audioTracks.push(...micStream.getAudioTracks());

  if (audioTracks.length > 0) {
    audioContext = new AudioContext();
    const destination = audioContext.createMediaStreamDestination();
    audioTracks.forEach((track) => {
      const src = audioContext.createMediaStreamSource(new MediaStream([track]));
      src.connect(destination);
    });
    destination.stream.getAudioTracks().forEach((t) => canvasStream.addTrack(t));
  }

  // --- Recorder setup ---
  const mimeCandidates = [
    'video/webm;codecs=vp9,opus',
    'video/webm;codecs=vp8,opus',
    'video/webm',
    'audio/webm'
  ];
  const mimeType = mimeCandidates.find((t) => MediaRecorder.isTypeSupported(t)) || '';

  recordedChunks = [];
  mediaRecorder = new MediaRecorder(canvasStream, mimeType ? { mimeType } : undefined);
  mediaRecorder.ondataavailable = (e) => {
    if (e.data && e.data.size > 0) recordedChunks.push(e.data);
  };
  mediaRecorder.onstop = () => {
    const blob = new Blob(recordedChunks, { type: mimeType.startsWith('audio') ? 'audio/webm' : 'video/webm' });
    const url = URL.createObjectURL(blob);
    downloadBtn.href = url;
    downloadBtn.download = mimeType.startsWith('audio') ? 'recording.webm' : 'recording.webm';
    downloadBtn.style.display = 'inline-block';
    downloadBtn.textContent = 'Download Recording';
    setStatus('Recording finished. Ready to download.');
  };

  mediaRecorder.start(250); // gather chunks periodically
  requestWakeLock();
  startTime = Date.now();
  timerInterval = setInterval(() => {
    timerEl.textContent = formatTime(Date.now() - startTime);
  }, 250);

  setStatus('Recording…', true);
  stopBtn.disabled = false;

  stopAllTracks = () => {
    [screenStream, micStream, cameraStream].forEach((stream) => {
      if (stream) stream.getTracks().forEach((t) => t.stop());
    });
  };

  // If the user stops screen-sharing via Chrome's own "Stop sharing" bar,
  // end the recording too.
  if (screenStream) {
    screenStream.getVideoTracks()[0].addEventListener('ended', () => {
      if (mediaRecorder && mediaRecorder.state !== 'inactive') stopRecording();
    });
  }
}

function stopRecording() {
  stopBtn.disabled = true;
  if (rafId) clearInterval(rafId); // draw loop is a setInterval id now, not rAF
  if (timerInterval) clearInterval(timerInterval);
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop();
  }
  stopAllTracks();
  if (audioContext) audioContext.close();
  if (wakeLock) wakeLock.release().catch(() => {});
  setStatus('Stopping…');
}

stopBtn.addEventListener('click', stopRecording);

main();

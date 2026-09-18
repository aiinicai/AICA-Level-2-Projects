// Minimal background service worker.
// The extension does not need persistent background logic; recording
// happens entirely inside the recorder.html tab so it can request
// getDisplayMedia/getUserMedia with a user gesture and keep all
// streams on one page (needed to keep them in sync).

chrome.runtime.onInstalled.addListener(() => {
  console.log('Sync Screen Recorder installed.');
});

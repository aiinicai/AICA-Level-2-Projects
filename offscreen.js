/* Offscreen helper: the service worker cannot create blob URLs, so it asks this page to. */
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (!msg || msg.target !== 'offscreen') return false;
  if (msg.type === 'makeUrl') {
    const blob = new Blob([msg.content], { type: msg.mime || 'application/octet-stream' });
    sendResponse({ url: URL.createObjectURL(blob) });
  } else if (msg.type === 'revoke') {
    // Give Chrome a moment in case it is still reading the blob.
    setTimeout(() => URL.revokeObjectURL(msg.url), 5000);
    sendResponse({ ok: true });
  }
  return false;
});

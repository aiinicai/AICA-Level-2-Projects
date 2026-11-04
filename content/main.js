/* Content-script entry point: answers the popup and owns the running export job. */
(function (g) {
  'use strict';
  const W = g.WDRE;
  const D = W.dom;
  let job = null;

  const busy = () => job && (job.status.state === 'running' || job.status.state === 'review');

  async function onMessage(msg) {
    switch (msg.type) {
      case 'ping':
        return {
          ok: true,
          version: W.VERSION,
          ready: D.isReady(),
          currentChat: D.currentChatTitle(),
          busy: !!busy(),
          jobId: job ? job.status.jobId : null,
          browserZone: W.tz.browserZone(),
        };
      case 'listChats': {
        if (busy()) return { ok: false, error: 'An export is running.' };
        const names = await D.listAllChats();
        return { ok: true, names, currentChat: D.currentChatTitle() };
      }
      case 'start': {
        if (busy()) return { ok: false, error: 'An export is already running in this tab.' };
        if (!D.isReady()) return { ok: false, error: 'WhatsApp Web is not ready yet. Wait until your chats are visible.' };
        job = new W.Job(msg.options);
        job.run();
        return { ok: true, jobId: job.status.jobId };
      }
      case 'cancel':
        if (job) job.cancel();
        return { ok: true };
      case 'reviewSubmit':
        if (job) job.submitReview(msg.renames, msg.selected);
        return { ok: true };
      case 'diagnose':
        return { ok: true, report: await D.diagnose() };
      case 'hideOverlay':
        if (!busy() && W.overlay) W.overlay.hide();
        return { ok: true };
      default:
        return undefined;
    }
  }

  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (!msg || msg.to !== 'content') return false;
    onMessage(msg).then(sendResponse, (e) => sendResponse({ ok: false, error: String((e && e.message) || e) }));
    return true;
  });

  document.addEventListener('visibilitychange', () => {
    if (busy()) job.publish(true);
  });
})(globalThis);

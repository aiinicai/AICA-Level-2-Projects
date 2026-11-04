/* Export screen. The export itself runs in the WhatsApp tab; this popup only starts it,
   shows progress (read from chrome.storage) and collects attachment renames. */
(function () {
  'use strict';
  const W = window.WDRE;
  const $ = (id) => document.getElementById(id);
  const esc = W.escapeHtml;

  let tab = null;
  let ping = null;
  let settings = {};
  let status = null;
  let chatNames = [];
  let allNames = null;
  const selected = new Set();
  let renderedReviewKey = '';
  let reviewItems = [];

  // ------------------------------------------------------------ plumbing
  async function findTab() {
    const tabs = await chrome.tabs.query({ url: 'https://web.whatsapp.com/*' });
    if (!tabs.length) return null;
    const [active] = await chrome.tabs.query({ active: true, currentWindow: true });
    const recent = tabs.slice().sort((a, b) => (b.lastAccessed || 0) - (a.lastAccessed || 0));
    return tabs.find((t) => active && t.id === active.id) || recent[0];
  }

  async function toContent(msg) {
    if (!tab) throw new Error('WhatsApp Web is not open.');
    return chrome.tabs.sendMessage(tab.id, Object.assign({ to: 'content' }, msg));
  }

  const saveSettings = () => chrome.storage.local.set({ wdreSettings: settings });
  const scope = () => document.querySelector('input[name="scope"]:checked').value;
  const mode = () => document.querySelector('input[name="mode"]:checked').value;

  // ------------------------------------------------------------ connection
  function renderConn() {
    const c = $('conn');
    if (!tab) {
      c.innerHTML = `<div class="box"><span class="bad">WhatsApp Web is not open in this browser.</span> <button id="openWa" class="small">Open WhatsApp Web</button></div>`;
      $('openWa').onclick = () => chrome.tabs.create({ url: 'https://web.whatsapp.com/' });
      return;
    }
    if (!ping) {
      c.innerHTML = `<div class="box"><span class="bad">Can't reach the WhatsApp tab.</span> Refresh it once after installing the extension. <button id="reloadWa" class="small">Refresh WhatsApp Web</button></div>`;
      $('reloadWa').onclick = async () => {
        await chrome.tabs.reload(tab.id);
        window.close();
      };
      return;
    }
    if (ping.version !== W.VERSION) {
      c.innerHTML = `<div class="box"><span class="bad">The WhatsApp tab is still running an older copy of this extension (v${esc(ping.version || '?')}).</span> Refresh it to load v${esc(W.VERSION)}. <button id="reloadWa" class="small">Refresh WhatsApp Web</button></div>`;
      $('reloadWa').onclick = async () => {
        await chrome.tabs.reload(tab.id);
        window.close();
      };
      return;
    }
    if (!ping.ready) {
      c.innerHTML = `<div class="box"><span class="bad">WhatsApp Web is still loading or not signed in.</span> Wait until your chats appear, then reopen this window.</div>`;
      return;
    }
    c.innerHTML = `<div class="box"><span class="ok">● Connected to WhatsApp Web</span>${ping.browserZone ? ` <span class="muted">· computer time zone ${esc(ping.browserZone)}</span>` : ''}</div>`;
  }

  // ------------------------------------------------------------ form
  function fillTz() {
    const sel = $('tz');
    for (const z of W.tz.list()) {
      const o = document.createElement('option');
      o.value = z;
      o.textContent = z === 'Asia/Dubai' ? 'Asia/Dubai (UAE)' : z.replace(/_/g, ' ');
      sel.appendChild(o);
    }
    sel.value = settings.tz && W.tz.isValid(settings.tz) ? settings.tz : 'Asia/Dubai';
  }

  function namesForScope() {
    const s = scope();
    if (s === 'current') return ping && ping.currentChat ? [ping.currentChat] : [];
    if (s === 'selected') return chatNames.length ? chatNames.filter((n) => selected.has(n)) : Array.from(selected);
    return allNames || [];
  }

  function rangeLabel() {
    const f = $('from').value;
    const t = $('to').value;
    if (!f || !t) return '<date range>';
    return f === t ? f : `${f} to ${t}`;
  }

  function updateSummary() {
    const s = scope();
    $('pickerBox').classList.toggle('hidden', s !== 'selected');
    $('allBox').classList.toggle('hidden', s !== 'all');
    $('currentName').textContent = ping && ping.currentChat ? ping.currentChat : 'no chat open';
    const names = namesForScope();
    let html;
    if (s === 'all' && !allNames) html = 'Click <b>Load chat list</b> to see which chats will be exported.';
    else if (!names.length) html = s === 'current' ? 'Open a chat in WhatsApp Web first.' : 'No chats selected yet.';
    else {
      const shown = names.slice(0, 40).map((n) => `<span class="pill" dir="auto">${esc(n)}</span>`).join(' ');
      html = `<b>${names.length}</b> chat${names.length > 1 ? 's' : ''}: ${shown}${names.length > 40 ? ` … and ${names.length - 40} more` : ''}`;
    }
    const m = { both: 'messages and media', messages: 'messages only', media: 'media only' }[mode()];
    const f = currentFilter();
    const fText = mode() !== 'messages' && !W.isDefaultFilter(f) ? ` · attachments: ${W.describeFilter(f)}` : '';
    html += `<div style="margin-top:4px">${esc(rangeLabel())} · ${esc($('tz').value)} · ${esc(m)}${esc(fText)}</div>`;
    $('summary').innerHTML = html;
    $('attFilterBox').classList.toggle('hidden', mode() === 'messages');
    $('filterNote').textContent = $('review').checked ? 'pre-ticks the list you review' : 'applied automatically';
    const client = $('client').value.trim();
    const first = names[0] ? W.cleanSegment(names[0], 60, 'Chat') : '<chat name>';
    $('pathPreview').textContent =
      `Downloads/WhatsApp Exports/${client ? W.cleanSegment(client, 60, 'Client') + '/' : ''}${first}/${rangeLabel()}/` +
      (mode() === 'media' ? '  →  Index.html, Index.csv, Media/' : mode() === 'messages' ? '  →  Transcript.html, Index.html, Index.csv' : '  →  Transcript.html, Index.html, Index.csv, Media/');
    $('selCount').textContent = `${selected.size} selected`;
  }

  // ------------------------------------------------------------ attachment filters
  function renderTypeList() {
    const chosen = settings.attFilter && Array.isArray(settings.attFilter.types) ? new Set(settings.attFilter.types) : null;
    $('typeList').innerHTML = W.FILE_TYPES.map(
      (t) => `<label><input type="checkbox" data-type="${t.key}" ${!chosen || chosen.has(t.key) ? 'checked' : ''}> ${esc(t.label)}</label>`
    ).join('');
    const dir = (settings.attFilter && settings.attFilter.direction) || 'all';
    const r = document.querySelector(`input[name="dir"][value="${dir}"]`);
    if (r) r.checked = true;
  }

  // { direction, types }: types is null when every type is ticked.
  function currentFilter() {
    const boxes = Array.from($('typeList').querySelectorAll('input[data-type]'));
    const ticked = boxes.filter((b) => b.checked).map((b) => b.dataset.type);
    const dirEl = document.querySelector('input[name="dir"]:checked');
    return { direction: dirEl ? dirEl.value : 'all', types: ticked.length === boxes.length ? null : ticked };
  }

  function saveFilter() {
    settings.attFilter = currentFilter();
    saveSettings();
    updateSummary();
  }

  function renderChatList() {
    const box = $('chatList');
    const f = W.norm($('chatFilter').value).toLowerCase();
    const list = chatNames.filter((n) => !f || W.norm(n).toLowerCase().includes(f));
    if (!chatNames.length) {
      box.innerHTML = `<div class="empty">Click “Load chat list”. WhatsApp's chat list will scroll briefly while it is read.</div>`;
      return;
    }
    box.innerHTML = list
      .map((n, i) => `<label><input type="checkbox" data-i="${i}" ${selected.has(n) ? 'checked' : ''}><span dir="auto">${esc(n)}</span></label>`)
      .join('') || `<div class="empty">No chats match.</div>`;
    box.querySelectorAll('input[type=checkbox]').forEach((cb) => {
      cb.onchange = () => {
        const n = list[+cb.dataset.i];
        if (cb.checked) selected.add(n);
        else selected.delete(n);
        settings.selectedChats = Array.from(selected);
        saveSettings();
        updateSummary();
      };
    });
  }

  async function loadChats(target) {
    const btn = target === 'all' ? $('loadAll') : $('loadChats');
    btn.disabled = true;
    btn.textContent = 'Reading chat list…';
    try {
      const res = await toContent({ type: 'listChats' });
      if (!res || !res.ok) throw new Error((res && res.error) || 'No response');
      chatNames = res.names;
      allNames = res.names.slice();
      $('allCount').textContent = `${allNames.length} chats found`;
      renderChatList();
    } catch (e) {
      showFormError('Could not read the chat list: ' + e.message);
    } finally {
      btn.disabled = false;
      btn.textContent = 'Reload chat list';
      updateSummary();
    }
  }

  function showFormError(t) {
    const e = $('formError');
    e.textContent = t;
    e.classList.toggle('hidden', !t);
  }

  async function start() {
    showFormError('');
    const from = $('from').value;
    const to = $('to').value;
    if (!from || !to) return showFormError('Choose both a From and a To date.');
    if (from > to) return showFormError('The From date is after the To date.');
    if (!ping || !ping.ready) return showFormError('WhatsApp Web is not connected.');
    const s = scope();
    const names = namesForScope();
    if (s === 'all' && !allNames) return showFormError('Load the chat list first so you can see what will be exported.');
    if (!names.length) return showFormError(s === 'current' ? 'Open a chat in WhatsApp Web first.' : 'Select at least one chat.');
    const attFilter = currentFilter();
    if (mode() !== 'messages' && attFilter.types && !attFilter.types.length) return showFormError('Tick at least one file type under "Attachments to save".');
    const options = {
      scope: s,
      chats: s === 'current' ? [] : names,
      from,
      to,
      tz: $('tz').value,
      mode: mode(),
      client: $('client').value.trim(),
      review: $('review').checked && mode() !== 'messages',
      dateOrder: $('dateOrder').value,
      attFilter: W.isDefaultFilter(attFilter) ? null : attFilter,
    };
    Object.assign(settings, { tz: options.tz, mode: options.mode, client: options.client, review: $('review').checked, dateOrder: options.dateOrder, scope: s, tabId: tab.id, attFilter });
    await saveSettings();
    $('startBtn').disabled = true;
    try {
      const res = await toContent({ type: 'start', options });
      if (!res || !res.ok) throw new Error((res && res.error) || 'No response from WhatsApp tab');
      status = {
        jobId: res.jobId,
        state: 'running',
        rangeLabel: options.from === options.to ? options.from : `${options.from} to ${options.to}`,
        options,
        chats: [],
        current: -1,
        totals: { messages: 0, saved: 0, skipped: 0, failed: 0 },
        log: ['Starting…'],
      };
      showProgress();
    } catch (e) {
      showFormError(e.message);
    } finally {
      $('startBtn').disabled = false;
    }
  }

  // ------------------------------------------------------------ progress
  function showForm() {
    $('formView').classList.remove('hidden');
    $('progressView').classList.add('hidden');
    updateSummary();
  }

  function showProgress() {
    $('formView').classList.add('hidden');
    $('progressView').classList.remove('hidden');
    renderProgress();
  }

  const STATE_TITLE = {
    running: 'Exporting…',
    review: 'Review attachment names',
    done: 'Export finished',
    cancelled: 'Export cancelled',
    error: 'Export stopped',
    interrupted: 'Export interrupted',
  };

  function renderProgress() {
    if (!status) return;
    const s = status;
    const live = s.state === 'running' || s.state === 'review';
    $('pTitle').textContent = STATE_TITLE[s.state] || s.state;
    $('pRange').textContent = `${s.rangeLabel || ''} · ${(s.options && s.options.tz) || ''}`;
    const warn = [s.blockWarning, s.warning].filter(Boolean).join(' ');
    $('pWarning').textContent = warn;
    $('pWarning').classList.toggle('hidden', !warn);
    $('pChats').innerHTML =
      (s.chats || [])
        .map((c, i) => {
          const badge = c.state === 'running' ? 'in progress' : c.state;
          const att = c.att || { total: 0, saved: 0, skipped: 0, failed: 0 };
          return `<div class="chat"><div><span class="name" dir="auto">${esc(c.name)}</span><span class="badge ${esc(c.state)}">${esc(badge)}</span></div>
            <div class="phase">${esc(c.phase || '')}</div>
            ${c.state !== 'pending' ? `<div class="counts">Messages in range: ${c.messagesInRange || 0} · Files saved ${att.saved}/${att.total}${att.skipped ? ` · skipped ${att.skipped}` : ''}${att.failed ? ` · failed ${att.failed}` : ''}</div>` : ''}
            ${c.coverage === 'partial' ? `<div class="warn">Partial: history only available back to <b>${esc(c.earliest || 'unknown')}</b>. ${esc(c.coverageNote || '')}</div>` : ''}
            ${i === s.current && live ? '' : ''}</div>`;
        })
        .join('') || `<div class="muted">${esc((s.log && s.log[s.log.length - 1]) || 'Starting…')}</div>`;
    const t = s.totals || {};
    $('pTotals').innerHTML = `<div><b>${t.messages || 0}</b><span>messages</span></div><div><b>${t.saved || 0}</b><span>files saved</span></div><div><b>${t.skipped || 0}</b><span>skipped</span></div><div><b>${t.failed || 0}</b><span>failed</span></div>`;
    $('pError').textContent = s.error || '';
    $('pError').classList.toggle('hidden', !s.error);
    $('pLog').textContent = (s.log || []).join('\n');
    $('cancelBtn').classList.toggle('hidden', !live);
    $('openFolder').classList.toggle('hidden', live);
    $('newExport').classList.toggle('hidden', live);
    const firstFile = (s.chats || []).find((c) => c.transcriptId || c.indexId);
    $('showTranscript').classList.toggle('hidden', live || !(firstFile || s.summaryId));
    renderReview();
  }

  function renderReview() {
    const r = status && status.review;
    $('reviewBox').classList.toggle('hidden', !r);
    if (!r) {
      renderedReviewKey = '';
      return;
    }
    const key = `${status.jobId}:${r.chatIndex}`;
    if (key === renderedReviewKey) return; // don't wipe what the user is typing
    renderedReviewKey = key;
    $('rChat').textContent = r.chatName;
    reviewItems = r.items;
    const f = r.filter || { direction: 'all', types: null };

    // Sent / received filter with counts.
    const nIn = r.items.filter((it) => !it.fromMe).length;
    const nOut = r.items.length - nIn;
    $('rDir').innerHTML = [
      ['all', `All (${r.items.length})`],
      ['received', `Received (${nIn})`],
      ['sent', `Sent (${nOut})`],
    ]
      .map(([v, t]) => `<label><input type="radio" name="rdir" value="${v}" ${(f.direction || 'all') === v ? 'checked' : ''}> ${esc(t)}</label>`)
      .join('');

    // File-type filter: only the types present in this chat, with counts.
    const counts = {};
    for (const it of r.items) counts[it.typeKey] = (counts[it.typeKey] || 0) + 1;
    $('rTypes').innerHTML = W.FILE_TYPES.filter((t) => counts[t.key])
      .map(
        (t) =>
          `<label><input type="checkbox" data-rtype="${t.key}" ${!f.types || f.types.includes(t.key) ? 'checked' : ''}> ${esc(t.label)} <span class="n">(${counts[t.key]})</span></label>`
      )
      .join('');

    $('rList').innerHTML = r.items
      .map((it) => {
        const placeholder = it.original ? W.splitExt(it.original)[0] : 'WhatsApp name (assigned on download)';
        const ext = it.ext || '(original extension)';
        const dirTag = it.fromMe ? '<span class="dir-tag out">Sent</span>' : '<span class="dir-tag in">Received</span>';
        const typeText = it.kind === 'document' ? ` · ${esc(it.typeLabel)}` : '';
        return `<div class="ritem"><label class="pick"><input type="checkbox" data-pick="${esc(it.key)}" ${it.viewOnce ? 'disabled' : ''}>
          <span class="meta"><b>${esc(it.label)}</b>${typeText} ${dirTag} · ${esc(it.when)} · <span dir="auto">${esc(it.sender || '')}</span>${it.original ? ` · <span dir="auto">${esc(it.original)}</span>` : ''}${it.size ? ` · ${esc(it.size)}` : ''}${it.viewOnce ? ' · view once (cannot be saved)' : ''}</span></label>
          <div class="in"><input type="text" data-key="${esc(it.key)}" placeholder="${esc(placeholder)}" ${it.viewOnce ? 'disabled' : ''} dir="auto"><span class="ext">${esc(ext)}</span></div></div>`;
      })
      .join('');
    $('rList').querySelectorAll('input[data-pick]').forEach((cb) => (cb.onchange = updatePickCount));
    $('rDir').querySelectorAll('input').forEach((x) => (x.onchange = () => quickSelect('filter')));
    $('rTypes').querySelectorAll('input').forEach((x) => (x.onchange = () => quickSelect('filter')));
    quickSelect('filter');
  }

  function reviewFilter() {
    const dirEl = document.querySelector('input[name="rdir"]:checked');
    const types = Array.from($('rTypes').querySelectorAll('input[data-rtype]'))
      .filter((b) => b.checked)
      .map((b) => b.dataset.rtype);
    return { direction: dirEl ? dirEl.value : 'all', types };
  }

  function picks() {
    return Array.from($('rList').querySelectorAll('input[data-pick]'));
  }

  function updatePickCount() {
    const n = picks().filter((cb) => cb.checked).length;
    $('rSave').textContent = `Save selected (${n})`;
    $('rList').querySelectorAll('.ritem').forEach((row) => {
      const cb = row.querySelector('input[data-pick]');
      row.classList.toggle('off', !cb.checked);
    });
  }

  // what: 'all' | 'none' | 'filter' (tick exactly the files matching the Sent/Received and type filters)
  function quickSelect(what) {
    const f = reviewFilter();
    const byKey = new Map(reviewItems.map((it) => [it.key, it]));
    picks().forEach((cb) => {
      if (cb.disabled) return;
      const it = byKey.get(cb.dataset.pick);
      cb.checked = what === 'all' ? true : what === 'none' ? false : W.matchesFilter(it, f);
    });
    updatePickCount();
  }

  async function submitReview(saveSelected) {
    const renames = {};
    const selected = saveSelected ? picks().filter((cb) => cb.checked).map((cb) => cb.dataset.pick) : [];
    $('rList').querySelectorAll('input[data-key]').forEach((inp) => {
      const v = inp.value.trim();
      if (v) renames[inp.dataset.key] = v;
    });
    $('rSave').disabled = $('rSkip').disabled = true;
    try {
      await toContent({ type: 'reviewSubmit', renames, selected });
    } catch (e) {
      $('pError').textContent = 'Could not reach the WhatsApp tab: ' + e.message;
      $('pError').classList.remove('hidden');
    } finally {
      $('rSave').disabled = $('rSkip').disabled = false;
    }
  }

  // ------------------------------------------------------------ init
  async function init() {
    $('ver').textContent = 'v' + W.VERSION;
    settings = (await chrome.storage.local.get('wdreSettings')).wdreSettings || {};
    status = (await chrome.storage.local.get('wdreStatus')).wdreStatus || null;
    fillTz();
    renderTypeList();
    const today = W.tz.today($('tz').value);
    $('from').value = today;
    $('to').value = today;
    if (settings.mode) document.querySelector(`input[name="mode"][value="${settings.mode}"]`).checked = true;
    $('client').value = settings.client || '';
    $('review').checked = settings.review !== false; // on unless the user turned it off
    $('dateOrder').value = settings.dateOrder || 'auto';
    (settings.selectedChats || []).forEach((n) => selected.add(n));

    tab = await findTab();
    if (tab) ping = await toContent({ type: 'ping' }).catch(() => null);
    renderConn();
    renderChatList();

    if (status && (status.state === 'running' || status.state === 'review')) {
      const alive = ping && ping.busy && ping.jobId === status.jobId;
      if (!alive) {
        status.state = 'interrupted';
        status.review = null;
        status.error = 'The WhatsApp tab was reloaded or closed during the export. Files already saved are kept; start again for the rest.';
        await chrome.storage.local.set({ wdreStatus: status });
        chrome.action.setBadgeText({ text: '' });
      }
    }
    if (status && !status.dismissed) showProgress();
    else showForm();

    document.querySelectorAll('input[name="scope"], input[name="mode"]').forEach((r) => (r.onchange = updateSummary));
    document.querySelectorAll('input[name="dir"], #typeList input').forEach((x) => (x.onchange = saveFilter));
    $('review').onchange = updateSummary;
    const setTypes = (on) => (e) => {
      e.preventDefault();
      $('typeList').querySelectorAll('input').forEach((b) => (b.checked = on));
      saveFilter();
    };
    $('typesAll').onclick = setTypes(true);
    $('typesNone').onclick = setTypes(false);
    ['from', 'to', 'tz', 'client'].forEach((id) => ($(id).oninput = updateSummary));
    $('tz').onchange = updateSummary;
    $('chatFilter').oninput = renderChatList;
    $('loadChats').onclick = () => loadChats('selected');
    $('loadAll').onclick = () => loadChats('all');
    $('selNone').onclick = (e) => {
      e.preventDefault();
      selected.clear();
      settings.selectedChats = [];
      saveSettings();
      renderChatList();
      updateSummary();
    };
    $('startBtn').onclick = start;
    $('cancelBtn').onclick = async () => {
      $('cancelBtn').disabled = true;
      $('cancelBtn').textContent = 'Cancelling…';
      await toContent({ type: 'cancel' }).catch(() => {});
    };
    $('rSave').onclick = () => submitReview(true);
    $('rSkip').onclick = () => submitReview(false);
    document.querySelectorAll('a[data-sel]').forEach((a) => {
      a.onclick = (e) => {
        e.preventDefault();
        quickSelect(a.dataset.sel);
      };
    });
    $('openFolder').onclick = () => chrome.downloads.showDefaultFolder();
    $('showTranscript').onclick = () => {
      const c = (status.chats || []).find((x) => x.transcriptId || x.indexId);
      const id = status.summaryId || (c && (c.transcriptId || c.indexId));
      if (id != null) chrome.downloads.show(id);
    };
    $('newExport').onclick = async () => {
      if (status) {
        status.dismissed = true;
        await chrome.storage.local.set({ wdreStatus: status });
      }
      chrome.action.setBadgeText({ text: '' });
      toContent({ type: 'hideOverlay' }).catch(() => {});
      showForm();
    };
    $('diagBtn').onclick = async () => {
      const out = $('diagOut');
      out.classList.remove('hidden');
      out.textContent = 'Checking…';
      try {
        const res = await toContent({ type: 'diagnose' });
        out.textContent = JSON.stringify(res.report, null, 2);
      } catch (e) {
        out.textContent = 'Could not reach the WhatsApp tab: ' + e.message;
      }
    };
    document.querySelectorAll('a[data-open]').forEach((a) => {
      a.onclick = (e) => {
        e.preventDefault();
        chrome.tabs.create({ url: a.dataset.open });
      };
    });

    chrome.storage.onChanged.addListener((changes, area) => {
      if (area !== 'local' || !changes.wdreStatus) return;
      const nv = changes.wdreStatus.newValue;
      if (!nv) return;
      status = nv;
      if (!status.dismissed && $('progressView').classList.contains('hidden') && (status.state === 'running' || status.state === 'review')) showProgress();
      else if (!$('progressView').classList.contains('hidden')) renderProgress();
      if (status.state !== 'running' && status.state !== 'review') {
        $('cancelBtn').disabled = false;
        $('cancelBtn').textContent = 'Cancel export';
      }
    });
    updateSummary();
  }

  init();
})();

/* WhatsApp Web page adapter.
   Everything that depends on WhatsApp's markup lives here. WhatsApp changes its class names
   often, so this file relies on the longer-lived hooks (ids such as #main/#pane-side,
   data-id, data-pre-plain-text, data-icon, aria-label, role) and uses several fallbacks. */
(function (g) {
  'use strict';
  const W = g.WDRE;
  const D = (W.dom = {});

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  D.$ = $;
  D.$$ = $$;

  const RE = {
    download: /^(download|save|تنزيل|تحميل|حفظ|télécharger|descargar|herunterladen|baixar|scarica|indir|скачать|downloaden|unduh)$/i,
    older: /(older messages|get older|load earlier|earlier messages|رسائل أقدم|الرسائل الأقدم|الرسائل السابقة)/i,
    historyLimited:
      /(use whatsapp on your phone to see older messages|older messages.*(phone|primary device)|messages older than|استخدم واتساب على هاتفك|لعرض الرسائل الأقدم)/i,
    chatStart:
      /(end-to-end encrypted|secured with end-to-end encryption|created (this )?group|created group ["“]|مشفّرة|مشفرة تمام|أنشأ المجموعة|أنشأت المجموعة|أنشأ هذه المجموعة)/i,
    readMore: /^(read more|اقرأ المزيد|قراءة المزيد|عرض المزيد|lire la suite|leer más|mehr lesen|ler mais)$/i,
    deleted: /^(this message was deleted|you deleted this message|تم حذف هذه الرسالة|لقد حذفت هذه الرسالة|حذفت هذه الرسالة)$/i,
    time: /^(\d{1,2})[:.](\d{2})(?::\d{2})?\s*(am|pm|a\.m\.|p\.m\.|ص|م)?$/i,
    viewOnce: /(view[- ]?once|عرض لمرة واحدة|لمرة واحدة)/i,
    voice: /(voice (message|note)|رسالة صوتية|الرسالة الصوتية|مقطع صوتي)/i,
    quote: /(quoted|اقتباس|مقتبس)/i,
    menuBtn: /^(context menu|message options|more options|menu|options|خيارات|قائمة|قائمة السياق|خيارات الرسالة)$/i,
    close: /^(close|إغلاق|اغلاق)$/i,
    docMeta: /\b(pdf|docx?|xlsx?|xlsm|pptx?|zip|rar|7z|txt|csv|rtf|odt|ods|odp|xml|json|apk|msg|eml|heic)\b\s*[•·]/i,
    pages: /\b\d+\s*(pages?|صفحات|صفحة)\b/i,
    fileName: /^[^\\/:*?"<>|\n]{1,200}\.[A-Za-z0-9]{1,8}$/,
  };
  D.RE = RE;

  // ------------------------------------------------------------------ basics
  D.isVisible = function (n) {
    if (!n || !n.getBoundingClientRect) return false;
    const r = n.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) return false;
    const cs = getComputedStyle(n);
    return cs.visibility !== 'hidden' && cs.display !== 'none';
  };

  D.waitFor = async function (fn, timeoutMs = 5000, interval = 150) {
    const t0 = Date.now();
    for (;;) {
      let v = null;
      try {
        v = fn();
      } catch (e) {
        v = null;
      }
      if (v) return v;
      if (Date.now() - t0 >= timeoutMs) return null;
      await W.sleep(interval);
    }
  };

  function center(el) {
    const r = el.getBoundingClientRect();
    return { x: r.left + Math.min(r.width / 2, 40), y: r.top + Math.min(r.height / 2, 20) };
  }

  D.hover = function (el) {
    const { x, y } = center(el);
    const base = { cancelable: true, clientX: x, clientY: y, view: window };
    el.dispatchEvent(new PointerEvent('pointerover', { ...base, bubbles: true, pointerType: 'mouse' }));
    el.dispatchEvent(new PointerEvent('pointerenter', { ...base, bubbles: false, pointerType: 'mouse' }));
    el.dispatchEvent(new MouseEvent('mouseover', { ...base, bubbles: true }));
    el.dispatchEvent(new MouseEvent('mouseenter', { ...base, bubbles: false }));
    el.dispatchEvent(new PointerEvent('pointermove', { ...base, bubbles: true, pointerType: 'mouse' }));
    el.dispatchEvent(new MouseEvent('mousemove', { ...base, bubbles: true }));
  };

  D.click = function (el) {
    const { x, y } = center(el);
    const base = { bubbles: true, cancelable: true, clientX: x, clientY: y, view: window, button: 0 };
    el.dispatchEvent(new PointerEvent('pointerdown', { ...base, pointerType: 'mouse', buttons: 1 }));
    el.dispatchEvent(new MouseEvent('mousedown', { ...base, buttons: 1 }));
    el.dispatchEvent(new PointerEvent('pointerup', { ...base, pointerType: 'mouse' }));
    el.dispatchEvent(new MouseEvent('mouseup', base));
    el.dispatchEvent(new MouseEvent('click', base));
  };

  D.pressEscape = function () {
    const t = document.activeElement || document.body;
    const opts = { key: 'Escape', code: 'Escape', keyCode: 27, which: 27, bubbles: true, cancelable: true };
    t.dispatchEvent(new KeyboardEvent('keydown', opts));
    t.dispatchEvent(new KeyboardEvent('keyup', opts));
  };

  // ---------------------------------------------------------- page structure
  D.isReady = () => !!($('#pane-side') || $('#side'));
  D.mainEl = () => $('#main');

  D.currentChatTitle = function () {
    const tt = $('#main [data-testid="conversation-info-header-chat-title"]');
    if (tt && W.stripMarks(tt.textContent || '').trim()) return W.stripMarks(tt.textContent).trim();
    const h = $('#main header');
    if (!h) return null;
    for (const sel of ['span[dir="auto"][title]', '[title] span[dir="auto"]', 'span[title]', 'span[dir="auto"]', 'div[title]']) {
      for (const el of $$(sel, h)) {
        const t = W.stripMarks((el.getAttribute('title') || el.textContent || '').trim());
        if (t && !/^(click here|online|typing|last seen)/i.test(t)) return t;
      }
    }
    return null;
  };

  // Older builds used data-id="true_<chat>_<key>[_<participant>]"; the 2026 build uses the bare
  // key plus data-testid="conv-msg-<key>". Both are supported.
  D.isMsgId = (id) => /^(true|false)_/.test(id || '');
  const MSG_SEL = '[data-id]';

  D.panel = () => $('#main [data-testid="conversation-panel-messages"]') || $('#main');

  D.isMsgEl = function (el) {
    const id = el.getAttribute('data-id');
    if (!id) return false;
    if (D.isMsgId(id)) return true;
    if (/^conv-msg-/.test(el.getAttribute('data-testid') || '')) return true;
    return !!el.closest('[role="row"]');
  };

  D.messageElements = function (root) {
    root = root || D.panel();
    if (!root) return [];
    return $$(MSG_SEL, root).filter((el) => {
      if (!D.isMsgEl(el)) return false;
      const p = el.parentElement && el.parentElement.closest(MSG_SEL);
      return !(p && root.contains(p) && D.isMsgEl(p));
    });
  };

  // The message list is virtualised: rows outside the viewport keep their data-id but are empty.
  D.isRendered = function (el) {
    if (el.querySelector('[data-virtualized="true"]') || el.getAttribute('data-virtualized') === 'true') return false;
    return (el.textContent || '').trim().length > 0 || !!el.querySelector('img[src], video, [role="slider"]');
  };

  D.parseId = function (id) {
    if (!D.isMsgId(id)) return { fromMe: null, chatJid: '', key: String(id), participant: '' };
    const parts = String(id).split('_');
    return {
      fromMe: parts[0] === 'true',
      chatJid: parts[1] || '',
      key: parts[2] || '',
      participant: parts.length > 3 ? parts.slice(3).join('_') : '',
    };
  };

  D.scrollContainer = function () {
    const p = $('#main [data-testid="conversation-panel-messages"]');
    if (p && /(auto|scroll)/.test(getComputedStyle(p).overflowY)) return p;
    const msgs = D.messageElements();
    const start = msgs[0] || $('#main [role="application"]');
    let firstAuto = null;
    for (let n = start; n && n !== document.body; n = n.parentElement) {
      const oy = getComputedStyle(n).overflowY;
      if (/(auto|scroll)/.test(oy)) {
        if (n.scrollHeight > n.clientHeight + 4) return n;
        if (!firstAuto) firstAuto = n;
      }
    }
    if (firstAuto) return firstAuto;
    const main = $('#main');
    if (!main) return null;
    let best = null;
    for (const n of $$('div', main)) {
      if (/(auto|scroll)/.test(getComputedStyle(n).overflowY) && (!best || n.scrollHeight > best.scrollHeight)) best = n;
    }
    return best;
  };

  D.scrollToBottom = async function () {
    const btn = $$('#main [data-icon]').find((n) => /^(down|ic-arrow-down|scroll-down)$/.test(n.getAttribute('data-icon')));
    if (btn && D.isVisible(btn)) D.click(btn.closest('[role="button"], button') || btn);
    const sc = D.scrollContainer();
    if (sc) sc.scrollTop = sc.scrollHeight;
    await W.sleep(400);
    if (sc) sc.scrollTop = sc.scrollHeight;
  };

  D.scrollToTop = function () {
    const sc = D.scrollContainer();
    if (!sc) return false;
    sc.scrollTop = 0;
    sc.dispatchEvent(new Event('scroll'));
    return true;
  };

  D.firstMessageId = function () {
    const m = D.messageElements()[0];
    return m ? m.getAttribute('data-id') : null;
  };

  D.findOlderMessagesButton = function () {
    return (
      $$('#main [role="button"], #main button').find((n) => RE.older.test(W.norm(n.textContent)) && D.isVisible(n)) || null
    );
  };

  D.isLoadingOlder = function () {
    const main = $('#main');
    if (!main) return false;
    return !!$$('[role="progressbar"], svg circle, [data-icon*="loading"], [aria-label*="oading"]', main).find(
      (n) => !n.closest(MSG_SEL) && D.isVisible(n)
    );
  };

  function lca(a, b) {
    const anc = new Set();
    for (let n = a; n; n = n.parentElement) anc.add(n);
    for (let n = b; n; n = n.parentElement) if (anc.has(n)) return n;
    return null;
  }

  // Ordered list of messages and the text rows between them (date dividers, system notices).
  D.snapshot = function () {
    const msgs = D.messageElements();
    if (!msgs.length) {
      const main = $('#main');
      const texts = main ? $$('[role="row"]', main).map((n) => W.norm(n.textContent)).filter(Boolean) : [];
      return { events: texts.map((text) => ({ kind: 'text', text })), count: 0 };
    }
    const set = new Set(msgs);
    let root;
    if (msgs.length > 1) root = lca(msgs[0], msgs[msgs.length - 1]);
    else {
      root = msgs[0].parentElement;
      while (root && root.parentElement && root.children.length < 2 && root.id !== 'main') root = root.parentElement;
    }
    const events = [];
    const walk = (node) => {
      for (const child of node.children) {
        if (set.has(child)) {
          events.push({ kind: 'message', el: child, id: child.getAttribute('data-id'), rendered: D.isRendered(child) });
        } else if (child.querySelector(MSG_SEL)) {
          walk(child);
        } else {
          const text = W.norm(child.textContent || '');
          if (text && text.length < 400) events.push({ kind: 'text', text });
        }
      }
    };
    walk(root);
    return { events, count: msgs.length };
  };

  // ------------------------------------------------------------ date parsing
  const WEEKDAYS = {
    sunday: 0, sun: 0, monday: 1, mon: 1, tuesday: 2, tue: 2, wednesday: 3, wed: 3, thursday: 4, thu: 4,
    friday: 5, fri: 5, saturday: 6, sat: 6,
    'الأحد': 0, 'الاحد': 0, 'الإثنين': 1, 'الاثنين': 1, 'الثلاثاء': 2, 'الأربعاء': 3, 'الاربعاء': 3,
    'الخميس': 4, 'الجمعة': 5, 'السبت': 6,
  };
  const MONTHS = {
    january: 1, jan: 1, february: 2, feb: 2, march: 3, mar: 3, april: 4, apr: 4, may: 5, june: 6, jun: 6,
    july: 7, jul: 7, august: 8, aug: 8, september: 9, sep: 9, sept: 9, october: 10, oct: 10,
    november: 11, nov: 11, december: 12, dec: 12,
    'يناير': 1, 'فبراير': 2, 'مارس': 3, 'أبريل': 4, 'ابريل': 4, 'إبريل': 4, 'مايو': 5, 'يونيو': 6,
    'يوليو': 7, 'أغسطس': 8, 'اغسطس': 8, 'سبتمبر': 9, 'أكتوبر': 10, 'اكتوبر': 10, 'نوفمبر': 11, 'ديسمبر': 12,
  };
  const TODAY = new Set(['today', 'اليوم', "aujourd'hui", 'hoy', 'heute', 'hoje', 'oggi', 'bugün', 'сегодня', 'vandaag']);
  const YESTERDAY = new Set(['yesterday', 'أمس', 'الأمس', 'امس', 'hier', 'ayer', 'gestern', 'ontem', 'ieri', 'dün', 'вчера', 'gisteren']);

  const valid = (y, m, d) => {
    if (!(y > 1990 && y < 2200 && m >= 1 && m <= 12 && d >= 1 && d <= 31)) return false;
    const t = new Date(y, m - 1, d);
    return t.getMonth() === m - 1 && t.getDate() === d;
  };
  const addDays = (o, k) => {
    const t = new Date(o.y, o.m - 1, o.d + k);
    return { y: t.getFullYear(), m: t.getMonth() + 1, d: t.getDate() };
  };
  D.addDays = addDays;

  D.localeDateOrder = function () {
    try {
      const parts = new Intl.DateTimeFormat(navigator.language || 'en-GB', { year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(
        new Date(2001, 10, 22)
      );
      const idx = (t) => parts.findIndex((p) => p.type === t);
      if (idx('year') < idx('month') && idx('year') < idx('day')) return 'YMD';
      return idx('day') < idx('month') ? 'DMY' : 'MDY';
    } catch (e) {
      return 'DMY';
    }
  };

  D.dateNums = (s) => W.norm(s).match(/\d+/g) || [];

  D.parseNumericDate = function (s, order) {
    const raw = D.dateNums(s);
    if (raw.length < 3) return null;
    const n = raw.slice(0, 3).map(Number);
    let y;
    let m;
    let d;
    if (raw[0].length === 4) [y, m, d] = n;
    else if (raw[2].length === 4 || raw[2].length === 2) {
      y = n[2] < 100 ? 2000 + n[2] : n[2];
      if (order === 'MDY') [m, d] = n;
      else [d, m] = n;
    } else return null;
    if (!valid(y, m, d)) {
      if (valid(y, d, m)) [m, d] = [d, m];
      else return null;
    }
    return { y, m, d };
  };

  // Date divider labels: Today / Yesterday / weekday / numeric / "1 November 2026".
  D.parseDayLabel = function (text, order, now) {
    now = now || new Date();
    const t = W.norm(text).toLowerCase().replace(/[,.]/g, ' ').replace(/\s+/g, ' ').trim();
    if (!t || t.length > 40) return null;
    const today = { y: now.getFullYear(), m: now.getMonth() + 1, d: now.getDate() };
    if (TODAY.has(t)) return today;
    if (YESTERDAY.has(t)) return addDays(today, -1);
    if (Object.prototype.hasOwnProperty.call(WEEKDAYS, t)) {
      for (let k = 1; k <= 7; k++) {
        const c = addDays(today, -k);
        if (new Date(c.y, c.m - 1, c.d).getDay() === WEEKDAYS[t]) return c;
      }
    }
    const compact = t.replace(/\s/g, '');
    if (/^\d{1,4}[/\-]\d{1,2}[/\-]\d{1,4}$/.test(compact) || /^\d{1,2} \d{1,2} \d{4}$/.test(t)) return D.parseNumericDate(compact || t, order);
    let month = null;
    const nums = [];
    for (const w of t.split(' ')) {
      if (Object.prototype.hasOwnProperty.call(MONTHS, w)) month = MONTHS[w];
      else if (/^\d+(st|nd|rd|th)?$/.test(w)) nums.push(parseInt(w, 10));
      else if (Object.prototype.hasOwnProperty.call(WEEKDAYS, w) || w === 'de' || w === 'of') continue;
      else return null;
    }
    if (!month) return null;
    const day = nums.find((x) => x >= 1 && x <= 31);
    if (!day) return null;
    let year = nums.find((x) => x > 1990);
    if (!year) {
      year = today.y;
      if (new Date(year, month - 1, day) > now) year -= 1;
    }
    return valid(year, month, day) ? { y: year, m: month, d: day } : null;
  };

  D.parseTime = function (s) {
    const m = RE.time.exec(W.norm(s));
    if (!m) return null;
    let h = +m[1];
    const mi = +m[2];
    const ap = (m[3] || '').toLowerCase();
    if (ap) {
      const pm = ap.startsWith('p') || ap === 'م';
      if (h === 12) h = pm ? 12 : 0;
      else if (pm) h += 12;
    }
    if (h > 23 || mi > 59) return null;
    return { h, mi };
  };

  // "[10:15, 01/11/2026] Sender Name: "
  D.parsePrePlain = function (ppt) {
    const s = W.stripMarks(String(ppt || '')).replace(/،/g, ',');
    const m = /^\s*\[([^\]]+)\]\s*([\s\S]*)$/.exec(s);
    if (!m) return null;
    const bits = m[1].split(',').map((x) => x.trim());
    let time = null;
    let dateRaw = null;
    for (const b of bits) {
      if (!time && D.parseTime(b)) time = D.parseTime(b);
      else if (!dateRaw && D.dateNums(b).length >= 3) dateRaw = b;
    }
    // WhatsApp Business names can span lines ("Name\nTitle\nCompany"); keep the name line.
    const sender = m[2].replace(/:\s*$/, '').trim().split(/\s*\n\s*/)[0];
    return { time, dateRaw, sender };
  };

  // --------------------------------------------------------- message parsing
  function inQuote(n, root) {
    for (let p = n; p && p !== root; p = p.parentElement) {
      const al = p.getAttribute && p.getAttribute('aria-label');
      if (al && RE.quote.test(al)) return true;
      if (p.getAttribute && p.getAttribute('data-testid') === 'quoted-message') return true;
      if (p.classList && Array.from(p.classList).some((c) => /quoted/i.test(c))) return true;
    }
    return false;
  }
  D.inQuote = inQuote;

  function richText(node) {
    let out = '';
    const walk = (n) => {
      if (n.nodeType === 3) {
        out += n.nodeValue;
        return;
      }
      if (n.nodeType !== 1) return;
      const tag = n.tagName;
      if (tag === 'IMG') {
        out += n.getAttribute('alt') || n.getAttribute('data-plain-text') || '';
        return;
      }
      if (tag === 'BR') {
        out += '\n';
        return;
      }
      if ((tag === 'BUTTON' || n.getAttribute('role') === 'button') && RE.readMore.test(W.norm(n.textContent))) return;
      const block = tag === 'DIV' || tag === 'P';
      if (block && out && !out.endsWith('\n')) out += '\n';
      for (const c of n.childNodes) walk(c);
      if (block && out && !out.endsWith('\n')) out += '\n';
    };
    walk(node);
    return out.replace(/\n{3,}/g, '\n\n').trim();
  }
  D.richText = richText;

  function extractText(el, pptEl) {
    let spans = $$('span.selectable-text', el).filter((s) => !inQuote(s, el));
    spans = spans.filter((s) => !spans.some((o) => o !== s && o.contains(s)));
    if (spans.length) return spans.map(richText).filter(Boolean).join('\n');
    if (pptEl) {
      const clone = pptEl.cloneNode(true);
      for (const q of $$('[aria-label]', clone)) if (RE.quote.test(q.getAttribute('aria-label'))) q.remove();
      for (const n of $$('span, div', clone)) if (!n.children.length && D.parseTime(n.textContent)) n.remove();
      return richText(clone);
    }
    return '';
  }

  function extractQuote(el) {
    for (const n of $$('[aria-label]', el)) {
      if (RE.quote.test(n.getAttribute('aria-label'))) {
        const t = richText(n);
        if (t) return t.length > 240 ? t.slice(0, 240) + '…' : t;
      }
    }
    return '';
  }

  function findMetaTime(el) {
    let found = null;
    const meta = $$('[data-testid="msg-meta"]', el).find((n) => !inQuote(n, el));
    for (const n of $$('span, div', meta || el)) {
      if (n.children.length > 1 || inQuote(n, el)) continue;
      const txt = n.textContent || '';
      if (txt.length > 16) continue;
      const t = D.parseTime(txt);
      if (t) found = t;
    }
    return found;
  }

  function findFileNameText(el) {
    for (const n of $$('span, div', el)) {
      if (n.children.length || inQuote(n, el)) continue;
      const t = W.stripMarks((n.getAttribute('title') || n.textContent || '').trim());
      if (RE.fileName.test(t) && !/^https?:/i.test(t)) return t;
    }
    return null;
  }

  function findHeaderName(el) {
    for (const n of $$('span[dir="auto"], span[aria-label]', el)) {
      if (inQuote(n, el) || n.closest('.selectable-text') || n.closest('[data-pre-plain-text]')) continue;
      const t = W.norm(n.getAttribute('aria-label') || n.textContent);
      if (!t || t.length > 60) continue;
      if (D.parseTime(t) || RE.fileName.test(t) || RE.docMeta.test(t) || RE.pages.test(t) || /[•·]|^\d+(:\d+)?$|\b(kb|mb|gb)\b/i.test(t)) continue;
      if (RE.voice.test(t) || RE.viewOnce.test(t) || /^(photo|video|gif|sticker|image|audio)$/i.test(t)) continue;
      return t.replace(/:$/, '');
    }
    return '';
  }

  // Clickable picture/video tiles (not link previews, avatars or inline emoji).
  D.mediaTiles = function (el) {
    const imgs = $$('img', el).filter((img) => {
      if (inQuote(img, el) || img.closest('a') || img.closest('span.selectable-text')) return false;
      const src = img.getAttribute('src') || '';
      if (!/^(blob:|data:image|https?:)/.test(src)) return false;
      if (/pps\.whatsapp\.net/.test(src)) return false;
      const r = img.getBoundingClientRect();
      const w = r.width || img.width || img.naturalWidth || 0;
      const h = r.height || img.height || img.naturalHeight || 0;
      if (w && h && w < 48 && h < 48) return false;
      return true;
    });
    const tiles = [];
    for (const img of imgs) {
      let t = img;
      for (let p = img.parentElement; p && p !== el; p = p.parentElement) {
        if (p.getAttribute('role') === 'button') {
          if ($$('img', p).filter((x) => imgs.includes(x)).length === 1) t = p;
          break;
        }
      }
      if (!tiles.some((x) => x === t || x.contains(t) || t.contains(x))) tiles.push(t);
    }
    // Thumbnails whose picture has not loaded yet (2026 build marks them with data-testid).
    for (const t of $$('[data-testid="image-thumb"], [data-testid="video-thumb"], [data-testid="gif-thumb"]', el)) {
      if (inQuote(t, el) || t.closest('a')) continue;
      if (!tiles.some((x) => x === t || x.contains(t) || t.contains(x))) tiles.push(t);
    }
    return tiles;
  };

  D.detectMedia = function (el) {
    const ok = (n) => !inQuote(n, el) && !n.closest('a');
    // Newer builds mark media with data-testid (image-thumb, document-thumb…) rather than data-icon.
    const icons = $$('[data-icon], [data-testid]', el)
      .filter(ok)
      .map((n) => (n.getAttribute('data-icon') || n.getAttribute('data-testid') || '').toLowerCase());
    const labels = $$('[aria-label]', el).filter(ok).map((n) => n.getAttribute('aria-label') || '');
    const titles = $$('[title]', el).filter(ok).map((n) => n.getAttribute('title') || '');
    const text = W.norm(el.textContent || '');
    const anyIcon = (re) => icons.some((i) => re.test(i));
    const anyLabel = (re) => labels.some((l) => re.test(l));
    const tiles = D.mediaTiles(el);

    const viewOnce = anyIcon(/view-?once/) || anyLabel(RE.viewOnce) || /^(view once|photo view once|video view once)/i.test(text);
    if (viewOnce) {
      const kind = anyIcon(/video/) || /video|فيديو/i.test(text) ? 'video' : anyIcon(/ptt|audio/) ? 'voice' : 'image';
      return [{ kind, viewOnce: true }];
    }

    let docName = null;
    for (const t of titles) {
      // 'Download "x.pdf"' (older builds) or 'View "x.pdf"' (2026 build), in any UI language.
      const s = W.stripMarks(t).trim();
      const m = /^[^"“«']{1,24}["“«'](.+)["”»']$/.exec(s) || /^(?:download|تنزيل|تحميل)\s*:?\s*(.+)$/i.exec(s);
      if (m && /\.[A-Za-z0-9]{1,8}$/.test(m[1])) {
        docName = m[1];
        break;
      }
    }
    const docIcon = anyIcon(/^(doc-|document|ic-doc|icon-doc|file-|msg-doc)/);
    const docMeta = RE.docMeta.test(text) || RE.pages.test(text);
    const isVoice = anyIcon(/ptt|voice/) || anyLabel(RE.voice);
    const hasSlider = !!$('[role="slider"], input[type="range"]', el);
    const audioIcon = anyIcon(/audio-(play|pause|file)|^audio$|music|headphone/);

    if (docName || docIcon || (docMeta && !tiles.length)) {
      const name = docName || findFileNameText(el);
      const size = (text.match(/\b\d+(?:[.,]\d+)?\s?(?:kb|mb|gb|bytes?)\b/i) || [''])[0];
      return [{ kind: 'document', name, sizeText: size }];
    }
    if (isVoice) return [{ kind: 'voice' }];
    if (audioIcon || (hasSlider && !tiles.length)) return [{ kind: 'audio', name: findFileNameText(el) }];

    const isSticker = anyLabel(/sticker|ملصق/i) || anyIcon(/sticker/);
    if (isSticker && tiles.length <= 1) return [{ kind: 'sticker' }];

    if (tiles.length > 1) {
      return tiles.map((t, i) => {
        const tIcons = $$('[data-icon]', t).map((n) => (n.getAttribute('data-icon') || '').toLowerCase());
        const more = /^\+\s?(\d+)$/.exec(W.norm(t.textContent));
        return {
          kind: tIcons.some((x) => /gif/.test(x)) ? 'gif' : tIcons.some((x) => /media-play|video/.test(x)) ? 'video' : 'image',
          albumIndex: i,
          tileCount: tiles.length,
          moreCount: more ? +more[1] : 0,
        };
      });
    }
    const hasVideoEl = !!$('video', el);
    if (tiles.length || hasVideoEl) {
      if (anyIcon(/gif/) || anyLabel(/\bgif\b/i)) return [{ kind: 'gif' }];
      if (hasVideoEl || anyIcon(/media-play|video|play-video/) || anyLabel(/play video|video|فيديو/i)) return [{ kind: 'video' }];
      return [{ kind: 'image' }];
    }
    return [];
  };

  const YOU = /^(you|أنت|انت|vous|tú|tu|du|você|sen|jij|вы|sie)$/i;

  // Sent or received, and the sender's name. The 2026 build no longer encodes this in data-id;
  // each bubble starts with a hidden label ("You:" / "Name:"), and sent bubbles sit on the right.
  D.messageSide = function (el) {
    let fromMe = null;
    let label = '';
    const box = $('[data-testid="msg-container"]', el) || el;
    for (const n of $$('span[aria-label]', box)) {
      if (inQuote(n, el)) continue;
      const l = W.norm(n.getAttribute('aria-label'));
      if (!/:$/.test(l) || l.length > 80) continue;
      const name = l.replace(/:$/, '').trim();
      if (YOU.test(name)) fromMe = true;
      else {
        fromMe = false;
        label = name;
      }
      break;
    }
    if (fromMe == null) {
      const tails = $$('[data-icon^="tail-"], [data-testid^="tail-"]', el).map((n) => n.getAttribute('data-icon') || n.getAttribute('data-testid'));
      if (tails.includes('tail-out')) fromMe = true;
      else if (tails.includes('tail-in')) fromMe = false;
    }
    if (fromMe == null && el.querySelector('.message-out')) fromMe = true;
    if (fromMe == null && el.querySelector('.message-in')) fromMe = false;
    if (fromMe == null) {
      const panel = D.panel();
      const b = box.getBoundingClientRect();
      const p = panel && panel.getBoundingClientRect();
      if (p && b.width > 0 && b.width < p.width * 0.95) fromMe = (b.left + b.right) / 2 > (p.left + p.right) / 2;
    }
    return { fromMe, label };
  };

  D.parseMessage = function (el) {
    const id = el.getAttribute('data-id');
    const rec = Object.assign(
      { id, pptTime: null, pptDateRaw: null, pptSender: '', timeOnly: null, text: '', quoted: '', media: [], note: '', headerName: '', system: false },
      D.parseId(id)
    );
    const pptEl = $$('[data-pre-plain-text]', el).find((n) => !inQuote(n, el));
    if (pptEl) {
      const p = D.parsePrePlain(pptEl.getAttribute('data-pre-plain-text'));
      if (p) {
        rec.pptTime = p.time;
        rec.pptDateRaw = p.dateRaw;
        rec.pptSender = p.sender;
      }
    }
    rec.text = extractText(el, pptEl);
    rec.quoted = extractQuote(el);
    rec.timeOnly = findMetaTime(el);
    rec.media = D.detectMedia(el);
    // Media whose preview has not rendered yet: read the message again on a later pass.
    rec.mediaPending = !rec.media.length && !!$('[data-testid$="-thumb"], [aria-label="Open picture"], [aria-label="Play video"]', el);
    const side = D.messageSide(el);
    if (rec.fromMe == null) rec.fromMe = side.fromMe;
    if (!rec.fromMe && !rec.pptSender) rec.headerName = side.label || findHeaderName(el);
    const flat = W.norm(el.textContent || '');
    if (!rec.text && !rec.media.length) {
      const bubbleText = flat.replace(/\s*\d{1,2}[:.]\d{2}\s*(am|pm|ص|م)?\s*$/i, '').trim();
      if (RE.deleted.test(bubbleText)) {
        rec.note = 'deleted';
        rec.text = bubbleText;
      } else if (!rec.pptTime && !rec.timeOnly) {
        rec.system = true;
        rec.text = flat;
      } else if (bubbleText) {
        rec.text = bubbleText;
        rec.note = 'other';
      }
    }
    return rec;
  };

  // Click "Read more" so long messages are captured in full.
  const readMoreBtn = (el) => $$('[role="button"], button, span', el).find((n) => !n.children.length && RE.readMore.test(W.norm(n.textContent)));
  D.hasReadMore = (el) => !!readMoreBtn(el);
  D.expandReadMore = async function (el) {
    const btn = readMoreBtn(el);
    if (!btn) return false;
    D.click(btn);
    await W.sleep(150);
    return true;
  };

  // ------------------------------------------------------------- chat list
  D.chatPane = () => $('#pane-side');

  D.chatRows = function () {
    const pane = D.chatPane();
    if (!pane) return [];
    let rows = $$('[role="listitem"], [role="row"]', pane).filter((r) => r.querySelector('span[title]'));
    rows = rows.filter((r) => !rows.some((o) => o !== r && o.contains(r)));
    if (rows.length) return rows;
    const seen = new Set();
    for (const s of $$('span[title]', pane)) {
      const r = s.closest('[tabindex]') || s.parentElement;
      if (r) seen.add(r);
    }
    return Array.from(seen);
  };

  D.rowTitle = function (row) {
    const s = row.querySelector('span[title]');
    return s ? W.stripMarks((s.getAttribute('title') || s.textContent || '').trim()) : '';
  };

  D.listAllChats = async function (onProgress, isCancelled) {
    const pane = D.chatPane();
    if (!pane) throw new Error('WhatsApp chat list not found. Is WhatsApp Web fully loaded?');
    const names = [];
    const seen = new Set();
    const collect = () => {
      for (const r of D.chatRows()) {
        const t = D.rowTitle(r);
        if (t && !seen.has(t)) {
          seen.add(t);
          names.push(t);
        }
      }
    };
    const startTop = pane.scrollTop;
    pane.scrollTop = 0;
    await W.sleep(400);
    let stable = 0;
    for (let i = 0; i < 2000 && stable < 3; i++) {
      if (isCancelled && isCancelled()) break;
      const before = names.length;
      collect();
      if (onProgress) onProgress(names.length);
      const atEnd = pane.scrollTop + pane.clientHeight >= pane.scrollHeight - 4;
      if (atEnd && names.length === before) stable++;
      else stable = 0;
      pane.scrollTop += Math.max(200, pane.clientHeight * 0.8);
      await W.sleep(350);
    }
    pane.scrollTop = startTop;
    return names;
  };

  async function waitForChat(name, ms) {
    return D.waitFor(() => D.currentChatTitle() === name && D.messageElements().length >= 0 && $('#main'), ms);
  }

  D.openChat = async function (name) {
    if (D.currentChatTitle() === name) return true;
    const pane = D.chatPane();
    if (!pane) throw new Error('WhatsApp chat list not found');
    const tryRow = async () => {
      const row = D.chatRows().find((r) => D.rowTitle(r) === name);
      if (!row) return false;
      row.scrollIntoView({ block: 'center' });
      await W.sleep(150);
      const target = row.querySelector('[role="gridcell"]') || row.querySelector('[tabindex]') || row;
      D.click(target);
      return !!(await waitForChat(name, 6000));
    };
    if (await tryRow()) return true;
    pane.scrollTop = 0;
    await W.sleep(300);
    for (let i = 0; i < 2000; i++) {
      if (await tryRow()) return true;
      const atEnd = pane.scrollTop + pane.clientHeight >= pane.scrollHeight - 4;
      if (atEnd) break;
      pane.scrollTop += Math.max(200, pane.clientHeight * 0.8);
      await W.sleep(300);
    }
    // Fall back to WhatsApp's own search box.
    const box = $('#side [contenteditable="true"]') || $('#side input[type="text"]');
    if (box) {
      box.focus();
      if (box.isContentEditable) {
        document.execCommand('selectAll', false, null);
        document.execCommand('insertText', false, name);
      } else {
        box.value = name;
        box.dispatchEvent(new Event('input', { bubbles: true }));
      }
      await W.sleep(1500);
      const ok = await tryRow();
      if (box.isContentEditable) {
        box.focus();
        document.execCommand('selectAll', false, null);
        document.execCommand('delete', false, null);
      } else {
        box.value = '';
        box.dispatchEvent(new Event('input', { bubbles: true }));
      }
      if (ok) return true;
    }
    return false;
  };

  // --------------------------------------------------- menus and the viewer
  D.findMenuButton = function (el) {
    for (const n of $$('[data-icon], [data-testid]', el)) {
      const ic = (n.getAttribute('data-icon') || n.getAttribute('data-testid') || '').toLowerCase();
      if (/down-context|chevron|context-menu|menu-down|ic-expand/.test(ic) && !inQuote(n, el)) {
        return n.closest('[role="button"], button') || n;
      }
    }
    for (const n of $$('[aria-label]', el)) {
      const l = W.norm(n.getAttribute('aria-label'));
      // "Context menu" (older) or "Context menu for message from <name>" (2026 build).
      if ((RE.menuBtn.test(l) || /^context menu\b/i.test(l)) && !inQuote(n, el)) return n;
    }
    return null;
  };

  D.findMenuItems = function () {
    const items = $$('[role="menuitem"], [role="menu"] [role="button"], ul li[role="button"], ul li [role="button"], li[data-animate-dropdown-item]');
    return items.filter((n) => D.isVisible(n) && !n.closest(MSG_SEL) && !n.closest('#pane-side'));
  };

  D.findMenuItem = function (re) {
    for (const n of D.findMenuItems()) {
      const t = W.norm(n.getAttribute('aria-label') || n.textContent);
      if (re.test(t)) return n;
    }
    return null;
  };

  D.menuOpen = () => D.findMenuItems().length > 0;

  // Escape must be sent from inside the menu: on the page itself WhatsApp ignores it while a menu
  // is open, and with nothing open it closes the chat.
  D.closeMenu = async function () {
    if (!D.menuOpen()) return;
    const item = D.findMenuItems()[0];
    const menu = item && (item.closest('[role="menu"]') || item);
    const opts = { key: 'Escape', code: 'Escape', keyCode: 27, which: 27, bubbles: true, cancelable: true };
    for (const target of [item, menu]) {
      if (!target || !D.menuOpen()) break;
      if (target.focus) target.focus();
      target.dispatchEvent(new KeyboardEvent('keydown', opts));
      target.dispatchEvent(new KeyboardEvent('keyup', opts));
      await D.waitFor(() => !D.menuOpen(), 800);
    }
  };

  D.openMessageMenu = async function (el) {
    await D.closeMenu();
    const targets = [$('[data-testid="msg-container"]', el), el, $('[data-pre-plain-text]', el), el.firstElementChild, $('[role="button"]', el)].filter(Boolean);
    let btn = D.findMenuButton(el);
    for (const t of targets) {
      if (btn) break;
      D.hover(t);
      await W.sleep(200);
      btn = D.findMenuButton(el);
    }
    if (btn) D.click(btn);
    else {
      const r = el.getBoundingClientRect();
      el.dispatchEvent(
        new MouseEvent('contextmenu', { bubbles: true, cancelable: true, clientX: r.left + 30, clientY: r.top + 12, button: 2, view: window })
      );
    }
    return !!(await D.waitFor(() => D.menuOpen(), 2500));
  };

  function outsideChat(n) {
    return !n.closest(MSG_SEL) && !n.closest('#side') && !n.closest('#pane-side');
  }

  D.findViewerDownload = function () {
    for (const n of $$('[data-icon="download"], [aria-label], [title]')) {
      if (!outsideChat(n) || n.closest('[role="menu"], ul li, [role="menuitem"]')) continue;
      const lab = W.norm(n.getAttribute('aria-label') || n.getAttribute('title') || '');
      if ((n.getAttribute('data-icon') === 'download' || RE.download.test(lab)) && D.isVisible(n)) {
        return n.closest('[role="button"], button') || n;
      }
    }
    return null;
  };

  D.viewerOpen = () => !!D.findViewerDownload() || !!$$('[data-icon="x-viewer"]').find(D.isVisible);

  D.viewerMediaSrc = function () {
    const btn = D.findViewerDownload();
    let c = btn;
    for (let i = 0; i < 20 && c; i++, c = c.parentElement) {
      const media = $$('img[src^="blob:"], video[src^="blob:"], video source[src^="blob:"]', c).filter(
        (n) => outsideChat(n) && (n.tagName === 'SOURCE' || D.isVisible(n))
      );
      if (media.length) {
        const area = (n) => {
          const r = (n.tagName === 'SOURCE' ? n.parentElement : n).getBoundingClientRect();
          return r.width * r.height;
        };
        media.sort((a, b) => area(b) - area(a));
        return { src: media[0].getAttribute('src'), tag: media[0].tagName === 'IMG' ? 'img' : 'video' };
      }
    }
    return null;
  };

  D.openViewer = async function (tile) {
    D.click(tile);
    return !!(await D.waitFor(() => D.findViewerDownload(), 7000));
  };

  D.closeViewer = async function () {
    if (!D.viewerOpen()) return true;
    const close = $$('[data-icon="x-viewer"], [data-icon="x"], [aria-label], [title]').find((n) => {
      if (!outsideChat(n) || !D.isVisible(n)) return false;
      const ic = n.getAttribute('data-icon');
      if (ic === 'x-viewer') return true;
      return RE.close.test(W.norm(n.getAttribute('aria-label') || n.getAttribute('title') || ''));
    });
    if (close) D.click(close.closest('[role="button"], button') || close);
    else D.pressEscape();
    return !!(await D.waitFor(() => !D.viewerOpen(), 3000));
  };

  // A WhatsApp popup such as "Download failed" — returns its text and dismisses it.
  // Only real pop-ups count: the 2026 build also marks the pinned-message bar inside the chat and
  // the message menu as role="dialog", and those must not be read as errors.
  D.takeDialogText = async function () {
    const okRe = /^(ok|close|cancel|got it|حسنا|حسنًا|إغلاق|إلغاء)$/i;
    const btnText = (b) => W.norm(b.getAttribute('aria-label') || b.textContent);
    const dlg = $$('[role="dialog"], [role="alertdialog"], [data-animate-modal-popup]').find(
      (n) =>
        D.isVisible(n) &&
        !n.closest('#main') &&
        !n.closest('#side') &&
        !n.closest('[data-testid="media-viewer-modal"]') &&
        !$('[role="menu"], [role="menuitem"]', n) &&
        $$('button, [role="button"]', n).some((b) => okRe.test(btnText(b)))
    );
    if (!dlg) return '';
    const text = W.norm(dlg.textContent).slice(0, 300);
    const btn = $$('button, [role="button"]', dlg).find((b) => okRe.test(btnText(b)));
    if (btn) D.click(btn);
    await W.sleep(300);
    return text;
  };

  // Trigger a page download of a URL WhatsApp already decrypted (blob:) — used for stickers
  // and as a fallback when the viewer exposes the file but its button does not respond.
  D.anchorDownload = function (url, name) {
    const a = document.createElement('a');
    a.href = url;
    a.download = name || '';
    a.style.display = 'none';
    document.body.appendChild(a);
    a.click();
    setTimeout(() => a.remove(), 1000);
  };

  D.locateMessage = async function (id, isCancelled) {
    const sel = `[data-id="${CSS.escape(id)}"]`;
    let el = $(sel);
    if (!el) {
      const sc = D.scrollContainer();
      if (sc) {
        for (const dir of [-1, 1]) {
          for (let i = 0; i < 60 && !el; i++) {
            if (isCancelled && isCancelled()) return null;
            const before = sc.scrollTop;
            sc.scrollTop += dir * sc.clientHeight * 0.8;
            await W.sleep(350);
            el = $(sel);
            if (sc.scrollTop === before) break;
          }
          if (el) break;
        }
      }
    }
    if (!el) return null;
    el.scrollIntoView({ block: 'center' });
    await W.sleep(250);
    // Wait for the virtualised row to render its content.
    return (await D.waitFor(() => {
      const n = $(sel);
      return n && D.isRendered(n) ? n : null;
    }, 4000)) || $(sel) || el;
  };

  D.docTile = function (el) {
    return (
      $$('[data-testid="document-thumb"]', el).find((n) => !inQuote(n, el)) ||
      $$('[role="button"][title]', el).find((n) => !inQuote(n, el) && /["“«'].+\.[A-Za-z0-9]{1,8}["”»']$/.test(n.getAttribute('title'))) ||
      null
    );
  };

  // ------------------------------------------------------------ diagnostics
  D.diagnose = async function () {
    const all = D.messageElements();
    const msgs = all.filter(D.isRendered);
    // WhatsApp only renders the message-menu button while the pointer is over the bubble.
    if (msgs.length) {
      D.hover($('[data-testid="msg-container"]', msgs[msgs.length - 1]) || msgs[msgs.length - 1]);
      await W.sleep(400);
    }
    const sample = msgs.slice(-40).map((el) => D.parseMessage(el));
    const kinds = {};
    for (const r of sample) for (const m of r.media) kinds[m.kind] = (kinds[m.kind] || 0) + 1;
    const snap = D.snapshot();
    return {
      ready: D.isReady(),
      chatListRows: D.chatRows().length,
      currentChat: D.currentChatTitle(),
      messagesInDom: all.length,
      renderedOnScreen: msgs.length,
      sentReceived: `${sample.filter((r) => r.fromMe === true).length} sent / ${sample.filter((r) => r.fromMe === false).length} received / ${sample.filter((r) => r.fromMe == null).length} unknown`,
      withDatePrefix: sample.filter((r) => r.pptDateRaw).length,
      withTimeOnly: sample.filter((r) => !r.pptDateRaw && r.timeOnly).length,
      undatable: sample.filter((r) => !r.pptDateRaw && !r.timeOnly && !r.system).length,
      dividers: snap.events.filter((e) => e.kind === 'text' && D.parseDayLabel(e.text, 'DMY')).length,
      scrollContainer: !!D.scrollContainer(),
      menuButtonOnLast: msgs.length ? !!D.findMenuButton(msgs[msgs.length - 1]) : false,
      localeOrder: D.localeDateOrder(),
      mediaKinds: kinds,
      browserZone: W.tz.browserZone(),
    };
  };
})(globalThis);

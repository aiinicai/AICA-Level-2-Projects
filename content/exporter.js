/* Export engine: runs inside the WhatsApp Web tab so it keeps going when the popup closes. */
(function (g) {
  'use strict';
  const W = g.WDRE;
  const D = W.dom;
  const RE = D.RE;

  function sw(msg) {
    return new Promise((resolve, reject) => {
      try {
        chrome.runtime.sendMessage(msg, (res) => {
          const err = chrome.runtime.lastError;
          if (err) reject(new Error(err.message));
          else resolve(res);
        });
      } catch (e) {
        reject(new Error('The extension was reloaded or updated. Refresh WhatsApp Web and start again.'));
      }
    });
  }
  W.sw = sw;

  class CancelledError extends Error {}

  // ------------------------------------------------------------------------
  // Collector: captures messages as WhatsApp loads them, keyed by data-id so
  // re-renders never create duplicates, while separate messages with the same
  // text keep their own ids.
  // ------------------------------------------------------------------------
  class Collector {
    constructor() {
      this.map = new Map();
      this.order = [];
      this.pass = 0;
      this.chatStartSeen = false;
      this.historyLimitedSeen = false;
      this.orderUsed = null;
      this.earliestTs = null;
    }

    async ingest() {
      this.pass++;
      const snap = D.snapshot();
      let label = '__top__' + this.pass;
      const domIds = [];
      for (const ev of snap.events) {
        if (ev.kind === 'text') {
          if (RE.chatStart.test(ev.text)) this.chatStartSeen = true;
          else if (RE.historyLimited.test(ev.text)) this.historyLimitedSeen = true;
          else if (ev.text.length <= 40 && D.parseDayLabel(ev.text, 'DMY')) label = ev.text;
          continue;
        }
        domIds.push(ev.id);
        if (!ev.rendered) continue; // off-screen placeholder: keep its place, read it once it is on screen
        let rec = this.map.get(ev.id);
        const incomplete =
          rec &&
          ((!rec.media.length && !rec.text && !rec.system) || rec.mediaPending || rec.media.some((m) => m.kind === 'document' && !m.name));
        if (!rec || incomplete) {
          let el = ev.el.isConnected ? ev.el : document.querySelector(`[data-id="${CSS.escape(ev.id)}"]`) || ev.el;
          if (await D.expandReadMore(el)) {
            // WhatsApp may re-render the bubble (or the whole list) when it expands.
            el = (await D.waitFor(() => {
              const n = document.querySelector(`[data-id="${CSS.escape(ev.id)}"]`);
              return n && !D.hasReadMore(n) ? n : null;
            }, 1500)) || document.querySelector(`[data-id="${CSS.escape(ev.id)}"]`) || el;
          }
          const fresh = D.parseMessage(el);
          if (rec) {
            // Keep anything we learnt earlier (e.g. a document name) and add new detail.
            fresh.media = fresh.media.length ? fresh.media : rec.media;
            fresh.text = fresh.text || rec.text;
          }
          rec = fresh;
          this.map.set(ev.id, rec);
        }
        if (rec.system && RE.chatStart.test(rec.text)) this.chatStartSeen = true;
        if (rec.system && RE.historyLimited.test(rec.text)) this.historyLimitedSeen = true;
        // A real date divider seen earlier beats "top of the screen, divider not visible".
        if (!(label.startsWith('__top__') && rec.groupKey && !rec.groupKey.startsWith('__top__'))) rec.groupKey = label;
      }
      this.mergeOrder(domIds);
      return snap.count;
    }

    mergeOrder(domIds) {
      if (!this.order.length) {
        this.order = domIds.slice();
        return;
      }
      const known = new Set(this.order);
      const inserts = [];
      let pending = [];
      let prevKnown = null;
      for (const id of domIds) {
        if (known.has(id)) {
          if (pending.length) inserts.push({ anchor: id, where: 'before', ids: pending });
          pending = [];
          prevKnown = id;
        } else pending.push(id);
      }
      if (pending.length) inserts.push({ anchor: prevKnown, where: prevKnown ? 'after' : 'end', ids: pending });
      for (const ins of inserts) {
        const i = ins.anchor ? this.order.indexOf(ins.anchor) : -1;
        if (ins.where === 'before') this.order.splice(i, 0, ...ins.ids);
        else if (ins.where === 'after') this.order.splice(i + 1, 0, ...ins.ids);
        else this.order.push(...ins.ids);
      }
    }

    records() {
      return this.order.map((id) => this.map.get(id)).filter(Boolean);
    }

    // Day/month order: explicit setting, else evidence from the page, else browser locale.
    inferOrder(recs) {
      let dmy = 0;
      let mdy = 0;
      const vote = (a, b) => {
        if (a > 12 && b <= 12) dmy++;
        else if (b > 12 && a <= 12) mdy++;
      };
      const groups = new Map();
      for (const r of recs) {
        if (!r.pptDateRaw) continue;
        const n = D.dateNums(r.pptDateRaw);
        if (n[0] && n[0].length === 4) continue;
        vote(+n[0], +n[1]);
        if (!groups.has(r.groupKey)) groups.set(r.groupKey, []);
        groups.get(r.groupKey).push(n.map(Number));
      }
      // A "Today"/"Yesterday"/weekday divider pins down the real date of its group.
      for (const [key, list] of groups) {
        if (key.startsWith('__top__') || /\d/.test(W.norm(key))) continue;
        const real = D.parseDayLabel(key, 'DMY');
        if (!real) continue;
        for (const [a, b] of list) {
          if (a === real.d && b === real.m && a !== b) dmy++;
          else if (a === real.m && b === real.d && a !== b) mdy++;
        }
      }
      if (dmy === mdy) return null;
      return dmy > mdy ? 'DMY' : 'MDY';
    }

    resolve(setting) {
      const recs = this.records();
      const order = setting && setting !== 'auto' ? setting : this.inferOrder(recs) || D.localeDateOrder();
      this.orderUsed = order;
      const votes = new Map();
      for (const r of recs) {
        r.pptDate = r.pptDateRaw ? D.parseNumericDate(r.pptDateRaw, order) : null;
        if (r.pptDate) {
          const k = W.tz.ymd(r.pptDate);
          if (!votes.has(r.groupKey)) votes.set(r.groupKey, new Map());
          const m = votes.get(r.groupKey);
          m.set(k, (m.get(k) || 0) + 1);
        }
      }
      const groupDate = new Map();
      for (const [key, m] of votes) {
        const best = Array.from(m.entries()).sort((a, b) => b[1] - a[1])[0][0];
        groupDate.set(key, W.tz.parseYmd(best));
      }
      const dateFor = (key) => {
        if (groupDate.has(key)) return groupDate.get(key);
        if (!key || key.startsWith('__top__')) return null;
        const d = D.parseDayLabel(key, order);
        groupDate.set(key, d);
        return d;
      };
      for (const r of recs) r.localDate = r.pptDate || dateFor(r.groupKey) || null;
      // A message between two messages of the same day is on that day too.
      let prevDated = null;
      const nextDated = new Array(recs.length).fill(null);
      for (let i = recs.length - 1, nd = null; i >= 0; i--) {
        nextDated[i] = nd;
        if (recs[i].localDate && !recs[i].system) nd = recs[i].localDate;
      }
      recs.forEach((r, i) => {
        if (!r.localDate && prevDated && nextDated[i] && W.tz.ymd(prevDated) === W.tz.ymd(nextDated[i])) r.localDate = prevDated;
        if (r.localDate && !r.system) prevDated = r.localDate;
      });
      let earliest = null;
      for (const r of recs) {
        const date = r.localDate;
        const time = r.pptTime || r.timeOnly;
        r.ts = date && time ? W.tz.localWallToEpoch(date.y, date.m, date.d, time.h, time.mi) : null;
        const cmp = r.ts != null ? r.ts : date ? W.tz.localWallToEpoch(date.y, date.m, date.d, 12, 0) : null;
        if (cmp != null && !r.system && (earliest == null || cmp < earliest)) earliest = cmp;
      }
      this.earliestTs = earliest;
      return recs;
    }
  }
  W.Collector = Collector;

  // ------------------------------------------------------------------------
  // Job
  // ------------------------------------------------------------------------
  const STRATEGIES = {
    document: ['menu', 'viewer', 'docButton'],
    image: ['menu', 'viewer', 'viewerBlob', 'tileBlob'],
    video: ['menu', 'viewer', 'viewerBlob'],
    gif: ['menu', 'viewer', 'viewerBlob'],
    voice: ['menu'],
    audio: ['menu', 'docButton'],
    sticker: ['tileBlob', 'menu'],
    unknown: ['menu'],
  };
  const ALBUM_STRATEGIES = ['viewer', 'viewerBlob'];

  class Job {
    constructor(opts) {
      this.opts = opts;
      this.cancelled = false;
      this.reviewResolve = null;
      this.lastPublish = 0;
      this.publishTimer = null;
      this.firstDownloadDone = false;
      const range = W.tz.dayRange(opts.tz, opts.from, opts.to);
      this.start = range.start;
      this.end = range.end;
      this.rangeLabel = opts.from === opts.to ? opts.from : `${opts.from} to ${opts.to}`;
      const client = (opts.client || '').trim();
      this.root = 'WhatsApp Exports' + (client ? '/' + W.cleanSegment(client, 60, 'Client') : '');
      this.status = {
        jobId: W.uid(),
        state: 'running',
        startedAt: Date.now(),
        finishedAt: null,
        options: opts,
        rangeLabel: this.rangeLabel,
        root: this.root,
        chats: [],
        current: -1,
        totals: { messages: 0, attachments: 0, saved: 0, skipped: 0, failed: 0 },
        review: null,
        log: [],
        warning: '',
        blockWarning: '',
        error: '',
        summaryPath: '',
      };
    }

    // ---------------------------------------------------------- status
    log(line) {
      const t = new Date();
      this.status.log.push(`${W.pad2(t.getHours())}:${W.pad2(t.getMinutes())}:${W.pad2(t.getSeconds())}  ${line}`);
      if (this.status.log.length > 60) this.status.log.splice(0, this.status.log.length - 60);
      this.publish();
    }

    publish(now) {
      const doIt = () => {
        this.lastPublish = Date.now();
        this.publishTimer = null;
        this.status.warning =
          document.visibilityState === 'hidden'
            ? 'The WhatsApp tab is in the background, so Chrome slows it down. Bring it to the front (a separate window works).'
            : '';
        chrome.storage.local.set({ wdreStatus: this.status }).catch(() => {});
        if (W.overlay) W.overlay.update(this.status);
        this.updateBadge();
      };
      if (now || Date.now() - this.lastPublish > 400) {
        clearTimeout(this.publishTimer);
        doIt();
      } else if (!this.publishTimer) this.publishTimer = setTimeout(doIt, 400);
    }

    updateBadge() {
      const s = this.status;
      let text = '';
      let color = '#00338D';
      if (s.state === 'review') {
        text = '!';
        color = '#C2410C';
      } else if (s.state === 'running') {
        text = s.chats.length > 1 ? `${Math.max(1, s.current + 1)}/${s.chats.length}` : '…';
      } else if (s.state === 'done') {
        text = s.totals.failed ? '!' : '✓';
        color = s.totals.failed ? '#C2410C' : '#15803D';
      }
      if (text !== this.lastBadge) {
        this.lastBadge = text;
        sw({ type: 'badge', text, color }).catch(() => {});
      }
    }

    check() {
      if (this.cancelled) throw new CancelledError('Cancelled');
    }

    async sleep(ms) {
      const t0 = Date.now();
      while (Date.now() - t0 < ms) {
        this.check();
        await W.sleep(Math.min(200, ms - (Date.now() - t0)));
      }
    }

    cancel() {
      this.cancelled = true;
      if (this.reviewResolve) this.reviewResolve(null);
      this.log('Cancel requested — stopping after the current step.');
    }

    // selected: keys of the attachments to download (null = all).
    submitReview(renames, selected) {
      if (this.reviewResolve) {
        const r = this.reviewResolve;
        this.reviewResolve = null;
        r({ renames: renames || {}, selected: Array.isArray(selected) ? selected : null });
      }
    }

    // ---------------------------------------------------------- main flow
    async run() {
      if (W.overlay) W.overlay.show(this);
      try {
        const names = await this.resolveChats();
        this.status.chats = names.map((name) => ({
          name,
          state: 'pending',
          phase: 'Waiting',
          messagesSeen: 0,
          messagesInRange: 0,
          earliest: '',
          coverage: '',
          coverageNote: '',
          att: { total: 0, saved: 0, skipped: 0, failed: 0 },
          transcriptPath: '',
          indexPath: '',
          error: '',
        }));
        this.log(`Exporting ${names.length} chat(s), ${this.rangeLabel} (${this.opts.tz}).`);
        for (let i = 0; i < names.length; i++) {
          this.check();
          this.status.current = i;
          await this.exportChat(i);
        }
        this.status.state = 'done';
      } catch (e) {
        if (e instanceof CancelledError) {
          this.status.state = 'cancelled';
          for (const c of this.status.chats) if (c.state === 'pending' || c.state === 'running') c.state = 'cancelled';
        } else {
          console.error(e);
          this.status.state = 'error';
          this.status.error = String((e && e.message) || e);
          this.log('Error: ' + this.status.error);
        }
      }
      try {
        if (this.status.chats.length > 1 || this.opts.scope === 'all') await this.writeSummary();
      } catch (e) {
        this.log('Could not write the export summary: ' + e.message);
      }
      this.status.finishedAt = Date.now();
      const t = this.status.totals;
      this.log(`Finished: ${t.messages} messages, ${t.saved} files saved, ${t.skipped} skipped, ${t.failed} failed.`);
      this.publish(true);
      if (W.overlay) W.overlay.done(this.status);
    }

    async resolveChats() {
      const o = this.opts;
      if (o.scope === 'current') {
        const t = D.currentChatTitle();
        if (!t) throw new Error('No chat is open in WhatsApp Web. Open a chat or choose "Selected chats".');
        return [t];
      }
      if (o.scope === 'selected' || (o.scope === 'all' && o.chats && o.chats.length)) {
        if (!o.chats || !o.chats.length) throw new Error('No chats were selected.');
        return o.chats.slice();
      }
      this.log('Reading the chat list…');
      const names = await D.listAllChats(null, () => this.cancelled);
      this.check();
      if (!names.length) throw new Error('No chats found in the WhatsApp chat list.');
      return names;
    }

    chatDir(name) {
      return `${this.root}/${W.cleanSegment(name, 60, 'Chat')}/${this.rangeLabel}`;
    }

    async exportChat(i) {
      const c = this.status.chats[i];
      const o = this.opts;
      c.state = 'running';
      c.phase = 'Opening chat';
      this.publish(true);
      try {
        const opened = o.scope === 'current' && D.currentChatTitle() === c.name ? true : await D.openChat(c.name);
        if (!opened) throw new Error(`Could not open the chat "${c.name}" from the chat list.`);
        await D.waitFor(() => D.messageElements().length || D.snapshot().events.length, 8000);
        await this.sleep(600);

        // 1. Load history back to the start date, capturing as we go.
        c.phase = 'Loading earlier messages';
        this.publish(true);
        const col = new Collector();
        const coverage = await this.loadHistory(col, c);
        const recs = col.resolve(o.dateOrder);
        c.coverage = coverage.state;
        c.coverageNote = coverage.note;
        c.earliest = col.earliestTs != null ? W.tz.fmtDate(o.tz, col.earliestTs) : '';

        // 2. Select messages inside the range.
        const incomingNames = new Set(recs.filter((r) => !r.system && r.fromMe === false).map((r) => r.pptSender || r.headerName).filter(Boolean));
        const isGroup = recs.some((r) => /@g\.us$/.test(r.chatJid)) || incomingNames.size > 1;
        this.assignSenders(recs, c.name, isGroup);
        const noonInRange = (d) => {
          const t = W.tz.localWallToEpoch(d.y, d.m, d.d, 12, 0);
          return t >= this.start && t < this.end;
        };
        const inRange = recs.filter((r) => (r.ts != null ? r.ts >= this.start && r.ts < this.end : r.localDate ? noonInRange(r.localDate) : false));
        const undated = recs.filter((r) => r.ts == null && !r.localDate && !r.system).length;
        const userMsgs = inRange.filter((r) => !r.system);
        c.messagesInRange = userMsgs.length;
        this.log(
          `${c.name}: ${userMsgs.length} message(s) in range` +
            (coverage.state === 'partial' ? ` — PARTIAL, earliest reached ${c.earliest || 'unknown'}` : '') +
            (undated ? ` (${undated} loaded message(s) had no readable date)` : '')
        );

        // 3. Attachments.
        const atts = [];
        for (const r of inRange) {
          r.media.forEach((m, k) => {
            atts.push(
              Object.assign({}, m, {
                key: `${r.id}#${k}`,
                recId: r.id,
                sender: r.sender,
                fromMe: !!r.fromMe,
                typeKey: W.fileTypeKey(m.kind, m.name),
                ts: r.ts,
                status: 'pending',
                reason: '',
                originalName: m.name || '',
                savedPath: '',
                savedName: '',
              })
            );
          });
        }
        c.att.total = atts.length;
        this.status.totals.attachments += atts.length;

        if (o.scope === 'all' && !userMsgs.length) {
          c.state = 'done';
          c.phase = 'No messages in range — no folder created';
          this.publish(true);
          return;
        }

        const dir = this.chatDir(c.name);
        if (o.mode === 'messages') {
          for (const a of atts) this.finishAtt(c, a, 'skipped', 'Not downloaded: "Messages only" export');
        } else if (atts.length) {
          let choice = { renames: {}, selected: null };
          const filter = o.attFilter || null;
          let skipReason = 'Not selected for download';
          if (o.review) {
            c.phase = 'Waiting for you to choose which attachments to save';
            choice = (await this.awaitReview(i, atts)) || choice;
            this.check();
          } else if (!W.isDefaultFilter(filter)) {
            // No review step: apply the export screen's sent/received and file-type rules directly.
            choice.selected = atts.filter((a) => W.matchesFilter(a, filter)).map((a) => a.key);
            skipReason = `Filtered out (${W.describeFilter(filter)})`;
          }
          const chosen = choice.selected ? new Set(choice.selected) : null;
          const todo = atts.filter((a) => !chosen || chosen.has(a.key) || a.viewOnce); // view-once gets its own reason below
          for (const a of atts) if (chosen && !chosen.has(a.key) && !a.viewOnce) this.finishAtt(c, a, 'skipped', skipReason);
          c.phase = 'Saving attachments';
          this.publish(true);
          for (let k = 0; k < todo.length; k++) {
            this.check();
            const a = todo[k];
            a.renameBase = (choice.renames && choice.renames[a.key]) || '';
            c.phase = `Saving attachment ${k + 1} of ${todo.length}`;
            this.publish();
            await this.saveAttachment(c, a, dir + '/Media');
          }
        }

        // 4. Transcript and index.
        c.phase = 'Writing transcript and index';
        this.publish(true);
        await this.writeChatFiles(c, dir, inRange, atts, isGroup, col);
        this.status.totals.messages += userMsgs.length;
        c.state = coverage.state === 'partial' ? 'partial' : 'done';
        c.phase = coverage.state === 'partial' ? `Partial — earliest message reached ${c.earliest || 'unknown'}` : 'Done';
      } catch (e) {
        if (e instanceof CancelledError) {
          c.state = 'cancelled';
          c.phase = 'Cancelled';
          throw e;
        }
        console.error(e);
        c.state = 'failed';
        c.error = String((e && e.message) || e);
        c.phase = 'Failed: ' + c.error;
        this.log(`${c.name}: ${c.error}`);
      } finally {
        this.publish(true);
      }
    }

    async loadHistory(col, c) {
      await D.scrollToBottom();
      await this.sleep(600);
      let stagnant = 0;
      let olderClicks = 0;
      const t0 = Date.now();
      for (;;) {
        this.check();
        const count = await col.ingest();
        col.resolve(this.opts.dateOrder);
        c.messagesSeen = col.map.size;
        c.earliest = col.earliestTs != null ? W.tz.fmtDate(this.opts.tz, col.earliestTs) : '';
        c.phase = `Loading earlier messages — ${col.map.size} read, back to ${c.earliest || '…'}`;
        this.publish();
        if (col.earliestTs != null && col.earliestTs < this.start) {
          return { state: 'complete', note: 'Loaded messages from before the start date.' };
        }
        // WhatsApp only renders the rows on screen, so step up one screen at a time and read
        // each screen, instead of jumping straight to the top.
        const sc = D.scrollContainer();
        if (sc && sc.scrollTop > 2) {
          sc.scrollTop = Math.max(0, sc.scrollTop - Math.max(150, Math.round(sc.clientHeight * 0.6)));
          await this.sleep(350);
          continue;
        }
        // At the top of what is loaded: ask WhatsApp for older messages.
        const anchor = D.messageElements().find(D.isRendered);
        const anchorId = anchor ? anchor.getAttribute('data-id') : null;
        const before = D.firstMessageId();
        const beforeHeight = sc ? sc.scrollHeight : 0;
        const older = D.findOlderMessagesButton();
        if (older && olderClicks < 30) {
          D.click(older);
          if (!olderClicks) this.log(`${c.name}: asked WhatsApp for older messages.`);
          olderClicks++;
        }
        D.scrollToTop();
        const grew = await D.waitFor(() => {
          if (this.cancelled) return true;
          return D.firstMessageId() !== before || D.messageElements().length !== count || (sc && sc.scrollHeight > beforeHeight + 20);
        }, older ? 15000 : 7000);
        this.check();
        if (grew) {
          stagnant = 0;
          await this.sleep(400);
          // If WhatsApp left us at the very top, go back to the old top message so the rows
          // just loaded above it are stepped through too.
          const a = anchorId && document.querySelector(`[data-id="${CSS.escape(anchorId)}"]`);
          if (a && sc && sc.scrollTop < 5) {
            a.scrollIntoView({ block: 'start' });
            await this.sleep(300);
          }
          continue;
        }
        if (D.isLoadingOlder()) {
          await this.sleep(1500);
          continue;
        }
        stagnant++;
        if (stagnant >= 3) {
          await col.ingest();
          col.resolve(this.opts.dateOrder);
          if (col.earliestTs != null && col.earliestTs < this.start) {
            return { state: 'complete', note: 'Loaded messages from before the start date.' };
          }
          if (col.chatStartSeen && !col.historyLimitedSeen) {
            return { state: 'complete', note: 'Reached the beginning of the chat.' };
          }
          const secs = Math.round((Date.now() - t0) / 1000);
          return {
            state: 'partial',
            note: col.historyLimitedSeen
              ? 'WhatsApp Web says older messages are only on the phone.'
              : `WhatsApp Web stopped providing older messages after ${secs}s, before the start date was reached.`,
          };
        }
        // Nudge: some builds only load when the top sentinel re-enters view.
        if (sc) {
          sc.scrollTop = Math.min(600, sc.scrollHeight);
          await this.sleep(300);
        }
      }
    }

    assignSenders(recs, chatName, isGroup) {
      let ownName = '';
      const byParticipant = new Map();
      for (const r of recs) {
        if (r.fromMe && r.pptSender && !ownName) ownName = r.pptSender;
        if (!r.fromMe && r.pptSender && r.participant) byParticipant.set(r.participant, r.pptSender);
      }
      let prev = null;
      for (const r of recs) {
        if (r.system) {
          r.sender = '';
          continue;
        }
        // Undecided side (no label, tail or position): a continuation of the previous bubble.
        if (r.fromMe == null) r.fromMe = prev ? prev.fromMe : false;
        if (r.fromMe) r.sender = r.pptSender || ownName || 'You';
        else if (r.pptSender) r.sender = r.pptSender;
        else if (!isGroup) r.sender = chatName;
        else if (r.participant && byParticipant.has(r.participant)) r.sender = byParticipant.get(r.participant);
        else if (r.headerName) r.sender = r.headerName;
        else if (prev && !prev.fromMe && prev.participant && prev.participant === r.participant) r.sender = prev.sender;
        else if (r.participant) {
          const num = r.participant.split('@')[0];
          r.sender = /@c\.us$/.test(r.participant) && /^\d+$/.test(num) ? '+' + num : 'Unknown participant';
        } else r.sender = 'Unknown sender';
        if (!r.fromMe && r.participant && r.sender && !byParticipant.has(r.participant)) byParticipant.set(r.participant, r.sender);
        prev = r;
      }
    }

    awaitReview(i, atts) {
      const tz = this.opts.tz;
      this.status.state = 'review';
      this.status.review = {
        chatIndex: i,
        chatName: this.status.chats[i].name,
        items: atts.map((a) => ({
          key: a.key,
          kind: a.kind,
          label: W.KIND_LABEL[a.kind] || 'Attachment',
          sender: a.sender,
          when: a.ts != null ? W.tz.fmtDateTime(tz, a.ts) : '',
          original: a.originalName,
          ext: a.originalName ? W.splitExt(a.originalName)[1] : '',
          size: a.sizeText || '',
          viewOnce: !!a.viewOnce,
          fromMe: a.fromMe,
          typeKey: a.typeKey,
          typeLabel: W.fileTypeLabel(a.typeKey),
        })),
        filter: this.opts.attFilter || null,
      };
      this.log(`${this.status.chats[i].name}: choose which of the ${atts.length} attachment(s) to save in the extension popup.`);
      this.publish(true);
      return new Promise((resolve) => {
        this.reviewResolve = (choice) => {
          this.status.review = null;
          this.status.state = 'running';
          this.publish(true);
          resolve(choice);
        };
      });
    }

    finishAtt(c, a, status, reason) {
      a.status = status;
      a.reason = reason || '';
      c.att[status] = (c.att[status] || 0) + 1;
      this.status.totals[status] = (this.status.totals[status] || 0) + 1;
      this.publish();
    }

    // ---------------------------------------------------------- attachments
    async saveAttachment(c, a, mediaDir) {
      if (a.viewOnce) {
        this.finishAtt(c, a, 'skipped', 'View-once media: WhatsApp does not allow it to be saved');
        return;
      }
      let el = await D.locateMessage(a.recId, () => this.cancelled);
      this.check();
      if (!el) {
        this.finishAtt(c, a, 'failed', 'The message is no longer loaded in WhatsApp Web, so its download control could not be reached');
        return;
      }
      const strategies = a.albumIndex != null ? ALBUM_STRATEGIES : STRATEGIES[a.kind] || STRATEGIES.unknown;
      const attempts = [];
      const label = W.KIND_LABEL[a.kind] || 'Attachment';
      for (const strat of strategies) {
        this.check();
        el = document.querySelector(`[data-id="${CSS.escape(a.recId)}"]`) || el;
        const token = W.uid();
        const startTimeout = this.firstDownloadDone ? (a.kind === 'video' || a.kind === 'document' ? 90000 : 45000) : 120000;
        await sw({
          type: 'arm',
          token,
          dir: mediaDir,
          renameBase: a.renameBase || '',
          fallbackBase: this.fallbackBase(a),
          hintName: a.kind === 'document' ? a.originalName : '',
          kind: a.kind,
          timeoutMs: startTimeout,
        });
        let trig = { ok: false, why: 'control not found' };
        try {
          trig = await this.trigger(strat, el, a);
        } catch (e) {
          trig = { ok: false, why: e.message };
        }
        if (!trig.ok) {
          await sw({ type: 'disarm', token });
          attempts.push(`${strat}: ${trig.why}`);
          if (trig.cleanup) await trig.cleanup();
          continue;
        }
        if (!this.firstDownloadDone) {
          this.log(`Waiting for Chrome to start the first download. If Chrome asks to allow multiple downloads from web.whatsapp.com, click Allow.`);
        }
        // After one file has gone through, a menu download that doesn't start quickly is usually
        // Chrome holding it back ("download multiple files"), so check for that sooner.
        let res = await this.waitForDownload(token, strat === 'menu' && this.firstDownloadDone ? 25000 : startTimeout);
        if (res.state === 'timeout' && strat === 'menu' && this.firstDownloadDone) res = await this.waitWhileBlocked(token, el, a, mediaDir);
        if (trig.cleanup) await trig.cleanup();
        if (res.state === 'complete') {
          this.recordSaved(c, a, res, mediaDir, label);
          return;
        }
        if (res.state === 'cancelled') throw new CancelledError('Cancelled');
        const dlg = await D.takeDialogText();
        if (res.state === 'interrupted') attempts.push(`${strat}: Chrome reported ${res.error || 'an interrupted download'}`);
        else if (res.state === 'stalled') attempts.push(`${strat}: download stalled${res.danger ? ' (Chrome flagged the file type and it was not kept)' : ''}`);
        else if (res.mismatch) attempts.push(`${strat}: a different file ("${res.mismatch}") was downloaded instead`);
        else attempts.push(`${strat}: no download started`);
        if (dlg) {
          attempts.push(`WhatsApp said: "${dlg}"`);
          if (/download|can.?t|cannot|couldn.?t|failed|unavailable|not available|no longer|resend|expired|تعذر|فشل/i.test(dlg)) break;
        }
        await this.sleep(1500); // let any late download settle before arming the next attempt
      }
      this.finishAtt(c, a, 'failed', `${label} could not be downloaded (${attempts.join('; ')})`);
      this.log(`${c.name}: could not save ${label.toLowerCase()} — ${attempts[attempts.length - 1] || 'no download control'}.`);
    }

    recordSaved(c, a, res, mediaDir, label) {
      this.firstDownloadDone = true;
      if (this.status.blockWarning) {
        this.status.blockWarning = '';
        this.log('Downloads are going through again.');
      }
      a.savedPath = res.savedPath || '';
      a.savedName = W.basename(res.savedPath);
      a.originalName = a.originalName || res.originalName || '';
      a.whatsappName = res.originalName || '';
      a.bytes = res.bytes || 0;
      const expected = mediaDir.split('/').pop();
      const parent = String(a.savedPath).split(/[\\/]/).slice(-2, -1)[0];
      this.finishAtt(c, a, 'saved', parent === expected ? '' : `Saved outside the Media folder (${a.savedPath}) — another extension may have changed the location`);
      this.log(`${c.name}: saved ${label.toLowerCase()} "${a.savedName}".`);
    }

    // Chrome lets a site start one automatic download, then holds the rest until the user allows
    // "download multiple files". Tell the user what to click, keep the held download routed to the
    // export folder, and retry the WhatsApp Download button for up to three minutes.
    async waitWhileBlocked(token, el, a, mediaDir) {
      this.status.blockWarning =
        'Chrome is holding back downloads from web.whatsapp.com. Click the blocked-download icon at the right end of the address bar ' +
        'and choose "Always allow https://web.whatsapp.com to download multiple files" (or click Allow if Chrome asks). The export keeps retrying for 3 minutes.';
      this.log('Chrome seems to be blocking further downloads from web.whatsapp.com — allow multiple downloads to continue.');
      this.publish(true);
      const arm = (tok, ms) =>
        sw({
          type: 'arm',
          token: tok,
          dir: mediaDir,
          renameBase: a.renameBase || '',
          fallbackBase: this.fallbackBase(a),
          hintName: a.kind === 'document' ? a.originalName : '',
          kind: a.kind,
          timeoutMs: ms,
        });
      // 1. A held download starts by itself once the user clicks Allow: keep the same token armed.
      await arm(token, 60000);
      let res = await this.waitForDownload(token, 60000);
      // 2. If Chrome dropped it instead, click WhatsApp's Download again every 30 seconds.
      const until = Date.now() + 120000;
      while (res.state === 'timeout' && Date.now() < until) {
        this.check();
        const fresh = (await D.locateMessage(a.recId, () => this.cancelled)) || el;
        const tok = W.uid();
        await arm(tok, 30000);
        const trig = await this.trigger('menu', fresh, a).catch(() => ({ ok: false }));
        if (!trig.ok) {
          await sw({ type: 'disarm', token: tok });
          break;
        }
        res = await this.waitForDownload(tok, 30000);
      }
      return res;
    }

    fallbackBase(a) {
      const label = W.KIND_LABEL[a.kind] || 'File';
      const when = a.ts != null ? W.tz.fmtDateTime(this.opts.tz, a.ts).replace(':', '.') : 'undated';
      return `WhatsApp ${label} ${when}`;
    }

    async trigger(strat, el, a) {
      if (strat === 'menu') {
        const opened = await D.openMessageMenu(el);
        if (!opened) return { ok: false, why: 'message menu did not open' };
        const item = D.findMenuItem(RE.download);
        if (!item) {
          await D.closeMenu();
          return { ok: false, why: 'menu has no Download option' };
        }
        D.click(item);
        await this.sleep(200);
        await D.closeMenu();
        return { ok: true };
      }
      if (strat === 'docButton') {
        const btn =
          D.$$('[title]', el).find((n) => /^(download|تنزيل|تحميل)\b/i.test(W.norm(n.getAttribute('title'))) && !D.inQuote(n, el)) ||
          D.$$('[data-icon]', el).find((n) => /download/.test(n.getAttribute('data-icon') || ''));
        if (!btn) return { ok: false, why: 'no download button on the bubble' };
        D.click(btn.closest('[role="button"], button') || btn);
        return { ok: true };
      }
      const tiles = D.mediaTiles(el);
      const tile = a.kind === 'document' ? D.docTile(el) : tiles[a.albumIndex != null ? Math.min(a.albumIndex, tiles.length - 1) : 0];
      if (strat === 'tileBlob') {
        const img = tile && (tile.tagName === 'IMG' ? tile : tile.querySelector('img'));
        const src = img && img.getAttribute('src');
        if (!src) return { ok: false, why: 'no picture on the bubble' };
        if (a.kind !== 'sticker' && !src.startsWith('blob:')) return { ok: false, why: 'only a preview thumbnail is available on the bubble' };
        const name = await this.blobName(src, a);
        let url = src;
        let revoke = null;
        if (src.startsWith('data:')) {
          // Downloads of data: URLs carry no referrer, so re-wrap the sticker as a page blob URL.
          try {
            url = URL.createObjectURL(await (await fetch(src)).blob());
            revoke = url;
          } catch (e) {
            url = src;
          }
        }
        D.anchorDownload(url, name);
        return { ok: true, cleanup: revoke ? async () => setTimeout(() => URL.revokeObjectURL(revoke), 10000) : null };
      }
      if (strat === 'viewer' || strat === 'viewerBlob') {
        if (!tile) return { ok: false, why: 'no clickable media preview' };
        const opened = await D.openViewer(tile);
        const cleanup = async () => {
          await D.closeViewer();
          await this.ensureChatOpen();
        };
        if (!opened) return { ok: false, why: 'media viewer did not open', cleanup };
        await this.sleep(400);
        if (strat === 'viewer') {
          const btn = D.findViewerDownload();
          if (!btn) return { ok: false, why: 'viewer has no Download button', cleanup };
          D.click(btn);
          return { ok: true, cleanup };
        }
        const media = await D.waitFor(() => D.viewerMediaSrc(), 5000);
        if (!media) return { ok: false, why: 'viewer did not expose the file', cleanup };
        D.anchorDownload(media.src, await this.blobName(media.src, a));
        return { ok: true, cleanup };
      }
      return { ok: false, why: 'unknown method' };
    }

    async blobName(src, a) {
      let ext = '';
      try {
        const r = await fetch(src);
        const b = await r.blob();
        ext = W.extForMime(b.type);
      } catch (e) {
        /* fall back to the kind default */
      }
      return this.fallbackBase(a) + (ext || W.KIND_DEFAULT_EXT[a.kind] || '');
    }

    async ensureChatOpen() {
      const want = this.status.chats[this.status.current] && this.status.chats[this.status.current].name;
      if (want && D.currentChatTitle() !== want) {
        this.log(`Re-opening "${want}".`);
        await D.openChat(want);
        await this.sleep(800);
      }
    }

    async waitForDownload(token, startTimeoutMs) {
      const t0 = Date.now();
      let lastBytes = -1;
      let lastProgress = Date.now();
      let started = false;
      let warnedDanger = false;
      for (;;) {
        if (this.cancelled) {
          await sw({ type: 'cancelDownload', token }).catch(() => {});
          return { state: 'cancelled' };
        }
        const s = (await sw({ type: 'dlStatus', token })) || {};
        if (s.state === 'complete' || s.state === 'interrupted') return s;
        if (s.state === 'started' || s.state === 'dangerous') {
          if (!started) {
            started = true;
            lastProgress = Date.now();
          }
          if (s.bytesReceived !== lastBytes) {
            lastBytes = s.bytesReceived;
            lastProgress = Date.now();
          }
          if (s.state === 'dangerous' && !warnedDanger) {
            warnedDanger = true;
            this.log('Chrome flagged a downloaded file type. Open the Chrome downloads bubble and choose Keep to save it.');
          }
          const limit = s.state === 'dangerous' ? 180000 : 120000;
          if (Date.now() - lastProgress > limit) {
            await sw({ type: 'cancelDownload', token }).catch(() => {});
            return Object.assign({}, s, { state: 'stalled' });
          }
        } else if (Date.now() - t0 > startTimeoutMs) {
          await sw({ type: 'disarm', token }).catch(() => {});
          return { state: 'timeout', mismatch: s.mismatch };
        }
        await W.sleep(400);
      }
    }

    // ---------------------------------------------------------- output files
    async write(path, content, mime) {
      const res = await sw({ type: 'writeFile', path, content, mime });
      if (!res || !res.ok) throw new Error(`Could not save ${path}: ${(res && res.error) || 'unknown error'}`);
      return res;
    }

    async writeChatFiles(c, dir, inRange, atts, isGroup, col) {
      const o = this.opts;
      const ctx = {
        chatName: c.name,
        isGroup,
        rangeLabel: this.rangeLabel,
        from: o.from,
        to: o.to,
        tz: o.tz,
        mode: o.mode,
        coverage: c.coverage,
        coverageNote: c.coverageNote,
        earliest: c.earliest,
        generatedAt: Date.now(),
        dateOrder: col.orderUsed,
        records: inRange,
        atts,
        client: (o.client || '').trim(),
        version: W.VERSION,
      };
      if (o.mode !== 'media') {
        const res = await this.write(`${dir}/Transcript.html`, W.report.transcript(ctx), 'text/html;charset=utf-8');
        c.transcriptPath = res.savedPath;
        c.transcriptId = res.downloadId;
      }
      const idx = await this.write(`${dir}/Index.html`, W.report.indexHtml(ctx), 'text/html;charset=utf-8');
      c.indexPath = idx.savedPath;
      c.indexId = idx.downloadId;
      await this.write(`${dir}/Index.csv`, W.report.indexCsv(ctx), 'text/csv;charset=utf-8');
    }

    async writeSummary() {
      const stamp = new Date();
      const name = `Export summary ${stamp.getFullYear()}-${W.pad2(stamp.getMonth() + 1)}-${W.pad2(stamp.getDate())} ${W.pad2(stamp.getHours())}.${W.pad2(stamp.getMinutes())}.html`;
      const res = await this.write(`${this.root}/${name}`, W.report.summary(this.status), 'text/html;charset=utf-8');
      this.status.summaryPath = res.savedPath;
      this.status.summaryId = res.downloadId;
    }
  }
  W.Job = Job;
})(globalThis);

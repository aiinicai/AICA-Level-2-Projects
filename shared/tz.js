/* Time-zone helpers built on Intl (no external libraries). */
(function (g) {
  'use strict';
  const W = (g.WDRE = g.WDRE || {});
  const cache = new Map();

  function dtf(tz) {
    if (!cache.has(tz)) {
      cache.set(
        tz,
        new Intl.DateTimeFormat('en-US', {
          timeZone: tz,
          hourCycle: 'h23',
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
          weekday: 'short',
        })
      );
    }
    return cache.get(tz);
  }

  const WD = { Sun: 0, Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6 };

  function parts(tz, ms) {
    const o = {};
    for (const p of dtf(tz).formatToParts(new Date(ms))) o[p.type] = p.value;
    return {
      y: +o.year,
      m: +o.month,
      d: +o.day,
      h: +o.hour % 24,
      mi: +o.minute,
      s: +o.second,
      wd: WD[o.weekday],
    };
  }

  // Minutes east of UTC for `tz` at instant `ms`.
  function offsetMinutes(tz, ms) {
    const p = parts(tz, ms);
    const asUtc = Date.UTC(p.y, p.m - 1, p.d, p.h, p.mi, p.s);
    return Math.round((asUtc - Math.floor(ms / 1000) * 1000) / 60000);
  }

  // Wall-clock time in `tz` -> epoch ms.
  function zonedToEpoch(tz, y, m, d, h = 0, mi = 0, s = 0) {
    const guess = Date.UTC(y, m - 1, d, h, mi, s);
    let t = guess - offsetMinutes(tz, guess) * 60000;
    const off2 = offsetMinutes(tz, t);
    t = guess - off2 * 60000;
    return t;
  }

  function parseYmd(str) {
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(str || ''));
    return m ? { y: +m[1], m: +m[2], d: +m[3] } : null;
  }

  function addDaysYmd(o, k) {
    const t = new Date(Date.UTC(o.y, o.m - 1, o.d + k));
    return { y: t.getUTCFullYear(), m: t.getUTCMonth() + 1, d: t.getUTCDate() };
  }

  const ymd = (o) => `${o.y}-${W.pad2(o.m)}-${W.pad2(o.d)}`;

  W.tz = {
    browserZone: () => Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
    isValid(tz) {
      try {
        new Intl.DateTimeFormat('en-US', { timeZone: tz });
        return true;
      } catch (e) {
        return false;
      }
    },
    list() {
      let zones = [];
      try {
        zones = Intl.supportedValuesOf('timeZone');
      } catch (e) {
        zones = ['Asia/Dubai', 'UTC'];
      }
      if (!zones.includes('Asia/Dubai')) zones.unshift('Asia/Dubai');
      if (!zones.includes('UTC')) zones.push('UTC');
      return zones;
    },
    parts,
    offsetMinutes,
    zonedToEpoch,
    parseYmd,
    addDaysYmd,
    ymd,
    // Inclusive date range in `tz` -> [start, endExclusive) epoch ms.
    dayRange(tz, from, to) {
      const a = parseYmd(from);
      const b = addDaysYmd(parseYmd(to), 1);
      return { start: zonedToEpoch(tz, a.y, a.m, a.d), end: zonedToEpoch(tz, b.y, b.m, b.d) };
    },
    // A wall-clock time as displayed by the browser (its local zone) -> epoch ms.
    localWallToEpoch: (y, m, d, h = 0, mi = 0) => new Date(y, m - 1, d, h, mi, 0, 0).getTime(),
    today(tz) {
      return ymd(parts(tz, Date.now()));
    },
    fmtDate(tz, ms) {
      return ymd(parts(tz, ms));
    },
    fmtTime(tz, ms) {
      const p = parts(tz, ms);
      return `${W.pad2(p.h)}:${W.pad2(p.mi)}`;
    },
    fmtDateTime(tz, ms) {
      const p = parts(tz, ms);
      return `${ymd(p)} ${W.pad2(p.h)}:${W.pad2(p.mi)}`;
    },
    fmtDayHeading(tz, ms) {
      return new Intl.DateTimeFormat('en-GB', {
        timeZone: tz,
        weekday: 'long',
        day: 'numeric',
        month: 'long',
        year: 'numeric',
      }).format(new Date(ms));
    },
    fmtOffset(tz, ms) {
      const off = offsetMinutes(tz, ms == null ? Date.now() : ms);
      const sign = off >= 0 ? '+' : '-';
      const a = Math.abs(off);
      return `UTC${sign}${W.pad2(Math.floor(a / 60))}:${W.pad2(a % 60)}`;
    },
  };
})(globalThis);

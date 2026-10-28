/*
 * Saathi web app logic. Works offline, with no server and no API key.
 * All personal data is kept in this browser (localStorage) and never sent anywhere.
 */
/* global SaathiCore */
(function () {
  'use strict';
  const S = SaathiCore;
  const KEY = 'saathi.v1';
  const $ = (id) => document.getElementById(id);

  /* ------------------------------ state ------------------------------ */
  const blank = () => ({
    profile: null, // { name, cityId, birthKey, adult, seed }
    system: 'Vedic',
    days: {}, // dayKey -> { water, steps, routines, cookie, points }
    bonus: 0, // one-off points (birth details, personality test)
    tipi: null, // { answers, pct }
    body: { weight: '', height: '', asian: true },
  });
  let state = blank();
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) state = Object.assign(blank(), JSON.parse(raw));
  } catch (e) { /* private mode: keep in memory */ }
  const save = () => { try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) { /* ignore */ } };

  const city = () => S.cityById(state.profile ? state.profile.cityId : 'dubai');
  const todayKey = () => S.localDateKey(new Date(), city().tz);
  const day = () => {
    const k = todayKey();
    if (!state.days[k]) state.days[k] = { water: 0, steps: 0, routines: 0, cookie: false, points: 0 };
    return state.days[k];
  };
  const totalPoints = () => Object.values(state.days).reduce((a, d) => a + (d.points || 0), 0) + (state.bonus || 0);
  const activeDays = () => Object.keys(state.days).filter((k) => { const d = state.days[k]; return d.water || d.steps || d.routines || d.cookie; });

  function award(n) {
    day().points += n;
    save();
    renderHeader();
  }

  /* ------------------------------ toast ------------------------------ */
  function toast(msg) {
    let t = $('saathiToast');
    if (!t) {
      t = document.createElement('div');
      t.id = 'saathiToast';
      t.setAttribute('role', 'status');
      t.style.cssText = 'position:fixed;left:50%;bottom:calc(var(--nav-height) + 20px);transform:translateX(-50%);background:#201A42;color:#F8FAFC;border:1px solid #F5C542;padding:10px 16px;border-radius:12px;font-size:13px;z-index:999;max-width:90vw;text-align:center;box-shadow:0 8px 24px rgba(0,0,0,.4);transition:opacity .3s';
      document.body.appendChild(t);
    }
    t.textContent = msg;
    t.style.opacity = '1';
    clearTimeout(t._h);
    t._h = setTimeout(() => { t.style.opacity = '0'; }, 2600);
  }

  /* ----------------------------- rendering ----------------------------- */
  function renderHeader() {
    const pts = totalPoints();
    $('hdrPoints').textContent = pts.toLocaleString();
    $('streakCount').textContent = S.streak(activeDays(), todayKey());
    const lv = S.levelFor(pts);
    if ($('meLevel')) $('meLevel').textContent = `Level: ${lv.name} (${pts.toLocaleString()} pts${lv.next ? `, ${(lv.next - pts).toLocaleString()} to next` : ''})`;
  }

  function renderHabits() {
    const d = day();
    $('waterLabel').textContent = `${d.water} of 8 glasses (250ml)`;
    $('stepsLabel').textContent = `${d.steps.toLocaleString()} / 8,000 steps`;
    $('bodyStepCount').textContent = d.steps.toLocaleString();
    const km = (d.steps * 0.75) / 1000;
    $('bodyDistance').textContent = `${km.toFixed(1)} km • ${Math.round(d.steps * 0.04)} kcal`;
  }

  function renderProfile() {
    const p = state.profile;
    const name = p && p.name ? p.name : 'Friend';
    $('greetingName').textContent = `Namaste, ${name} ✨`;
    $('meName').textContent = name;
    if ($('meInitial')) $('meInitial').textContent = name.charAt(0).toUpperCase();
  }

  function renderSky() {
    const p = state.profile;
    const card = S.dayCard({ now: new Date(), cityId: city().id, system: state.system, birthKey: p && p.birthKey, seed: p ? p.seed : '' });
    const opts = { weekday: 'long', year: 'numeric', month: 'short', day: 'numeric', timeZone: card.city.tz };
    $('todayDateStr').textContent = `${new Date().toLocaleDateString(undefined, opts)} • ${card.moonPhase} • ${card.city.name}`;
    // Today snapshot
    $('quickMoonLabel').textContent = state.system === 'Vedic' ? 'Vedic Moon (sidereal)' : 'Western Moon (tropical)';
    $('quickMoonVedic').textContent = card.moonSign;
    $('quickNakshatra').textContent = `${card.nakshatra.name} Nakshatra`;
    $('quickAbhijit').textContent = card.abhijit;
    $('quickSun').textContent = `Sunrise ${card.sunrise} • Sunset ${card.sunset}`;
    $('quickRahuKaal').textContent = card.rahuKaal;
    $('quickLuckyColor').textContent = `${card.luckyColour} • ${card.luckyNumber}`;
    $('quickLuckyColor').style.color = card.luckyHex;
    $('quickDayLord').textContent = `Day Lord: ${card.vara.lord}`;
    // Stars deep card
    $('astroMoonTitle').textContent = `Moon in ${card.moonSign} (${state.system === 'Vedic' ? 'Sidereal Lahiri' : 'Tropical Western'})`;
    $('astroPanchangTitle').textContent = `${card.nakshatra.name} Nakshatra (pada ${card.nakshatra.pada}) • ${card.tithi.label} • ${card.vara.vedic}`;
    $('astroScore').textContent = card.score != null
      ? `Day Harmony Score: ${card.score}/10 (Moon in ${card.moonSign} vs your Sun in ${card.natalSun})`
      : 'Day Harmony Score: add your birth date (Edit Details) for a personal score';
    $('astroProTip').textContent = card.tip;
    $('astroLoved').textContent = `“${card.lovedLine}”`;
    $('astroFacts').textContent = `Lucky number ${card.luckyNumber}: ${card.luckyWhy}. Lucky colour from today's ruler, ${card.vara.lord}. Calculated for ${card.city.name}; sunrise ${card.sunrise}.`;
    const vb = $('btnVedic'), wb = $('btnWestern');
    const on = (b, colour) => { b.style.background = colour; b.style.color = '#0D0A1E'; };
    const off = (b) => { b.style.background = 'var(--card-elevated)'; b.style.color = 'var(--text-soft)'; };
    if (state.system === 'Vedic') { on(vb, 'var(--gold)'); off(wb); } else { on(wb, 'var(--lavender)'); off(vb); }
  }

  const LP_HINTS = { 1: 'Leader', 2: 'Peacemaker', 3: 'Creator', 4: 'Builder', 5: 'Explorer', 6: 'Nurturer', 7: 'Seeker', 8: 'Achiever', 9: 'Humanitarian', 11: 'Intuitive (master)', 22: 'Master builder', 33: 'Master teacher' };
  function renderNumbers() {
    const b = state.profile && state.profile.birthKey;
    const grid = $('loshuGrid');
    if (!b) {
      $('numLifePath').textContent = '—'; $('numMoolank').textContent = '—'; $('numBhagyank').textContent = '—';
      $('numLifePathHint').textContent = 'Add birth date';
      grid.innerHTML = S.LOSHU_ORDER.map((n) => `<div class="loshu-cell"><div class="cell-num">${n}</div><div class="cell-count">—</div></div>`).join('');
      $('loshuNote').textContent = 'Add your birth date (Edit Details) to see your numbers and grid.';
      return;
    }
    const lp = S.lifePath(b), bh = S.bhagyank(b), g = S.loShu(b);
    $('numLifePath').textContent = lp.compound !== lp.value ? `${lp.compound}/${lp.value}` : lp.value;
    $('numLifePathHint').textContent = LP_HINTS[lp.value] || '';
    $('numMoolank').textContent = S.moolank(b);
    $('numBhagyank').textContent = bh.compound !== bh.value ? `${bh.compound}/${bh.value}` : bh.value;
    grid.innerHTML = S.LOSHU_ORDER.map((n) => {
      const c = g.counts[n];
      return `<div class="loshu-cell${c ? ' present' : ''}"><div class="cell-num">${n}</div><div class="cell-count">${c ? '×' + c : '—'}</div></div>`;
    }).join('');
    const parts = [];
    if (g.complete.length) parts.push(...g.complete.map((pl) => `<strong>${pl.name} (${pl.nums.join('-')}) complete:</strong> ${pl.meaning}.`));
    else parts.push('<strong>No complete plane:</strong> your strengths are spread out rather than concentrated in one line.');
    if (g.missing.length) parts.push(`<span style="color: var(--text-muted)">Missing numbers: ${g.missing.join(', ')}. In the tradition these are qualities to grow, not weaknesses.</span>`);
    $('loshuNote').innerHTML = parts.join('<br>');
  }

  /* --------------------------- glow rituals --------------------------- */
  const RITUALS = {
    skin: ['☀️ Morning Skin Ritual', ['Splash face with lukewarm water', 'Apply gentle hyaluronic serum onto damp skin', 'Seal with barrier ceramides and broad-spectrum SPF 50+'], '🌙 Evening Recovery Ritual', ['Double cleanse to remove sunscreen and city pollutants', 'Centella asiatica (Cica) soothing essence', 'Light peptide cream overnight']],
    hair: ['☀️ Morning Hair Ritual', ['Comb gently from the ends upward', 'Light leave-in conditioner on the lengths', 'Cover hair or use UV protection in strong sun'], '🌙 Evening Scalp Ritual', ['2-minute fingertip scalp massage', 'A few drops of argan or coconut oil on dry ends', 'Silk or satin pillowcase to reduce friction']],
    nails: ['☀️ Morning Hand Ritual', ['Hand cream after every wash', 'Wear gloves for cleaning and dishes', 'File in one direction only'], '🌙 Evening Nail Ritual', ['Cuticle oil massage for 1 minute', 'Rich hand balm (shea butter)', 'Give nails a polish-free day each week']],
  };
  window.setGlowMode = function (mode) {
    const r = RITUALS[mode] || RITUALS.skin;
    const li = (arr) => arr.map((x, i) => `${i + 1}. ${x}`).join('<br>');
    $('glowRitual').innerHTML = `<h4 style="color: var(--gold-light); font-size: 14px;">${r[0]}</h4><p style="font-size: 12px; color: var(--text-soft); margin-top: 4px; line-height: 1.5;">${li(r[1])}</p><h4 style="color: var(--lavender); font-size: 14px; margin-top: 10px;">${r[2]}</h4><p style="font-size: 12px; color: var(--text-soft); margin-top: 4px; line-height: 1.5;">${li(r[3])}</p>`;
    document.querySelectorAll('[data-glow]').forEach((b) => {
      const active = b.getAttribute('data-glow') === mode;
      b.style.background = active ? 'rgba(244, 114, 182, 0.2)' : '';
      b.style.borderColor = active ? 'var(--rose)' : '';
      b.style.color = active ? 'var(--rose)' : '';
    });
  };

  /* ------------------------------ cookie ------------------------------ */
  function renderCookie() {
    const d = day();
    const p = state.profile;
    const f = S.dailyFortune(p ? p.seed : 'guest', todayKey());
    $('fortuneText').textContent = f.text;
    $('cookieRarity').textContent = f.golden ? '✨ Golden cookie today!' : 'One cookie a day';
    $('fortuneBadge').textContent = f.golden ? '★ Golden Fortune (+25 Pts) ★' : '★ Saathi Daily Oracle (+5 Pts) ★';
    $('cookieClickArea').style.display = d.cookie ? 'none' : '';
    $('fortuneScroll').style.display = d.cookie ? 'block' : 'none';
  }
  window.crackFortuneCookie = function () {
    const d = day();
    if (d.cookie) return;
    if (typeof window.playCookieCrackSound === 'function') window.playCookieCrackSound();
    const f = S.dailyFortune(state.profile ? state.profile.seed : 'guest', todayKey());
    d.cookie = true;
    award(f.golden ? 25 : 5);
    renderCookie();
    toast(f.golden ? 'Golden cookie! +25 points' : '+5 points. See you tomorrow for a new fortune.');
  };
  window.shareFortune = function () {
    const text = `✨ "${$('fortuneText').textContent}" — via Saathi`;
    if (navigator.share) navigator.share({ title: 'Saathi Daily Fortune', text }).catch(() => {});
    else if (navigator.clipboard) navigator.clipboard.writeText(text).then(() => toast('Fortune copied to clipboard'));
  };

  /* ------------------------------ habits ------------------------------ */
  window.addWaterGlass = function () {
    const d = day();
    if (d.water >= 12) return toast('That is plenty of water for today 💧');
    d.water++;
    award(5);
    renderHabits();
    toast(d.water === 8 ? 'Water goal reached! 🎉 +5' : '+5 points 💧');
  };
  window.addManualSteps = function () {
    const d = day();
    d.steps += 500;
    award(d.steps <= 15000 ? 5 : 0);
    renderHabits();
  };
  let walkTimer = null, walkStart = 0;
  window.toggleWalkSession = function () {
    const btn = $('btnWalkTimer');
    if (!walkTimer) {
      walkStart = Date.now();
      btn.textContent = '⏹ Stop Walk';
      btn.style.background = 'var(--danger)';
      const base = day().steps;
      walkTimer = setInterval(() => {
        const mins = (Date.now() - walkStart) / 60000;
        day().steps = base + Math.round(mins * 100);
        renderHabits();
      }, 1000);
    } else {
      clearInterval(walkTimer);
      walkTimer = null;
      btn.textContent = '▶ Start Walk';
      btn.style.background = 'var(--mint)';
      const mins = Math.round((Date.now() - walkStart) / 60000);
      if (mins >= 10) { award(15); toast(`Walk saved: ${mins} min. +15 points`); } else { save(); toast(`Walk saved: ${mins} min. Walks of 10+ minutes earn 15 points.`); }
    }
  };
  let routineInterval = null;
  window.triggerRoutine = function (type) {
    const info = {
      eye: ['Eye Refresh (20-20-20 Rule)', 'Look at something about 6 metres (20 feet) away and blink slowly.', 20],
      neck: ['Neck Relief Stretch', 'Slowly lower chin to chest, then gently tilt right ear to right shoulder, then left.', 30],
      desk: ['Desk Mobility & Posture', 'Interlace fingers, reach to the sky, and take 3 deep belly breaths.', 30],
    }[type] || ['Desk Mobility & Posture', 'Interlace fingers, reach to the sky, and take 3 deep belly breaths.', 30];
    let seconds = info[2];
    $('routineTitle').textContent = info[0];
    $('routineInstruction').textContent = info[1];
    $('timerCount').textContent = seconds;
    $('routineRunner').style.display = 'block';
    clearInterval(routineInterval);
    routineInterval = setInterval(() => {
      seconds--;
      $('timerCount').textContent = seconds;
      if (seconds <= 0) {
        clearInterval(routineInterval);
        $('routineRunner').style.display = 'none';
        const d = day();
        d.routines++;
        award(d.routines <= 8 ? 10 : 0);
        toast(`${info[0]} complete! +10 points`);
      }
    }, 1000);
  };
  window.closeRoutineRunner = function () {
    clearInterval(routineInterval);
    $('routineRunner').style.display = 'none';
  };

  /* -------------------------------- BMI -------------------------------- */
  window.updateBmiCalculations = function () {
    const w = parseFloat($('inpWeightVal').value);
    const hcm = parseFloat($('inpHeightVal').value);
    const isAsian = $('chkAsianCutoff').checked;
    state.body = { weight: $('inpWeightVal').value, height: $('inpHeightVal').value, asian: isAsian };
    save();
    if (!(w >= 25 && w <= 300) || !(hcm >= 100 && hcm <= 250)) {
      $('bmiNumberDisplay').textContent = '—';
      $('bmiCategoryLabel').textContent = 'Enter weight and height';
      $('bmiRangeText').textContent = 'BMI uses only the numbers you type. Saathi never estimates it from a photo.';
      return;
    }
    const h = hcm / 100;
    const bmi = w / (h * h);
    const healthyMax = isAsian ? 22.9 : 24.9;
    const obeseFrom = isAsian ? 27.5 : 30;
    let cat = 'Healthy range';
    if (bmi < 18.5) cat = 'Below healthy range';
    else if (bmi >= obeseFrom) cat = 'Well above healthy range';
    else if (bmi > healthyMax) cat = 'Above healthy range';
    $('bmiNumberDisplay').textContent = bmi.toFixed(1);
    $('bmiCategoryLabel').textContent = cat;
    $('bmiRangeText').textContent = `Healthy range for ${hcm.toFixed(0)} cm: ${(18.5 * h * h).toFixed(1)} – ${(healthyMax * h * h).toFixed(1)} kg (${isAsian ? 'Asian' : 'WHO'} cut-offs). BMI is a rough guide; talk to a doctor for personal advice.`;
  };

  /* --------------------------- astro system --------------------------- */
  window.setAstroSystem = function (sys) {
    state.system = sys === 'Western' ? 'Western' : 'Vedic';
    save();
    renderSky();
  };

  /* ------------------------ onboarding / details ------------------------ */
  function fillCities() {
    const sel = $('modalInpCity');
    if (sel.options.length) return;
    sel.innerHTML = S.CITIES.map((c) => `<option value="${c.id}">${c.name}</option>`).join('');
  }
  window.openBirthModal = function (welcome) {
    fillCities();
    const p = state.profile;
    $('modalTitle').textContent = welcome === true ? 'Welcome to Saathi ✨' : 'Edit Astrological Details';
    $('modalInpName').value = p ? p.name : '';
    $('modalInpCity').value = p ? p.cityId : 'dubai';
    $('modalInpDate').value = p && p.birthKey ? p.birthKey : '';
    $('modalAdult').checked = !!(p && p.adult);
    $('modalAdult').parentElement.style.display = p && p.adult ? 'none' : '';
    $('birthModal').classList.add('open');
  };
  window.closeBirthModal = function () {
    if (!state.profile) return toast('Please add your name and confirm you are 18+ to begin.');
    $('birthModal').classList.remove('open');
  };
  window.saveBirthDetails = function () {
    const name = $('modalInpName').value.trim().slice(0, 40);
    const birthKey = $('modalInpDate').value;
    const adult = $('modalAdult').checked || (state.profile && state.profile.adult);
    if (!name) return toast('Please enter your name.');
    if (!adult) return toast('Saathi is for adults (18+). Please confirm to continue.');
    if (birthKey && (birthKey < '1900-01-01' || birthKey > new Date().toISOString().slice(0, 10))) return toast('Please check the birth date.');
    const first = !state.profile;
    const hadBirth = state.profile && state.profile.birthKey;
    state.profile = {
      name, cityId: $('modalInpCity').value, birthKey: birthKey || null, adult: true,
      seed: state.profile ? state.profile.seed : Math.random().toString(36).slice(2) + Date.now().toString(36),
    };
    if (birthKey && !hadBirth) state.bonus = (state.bonus || 0) + 20;
    save();
    $('birthModal').classList.remove('open');
    renderAll();
    toast(first ? `Welcome, ${name}! Your day is ready.` : 'Your day card has been recalculated.');
  };
  window.resetAll = function () {
    if (!confirm('Delete all your Saathi data on this device?')) return;
    try { localStorage.removeItem(KEY); } catch (e) { /* ignore */ }
    state = blank();
    renderAll();
    window.openBirthModal(true);
  };

  /* ---------------------------- signature ---------------------------- */
  let strokes = [], current = null, canvas, ctx, resizeCanvas = () => {};
  function initCanvas() {
    canvas = $('sigCanvas');
    if (!canvas) return;
    ctx = canvas.getContext('2d');
    const resize = () => { canvas.width = canvas.parentElement.clientWidth || 300; canvas.height = 160; ctx.lineWidth = 3; ctx.lineCap = 'round'; ctx.lineJoin = 'round'; ctx.strokeStyle = '#F5C542'; redraw(); };
    const pos = (e) => { const r = canvas.getBoundingClientRect(); const t = e.touches ? e.touches[0] : e; return { x: t.clientX - r.left, y: t.clientY - r.top }; };
    const start = (e) => { current = [pos(e)]; strokes.push(current); e.preventDefault && e.preventDefault(); };
    const move = (e) => { if (!current) return; const p = pos(e); const last = current[current.length - 1]; current.push(p); ctx.beginPath(); ctx.moveTo(last.x, last.y); ctx.lineTo(p.x, p.y); ctx.stroke(); e.preventDefault && e.preventDefault(); };
    const end = () => { if (!current) return; current = null; analyse(); };
    canvas.addEventListener('mousedown', start); canvas.addEventListener('mousemove', move); window.addEventListener('mouseup', end);
    canvas.addEventListener('touchstart', start, { passive: false }); canvas.addEventListener('touchmove', move, { passive: false }); canvas.addEventListener('touchend', end);
    window.addEventListener('resize', resize);
    resizeCanvas = resize;
    resize();
  }
  function redraw() {
    if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    for (const s of strokes) { ctx.beginPath(); s.forEach((p, i) => (i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y))); ctx.stroke(); }
  }
  function analyse() {
    const r = S.analyseSignature(strokes, canvas.width, canvas.height);
    const box = $('sigAnalysisBox');
    if (!r) { box.innerHTML = '<strong>Keep going:</strong> draw your full signature so Saathi has enough strokes to measure.'; return; }
    box.innerHTML = `<strong>Measured from your strokes:</strong> slant ${r.slantDeg}° (${r.slantClass}), baseline ${r.baselineDeg > 0 ? '+' : ''}${r.baselineDeg}° (${r.baselineClass}), size ${r.sizeClass}${r.underline ? ', underlined' : ''}.<br><br><strong>What graphology tradition says:</strong> ${r.reading.join(' ')}<br><br><span style="color: var(--text-muted)">For fun and reflection only. Never used for hiring, legal or money decisions, and your signature is not stored.</span>`;
  }
  window.clearSignature = function () {
    strokes = [];
    redraw();
    $('sigAnalysisBox').innerHTML = '<strong>Graphology Reading:</strong> Draw your signature above. Saathi measures your strokes on this device (slant, baseline, size) and explains what the tradition says.';
  };

  /* -------------------------------- TIPI -------------------------------- */
  const SCALE = ['Disagree strongly', 'Disagree moderately', 'Disagree a little', 'Neutral', 'Agree a little', 'Agree moderately', 'Agree strongly'];
  const TRAIT_COLOURS = { Extraversion: 'var(--gold)', Agreeableness: 'var(--rose)', Conscientiousness: 'var(--mint)', 'Emotional stability': 'var(--cyan)', Openness: 'var(--lavender)' };
  let tipiDraft = null;
  function renderTipi() {
    const box = $('tipiBox');
    if (!box) return;
    if (state.tipi && !tipiDraft) {
      const pct = state.tipi.pct;
      box.innerHTML = Object.keys(pct).map((k) => `<div style="margin-bottom:8px"><div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:2px"><span>${k}</span><span style="color:${TRAIT_COLOURS[k]};font-weight:700">${pct[k]}%</span></div><div style="height:6px;background:var(--card-elevated);border-radius:3px;overflow:hidden"><div style="width:${pct[k]}%;height:100%;background:${TRAIT_COLOURS[k]}"></div></div></div>`).join('')
        + '<button id="tipiRetake" class="btn-habit-act" style="margin-top:6px">Retake the test</button>';
      $('tipiRetake').onclick = () => { tipiDraft = []; renderTipi(); };
      return;
    }
    if (!tipiDraft) {
      box.innerHTML = '<p style="font-size:12px;color:var(--text-soft);line-height:1.5">10 quick statements, about a minute. Your scores stay on this device.</p><button id="tipiStart" class="btn-habit-act" style="margin-top:8px">Start the test (+50 pts)</button>';
      $('tipiStart').onclick = () => { tipiDraft = []; renderTipi(); };
      return;
    }
    const i = tipiDraft.length;
    box.innerHTML = `<div style="font-size:11px;color:var(--text-muted)">Question ${i + 1} of 10 · I see myself as…</div><div style="font-size:15px;font-weight:700;margin:6px 0 10px">${S.TIPI_ITEMS[i]}</div>`
      + SCALE.map((l, k) => `<button data-v="${k + 1}" class="btn-habit-act" style="display:block;width:100%;margin-bottom:6px;text-align:left">${l}</button>`).join('');
    box.querySelectorAll('[data-v]').forEach((b) => b.addEventListener('click', () => {
      tipiDraft.push(Number(b.getAttribute('data-v')));
      if (tipiDraft.length === 10) {
        const first = !state.tipi;
        state.tipi = { answers: tipiDraft, pct: S.scoreTipi(tipiDraft).pct };
        tipiDraft = null;
        if (first) state.bonus = (state.bonus || 0) + 50;
        save();
        renderHeader();
        toast(first ? 'Personality test complete! +50 points' : 'Scores updated');
      }
      renderTipi();
    }));
  }

  /* ------------------------------ tabs ------------------------------ */
  window.switchTab = function (tabId) {
    document.querySelectorAll('.tab-content').forEach((el) => el.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach((el) => el.classList.remove('active'));
    const t = $(`tab-${tabId}`), n = $(`nav-${tabId}`);
    if (t) t.classList.add('active');
    if (n) n.classList.add('active');
    window.scrollTo({ top: 0, behavior: 'smooth' });
    if (tabId === 'stars') requestAnimationFrame(() => resizeCanvas());
  };

  /* ------------------------------ misc ------------------------------ */
  /* ---------------------- installable web app (PWA) ---------------------- */
  // Works when the folder is served over https (or localhost). Opening index.html as a file still works, just without install/offline.
  let installEvent = null;
  window.addEventListener('beforeinstallprompt', (e) => { e.preventDefault(); installEvent = e; });
  window.addEventListener('appinstalled', () => { installEvent = null; toast('Saathi is installed. Find it on your home screen ✨'); });
  if ('serviceWorker' in navigator && /^https?:$/.test(location.protocol)) {
    const reg = () => navigator.serviceWorker.register('sw.js').catch(() => {});
    if (document.readyState === 'complete') reg(); else window.addEventListener('load', reg);
  }
  const isStandalone = () => matchMedia('(display-mode: standalone)').matches || navigator.standalone === true;

  window.promptPwaInstall = async function () {
    if (isStandalone()) return toast('You are already using the installed Saathi app ✨');
    if (installEvent) {
      installEvent.prompt();
      const { outcome } = await installEvent.userChoice;
      installEvent = null;
      if (outcome !== 'accepted') toast('No problem. You can install it any time from here.');
      return;
    }
    if (location.protocol === 'file:') return toast('To install, open Saathi from its web link (https), then tap this button again.');
    if (/iPhone|iPad|iPod/.test(navigator.userAgent)) return toast('On iPhone: tap Share ⬆️ then "Add to Home Screen".');
    toast('Use your browser menu ⋮ → "Install app" or "Add to Home screen".');
  };

  function renderAll() {
    renderProfile();
    renderHeader();
    renderHabits();
    renderSky();
    renderNumbers();
    renderCookie();
    renderTipi();
    if (state.body) {
      $('inpWeightVal').value = state.body.weight;
      $('inpHeightVal').value = state.body.height;
      $('chkAsianCutoff').checked = state.body.asian !== false;
    }
    window.updateBmiCalculations();
  }

  function start() {
    initCanvas();
    window.setGlowMode('skin');
    renderAll();
    if (!state.profile) window.openBirthModal(true);
    setInterval(() => { renderSky(); renderHabits(); renderCookie(); }, 60000); // roll over at midnight and keep times fresh
  }
  // Start once the page is ready, even if this script was loaded late (e.g. by an online preview).
  if (document.readyState === 'complete') start();
  else window.addEventListener('load', start);
})();

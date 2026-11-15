// Shared behaviour for every screen: Back button, Esc (asks first), GSTIN -> PAN, pincode -> city/state.
(function () {
  const STATES = {"01":"Jammu & Kashmir","02":"Himachal Pradesh","03":"Punjab","04":"Chandigarh","05":"Uttarakhand","06":"Haryana","07":"Delhi","08":"Rajasthan","09":"Uttar Pradesh","10":"Bihar","11":"Sikkim","12":"Arunachal Pradesh","13":"Nagaland","14":"Manipur","15":"Mizoram","16":"Tripura","17":"Meghalaya","18":"Assam","19":"West Bengal","20":"Jharkhand","21":"Odisha","22":"Chhattisgarh","23":"Madhya Pradesh","24":"Gujarat","26":"Dadra & Nagar Haveli and Daman & Diu","27":"Maharashtra","29":"Karnataka","30":"Goa","31":"Lakshadweep","32":"Kerala","33":"Tamil Nadu","34":"Puducherry","35":"Andaman & Nicobar","36":"Telangana","37":"Andhra Pradesh","38":"Ladakh"};
  const GSTIN = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$/;

  // fill a box only when it is empty or we filled it earlier, so anything the user typed is never overwritten
  function autofill(input, value) {
    if (!input || !value) return;
    if (input.value.trim() === '' || input.dataset.auto === '1') { input.value = value; input.dataset.auto = '1'; }
  }
  document.querySelectorAll('input').forEach(i => i.addEventListener('input', e => { if (e.isTrusted) delete i.dataset.auto; }));

  // ---- unsaved-changes tracking (only forms that save something)
  let dirty = false;
  document.querySelectorAll('form[method="post" i]').forEach(f => {
    if (f.querySelector('select[name=theme]')) return;
    f.addEventListener('input', () => { dirty = true; });
    f.addEventListener('submit', () => { dirty = false; });
  });

  // ---- Back button and Esc
  const modalEl = document.getElementById('backModal');
  if (modalEl) {
    const modal = new bootstrap.Modal(modalEl);
    // "Back" means one level up (client -> client list -> dashboard), which stays predictable after saving a form.
    const parent = () => {
      const parts = location.pathname.split('/').filter(Boolean); parts.pop();
      if (!parts.length || ['account', 'lookup', 'trackers'].includes(parts[0]) && parts.length === 1) return AM.home;
      return '/' + parts.join('/') + (parts.length === 1 ? '/' : '');
    };
    const goBack = () => { dirty = false; location.href = parent(); };
    const ask = () => {
      document.getElementById('backMsg').textContent = dirty ? 'What you typed on this screen has not been saved and will be lost.' : '';
      modal.show();
    };
    document.getElementById('backYes').addEventListener('click', goBack);
    modalEl.addEventListener('shown.bs.modal', () => document.getElementById('backYes').focus());
    const btn = document.getElementById('backBtn');
    if (btn) btn.addEventListener('click', () => { dirty ? ask() : goBack(); });
    document.addEventListener('keydown', e => {
      if (e.key !== 'Escape' || AM.isHome) return;
      if (document.querySelector('.modal.show, .dropdown-menu.show')) return;   // Esc closes the open pop-up first
      e.preventDefault(); ask();
    });
  }

  // ---- GSTIN -> PAN (and state), on every form that has both boxes
  [['gstin', 'pan'], ['firm_gstin', 'firm_pan']].forEach(([gName, pName]) => {
    document.querySelectorAll('input[name="' + gName + '"]').forEach(g => {
      const form = g.form; if (!form) return;
      const pan = form.querySelector('input[name="' + pName + '"]');
      const state = form.querySelector('input[name="state"]');
      const reg = form.querySelector('input[name="is_gst_registered"]');
      const run = () => {
        g.value = g.value.toUpperCase().replace(/\s/g, '');
        if (!GSTIN.test(g.value)) return;
        autofill(pan, g.value.substring(2, 12));
        autofill(state, STATES[g.value.substring(0, 2)]);
        if (reg) reg.checked = true;
      };
      g.addEventListener('input', run); g.addEventListener('change', run);
    });
  });
  document.querySelectorAll('input[name="pan"], input[name="firm_pan"], input[name="tan"]').forEach(p => p.addEventListener('input', () => { p.value = p.value.toUpperCase(); }));

  // ---- Pincode -> city and state (both stay editable)
  document.querySelectorAll('input[name="pincode"]').forEach(pin => {
    const form = pin.form; if (!form) return;
    const city = form.querySelector('input[name="city"]'), state = form.querySelector('input[name="state"]');
    let last = '';
    const run = async () => {
      const v = pin.value.replace(/\D/g, '');
      if (v.length !== 6 || v === last) return;
      last = v;
      try {
        const r = await fetch('/lookup/pincode/' + v); const d = await r.json();
        if (d.ok) { autofill(city, d.city); autofill(state, d.state); }
      } catch (err) { /* offline: the user types city and state */ }
    };
    pin.addEventListener('input', run); pin.addEventListener('blur', run);
  });

  // ---- "Fetch from GST portal" (client form). The captcha is typed by the user.
  const fetchBtn = document.getElementById('gstFetchBtn');
  if (fetchBtn) {
    const form = fetchBtn.closest('form'), gst = form.querySelector('input[name="gstin"]');
    const el = document.getElementById('gstModal'), modal = new bootstrap.Modal(el);
    const img = document.getElementById('gstCaptchaImg'), box = document.getElementById('gstCaptcha'), msg = document.getElementById('gstMsg'), go = document.getElementById('gstGo');
    const say = (t, bad) => { msg.textContent = t; msg.className = 'small mt-2 ' + (bad ? 'text-danger' : 'text-muted'); };
    const loadCaptcha = async () => {
      box.value = ''; say('Loading captcha from the GST portal...');
      try {
        const r = await fetch('/lookup/gst/captcha?t=' + Date.now());
        if (!r.ok) { const d = await r.json().catch(() => ({})); say(d.message || 'Could not load the captcha.', true); return; }
        img.src = URL.createObjectURL(await r.blob()); say('Type the characters shown and press Enter.'); box.focus();
      } catch (err) { say('Could not reach the GST portal. Check the internet connection.', true); }
    };
    fetchBtn.addEventListener('click', () => {
      gst.value = gst.value.toUpperCase().trim();
      if (!GSTIN.test(gst.value)) { alert('Type a valid 15-character GSTIN first.'); gst.focus(); return; }
      document.getElementById('gstFor').textContent = gst.value; modal.show(); loadCaptcha();
    });
    document.getElementById('gstNew').addEventListener('click', loadCaptcha);
    const submit = async () => {
      if (!box.value.trim()) { box.focus(); return; }
      go.disabled = true; say('Fetching details...');
      try {
        const r = await fetch('/lookup/gst', {method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRF-Token': AM.csrf}, body: JSON.stringify({gstin: gst.value, captcha: box.value.trim()})});
        const d = await r.json();
        if (!d.ok) { say(d.message || 'Could not fetch details.', true); if (d.captcha) await loadCaptcha().then(() => say(d.message, true)); return; }
        const set = (n, v) => { const i = form.querySelector('[name="' + n + '"]'); if (i && v) { i.value = v; i.dataset.auto = '1'; } };
        set('name', d.name); set('pan', d.pan); set('address', d.address); set('city', d.city); set('state', d.state); set('pincode', d.pincode);
        const reg = form.querySelector('input[name="is_gst_registered"]'); if (reg) reg.checked = true;
        const notes = form.querySelector('[name="notes"]');
        const extra = [d.legal_name && d.legal_name !== d.name ? 'Legal name: ' + d.legal_name : '', d.constitution, d.status ? 'GST status: ' + d.status : '', d.registered_on ? 'Registered: ' + d.registered_on : ''].filter(Boolean).join(' | ');
        if (notes && extra && !notes.value.includes(extra)) notes.value = (notes.value ? notes.value + '\n' : '') + extra;
        form.dispatchEvent(new Event('input')); modal.hide();
        const info = document.getElementById('gstInfo'); if (info) info.textContent = 'Filled from the GST portal' + (d.status ? ' (status: ' + d.status + ')' : '') + '. Check and edit anything before saving.';
      } catch (err) { say('Could not reach the GST portal. Try again.', true); }
      finally { go.disabled = false; }
    };
    go.addEventListener('click', submit);
    box.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); submit(); } });
  }
})();

// ---- Record counts under every grid ("Showing 25 of 140 records")
(function () {
  document.querySelectorAll('.card-box table.table, table.table.counted').forEach(t => {
    if (t.dataset.nocount || t.closest('.cal') || t.classList.contains('cal') || t.closest('.modal')) return;
    const body = t.tBodies[0]; if (!body || !t.tHead) return;
    const shown = Array.from(body.rows).filter(r => !r.querySelector('td[colspan]')).length;
    const total = t.dataset.total ? parseInt(t.dataset.total, 10) : shown;
    const note = document.createElement('div');
    note.className = 'small text-muted px-2 py-1 border-top no-print grid-count';
    note.textContent = total > shown ? 'Showing ' + shown + ' of ' + total + ' records' : shown + (shown === 1 ? ' record' : ' records');
    (t.closest('.table-responsive') || t).after(note);
  });
})();

// ---- "Browse" for folders: only inside the desktop window on the host PC (a web browser cannot pick a folder path)
(function () {
  const buttons = document.querySelectorAll('.browse-folder'); if (!buttons.length) return;
  const enable = () => { if (!(window.pywebview && window.pywebview.api && window.pywebview.api.pick_folder)) return;
    buttons.forEach(b => { b.style.display = ''; b.onclick = async () => { try { const p = await window.pywebview.api.pick_folder(); if (p) { const i = document.getElementById(b.dataset.target); i.value = p; i.dispatchEvent(new Event('input', {bubbles: true})); } } catch (e) {} }; }); };
  window.addEventListener('pywebviewready', enable); enable();
})();

// ---- Downloads inside the desktop window: save to the Downloads folder and open, with a visible confirmation.
(function () {
  const toast = (html, bad) => { const box = document.getElementById('amToast'); if (!box) return;
    box.innerHTML = '<div class="alert ' + (bad ? 'alert-danger' : 'alert-success') + ' shadow small mb-0">' + html + '</div>'; setTimeout(() => { box.innerHTML = ''; }, 9000); };
  const isDownload = a => a.dataset.download === '1' || /\/export\.(pdf|xlsx|csv)|\/pdf(\?|$)|template\.xlsx|\/settings\/backup(\?|$)/.test(a.getAttribute('href') || '');
  document.addEventListener('click', async e => {
    const a = e.target.closest('a[href]'); if (!a || !isDownload(a)) return;
    if (!window.pywebview) return;                       // an ordinary browser downloads the normal way
    e.preventDefault();
    const url = a.href + (a.href.includes('?') ? '&' : '?') + 'save=1';
    toast('Preparing the file...');
    try {
      const r = await fetch(url); const type = r.headers.get('Content-Type') || '';
      if (type.includes('application/json')) { const d = await r.json();
        if (d.ok) toast('<strong>Saved:</strong> ' + d.path.replace(/</g, '&lt;') + (d.opened ? '<br>It has been opened for you.' : '<br>Open it from your Downloads folder.'));
        else toast(d.message || 'Could not save the file.', true);
      } else { window.location.href = a.href; }          // window connected to another PC: fall back to a normal download
    } catch (err) { toast('Could not prepare the file. Try again.', true); }
  });
})();

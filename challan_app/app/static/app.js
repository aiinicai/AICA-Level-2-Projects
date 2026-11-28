(function () {
  const csrf = document.querySelector('meta[name=csrf]')?.content || '';
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const esc = s => String(s).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));

  // confirm dialogs for dangerous buttons: <form data-confirm="...">
  document.addEventListener('submit', e => {
    const m = e.target.dataset.confirm;
    if (m && !confirm(m)) e.preventDefault();
  });

  // ------------------------------------------------------------ challan form
  const form = $('#challan-form');
  if (!form) return;
  const ctype = form.dataset.ctype, isAdmin = form.dataset.admin === '1';
  const vq = $('#vendor_q'), vid = $('#vendor_id'), sugg = $('#vendor_sugg'), info = $('#vendor_info');
  const pos = $('#place_of_supply'), plant = $('#plant_id');
  let timer, vendorState = '';

  function showVendor(v) {
    vid.value = v.id; vq.value = v.name + ' (' + v.vendor_no + ')'; sugg.hidden = true; vendorState = v.state_code;
    let h = `<b>${esc(v.vendor_no)}</b> · GSTIN: ${esc(v.gstin || 'unregistered')} · State: ${esc(v.state_code)} - ${esc(v.state)}`;
    if (v.erp_code) {
      h += `<br><b>ERP code: ${esc(v.erp_code)}</b>`;
      if (ctype === 'MRC') h += isAdmin
        ? '<br>⚠ This vendor is set up in the ERP. Returnable challans should come from the ERP - you may proceed only because you are Admin.'
        : `<br>⛔ This vendor is now set up in the ERP (Vendor Code: ${esc(v.erp_code)}). Please generate the returnable challan from the ERP system.`;
    }
    info.innerHTML = h; info.className = 'muted' + (v.erp_code && ctype === 'MRC' ? ' errors' : '');
    if (!pos.value || pos.dataset.auto === '1') { pos.value = v.state_code; pos.dataset.auto = '1'; }
    supplyType();
  }

  async function search() {
    const q = vq.value.trim(); vid.value = ''; info.textContent = '';
    if (!q) { sugg.hidden = true; return; }
    const r = await fetch('/api/vendors/search?q=' + encodeURIComponent(q));
    const list = await r.json();
    sugg.innerHTML = list.map(v => `<div data-id="${v.id}">${esc(v.name)} <span class="muted">${esc(v.vendor_no)} · ${esc(v.gstin || 'no GSTIN')}${v.erp_code ? ' · ERP ' + esc(v.erp_code) : ''}</span></div>`).join('') +
      `<div class="new" data-new="1">＋ "${esc(q)}" is not in the vendor master - add as a new vendor…</div>`;
    sugg.hidden = false;
    $$('div', sugg).forEach((d, i) => d.onclick = () => d.dataset.new ? openModal(q) : showVendor(list[i]));
  }
  vq.addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(search, 200); });
  vq.addEventListener('focus', () => { if (!vid.value) search(); });
  document.addEventListener('click', e => { if (!e.target.closest('.pos')) sugg.hidden = true; });
  if (vid.value && vq.dataset.init) showVendor(JSON.parse(vq.dataset.init));

  // ------------------------------------------------------------ quick-add vendor modal
  const modal = $('#vendor-modal');
  function openModal(name) {
    sugg.hidden = true;
    if (!confirm(`"${name}" is not in the vendor master.\n\nThis will be added as a NEW vendor. Continue?`)) return;
    $('#qa_name').value = name; $('#qa_msg').innerHTML = ''; $('#qa_confirm').checked = false;
    modal.style.display = 'flex';
  }
  $('#qa_cancel').onclick = () => modal.style.display = 'none';
  $('#qa_gstin').addEventListener('input', e => {
    const g = e.target.value.trim().toUpperCase();
    if (g.length >= 2 && $('#qa_state option[value="' + g.slice(0, 2) + '"]')) $('#qa_state').value = g.slice(0, 2);
  });
  $('#qa_save').onclick = async () => {
    const body = {confirm_similar: $('#qa_confirm').checked};
    ['name', 'address', 'pin', 'gstin', 'contact_person', 'phone', 'email'].forEach(k => body[k] = $('#qa_' + k).value);
    body.state_code = $('#qa_state').value;
    const r = await fetch('/api/vendors/quick-add', {method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrf}, body: JSON.stringify(body)});
    const d = await r.json(), msg = $('#qa_msg');
    if (d.ok) { modal.style.display = 'none'; showVendor(d.vendor); return; }
    if (d.needs_confirm) {
      msg.innerHTML = '<div class="errors warn">Similar vendors already exist: ' + d.similar.map(v => esc(v.name) + ' (' + esc(v.vendor_no) + ')').join(', ') +
        '. If this really is a different vendor tick the box below and save again. Otherwise cancel and pick the existing one.</div>';
      $('#qa_confirm_row').style.display = 'block'; return;
    }
    msg.innerHTML = '<ul class="errors">' + d.errors.map(e => '<li>' + esc(e) + '</li>').join('') + '</ul>';
  };

  // ------------------------------------------------------------ supply type + lines
  function supplyType() {
    const ps = plant.selectedOptions[0]?.dataset.state, p = pos.value, box = $('#supply_type');
    if (!ps || !p) { box.textContent = ''; return; }
    box.textContent = ps === p ? 'Intra-state supply: CGST + SGST/UTGST will be charged' : 'Inter-state supply: IGST will be charged';
    recalc();
  }
  pos.addEventListener('change', () => { pos.dataset.auto = '0'; supplyType(); });
  plant.addEventListener('change', supplyType);

  const tbody = $('#lines tbody'), tpl = $('#line-tpl');
  function addLine(vals) {
    const tr = tpl.content.firstElementChild.cloneNode(true);
    if (vals) $$('[data-f]', tr).forEach(i => { if (vals[i.dataset.f] !== undefined) i.value = vals[i.dataset.f]; });
    tbody.appendChild(tr); renumber();
  }
  function renumber() { $$('tr', tbody).forEach((tr, i) => $('.sl', tr).textContent = i + 1); recalc(); }
  $('#add-line').onclick = () => addLine();
  tbody.addEventListener('click', e => { if (e.target.classList.contains('rm') && tbody.children.length > 1) { e.target.closest('tr').remove(); renumber(); } });
  tbody.addEventListener('input', recalc);
  const fmt = n => n.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2});
  function recalc() {
    const inter = plant.selectedOptions[0]?.dataset.state !== pos.value;
    let taxable = 0, tax = 0, cess = 0;
    $$('tr', tbody).forEach(tr => {
      const g = f => parseFloat($('[data-f=' + f + ']', tr).value) || 0;
      const t = Math.round(g('qty') * g('rate') * 100) / 100;
      taxable += t; tax += t * g('tax_rate') / 100; cess += t * g('cess_rate') / 100;
      $('.tv', tr).textContent = fmt(t);
    });
    $('#tot').textContent = `Taxable ${fmt(taxable)} · ${inter ? 'IGST' : 'CGST+SGST'} ${fmt(tax)} · Cess ${fmt(cess)} · Total ${fmt(taxable + tax + cess)}`;
  }
  const init = JSON.parse($('#init-lines').textContent || '[]');
  (init.length ? init : [{}]).forEach(v => addLine(v));
  if (form.dataset.locked === '1') $$('input', tbody).forEach(i => i.readOnly = true);
  supplyType();
})();


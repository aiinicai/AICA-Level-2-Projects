// ============================================================
// CA FIRM INTRANET - MAIN JS
// ============================================================

// ── PAN Auto-detect Constitution ───────────────────────────
function detectConstitutionFromPAN(pan) {
  if (!pan || pan.length < 4) return '';
  const map = {
    'P': 'Individual', 'H': 'HUF', 'F': 'Firm/LLP',
    'C': 'Company',    'A': 'AOP', 'B': 'BOI',
    'G': 'Government', 'J': 'Artificial Juridical Person',
    'L': 'Local Authority', 'T': 'Trust'
  };
  return map[pan[3].toUpperCase()] || 'Other';
}

document.addEventListener('DOMContentLoaded', function () {

  // ── Navbar Dropdown — robust hover with 120ms close delay ────────
  // Fixes the gap between nav trigger and dropdown menu
  var dropdowns = document.querySelectorAll('.nav-dropdown');
  dropdowns.forEach(function(dd) {
    var menu = dd.querySelector('.dropdown-menu');
    var closeTimer = null;

    function openMenu() {
      clearTimeout(closeTimer);
      // Close siblings first
      dropdowns.forEach(function(other) {
        if (other !== dd) {
          var m = other.querySelector('.dropdown-menu');
          if (m) m.style.display = 'none';
        }
      });
      if (menu) menu.style.display = 'block';
    }

    function scheduleClose() {
      closeTimer = setTimeout(function() {
        if (menu) menu.style.display = 'none';
      }, 150); // 150ms grace period to move mouse to menu
    }

    dd.addEventListener('mouseenter', openMenu);
    dd.addEventListener('mouseleave', scheduleClose);
    if (menu) {
      menu.addEventListener('mouseenter', function() { clearTimeout(closeTimer); });
      menu.addEventListener('mouseleave', scheduleClose);
    }
  });

  // Close all on outside click
  document.addEventListener('click', function(e) {
    if (!e.target.closest('.nav-dropdown')) {
      dropdowns.forEach(function(dd) {
        var m = dd.querySelector('.dropdown-menu');
        if (m) m.style.display = 'none';
      });
    }
  });

  // ── PAN field auto-detection
  const panField = document.getElementById('pan');
  const constitField = document.getElementById('constitution');
  if (panField && constitField) {
    panField.addEventListener('input', function () {
      this.value = this.value.toUpperCase();
      const c = detectConstitutionFromPAN(this.value);
      if (c) {
        constitField.value = c;
        // Show/hide ROC/TAN sections based on constitution
        toggleConstitutionSections(c);
      }
    });
  }

  function toggleConstitutionSections(c) {
    const rocSection = document.getElementById('section-roc');
    const tdsSection = document.getElementById('section-tds');
    const gstSection = document.getElementById('section-gst');
    // All types can have GST
    // TDS: applicable for Company, Firm, Individual (business), etc.
    // ROC: only Company / LLP / Section 8
    if (rocSection) {
      rocSection.style.display = ['Company', 'Firm/LLP'].includes(c) ? 'block' : 'none';
    }
  }

  // ── Toggle sections in client form
  ['gst_applicable','tds_applicable','roc_applicable','itr_applicable'].forEach(function(id) {
    const el = document.getElementById(id);
    if (!el) return;
    el.addEventListener('change', function() {
      const target = document.getElementById('section-' + id.replace('_applicable',''));
      if (target) target.style.display = this.checked ? 'block' : 'none';
    });
    // Init
    const target = document.getElementById('section-' + id.replace('_applicable',''));
    if (target) target.style.display = el.checked ? 'block' : 'none';
  });

  // ── Auto-compute GST due dates
  const returnTypeEl = document.getElementById('return_type');
  const periodEl     = document.getElementById('return_period');
  const dueDateEl    = document.getElementById('due_date');
  const freqEl       = document.getElementById('gst_return_freq');
  if (returnTypeEl && periodEl && dueDateEl) {
    function computeGSTDue() {
      const type   = returnTypeEl.value;
      const period = periodEl.value;
      const freq   = freqEl ? freqEl.value : 'Monthly';
      if (!type || !period) return;
      // Simple client-side due date logic
      const dueDates = {
        'GSTR-1':  { Monthly: 11, QRMP: 13 },
        'GSTR-3B': { Monthly: 20, QRMP: 22 },
      };
      if (dueDates[type]) {
        const day = dueDates[type][freq] || dueDates[type]['Monthly'];
        // Parse "Apr-2025" format
        const parts = period.split('-');
        if (parts.length === 2) {
          const monthNames = {Jan:1,Feb:2,Mar:3,Apr:4,May:5,Jun:6,Jul:7,Aug:8,Sep:9,Oct:10,Nov:11,Dec:12};
          const m = monthNames[parts[0]];
          const y = parseInt(parts[1]);
          if (m && y) {
            // Due in NEXT month
            let dm = m + 1, dy = y;
            if (dm > 12) { dm = 1; dy++; }
            const dd = String(dy) + '-' + String(dm).padStart(2,'0') + '-' + String(day).padStart(2,'0');
            dueDateEl.value = dd;
          }
        }
      }
    }
    returnTypeEl.addEventListener('change', computeGSTDue);
    periodEl.addEventListener('change', computeGSTDue);
    if (freqEl) freqEl.addEventListener('change', computeGSTDue);
  }

  // ── Auto-compute ETDS due dates
  const etdsQtrEl = document.getElementById('etds_quarter');
  const etdsFyEl  = document.getElementById('etds_fy');
  const etdsDueEl = document.getElementById('etds_due_date');
  if (etdsQtrEl && etdsFyEl && etdsDueEl) {
    function computeETDSDue() {
      const q  = etdsQtrEl.value;
      const fy = etdsFyEl.value;
      if (!q || !fy) return;
      const fy_start = parseInt(fy.split('-')[0]);
      const map = {
        Q1: fy_start + '-07-31',
        Q2: fy_start + '-10-31',
        Q3: (fy_start+1) + '-01-31',
        Q4: (fy_start+1) + '-05-31',
      };
      if (map[q]) etdsDueEl.value = map[q];
    }
    etdsQtrEl.addEventListener('change', computeETDSDue);
    etdsFyEl.addEventListener('change', computeETDSDue);
  }

  // ── Confirm delete
  document.querySelectorAll('[data-confirm]').forEach(function(el) {
    el.addEventListener('click', function(e) {
      if (!confirm(this.dataset.confirm || 'Are you sure?')) e.preventDefault();
    });
  });

  // ── Inline status update (AJAX)
  document.querySelectorAll('.status-select').forEach(function(sel) {
    sel.addEventListener('change', function() {
      const id     = this.dataset.id;
      const module = this.dataset.module;
      const val    = this.value;
      const row    = this.closest('tr');
      fetch('/ca_intranet/api/update_status.php', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({id, module, status: val})
      })
      .then(r => r.json())
      .then(d => {
        if (d.success) {
          showToast('Status updated', 'success');
          if (row) {
            row.classList.remove('row-overdue','row-due-soon');
          }
        } else { showToast('Update failed', 'error'); this.value = this.dataset.old; }
      })
      .catch(() => showToast('Network error', 'error'));
      this.dataset.old = val;
    });
    sel.dataset.old = sel.value;
  });

  // ── Toast notification
  window.showToast = function(msg, type='info') {
    const t = document.createElement('div');
    t.className = 'toast toast-' + type;
    t.textContent = msg;
    t.style.cssText = 'position:fixed;bottom:20px;right:20px;padding:10px 18px;border-radius:6px;font-size:13px;z-index:9999;box-shadow:0 4px 12px rgba(0,0,0,.15);';
    const colors = {success:'#166534;background:#f0fdf4;border:1px solid #bbf7d0', error:'#c0392b;background:#fdf0ef;border:1px solid #fecaca', info:'#1d6fa5;background:#e8f4fc;border:1px solid #bae6fd'};
    t.style.cssText += 'color:' + (colors[type] || colors.info);
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 3000);
  };

  // ── Export table to CSV (works in Excel, LibreOffice, Google Sheets) ──
  window.exportTableToXLS = function(tableId, filename) {
    const table = document.getElementById(tableId);
    if (!table) return;

    const rows  = table.querySelectorAll('tr');
    const lines = [];

    rows.forEach(function(row) {
      const cells = row.querySelectorAll('th, td');
      if (!cells.length) return;
      const cols = [];
      cells.forEach(function(cell) {
        if (cell.classList.contains('no-export')) return;
        // Get plain text — remove any nested badge/tag formatting
        let text = cell.innerText.replace(/\n/g, ' ').replace(/\r/g, '').trim();
        // CSV-escape: wrap in quotes, escape internal quotes
        text = '"' + text.replace(/"/g, '""') + '"';
        cols.push(text);
      });
      if (cols.length) lines.push(cols.join(','));
    });

    // UTF-8 BOM so Excel opens it correctly
    const bom  = '\uFEFF';
    const csv  = bom + lines.join('\r\n');
    const blob = new Blob([csv], {type: 'text/csv; charset=utf-8'});
    const link = document.createElement('a');
    link.href     = URL.createObjectURL(blob);
    link.download = (filename || 'export') + '_' + new Date().toISOString().slice(0,10) + '.csv';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setTimeout(function() { URL.revokeObjectURL(link.href); }, 1000);
  };

  // Alias
  window.exportToExcel = window.exportTableToXLS;

  // ── Auto-uppercase PAN, TAN, GSTIN
  document.querySelectorAll('input[data-uppercase]').forEach(function(el) {
    el.addEventListener('input', function() { this.value = this.value.toUpperCase(); });
  });

  // ── GSTIN auto-fill state from GSTIN
  const gstinEl = document.getElementById('gstin');
  if (gstinEl) {
    gstinEl.addEventListener('input', function() {
      this.value = this.value.toUpperCase();
    });
  }

  // ── Modal handling
  window.openModal = function(id) {
    const m = document.getElementById(id);
    if (m) m.classList.add('active');
  };
  window.closeModal = function(id) {
    const m = document.getElementById(id);
    if (m) m.classList.remove('active');
  };
  document.querySelectorAll('.modal-overlay').forEach(function(overlay) {
    overlay.addEventListener('click', function(e) {
      if (e.target === this) this.classList.remove('active');
    });
  });

});

// ============================================================
// SHARED: Group-Filterable Client Picker
// Used in Bulk Create forms across GST / ETDS / ITR / ROC / PT registers
// Expects:
//   - a <select id="bulk_group_filter"> with group IDs as option values, each
//     client <option> carrying data-group="<group_id>"
//   - a <select multiple id="bulk_client_ids"> listing all eligible clients
//   - optional buttons calling selectAllClients() / selectNoneClients() / selectGroupClients()
// ============================================================
function filterClientsByGroup(groupSelectId, clientSelectId) {
  const groupSel  = document.getElementById(groupSelectId);
  const clientSel = document.getElementById(clientSelectId);
  if (!groupSel || !clientSel) return;
  const gid = groupSel.value;

  Array.from(clientSel.options).forEach(function(opt) {
    if (!gid) {
      opt.style.display = '';
    } else {
      opt.style.display = (opt.dataset.group === gid) ? '' : 'none';
    }
  });
}

function selectAllVisibleClients(clientSelectId) {
  const sel = document.getElementById(clientSelectId);
  if (!sel) return;
  Array.from(sel.options).forEach(function(opt) {
    if (opt.style.display !== 'none') opt.selected = true;
  });
}

function selectNoneClients(clientSelectId) {
  const sel = document.getElementById(clientSelectId);
  if (!sel) return;
  Array.from(sel.options).forEach(function(opt) { opt.selected = false; });
}

function updateClientSelectionCount(clientSelectId, countElId) {
  const sel = document.getElementById(clientSelectId);
  const out = document.getElementById(countElId);
  if (!sel || !out) return;
  const n = Array.from(sel.selectedOptions).length;
  out.textContent = n + ' client' + (n === 1 ? '' : 's') + ' selected';
}

(() => {
  'use strict';

  const {
    PDFDocument, StandardFonts, rgb, degrees, PDFName, PDFHexString, PDFString
  } = PDFLib;

  const A4 = [595.28, 841.89];
  const DETAIL_COLUMNS = {
    documentDate: ['Date', 'DD-MMM-YYYY'], documentType: ['Type', 'Example: Show Cause Notice'],
    referenceNumber: ['Reference No.', 'Example: ZD1902250474691'], issuedBy: ['Issued by', 'Example: Deputy Commissioner, Kolkata'],
    financialYear: ['Financial year', 'Example: 2021-22'], taxPeriod: ['Tax period', 'Example: Apr-2021 to Mar-2022'],
    issues: ['Issue', 'Example: ITC mismatch'], remarks: ['Remarks', 'Optional note']
  };
  const state = {
    documents: [], nextId: 1, stampBytes: null, stampKind: null,
    revision: 1, previewRevision: 0, previewVolumes: [], previewUrls: [], previewJumps: [],
    visibleDetailColumns: [], chronologyRows: [], chronologyColumns: [
      { key:'date', label:'Date' }, { key:'event', label:'Event / Description' },
      { key:'referenceNumber', label:'Reference No.' }, { key:'annexure', label:'Annexure' }
    ],
    customDetailColumns: [], nextChronologyId: 1, referenceResults: [], appealDraft: null,
    editorDocId: null, editorWorkingPlan: null, editorHistory: [],
    // Original page numbers selected in the optional bulk page editor. Keeping
    // source-page identities (rather than tile positions) makes selection stay
    // correct after a reorder.
    editorSelectedPages: new Set(), draggedDocumentId: null
  };
  if (globalThis.pdfjsLib) pdfjsLib.GlobalWorkerOptions.workerSrc = 'app/vendor/pdf.worker.min.js';
  const THEMES = {
    red: {
      accent: rgb(0.75, 0.04, 0.07),
      header: rgb(0.82, 0.04, 0.07),
      link: rgb(0.66, 0.04, 0.07),
      highlight: rgb(0.98, 0.90, 0.91)
    },
    blue: {
      accent: rgb(0.04, 0.22, 0.62),
      header: rgb(0.03, 0.18, 0.52),
      link: rgb(0.03, 0.20, 0.58),
      highlight: rgb(0.89, 0.93, 0.99)
    },
    navy: {
      accent: rgb(0.03, 0.12, 0.35), header: rgb(0.03, 0.12, 0.35),
      link: rgb(0.03, 0.16, 0.48), highlight: rgb(0.91, 0.94, 0.98)
    },
    maroon: {
      accent: rgb(0.42, 0.03, 0.12), header: rgb(0.42, 0.03, 0.12),
      link: rgb(0.48, 0.04, 0.14), highlight: rgb(0.98, 0.91, 0.93)
    },
    green: {
      accent: rgb(0.02, 0.33, 0.20), header: rgb(0.02, 0.29, 0.18),
      link: rgb(0.02, 0.35, 0.21), highlight: rgb(0.90, 0.97, 0.93)
    },
    black: {
      accent: rgb(0.10, 0.11, 0.13),
      header: rgb(0.12, 0.13, 0.15),
      link: rgb(0.10, 0.11, 0.13),
      highlight: rgb(0.91, 0.92, 0.93)
    }
  };

  function getTheme(settings) {
    if (settings.layoutStyle === 'minimal') return THEMES.black;
    return THEMES[settings.accentColor] || THEMES.red;
  }

  const $ = (id) => document.getElementById(id);
  const ui = {
    fileInput: $('fileInput'), dropZone: $('dropZone'), documentsBody: $('documentsBody'),
    generateButton: $('generateButton'), progressPanel: $('progressPanel'),
    progressBar: $('progressBar'), progressText: $('progressText'), resultPanel: $('resultPanel'),
    validationList: $('validationList')
  };

  function showPanel(panelId) {
    document.querySelectorAll('.panel').forEach(p => p.classList.toggle('active', p.id === panelId));
    document.querySelectorAll('.step').forEach(s => s.classList.toggle('active', s.dataset.panel === panelId));
    if (panelId === 'outputPanel') updateValidation();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function markChanged() {
    state.revision += 1;
    if (state.previewRevision && state.previewRevision !== state.revision) {
      $('previewStatus').textContent = 'Preview out of date';
      $('previewStatus').className = 'status-pill stale';
    }
  }

  document.addEventListener('input', e => {
    if (!['previewVolume'].includes(e.target.id)) markChanged();
  });
  document.addEventListener('change', e => {
    if (!['previewVolume'].includes(e.target.id)) markChanged();
  });

  document.querySelectorAll('[data-panel]').forEach(btn => btn.addEventListener('click', () => showPanel(btn.dataset.panel)));
  document.querySelectorAll('[data-next]').forEach(btn => btn.addEventListener('click', () => showPanel(btn.dataset.next)));

  ui.fileInput.addEventListener('change', (e) => addFiles([...e.target.files]));
  ui.dropZone.addEventListener('click', () => ui.fileInput.click());
  ui.dropZone.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') ui.fileInput.click(); });
  ['dragenter', 'dragover'].forEach(type => ui.dropZone.addEventListener(type, e => {
    e.preventDefault(); ui.dropZone.classList.add('drag');
  }));
  ['dragleave', 'drop'].forEach(type => ui.dropZone.addEventListener(type, e => {
    e.preventDefault(); ui.dropZone.classList.remove('drag');
  }));
  ui.dropZone.addEventListener('drop', e => addFiles([...e.dataTransfer.files]));
  ui.generateButton.addEventListener('click', () => generatePaperBook('final'));
  $('previewButton').addEventListener('click', () => generatePaperBook('preview'));
  $('refreshPreview').addEventListener('click', () => generatePaperBook('preview'));
  $('previewVolume').addEventListener('change', showSelectedPreviewVolume);
  if ($('previewJump')) $('previewJump').addEventListener('change', showSelectedPreviewJump);
  if ($('outputMode')) $('outputMode').addEventListener('change', () => {
    if (!ui.generateButton.disabled) ui.generateButton.textContent = generateButtonLabel();
  });
  $('toggleMoreDetails').addEventListener('click', () => $('moreDetailsPanel').classList.toggle('hidden'));
  $('closeMoreDetails').addEventListener('click', () => $('moreDetailsPanel').classList.add('hidden'));
  document.querySelectorAll('.optionalColumn').forEach(box => box.addEventListener('change', updateVisibleDetailColumns));
  $('createChronology').addEventListener('click', openChronology);
  $('addDocumentColumn').addEventListener('click', addDocumentDetailColumn);
  $('downloadIssueList').addEventListener('click', downloadIssueList);
  $('closeChronology').addEventListener('click', () => $('chronologyPanel').classList.add('hidden'));
  $('addChronologyRow').addEventListener('click', addChronologyRow);
  $('addChronologyColumn').addEventListener('click', addChronologyColumn);
  $('sortChronology').addEventListener('click', sortChronology);
  $('refreshChronology').addEventListener('click', () => buildChronologyFromDocuments(true));
  $('downloadChronologyCsv').addEventListener('click', downloadChronologyCsv);
  $('openReferenceChecker').addEventListener('click', () => $('referencePanel').classList.remove('hidden'));
  $('closeReferenceChecker').addEventListener('click', () => $('referencePanel').classList.add('hidden'));
  $('appealDraftFile').addEventListener('change', e => { state.appealDraft = e.target.files && e.target.files[0] || null; $('referenceStatus').textContent = state.appealDraft ? state.appealDraft.name : 'Upload a draft to begin.'; });
  $('runReferenceCheck').addEventListener('click', runReferenceCheck);
  $('downloadReferenceReport').addEventListener('click', downloadReferenceReport);
  $('closePageEditor').addEventListener('click', closePageEditor);
  $('undoPageEdit').addEventListener('click', undoPageEdit);
  $('resetPageEdit').addEventListener('click', resetPageEdit);
  $('applyPageEdit').addEventListener('click', applyPageEdit);
  bindOptionalClick('selectPageRange', selectEditorPageRange);
  bindOptionalClick('selectAllPages', () => selectAllEditorPages(true));
  bindOptionalClick('clearPageSelection', () => selectAllEditorPages(false));
  bindOptionalClick('bulkRotateLeft', () => bulkEditSelectedPages('left'));
  bindOptionalClick('bulkRotateRight', () => bulkEditSelectedPages('right'));
  bindOptionalClick('bulkRemovePages', () => bulkEditSelectedPages('remove'));
  bindOptionalClick('bulkRestorePages', () => bulkEditSelectedPages('restore'));
  bindOptionalClick('bulkMovePagesUp', () => bulkEditSelectedPages('up'));
  bindOptionalClick('bulkMovePagesDown', () => bulkEditSelectedPages('down'));
  bindOptionalClick('bulkMovePagesStart', () => bulkEditSelectedPages('start'));
  bindOptionalClick('bulkMovePagesEnd', () => bulkEditSelectedPages('end'));
  $('appealType').addEventListener('change', () => $('customAppealTypeWrap').classList.toggle('hidden', $('appealType').value !== 'custom'));
  $('annexurePrefix').addEventListener('change', updateAnnexureModeUI);
  $('annexureMode').addEventListener('change', updateAnnexureModeUI);
  $('applyAnnexureNumbering').addEventListener('click', applyAnnexureNumbering);
  $('stampFile').addEventListener('change', async e => {
    const file = e.target.files && e.target.files[0];
    if (!file) { state.stampBytes = null; state.stampKind = null; return; }
    state.stampBytes = new Uint8Array(await file.arrayBuffer());
    state.stampKind = /png/i.test(file.type || file.name) ? 'png' : 'jpg';
  });

  function bindOptionalClick(id, handler) {
    const element = $(id);
    if (element) element.addEventListener('click', handler);
  }

  function updateAnnexureModeUI() {
    const mixed = $('annexureMode').value === 'main_then_annexure';
    document.querySelectorAll('.single-series-control').forEach(label => label.classList.toggle('inactive', mixed));
    $('annexurePrefix').disabled = mixed;
    $('annexureSeries').disabled = mixed;
    $('customAnnexurePrefix').disabled = mixed;
    $('customAnnexurePrefixWrap').classList.toggle('hidden', mixed || $('annexurePrefix').value !== 'custom');
    $('mainDocumentCount').disabled = !mixed;
    $('mainDocumentCountWrap').classList.toggle('inactive', !mixed);
  }

  function applyAnnexureNumbering() {
    const start = Math.max(1, Number($('annexureStart').value) || 1);
    const mode = $('annexureMode') ? $('annexureMode').value : 'single';
    if (mode === 'main_then_annexure') {
      const mainCount = Math.max(0, Number($('mainDocumentCount').value) || 0);
      state.documents.forEach((doc, i) => {
        doc.annexure = i < mainCount ? String(start + i) : `A${start + i - mainCount}`;
      });
      renderDocuments();
      markChanged();
      return;
    }
    let prefix = $('annexurePrefix').value;
    if (prefix === 'custom') prefix = $('customAnnexurePrefix').value;
    state.documents.forEach((doc, i) => { doc.annexure = `${prefix}${seriesValue(start + i, $('annexureSeries').value)}`; });
    renderDocuments();
    markChanged();
  }

  function seriesValue(value, series) {
    if (series === 'upper_alpha' || series === 'lower_alpha') {
      let n = value, out = '';
      while (n > 0) { n--; out = String.fromCharCode(65 + (n % 26)) + out; n = Math.floor(n / 26); }
      return series === 'lower_alpha' ? out.toLowerCase() : out;
    }
    if (series === 'upper_roman' || series === 'lower_roman') {
      const map = [[1000,'M'],[900,'CM'],[500,'D'],[400,'CD'],[100,'C'],[90,'XC'],[50,'L'],[40,'XL'],[10,'X'],[9,'IX'],[5,'V'],[4,'IV'],[1,'I']];
      let n = value, out = '';
      map.forEach(([v, s]) => { while (n >= v) { out += s; n -= v; } });
      return series === 'lower_roman' ? out.toLowerCase() : out;
    }
    return String(value);
  }

  async function addFiles(files) {
    const accepted = files.filter(file => /\.(pdf|jpe?g|png)$/i.test(file.name));
    if (!accepted.length) {
      alert('Please add PDF, JPG or PNG files.');
      return;
    }

    for (const file of accepted) {
      const item = {
        id: state.nextId++, file, name: file.name, bytes: null,
        annexure: `A-${state.documents.length + 1}`,
        particulars: baseName(file.name), pageCount: '…', originalPageCount: 0,
        pagePlan: [], details: Object.fromEntries(Object.keys(DETAIL_COLUMNS).map(k => [k, ''])),
        risk: { signed:false, forms:false, annotations:false }, error: '', type: file.type
      };
      state.documents.push(item);
      renderDocuments();
      try {
        const bytes = new Uint8Array(await file.arrayBuffer());
        item.bytes = bytes;
        if (/\.pdf$/i.test(file.name)) {
          const doc = await PDFDocument.load(bytes, { updateMetadata: false });
          item.pageCount = doc.getPageCount();
          item.originalPageCount = item.pageCount;
          item.pagePlan = Array.from({ length: item.pageCount }, (_, index) => ({ sourcePage:index, included:true, rotation:0 }));
          item.risk = detectPdfRisks(bytes);
          item.kind = 'pdf';
        } else {
          item.pageCount = 1;
          item.originalPageCount = 1;
          item.pagePlan = [{ sourcePage:0, included:true, rotation:0 }];
          item.kind = /\.png$/i.test(file.name) ? 'png' : 'jpg';
        }
      } catch (err) {
        item.pageCount = 'Error';
        item.error = friendlyError(err);
      }
      renderDocuments();
    }
    if ($('autoRenumber').checked) applyAnnexureNumbering();
    markChanged();
    ui.fileInput.value = '';
  }

  function renderDocuments() {
    const header = $('documentsHeaderRow');
    header.innerHTML = '<th>#</th><th>Annexure</th><th>Particulars</th><th>File</th><th>Pages</th>'
      + state.visibleDetailColumns.map(key => `<th>${escapeHtml(DETAIL_COLUMNS[key][0])}</th>`).join('')
      + '<th>Actions</th>';
    ui.documentsBody.innerHTML = '';
    if (!state.documents.length) {
      ui.documentsBody.innerHTML = `<tr><td colspan="${6 + state.visibleDetailColumns.length}" class="empty">No files added.</td></tr>`;
      return;
    }
    state.documents.forEach((doc, index) => {
      const row = document.createElement('tr');
      row.className = 'document-row';
      row.dataset.docId = String(doc.id);
      const riskLabel = doc.risk.signed ? '<br><small style="color:#9a6700">Signed original - keep separately</small>' : '';
      const detailCells = state.visibleDetailColumns.map(key => {
        const hint = DETAIL_COLUMNS[key][1];
        return `<td><input data-detail="${key}" data-id="${doc.id}" value="${escapeHtml(doc.details[key] || '')}" placeholder="${escapeHtml(hint)}"></td>`;
      }).join('');
      row.innerHTML = `
        <td><span class="drag-handle" draggable="true" data-drag-id="${doc.id}" title="Drag to rearrange" aria-label="Drag document ${index + 1}">☰ ${index + 1}</span></td>
        <td><input data-field="annexure" data-id="${doc.id}" value="${escapeHtml(doc.annexure)}"></td>
        <td><input class="particulars" data-field="particulars" data-id="${doc.id}" value="${escapeHtml(doc.particulars)}"></td>
        <td title="${escapeHtml(doc.error || doc.name)}">${escapeHtml(doc.name)}${riskLabel}${doc.error ? '<br><small style="color:#b42318">' + escapeHtml(doc.error) + '</small>' : ''}</td>
        <td>${effectivePageCount(doc)}${doc.originalPageCount && doc.originalPageCount !== effectivePageCount(doc) ? ` of ${doc.originalPageCount}` : ''}</td>
        ${detailCells}
        <td>
          <button class="icon-btn" data-action="edit-pages" data-id="${doc.id}" title="Edit pages">Edit pages</button>
          <button class="icon-btn" data-action="up" data-id="${doc.id}" title="Move up">↑</button>
          <button class="icon-btn" data-action="down" data-id="${doc.id}" title="Move down">↓</button>
          <button class="icon-btn danger" data-action="remove" data-id="${doc.id}" title="Remove">×</button>
        </td>`;
      ui.documentsBody.appendChild(row);
    });

    ui.documentsBody.querySelectorAll('input[data-field]').forEach(input => input.addEventListener('input', e => {
      const doc = state.documents.find(d => d.id === Number(e.target.dataset.id));
      if (doc) { doc[e.target.dataset.field] = e.target.value; markChanged(); }
    }));
    ui.documentsBody.querySelectorAll('input[data-detail]').forEach(input => input.addEventListener('change', e => {
      const doc = state.documents.find(d => d.id === Number(e.target.dataset.id));
      if (!doc) return;
      const key = e.target.dataset.detail;
      doc.details[key] = key === 'documentDate' ? normaliseDateInput(e.target.value, e.target) : e.target.value;
      e.target.value = doc.details[key]; markChanged();
    }));
    ui.documentsBody.querySelectorAll('button[data-action]').forEach(button => button.addEventListener('click', e => {
      const id = Number(e.currentTarget.dataset.id);
      const index = state.documents.findIndex(d => d.id === id);
      if (index < 0) return;
      const action = e.currentTarget.dataset.action;
      if (action === 'edit-pages') { openPageEditor(id); return; }
      if (action === 'remove') state.documents.splice(index, 1);
      if (action === 'up' && index > 0) [state.documents[index - 1], state.documents[index]] = [state.documents[index], state.documents[index - 1]];
      if (action === 'down' && index < state.documents.length - 1) [state.documents[index + 1], state.documents[index]] = [state.documents[index], state.documents[index + 1]];
      if ($('autoRenumber').checked) applyAnnexureNumbering();
      else renderDocuments();
      markChanged();
    }));
    bindDocumentDragAndDrop();
  }

  function bindDocumentDragAndDrop() {
    ui.documentsBody.querySelectorAll('.drag-handle').forEach(handle => handle.addEventListener('dragstart', e => {
      state.draggedDocumentId = Number(e.currentTarget.dataset.dragId);
      e.dataTransfer.effectAllowed = 'move';
      e.dataTransfer.setData('text/plain', String(state.draggedDocumentId));
      e.currentTarget.closest('.document-row')?.classList.add('dragging');
    }));
    ui.documentsBody.querySelectorAll('.drag-handle').forEach(handle => handle.addEventListener('dragend', e => {
      e.currentTarget.closest('.document-row')?.classList.remove('dragging');
      ui.documentsBody.querySelectorAll('.document-row').forEach(clearDocumentDropMarker);
      state.draggedDocumentId = null;
    }));
    ui.documentsBody.querySelectorAll('.document-row').forEach(row => {
      row.addEventListener('dragover', e => {
        if (!state.draggedDocumentId || Number(row.dataset.docId) === state.draggedDocumentId) return;
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        const after = e.clientY > row.getBoundingClientRect().top + row.getBoundingClientRect().height / 2;
        ui.documentsBody.querySelectorAll('.document-row').forEach(clearDocumentDropMarker);
        row.classList.add(after ? 'drag-over-after' : 'drag-over-before');
      });
      row.addEventListener('dragleave', () => clearDocumentDropMarker(row));
      row.addEventListener('drop', e => {
        e.preventDefault();
        const draggedId = state.draggedDocumentId || Number(e.dataTransfer.getData('text/plain'));
        const targetId = Number(row.dataset.docId);
        const after = e.clientY > row.getBoundingClientRect().top + row.getBoundingClientRect().height / 2;
        reorderDocumentByDrop(draggedId, targetId, after);
      });
    });
  }

  function clearDocumentDropMarker(row) {
    row.classList.remove('drag-over-before', 'drag-over-after');
  }

  function reorderDocumentByDrop(draggedId, targetId, after) {
    if (!draggedId || draggedId === targetId) return;
    const from = state.documents.findIndex(doc => doc.id === draggedId);
    if (from < 0) return;
    const [moved] = state.documents.splice(from, 1);
    let target = state.documents.findIndex(doc => doc.id === targetId);
    if (target < 0) { state.documents.splice(from, 0, moved); return; }
    if (after) target += 1;
    state.documents.splice(target, 0, moved);
    if ($('autoRenumber').checked) applyAnnexureNumbering(); else renderDocuments();
    markChanged();
  }

  function updateVisibleDetailColumns() {
    const standard = [...document.querySelectorAll('.optionalColumn:checked')].map(box => box.value);
    state.visibleDetailColumns = [...standard, ...state.customDetailColumns.map(c=>c.key)];
    renderDocuments(); markChanged();
  }

  function addDocumentDetailColumn() {
    const label=prompt('Column name (example: Remarks by counsel)'); if(!label||!label.trim())return;
    const key=`detail_${Date.now()}`; DETAIL_COLUMNS[key]=[label.trim(),'Optional']; state.customDetailColumns.push({key,label:label.trim()});
    state.visibleDetailColumns.push(key); state.documents.forEach(d=>d.details[key]=''); renderCustomDetailColumns(); renderDocuments(); markChanged();
  }

  function renderCustomDetailColumns() {
    $('customColumnsList').innerHTML=state.customDetailColumns.map(c=>`<span class="status-pill">${escapeHtml(c.label)} <button class="icon-btn danger" data-remove-detail-column="${c.key}" title="Remove column">×</button></span>`).join('');
    $('customColumnsList').querySelectorAll('button[data-remove-detail-column]').forEach(button=>button.addEventListener('click',e=>{
      const key=e.currentTarget.dataset.removeDetailColumn;if(!confirm('Remove this column and its stored values?'))return;
      state.customDetailColumns=state.customDetailColumns.filter(c=>c.key!==key);state.visibleDetailColumns=state.visibleDetailColumns.filter(k=>k!==key);state.documents.forEach(d=>delete d.details[key]);delete DETAIL_COLUMNS[key];renderCustomDetailColumns();renderDocuments();markChanged();
    }));
  }

  function effectivePageCount(doc) {
    return (doc.pagePlan || []).filter(p => p.included).length || 0;
  }

  function detectPdfRisks(bytes) {
    let raw = '';
    try { raw = new TextDecoder('latin1').decode(bytes); } catch (_) {}
    return {
      signed: /\/FT\s*\/Sig\b|\/Type\s*\/Sig\b|\/ByteRange\s*\[/.test(raw),
      forms: /\/AcroForm\b|\/Subtype\s*\/Widget\b/.test(raw),
      annotations: /\/Annots\b/.test(raw)
    };
  }

  function normaliseDateInput(value, input) {
    const text = String(value || '').trim();
    if (!text) { input && input.classList.remove('date-warning'); return ''; }
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    let m = text.match(/^(\d{1,2})[-\/.](\d{1,2})[-\/.](\d{4})$/);
    if (m) {
      const d=Number(m[1]), mo=Number(m[2]), y=Number(m[3]);
      if (d>=1 && d<=31 && mo>=1 && mo<=12) { input && input.classList.remove('date-warning'); return `${String(d).padStart(2,'0')}-${months[mo-1]}-${y}`; }
    }
    m = text.match(/^(\d{1,2})-([A-Za-z]{3})-(\d{4})$/);
    if (m && months.some(x => x.toLowerCase() === m[2].toLowerCase())) { input && input.classList.remove('date-warning'); return `${String(Number(m[1])).padStart(2,'0')}-${months.find(x=>x.toLowerCase()===m[2].toLowerCase())}-${m[3]}`; }
    input && input.classList.add('date-warning');
    return text;
  }

  function formatDateForPrint(value) {
    const text = String(value || '').trim();
    if (!text) return '';
    const iso = text.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (iso) {
      const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
      const month = Number(iso[2]), day = Number(iso[3]);
      if (month >= 1 && month <= 12 && day >= 1 && day <= 31) return `${iso[3]}-${months[month - 1]}-${iso[1]}`;
    }
    return normaliseDateInput(text);
  }

  async function openPageEditor(docId) {
    const doc = state.documents.find(d => d.id === docId);
    if (!doc || doc.error) return;
    state.editorDocId = docId;
    state.editorWorkingPlan = JSON.parse(JSON.stringify(doc.pagePlan));
    state.editorHistory = [];
    state.editorSelectedPages = new Set();
    $('pageEditorTitle').textContent = `Edit pages - ${doc.name}`;
    const warnings = [];
    if (doc.risk.signed) warnings.push('This file appears digitally signed. The original signed PDF will be kept separately; the paper-book copy will not retain DSC validity.');
    if (doc.risk.forms || doc.risk.annotations) warnings.push('This file contains forms, links or comments. Review the edited output carefully because page removal can affect interactive items.');
    $('pageEditorWarning').textContent = warnings.join(' ');
    $('pageEditorWarning').classList.toggle('hidden', !warnings.length);
    $('pageEditorModal').classList.remove('hidden');
    await renderPageEditor();
  }

  function closePageEditor() {
    $('pageEditorModal').classList.add('hidden');
    state.editorDocId = null; state.editorWorkingPlan = null; state.editorHistory = [];
    state.editorSelectedPages = new Set();
  }

  function pushEditorHistory() {
    state.editorHistory.push(JSON.stringify(state.editorWorkingPlan));
    if (state.editorHistory.length > 30) state.editorHistory.shift();
  }

  function editPagePlan(position, action) {
    const plan = state.editorWorkingPlan;
    if (!plan || !plan[position]) return;
    pushEditorHistory();
    if (action === 'left') plan[position].rotation = (plan[position].rotation + 270) % 360;
    if (action === 'right') plan[position].rotation = (plan[position].rotation + 90) % 360;
    if (action === 'toggle') plan[position].included = !plan[position].included;
    if (action === 'up' && position > 0) [plan[position - 1], plan[position]] = [plan[position], plan[position - 1]];
    if (action === 'down' && position < plan.length - 1) [plan[position + 1], plan[position]] = [plan[position], plan[position + 1]];
    renderPageEditor();
  }

  function undoPageEdit() {
    if (!state.editorHistory.length) return;
    state.editorWorkingPlan = JSON.parse(state.editorHistory.pop());
    renderPageEditor();
  }

  function resetPageEdit() {
    const doc = state.documents.find(d => d.id === state.editorDocId);
    if (!doc) return;
    pushEditorHistory();
    state.editorWorkingPlan = Array.from({ length: doc.originalPageCount }, (_, sourcePage) => ({ sourcePage, included:true, rotation:0 }));
    state.editorSelectedPages = new Set();
    renderPageEditor();
  }

  function parseEditorPageRange(value, pageCount) {
    const selected = new Set();
    const errors = [];
    const source = String(value || '').trim().toLowerCase();
    if (!source) return { selected, errors:['Type page numbers, for example 1-3, 7.'] };
    const add = number => {
      if (number < 1 || number > pageCount) errors.push(`Page ${number} is outside 1-${pageCount}.`);
      else selected.add(number - 1);
    };
    source.split(',').map(part => part.trim()).filter(Boolean).forEach(part => {
      if (part === 'all') { for (let n = 1; n <= pageCount; n++) add(n); return; }
      if (part === 'odd' || part === 'even') {
        const first = part === 'odd' ? 1 : 2;
        for (let n = first; n <= pageCount; n += 2) add(n);
        return;
      }
      const range = part.match(/^(\d+)\s*-\s*(\d+)$/);
      if (range) {
        const first = Number(range[1]), last = Number(range[2]);
        if (first < 1 || first > pageCount || last < 1 || last > pageCount) {
          errors.push(`Range ${first}-${last} is outside 1-${pageCount}.`);
          return;
        }
        const step = first <= last ? 1 : -1;
        for (let n = first; ; n += step) { add(n); if (n === last) break; }
        return;
      }
      if (/^\d+$/.test(part)) { add(Number(part)); return; }
      errors.push(`“${part}” is not a page number or range.`);
    });
    return { selected, errors:[...new Set(errors)] };
  }

  function selectEditorPageRange() {
    const input = $('editorPageRange');
    const doc = state.documents.find(d => d.id === state.editorDocId);
    if (!input || !doc) return;
    const parsed = parseEditorPageRange(input.value, doc.originalPageCount);
    if (parsed.errors.length) { alert(parsed.errors.join('\n')); return; }
    state.editorSelectedPages = parsed.selected;
    renderPageEditor();
  }

  function selectAllEditorPages(select) {
    if (!state.editorWorkingPlan) return;
    state.editorSelectedPages = select ? new Set(state.editorWorkingPlan.map(page => page.sourcePage)) : new Set();
    renderPageEditor();
  }

  function bulkEditSelectedPages(action) {
    const plan = state.editorWorkingPlan;
    const selected = state.editorSelectedPages;
    if (!plan || !selected || !selected.size) { alert('Select one or more pages first.'); return; }
    pushEditorHistory();
    if (action === 'left' || action === 'right' || action === 'remove' || action === 'restore') {
      plan.forEach(page => {
        if (!selected.has(page.sourcePage)) return;
        if (action === 'left') page.rotation = (page.rotation + 270) % 360;
        if (action === 'right') page.rotation = (page.rotation + 90) % 360;
        if (action === 'remove') page.included = false;
        if (action === 'restore') page.included = true;
      });
    } else if (action === 'up') {
      for (let i = 1; i < plan.length; i++) if (selected.has(plan[i].sourcePage) && !selected.has(plan[i - 1].sourcePage)) [plan[i - 1], plan[i]] = [plan[i], plan[i - 1]];
    } else if (action === 'down') {
      for (let i = plan.length - 2; i >= 0; i--) if (selected.has(plan[i].sourcePage) && !selected.has(plan[i + 1].sourcePage)) [plan[i + 1], plan[i]] = [plan[i], plan[i + 1]];
    } else if (action === 'start' || action === 'end') {
      const chosen = plan.filter(page => selected.has(page.sourcePage));
      const remaining = plan.filter(page => !selected.has(page.sourcePage));
      state.editorWorkingPlan = action === 'start' ? [...chosen, ...remaining] : [...remaining, ...chosen];
    }
    renderPageEditor();
  }

  function updateEditorSelectionStatus() {
    const status = $('editorSelectionStatus');
    if (!status) return;
    const selected = state.editorSelectedPages ? state.editorSelectedPages.size : 0;
    const total = state.editorWorkingPlan ? state.editorWorkingPlan.length : 0;
    status.textContent = selected ? `${selected} of ${total} pages selected` : `No pages selected (${total} pages)`;
  }

  function applyPageEdit() {
    const doc = state.documents.find(d => d.id === state.editorDocId);
    if (!doc) return;
    if (!state.editorWorkingPlan.some(p => p.included) && !confirm('All pages are removed from the paper book. Keep this document with zero included pages?')) return;
    doc.pagePlan = JSON.parse(JSON.stringify(state.editorWorkingPlan));
    doc.pageCount = effectivePageCount(doc);
    closePageEditor(); renderDocuments(); markChanged();
  }

  async function renderPageEditor() {
    const doc = state.documents.find(d => d.id === state.editorDocId);
    if (!doc || !state.editorWorkingPlan) return;
    $('pageTiles').innerHTML = state.editorWorkingPlan.map((p, position) => `
      <article class="page-tile ${p.included ? '' : 'excluded'} ${state.editorSelectedPages.has(p.sourcePage) ? 'selected' : ''}" data-position="${position}">
        <label class="page-select-label"><input type="checkbox" class="page-select" data-source-page="${p.sourcePage}" ${state.editorSelectedPages.has(p.sourcePage) ? 'checked' : ''}> Select page</label>
        <canvas width="140" height="170" aria-label="Original page ${p.sourcePage + 1}"></canvas>
        <div class="page-meta"><strong>Original page ${p.sourcePage + 1}</strong><span>${p.rotation ? `${p.rotation}°` : 'No rotation'}</span></div>
        <div class="tile-actions">
          <button data-page-action="left">Rotate left</button><button data-page-action="right">Rotate right</button>
          <button data-page-action="up">Move before</button><button data-page-action="down">Move after</button>
          <button data-page-action="toggle" class="${p.included ? 'danger' : ''}">${p.included ? 'Remove from book' : 'Restore page'}</button>
        </div>
      </article>`).join('');
    $('pageTiles').querySelectorAll('input.page-select').forEach(box => box.addEventListener('change', e => {
      e.stopPropagation();
      const sourcePage = Number(e.currentTarget.dataset.sourcePage);
      if (e.currentTarget.checked) state.editorSelectedPages.add(sourcePage);
      else state.editorSelectedPages.delete(sourcePage);
      e.currentTarget.closest('.page-tile').classList.toggle('selected', e.currentTarget.checked);
      updateEditorSelectionStatus();
    }));
    $('pageTiles').querySelectorAll('button[data-page-action]').forEach(button => button.addEventListener('click', e => {
      const tile = e.currentTarget.closest('.page-tile'); editPagePlan(Number(tile.dataset.position), e.currentTarget.dataset.pageAction);
    }));
    updateEditorSelectionStatus();
    try {
      if (doc.kind === 'pdf' && globalThis.pdfjsLib) {
        const loading = pdfjsLib.getDocument({ data: doc.bytes.slice() });
        const pdf = await loading.promise;
        for (const tile of $('pageTiles').querySelectorAll('.page-tile')) {
          const plan = state.editorWorkingPlan[Number(tile.dataset.position)];
          const page = await pdf.getPage(plan.sourcePage + 1);
          const previewRotation = (Number(page.rotate || 0) + Number(plan.rotation || 0)) % 360;
          const base = page.getViewport({ scale: 0.28, rotation: previewRotation });
          const canvas = tile.querySelector('canvas');
          const scale = Math.min(140 / base.width, 170 / base.height);
          const viewport = page.getViewport({ scale: 0.28 * scale, rotation: previewRotation });
          canvas.width = Math.max(1, Math.floor(viewport.width)); canvas.height = Math.max(1, Math.floor(viewport.height));
          await page.render({ canvasContext: canvas.getContext('2d'), viewport }).promise;
        }
      } else if (doc.kind === 'png' || doc.kind === 'jpg') {
        const url=URL.createObjectURL(new Blob([doc.bytes],{type:doc.kind==='png'?'image/png':'image/jpeg'}));
        const img=new Image(); await new Promise((resolve,reject)=>{img.onload=resolve;img.onerror=reject;img.src=url;});
        const canvas=$('pageTiles').querySelector('canvas'), scale=Math.min(140/img.width,170/img.height);
        canvas.width=Math.max(1,Math.floor(img.width*scale));canvas.height=Math.max(1,Math.floor(img.height*scale));canvas.getContext('2d').drawImage(img,0,0,canvas.width,canvas.height);URL.revokeObjectURL(url);
      }
    } catch (err) {
      console.warn('Thumbnail preview unavailable', err);
    }
  }

  function openChronology() {
    $('chronologyPanel').classList.remove('hidden');
    if (!state.chronologyRows.length) buildChronologyFromDocuments(false); else renderChronology();
  }

  function buildChronologyFromDocuments(confirmRefresh) {
    if (confirmRefresh && state.chronologyRows.some(r => r.manual) && !confirm('Refresh will keep manual rows but update rows linked to documents. Continue?')) return;
    const manual = state.chronologyRows.filter(r => r.manual);
    const generated = state.documents.map((doc, order) => ({
      id: `c${state.nextChronologyId++}`, date: doc.details.documentDate || '',
      event: doc.particulars || doc.name, referenceNumber: doc.details.referenceNumber || '',
      annexure: doc.annexure || '', sourceDocumentId: doc.id, manual:false, originalOrder:order
    }));
    state.chronologyRows = [...generated, ...manual]; renderChronology(); markChanged();
  }

  function addChronologyRow() {
    const row = { id:`c${state.nextChronologyId++}`, date:'', event:'', referenceNumber:'', annexure:'', sourceDocumentId:null, manual:true };
    state.chronologyColumns.forEach(c => { if (!(c.key in row)) row[c.key] = ''; });
    state.chronologyRows.push(row); renderChronology(); markChanged();
  }

  function addChronologyColumn() {
    const label = prompt('Column name (example: Remarks)');
    if (!label || !label.trim()) return;
    const key = `custom_${Date.now()}`;
    state.chronologyColumns.push({ key, label:label.trim(), custom:true });
    state.chronologyRows.forEach(r => r[key] = ''); renderChronology(); markChanged();
  }

  function sortChronology() {
    const parse = value => { const m=String(value).match(/^(\d{2})-([A-Za-z]{3})-(\d{4})$/); if(!m)return Number.MAX_SAFE_INTEGER; const months=['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec']; return Date.UTC(Number(m[3]),months.indexOf(m[2].toLowerCase()),Number(m[1])); };
    state.chronologyRows.sort((a,b) => parse(a.date)-parse(b.date) || (a.originalOrder||0)-(b.originalOrder||0)); renderChronology(); markChanged();
  }

  function renderChronology() {
    $('chronologyHeader').innerHTML = state.chronologyColumns.map(c => `<th>${escapeHtml(c.label)}${c.custom ? ` <button data-remove-column="${c.key}" class="icon-btn danger" title="Remove column">×</button>` : ''}</th>`).join('') + '<th>Actions</th>';
    $('chronologyBody').innerHTML = state.chronologyRows.map((row, index) => `<tr data-row-id="${row.id}">${state.chronologyColumns.map(c => `<td><input data-chronology-key="${c.key}" value="${escapeHtml(row[c.key] || '')}" placeholder="${c.key==='date'?'DD-MMM-YYYY':''}"></td>`).join('')}<td><button data-chronology-action="up" class="icon-btn">↑</button><button data-chronology-action="down" class="icon-btn">↓</button><button data-chronology-action="delete" class="icon-btn danger">×</button></td></tr>`).join('');
    $('chronologyBody').querySelectorAll('input').forEach(input => input.addEventListener('change', e => {
      const row = state.chronologyRows.find(r => r.id === e.target.closest('tr').dataset.rowId); const key=e.target.dataset.chronologyKey;
      row[key] = key==='date' ? normaliseDateInput(e.target.value,e.target) : e.target.value; row.manual=true; e.target.value=row[key]; markChanged();
    }));
    $('chronologyBody').querySelectorAll('button[data-chronology-action]').forEach(button => button.addEventListener('click', e => {
      const id=e.target.closest('tr').dataset.rowId, index=state.chronologyRows.findIndex(r=>r.id===id), action=e.target.dataset.chronologyAction;
      if(action==='delete') state.chronologyRows.splice(index,1);
      if(action==='up'&&index>0)[state.chronologyRows[index-1],state.chronologyRows[index]]=[state.chronologyRows[index],state.chronologyRows[index-1]];
      if(action==='down'&&index<state.chronologyRows.length-1)[state.chronologyRows[index+1],state.chronologyRows[index]]=[state.chronologyRows[index],state.chronologyRows[index+1]];
      renderChronology(); markChanged();
    }));
    $('chronologyHeader').querySelectorAll('button[data-remove-column]').forEach(button => button.addEventListener('click', e => {
      const key=e.currentTarget.dataset.removeColumn; if(!confirm('Remove this column and its stored values?'))return;
      state.chronologyColumns=state.chronologyColumns.filter(c=>c.key!==key); state.chronologyRows.forEach(r=>delete r[key]); renderChronology(); markChanged();
    }));
  }

  function downloadChronologyCsv() {
    const rows=[state.chronologyColumns.map(c=>c.label),...state.chronologyRows.map(r=>state.chronologyColumns.map(c=>r[c.key]||''))];
    downloadText('Chronology.csv', rows.map(row=>row.map(csvCell).join(',')).join('\r\n'), 'text/csv');
  }

  function downloadIssueList() {
    const groups=new Map();
    state.documents.forEach(doc=>String(doc.details.issues||'').split(/[,;|]/).map(v=>v.trim()).filter(Boolean).forEach(issue=>{
      const key=issue.toLowerCase();if(!groups.has(key))groups.set(key,{issue,docs:[]});groups.get(key).docs.push(doc);
    }));
    if(!groups.size){alert('No issue tags are available. Open More details and add an Issue first.');return;}
    const rows=[['Issue','Annexures','Documents'],...[...groups.values()].map(g=>[g.issue,g.docs.map(d=>d.annexure).join('; '),g.docs.map(d=>d.particulars||d.name).join('; ')])];
    downloadText('Issue_wise_Document_List.csv',rows.map(row=>row.map(csvCell).join(',')).join('\r\n'),'text/csv');
  }

  async function extractDraftText(file) {
    if (!file) throw new Error('Please select the appeal draft.');
    if (/\.txt$/i.test(file.name)) return await file.text();
    if (/\.docx$/i.test(file.name)) {
      const zip=await JSZip.loadAsync(await file.arrayBuffer()); const xml=await zip.file('word/document.xml')?.async('string');
      if(!xml) throw new Error('The Word document could not be read.');
      return xml.replace(/<w:tab\/?\s*>/g,'\t').replace(/<\/w:p>/g,'\n').replace(/<[^>]+>/g,' ').replace(/&amp;/g,'&').replace(/&lt;/g,'<').replace(/&gt;/g,'>');
    }
    if (/\.pdf$/i.test(file.name) && globalThis.pdfjsLib) {
      const pdf=await pdfjsLib.getDocument({data:new Uint8Array(await file.arrayBuffer())}).promise; let text='';
      for(let n=1;n<=pdf.numPages;n++){const content=await (await pdf.getPage(n)).getTextContent(); text+=content.items.map(i=>i.str).join(' ')+'\n';}
      if(!text.trim()) throw new Error('No readable text was found. This may be a scanned PDF; please check manually.');
      return text;
    }
    throw new Error('Use DOCX, searchable PDF or TXT.');
  }

  function normaliseAnnexure(value) {
    let key = String(value || '').toUpperCase().trim();
    key = key.replace(/^(ANNEXURE|ANNEX|ANX|EXHIBIT|DOCUMENT)\s*/, '');
    key = key.replace(/\b(ANNEXURE|ANNEX|ANX|EXHIBIT|DOCUMENT)\b/g, '').replace(/^NO\.?\s*/, '');
    key = key.replace(/[\s._-]+/g, '/').replace(/\/{2,}/g, '/').replace(/^\/|\/$/g, '');
    const joined = key.match(/^([A-Z]{1,3})(\d+|[IVXLCDM]+)$/);
    if (joined) key = `${joined[1]}/${joined[2]}`;
    return key;
  }

  function extractAnnexureReferences(text) {
    const named = /\b(?:Annexure|Annex|Anx|Exhibit|Document)\s*(?:No\.?\s*)?[A-Za-z]{0,3}\s*[-/.]?\s*(?:\d{1,4}|[IVXLCDM]+)\b/gi;
    const separated = /\b[A-Z]{1,3}\s*[-/]\s*(?:\d{1,4}|[IVXLCDM]+)\b/gi;
    const compactA = /\bA\d{1,4}\b/gi;
    const matches = [...text.matchAll(named), ...text.matchAll(separated), ...text.matchAll(compactA)];
    matches.sort((a, b) => a.index - b.index || b[0].length - a[0].length);
    return matches.filter((match, index, all) => !all.slice(0, index).some(previous => {
      const previousEnd = previous.index + previous[0].length;
      const currentEnd = match.index + match[0].length;
      return match.index >= previous.index && currentEnd <= previousEnd;
    }));
  }

  function documentsForReference(reference, key, available) {
    const exact = available.get(key) || [];
    if (exact.length) return exact;
    if (/^(?:Annexure|Annex|Anx)(?:\b|(?=\d))/i.test(String(reference).trim()) && /^\d+$/.test(key)) {
      const aSeries = available.get(`A/${key}`) || [];
      if (aSeries.length) return aSeries;
    }
    return [];
  }

  async function runReferenceCheck() {
    $('referenceStatus').textContent='Reading the draft…';
    try {
      const text=await extractDraftText(state.appealDraft);
      const matches=extractAnnexureReferences(text); const available=new Map();
      state.documents.forEach(d=>{const key=normaliseAnnexure(d.annexure);if(!available.has(key))available.set(key,[]);available.get(key).push(d);});
      state.referenceResults=matches.map(m=>{const key=normaliseAnnexure(m[0]), docs=documentsForReference(m[0],key,available), start=Math.max(0,m.index-80),end=Math.min(text.length,m.index+m[0].length+80);return{reference:m[0],status:docs.length===1?'Matched':docs.length>1?'Duplicate annexure in paper book':'Mentioned but missing',context:text.slice(start,end).replace(/\s+/g,' ').trim(),suggestion:suggestReference(key,available)};});
      const seen=new Set();
      state.referenceResults.forEach(result=>{
        const key=normaliseAnnexure(result.reference); seen.add(key);
        if (/^(?:Annexure|Annex|Anx)(?:\b|(?=\d))/i.test(result.reference) && /^\d+$/.test(key) && available.has(`A/${key}`)) seen.add(`A/${key}`);
      });
      available.forEach((docs,key)=>{if(!seen.has(key))state.referenceResults.push({reference:docs[0].annexure,status:'Available but not found in draft',context:'This is not necessarily an error.',suggestion:''});});
      renderReferenceResults(); $('referenceStatus').textContent=`${state.referenceResults.length} result(s). Please review; this check does not change the appeal.`; $('downloadReferenceReport').disabled=false;
    } catch(err){$('referenceStatus').textContent=err.message||String(err);state.referenceResults=[];renderReferenceResults();}
  }

  function suggestReference(key, available) {
    const tail=(key.match(/(?:^|\/)(\d+|[IVXLCDM]+)$/)||[])[1]; if(!tail)return'';
    const candidates=[]; available.forEach((docs,k)=>{if(k.endsWith('/'+tail)||k===tail)candidates.push(docs[0].annexure);});
    return candidates.length===1?candidates[0]:'';
  }

  function renderReferenceResults() {
    $('referenceResults').classList.toggle('hidden',!state.referenceResults.length);
    $('referenceResultsBody').innerHTML=state.referenceResults.map(r=>`<tr><td>${escapeHtml(r.reference)}</td><td>${escapeHtml(r.status)}</td><td>${escapeHtml(r.context)}</td><td>${escapeHtml(r.suggestion||'')}</td></tr>`).join('');
  }

  function downloadReferenceReport() {
    const rows=[['Reference found','Result','Context','Suggested correction'],...state.referenceResults.map(r=>[r.reference,r.status,r.context,r.suggestion])];
    downloadText('Appeal_Annexure_Check.csv',rows.map(row=>row.map(csvCell).join(',')).join('\r\n'),'text/csv');
  }

  function csvCell(value){return `"${String(value??'').replace(/"/g,'""')}"`;}
  function downloadText(filename,textValue,type){const blob=new Blob([textValue],{type});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=filename;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}

  async function prepareDocumentPdf(item) {
    const included = (item.pagePlan || []).filter(p => p.included);
    if (!included.length) return null;
    const baseBytes = item.kind === 'pdf' ? item.bytes : await imageToPdf(item);
    const source = await PDFDocument.load(baseBytes, { updateMetadata:false });
    const output = await PDFDocument.create();
    const copied = await output.copyPages(source, included.map(p => p.sourcePage));
    const pageMap = [];
    copied.forEach((page, outputIndex) => {
      const plan = included[outputIndex];
      const originalRotation = Number(page.getRotation().angle || 0);
      page.setRotation(degrees((originalRotation + Number(plan.rotation || 0)) % 360));
      output.addPage(page);
      pageMap.push({ outputPage:outputIndex + 1, originalPage:plan.sourcePage + 1, rotationAdded:Number(plan.rotation||0) });
    });
    return { bytes:await output.save({ useObjectStreams:true, addDefaultPage:false }), pageCount:copied.length, pageMap };
  }

  async function buildChronologyPdf() {
    const doc=await PDFDocument.create(); const font=await doc.embedFont(StandardFonts.Helvetica); const bold=await doc.embedFont(StandardFonts.HelveticaBold);
    const pageSize=[841.89,595.28], margin=30, tableWidth=pageSize[0]-margin*2;
    const columns=state.chronologyColumns.length?state.chronologyColumns:[{key:'date',label:'Date'},{key:'event',label:'Event'}];
    const columnWidth=tableWidth/columns.length; let page,y,pageNo=0;
    const addPage=()=>{page=doc.addPage(pageSize);pageNo++;page.drawText('CHRONOLOGY OF EVENTS',{x:margin,y:pageSize[1]-42,size:16,font:bold,color:rgb(.12,.13,.15)});y=pageSize[1]-72;page.drawRectangle({x:margin,y:y-20,width:tableWidth,height:20,color:rgb(.92,.93,.95)});columns.forEach((c,i)=>page.drawText(String(c.label),{x:margin+i*columnWidth+4,y:y-14,size:7,font:bold}));y-=24;};
    addPage();
    for(const row of state.chronologyRows){
      const wrapped=columns.map(c=>wrapText(row[c.key]||'',font,7,columnWidth-8)); const rowHeight=Math.max(22,...wrapped.map(lines=>lines.length*9+8));
      if(y-rowHeight<42)addPage();
      page.drawRectangle({x:margin,y:y-rowHeight+4,width:tableWidth,height:rowHeight,color:rgb(.985,.987,.99)});
      columns.forEach((c,i)=>wrapped[i].forEach((line,n)=>page.drawText(line,{x:margin+i*columnWidth+4,y:y-10-n*9,size:7,font,color:rgb(.13,.14,.16)})));
      page.drawLine({start:{x:margin,y:y-rowHeight+4},end:{x:margin+tableWidth,y:y-rowHeight+4},thickness:.4,color:rgb(.8,.82,.85)});y-=rowHeight;
    }
    return await doc.save({useObjectStreams:true,addDefaultPage:false});
  }

  function setPreviewVolumes(bytesList, outputRecords, volumes) {
    state.previewUrls.forEach(url=>URL.revokeObjectURL(url));
    state.previewVolumes=bytesList.map(bytes=>new Uint8Array(bytes)); state.previewOutputRecords=outputRecords.map(r=>({...r}));
    state.previewUrls=state.previewVolumes.map(bytes=>URL.createObjectURL(new Blob([bytes],{type:'application/pdf'})));
    state.previewRevision=state.revision;
    $('previewVolume').innerHTML=state.previewUrls.map((_,i)=>`<option value="${i}">Volume ${i+1}</option>`).join('');
    state.previewJumps = (volumes || []).flatMap((volume, volumeIndex) => volume.entries.map(entry => ({
      volumeIndex, page:entry.outputFirstPageIndex + 1,
      label:`${entry.source.annexure || 'Document'}${entry.part ? ` (Part ${entry.part})` : ''} - ${entryTitle(entry)}`
    })));
    if ($('previewJump')) $('previewJump').innerHTML = '<option value="">Jump to an annexure…</option>' + state.previewJumps.map((jump, index) =>
      `<option value="${index}">${escapeHtml(`Vol-${jump.volumeIndex + 1} · p.${jump.page} · ${jump.label}`)}</option>`).join('');
    $('previewPanel').classList.remove('hidden'); $('previewStatus').textContent='Ready'; $('previewStatus').className='status-pill ready';
    showSelectedPreviewVolume();
  }

  function showSelectedPreviewVolume() {
    const index=Number($('previewVolume').value)||0, url=state.previewUrls[index]; if(!url)return;
    $('previewFrame').src=url+'#view=FitH'; $('openPreviewNew').href=url; $('openPreviewNew').classList.remove('hidden');
  }

  function showSelectedPreviewJump() {
    const jumpSelect = $('previewJump');
    if (!jumpSelect || jumpSelect.value === '') return;
    const jump = state.previewJumps[Number(jumpSelect.value)];
    if (!jump || !state.previewUrls[jump.volumeIndex]) return;
    $('previewVolume').value = String(jump.volumeIndex);
    const url = state.previewUrls[jump.volumeIndex];
    $('previewFrame').src = `${url}#page=${jump.page}&view=FitH`;
    $('openPreviewNew').href = `${url}#page=${jump.page}&view=FitH`;
    $('openPreviewNew').classList.remove('hidden');
  }

  function updateValidation() {
    const items = [];
    const project = $('projectName').value.trim();
    if (project) items.push(['ok', `Project: ${project}`]); else items.push(['warn', 'Project name is blank. “Paper Book” will be used.']);
    if (state.documents.length) items.push(['ok', `${state.documents.length} document(s) added.`]); else items.push(['bad', 'Add at least one document.']);
    const bad = state.documents.filter(d => d.error || !Number.isFinite(Number(d.pageCount)));
    if (bad.length) items.push(['bad', `${bad.length} file(s) could not be read. Remove or replace them.`]);
    else if (state.documents.length) items.push(['ok', 'All added files are readable.']);
    const max = Number($('maxPages').value);
    if (max >= 10) items.push(['ok', `Volume limit: ${max} pages.`]); else items.push(['bad', 'Maximum pages per volume must be at least 10.']);
    const maxFileSizeMB = $('maxFileSizeMB') ? Number($('maxFileSizeMB').value) : 0;
    if (maxFileSizeMB > 0) items.push(['warn', `File-size guide: ${maxFileSizeMB} MB per volume. This is checked after PDF creation; page count remains the splitting rule.`]);
    if ($('addIndex').checked && $('addMasterIndex').checked) items.push(['ok', 'Every volume will contain the complete master index; its own entries will be highlighted.']);
    const blankParticulars = state.documents.filter(d => !String(d.particulars || '').trim()).length;
    const duplicateAnnexures = state.documents.map(d => String(d.annexure || '').trim()).filter((v, i, a) => v && a.indexOf(v) !== i);
    if (blankParticulars) items.push(['warn', `${blankParticulars} document(s) have blank particulars. Generation remains available.`]);
    if (duplicateAnnexures.length) items.push(['warn', `Duplicate annexure labels found: ${[...new Set(duplicateAnnexures)].join(', ')}. Generation remains available.`]);
    if ($('caseTitle').value.length > 600) items.push(['warn', 'The subject is unusually long. Review the exact preview carefully for readable text size and page spacing.']);
    if ($('showPreparedBy').checked && !$('preparedBy').value.trim()) items.push(['warn', '“Prepared by” is selected but the name/team is blank, so the line will not be printed.']);
    if (state.stampBytes) items.push(['warn', 'A visible stamp/signature image is selected. This is not a DSC and does not preserve source digital signatures.']);
    const signed=state.documents.filter(d=>d.risk&&d.risk.signed).length;if(signed)items.push(['warn',`${signed} signed original file(s) detected. Originals will be included separately; copied pages do not retain DSC validity.`]);
    const empty=state.documents.filter(d=>effectivePageCount(d)===0).length;if(empty)items.push(['warn',`${empty} document(s) have all pages removed from the paper book.`]);
    if(state.previewRevision&&state.previewRevision!==state.revision)items.push(['warn','The preview is out of date because settings or documents changed.']);
    items.push(['warn', 'Professional v0.6.2 supports PDF, JPG and PNG. Always verify the final filing in Adobe Reader.']);
    ui.validationList.innerHTML = items.map(([cls, text]) => `<li class="${cls}">${escapeHtml(text)}</li>`).join('');
  }

  async function generatePaperBook(mode = 'final') {
    updateValidation();
    if (mode === 'final' && state.previewRevision && state.previewRevision !== state.revision
        && !confirm('The preview is out of date because something changed. Generate anyway without refreshing the preview?')) return;
    const errors = [];
    if (!state.documents.length) errors.push('Add at least one document.');
    if (state.documents.some(d => d.error || !d.bytes)) errors.push('Remove or replace unreadable files.');
    const maxPages = Number($('maxPages').value);
    if (!Number.isInteger(maxPages) || maxPages < 10) errors.push('Maximum pages per volume must be at least 10.');
    if (errors.length) { alert(errors.join('\n')); return; }

    setBusy(true);
    try {
      setProgress(3, 'Preparing source documents…');
      const sources = [];
      for (let i = 0; i < state.documents.length; i++) {
        const item = state.documents[i];
        const prepared = await prepareDocumentPdf(item);
        if (!prepared) continue;
        sources.push({ ...item, pdfBytes: prepared.bytes, pageCount: prepared.pageCount, outputPageMap: prepared.pageMap });
        setProgress(5 + Math.round((i + 1) / state.documents.length * 15), `Prepared ${i + 1} of ${state.documents.length} documents…`);
      }

      if ($('includeChronology').checked && state.chronologyRows.length) {
        const chronologyBytes = await buildChronologyPdf();
        const chronologyDoc = await PDFDocument.load(chronologyBytes);
        sources.unshift({ id:'chronology', name:'Chronology.pdf', annexure:'Chronology', particulars:'Chronology of events', bytes:chronologyBytes, pdfBytes:chronologyBytes, pageCount:chronologyDoc.getPageCount(), kind:'pdf', risk:{signed:false,forms:false,annotations:false}, outputPageMap:[] });
      }
      if (!sources.length) throw new Error('All document pages are excluded. Restore at least one page before generation.');

      const settings = collectSettings();
      const volumes = planVolumes(sources, settings);
      const masterEntries = [];
      volumes.forEach((volume, index) => {
        volume.volumeNo = index + 1;
        volume.entries.forEach(entry => {
          entry.volumeNo = volume.volumeNo;
          masterEntries.push(entry);
        });
      });

      let entrySerial = 1;
      for (const volume of volumes) {
        volume.coverPages = settings.addCover ? 1 : 0;
        if (!settings.addIndex) volume.indexPages = 0;
        else if (settings.addMasterIndex) volume.indexPages = countIndexPages(masterEntries, true, settings);
        else volume.indexPages = countIndexPages(volume.entries, false, settings);

        let contentOffset = 0;
        volume.entries.forEach(entry => {
          entry.serial = entrySerial++;
          entry.outputFirstPageIndex = volume.coverPages + volume.indexPages + contentOffset;
          contentOffset += entry.pageCount;
        });
        volume.totalPages = volume.coverPages + volume.indexPages + volume.contentPages;
      }

      let globalPhysical = 1;
      let nextDisplay = settings.startNumber;
      let firstEligibleSeen = false;
      for (const volume of volumes) {
        volume.globalPhysicalStart = globalPhysical;
        volume.pageNumberMap = [];
        for (let i = 0; i < volume.totalPages; i++, globalPhysical++) {
          const isCover = i < volume.coverPages;
          const isDocument = i >= volume.coverPages + volume.indexPages;
          let eligible = settings.paginationScope === 'all'
            || (settings.paginationScope === 'exclude_cover' && !isCover)
            || (settings.paginationScope === 'documents_only' && isDocument)
            || (settings.paginationScope === 'physical_start' && globalPhysical >= settings.paginationStartPhysical);
          if (!settings.addPagination) eligible = false;
          let displayed = eligible ? nextDisplay++ : null;
          if (eligible && !firstEligibleSeen) {
            firstEligibleSeen = true;
            if (!settings.showFirstNumber) displayed = null;
          }
          volume.pageNumberMap.push(displayed);
        }
        const visible = volume.pageNumberMap.filter(v => v !== null);
        volume.startPrinted = visible.length ? visible[0] : '—';
        volume.endPrinted = visible.length ? visible[visible.length - 1] : '—';
        volume.entries.forEach(entry => {
          const first = entry.outputFirstPageIndex;
          entry.printedStart = volume.pageNumberMap[first] ?? `P${first + 1}`;
          entry.printedEnd = volume.pageNumberMap[first + entry.pageCount - 1] ?? `P${first + entry.pageCount}`;
        });
      }
      settings.finalPrintedNumber = Math.max(settings.startNumber, nextDisplay - 1);
      const totalOutputPages = volumes.reduce((sum, volume) => sum + volume.totalPages, 0);

      let outputRecords = [];
      let builtVolumes = [];
      for (let i = 0; i < volumes.length; i++) {
        setProgress(22 + Math.round(i / volumes.length * 63), `Generating volume ${i + 1} of ${volumes.length}…`);
        const bytes = await buildVolume(volumes[i], i + 1, volumes.length, settings, masterEntries);
        builtVolumes.push(bytes);
        const filename = `${sanitizeFilename(settings.filePrefix)}_Volume_${String(i + 1).padStart(2, '0')}.pdf`;
        outputRecords.push({ filename, pages: volumes[i].totalPages, bytes:bytes.length, sha256: await sha256(bytes) });
      }

      if (mode === 'final' && state.previewRevision === state.revision && state.previewVolumes.length === builtVolumes.length) {
        builtVolumes = state.previewVolumes.map(bytes => new Uint8Array(bytes));
        outputRecords = await Promise.all(outputRecords.map(async (record, i) => ({ ...record, sha256:await sha256(builtVolumes[i]) })));
      }

      if (mode === 'preview') {
        setPreviewVolumes(builtVolumes, outputRecords, volumes);
        const sizeWarnings = getFileSizeWarnings(outputRecords, settings.maxFileSizeMB);
        ui.resultPanel.className = 'result';
        ui.resultPanel.innerHTML = `<strong>Exact preview created.</strong><br>${volumes.length} volume(s), ${totalOutputPages} total physical pages. Scroll through the preview before generating the final ZIP.${sizeWarnings.length ? `<br><span class="warning-text">${escapeHtml(sizeWarnings.join(' '))}</span>` : ''}`;
        setProgress(100, 'Preview ready.');
        return;
      }

      const zip = new JSZip();
      builtVolumes.forEach((bytes, i) => zip.file(outputRecords[i].filename, bytes));

      setProgress(88, 'Creating audit manifest…');
      const inputRecords = [];
      for (const source of sources) {
        inputRecords.push({
          file: source.name, annexure: source.annexure, particulars: source.particulars,
          pages: source.pageCount, originalPages: source.originalPageCount || source.pageCount,
          pageMap: source.outputPageMap || [], details:source.details || {}, risk:source.risk || {},
          bytes: source.bytes.length, sha256: await sha256(source.bytes)
        });
      }
      const manifest = {
        product: 'SME GSTAT AppealKit', set: 'Professional v0.6.2', generatedAt: new Date().toISOString(),
        project: settings.projectName, appellant: settings.appellant, gstin: settings.gstin,
        volumeLimit: settings.maxPages, totalVolumes: volumes.length,
        fileSizeGuideMB: settings.maxFileSizeMB || null,
        outputMode: settings.outputMode,
        masterIndexEnabled: settings.addIndex && settings.addMasterIndex,
        masterIndexPlacement: settings.addIndex && settings.addMasterIndex ? 'Every volume' : 'Volume-specific index',
        accentColor: settings.accentColor,
        pageNumberFormat: settings.pageNumberFormat,
        pageNumberPosition: settings.pageNumberPosition,
        pageNumberSize: settings.pageNumberSize,
        paginationScope: settings.paginationScope,
        returnPosition: settings.returnPosition,
        returnSize: settings.returnSize,
        finalPrintedNumber: settings.finalPrintedNumber,
        chronologyIncluded: $('includeChronology').checked && state.chronologyRows.length > 0,
        chronologyRows: state.chronologyRows.length,
        volumeMap: masterEntries.map(entry => ({
          serial: entry.serial, annexure: entry.source.annexure, particulars: entryTitle(entry),
          volume: entry.volumeNo, printedStart: entry.printedStart, printedEnd: entry.printedEnd
        })),
        inputs: inputRecords, outputs: outputRecords
      };
      zip.file(`${sanitizeFilename(settings.filePrefix)}_Audit_Manifest.json`, JSON.stringify(manifest, null, 2));
      zip.file(`${sanitizeFilename(settings.filePrefix)}_Portal_Upload_Map.csv`, buildPortalUploadMap(outputRecords, settings));
      zip.file('READ_ME_FIRST.txt', buildOutputReadme(settings, volumes));
      for (const item of state.documents.filter(d => d.risk && d.risk.signed)) {
        zip.file(`Original_Signed_Documents/${sanitizeFilename(item.name)}`, item.bytes);
      }

      setProgress(94, 'Packing final ZIP…');
      const blob = await zip.generateAsync({ type: 'blob', compression: 'DEFLATE', compressionOptions: { level: 6 } }, metadata => {
        setProgress(94 + Math.round(metadata.percent * 0.05), `Packing final ZIP… ${Math.round(metadata.percent)}%`);
      });
      const zipName = `${sanitizeFilename(settings.filePrefix)}_Generated.zip`;
      const url = URL.createObjectURL(blob);
      ui.resultPanel.className = 'result';
      const sizeWarnings = getFileSizeWarnings(outputRecords, settings.maxFileSizeMB);
      ui.resultPanel.innerHTML = `<strong>Generation completed.</strong><br>${volumes.length} volume(s) created with ${totalOutputPages} total pages.${sizeWarnings.length ? `<br><span class="warning-text">${escapeHtml(sizeWarnings.join(' '))}</span>` : ''}<br><a id="downloadResult" download="${escapeHtml(zipName)}">Download ${escapeHtml(zipName)}</a>`;
      $('downloadResult').href = url;
      setProgress(100, 'Completed. Download the generated ZIP.');
    } catch (err) {
      console.error(err);
      ui.resultPanel.className = 'result error';
      ui.resultPanel.innerHTML = `<strong>Generation failed.</strong><br>${escapeHtml(friendlyError(err))}`;
      setProgress(0, 'Generation stopped.');
    } finally {
      setBusy(false, true);
    }
  }

  function collectSettings() {
    const selectedType = $('appealType').value;
    return {
      projectName: $('projectName').value.trim() || 'Paper Book',
      coverHeading: $('coverHeading').value.trim(), coverSubheading: $('coverSubheading').value.trim(),
      showCoverHeading: $('showCoverHeading').checked, showDocumentType: $('showDocumentType').checked,
      showPreparedBy: $('showPreparedBy').checked,
      showCaseTitleOnIndex: $('showCaseTitleOnIndex').checked,
      appealType: selectedType === 'custom' ? $('customAppealType').value.trim() : selectedType,
      appellant: $('appellant').value.trim(), respondent: $('respondent').value.trim(),
      bench: $('bench').value.trim(), gstin: $('gstin').value.trim(), financialYear: $('financialYear').value.trim(),
      orderNumber: $('orderNumber').value.trim(), orderDate: formatDateForPrint($('orderDate').value),
      preparedBy: $('preparedBy').value.trim(), caseTitle: $('caseTitle').value.trim(),
      coverTextSize: $('coverTextSize') ? $('coverTextSize').value : 'normal',
      maxPages: Number($('maxPages').value), startNumber: Number($('startNumber').value) || 1,
      maxFileSizeMB: $('maxFileSizeMB') ? Math.max(0, Number($('maxFileSizeMB').value) || 0) : 0,
      outputMode: $('outputMode') ? $('outputMode').value : 'final',
      paginationScope: $('paginationScope').value,
      paginationStartPhysical: Math.max(1, Number($('paginationStartPhysical').value) || 1),
      showFirstNumber: $('showFirstNumber').checked,
      pageNumberFormat: $('pageNumberFormat').value,
      pageNumberPosition: $('pageNumberPosition').value,
      pageNumberSize: $('pageNumberSize').value,
      returnPosition: $('returnPosition').value,
      returnSize: $('returnSize').value,
      accentColor: $('accentColor').value,
      layoutStyle: $('layoutStyle').value,
      footerText: $('footerText').value.trim(), filePrefix: $('filePrefix').value.trim() || 'SME_GSTAT_Appeal_PaperBook',
      addCover: $('addCover').checked, addIndex: $('addIndex').checked, addMasterIndex: $('addMasterIndex').checked,
      addLinks: $('addLinks').checked, addReturn: $('addReturn').checked,
      addBookmarks: $('addBookmarks').checked, addPagination: $('addPagination').checked,
      stampScope: $('stampScope').value, stampPages: $('stampPages').value.trim(),
      stampPosition: $('stampPosition').value, stampWidth: Math.max(20, Number($('stampWidth').value) || 90),
      stampOpacity: Math.min(1, Math.max(0.1, Number($('stampOpacity').value) || 0.9)),
      textStamp: $('textStamp').value.trim(), stampBytes: state.stampBytes, stampKind: state.stampKind
    };
  }

  function planVolumes(sources, settings) {
    if (!settings.addIndex || !settings.addMasterIndex) {
      return planVolumesWithMasterPages(sources, settings, 0);
    }

    let masterIndexPages = 1;
    for (let attempt = 0; attempt < 20; attempt++) {
      const volumes = planVolumesWithMasterPages(sources, settings, masterIndexPages);
      const allEntries = volumes.flatMap(volume => volume.entries);
      const required = countIndexPages(allEntries, true, settings);
      if (required === masterIndexPages) return volumes;
      masterIndexPages = required;
    }
    throw new Error('Could not stabilise the master index layout. Increase the page limit per volume.');
  }

  function estimateIndexLines(text, master) {
    const limit = master ? 52 : 62;
    const words = String(text || '').replace(/\s+/g, ' ').trim().split(' ').filter(Boolean);
    let lines = 1, used = 0;
    for (const word of words) {
      let remaining = word.length;
      while (remaining > 0) {
        const separator = used ? 1 : 0;
        const available = limit - used - separator;
        if (available <= 0) { lines++; used = 0; continue; }
        if (remaining <= available) { used += separator + remaining; remaining = 0; }
        else { lines++; remaining -= available; used = 0; }
      }
    }
    return Math.max(1, lines);
  }

  function estimatedRowHeight(entry, master) {
    return Math.max(master ? 29 : 27, estimateIndexLines(entryTitle(entry), master) * 10 + 11);
  }

  function paginateIndexEntries(entries, master, settings = {}) {
    const pages = [];
    let page = [], used = 0;
    const caseLines = master && settings.showCaseTitleOnIndex && settings.caseTitle ? estimateIndexLines(settings.caseTitle, true) : 0;
    const caseReserve = 22 + (caseLines ? caseLines * 10 + 6 : 0);
    const capacity = 632 - caseReserve;
    for (const entry of entries) {
      const height = estimatedRowHeight(entry, master);
      if (page.length && used + height > capacity) { pages.push(page); page = []; used = 0; }
      page.push(entry); used += height;
    }
    if (page.length) pages.push(page);
    return pages.length ? pages : [[]];
  }

  function countIndexPages(entries, master, settings) {
    return paginateIndexEntries(entries, master, settings).length;
  }

  function planVolumesWithMasterPages(sources, settings, masterIndexPages) {
    const volumes = [];
    let sourceIndex = 0;
    let sourceOffset = 0;
    let partCounter = 1;

    while (sourceIndex < sources.length) {
      const volumeNo = volumes.length + 1;
      const volume = { entries: [], contentPages: 0, volumeNo };
      while (sourceIndex < sources.length) {
        const source = sources[sourceIndex];
        let indexPages = 0;
        if (settings.addIndex) {
          indexPages = settings.addMasterIndex
            ? masterIndexPages
            : countIndexPages([...volume.entries, { source, part: null }], false, settings);
        }
        const overhead = (settings.addCover ? 1 : 0) + indexPages;
        const available = settings.maxPages - overhead - volume.contentPages;
        if (available <= 0) break;

        const remaining = source.pageCount - sourceOffset;
        const take = Math.min(remaining, available);
        if (take <= 0) break;
        volume.entries.push({
          source, sourcePageStart: sourceOffset, pageCount: take,
          part: sourceOffset > 0 || take < source.pageCount ? partCounter : null
        });
        volume.contentPages += take;
        sourceOffset += take;
        if (sourceOffset >= source.pageCount) {
          sourceIndex += 1; sourceOffset = 0; partCounter = 1;
        } else {
          partCounter += 1;
          break;
        }
      }
      if (!volume.entries.length) {
        throw new Error('The selected page limit is too small for the cover/index and at least one document page.');
      }
      volumes.push(volume);
    }
    return volumes;
  }

  async function buildVolume(volume, volumeNo, totalVolumes, settings, masterEntries) {
    const pdfDoc = await PDFDocument.create();
    pdfDoc.setTitle(`${settings.projectName} - Volume ${volumeNo}`);
    if (settings.showPreparedBy && settings.preparedBy) pdfDoc.setAuthor(settings.preparedBy);
    pdfDoc.setSubject(settings.caseTitle || settings.appealType);
    pdfDoc.setCreator('SME GSTAT AppealKit - Professional v0.6.2');
    pdfDoc.setProducer('SME GSTAT AppealKit');

    const helvetica = await pdfDoc.embedFont(StandardFonts.Helvetica);
    const helveticaBold = await pdfDoc.embedFont(StandardFonts.HelveticaBold);
    let stampImage = null;
    if (settings.stampBytes && settings.stampScope !== 'none') {
      stampImage = settings.stampKind === 'png' ? await pdfDoc.embedPng(settings.stampBytes) : await pdfDoc.embedJpg(settings.stampBytes);
    }
    const indexLinkRects = [];
    const bookmarkTargets = [];

    if (settings.addCover) {
      const page = pdfDoc.addPage(A4);
      drawCover(page, helvetica, helveticaBold, settings, volumeNo, totalVolumes, volume);
      bookmarkTargets.push({ title: 'Cover', pageIndex: 0 });
    }

    const firstIndexPageIndex = settings.addIndex ? pdfDoc.getPageCount() : -1;
    const usesMasterIndex = settings.addIndex && settings.addMasterIndex;
    if (settings.addIndex) {
      const indexSource = usesMasterIndex ? masterEntries : volume.entries;
      const groupedIndexEntries = paginateIndexEntries(indexSource, usesMasterIndex, settings);
      const indexPages = groupedIndexEntries.length;
      let indexOffset = 0;
      for (let p = 0; p < indexPages; p++) {
        const page = pdfDoc.addPage(A4);
        const slice = groupedIndexEntries[p];
        const rects = usesMasterIndex
          ? drawMasterIndexPage(page, helvetica, helveticaBold, settings, volumeNo, totalVolumes, slice, p + 1, indexPages)
          : drawIndexPage(page, helvetica, helveticaBold, settings, volumeNo, totalVolumes, slice, p + 1, indexPages);
        rects.forEach((rect, local) => {
          indexLinkRects.push({
            pageIndex: pdfDoc.getPageCount() - 1,
            rect,
            entry: indexSource[indexOffset + local],
            remote: usesMasterIndex && indexSource[indexOffset + local].volumeNo !== volumeNo
          });
        });
        indexOffset += slice.length;
      }
      bookmarkTargets.push({ title: usesMasterIndex ? 'Master Index — All Volumes' : 'Index', pageIndex: firstIndexPageIndex });
    }

    const pageEntryMap = new Map();
    for (let i = 0; i < volume.entries.length; i++) {
      const entry = volume.entries[i];
      const sourcePdf = await PDFDocument.load(entry.source.pdfBytes, { updateMetadata: false });
      const indices = Array.from({ length: entry.pageCount }, (_, j) => entry.sourcePageStart + j);
      const copied = await pdfDoc.copyPages(sourcePdf, indices);
      const firstPageIndex = pdfDoc.getPageCount();
      copied.forEach((page, copiedIndex) => {
        pdfDoc.addPage(page);
        pageEntryMap.set(firstPageIndex + copiedIndex, entry);
      });
      const title = entryTitle(entry);
      bookmarkTargets.push({ title, pageIndex: firstPageIndex });
    }

    const pages = pdfDoc.getPages();
    const theme = getTheme(settings);
    if (settings.addPagination || settings.footerText || (settings.addReturn && settings.addIndex) || settings.outputMode === 'draft') {
      for (let i = 0; i < pages.length; i++) {
        const page = pages[i];
        const visual = getVisualPageSize(page);
        if (settings.outputMode === 'draft') {
          drawVisualText(page, 'DRAFT - FOR REVIEW', {
            x: visual.width / 2, y: visual.height / 2, size: 34, font: helveticaBold,
            color: rgb(0.68, 0.08, 0.08), opacity: 0.14, align: 'center'
          });
        }
        if (settings.footerText) {
          drawVisualText(page, settings.footerText, {
            x: 28, y: 11, size: 7, font: helvetica,
            color: rgb(0.38, 0.4, 0.44), align: 'left'
          });
        }
        const contentStartIndex = volume.coverPages + volume.indexPages;
        const hasReturnLabel = settings.addReturn && settings.addIndex && i >= contentStartIndex;
        let returnLayout = null;
        if (hasReturnLabel) {
          const entry = pageEntryMap.get(i);
          const returnLabel = 'RETURN TO INDEX';
          const annexureLabel = entry ? formatAnnexureLabel(entry) : '';
          const returnSize = getLabelSize(settings.returnSize, 7);
          returnLayout = getReturnLayout(
            visual, settings.returnPosition, returnSize, helveticaBold,
            returnLabel, annexureLabel
          );
          drawVisualRectangle(page, {
            x: returnLayout.x, y: returnLayout.y,
            width: returnLayout.width, height: returnLayout.height,
            color: rgb(1, 1, 1), opacity: 0.92
          });
          drawVisualText(page, returnLabel, {
            x: returnLayout.textX, y: returnLayout.returnY, size: returnSize,
            font: helveticaBold, color: theme.accent, align: returnLayout.align
          });
          if (annexureLabel) {
            drawVisualText(page, annexureLabel, {
              x: returnLayout.textX, y: returnLayout.annexureY, size: returnSize,
              font: helveticaBold, color: rgb(0.2, 0.22, 0.25), align: returnLayout.align
            });
          }
          const linkRect = visualRectangleToPage(
            page, returnLayout.x, returnLayout.y, returnLayout.width, returnLayout.height
          );
          addInternalLink(pdfDoc, page, linkRect, pages[firstIndexPageIndex]);
        }
        if (settings.addPagination) {
          const currentPrinted = volume.pageNumberMap[i];
          if (currentPrinted !== null && currentPrinted !== undefined) {
          const label = formatPageNumber(currentPrinted, settings.finalPrintedNumber, settings.pageNumberFormat);
          const pageNumberSize = getLabelSize(settings.pageNumberSize, 8);
          const numberLayout = getPageNumberLayout(
            visual, settings.pageNumberPosition, pageNumberSize,
            settings.footerText, returnLayout, settings.returnPosition
          );
          drawVisualText(page, label, {
            x: numberLayout.x, y: numberLayout.y, size: pageNumberSize, font: helvetica,
            color: rgb(0.2, 0.22, 0.25), align: numberLayout.align
          });
          }
        }
        if (i >= contentStartIndex && shouldStampPage(settings, volume, i, pageEntryMap.get(i))) {
          const stampLayout = getStampLayout(visual, settings.stampPosition, settings.stampWidth, stampImage);
          if (stampImage) {
            drawVisualImage(page, stampImage, { ...stampLayout, opacity: settings.stampOpacity });
          }
          if (settings.textStamp) {
            drawVisualRectangle(page, { x: stampLayout.x, y: stampLayout.y - 17, width: Math.max(stampLayout.width, 120), height: 15, color: rgb(1,1,1), opacity: 0.88 });
            drawVisualText(page, settings.textStamp, { x: stampLayout.x + 3, y: stampLayout.y - 13, size: 7, font: helveticaBold, color: theme.accent, align: 'left' });
          }
        }
      }
    }

    if (settings.addLinks && settings.addIndex) {
      indexLinkRects.forEach(link => {
        const sourcePage = pages[link.pageIndex];
        if (link.remote) {
          const filename = `${sanitizeFilename(settings.filePrefix)}_Volume_${String(link.entry.volumeNo).padStart(2, '0')}.pdf`;
          addRemoteLink(pdfDoc, sourcePage, link.rect, filename, link.entry.outputFirstPageIndex);
        } else {
          const targetPage = pages[link.entry.outputFirstPageIndex];
          addInternalLink(pdfDoc, sourcePage, link.rect, targetPage);
        }
      });
    }

    if (settings.addBookmarks) addBookmarks(pdfDoc, bookmarkTargets);
    return await pdfDoc.save({ useObjectStreams: true, addDefaultPage: false, objectsPerTick: 40 });
  }

  function drawCover(page, font, bold, settings, volumeNo, totalVolumes, volume) {
    const { width, height } = page.getSize();
    const theme = getTheme(settings);
    const scale = settings.coverTextSize === 'small' ? 0.9 : settings.coverTextSize === 'large' ? 1.1 : 1;
    let topY = height - 42;
    if (settings.showCoverHeading && (settings.coverHeading || settings.coverSubheading)) {
      const baseHeaderHeight = settings.layoutStyle === 'minimal' ? 72 : settings.layoutStyle === 'formal' ? 88 : 105;
      const headerHeight = baseHeaderHeight * (0.96 + scale * 0.04);
      page.drawRectangle({ x: 0, y: height - headerHeight, width, height: headerHeight, color: theme.header });
      if (settings.coverHeading) fitAndDrawText(page, settings.coverHeading, { x: 45, y: height - headerHeight * 0.53, maxWidth: width - 90, size: (settings.layoutStyle === 'minimal' ? 20 : 24) * scale, minSize: 13, font: bold, color: rgb(1, 1, 1) });
      if (settings.coverSubheading) fitAndDrawText(page, settings.coverSubheading, { x: 46, y: height - headerHeight * 0.79, maxWidth: width - 92, size: 11 * scale, minSize: 7.5, font, color: rgb(1, 1, 1) });
      topY = height - headerHeight - 45;
    }

    if (settings.showDocumentType && settings.appealType) {
      centerFitText(page, settings.appealType.toUpperCase(), bold, 18 * scale, topY, 510, rgb(0.15, 0.16, 0.18));
      topY -= 48 * scale;
    }
    centerWrapped(page, settings.projectName, bold, 20 * scale, topY, 500, 25 * scale, rgb(0.1, 0.11, 0.13));
    topY -= 78 * scale;
    centerText(page, `VOLUME ${volumeNo} OF ${totalVolumes}`, bold, 14 * scale, topY, theme.accent);
    centerText(page, `Pages ${volume.startPrinted}-${volume.endPrinted}`, font, 10 * scale, topY - 22 * scale, rgb(0.35, 0.37, 0.4));

    const lines = [
      ['Appellant', settings.appellant], ['Respondent', settings.respondent], ['Bench', settings.bench],
      ['GSTIN', settings.gstin], ['Financial Year', settings.financialYear],
      ['Impugned Order', settings.orderNumber], ['Order Date', settings.orderDate]
    ].filter(([, v]) => v);
    let y = topY - 70 * scale;
    lines.forEach(([label, value]) => {
      const detailSize = 10 * scale, detailLineHeight = 14 * scale;
      page.drawText(label, { x: 70, y, size: detailSize, font: bold, color: rgb(0.2, 0.22, 0.25) });
      page.drawText(':', { x: 175, y, size: detailSize, font: bold });
      const wrapped = wrapText(value, font, detailSize, 330);
      wrapped.forEach((line, lineNo) => page.drawText(line, { x: 192, y: y - lineNo * detailLineHeight, size: detailSize, font, color: rgb(0.16, 0.18, 0.21) }));
      y -= Math.max(30 * scale, wrapped.length * detailLineHeight + 8 * scale);
    });
    if (settings.caseTitle) {
      const labelSize = 10 * scale;
      page.drawText('Subject', { x: 70, y, size: labelSize, font: bold });
      page.drawText(':', { x: 175, y, size: labelSize, font: bold });
      let subjectSize = 10 * scale;
      let subjectLines = wrapText(settings.caseTitle, font, subjectSize, 330);
      let subjectLineHeight = subjectSize + 3;
      const subjectBottom = settings.showPreparedBy && settings.preparedBy ? 95 : 60;
      let availableLines = Math.max(1, Math.floor((y - subjectBottom) / subjectLineHeight));
      while (subjectLines.length > availableLines && subjectSize > 7) {
        subjectSize -= 0.5;
        subjectLines = wrapText(settings.caseTitle, font, subjectSize, 330);
        subjectLineHeight = subjectSize + 3;
        availableLines = Math.max(1, Math.floor((y - subjectBottom) / subjectLineHeight));
      }
      drawJustifiedLines(page, subjectLines, { x: 192, y, width: 330, size: subjectSize, lineHeight: subjectLineHeight, font, color: rgb(0.12, 0.13, 0.15) });
    }
    if (settings.showPreparedBy && settings.preparedBy) {
      page.drawText(`Prepared by: ${settings.preparedBy}`, { x: 70, y: 70, size: 9 * scale, font, color: rgb(0.35, 0.37, 0.4) });
    }
  }

  function drawIndexPage(page, font, bold, settings, volumeNo, totalVolumes, entries, pageNo, indexPages) {
    const { width, height } = page.getSize();
    const theme = getTheme(settings);
    page.drawText('INDEX', { x: 45, y: height - 55, size: 20, font: bold, color: theme.accent });
    page.drawText(`${settings.projectName} · Volume ${volumeNo} of ${totalVolumes}`, { x: 45, y: height - 76, size: 9, font, color: rgb(0.35, 0.37, 0.4) });
    if (indexPages > 1) page.drawText(`Index page ${pageNo} of ${indexPages}`, { x: width - 130, y: height - 76, size: 8, font });

    const top = height - 110;
    page.drawRectangle({ x: 38, y: top - 22, width: width - 76, height: 22, color: rgb(0.93, 0.94, 0.96) });
    page.drawText('Sl.', { x: 44, y: top - 15, size: 8, font: bold });
    page.drawText('Annexure', { x: 73, y: top - 15, size: 8, font: bold });
    page.drawText('Particulars', { x: 145, y: top - 15, size: 8, font: bold });
    page.drawText('Pages', { x: width - 93, y: top - 15, size: 8, font: bold });

    const rects = [];
    let y = top - 44;
    entries.forEach(entry => {
      const title = entryTitle(entry);
      const titleLines = wrapText(title, font, 8, 340);
      const rowHeight = Math.max(27, titleLines.length * 10 + 11);
      const rowTop = y + 9;
      const rowBottom = rowTop - rowHeight;
      page.drawLine({ start: { x: 38, y: rowBottom }, end: { x: width - 38, y: rowBottom }, thickness: 0.5, color: rgb(0.82, 0.84, 0.87) });
      page.drawText(String(entry.serial), { x: 46, y, size: 8, font });
      page.drawText(entry.source.annexure || '-', { x: 73, y, size: 8, font });
      titleLines.forEach((line, n) => page.drawText(line, { x: 145, y: y - n * 10, size: 8, font, color: theme.link }));
      const pages = entry.printedStart === entry.printedEnd ? String(entry.printedStart) : `${entry.printedStart}–${entry.printedEnd}`;
      page.drawText(pages, { x: width - 93, y, size: 8, font });
      rects.push([140, rowBottom, width - 105, rowTop]);
      y -= rowHeight;
    });
    page.drawText('Click a coloured particulars entry to open the corresponding document.', { x: 42, y: 35, size: 7, font, color: rgb(0.35, 0.37, 0.4) });
    return rects;
  }

  function drawMasterIndexPage(page, font, bold, settings, currentVolumeNo, totalVolumes, entries, pageNo, indexPages) {
    const { width, height } = page.getSize();
    const theme = getTheme(settings);
    page.drawText('MASTER INDEX — ALL VOLUMES', { x: 38, y: height - 55, size: 18, font: bold, color: theme.accent });
    let infoY = height - 78;
    if (settings.showCaseTitleOnIndex && settings.caseTitle) {
      const caseLines = wrapText(settings.caseTitle, font, 8, width - 76);
      caseLines.forEach((line, n) => page.drawText(line, { x: 38, y: infoY - n * 10, size: 8, font, color: rgb(0.28, 0.30, 0.34) }));
      infoY -= caseLines.length * 10 + 6;
    }
    page.drawText(`Viewing Volume ${currentVolumeNo} of ${totalVolumes}`, { x: 38, y: infoY, size: 8, font: bold, color: theme.accent });
    const marker = `Index page ${pageNo} of ${indexPages}`;
    page.drawText(marker, { x: width - 38 - font.widthOfTextAtSize(marker, 8), y: infoY, size: 8, font });

    const top = infoY - 28;
    page.drawRectangle({ x: 34, y: top - 22, width: width - 68, height: 22, color: rgb(0.93, 0.94, 0.96) });
    page.drawText('Sl.', { x: 40, y: top - 15, size: 8, font: bold });
    page.drawText('Annexure', { x: 67, y: top - 15, size: 8, font: bold });
    page.drawText('Particulars', { x: 137, y: top - 15, size: 8, font: bold });
    page.drawText('Volume', { x: 433, y: top - 15, size: 8, font: bold });
    page.drawText('Pages', { x: 498, y: top - 15, size: 8, font: bold });

    const rects = [];
    let y = top - 44;
    entries.forEach(entry => {
      const isCurrentVolume = entry.volumeNo === currentVolumeNo;
      const rowFont = isCurrentVolume ? bold : font;
      const titleLines = wrapText(entryTitle(entry), rowFont, 8, 282);
      const rowHeight = Math.max(29, titleLines.length * 10 + 11);
      const rowTop = y + 9;
      const rowBottom = rowTop - rowHeight;
      if (isCurrentVolume) {
        page.drawRectangle({ x: 34, y: rowBottom, width: width - 68, height: rowHeight, color: theme.highlight });
      }
      page.drawLine({ start: { x: 34, y: rowBottom }, end: { x: width - 34, y: rowBottom }, thickness: 0.5, color: rgb(0.82, 0.84, 0.87) });
      page.drawText(String(entry.serial), { x: 41, y, size: 8, font: rowFont });
      page.drawText(entry.source.annexure || '-', { x: 67, y, size: 8, font: rowFont });
      titleLines.forEach((line, n) => page.drawText(line, { x: 137, y: y - n * 10, size: 8, font: rowFont, color: theme.link }));
      page.drawText(`Vol-${entry.volumeNo}`, { x: 437, y, size: 8, font: rowFont, color: isCurrentVolume ? theme.accent : rgb(0.16, 0.18, 0.21) });
      const pages = entry.printedStart === entry.printedEnd ? String(entry.printedStart) : `${entry.printedStart}–${entry.printedEnd}`;
      page.drawText(pages, { x: 498, y, size: 8, font: rowFont });
      rects.push([133, rowBottom, width - 36, rowTop]);
      y -= rowHeight;
    });
    page.drawText(`Highlighted rows belong to Volume ${currentVolumeNo}. Other rows show documents available in the remaining volumes.`, { x: 38, y: 35, size: 7, font, color: rgb(0.35, 0.37, 0.4) });
    return rects;
  }

  function addInternalLink(pdfDoc, sourcePage, rect, targetPage) {
    const annot = pdfDoc.context.obj({
      Type: PDFName.of('Annot'), Subtype: PDFName.of('Link'), Rect: rect,
      Border: [0, 0, 0], Dest: [targetPage.ref, PDFName.of('Fit')], H: PDFName.of('I')
    });
    sourcePage.node.addAnnot(pdfDoc.context.register(annot));
  }

  function addRemoteLink(pdfDoc, sourcePage, rect, filename, targetPageIndex) {
    const action = pdfDoc.context.obj({
      S: PDFName.of('GoToR'), F: PDFString.of(filename),
      D: [targetPageIndex, PDFName.of('Fit')], NewWindow: true
    });
    const annot = pdfDoc.context.obj({
      Type: PDFName.of('Annot'), Subtype: PDFName.of('Link'), Rect: rect,
      Border: [0, 0, 0], A: pdfDoc.context.register(action), H: PDFName.of('I')
    });
    sourcePage.node.addAnnot(pdfDoc.context.register(annot));
  }

  function addBookmarks(pdfDoc, targets) {
    if (!targets.length) return;
    const ctx = pdfDoc.context;
    const outlines = ctx.obj({ Type: PDFName.of('Outlines') });
    const outlinesRef = ctx.register(outlines);
    const itemDicts = [];
    const itemRefs = [];
    targets.forEach(target => {
      const page = pdfDoc.getPages()[target.pageIndex];
      const item = ctx.obj({
        Title: PDFHexString.fromText(target.title), Parent: outlinesRef,
        Dest: [page.ref, PDFName.of('Fit')]
      });
      itemDicts.push(item); itemRefs.push(ctx.register(item));
    });
    itemDicts.forEach((item, i) => {
      if (i > 0) item.set(PDFName.of('Prev'), itemRefs[i - 1]);
      if (i < itemRefs.length - 1) item.set(PDFName.of('Next'), itemRefs[i + 1]);
    });
    outlines.set(PDFName.of('First'), itemRefs[0]);
    outlines.set(PDFName.of('Last'), itemRefs[itemRefs.length - 1]);
    outlines.set(PDFName.of('Count'), ctx.obj(itemRefs.length));
    pdfDoc.catalog.set(PDFName.of('Outlines'), outlinesRef);
    pdfDoc.catalog.set(PDFName.of('PageMode'), PDFName.of('UseOutlines'));
  }

  async function imageToPdf(item) {
    const doc = await PDFDocument.create();
    const image = item.kind === 'png' ? await doc.embedPng(item.bytes) : await doc.embedJpg(item.bytes);
    const page = doc.addPage(A4);
    const margin = 28;
    const scale = Math.min((A4[0] - margin * 2) / image.width, (A4[1] - margin * 2) / image.height, 1);
    const w = image.width * scale, h = image.height * scale;
    page.drawImage(image, { x: (A4[0] - w) / 2, y: (A4[1] - h) / 2, width: w, height: h });
    return await doc.save();
  }

  function normalizePageRotation(page) {
    const angle = ((Number(page.getRotation().angle || 0) % 360) + 360) % 360;
    return angle === 90 || angle === 180 || angle === 270 ? angle : 0;
  }

  function getVisualPageSize(page) {
    const { width, height } = page.getSize();
    const rotation = normalizePageRotation(page);
    return {
      width: rotation === 90 || rotation === 270 ? height : width,
      height: rotation === 90 || rotation === 270 ? width : height,
      baseWidth: width,
      baseHeight: height,
      rotation
    };
  }

  function visualPointToPage(page, visualX, visualY) {
    const { baseWidth, baseHeight, rotation } = getVisualPageSize(page);
    if (rotation === 90) return { x: baseWidth - visualY, y: visualX };
    if (rotation === 180) return { x: baseWidth - visualX, y: baseHeight - visualY };
    if (rotation === 270) return { x: visualY, y: baseHeight - visualX };
    return { x: visualX, y: visualY };
  }

  function visualRectangleToPage(page, visualX, visualY, width, height) {
    const corners = [
      visualPointToPage(page, visualX, visualY),
      visualPointToPage(page, visualX + width, visualY),
      visualPointToPage(page, visualX, visualY + height),
      visualPointToPage(page, visualX + width, visualY + height)
    ];
    const xs = corners.map(point => point.x);
    const ys = corners.map(point => point.y);
    return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
  }

  function drawVisualRectangle(page, options) {
    const rect = visualRectangleToPage(page, options.x, options.y, options.width, options.height);
    page.drawRectangle({
      x: rect[0], y: rect[1], width: rect[2] - rect[0], height: rect[3] - rect[1],
      color: options.color, opacity: options.opacity
    });
  }

  function drawVisualText(page, text, options) {
    const textWidth = options.font.widthOfTextAtSize(text || '', options.size);
    let visualX = options.x;
    if (options.align === 'right') visualX -= textWidth;
    else if (options.align === 'center') visualX -= textWidth / 2;
    const point = visualPointToPage(page, visualX, options.y);
    page.drawText(text || '', {
      x: point.x, y: point.y, size: options.size, font: options.font,
      color: options.color, opacity: options.opacity, rotate: degrees(normalizePageRotation(page))
    });
  }

  function getFileSizeWarnings(outputRecords, maxFileSizeMB) {
    if (!(maxFileSizeMB > 0)) return [];
    const limitBytes = maxFileSizeMB * 1024 * 1024;
    return outputRecords.filter(record => record.bytes > limitBytes).map(record =>
      `${record.filename} is ${(record.bytes / 1024 / 1024).toFixed(1)} MB, above the ${maxFileSizeMB} MB guide.`
    );
  }

  function drawVisualImage(page, image, options) {
    const point = visualPointToPage(page, options.x, options.y);
    page.drawImage(image, {
      x: point.x, y: point.y, width: options.width, height: options.height,
      opacity: options.opacity, rotate:degrees(normalizePageRotation(page))
    });
  }

  function getStampLayout(visual, position, width, image) {
    const ratio = image ? image.height / image.width : 0.4;
    const height = Math.max(18, width * ratio);
    const placement = parsePlacement(position, 'bottom_right');
    const x = placement.horizontal === 'left' ? 28 : placement.horizontal === 'center' ? (visual.width - width) / 2 : visual.width - width - 28;
    const y = placement.vertical === 'top' ? visual.height - height - 35 : 32;
    return { x, y, width, height };
  }

  function parsePageSelection(value) {
    const selected = new Set();
    String(value || '').split(',').map(v => v.trim()).filter(Boolean).forEach(part => {
      const match = part.match(/^(\d+)\s*-\s*(\d+)$/);
      if (match) {
        const from = Number(match[1]), to = Number(match[2]);
        for (let n = Math.min(from, to); n <= Math.max(from, to); n++) selected.add(n);
      } else if (/^\d+$/.test(part)) selected.add(Number(part));
    });
    return selected;
  }

  function shouldStampPage(settings, volume, pageIndex, entry) {
    if (settings.stampScope === 'none' || (!settings.stampBytes && !settings.textStamp)) return false;
    if (settings.stampScope === 'all_document_pages') return true;
    if (settings.stampScope === 'first_document_page') return entry && pageIndex === entry.outputFirstPageIndex;
    if (settings.stampScope === 'last_document_page') return entry && pageIndex === entry.outputFirstPageIndex + entry.pageCount - 1;
    if (settings.stampScope === 'custom_pages') return parsePageSelection(settings.stampPages).has(volume.globalPhysicalStart + pageIndex);
    return false;
  }

  function getLabelSize(choice, normalSize) {
    if (choice === 'small') return Math.max(5, normalSize - 2);
    if (choice === 'large') return normalSize + 2;
    return normalSize;
  }

  function parsePlacement(value, fallback) {
    const safe = String(value || fallback || 'bottom_right');
    const parts = safe.split('_');
    return {
      vertical: parts[0] === 'top' ? 'top' : 'bottom',
      horizontal: parts[1] === 'left' || parts[1] === 'center' ? parts[1] : 'right'
    };
  }

  function horizontalAnchor(visualWidth, horizontal, margin = 24) {
    if (horizontal === 'left') return { x: margin, align: 'left' };
    if (horizontal === 'center') return { x: visualWidth / 2, align: 'center' };
    return { x: visualWidth - margin, align: 'right' };
  }

  function getReturnLayout(visual, position, size, font, returnLabel, annexureLabel) {
    const placement = parsePlacement(position, 'top_right');
    const lineGap = size + 4;
    const paddingX = 5;
    const paddingY = 5;
    const returnWidth = font.widthOfTextAtSize(returnLabel || '', size);
    const annexureWidth = annexureLabel ? font.widthOfTextAtSize(annexureLabel, size) : 0;
    const width = Math.max(returnWidth, annexureWidth) + paddingX * 2;
    const height = lineGap * (annexureLabel ? 2 : 1) + paddingY * 2 - 2;
    const y = visual.height - height - 7;
    let x;
    let textX;
    let align;
    if (placement.horizontal === 'left') {
      x = 20; textX = x + paddingX; align = 'left';
    } else if (placement.horizontal === 'center') {
      x = (visual.width - width) / 2; textX = visual.width / 2; align = 'center';
    } else {
      x = visual.width - width - 20; textX = x + width - paddingX; align = 'right';
    }
    return {
      x, y, width, height, textX, align,
      returnY: y + height - paddingY - size,
      annexureY: y + paddingY
    };
  }

  function getPageNumberLayout(visual, position, size, footerText, returnLayout, returnPosition) {
    const placement = parsePlacement(position, 'bottom_right');
    const anchor = horizontalAnchor(visual.width, placement.horizontal, 28);
    let y = placement.vertical === 'top' ? visual.height - size - 8 : 10;

    // Avoid covering the return/annexure block when both use the same top slot.
    if (placement.vertical === 'top' && returnLayout) {
      const returnPlacement = parsePlacement(returnPosition, 'top_right');
      if (returnPlacement.horizontal === placement.horizontal) {
        y = Math.max(size + 8, returnLayout.y - size - 6);
      }
    }

    // The default footer occupies the bottom-left. Put the number just above it.
    if (placement.vertical === 'bottom' && placement.horizontal === 'left' && footerText) {
      y = 22;
    }
    return { x: anchor.x, y, align: anchor.align };
  }

  function formatPageNumber(current, finalNumber, format) {
    if (format === 'x') return String(current);
    if (format === 'page_x') return `Page ${current}`;
    if (format === 'x_of_y') return `${current} of ${finalNumber}`;
    return `Page ${current} of ${finalNumber}`;
  }

  function formatAnnexureLabel(entry) {
    const annexure = String(entry.source.annexure || '').trim() || '-';
    const base = /^(annexure|exhibit|document|chronology)\b/i.test(annexure) ? annexure : `ANNEXURE ${annexure}`;
    return entry.part ? `${base} · PART ${entry.part}` : base;
  }

  function entryTitle(entry) {
    const base = entry.source.particulars || entry.source.name;
    return entry.part ? `${base} (Part ${entry.part})` : base;
  }

  function centerText(page, text, font, size, y, color) {
    const width = font.widthOfTextAtSize(text || '', size);
    page.drawText(text || '', { x: Math.max(35, (page.getWidth() - width) / 2), y, size, font, color });
  }

  function fitAndDrawText(page, text, options) {
    let size = options.size;
    while (size > options.minSize && options.font.widthOfTextAtSize(String(text), size) > options.maxWidth) size -= 0.5;
    page.drawText(String(text), { x: options.x, y: options.y, size, font: options.font, color: options.color });
  }

  function centerFitText(page, text, font, size, y, maxWidth, color) {
    let fitted = size;
    while (fitted > 8 && font.widthOfTextAtSize(String(text), fitted) > maxWidth) fitted -= 0.5;
    centerText(page, text, font, fitted, y, color);
  }

  function centerWrapped(page, text, font, size, y, maxWidth, lineHeight, color) {
    const lines = wrapText(text || '', font, size, maxWidth);
    lines.forEach((line, i) => centerText(page, line, font, size, y - i * lineHeight, color));
  }

  function drawJustifiedLines(page, lines, options) {
    lines.forEach((line, lineIndex) => {
      const words = String(line).trim().split(/\s+/).filter(Boolean);
      const nextLineIsBlank = lineIndex < lines.length - 1 && !String(lines[lineIndex + 1]).trim();
      const isParagraphEnd = lineIndex === lines.length - 1 || nextLineIsBlank;
      const naturalLine = words.join(' ');
      if (!naturalLine) return;
      const normalSpace = options.font.widthOfTextAtSize(' ', options.size);
      const wordsWidth = words.reduce((sum, word) => sum + options.font.widthOfTextAtSize(word, options.size), 0);
      const proposedGap = words.length > 1 ? (options.width - wordsWidth) / (words.length - 1) : Infinity;
      const safeToJustify = !isParagraphEnd && words.length >= 3 && proposedGap >= normalSpace && proposedGap <= normalSpace * 2.25;
      if (!safeToJustify) {
        page.drawText(naturalLine, { x: options.x, y: options.y - lineIndex * options.lineHeight, size: options.size, font: options.font, color: options.color });
        return;
      }
      let x = options.x;
      words.forEach((word, wordIndex) => {
        page.drawText(word, { x, y: options.y - lineIndex * options.lineHeight, size: options.size, font: options.font, color: options.color });
        x += options.font.widthOfTextAtSize(word, options.size) + (wordIndex < words.length - 1 ? proposedGap : 0);
      });
    });
  }

  function wrapText(text, font, size, maxWidth) {
    const paragraphs = String(text || '').replace(/\r\n?/g, '\n').split('\n');
    const lines = [];
    paragraphs.forEach((paragraph, paragraphIndex) => {
      const words = paragraph.replace(/[\t ]+/g, ' ').trim().split(' ').filter(Boolean);
      let line = '';
      for (const originalWord of words) {
        const pieces = splitOverwideToken(originalWord, font, size, maxWidth);
        pieces.forEach((word, pieceIndex) => {
          if (pieceIndex > 0 && line) { lines.push(line); line = ''; }
          const candidate = line ? `${line} ${word}` : word;
          if (font.widthOfTextAtSize(candidate, size) <= maxWidth) line = candidate;
          else {
            if (line) lines.push(line);
            line = word;
          }
          if (pieceIndex < pieces.length - 1 && line) { lines.push(line); line = ''; }
        });
      }
      if (line) lines.push(line);
      if (paragraphIndex < paragraphs.length - 1) lines.push('');
    });
    return lines.length ? lines : [''];
  }

  function splitOverwideToken(token, font, size, maxWidth) {
    if (font.widthOfTextAtSize(token, size) <= maxWidth) return [token];
    const pieces = [];
    let piece = '';
    for (const character of Array.from(token)) {
      const candidate = piece + character;
      if (piece && font.widthOfTextAtSize(candidate, size) > maxWidth) {
        pieces.push(piece);
        piece = character;
      } else {
        piece = candidate;
      }
    }
    if (piece) pieces.push(piece);
    return pieces.length ? pieces : [''];
  }

  function setBusy(busy, keepProgress = false) {
    ui.generateButton.disabled = busy;
    $('previewButton').disabled = busy;
    ui.generateButton.textContent = busy ? 'Working…' : generateButtonLabel();
    $('previewButton').textContent = busy ? 'Working…' : 'Create exact preview';
    if (busy) {
      ui.progressPanel.classList.remove('hidden'); ui.resultPanel.classList.add('hidden');
    } else {
      ui.resultPanel.classList.remove('hidden');
      if (!keepProgress && !ui.progressText.textContent.includes('Completed')) ui.progressPanel.classList.add('hidden');
    }
  }

  function generateButtonLabel() {
    return $('outputMode') && $('outputMode').value === 'draft' ? 'Generate Draft ZIP' : 'Generate Final ZIP';
  }

  function setProgress(percent, text) {
    ui.progressBar.style.width = `${Math.max(0, Math.min(100, percent))}%`;
    ui.progressText.textContent = text;
  }

  async function sha256(bytes) {
    try {
      if (!globalThis.crypto || !globalThis.crypto.subtle) return 'unavailable-in-this-browser';
      const view = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
      const digest = await globalThis.crypto.subtle.digest('SHA-256', view);
      return [...new Uint8Array(digest)].map(b => b.toString(16).padStart(2, '0')).join('');
    } catch (_) {
      return 'unavailable-in-this-browser';
    }
  }

  function buildOutputReadme(settings, volumes) {
    return `SME GSTAT AppealKit - Generated Output\r\n\r\nVersion: Professional v0.6.2\r\nProject: ${settings.projectName}\r\nVolumes: ${volumes.length}\r\nGenerated: ${new Date().toLocaleString()}\r\n\r\nVerification steps:\r\n1. Open every volume in Adobe Acrobat Reader.\r\n2. Check the complete master index, chronology (if used), full particulars, Volume and Pages columns.\r\n3. Confirm drag/order changes, annexure numbering, page edits, rotation and removed-page choices.\r\n4. Confirm the first-page size, smart-justified subject, optional Prepared by line, printed dates, page markers and stamps.\r\n5. Click internal and cross-volume links and review bookmarks.\r\n6. Confirm the final ZIP PDF matches the last current preview.\r\n7. Check the current GSTAT portal upload limit; the size guide is advisory.\r\n8. Preserve original digitally signed source files separately.\r\n\r\nDo not file the output until it has been manually reviewed.\r\n`;
  }

  function buildPortalUploadMap(outputRecords, settings) {
    const rows = [['Sequence','Generated PDF','Pages','Size (MB)','Stage','Size guide (MB)','Within guide','SHA-256']];
    outputRecords.forEach((record, index) => {
      const sizeMB = record.bytes / 1024 / 1024;
      const withinGuide = settings.maxFileSizeMB > 0 ? (sizeMB <= settings.maxFileSizeMB ? 'Yes' : 'No - review') : 'Not checked';
      rows.push([
        index + 1, record.filename, record.pages, sizeMB.toFixed(2),
        settings.outputMode === 'draft' ? 'Draft review' : 'Final filing',
        settings.maxFileSizeMB || '', withinGuide, record.sha256
      ]);
    });
    return rows.map(row => row.map(csvCell).join(',')).join('\r\n');
  }

  function baseName(name) { return name.replace(/\.[^.]+$/, '').replace(/[_-]+/g, ' '); }
  function sanitizeFilename(name) { return String(name || 'Output').replace(/[<>:"/\\|?*\x00-\x1F]/g, '_').replace(/\s+/g, '_').slice(0, 120); }
  function friendlyError(err) {
    const msg = String(err && err.message ? err.message : err);
    if (/encrypted|password/i.test(msg)) return 'The PDF is password-protected or encrypted.';
    if (/invalid|parse|header|object/i.test(msg)) return 'The file appears damaged or is not a valid supported PDF/image.';
    return msg.slice(0, 240);
  }
  function escapeHtml(value) { return String(value ?? '').replace(/[&<>'"]/g, c => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', "'":'&#39;', '"':'&quot;' }[c])); }

  updateAnnexureModeUI();
  updateValidation();
})();

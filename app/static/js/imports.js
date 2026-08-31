document.addEventListener('DOMContentLoaded', () => {
        loadBatchLogs();
        hideGeminiKeyIfSaved();
    });

    async function hideGeminiKeyIfSaved() {
        const el = document.getElementById('impGeminiKey');
        if (!el) return;
        try {
            const st = await apiFetch('/api/imports/ai-ocr-status');
            el.style.display = (st && st.configured) ? 'none' : 'block';
        } catch (e) {
            el.style.display = 'none';
        }
    }

    async function deleteImportBatch(batchId, filename) {
        if (!confirm(`Are you sure you want to delete import batch #${batchId} (${filename})?\n\nThis will remove all sales, bank transactions, or settlement data imported in this file.`)) return;

        const res = await apiFetch(`/api/imports/batch/${batchId}`, { method: 'DELETE' });
        if (res) {
            showToast(`Import Batch #${batchId} deleted successfully!`, 'success');
            loadBatchLogs();
        }
    }

    async function loadBatchLogs() {
        const tbody = document.getElementById('batchLogTbody');
        if (!tbody) return;
        const batches = await apiFetch('/api/imports/batches');
        if (!batches) return;

        tbody.innerHTML = '';

        if (batches.length === 0) {
            tbody.innerHTML = `<tr><td colspan="11" style="text-align: center; color: var(--text-muted);">No import batches logged yet.</td></tr>`;
            return;
        }

        batches.forEach(b => {
            let statusBadge = b.status === 'COMPLETED' ? '<span class="badge badge-reconciled">Completed</span>' :
                              '<span class="badge badge-amber">' + b.status + '</span>';

            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>#${b.id}</td>
                <td>${new Date(b.uploaded_at).toLocaleString()}</td>
                <td><small>${b.file_type}</small></td>
                <td><strong>${b.filename}</strong></td>
                <td>${b.source_name}</td>
                <td>${b.total_rows}</td>
                <td style="color: var(--status-green);">${b.success_rows}</td>
                <td style="color: var(--status-red);">${b.failed_rows}</td>
                <td>${b.duplicate_rows}</td>
                <td>${statusBadge}</td>
                <td>
                    <button class="btn btn-outline-pdf" style="padding: 0.35rem 0.65rem; font-size: 0.78rem;" onclick="deleteImportBatch(${b.id}, '${b.filename.replace(/'/g, "\\'")}')">
                        <i class="fa-solid fa-trash"></i> Delete
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    }

    function setFieldInput(elId, val) {
        const el = document.getElementById(elId);
        if (!el) return;
        if (val !== null && val !== undefined) {
            el.value = val;
        } else {
            el.value = ""; // Leave blank for NOT DETECTED
        }
    }

    const IMAGE_EXTS = ['jpg', 'jpeg', 'png', 'bmp', 'webp'];
    const SHEET_EXTS = ['xlsx', 'xls', 'csv'];
    const KIND_HINT = {
        DAYBOOK: 'from cash register',
        PETPOOJA: 'from POS screen',
        EDC: 'from card machine',
        OTHER: 'from photo',
    };
    let _previewObjectUrls = [];

    function revokePreviewUrls() {
        _previewObjectUrls.forEach((url) => URL.revokeObjectURL(url));
        _previewObjectUrls = [];
    }

    function fileExt(name) {
        return String(name || '').split('.').pop().toLowerCase();
    }

    function setFieldSourceHint(elId, kind) {
        const el = document.getElementById(elId);
        if (!el) return;
        el.textContent = kind ? (KIND_HINT[kind] || '') : '';
    }

    function renderImageSourceStrip(imageFiles, sources) {
        const strip = document.getElementById('imgSourceStrip');
        revokePreviewUrls();
        if (!strip) return;
        strip.innerHTML = '';
        const urls = imageFiles.map((file) => {
            const url = URL.createObjectURL(file);
            _previewObjectUrls.push(url);
            return url;
        });
        let defaultIdx = 0;
        (sources || []).forEach((src, i) => {
            if (src && src.image_kind === 'DAYBOOK') defaultIdx = i;
        });
        imageFiles.forEach((file, i) => {
            const src = (sources || [])[i] || {};
            const kind = src.image_kind || 'OTHER';
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'img-source-chip' + (i === defaultIdx ? ' active' : '');
            btn.innerHTML = `<img src="${urls[i]}" alt=""><span>${src.label || KIND_HINT[kind] || file.name}</span>`;
            btn.onclick = () => {
                const pic = document.getElementById('imgPreviewPic');
                if (pic) pic.src = urls[i];
                strip.querySelectorAll('.img-source-chip').forEach((el) => el.classList.remove('active'));
                btn.classList.add('active');
            };
            strip.appendChild(btn);
        });
        const pic = document.getElementById('imgPreviewPic');
        if (pic && urls[defaultIdx]) pic.src = urls[defaultIdx];
    }

    function fillImageConfirmForm(data, branchId, imageFiles) {
        globalActiveAuditData = data;
        document.getElementById('imgConfirmAuditId').value = data.audit_id || '';
        document.getElementById('imgConfirmBranch').value = branchId;
        document.getElementById('imgConfirmDate').value = data.date || new Date().toISOString().split('T')[0];

        setFieldInput('imgConfirmCash', data.cash);
        setFieldInput('imgConfirmCard', data.card_qr);
        setFieldInput('imgConfirmZomato', data.zomato);
        setFieldInput('imgConfirmSwiggy', data.swiggy);
        setFieldInput('imgConfirmDineout', data.dineout);
        setFieldInput('imgConfirmOpening', data.opening_balance);
        setFieldInput('imgConfirmExpenses', data.site_expenses);
        setFieldInput('imgConfirmSalaryAdv', data.salary_advance);
        let closingVal = data.closing_balance;
        if (closingVal === null || closingVal === undefined) {
            const op = parseFloat(data.opening_balance || 0);
            const cashAmt = parseFloat(data.cash || 0);
            const exp = parseFloat(data.site_expenses || 0);
            const adv = parseFloat(data.salary_advance || 0);
            closingVal = Math.round((op + cashAmt - exp - adv) * 100) / 100;
        }
        setFieldInput('imgConfirmClosing', closingVal);

        const sources = data.field_sources || {};
        setFieldSourceHint('srcDate', sources.date);
        setFieldSourceHint('srcCash', sources.cash);
        setFieldSourceHint('srcCard', sources.card_qr);
        setFieldSourceHint('srcZomato', sources.zomato);
        setFieldSourceHint('srcSwiggy', sources.swiggy);
        setFieldSourceHint('srcDineout', sources.dineout);
        setFieldSourceHint('srcOpening', sources.opening_balance);
        setFieldSourceHint('srcClosing', sources.closing_balance);
        setFieldSourceHint('srcExpenses', sources.site_expenses);
        setFieldSourceHint('srcSalary', sources.salary_advance);
        refreshSalaryAdvanceMap();

        renderImageSourceStrip(imageFiles, data.source_images || []);

        const banner = document.getElementById('imgTotalMismatchBanner');
        const mismatchParts = (data.mismatches || []).map((m) => m.message).filter(Boolean);
        if (data.handwritten_total && Math.abs(data.total_difference) > 1.0) {
            mismatchParts.push(
                `Sheet total ${formatINR(data.handwritten_total)} vs ${formatINR(data.calculated_total)} — please check.`
            );
        }
        if (mismatchParts.length) {
            document.getElementById('imgTotalMismatchText').innerText = mismatchParts.join(' ');
            banner.style.display = 'block';
        } else {
            banner.style.display = 'none';
        }

        const verifyBanner = document.getElementById('imgVerifyBanner');
        const verifyParts = (data.verifications || []).map((v) => v.message).filter(Boolean);
        if (verifyBanner) {
            if (verifyParts.length) {
                document.getElementById('imgVerifyText').innerText = verifyParts.join(' ');
                verifyBanner.style.display = 'block';
            } else {
                verifyBanner.style.display = 'none';
            }
        }

        calcModalSalesTotal();
        openModal('imagePreviewModal');
    }

    function calcModalSalesTotal() {
        const cash = parseFloat(document.getElementById('imgConfirmCash').value || 0);
        const card = parseFloat(document.getElementById('imgConfirmCard').value || 0);
        const zomato = parseFloat(document.getElementById('imgConfirmZomato').value || 0);
        const swiggy = parseFloat(document.getElementById('imgConfirmSwiggy').value || 0);
        const dineout = parseFloat(document.getElementById('imgConfirmDineout').value || 0);
        const total = cash + card + zomato + swiggy + dineout;
        const el = document.getElementById('imgConfirmTotalSalesBar');
        if (el) el.innerText = formatINR(total);
    }

    let globalActiveAuditData = null;

    function renderStatusBadge(elId, srcElId, fieldObj) {
        const bEl = document.getElementById(elId);
        const sEl = document.getElementById(srcElId);
        if (!bEl || !fieldObj) return;

        const valScore = Math.round(fieldObj.numeric_validation_score || 85);
        const ocrConf = Math.round((fieldObj.ocr_confidence || fieldObj.confidence || 0.85) * 100);

        if (fieldObj.status === 'CONFIRMED') {
            bEl.className = 'badge badge-reconciled';
            bEl.innerText = `✓ CONFIRMED (Val: ${valScore}%)`;
            bEl.style.display = 'inline-block';
        } else if (fieldObj.status === 'REVIEW_REQUIRED' || (fieldObj.status && fieldObj.status.startsWith('AMBIGUOUS'))) {
            bEl.className = 'badge badge-amber';
            bEl.innerText = `⚠ REVIEW REQUIRED (Val: ${valScore}%)`;
            bEl.style.display = 'inline-block';
        } else {
            bEl.className = 'badge badge-unmatched';
            bEl.innerText = `NOT DETECTED`;
            bEl.style.display = 'inline-block';
        }

        if (sEl) {
            let srcText = '';
            if (fieldObj.source_row_id) {
                srcText = `Source: Row #${fieldObj.source_row_id} (${fieldObj.source_description || fieldObj.raw_description || ''})`;
            } else if (fieldObj.source_row) {
                srcText = `Source: ${fieldObj.source_row}`;
            } else {
                srcText = 'Not detected in sheet — please verify';
            }

            if (fieldObj.value !== null) {
                srcText += ` | OCR: ${ocrConf}% | Numeric Validation: ${valScore}%`;
            }
            sEl.innerText = srcText;
        }
    }

    async function reprocessRow(rowId, yTop, yBottom) {
        const fileInput = document.getElementById('impDailyFile');
        if (!fileInput.files[0]) {
            showToast('Original image file not found in file input.', 'warning');
            return;
        }

        showToast(`Reprocessing Row #${rowId}...`, 'info');
        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        formData.append('row_id', rowId);
        formData.append('y_top', yTop);
        formData.append('y_bottom', yBottom);

        const updatedRow = await apiFetch('/api/imports/reprocess-row', {
            method: 'POST',
            body: formData
        });

        if (updatedRow && globalActiveAuditData) {
            const rows = globalActiveAuditData.parsed_rows || [];
            const idx = rows.findIndex(r => r.row_id === rowId);
            if (idx !== -1) {
                rows[idx] = updatedRow;
            }
            showToast(`Row #${rowId} reprocessed! Amount: ${updatedRow.amount !== null ? formatINR(updatedRow.amount) : 'Not detected'}`, 'success');
            openOcrDetailsDrawer();
        }
    }

    async function openOcrDetailsDrawer() {
        if (!globalActiveAuditData) {
            showToast('No active OCR session found.', 'warning');
            return;
        }

        const data = globalActiveAuditData;
        const boxesImg = document.getElementById('ocrDetailsBoxesImg');
        if (boxesImg) boxesImg.src = data.annotated_row_boxes_b64 || data.image_b64;
        document.getElementById('ocrDetailsPrepImg').src = data.preprocessed_image_b64 || data.image_b64;
        document.getElementById('ocrDetailsCropImg').src = data.amount_crop_b64 || data.image_b64;

        // Render Rows Table
        const tbody = document.getElementById('ocrDetailsRowsTbody');
        tbody.innerHTML = '';
        const rows = data.parsed_rows || [];

        if (rows.length === 0) {
            tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-muted);">No structured table rows extracted.</td></tr>`;
        } else {
            rows.forEach(r => {
                const tr = document.createElement('tr');
                const valScore = Math.round(r.numeric_validation_score || 80);
                const amtValStr = r.amount !== null ? formatINR(r.amount) : (r.amount_status && r.amount_status.startsWith('AMBIGUOUS') ? '⚠️ Ambiguous' : 'Not detected');
                
                const amtCropImg = r.amount_crop_b64 ? 
                    `<img src="data:image/jpeg;base64,${r.amount_crop_b64.replace('data:image/jpeg;base64,','')}" style="max-height: 28px; max-width: 90px; object-fit: contain; border-radius: 3px; border: 1px solid var(--border-color); background: #000;">` : 
                    (r.row_crop_b64 ? `<img src="${r.row_crop_b64}" style="max-height: 28px; max-width: 90px; object-fit: contain; border-radius: 3px;">` : '-');

                let candHtml = '';
                if (r.candidates && r.candidates.length > 0) {
                    candHtml = '<ul style="margin: 0; padding-left: 1rem; font-size: 0.70rem; color: var(--text-muted);">' + 
                        r.candidates.map(c => `<li>${c.pass || 'Pass'}: <strong>${c.ocr_text || c.value}</strong></li>`).join('') + 
                        '</ul>';
                }
                if (r.why_selected) {
                    candHtml += `<div style="font-size: 0.68rem; color: #38bdf8; margin-top: 0.2rem; white-space: pre-line;">${r.why_selected}</div>`;
                }
                if (!candHtml) candHtml = `<small style="color: var(--text-muted);">${r.amount_raw || '-'}</small>`;

                const stBadge = r.amount_status === 'CONFIRMED' ? 
                    '<span class="badge badge-reconciled">✓ CONFIRMED</span>' : 
                    (r.amount_status === 'REVIEW_REQUIRED' ? '<span class="badge badge-amber">⚠ REVIEW</span>' : '<span class="badge badge-unmatched">NOT DETECTED</span>');

                tr.innerHTML = `
                    <td><strong>Row #${r.row_id || r.row}</strong></td>
                    <td><strong>${r.description_raw || r.description || '-'}</strong></td>
                    <td style="text-align: center;">${amtCropImg}</td>
                    <td><strong style="color: #38bdf8; font-size: 0.95rem;">${amtValStr}</strong></td>
                    <td>${candHtml}</td>
                    <td><strong style="color: ${valScore >= 80 ? 'var(--status-green)' : 'var(--status-amber)'};">${valScore}%</strong></td>
                    <td>${stBadge}</td>
                    <td>
                        <button class="btn btn-secondary" style="padding: 0.2rem 0.45rem; font-size: 0.7rem;" onclick="reprocessRow(${r.row_id || r.row}, ${r.y_top || 0}, ${r.y_bottom || 0})">
                            <i class="fa-solid fa-rotate"></i> Reprocess
                        </button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        }

        // Render Full Extraction Trace JSON Log
        const traceData = data.extraction_trace || {
            raw_ocr_detections: data.raw_ocr_response || [],
            reconstructed_rows: data.parsed_rows || [],
            classified_fields: data.fields || {}
        };
        document.getElementById('ocrDetailsRawJson').innerText = JSON.stringify(traceData, null, 2);

        openModal('ocrDetailsModal');
    }

    async function uploadDailySales(e) {
        e.preventDefault();
        const branch_id = document.getElementById('impDailyBranch').value;
        const fileInput = document.getElementById('impDailyFile');
        const allFiles = Array.from(fileInput.files || []);
        if (!allFiles.length) return;

        const images = allFiles.filter((f) => IMAGE_EXTS.includes(fileExt(f.name)));
        const sheets = allFiles.filter((f) => SHEET_EXTS.includes(fileExt(f.name)));
        if (images.length && sheets.length) {
            showToast('Choose either one Excel/CSV file or 1–5 photos of the same day.', 'error');
            return;
        }
        if (images.length > 5) {
            showToast('Upload at most 5 photos for the same day.', 'error');
            return;
        }

        const file = sheets[0] || images[0];

        const submitBtn = e.target ? e.target.querySelector('button[type="submit"]') : null;
        const origBtnHtml = submitBtn ? submitBtn.innerHTML : '';
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = images.length
                ? `<i class="fa-solid fa-spinner fa-spin"></i> Reading ${images.length} photo${images.length > 1 ? 's' : ''}...`
                : '<i class="fa-solid fa-spinner fa-spin"></i> Reading Image & Figures...';
        }

        try {
            // If Image File -> Trigger Preview & Confirm Modal
            if (images.length) {
                const geminiKey = (document.getElementById('impGeminiKey') || {}).value || '';
                if (geminiKey.trim()) {
                    await apiFetch('/api/imports/ai-ocr-key', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ key: geminiKey.trim() })
                    });
                    document.getElementById('impGeminiKey').value = '';
                    document.getElementById('impGeminiKey').style.display = 'none';
                }
                showToast(images.length > 1
                    ? `Reading ${images.length} photos and matching the same-day figures...`
                    : 'Reading image with AI...', 'info');
                const formData = new FormData();
                images.forEach((img) => formData.append('files', img));

                const data = await apiFetch('/api/imports/preview-image', {
                    method: 'POST',
                    body: formData
                });

                if (data) {
                    if (data.status === 'ERROR') {
                        showToast(`Image Processing Failed: ${data.error_detail}`, 'error');
                        if ((data.last_step || '').includes('not configured')) {
                            const keyBox = document.getElementById('impGeminiKey');
                            if (keyBox) keyBox.style.display = 'block';
                        }
                        alert(`IMAGE EXTRACTION FAILED\n\nLast Step: ${data.last_step || 'UNKNOWN'}\nError: ${data.error_detail}`);
                        return;
                    }
                    fillImageConfirmForm(data, branch_id, images);
                }
                return;
            }

            // Excel or CSV File Upload
            const formData = new FormData();
            formData.append('branch_id', branch_id);
            formData.append('file', file);

            showToast('Uploading daily sales file...', 'info');
            const res = await apiFetch('/api/imports/daily-sales', {
                method: 'POST',
                body: formData
            });

            if (res) {
                showToast(`Daily Sales Import Completed! Success: ${res.success_rows}, Duplicates: ${res.duplicate_rows}`, 'success');
                loadBatchLogs();
                if (typeof loadDayBook === 'function') loadDayBook();
            }
        } catch (err) {
            showToast(err.message || 'Image import failed', 'error');
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = origBtnHtml;
            }
        }
    }

    async function submitConfirmedImageImport(e) {
        e.preventDefault();
        const payload = {
            audit_id: parseInt(document.getElementById('imgConfirmAuditId').value || 0) || null,
            branch_id: parseInt(document.getElementById('imgConfirmBranch').value),
            sale_date: document.getElementById('imgConfirmDate').value,
            cash: parseFloat(document.getElementById('imgConfirmCash').value || 0),
            card_qr: parseFloat(document.getElementById('imgConfirmCard').value || 0),
            zomato: parseFloat(document.getElementById('imgConfirmZomato').value || 0),
            swiggy: parseFloat(document.getElementById('imgConfirmSwiggy').value || 0),
            dineout: parseFloat(document.getElementById('imgConfirmDineout').value || 0),
            opening_balance: parseFloat(document.getElementById('imgConfirmOpening').value || 0),
            site_expenses: parseFloat(document.getElementById('imgConfirmExpenses').value || 0),
            salary_advance: parseFloat(document.getElementById('imgConfirmSalaryAdv').value || 0),
            salary_advance_splits: collectSalaryAdvanceSplits(),
            closing_balance: parseFloat(document.getElementById('imgConfirmClosing').value || 0)
        };

        const res = await apiFetch('/api/imports/confirm-image-import', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (res) {
            showToast('Image register data confirmed and saved to Day Book & Cash Rec!', 'success');
            revokePreviewUrls();
            closeModal('imagePreviewModal');
            loadBatchLogs();
            if (typeof loadDayBook === 'function') loadDayBook();
            if (typeof loadCashRec === 'function') loadCashRec();
        }
    }

    async function uploadBankStatement(e) {
        e.preventDefault();
        const bank_account = document.getElementById('impBankAccount').value;
        const fileInput = document.getElementById('impBankFile');

        if (!fileInput.files[0]) return;

        const formData = new FormData();
        formData.append('bank_account', bank_account);
        formData.append('file', fileInput.files[0]);

        showToast('Importing bank receipts and reconciling to Day Book Card/QR...', 'info');
        const res = await apiFetch('/api/imports/bank-statement', {
            method: 'POST',
            body: formData
        });

        if (res) {
            const skipped = res.skipped_rows ? ` · skipped ${res.skipped_rows} non-bank rows` : '';
            const matched = res.matched_count ? ` · matched ${res.matched_count} sale day(s)` : '';
            showToast(`Imported ${res.success_rows} bank receipt(s)${skipped}${matched}.`, 'success');
            if (typeof loadBatchLogs === 'function') loadBatchLogs();
            if (typeof loadCardQrRec === 'function') loadCardQrRec();
        }
    }

    async function uploadAggregatorSettlement(e) {
        e.preventDefault();
        const aggregator_id = document.getElementById('impAggregatorId').value;
        const branch_id = document.getElementById('impAggBranchId').value;
        const period_start_date = document.getElementById('impAggStart').value;
        const period_end_date = document.getElementById('impAggEnd').value;
        const fileInput = document.getElementById('impAggFile');

        if (!fileInput.files[0]) return;

        const formData = new FormData();
        formData.append('aggregator_id', aggregator_id);
        formData.append('branch_id', branch_id);
        formData.append('period_start_date', period_start_date);
        formData.append('period_end_date', period_end_date);
        formData.append('file', fileInput.files[0]);

        showToast('Processing Aggregator Settlement file...', 'info');
        const res = await apiFetch('/api/imports/aggregator-settlement', {
            method: 'POST',
            body: formData
        });

        if (res) {
            showToast(`Settlement Processed! Gross: ${formatINR(res.gross_sales)}, Payout: ${formatINR(res.payout)}`, 'success');
            loadBatchLogs();
            if (typeof loadPayoutBreakup === 'function') loadPayoutBreakup();
        }
    }

    let salaryAdvanceStaff = [];

    function onSalaryAdvanceChanged() {
        if (typeof calcModalSalesTotal === 'function') calcModalSalesTotal();
        refreshSalaryAdvanceMap();
    }

    function collectSalaryAdvanceSplits() {
        const splits = [];
        document.querySelectorAll('.sal-adv-row').forEach((row) => {
            const employeeId = parseInt((row.querySelector('.sal-adv-emp') || {}).value || 0, 10);
            const amount = parseFloat((row.querySelector('.sal-adv-amt') || {}).value || 0);
            if (employeeId && amount > 0) splits.push({ employee_id: employeeId, amount });
        });
        return splits;
    }

    function addSalaryAdvanceRow(employeeId, amount) {
        const wrap = document.getElementById('salaryAdvanceRows');
        if (!wrap) return;
        const row = document.createElement('div');
        row.className = 'sal-adv-row';
        row.style.cssText = 'display:grid;grid-template-columns:1fr 110px 36px;gap:0.4rem;margin-bottom:0.4rem;align-items:center;';
        const options = [`<option value="">Select staff</option>`].concat(
            salaryAdvanceStaff.map((s) => `<option value="${s.id}">${s.name}${s.rank ? ' · ' + s.rank : ''}</option>`)
        ).join('');
        row.innerHTML = `
            <select class="form-select sal-adv-emp">${options}</select>
            <input type="number" step="0.01" class="form-control sal-adv-amt" value="${amount || ''}" oninput="updateSalaryAdvanceHint()">
            <button type="button" class="btn btn-secondary btn-sm" onclick="this.closest('.sal-adv-row').remove(); updateSalaryAdvanceHint();">&times;</button>
        `;
        wrap.appendChild(row);
        if (employeeId) row.querySelector('.sal-adv-emp').value = String(employeeId);
        updateSalaryAdvanceHint();
    }

    function updateSalaryAdvanceHint() {
        const hint = document.getElementById('salaryAdvanceHint');
        if (!hint) return;
        const total = parseFloat((document.getElementById('imgConfirmSalaryAdv') || {}).value || 0);
        const mapped = collectSalaryAdvanceSplits().reduce((sum, row) => sum + row.amount, 0);
        const left = Math.round((total - mapped) * 100) / 100;
        hint.textContent = left === 0
            ? 'All of this advance is mapped to staff.'
            : `Unmapped: ${typeof formatINR === 'function' ? formatINR(left) : left}`;
    }

    async function refreshSalaryAdvanceMap() {
        const box = document.getElementById('salaryAdvanceMap');
        const wrap = document.getElementById('salaryAdvanceRows');
        if (!box || !wrap) return;
        const total = parseFloat((document.getElementById('imgConfirmSalaryAdv') || {}).value || 0);
        if (!(total > 0)) {
            box.style.display = 'none';
            wrap.innerHTML = '';
            return;
        }
        box.style.display = 'block';
        const branchId = (document.getElementById('imgConfirmBranch') || {}).value || '';
        const rows = await apiFetch(`/api/attendance/staff${branchId ? `?branch_id=${branchId}` : ''}`);
        salaryAdvanceStaff = rows || [];
        const current = collectSalaryAdvanceSplits();
        wrap.innerHTML = '';
        if (current.length) current.forEach((row) => addSalaryAdvanceRow(row.employee_id, row.amount));
        else addSalaryAdvanceRow('', total);
        updateSalaryAdvanceHint();
    }

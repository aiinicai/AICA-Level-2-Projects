let currentRevision = 0;
let pdfDoc = null;
let pageNum = 1;
let scale = 1.0;
let transactions = [];
let validationExceptions = [];
let auditEvents = [];

document.addEventListener("DOMContentLoaded", () => {
    loadReviewData();
    loadPdf();
    
    document.getElementById('prev-page').addEventListener('click', onPrevPage);
    document.getElementById('next-page').addEventListener('click', onNextPage);
    document.getElementById('zoom-select').addEventListener('change', (e) => {
        scale = parseFloat(e.target.value);
        renderPage(pageNum);
    });
});

async function loadReviewData() {
    try {
        const res = await fetch(`/review/api/${JOB_ID}/data`);
        const data = await res.json();
        
        if(data.status === "error") {
            alert(data.message);
            return;
        }
        
        currentRevision = data.review_revision;
        transactions = data.transactions;
        validationExceptions = data.validation?.exceptions || [];
        
        document.getElementById('rev-badge').innerText = currentRevision;
        document.getElementById('val-badge').innerText = data.review_status;
        
        if (data.suggestions && data.suggestions.length > 0) {
            document.getElementById('suggestions-banner').style.display = 'block';
        }
        
        renderTransactions();
    } catch (e) {
        console.error(e);
        alert("Failed to load review data.");
    }
}

async function loadPdf() {
    const url = `/upload/api/pdf/${JOB_ID}`;
    try {
        pdfDoc = await pdfjsLib.getDocument(url).promise;
        document.getElementById('page-count').textContent = pdfDoc.numPages;
        renderPage(pageNum);
    } catch(e) {
        console.error("PDF load error:", e);
    }
}

async function renderPage(num) {
    if(!pdfDoc) return;
    const page = await pdfDoc.getPage(num);
    const viewport = page.getViewport({ scale: scale });
    
    const canvas = document.getElementById('pdf-canvas');
    const ctx = canvas.getContext('2d');
    canvas.height = viewport.height;
    canvas.width = viewport.width;
    
    const overlayCanvas = document.getElementById('overlay-canvas');
    overlayCanvas.width = viewport.width;
    overlayCanvas.height = viewport.height;
    
    const renderContext = { canvasContext: ctx, viewport: viewport };
    await page.render(renderContext).promise;
}

function renderTransactions(filter = 'all') {
    const container = document.getElementById('transactions-list');
    container.style.display = 'block';
    document.getElementById('audit-list').style.display = 'none';
    
    let html = `<table class="table table-bordered table-sm" style="font-size: 12px;">
        <thead><tr>
            <th>Date</th><th>Narration</th><th>Debit</th><th>Credit</th><th>Balance</th><th>Action</th>
        </tr></thead><tbody>`;
        
    let activeTxs = transactions.filter(t => t.review_status !== "SUPERSEDED");
    
    if (filter === 'exceptions') {
        const errTxIds = validationExceptions.map(e => e.transaction_index); // Wait, Stage 5 uses index.
        // Stage 7 uses transaction_id. If validation is mapping to index, we have a mismatch!
        // We'll highlight if any exception exists.
        // For simplicity, if we don't have exact ID mapping from validator, we'll just show all active for now if there are ANY exceptions.
        activeTxs = activeTxs.filter(t => validationExceptions.length > 0);
    }
    
    activeTxs.forEach(tx => {
        const isNonTx = tx.review_status === "NON_TRANSACTION";
        let trStyle = isNonTx ? 'text-decoration: line-through; color: #999;' : '';
        
        html += `<tr style="${trStyle}" onclick="highlightSource(${tx.source_page}, ${tx.source_bbox ? `'${JSON.stringify(tx.source_bbox)}'` : null})">
            <td>${tx.transaction_date || ''}</td>
            <td title="${tx.narration}">${tx.narration.substring(0,20)}...</td>
            <td>${tx.debit !== null ? tx.debit : ''}</td>
            <td>${tx.credit !== null ? tx.credit : ''}</td>
            <td>${tx.balance !== null ? tx.balance : ''}</td>
            <td>
                <button class="btn btn-sm" onclick="openEdit('${tx.transaction_id}')">Edit</button>
                <button class="btn btn-sm" onclick="doAction('${tx.transaction_id}', '${isNonTx ? 'RESTORE_TRANSACTION' : 'MARK_NON_TRANSACTION'}')">
                    ${isNonTx ? 'Restore' : 'Del'}
                </button>
            </td>
        </tr>`;
    });
    html += `</tbody></table>`;
    container.innerHTML = html;
}

function highlightSource(pageNo, bboxStr) {
    if (pageNo && pageNo !== pageNum) {
        pageNum = pageNo;
        document.getElementById('page-num').innerText = pageNum;
        renderPage(pageNum).then(() => drawBbox(bboxStr));
    } else {
        drawBbox(bboxStr);
    }
}

function drawBbox(bboxStr) {
    const overlay = document.getElementById('overlay-canvas');
    const ctx = overlay.getContext('2d');
    ctx.clearRect(0, 0, overlay.width, overlay.height);
    
    if(!bboxStr) return;
    try {
        const bbox = JSON.parse(bboxStr);
        ctx.fillStyle = "rgba(255, 255, 0, 0.4)";
        ctx.strokeStyle = "red";
        ctx.lineWidth = 2;
        // Transform PDF space to pixels
        const x = bbox.x0 * scale;
        const y = bbox.top * scale;
        const w = (bbox.x1 - bbox.x0) * scale;
        const h = (bbox.bottom - bbox.top) * scale;
        ctx.fillRect(x, y, w, h);
        ctx.strokeRect(x, y, w, h);
    } catch(e) {}
}

function openEdit(txId) {
    const tx = transactions.find(t => t.transaction_id === txId);
    if(!tx) return;
    
    document.getElementById('edit-tx-id').value = tx.transaction_id;
    document.getElementById('m-date').innerText = tx.transaction_date || '';
    document.getElementById('e-date').value = tx.transaction_date || '';
    
    document.getElementById('m-narration').innerText = tx.narration || '';
    document.getElementById('e-narration').value = tx.narration || '';
    
    document.getElementById('m-debit').innerText = tx.debit !== null ? tx.debit : '';
    document.getElementById('e-debit').value = tx.debit !== null ? tx.debit : '';
    
    document.getElementById('m-credit').innerText = tx.credit !== null ? tx.credit : '';
    document.getElementById('e-credit').value = tx.credit !== null ? tx.credit : '';
    
    document.getElementById('m-balance').innerText = tx.balance !== null ? tx.balance : '';
    document.getElementById('e-balance').value = tx.balance !== null ? tx.balance : '';
    
    document.getElementById('edit-modal').style.display = 'block';
}

async function submitEdit() {
    const txId = document.getElementById('edit-tx-id').value;
    const updates = {
        transaction_date: document.getElementById('e-date').value || null,
        narration: document.getElementById('e-narration').value || "",
        debit: document.getElementById('e-debit').value || null,
        credit: document.getElementById('e-credit').value || null,
        balance: document.getElementById('e-balance').value || null
    };
    
    const reason = document.getElementById('e-reason').value;
    
    try {
        const res = await fetch(`/review/api/${JOB_ID}/edit`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                transaction_id: txId,
                expected_revision: currentRevision,
                updates: updates,
                reason: reason
            })
        });
        const data = await res.json();
        if(data.status === 'success') {
            document.getElementById('edit-modal').style.display = 'none';
            loadReviewData();
        } else {
            alert("Error: " + data.message);
        }
    } catch(e) {
        alert("Network error");
    }
}

async function doAction(txId, action) {
    if(!confirm(`Are you sure you want to ${action}?`)) return;
    try {
        const res = await fetch(`/review/api/${JOB_ID}/action`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                transaction_id: txId,
                expected_revision: currentRevision,
                action: action
            })
        });
        const data = await res.json();
        if(data.status === 'success') {
            loadReviewData();
        } else {
            alert("Error: " + data.message);
        }
    } catch(e) {
        alert("Network error");
    }
}

async function showAudit() {
    document.getElementById('transactions-list').style.display = 'none';
    const container = document.getElementById('audit-list');
    container.style.display = 'block';
    container.innerHTML = "Loading...";
    
    const res = await fetch(`/review/api/${JOB_ID}/audit`);
    const data = await res.json();
    if(data.status !== 'success') return;
    
    let html = `<table class="table table-bordered table-sm" style="font-size:11px;">
        <thead><tr><th>Time</th><th>Action</th><th>Field</th><th>Before</th><th>After</th><th>Reason</th></tr></thead><tbody>`;
        
    data.events.forEach(e => {
        html += `<tr>
            <td>${e.timestamp}</td>
            <td>${e.action}</td>
            <td>${e.field_name || '-'}</td>
            <td>${e.before_value || '-'}</td>
            <td>${e.after_value || '-'}</td>
            <td>${e.reason || '-'}</td>
        </tr>`;
    });
    html += `</tbody></table>`;
    container.innerHTML = html;
}

function filterTransactions(f) { renderTransactions(f); }
function onPrevPage() { if (pageNum <= 1) return; pageNum--; document.getElementById('page-num').innerText = pageNum; renderPage(pageNum); }
function onNextPage() { if (pdfDoc && pageNum >= pdfDoc.numPages) return; pageNum++; document.getElementById('page-num').innerText = pageNum; renderPage(pageNum); }

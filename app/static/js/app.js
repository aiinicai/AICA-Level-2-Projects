// Core JS Helper Utilities for Restaurant Sales & Reconciliation App

function formatINR(amount) {
    if (amount === null || amount === undefined || isNaN(amount)) return "₹ 0.00";
    const val = Number(amount);
    const formatted = new Intl.NumberFormat('en-IN', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(val);
    return `₹ ${formatted}`;
}

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.style.position = 'fixed';
    toast.style.bottom = '20px';
    toast.style.right = '20px';
    toast.style.padding = '12px 20px';
    toast.style.borderRadius = '8px';
    toast.style.color = '#fff';
    toast.style.fontSize = '0.9rem';
    toast.style.fontWeight = '600';
    toast.style.zIndex = '9999';
    toast.style.boxShadow = '0 4px 12px rgba(0,0,0,0.4)';
    toast.style.transition = 'all 0.3s ease';

    if (type === 'success') {
        toast.style.background = '#16a34a';
    } else if (type === 'error') {
        toast.style.background = '#ef4444';
    } else {
        toast.style.background = '#0f172a';
    }

    toast.innerText = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

async function apiFetch(url, options = {}) {
    try {
        const response = await fetch(url, {
            ...options,
            headers: {
                'Accept': 'application/json',
                ...options.headers
            }
        });

        if (response.status === 401) {
            window.location.href = '/login';
            return null;
        }

        const text = await response.text();
        let data;
        try {
            data = JSON.parse(text);
        } catch (e) {
            if (!response.ok) {
                throw new Error(`Server error (${response.status}): ${text.substring(0, 100)}`);
            }
            throw new Error(`Invalid server response format: ${text.substring(0, 100)}`);
        }

        if (!response.ok) {
            throw new Error(data.detail || data.error_detail || 'An API error occurred');
        }
        return data;
    } catch (err) {
        showToast(err.message, 'error');
        throw err;
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('active');
    }
}

function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('active');
    }
}

function pad2(value) {
    return String(value).padStart(2, '0');
}

function currentFinancialYearStart(now) {
    now = now || new Date();
    return now.getMonth() >= 3 ? now.getFullYear() : now.getFullYear() - 1;
}

function financialYearRange(startYear) {
    return { start: `${startYear}-04-01`, end: `${startYear + 1}-03-31` };
}

function financialYearLabel(startYear) {
    return `FY ${startYear}-${String(startYear + 1).slice(-2)}`;
}

function periodRange(prefix) {
    const type = ((document.getElementById(prefix + 'PeriodType') || {}).value) || 'month';
    const now = new Date();
    if (type === 'date') {
        let start = (document.getElementById(prefix + 'Date') || {}).value || '';
        let end = (document.getElementById(prefix + 'DateEnd') || {}).value || start;
        if (start && end && end < start) {
            const swap = start;
            start = end;
            end = swap;
        }
        return { start, end: end || start };
    }
    if (type === 'year') {
        const year = parseInt((document.getElementById(prefix + 'Year') || {}).value, 10) || currentFinancialYearStart(now);
        return financialYearRange(year);
    }
    const raw = (document.getElementById(prefix + 'Month') || {}).value || '';
    const [year, month] = raw.split('-').map(Number);
    if (!year || !month) return { start: '', end: '' };
    const last = new Date(year, month, 0).getDate();
    return { start: `${year}-${pad2(month)}-01`, end: `${year}-${pad2(month)}-${pad2(last)}` };
}

function periodLabel(prefix) {
    const type = ((document.getElementById(prefix + 'PeriodType') || {}).value) || 'month';
    const range = periodRange(prefix);
    if (type === 'date') {
        if (range.start && range.end && range.start !== range.end) return `${range.start} to ${range.end}`;
        return range.start || 'Custom range';
    }
    if (type === 'year') {
        const year = parseInt((document.getElementById(prefix + 'Year') || {}).value, 10);
        return year ? financialYearLabel(year) : 'Financial year';
    }
    return (document.getElementById(prefix + 'Month') || {}).value || 'Month';
}

function syncPeriodFilterUi(prefix) {
    const type = ((document.getElementById(prefix + 'PeriodType') || {}).value) || 'month';
    const monthWrap = document.getElementById(prefix + 'MonthWrap');
    const dateWrap = document.getElementById(prefix + 'DateWrap');
    const dateEndWrap = document.getElementById(prefix + 'DateEndWrap');
    const yearWrap = document.getElementById(prefix + 'YearWrap');
    const monthLabel = document.getElementById(prefix + 'MonthLabel');
    if (monthWrap) monthWrap.style.display = type === 'month' ? '' : 'none';
    if (dateWrap) dateWrap.style.display = type === 'date' ? '' : 'none';
    if (dateEndWrap) dateEndWrap.style.display = type === 'date' ? '' : 'none';
    if (yearWrap) yearWrap.style.display = type === 'year' ? '' : 'none';
    if (monthLabel) monthLabel.textContent = 'Month';
}

function onPeriodFilterChange(prefix, reloadName) {
    syncPeriodFilterUi(prefix);
    if (reloadName && typeof window[reloadName] === 'function') window[reloadName]();
}

function initPeriodFilter(prefix) {
    const now = new Date();
    const monthEl = document.getElementById(prefix + 'Month');
    const dateEl = document.getElementById(prefix + 'Date');
    const yearEl = document.getElementById(prefix + 'Year');
    if (monthEl && !monthEl.value) monthEl.value = `${now.getFullYear()}-${pad2(now.getMonth() + 1)}`;
    const dateEndEl = document.getElementById(prefix + 'DateEnd');
    if (dateEl && !dateEl.value) dateEl.value = now.toISOString().split('T')[0];
    if (dateEndEl && !dateEndEl.value) dateEndEl.value = dateEl && dateEl.value ? dateEl.value : now.toISOString().split('T')[0];
    if (yearEl && !yearEl.value) yearEl.value = String(currentFinancialYearStart(now));
    syncPeriodFilterUi(prefix);
}

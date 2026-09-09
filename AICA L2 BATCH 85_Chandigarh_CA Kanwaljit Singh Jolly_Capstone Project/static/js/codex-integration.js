let codexLoginPoll = null;
let codexLoginPending = false;

function setCodexLoginState(state) {
    codexLoginPending = state !== 'idle';
    const button = document.getElementById('connect-codex-btn');
    if (!button) return;

    const generating = state === 'generating';
    button.disabled = codexLoginPending;
    button.setAttribute('aria-busy', generating ? 'true' : 'false');
    button.classList.toggle('is-loading', generating);
    button.classList.toggle('is-waiting', state === 'waiting');

    if (generating) {
        button.dataset.idleLabel ||= button.textContent.trim() || 'Connect ChatGPT';
        button.style.minInlineSize = `${Math.ceil(button.getBoundingClientRect().width)}px`;
        button.textContent = '';
        button.setAttribute('aria-label', 'Generating ChatGPT login code');
    } else {
        button.style.minInlineSize = '';
        button.removeAttribute('aria-label');
        button.textContent = state === 'waiting'
            ? 'Waiting for ChatGPT login...'
            : (button.dataset.idleLabel || 'Connect ChatGPT');
    }
}

function stopCodexLoginPolling() {
    clearInterval(codexLoginPoll);
    codexLoginPoll = null;
    setCodexLoginState('idle');
}

async function loadCodexIntegration() {
    const status = document.getElementById('codex-connection-status');
    if (!status) return;
    try {
        const integrations = await apiRequest('/api/tenant/integrations', { method: 'GET' }, 'Loading integrations');
        const connection = integrations.codex;
        const connectBtn = document.getElementById('connect-codex-btn');
        const disconnectBtn = document.getElementById('disconnect-codex-btn');
        if (connection) {
            status.innerHTML = `<p><strong>Connected</strong>${connection.account_email ? ` as ${escapeHtml(connection.account_email)}` : ''}</p>
                <p class="text-muted">Plan: ${escapeHtml(connection.account_plan || 'ChatGPT')} · SDK ${escapeHtml(connection.sdk_version || 'unknown')}</p>`;
            connectBtn.dataset.idleLabel = 'Reconnect ChatGPT';
            if (!codexLoginPending) setCodexLoginState('idle');
            disconnectBtn.style.display = 'inline-flex';
        } else {
            status.innerHTML = '<p><strong>Not connected.</strong> Agent runs cannot start until the tenant superadmin connects ChatGPT.</p>';
            connectBtn.dataset.idleLabel = 'Connect ChatGPT';
            if (!codexLoginPending) setCodexLoginState('idle');
            disconnectBtn.style.display = 'none';
        }
    } catch (error) {
        status.innerHTML = `<p class="status-error">${escapeHtml(error.message)}</p>`;
    }
}

async function pollCodexLogin(sessionId) {
    const login = await apiRequest(`/api/tenant/integrations/codex/login/${sessionId}`, { method: 'GET' }, 'Checking ChatGPT login');
    const panel = document.getElementById('codex-device-login');
    if (login.verification_url && login.user_code) {
        setCodexLoginState('waiting');
        panel.style.display = 'block';
        const link = document.getElementById('codex-verification-url');
        link.href = login.verification_url;
        document.getElementById('codex-user-code').textContent = login.user_code;
    }
    if (login.status === 'CONNECTED') {
        stopCodexLoginPolling();
        panel.style.display = 'none';
        await loadCodexIntegration();
    } else if (['FAILED', 'EXPIRED', 'CANCELLED'].includes(login.status)) {
        stopCodexLoginPolling();
        throw new Error(login.last_error || `Login ${login.status.toLowerCase()}`);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('connect-codex-btn')?.addEventListener('click', async () => {
        if (codexLoginPending) return;
        setCodexLoginState('generating');
        try {
            const login = await apiRequest('/api/tenant/integrations/codex/login', { method: 'POST' }, 'Starting ChatGPT login');
            clearInterval(codexLoginPoll);
            await pollCodexLogin(login.id);
            if (codexLoginPending) {
                codexLoginPoll = setInterval(() => pollCodexLogin(login.id).catch(error => {
                    stopCodexLoginPolling();
                    customAlert(error.message, 'ChatGPT Login');
                }), 2000);
            }
        } catch (error) {
            stopCodexLoginPolling();
            customAlert(error.message, 'ChatGPT Login');
        }
    });
    document.getElementById('disconnect-codex-btn')?.addEventListener('click', async () => {
        if (!await customConfirm('Disconnect the tenant ChatGPT account?', 'Disconnect ChatGPT')) return;
        await apiRequest('/api/tenant/integrations/codex', { method: 'DELETE' }, 'Disconnecting ChatGPT');
        await loadCodexIntegration();
    });
});

window.loadCodexIntegration = loadCodexIntegration;

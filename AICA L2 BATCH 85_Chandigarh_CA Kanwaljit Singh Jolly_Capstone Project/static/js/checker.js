// Checker Module - queue a Codex validation run and render its report.
//
// Admins submit no paths, workflow text, or model overrides: the tenant's
// stored agent configuration is the only input. The legacy in-browser
// pipeline renderers were removed once TASKCHECKER_VALIDATOR=codex became
// the production path; `legacy` is a server-side rollback switch only.

// Three verdicts are three different outcomes, so each gets its own treatment.
// A crashed run is deliberately NOT one of them: it is rendered neutrally, so a
// system failure never reads as a judgment on the user's work.
const VERDICT_COPY = {
    PASS: {
        label: 'Pass',
        lede: 'The output meets every check derived for this task.'
    },
    FAIL: {
        label: 'Fail',
        lede: 'The output did not meet one or more checks. The findings below say which, and where.'
    },
    INDETERMINATE: {
        label: 'Needs review',
        lede: 'The check could not reach a confident answer on its own. Someone needs to look at the findings below.'
    }
};

function verdictKey(verdict) {
    return VERDICT_COPY[verdict] ? verdict : 'INDETERMINATE';
}

// The dialog is also its own accessible name (modal-a11y points
// aria-labelledby at this heading), so keep it specific to what is on screen.
function setResultsTitle(text) {
    const heading = document.getElementById('results-modal-title');
    if (heading) heading.textContent = text;
}

// A run that never produced a verdict. Neutral on purpose.
function renderRunError(title, message, retryHtml) {
    return `
        <div class="sections-27-container report-document">
            <section class="verdict-block verdict-error">
                <div class="verdict-headline">
                    <p class="verdict-label">${escapeHtml(title)}</p>
                </div>
                <p class="verdict-lede">This is a problem with the check itself, not a judgment on the work.</p>
                ${message ? `<p class="verdict-summary">${escapeHtml(message)}</p>` : ''}
            </section>
            <div class="form-actions report-actions">
                ${retryHtml || ''}
                <button class="btn btn-secondary" onclick="document.getElementById('results-modal').style.display='none'">Close</button>
            </div>
        </div>`;
}

/**
 * Queue a run and follow it to its verdict.
 *
 * The single entry point for starting a check. Runs are started from a task
 * row: the task already names its agent, so nothing here has to resolve one.
 */
window.startCheckRun = async function(agent, task) {
    if (!agent || !task) return;
    const modal = document.getElementById('results-modal');
    const content = document.getElementById('results-content');
    modal.style.display = 'block';
    setResultsTitle(`Checking ${task.name || agent.name}`);
    content.innerHTML = `<div class="loading"><div class="spinner"></div>
        <p>Queueing “${escapeHtml(task.name || agent.name)}”...</p>
        <p class="text-muted">The workspace's configured OneDrive files and ChatGPT account are used automatically.</p></div>`;
    try {
        const queued = await apiRequest(`/api/agents/${agent.id}/run-check`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_id: task.id })
        }, 'Queueing validation', 15000);
        await pollCodexRun(queued.check_run_id, agent, task);
    } catch (error) {
        content.innerHTML = renderRunError(
            'Could not complete this check',
            error.message,
            `<button class="btn btn-primary" onclick="runTask('${escapeHtml(String(task.id))}')">Try again</button>`
        );
    }
};

async function pollCodexRun(runId, agent, task) {
    const content = document.getElementById('results-content');
    const modal = document.getElementById('results-modal');
    const startedAt = Date.now();
    const deadline = startedAt + 60 * 60 * 1000;

    // Repaint the elapsed counter between polls so the wait never looks frozen.
    let lastRun = null;
    let lastEvents = [];
    const ticker = setInterval(() => {
        if (lastRun) RunProgress.render(content, lastRun, lastEvents, startedAt);
    }, 1000);

    try {
        while (Date.now() < deadline) {
            const run = await apiRequest(`/api/check-runs/${runId}`, { method: 'GET' }, 'Checking validation status');

            if (run.run_status === 'COMPLETED') {
                renderCodexResult(run, agent, task);
                loadAgents();
                return;
            }
            if (['ERROR', 'CANCELLED'].includes(run.run_status)) {
                throw new Error(run.error_detail || `Validation ${String(run.run_status).toLowerCase()}`);
            }

            // The event log is supplementary: a failure to read it must not stop
            // the run from being reported.
            let events = lastEvents;
            try {
                events = await apiRequest(`/api/check-runs/${runId}/events`, { method: 'GET' }, 'Reading run activity');
            } catch (_) { /* keep the previous activity list */ }

            lastRun = run;
            lastEvents = Array.isArray(events) ? events : [];
            RunProgress.render(content, lastRun, lastEvents, startedAt);

            await new Promise(resolve => setTimeout(resolve, 2000));
        }
        throw new Error('Validation is still running after one hour. Check the run history later.');
    } finally {
        clearInterval(ticker);
        // A run that finished while the user was away should still land in the
        // agent's history even though nobody is looking at this dialog.
        if (modal && getComputedStyle(modal).display === 'none') loadAgents();
    }
}

window.downloadDisplayedCodexReport = async function() {
    const source = document.querySelector('#results-content .sections-27-container');
    if (!source) {
        customAlert('No completed report is available to download.', 'Download Report');
        return;
    }

    const reportName = source.dataset.reportName || 'Task Check Report';
    const runId = source.dataset.runId || '';
    const safeName = reportName
        .replace(/[<>:"/\\|?*\x00-\x1f]/g, '-')
        .replace(/\s+/g, '-')
        .replace(/-+/g, '-')
        .slice(0, 80) || 'task-check-report';
    const button = source.querySelector('.report-actions .btn-primary');
    const originalLabel = button?.textContent;
    if (button) {
        button.disabled = true;
        button.textContent = 'Preparing PDF...';
    }

    try {
        const token = await getAccessToken();
        const response = await withTimeout(fetch(`${API_URL}/api/check-runs/${runId}/report.pdf`, {
            headers: { 'Authorization': `Bearer ${token}` }
        }), 30000, 'Preparing PDF report');
        if (!response.ok) {
            const payload = await parseJsonResponse(response);
            throw new Error(payload?.error || 'The PDF report could not be generated.');
        }

        const url = URL.createObjectURL(await response.blob());
        const link = document.createElement('a');
        link.href = url;
        link.download = `${safeName}${runId ? '-' + runId.slice(0, 8) : ''}-report.pdf`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        setTimeout(() => URL.revokeObjectURL(url), 0);
    } catch (error) {
        customAlert(error.message, 'Download Report');
    } finally {
        if (button) {
            button.disabled = false;
            button.textContent = originalLabel;
        }
    }
};

window.openPreviousRun = async function(runId, agentId) {
    const modal = document.getElementById('results-modal');
    const content = document.getElementById('results-content');
    const agent = currentAgents.find(item => String(item.id) === String(agentId)) || { name: 'Task Checker Agent' };
    modal.style.display = 'block';
    setResultsTitle('Loading run');
    content.innerHTML = '<div class="loading"><div class="spinner"></div><p>Loading previous run...</p></div>';

    try {
        const run = await apiRequest(`/api/check-runs/${runId}`, { method: 'GET' }, 'Loading previous run');
        if (run.run_status === 'COMPLETED') {
            renderCodexResult(run, agent, null);
            return;
        }
        content.innerHTML = renderRunError(
            'This run has no report',
            run.error_detail || run.result_summary || `The run ended as ${String(run.run_status || 'unknown').toLowerCase()}.`,
            ''
        );
    } catch (error) {
        content.innerHTML = renderRunError('Could not load this run', error.message, '');
    }
};

function userFacingCodexText(value) {
    return String(value ?? '')
        .replace(/(^|[\s("'`:=])(?:\.?[\\/])?tasks?[\\/](?=\s|[.,;:!?"'`)]|$)/gi, '$1task folder')
        .replace(/(^|[\s("'`:=])(?:\.?[\\/])?workflows?[\\/](?=\s|[.,;:!?"'`)]|$)/gi, '$1workflow folder')
        .replace(/(^|[\s("'`:=])(?:\.?[\\/])?(?:tasks?|workflows?)[\\/]/gi, '$1');
}

function renderEvidence(items) {
    if (!items || !items.length) return '';
    return `<ul class="finding-evidence">${items.map(item => `
        <li>
            <span class="evidence-path">${escapeHtml(userFacingCodexText(item.path))}</span>
            <span class="evidence-detail">${escapeHtml(userFacingCodexText(item.detail))}</span>
        </li>`).join('')}</ul>`;
}

function renderFinding(check, openByDefault) {
    const key = verdictKey(String(check.status || 'INDETERMINATE').toUpperCase());
    const evidence = check.evidence || [];
    const count = evidence.length;
    return `
        <details class="finding finding-${key.toLowerCase()}"${openByDefault ? ' open' : ''}>
            <summary>
                <span class="finding-status">${escapeHtml(VERDICT_COPY[key].label)}</span>
                <span class="finding-name">${escapeHtml(userFacingCodexText(check.name || 'Unnamed check'))}</span>
                <span class="finding-meta">${count ? count + (count === 1 ? ' citation' : ' citations') : 'no citations'}</span>
            </summary>
            <div class="finding-body">
                ${check.reason ? `<p class="finding-reason">${escapeHtml(userFacingCodexText(check.reason))}</p>` : ''}
                ${renderEvidence(evidence)}
            </div>
        </details>`;
}

function renderCodexResult(run, agent, task) {
    const result = run.result_json || {};
    const taskName = task?.name || run.config_snapshot?.task_name ||
        currentTasks.find(item => String(item.id) === String(run.task_id))?.name;

    const verdict = verdictKey(
        String(run.final_verdict || run.codex_verdict || result.verdict || 'INDETERMINATE').toUpperCase()
    );
    const copy = VERDICT_COPY[verdict];

    // PASS is final automatically; FAIL and INDETERMINATE are provisional until a
    // superadmin resolves them. That standing belongs on the verdict itself, not
    // in a card further down the page.
    const pending = run.review_status === 'PENDING';
    const standing = pending
        ? '<span class="verdict-standing verdict-standing-provisional">Provisional</span>'
        : '<span class="verdict-standing verdict-standing-final">Final</span>';

    // Counts come straight from the returned checks. The Codex result schema is
    // additionalProperties:false over verdict/summary/checks/warnings, so there
    // is no coverage or confidence data to report — do not imply any.
    const allChecks = result.checks || [];
    const statusOf = check => String(check.status || '').toUpperCase();
    const rank = { FAIL: 0, INDETERMINATE: 1, PASS: 2 };
    const ordered = allChecks.slice().sort(
        (a, b) => (rank[statusOf(a)] ?? 1) - (rank[statusOf(b)] ?? 1)
    );
    const needsAttention = ordered.filter(check => statusOf(check) !== 'PASS');
    const passed = ordered.filter(check => statusOf(check) === 'PASS');

    const attentionHtml = needsAttention.length
        ? needsAttention.map(check => renderFinding(check, true)).join('')
        : '<p class="findings-empty">Every check passed. Nothing needs your attention.</p>';

    // Passing checks show the run was thorough, so they stay reachable — but
    // collapsed, because they are not the admin's work list.
    const passedHtml = passed.length ? `
        <details class="findings-passed">
            <summary>${passed.length} check${passed.length === 1 ? '' : 's'} passed</summary>
            <div class="findings-passed-body">${passed.map(check => renderFinding(check, false)).join('')}</div>
        </details>` : '';

    const resolveActions = (pending && currentUserRole === 'super_admin') ? `
        <div class="verdict-resolve">
            <p>Resolving records your decision on this run permanently.</p>
            <div class="verdict-resolve-actions">
                <button class="btn btn-primary" onclick="resolveCodexRun('${escapeHtml(String(run.id))}', 'PASS')">Resolve as Pass</button>
                <button class="btn btn-danger" onclick="resolveCodexRun('${escapeHtml(String(run.id))}', 'FAIL')">Resolve as Fail</button>
            </div>
        </div>` : '';

    const pendingNote = (pending && currentUserRole !== 'super_admin')
        ? '<p class="verdict-note">This result is queued for your workspace superadmin to confirm.</p>'
        : '';

    const warnings = (result.warnings || []).length ? `
        <section class="report-section">
            <h4>Warnings</h4>
            <ul class="warning-list">${result.warnings.map(item => `<li>${escapeHtml(userFacingCodexText(item))}</li>`).join('')}</ul>
        </section>` : '';

    const summaryText = userFacingCodexText(result.summary || run.result_summary || '');
    const reportName = `${agent.name || 'Task Check'}${taskName ? ' - ' + taskName : ''}`;
    setResultsTitle(`${copy.label} · ${agent.name || 'Check result'}`);

    document.getElementById('results-content').innerHTML = `
        <div class="sections-27-container report-document"
             data-run-id="${escapeHtml(String(run.id || ''))}"
             data-report-name="${escapeHtml(reportName)}">
            <section class="verdict-block verdict-${verdict.toLowerCase()}">
                <div class="verdict-headline">
                    <p class="verdict-label">${escapeHtml(copy.label)}</p>
                    ${standing}
                </div>
                <p class="verdict-lede">${escapeHtml(copy.lede)}</p>
                ${summaryText ? `<p class="verdict-summary">${escapeHtml(summaryText)}</p>` : ''}
                ${pendingNote}
                ${resolveActions}
            </section>

            <p class="report-provenance">${escapeHtml(agent.name || '')}${taskName ? ' · ' + escapeHtml(taskName) : ''}${
                // Model and effort are configuration, so they are shown to the
                // person who chose them and nobody else.
                currentUserRole === 'super_admin' && run.codex_model
                    ? ` · <span class="report-config">${escapeHtml(run.codex_model)} · ${escapeHtml(run.codex_reasoning_effort || '')} reasoning</span>`
                    : ''
            }</p>

            <section class="report-section">
                <div class="findings-head">
                    <h4>${needsAttention.length ? 'What needs attention' : 'Checks'}</h4>
                    <div class="findings-tally">
                        <span class="badge badge-fail">${allChecks.filter(c => statusOf(c) === 'FAIL').length} failed</span>
                        <span class="badge badge-indeterminate">${allChecks.filter(c => statusOf(c) === 'INDETERMINATE').length} needs review</span>
                        <span class="badge badge-pass">${passed.length} passed</span>
                    </div>
                </div>
                <div class="findings-list">${attentionHtml}</div>
                ${passedHtml}
            </section>

            ${warnings}

            <div class="form-actions report-actions">
                <button class="btn btn-primary" onclick="downloadDisplayedCodexReport()">Download Report</button>
                <button class="btn btn-secondary" onclick="document.getElementById('results-modal').style.display='none'">Close</button>
            </div>
        </div>`;
}

window.resolveCodexRun = async function(runId, verdict) {
    const reasoning = window.prompt(`Why should this run be finalized as ${verdict}?`);
    if (!reasoning) return;
    await apiRequest(`/api/check-runs/${runId}/resolve`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ verdict, reasoning })
    }, 'Resolving validation');
    document.getElementById('results-modal').style.display = 'none';
    loadAgents();
};

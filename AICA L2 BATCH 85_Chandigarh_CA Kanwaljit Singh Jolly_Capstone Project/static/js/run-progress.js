/**
 * Run progress: the wait, rendered from what the backend actually reports.
 *
 * A check takes minutes to an hour. Previously that was a rotating ring and a
 * raw UUID. The backend already publishes a per-run event log and a set of run
 * statuses; this turns them into a stage rail with real timestamps.
 *
 * The lifecycle is written in two places, so the stage is derived from
 * run_status AND the event stream rather than either alone:
 *   - PREPARING is set by claim_next_check_run_task() in SQL at claim time;
 *     worker.py separately emits a `preparing` event but never sets the status.
 *     Either can arrive first, so both are treated as evidence of the stage.
 *   - FINALIZING is only ever a status. No event is emitted for it.
 */
(function () {
    'use strict';

    /**
     * What the queue note says while waiting. Scoped to the workspace on
     * purpose: the claim function is globally FIFO and skips busy tenants, so
     * runs from other workspaces also sit ahead of this one and we cannot see
     * them. No wait estimate is shown, because nothing here can support one.
     */
    function queueNote(run) {
        if (!run || run.run_status !== 'QUEUED') return '';
        var ahead = run.queue_ahead;

        if (run.workspace_busy) {
            return ahead
                ? 'Another check is using this workspace now, and ' + ahead +
                  (ahead === 1 ? ' run is' : ' runs are') + ' ahead of this one.'
                : 'Another check is using this workspace now. This run starts when it finishes.';
        }
        if (ahead === 0) return 'Next in this workspace. Waiting for a free worker.';
        if (ahead > 0) {
            return ahead + (ahead === 1 ? ' run is' : ' runs are') + ' ahead of this one in this workspace.';
        }
        return '';
    }

    var STAGES = [
        { key: 'QUEUED', label: 'Queued', note: 'Waiting for the tenant worker' },
        { key: 'PREPARING', label: 'Preparing', note: 'Downloading the configured files' },
        { key: 'RUNNING', label: 'Running', note: 'Codex is validating the task' },
        { key: 'FINALIZING', label: 'Finalizing', note: 'Recording the verdict and evidence' }
    ];

    // Events that say something about which stage the run is in. `retry_scheduled`
    // counts: a transient failure puts the run back to QUEUED to be re-claimed.
    var STAGE_EVENTS = { queued: 0, retry_scheduled: 0, preparing: 1, running: 2 };

    function stageIndex(run, events) {
        var status = String((run && run.run_status) || 'QUEUED').toUpperCase();
        if (status === 'FINALIZING') return 3;
        if (status === 'RUNNING') return 2;
        // claim_next_check_run_task() sets PREPARING at claim time, before
        // worker.py emits its own `preparing` event, so the status is
        // authoritative here and must be checked before the event fallback.
        if (status === 'PREPARING') return 1;

        // The worker emits `preparing` before it flips the status to RUNNING, so
        // while the status still reads QUEUED the event log is the only signal
        // that work has started. Read the LATEST stage event, not any of them:
        // a retried run carries a stale `preparing` from its first attempt and
        // would otherwise report progress it has given up.
        var latest = 0;
        (events || []).forEach(function (event) {
            var mapped = STAGE_EVENTS[String(event.event_type || '').toLowerCase()];
            if (mapped !== undefined) latest = mapped;
        });
        return status === 'QUEUED' ? Math.min(latest, 1) : 0;
    }

    function formatElapsed(ms) {
        if (!isFinite(ms) || ms < 0) return '';
        var total = Math.floor(ms / 1000);
        var h = Math.floor(total / 3600);
        var m = Math.floor((total % 3600) / 60);
        var s = total % 60;
        if (h) return h + 'h ' + m + 'm';
        if (m) return m + 'm ' + String(s).padStart(2, '0') + 's';
        return s + 's';
    }

    function escape(text) {
        return (typeof escapeHtml === 'function')
            ? escapeHtml(text)
            : String(text == null ? '' : text);
    }

    /**
     * Cancel only where it actually does something. worker.py checks
     * `cancel_requested` once, before execution begins, so cancelling a run that
     * Codex has already started does not stop it. Offering the button anyway
     * would be a lie, so past that point we say what is true instead.
     */
    function renderCancel(runId, index) {
        if (index === 0) {
            return '<button class="btn btn-secondary btn-small" data-cancel-run="' + escape(runId) + '">Cancel run</button>';
        }
        return '<p class="progress-cancel-note">This run has started and can no longer be cancelled.</p>';
    }

    function render(container, run, events, startedAtMs) {
        var index = stageIndex(run, events);
        var runId = (run && run.id) || '';
        var elapsed = formatElapsed(Date.now() - startedAtMs);

        var queued = queueNote(run);

        var rail = STAGES.map(function (stage, i) {
            var state = i < index ? 'done' : (i === index ? 'current' : 'todo');
            // While queued, the live standing is more useful than the generic note.
            var note = (i === 0 && i === index && queued) ? queued : stage.note;
            return '' +
                '<li class="progress-step progress-step-' + state + '">' +
                    '<span class="progress-marker" aria-hidden="true"></span>' +
                    '<span class="progress-step-body">' +
                        '<span class="progress-step-label">' + escape(stage.label) +
                            (i === 0 && i === index && run && run.queue_position
                                ? ' <span class="queue-position">#' + escape(run.queue_position) + ' in workspace</span>'
                                : '') +
                        '</span>' +
                        '<span class="progress-step-note">' + escape(note) + '</span>' +
                    '</span>' +
                '</li>';
        }).join('');

        container.innerHTML = '' +
            '<div class="run-progress">' +
                '<div class="run-progress-head">' +
                    '<h3>' + escape(STAGES[index].label) + '</h3>' +
                    '<span class="run-elapsed" role="timer">' + escape(elapsed) + ' elapsed</span>' +
                '</div>' +
                '<ol class="progress-rail" aria-label="Run progress">' + rail + '</ol>' +
                '<p class="progress-safe-to-leave">You can close this window. The result will be waiting in this agent’s run history.</p>' +
                '<div class="progress-actions">' + renderCancel(runId, index) + '</div>' +
            '</div>';
    }

    window.RunProgress = { render: render, stageIndex: stageIndex, formatElapsed: formatElapsed, STAGES: STAGES };

    // One delegated handler rather than a listener per repaint: the progress
    // view re-renders on every poll tick.
    document.addEventListener('click', async function (event) {
        var button = event.target.closest('[data-cancel-run]');
        if (!button) return;
        var runId = button.getAttribute('data-cancel-run');
        if (!runId) return;

        var confirmed = await customConfirm(
            'Cancel this run? It will not produce a report.', 'Cancel run'
        );
        if (!confirmed) return;

        button.disabled = true;
        button.textContent = 'Cancelling...';
        try {
            await apiRequest('/api/check-runs/' + runId + '/cancel', { method: 'POST' }, 'Cancelling run');
        } catch (error) {
            button.disabled = false;
            button.textContent = 'Cancel run';
            await customAlert(error.message || 'Could not cancel this run.', 'Cancel run');
        }
    });
})();

// Tasks bind OneDrive inputs and workflows to an existing agent.

let taskListenersInitialized = false;
let editingTaskId = null;
let taskClientSelector = null;
let taskInputOutputSelector = null;
let taskWorkflowSelector = null;

function showWorkspacePage(page) {
    const showTasks = page === 'tasks';
    document.getElementById('agents-page').style.display = showTasks ? 'none' : 'block';
    document.getElementById('tasks-page').style.display = showTasks ? 'block' : 'none';
    document.getElementById('nav-agents-btn').classList.toggle('active', !showTasks);
    document.getElementById('nav-tasks-btn').classList.toggle('active', showTasks);
}

function initializeTaskSelectors() {
    if (!taskClientSelector) {
        taskClientSelector = new FileSelector('task-client-files-selector', {
            label: 'Client Folder Files',
            fileTypes: ['.pdf', '.docx', '.txt', '.md', '.xlsx', '.csv', '.xls']
        });
    }
    if (!taskInputOutputSelector) {
        taskInputOutputSelector = new FileSelector('task-input-output-selector', {
            label: 'Input/Output Files',
            fileTypes: ['.txt', '.md', '.csv', '.xlsx', '.xls', '.pdf', '.docx']
        });
    }
    if (!taskWorkflowSelector) {
        taskWorkflowSelector = new FileSelector('task-workflow-selector', {
            label: 'Workflow Files',
            fileTypes: ['.txt', '.md', '.csv', '.xlsx', '.xls', '.pdf', '.docx']
        });
    }
}

function populateTaskAgentOptions(selectedAgentId = '') {
    const select = document.getElementById('task-agent-id');
    select.innerHTML = '<option value="">Select an agent...</option>' + currentAgents.map(agent =>
        `<option value="${escapeHtml(String(agent.id))}" ${String(agent.id) === String(selectedAgentId) ? 'selected' : ''}>${escapeHtml(agent.name)}</option>`
    ).join('');
}

async function openTaskModal(task = null) {
    editingTaskId = task?.id || null;
    document.getElementById('task-id').value = editingTaskId || '';
    document.getElementById('task-modal-title').textContent = task ? 'Edit Task' : 'Create Task';
    document.getElementById('task-name').value = task?.name || '';
    document.getElementById('task-modal').style.display = 'block';
    populateTaskAgentOptions(task?.agent_id || '');

    initializeTaskSelectors();
    taskClientSelector.reset();
    taskInputOutputSelector.reset();
    taskWorkflowSelector.reset();
    if (task) {
        await Promise.all([
            taskClientSelector.preselectFolderAndFiles(task.client_folder_path || '', task.client_file_paths || []),
            taskInputOutputSelector.preselectFolderAndFiles(task.onedrive_folder_path || '', task.task_file_paths || []),
            taskWorkflowSelector.preselectFolderAndFiles(
                inferFolderFromSelections(task.workflow_file_paths || []),
                task.workflow_file_paths || []
            )
        ]);
    }
}

function taskCountLabel(task) {
    const inputs = (task.task_file_paths || []).length;
    const workflows = (task.workflow_file_paths || []).length;
    const client = (task.client_file_paths || []).length;
    return `${inputs} input/output · ${workflows} workflow · ${client} client`;
}

function taskLastRun(taskId) {
    const runs = (typeof recentRunsByTask !== 'undefined' && recentRunsByTask)
        ? recentRunsByTask.get(String(taskId)) || []
        : [];
    return runs[0] || null;
}

function runStatusOf(run) {
    return String(run.final_verdict || run.codex_verdict || run.run_status || run.status || 'UNKNOWN').toUpperCase();
}

// The row uses the same words as the report. INDETERMINATE is a machine token
// and, spelled out, the widest chip in the column.
const RUN_STATUS_LABEL = {
    PASS: 'Pass',
    FAIL: 'Fail',
    INDETERMINATE: 'Needs review',
    QUEUED: 'Queued',
    PREPARING: 'Running',
    RUNNING: 'Running',
    FINALIZING: 'Running',
    CANCELLED: 'Cancelled',
    ERROR: 'Error'
};

function runStatusLabel(status) {
    return RUN_STATUS_LABEL[status] || 'Unknown';
}

function relativeTime(value) {
    const date = value ? new Date(value) : null;
    if (!date || Number.isNaN(date.getTime())) return '';
    const mins = Math.round((Date.now() - date.getTime()) / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return mins + 'm ago';
    const hours = Math.round(mins / 60);
    if (hours < 24) return hours + 'h ago';
    const days = Math.round(hours / 24);
    if (days < 7) return days + 'd ago';
    return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
}

/**
 * Tasks are the run surface. Every task is one row, and Run sits at the end of
 * that row, so the work happens where the work is defined rather than on a
 * separate agents page. Both tenant roles can run and manage their tasks.
 */
function renderTasks() {
    const list = document.getElementById('tasks-list');
    const empty = document.getElementById('tasks-empty-state');
    if (!list || !empty) return;

    if (!currentTasks.length) {
        list.innerHTML = '';
        empty.style.display = 'block';
        const heading = empty.querySelector('h3');
        const body = empty.querySelector('p');
        const firstButton = document.getElementById('create-first-task-btn');
        if (heading) heading.textContent = 'No tasks yet';
        if (body) {
            body.textContent = currentAgents.length
                ? 'Create a task to bind files and a workflow to one of your agents. You run checks from here.'
                : 'Create an agent first, then add a task to it. You run checks from this page.';
        }
        if (firstButton) firstButton.style.display = currentAgents.length ? 'inline-flex' : 'none';
        return;
    }

    empty.style.display = 'none';

    const rows = currentTasks.map(task => {
        const agent = currentAgents.find(item => String(item.id) === String(task.agent_id));
        const last = taskLastRun(task.id);
        const status = last ? runStatusOf(last) : null;
        const statusClass = status === 'PASS' ? 'status-pass'
            : status === 'FAIL' ? 'status-fail'
            : status ? 'status-error' : '';

        const lastCell = last
            ? `<button type="button" class="task-last-run" onclick="openPreviousRun('${escapeHtml(String(last.id))}', '${escapeHtml(String(task.agent_id))}')">
                   <span class="task-status ${statusClass}">${escapeHtml(runStatusLabel(status))}</span>
                   <span class="task-last-time">${escapeHtml(relativeTime(last.completed_at || last.created_at || last.queued_at))}</span>
               </button>`
            : '<span class="task-last-none">Not run yet</span>';

        const runnable = Boolean(agent);
        return `<tr class="task-row" data-task-id="${escapeHtml(String(task.id))}">
            <td class="task-cell-name">
                <span class="task-name">${escapeHtml(task.name || 'Untitled task')}</span>
                <span class="task-meta">${escapeHtml(taskCountLabel(task))}</span>
            </td>
            <td class="task-cell-agent">${escapeHtml(agent?.name || 'Agent unavailable')}</td>
            <td class="task-cell-last">${lastCell}</td>
            <td class="task-cell-actions">
                <button class="btn btn-primary btn-small" type="button" ${runnable ? '' : 'disabled'}
                        onclick="runTask('${escapeHtml(String(task.id))}')">Run</button>
                <button class="btn btn-secondary btn-small" type="button" onclick="editTask('${escapeHtml(String(task.id))}')">Edit</button>
                <button class="btn btn-quiet btn-small" type="button" onclick="deleteTask('${escapeHtml(String(task.id))}')" aria-label="Delete ${escapeHtml(task.name || 'task')}">Delete</button>
            </td>
        </tr>`;
    }).join('');

    list.innerHTML = `<table class="task-table">
        <thead><tr>
            <th scope="col">Task</th>
            <th scope="col">Agent</th>
            <th scope="col">Last run</th>
            <th scope="col"><span class="visually-hidden">Actions</span></th>
        </tr></thead>
        <tbody>${rows}</tbody>
    </table>`;
}

/**
 * Run a task. Resolves the agent from the task itself, so the caller no longer
 * has to pick an agent first; the endpoint and polling are unchanged.
 */
window.runTask = async function(taskId) {
    const task = currentTasks.find(item => String(item.id) === String(taskId));
    if (!task) return;
    const agent = currentAgents.find(item => String(item.id) === String(task.agent_id));
    if (!agent) {
        await customAlert('This task points at an agent you cannot access. Ask your workspace superadmin.', 'Cannot Run');
        return;
    }
    await startCheckRun(agent, task);
};

window.editTask = function(taskId) {
    const task = currentTasks.find(item => String(item.id) === String(taskId));
    if (task) openTaskModal(task).catch(error => customAlert(error.message, 'Could Not Open Task'));
};

window.deleteTask = async function(taskId) {
    const task = currentTasks.find(item => String(item.id) === String(taskId));
    if (!task || !await customConfirm(`Delete “${task.name}”? Existing run reports will remain available.`, 'Delete Task')) return;
    try {
        await apiRequest(`/api/tasks/${taskId}`, { method: 'DELETE' }, 'Deleting task');
        await loadAgents();
    } catch (error) {
        await customAlert(error.message, 'Could Not Delete Task');
    }
};

function initTaskListeners() {
    if (taskListenersInitialized) return;
    document.getElementById('nav-agents-btn')?.addEventListener('click', () => showWorkspacePage('agents'));
    document.getElementById('nav-tasks-btn')?.addEventListener('click', () => showWorkspacePage('tasks'));
    document.getElementById('create-task-btn')?.addEventListener('click', () => openTaskModal());
    document.getElementById('create-first-task-btn')?.addEventListener('click', () => openTaskModal());
    document.getElementById('cancel-task-btn')?.addEventListener('click', () => {
        document.getElementById('task-modal').style.display = 'none';
    });

    document.getElementById('task-form')?.addEventListener('submit', async event => {
        event.preventDefault();
        const saveButton = document.getElementById('save-task-btn');
        const buttonText = saveButton.querySelector('.btn-text');
        const loadingText = saveButton.querySelector('.btn-loading');
        try {
            initializeTaskSelectors();
            const taskFiles = taskInputOutputSelector.getSelectedFiles();
            const workflowFiles = taskWorkflowSelector.getSelectedFiles();
            let taskFolder = taskInputOutputSelector.currentFolder || inferFolderFromSelections(taskFiles);
            if (!taskFolder && editingTaskId) {
                taskFolder = currentTasks.find(item => item.id === editingTaskId)?.onedrive_folder_path || '';
            }
            const payload = {
                name: document.getElementById('task-name').value.trim(),
                agent_id: document.getElementById('task-agent-id').value,
                client_folder_path: taskClientSelector.currentFolder || '',
                client_file_paths: taskClientSelector.getSelectedFiles(),
                onedrive_folder_path: taskFolder,
                task_file_paths: taskFiles,
                workflow_file_paths: workflowFiles
            };
            if (!payload.name) throw new Error('Enter a task name');
            if (!payload.agent_id) throw new Error('Select an agent');
            if (!payload.task_file_paths.length) throw new Error('Select an input/output folder or at least one input/output file');
            if (!payload.workflow_file_paths.length) throw new Error('Select a Workflow folder or at least one workflow file');

            saveButton.disabled = true;
            buttonText.style.display = 'none';
            loadingText.style.display = 'inline';
            await apiRequest(editingTaskId ? `/api/tasks/${editingTaskId}` : '/api/tasks', {
                method: editingTaskId ? 'PUT' : 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            }, editingTaskId ? 'Updating task' : 'Creating task');
            document.getElementById('task-modal').style.display = 'none';
            await loadAgents();
            showWorkspacePage('tasks');
        } catch (error) {
            await customAlert(error.message, 'Could Not Save Task');
        } finally {
            saveButton.disabled = false;
            buttonText.style.display = 'inline';
            loadingText.style.display = 'none';
        }
    });
    taskListenersInitialized = true;
}

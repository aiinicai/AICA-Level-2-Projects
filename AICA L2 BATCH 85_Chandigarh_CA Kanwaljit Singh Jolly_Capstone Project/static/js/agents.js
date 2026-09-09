// Agents Management Module

const REQUEST_TIMEOUT_MS = 10000;

function withTimeout(promise, timeoutMs, label) {
    let timeoutId;
    const timeoutPromise = new Promise((_, reject) => {
        timeoutId = setTimeout(() => {
            reject(new Error(`${label} timed out after ${Math.ceil(timeoutMs / 1000)}s`));
        }, timeoutMs);
    });

    return Promise.race([promise, timeoutPromise]).finally(() => {
        clearTimeout(timeoutId);
    });
}

async function getAccessToken() {
    const { data: { session }, error } = await supabaseClient.auth.getSession();
    if (error) throw error;
    if (!session) {
        throw new Error('Not authenticated. Please log in again.');
    }
    return session.access_token;
}

async function parseJsonResponse(response) {
    const text = await response.text();
    if (!text) return null;
    try {
        return JSON.parse(text);
    } catch {
        return { raw: text };
    }
}

async function apiRequest(path, options, label, timeoutMs = REQUEST_TIMEOUT_MS) {
    const token = await getAccessToken();
    const headers = Object.assign(
        { 'Authorization': `Bearer ${token}` },
        options?.headers || {}
    );

    const response = await withTimeout(
        fetch(`${API_URL}${path}`, { ...options, headers }),
        timeoutMs,
        label
    );

    const payload = await parseJsonResponse(response);
    if (!response.ok) {
        const message = payload?.error || payload?.message || response.statusText || 'Request failed';
        throw new Error(message);
    }

    return payload;
}

function normalizePathList(value) {
    if (!value) return [];
    const parts = value.replace(/,/g, '\n').split('\n');
    const cleaned = [];
    parts.forEach((part) => {
        if (!part) return;
        let path = String(part).trim();
        if (!path) return;
        if (!path.startsWith('/')) {
            path = '/' + path;
        }
        cleaned.push(path);
    });
    const seen = new Set();
    return cleaned.filter((path) => {
        if (seen.has(path)) return false;
        seen.add(path);
        return true;
    });
}

function inferFolderFromSelections(selectedPaths) {
    if (!Array.isArray(selectedPaths) || selectedPaths.length === 0) return '';

    const folders = selectedPaths.map((rawPath) => {
        if (!rawPath) return '';
        let path = String(rawPath).trim();
        if (!path) return '';
        path = path.replace(/\/+$/, '');
        const lastSlash = path.lastIndexOf('/');
        if (lastSlash <= 0) return path;
        return path.slice(0, lastSlash);
    }).filter(Boolean);

    if (folders.length === 0) return '';

    const parts = folders.map(folder => folder.split('/').filter(Boolean));
    const minLen = Math.min(...parts.map(p => p.length));
    const common = [];

    for (let i = 0; i < minLen; i++) {
        const segment = parts[0][i];
        if (parts.every(p => p[i] === segment)) {
            common.push(segment);
        } else {
            break;
        }
    }

    return common.length ? '/' + common.join('/') : '';
}

console.log('📦 [LOAD] agents.js file loaded successfully!');

// Flag to prevent duplicate initialization
let listenersInitialized = false;

// FileSelector instances (global to persist across modal open/close)
let exampleInputSelector = null;
let exampleOutputSelector = null;
let kbFilesSelector = null;
let recentRunsByAgent = new Map();
let recentRunsByTask = new Map();

async function loadAssignableAdmins(selectedIds = []) {
    const container = document.getElementById('agent-admin-assignments');
    if (!container) return;
    try {
        const users = await apiRequest('/api/users', { method: 'GET' }, 'Loading tenant admins');
        const selected = new Set(selectedIds.map(String));
        const admins = (users || []).filter(user => user.role === 'admin' && user.status !== 'disabled');
        container.innerHTML = admins.length ? admins.map(user => `
            <label class="user-item" style="cursor: pointer;">
                <input type="checkbox" class="agent-admin-checkbox" value="${escapeHtml(String(user.id))}" ${selected.has(String(user.id)) ? 'checked' : ''}>
                <span>${escapeHtml(user.display_name || user.email || user.id)}</span>
            </label>`).join('') : '<p class="text-muted">Create an admin before assigning this agent.</p>';
    } catch (error) {
        container.innerHTML = `<p class="status-error">${escapeHtml(error.message)}</p>`;
    }
}

/**
 * Initialize all FileSelector components for the agent modal
 */
function initializeFileSelectors() {
    console.log('📁 [FILE-SELECTOR] Initializing FileSelector components...');

    try {
        // Example Input Files
        exampleInputSelector = new FileSelector('example-input-selector', {
            label: 'Example Input Files',
            fileTypes: ['.txt', '.md', '.csv', '.xlsx', '.xls', '.pdf', '.docx']
        });
        console.log('✅ [FILE-SELECTOR] Example Input selector initialized');

        // Example Output Files
        exampleOutputSelector = new FileSelector('example-output-selector', {
            label: 'Example Output Files',
            fileTypes: ['.txt', '.md', '.csv', '.xlsx', '.xls', '.pdf', '.docx']
        });

        console.log('✅ [FILE-SELECTOR] Example Output selector initialized');

        // Task Folder Files
        console.log('✅ [FILE-SELECTOR] Task Folder selector initialized');

        // Knowledge Base Files
        kbFilesSelector = new FileSelector('kb-files-selector', {
            label: 'Knowledge Base Files',
            fileTypes: ['.pdf', '.docx', '.txt', '.md', '.xlsx', '.csv', '.xls']
        });
        console.log('✅ [FILE-SELECTOR] KB Files selector initialized');

        // Client Folder Files
        console.log('✅ [FILE-SELECTOR] Client Files selector initialized');

        console.log('✅ [FILE-SELECTOR] All FileSelectors initialized successfully!');
    } catch (error) {
        console.error('❌ [FILE-SELECTOR] Error initializing FileSelectors:', error);
    }
}

/**
 * Reset all FileSelector components
 */
function resetFileSelectors() {
    console.log('🔄 [FILE-SELECTOR] Resetting all FileSelectors...');

    if (exampleInputSelector) exampleInputSelector.reset();
    if (exampleOutputSelector) exampleOutputSelector.reset();
    if (kbFilesSelector) kbFilesSelector.reset();

    console.log('✅ [FILE-SELECTOR] All FileSelectors reset');
}

// Load OneDrive Folders (Root level only for speed)
async function loadOneDriveFolders() {
    const folderSelect = document.getElementById('agent-folder-select');
    const clientFolderSelect = document.getElementById('agent-client-folder-select');
    const loadingDiv = document.getElementById('folder-loading');
    const refreshBtn = document.getElementById('refresh-folders-btn');
    const refreshClientBtn = document.getElementById('refresh-agent-client-folders-btn');

    if (!folderSelect && !clientFolderSelect) return;

    const setOptions = (select, items) => {
        if (!select) return;
        select.innerHTML = '';
        items.forEach((item) => {
            const option = document.createElement('option');
            option.value = item.value;
            option.textContent = item.text;
            if (item.disabled) option.disabled = true;
            select.appendChild(option);
        });
    };

    try {
        console.log('Loading OneDrive root folders...');

        if (loadingDiv) loadingDiv.style.display = 'flex';
        if (refreshBtn) refreshBtn.disabled = true;
        if (refreshClientBtn) refreshClientBtn.disabled = true;

        setOptions(folderSelect, [{ value: '', text: '-- Loading folders... --' }]);
        setOptions(clientFolderSelect, [{ value: '', text: '-- Loading folders... --' }]);

        const result = await apiRequest('/api/onedrive/folders?depth=1', {}, 'Loading OneDrive folders', 15000);
        const folders = result.folders || [];

        if (folders.length > 0) {
            const commonFolders = [
                '/Documents',
                '/Documents/TaskChecker',
                '/Documents/TaskChecker/TestPass',
                '/Documents/TaskChecker/TestFail'
            ];

            const items = [{ value: '', text: '-- Select a folder --' }];
            commonFolders.forEach((path) => {
                items.push({ value: path, text: path });
            });
            items.push({ value: '', text: '--------------', disabled: true });
            folders.forEach((folder) => {
                items.push({ value: folder.path, text: folder.path });
            });

            setOptions(folderSelect, items);
            setOptions(clientFolderSelect, items);
        } else {
            const items = [{ value: '', text: '-- Select a folder --' }];
            ['/Documents/TaskChecker/TestPass', '/Documents/TaskChecker/TestFail'].forEach((path) => {
                items.push({ value: path, text: path });
            });
            setOptions(folderSelect, items);
            setOptions(clientFolderSelect, items);
        }
    } catch (error) {
        console.error('Error loading folders:', error);
        const items = [{ value: '', text: '-- Select or type path below --' }];
        ['/Documents/TaskChecker/TestPass', '/Documents/TaskChecker/TestFail'].forEach((path) => {
            items.push({ value: path, text: path });
        });
        setOptions(folderSelect, items);
        setOptions(clientFolderSelect, items);
    } finally {
        if (loadingDiv) loadingDiv.style.display = 'none';
        if (refreshBtn) refreshBtn.disabled = false;
        if (refreshClientBtn) refreshClientBtn.disabled = false;
    }
}

function initAgentListeners() {
    if (listenersInitialized) {
        console.log('⚠️ [INIT] Listeners already initialized, skipping duplicate initialization');
        return;
    }

    console.log('🔧 [INIT] Starting initAgentListeners...');
    console.log('🔧 [INIT] Current user:', currentUser ? currentUser.id : 'NO USER');
    console.log('🔧 [INIT] Supabase client:', typeof supabaseClient);

    // Create Agent Button
    const createBtn = document.getElementById('create-agent-btn');
    console.log('🔧 [INIT] Create button found:', createBtn !== null);

    if (createBtn) {
        console.log('🔧 [INIT] Attaching click listener to create button...');
        createBtn.addEventListener('click', () => {
            console.log('🎯 [CLICK] Create Agent button clicked!');
            try {
                editingAgentId = null;
                console.log('🎯 [CLICK] Set editingAgentId to null');

                document.getElementById('modal-title').textContent = 'Create Task Checker Agent';
                console.log('🎯 [CLICK] Set modal title');

                document.getElementById('agent-id').value = '';
                console.log('🎯 [CLICK] Cleared agent-id');

                document.getElementById('agent-name').value = '';
                console.log('🎯 [CLICK] Cleared agent-name');

                document.getElementById('agent-description').value = '';
                console.log('🎯 [CLICK] Cleared agent-description');

                document.getElementById('agent-prompt').value = '';
                document.getElementById('agent-codex-model').value = 'gpt-5.6-sol';
                document.getElementById('agent-codex-effort').value = 'xhigh';
                loadAssignableAdmins([]);
                console.log('🎯 [CLICK] Cleared agent-prompt');

                // Clear reference files UI
                clearReferenceFilesUI();
                console.log('🎯 [CLICK] Cleared reference files');

                // Reset FileSelectors
                resetFileSelectors();
                console.log('🎯 [CLICK] Reset FileSelectors');

                document.getElementById('agent-modal').style.display = 'block';
                console.log('🎯 [CLICK] Modal should now be visible!');

                // Initialize FileSelectors (must be done after modal is visible)
                setTimeout(() => {
                    initializeFileSelectors();
                }, 100);
            } catch (error) {
                console.error('❌ [CLICK] Error in create button handler:', error);
            }
        });
        console.log('✅ [INIT] Create button listener attached successfully');
    } else {
        console.error('❌ [INIT] Create button NOT FOUND in DOM!');
    }

    // Save Agent Form
    const agentForm = document.getElementById('agent-form');
    console.log('🔧 [INIT] Agent form found:', agentForm !== null);

    if (agentForm) {
        console.log('🔧 [INIT] Attaching submit listener to form...');
        agentForm.addEventListener('submit', async (e) => {
            console.log('📝 [SUBMIT] Form submitted!');
            e.preventDefault();
            console.log('📝 [SUBMIT] Default prevented');

            const saveBtn = document.getElementById('save-agent-btn');
            const btnText = saveBtn?.querySelector('.btn-text');
            const btnLoading = saveBtn?.querySelector('.btn-loading');

            try {
                if (!saveBtn || !btnText || !btnLoading) {
                    throw new Error('Save button UI is missing. Please refresh the page.');
                }
                console.log('📝 [SUBMIT] Disabling save button...');
                // Disable button and show loading
                saveBtn.disabled = true;
                btnText.style.display = 'none';
                btnLoading.style.display = 'inline';

                console.log('📝 [SUBMIT] Collecting form data...');

                if (!currentUser?.id) {
                    throw new Error('No active user. Please log in again.');
                }

                // Collect selected file paths from FileSelectors
                const selectedKBFiles = kbFilesSelector ? kbFilesSelector.getSelectedFiles() : [];
                const selectedExampleInputs = exampleInputSelector ? exampleInputSelector.getSelectedFiles() : [];
                const selectedExampleOutputs = exampleOutputSelector ? exampleOutputSelector.getSelectedFiles() : [];

                const agentData = {
                    name: document.getElementById('agent-name').value.trim(),
                    description: document.getElementById('agent-description').value.trim() || null,
                    system_prompt: document.getElementById('agent-prompt').value.trim(),
                    workflow_text: document.getElementById('agent-prompt').value.trim(),
                    codex_model: document.getElementById('agent-codex-model').value,
                    codex_reasoning_effort: document.getElementById('agent-codex-effort').value,
                    assigned_admin_ids: Array.from(document.querySelectorAll('.agent-admin-checkbox:checked')).map(input => input.value),
                    kb_folder_paths: selectedKBFiles,
                    kb_file_paths: selectedKBFiles, // Store selected KB files
                    reference_file_paths: {
                        example_inputs: selectedExampleInputs,
                        example_outputs: selectedExampleOutputs
                    }
                };

                console.log('📁 [FILE-SELECTOR] Collected selected files:');
                console.log('  - KB Files:', selectedKBFiles.length);
                console.log('  - Example Inputs:', selectedExampleInputs.length);
                console.log('  - Example Outputs:', selectedExampleOutputs.length);

                console.log('💾 [SUBMIT] Agent data collected:');
                console.log('  - Name:', agentData.name, '(length:', agentData.name.length, ')');
                console.log('  - Description:', agentData.description ? agentData.description.substring(0, 50) + '...' : 'null', '(length:', agentData.description?.length || 0, ')');
                console.log('  - System Prompt:', agentData.system_prompt ? agentData.system_prompt.substring(0, 100) + '...' : '(none)', '(length:', agentData.system_prompt.length, ')');

                // Validate required fields
                if (!agentData.name) {
                    throw new Error('Agent name is required');
                }
                console.log('✅ [SUBMIT] All required fields validated');

                let savedAgentId = editingAgentId;

                if (editingAgentId) {
                    // Update existing agent
                    console.log('📝 [SUBMIT] Updating existing agent:', editingAgentId);
                    await apiRequest(
                        `/api/agents/${editingAgentId}`,
                        {
                            method: 'PUT',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(agentData)
                        },
                        'Updating agent'
                    );
                    await apiRequest(
                        `/api/agents/${editingAgentId}/assignments`,
                        {
                            method: 'PUT',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ admin_user_ids: agentData.assigned_admin_ids })
                        },
                        'Updating assignments'
                    );
                    console.log('✅ [SUBMIT] Agent updated successfully');
                } else {
                    // Create new agent
                    console.log('📝 [SUBMIT] Creating new agent...');
                    console.log('📝 [SUBMIT] Supabase client available:', typeof supabaseClient);
                    console.log('📝 [SUBMIT] Using current user from auth state:', currentUser?.id);

                    console.log('📝 [SUBMIT] Waiting for create operation...');
                    const data = await apiRequest(
                        '/api/agents',
                        {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(agentData)
                        },
                        'Creating agent'
                    );
                    console.log('📝 [SUBMIT] Create operation completed!');
                    console.log('✅ [SUBMIT] Agent created successfully:', data);
                    savedAgentId = data.id;
                }

                // Upload reference files if any were selected
                console.log('📚 [SUBMIT] Checking for reference files to upload...');
                const fileUploads = [
                    { type: 'example_input', inputId: 'example-input-file' },
                    { type: 'example_output', inputId: 'example-output-file' },
                    { type: 'quality_standard', inputId: 'quality-standard-file' },
                    { type: 'reference_doc', inputId: 'reference-doc-file' }
                ];

                let uploadedCount = 0;
                for (const { type, inputId } of fileUploads) {
                    const fileInput = document.getElementById(inputId);
                    if (fileInput && fileInput.files.length > 0) {
                        console.log(`📤 [SUBMIT] Uploading ${fileInput.files.length} files for ${type}...`);
                        try {
                            await uploadReferenceFiles(savedAgentId, fileInput.files, type);
                            uploadedCount += fileInput.files.length;
                        } catch (error) {
                            console.error(`❌ [SUBMIT] Failed to upload ${type} files:`, error);
                            await customAlert(`Warning: Some reference files failed to upload: ${error.message}`, 'Upload Warning');
                        }
                    }
                }

                if (uploadedCount > 0) {
                    console.log(`✅ [SUBMIT] Uploaded ${uploadedCount} reference files`);
                }

                console.log('📝 [SUBMIT] Closing modal...');
                // Close modal and reload agents
                document.getElementById('agent-modal').style.display = 'none';

                console.log('📝 [SUBMIT] Reloading agents list...');
                await loadAgents();
                console.log('✅ [SUBMIT] All done!');

            } catch (error) {
                console.error('❌ [SUBMIT] Error saving agent:', error);
                console.error('❌ [SUBMIT] Error details:', JSON.stringify(error, null, 2));
                console.error('❌ [SUBMIT] Error message:', error.message);
                console.error('❌ [SUBMIT] Error code:', error.code);
                console.error('❌ [SUBMIT] Error hint:', error.hint);

                let errorMsg = 'Failed to save agent: ' + error.message;
                if (error.details) errorMsg += '\nDetails: ' + error.details;
                if (error.hint) errorMsg += '\nHint: ' + error.hint;

                await customAlert(errorMsg, 'Error Saving Agent');
            } finally {
                console.log('📝 [SUBMIT] Re-enabling button...');
                // Re-enable button
                if (saveBtn) {
                    saveBtn.disabled = false;
                }
                if (btnText) {
                    btnText.style.display = 'inline';
                }
                if (btnLoading) {
                    btnLoading.style.display = 'none';
                }
            }
        });
        console.log('✅ [INIT] Form submit listener attached successfully');
    } else {
        console.error('❌ [INIT] Agent form NOT FOUND in DOM!');
    }


    // Cancel Button
    const cancelBtn = document.getElementById('cancel-btn');
    console.log('🔧 [INIT] Cancel button found:', cancelBtn !== null);
    if (cancelBtn) {
        cancelBtn.addEventListener('click', () => {
            console.log('🔧 [CANCEL] Cancel button clicked');
            document.getElementById('agent-modal').style.display = 'none';
        });
    }

    // Close modals on X click
    console.log('🔧 [INIT] Setting up modal close buttons...');
    document.querySelectorAll('.modal .close').forEach(closeBtn => {
        closeBtn.addEventListener('click', function() {
            console.log('🔧 [CLOSE] X button clicked');
            this.closest('.modal').style.display = 'none';
        });
    });


    console.log('✅✅✅ [INIT] ALL agent listeners initialized successfully! ✅✅✅');
    listenersInitialized = true;
    console.log('✅ [INIT] Flag set - future calls will be skipped');
}

async function loadAgents() {
    try {
        console.log('📥 Loading agents...');

        if (!currentUser?.id) {
            throw new Error('User session not available. Please log in again.');
        }

        const [agents, tasks, runs] = await Promise.all([
            apiRequest('/api/agents', { method: 'GET' }, 'Loading agents'),
            apiRequest('/api/tasks', { method: 'GET' }, 'Loading tasks'),
            apiRequest('/api/check-runs?summary_only=true', { method: 'GET' }, 'Loading recent runs').catch(error => {
                console.error('Could not load recent runs:', error);
                return [];
            })
        ]);

        currentAgents = agents || [];
        currentTasks = tasks || [];
        recentRunsByAgent = new Map();
        // Runs are read per task now that the task row is the run surface.
        recentRunsByTask = new Map();
        (runs || []).forEach(run => {
            const agentId = String(run.agent_id || '');
            if (agentId) {
                const agentRuns = recentRunsByAgent.get(agentId) || [];
                if (agentRuns.length < 7) {
                    agentRuns.push(run);
                    recentRunsByAgent.set(agentId, agentRuns);
                }
            }
            const taskId = String(run.task_id || '');
            if (taskId) {
                const taskRuns = recentRunsByTask.get(taskId) || [];
                if (taskRuns.length < 7) {
                    taskRuns.push(run);
                    recentRunsByTask.set(taskId, taskRuns);
                }
            }
        });
        console.log(`✅ Loaded ${currentAgents.length} agents`);

        renderAgents();
        if (typeof renderTasks === 'function') renderTasks();
    } catch (error) {
        console.error('Error loading agents:', error);
        customAlert('Failed to load agents: ' + error.message, 'Error Loading Agents');
    }
}

/**
 * Agents are configuration. Running moved to the task row, so this list no
 * longer carries a task picker or a Run button: an agent is defined here and
 * exercised on the Tasks page.
 */
function renderAgents() {
    const agentsList = document.getElementById('agents-list');
    const emptyState = document.getElementById('empty-state');
    if (currentAgents.length === 0) {
        agentsList.innerHTML = '';
        emptyState.style.display = 'block';
        return;
    }

    emptyState.style.display = 'none';

    agentsList.innerHTML = currentAgents.map(agent => {
        const taskCount = currentTasks.filter(task => String(task.agent_id) === String(agent.id)).length;
        const taskLabel = taskCount === 0
            ? 'No tasks yet'
            : `${taskCount} task${taskCount === 1 ? '' : 's'}`;
        return `
        <div class="agent-row" data-agent-id="${escapeHtml(String(agent.id))}">
            <div class="agent-row-identity">
                <span class="agent-row-name">${escapeHtml(agent.name)}</span>
                ${agent.description ? `<span class="agent-row-desc">${escapeHtml(agent.description)}</span>` : ''}
            </div>
            <div class="agent-row-meta">
                <span class="agent-task-count${taskCount ? '' : ' is-empty'}">${escapeHtml(taskLabel)}</span>
            </div>
            <div class="agent-row-actions">
                <button class="btn btn-secondary btn-small" type="button" onclick="editAgent('${escapeHtml(String(agent.id))}')">Edit</button>
                <button class="btn btn-quiet btn-small" type="button" onclick="deleteAgent('${escapeHtml(String(agent.id))}')" aria-label="Delete ${escapeHtml(agent.name)}">Delete</button>
            </div>
        </div>`;
    }).join('');
}

// Edit Agent
window.editAgent = async function(agentId) {
    const agent = currentAgents.find(a => a.id === agentId);
    if (!agent) return;

    editingAgentId = agentId;
    document.getElementById('modal-title').textContent = 'Edit Task Checker Agent';
    document.getElementById('agent-id').value = agent.id;
    document.getElementById('agent-name').value = agent.name;
    document.getElementById('agent-description').value = agent.description || '';
    document.getElementById('agent-prompt').value = agent.system_prompt || '';
    document.getElementById('agent-codex-model').value = agent.codex_model || 'gpt-5.6-sol';
    document.getElementById('agent-codex-effort').value = agent.codex_reasoning_effort || 'xhigh';
    document.getElementById('agent-modal').style.display = 'block';

    try {
        const assignments = await apiRequest(`/api/agents/${agentId}/assignments`, { method: 'GET' }, 'Loading assignments');
        await loadAssignableAdmins((assignments || []).map(row => row.admin_user_id));
    } catch (error) {
        console.error('Failed to load assignments:', error);
    }

    // Initialize FileSelectors only if not already initialized, then populate with existing data
    setTimeout(() => {
        console.log('📁 [EDIT] Checking FileSelectors...');

        // Only initialize if they don't exist yet
        if (!kbFilesSelector || !exampleInputSelector || !exampleOutputSelector) {
            console.log('📁 [EDIT] FileSelectors not initialized, initializing now...');
            initializeFileSelectors();
        } else {
            console.log('📁 [EDIT] FileSelectors already initialized, skipping...');
        }

        // Wait for FileSelectors to be ready, then populate with existing data
        setTimeout(async () => {
            console.log('📁 [EDIT] Populating FileSelectors with existing data...');

            // Populate KB Files
            if (kbFilesSelector && agent.kb_file_paths) {
                const kbFiles = Array.isArray(agent.kb_file_paths) ? agent.kb_file_paths : [];
                kbFilesSelector.setSelectedFiles(kbFiles);
                console.log(`  - Set ${kbFiles.length} KB files`);
            }

            // Populate Reference Files from stored paths
            if (agent.reference_file_paths) {
                if (exampleInputSelector && agent.reference_file_paths.example_inputs) {
                    exampleInputSelector.setSelectedFiles(agent.reference_file_paths.example_inputs);
                    console.log(`  - Set ${agent.reference_file_paths.example_inputs.length} example inputs`);
                }
                if (exampleOutputSelector && agent.reference_file_paths.example_outputs) {
                    exampleOutputSelector.setSelectedFiles(agent.reference_file_paths.example_outputs);
                    console.log(`  - Set ${agent.reference_file_paths.example_outputs.length} example outputs`);
                }
            }

            console.log('✅ [EDIT] FileSelectors populated');
        }, 200);
    }, 100);

    // Load reference files for this agent (Supabase Storage files)
    loadReferenceFiles(agentId);
};

// Delete Agent
window.deleteAgent = async function(agentId) {
    console.log('🗑 [DELETE] Delete function called with agentId:', agentId);

    const agent = currentAgents.find(a => a.id === agentId);
    console.log('🗑 [DELETE] Found agent:', agent);

    if (!agent) {
        console.error('❌ [DELETE] Agent not found in currentAgents array');
        return;
    }

    console.log('🗑 [DELETE] Showing confirmation dialog...');
    const confirmed = await customConfirm(
        `Are you sure you want to delete "${agent.name}"? This action cannot be undone.`,
        'Delete Agent'
    );

    if (!confirmed) {
        console.log('🗑 [DELETE] User cancelled deletion');
        return;
    }

    try {
        console.log('🗑 [DELETE] User confirmed, deleting agent from database...');

        await apiRequest(
            `/api/agents/${agentId}`,
            { method: 'DELETE' },
            'Deleting agent'
        );

        console.log('✅ [DELETE] Agent deleted successfully from database');
        console.log('🗑 [DELETE] Reloading agents list...');
        await loadAgents();
        console.log('✅ [DELETE] Agents list reloaded');
    } catch (error) {
        console.error('❌ [DELETE] Error deleting agent:', error);
        await customAlert('Failed to delete agent: ' + error.message, 'Error Deleting Agent');
    }
};

// Utility function to escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ==================== REFERENCE FILES FUNCTIONALITY ====================

/**
 * Upload reference files for an agent
 * @param {string} agentId - Agent UUID
 * @param {FileList} files - Files to upload
 * @param {string} fileType - Type of reference file
 * @returns {Promise<Array>} - Array of upload results
 */
async function uploadReferenceFiles(agentId, files, fileType) {
    if (!files || files.length === 0) return [];

    const results = [];
    const token = await getAccessToken();

    for (const file of files) {
        try {
            console.log(`📤 [REF] Uploading ${file.name} as ${fileType}...`);

            const formData = new FormData();
            formData.append('file', file);
            formData.append('file_type', fileType);

            const response = await fetch(`${API_URL}/api/agents/${agentId}/reference-files`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`
                },
                body: formData
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Upload failed');
            }

            const result = await response.json();
            results.push(result);
            console.log(`✅ [REF] Uploaded ${file.name} successfully`);

        } catch (error) {
            console.error(`❌ [REF] Failed to upload ${file.name}:`, error);
            throw new Error(`Failed to upload ${file.name}: ${error.message}`);
        }
    }

    return results;
}

/**
 * Load reference files for an agent and display them
 * @param {string} agentId - Agent UUID
 */
async function loadReferenceFiles(agentId) {
    try {
        console.log(`📚 [REF] Loading reference files for agent ${agentId}...`);

        const files = await apiRequest(
            `/api/agents/${agentId}/reference-files`,
            {},
            'Loading reference files'
        );

        displayReferenceFiles(files);
        console.log(`✅ [REF] Loaded ${files.length} reference files`);

    } catch (error) {
        console.error('❌ [REF] Error loading reference files:', error);
        // Don't show error to user - just log it
    }
}

/**
 * Display reference files in the UI
 * @param {Array} files - Array of file metadata
 */
function displayReferenceFiles(files) {
    // Group files by type
    const grouped = {
        example_input: [],
        example_output: [],
        quality_standard: [],
        reference_doc: []
    };

    files.forEach(file => {
        if (grouped[file.file_type]) {
            grouped[file.file_type].push(file);
        }
    });

    // Display in each section
    const sections = [
        { type: 'example_input', listId: 'example-input-list' },
        { type: 'example_output', listId: 'example-output-list' },
        { type: 'quality_standard', listId: 'quality-standard-list' },
        { type: 'reference_doc', listId: 'reference-doc-list' }
    ];

    sections.forEach(({ type, listId }) => {
        const listDiv = document.getElementById(listId);
        if (!listDiv) return;

        const fileList = grouped[type] || [];

        if (fileList.length === 0) {
            listDiv.innerHTML = '';
            return;
        }

        listDiv.innerHTML = fileList.map(file => `
            <div class="uploaded-file-item" data-file-id="${file.id}">
                <span title="${escapeHtml(file.file_name)}">${escapeHtml(file.file_name)}</span>
                <span>${formatFileSize(file.file_size)}</span>
                <button type="button" onclick="deleteReferenceFile('${file.id}')" class="btn-delete" title="Delete file">🗑️</button>
            </div>
        `).join('');
    });
}

/**
 * Delete a reference file
 * @param {string} fileId - File UUID
 */
window.deleteReferenceFile = async function(fileId) {
    if (!editingAgentId) {
        await customAlert('No agent selected', 'Error');
        return;
    }

    const confirmed = await customConfirm(
        'Are you sure you want to delete this reference file?',
        'Delete Reference File'
    );

    if (!confirmed) return;

    try {
        console.log(`🗑️ [REF] Deleting reference file ${fileId}...`);

        await apiRequest(
            `/api/agents/${editingAgentId}/reference-files/${fileId}`,
            { method: 'DELETE' },
            'Deleting reference file'
        );

        // Remove from UI
        const fileItem = document.querySelector(`[data-file-id="${fileId}"]`);
        if (fileItem) {
            fileItem.remove();
        }

        console.log(`✅ [REF] Reference file deleted successfully`);

    } catch (error) {
        console.error('❌ [REF] Error deleting reference file:', error);
        await customAlert('Failed to delete file: ' + error.message, 'Error');
    }
};

/**
 * Format file size for display
 * @param {number} bytes - File size in bytes
 * @returns {string} - Formatted file size
 */
function formatFileSize(bytes) {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Clear reference files UI
 */
function clearReferenceFilesUI() {
    const listIds = [
        'example-input-list',
        'example-output-list',
        'quality-standard-list',
        'reference-doc-list'
    ];

    listIds.forEach(id => {
        const list = document.getElementById(id);
        if (list) list.innerHTML = '';
    });

    // Clear file inputs
    const fileInputs = [
        'example-input-file',
        'example-output-file',
        'quality-standard-file',
        'reference-doc-file'
    ];

    fileInputs.forEach(id => {
        const input = document.getElementById(id);
        if (input) input.value = '';
    });
}

// Expose functions to window for debugging
window.initAgentListeners = initAgentListeners;
window.loadAgents = loadAgents;
window.renderAgents = renderAgents;
window.uploadReferenceFiles = uploadReferenceFiles;
window.loadReferenceFiles = loadReferenceFiles;
window.formatFileSize = formatFileSize;

console.log('✅ [LOAD] agents.js fully loaded and functions exposed to window');
console.log('✅ [LOAD] initAgentListeners:', typeof window.initAgentListeners);
console.log('✅ [LOAD] loadAgents:', typeof window.loadAgents);

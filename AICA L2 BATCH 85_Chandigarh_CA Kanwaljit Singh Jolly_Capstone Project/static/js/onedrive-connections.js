// OneDrive Connections Management
console.log('📦 [LOAD] onedrive-connections.js loaded');

let currentlyEditingConnectionId = null;
let pendingRefreshToken = null; // Store refresh token from OAuth callback

/**
 * Show loading spinner
 */
function showOnedriveLoading(text = 'Loading...') {
    const loadingEl = document.getElementById('onedrive-loading');
    const loadingTextEl = document.getElementById('onedrive-loading-text');
    const connectionsListEl = document.getElementById('onedrive-connections-list');
    const noConnectionsEl = document.getElementById('no-connections-message');

    if (loadingEl) loadingEl.style.display = 'flex';
    if (loadingTextEl) loadingTextEl.textContent = text;
    if (connectionsListEl) connectionsListEl.style.display = 'none';
    if (noConnectionsEl) noConnectionsEl.style.display = 'none';
}

/**
 * Hide loading spinner
 */
function hideOnedriveLoading() {
    const loadingEl = document.getElementById('onedrive-loading');
    if (loadingEl) loadingEl.style.display = 'none';
}

/**
 * Load and display all OneDrive connections for the current user
 */
async function loadOnedriveConnections() {
    try {
        console.log('📁 [ONEDRIVE] Loading connections...');
        showOnedriveLoading('Loading connections...');

        const token = await getAccessToken();
        const response = await fetch(`${API_URL}/api/onedrive/connections`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            // If it's a 404 or table doesn't exist, just show empty state
            // Don't show error modal for missing table or no connections
            if (response.status === 404 || response.status === 500) {
                console.log('📁 [ONEDRIVE] No connections table yet or no connections found');
                hideOnedriveLoading();
                renderOnedriveConnections([]);
                return;
            }
            throw new Error('Failed to load connections');
        }

        const data = await response.json();
        const connections = data.connections || [];

        console.log(`✅ [ONEDRIVE] Loaded ${connections.length} connections`);

        hideOnedriveLoading();
        renderOnedriveConnections(connections);

    } catch (error) {
        console.error('❌ [ONEDRIVE] Error loading connections:', error);
        hideOnedriveLoading();

        // Only show error alert for actual network/auth errors
        // If it's just missing data or table, show empty state
        if (error.message.includes('Failed to fetch') || error.message.includes('Unauthorized')) {
            await customAlert('Failed to load OneDrive connections: ' + error.message, 'Error');
        } else {
            // For other errors (like table doesn't exist), just show empty state
            console.log('📁 [ONEDRIVE] Showing empty state due to error:', error.message);
            renderOnedriveConnections([]);
        }
    }
}

/**
 * Render the list of OneDrive connections
 */
function renderOnedriveConnections(connections) {
    const listContainer = document.getElementById('onedrive-connections-list');
    const noConnectionsMessage = document.getElementById('no-connections-message');

    if (!listContainer) return;

    // Always show the list container
    listContainer.style.display = 'block';

    if (connections.length === 0) {
        listContainer.innerHTML = '';
        listContainer.style.display = 'none';
        if (noConnectionsMessage) {
            noConnectionsMessage.style.display = 'block';
        }
        return;
    }

    if (noConnectionsMessage) {
        noConnectionsMessage.style.display = 'none';
    }

    listContainer.innerHTML = connections.map(conn => `
        <div class="onedrive-connection-card ${conn.is_active ? 'active' : ''}">
            <div class="connection-info">
                <div class="connection-header">
                    <span class="connection-name">${escapeHtml(conn.account_name)}</span>
                    ${conn.is_active ? '<span class="connection-active-badge">Active</span>' : ''}
                </div>
                <div class="connection-meta">
                    ${conn.account_email ? `<span>${escapeHtml(conn.account_email)}</span>` : ''}
                    <span>Base Path: <code>${escapeHtml(conn.base_folder_path || '/')}</code></span>
                </div>
            </div>
            <div class="connection-actions">
                ${!conn.is_active ? `
                    <button class="btn btn-secondary" onclick="activateConnection('${conn.id}')">
                        Set Active
                    </button>
                ` : ''}
                <button class="btn btn-secondary" onclick="editConnection('${conn.id}')">
                    Edit
                </button>
                <button class="btn btn-danger" onclick="deleteConnection('${conn.id}')">
                    Delete
                </button>
            </div>
        </div>
    `).join('');
}

/**
 * Show the add connection form
 * This immediately triggers the OAuth popup
 */
async function showAddConnectionForm() {
    console.log('📝 [ONEDRIVE] Showing add connection form - triggering OAuth first');

    currentlyEditingConnectionId = null;
    pendingRefreshToken = null;

    // Clear form fields
    document.getElementById('connection-form-title').textContent = 'Add OneDrive Connection';
    document.getElementById('editing-connection-id').value = '';
    document.getElementById('connection-account-name').value = '';
    document.getElementById('connection-account-email').value = '';
    document.getElementById('connection-base-path').value = '/';
    document.getElementById('onedrive-connected-status').style.display = 'none';

    // Immediately trigger OAuth flow (popup appears on button click)
    await connectNewOneDrive();
}

/**
 * Hide the connection form
 */
function hideConnectionForm() {
    console.log('📝 [ONEDRIVE] Hiding connection form');
    document.getElementById('onedrive-connection-form').style.display = 'none';
    currentlyEditingConnectionId = null;
    pendingRefreshToken = null;
}

/**
 * Edit an existing connection
 */
window.editConnection = async function(connectionId) {
    console.log('✏️ [ONEDRIVE] Editing connection:', connectionId);

    try {
        showOnedriveLoading('Loading connection details...');

        const token = await getAccessToken();
        const response = await fetch(`${API_URL}/api/onedrive/connections`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            throw new Error('Failed to load connection details');
        }

        const data = await response.json();
        const connection = (data.connections || []).find(c => c.id === connectionId);

        if (!connection) {
            throw new Error('Connection not found');
        }

        // Populate form
        currentlyEditingConnectionId = connectionId;
        document.getElementById('connection-form-title').textContent = 'Edit OneDrive Connection';
        document.getElementById('editing-connection-id').value = connectionId;
        document.getElementById('connection-account-name').value = connection.account_name;
        document.getElementById('connection-account-email').value = connection.account_email || '';
        document.getElementById('connection-base-path').value = connection.base_folder_path || '/';

        // Hide the connected status indicator when editing
        document.getElementById('onedrive-connected-status').style.display = 'none';

        // Hide loading and show form
        hideOnedriveLoading();
        document.getElementById('onedrive-connection-form').style.display = 'block';

        // Show connections list again
        document.getElementById('onedrive-connections-list').style.display = 'block';

    } catch (error) {
        console.error('❌ [ONEDRIVE] Error loading connection:', error);
        hideOnedriveLoading();
        await customAlert('Failed to load connection: ' + error.message, 'Error');
    }
};

/**
 * Save connection (create or update)
 */
async function saveConnection(event) {
    event.preventDefault();

    try {
        console.log('💾 [ONEDRIVE] Saving connection...');

        const connectionId = document.getElementById('editing-connection-id').value;
        const accountName = document.getElementById('connection-account-name').value.trim();
        const accountEmail = document.getElementById('connection-account-email').value.trim();
        const basePath = document.getElementById('connection-base-path').value.trim();

        if (!accountName) {
            await customAlert('Account name is required', 'Validation Error');
            return;
        }

        if (!basePath.startsWith('/')) {
            await customAlert('Base path must start with /', 'Validation Error');
            return;
        }

        // Show loading
        showOnedriveLoading(connectionId ? 'Updating connection...' : 'Saving connection...');

        const token = await getAccessToken();

        if (connectionId) {
            // Update existing connection
            const response = await fetch(`${API_URL}/api/onedrive/connections/${connectionId}`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    account_name: accountName,
                    account_email: accountEmail,
                    base_folder_path: basePath
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to update connection');
            }

            console.log('✅ [ONEDRIVE] Connection updated');
            await customAlert('Connection updated successfully!', 'Success');

        } else {
            // Create new connection
            if (!pendingRefreshToken) {
                await customAlert('Please connect your OneDrive account first', 'Validation Error');
                return;
            }

            const response = await fetch(`${API_URL}/api/onedrive/connections`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    account_name: accountName,
                    account_email: accountEmail,
                    base_folder_path: basePath,
                    refresh_token: pendingRefreshToken
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to create connection');
            }

            console.log('✅ [ONEDRIVE] Connection created');
            await customAlert('Connection added successfully!', 'Success');
        }

        hideConnectionForm();
        await loadOnedriveConnections();

    } catch (error) {
        console.error('❌ [ONEDRIVE] Error saving connection:', error);
        await customAlert('Failed to save connection: ' + error.message, 'Error');
    }
}

/**
 * Delete a connection
 */
window.deleteConnection = async function(connectionId) {
    const confirmed = await customConfirm(
        'Are you sure you want to delete this OneDrive connection?',
        'Delete Connection'
    );

    if (!confirmed) return;

    try {
        console.log('🗑️ [ONEDRIVE] Deleting connection:', connectionId);
        showOnedriveLoading('Deleting connection...');

        const token = await getAccessToken();
        const response = await fetch(`${API_URL}/api/onedrive/connections/${connectionId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to delete connection');
        }

        console.log('✅ [ONEDRIVE] Connection deleted');
        await customAlert('Connection deleted successfully!', 'Success');
        await loadOnedriveConnections();

    } catch (error) {
        console.error('❌ [ONEDRIVE] Error deleting connection:', error);
        await customAlert('Failed to delete connection: ' + error.message, 'Error');
    }
};

/**
 * Activate a connection (make it the active one)
 */
window.activateConnection = async function(connectionId) {
    try {
        console.log('✅ [ONEDRIVE] Activating connection:', connectionId);
        showOnedriveLoading('Activating connection...');

        const token = await getAccessToken();
        const response = await fetch(`${API_URL}/api/onedrive/connections/${connectionId}/activate`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to activate connection');
        }

        console.log('✅ [ONEDRIVE] Connection activated');
        await customAlert('Connection is now active!', 'Success');
        await loadOnedriveConnections();

    } catch (error) {
        console.error('❌ [ONEDRIVE] Error activating connection:', error);
        await customAlert('Failed to activate connection: ' + error.message, 'Error');
    }
};

/**
 * Handle OneDrive OAuth callback
 * This captures the refresh token from the OAuth flow
 */
function handleOnedriveOAuthCallback(refreshToken) {
    console.log('🔐 [ONEDRIVE] OAuth callback received, refresh token captured');
    pendingRefreshToken = refreshToken;
    document.getElementById('onedrive-connected-status').style.display = 'block';
}

/**
 * Initiate OneDrive connection flow
 * Opens a popup window for OAuth without changing the logged-in user
 */
async function connectNewOneDrive() {
    try {
        console.log('🔗 [ONEDRIVE] Initiating OneDrive connection...');

        // Get authorization URL from backend
        const token = await getAccessToken();
        const response = await fetch(`${API_URL}/api/onedrive/auth`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to get authorization URL');
        }

        const data = await response.json();
        const authUrl = data.authorization_url;

        console.log('🔗 [ONEDRIVE] Opening OAuth popup...');

        // Open OAuth flow in popup window
        const popup = window.open(
            authUrl,
            'OneDrive OAuth',
            'width=600,height=700,left=100,top=100'
        );

        if (!popup) {
            throw new Error('Popup blocked. Please allow popups for this site.');
        }

        // Listen for OAuth callback message
        const messageHandler = (event) => {
            // Verify origin for security (allow same-origin + localhost/127.0.0.1 variants)
            const allowedOrigins = new Set();
            const addOrigin = (value) => {
                if (!value) return;
                try {
                    const origin = new URL(value, window.location.origin).origin;
                    allowedOrigins.add(origin);
                } catch (_) {
                    // ignore invalid
                }
            };
            addOrigin(window.location.origin);
            addOrigin(API_URL);

            const expandLocal = (origin) => {
                try {
                    const url = new URL(origin);
                    const host = url.hostname;
                    const port = url.port || (url.protocol === 'https:' ? '443' : '80');
                    const altHost = host === 'localhost' ? '127.0.0.1' : (host === '127.0.0.1' ? 'localhost' : null);
                    if (altHost) {
                        allowedOrigins.add(`${url.protocol}//${altHost}:${port}`);
                    }
                    if (host === 'localhost' || host === '127.0.0.1') {
                        ['5000', '5001'].forEach((p) => {
                            allowedOrigins.add(`${url.protocol}//${host}:${p}`);
                            if (altHost) {
                                allowedOrigins.add(`${url.protocol}//${altHost}:${p}`);
                            }
                        });
                    }
                } catch (_) {
                    // ignore invalid
                }
            };
            Array.from(allowedOrigins).forEach(expandLocal);

            if (!allowedOrigins.has(event.origin)) {
                console.warn('⚠️ [ONEDRIVE] Ignoring message from unknown origin:', event.origin);
                return;
            }

            if (event.data.type === 'onedrive_success') {
                console.log('✅ [ONEDRIVE] OAuth successful, refresh token received');

                // Store refresh token and account email
                pendingRefreshToken = event.data.refreshToken;
                const accountEmail = event.data.accountEmail;

                // Auto-generate account name from email
                let accountName = 'OneDrive Account';
                if (accountEmail) {
                    // Extract name from email (e.g., work@company.com -> "work@company.com OneDrive")
                    const emailParts = accountEmail.split('@');
                    if (emailParts.length === 2) {
                        const username = emailParts[0];
                        const domain = emailParts[1].split('.')[0];
                        // Capitalize first letter
                        accountName = domain.charAt(0).toUpperCase() + domain.slice(1) + ' OneDrive';
                    }
                }

                // Show the form with auto-filled details
                document.getElementById('onedrive-connection-form').style.display = 'block';
                document.getElementById('connection-account-name').value = accountName;
                document.getElementById('connection-account-email').value = accountEmail || '';
                document.getElementById('connection-base-path').value = '/';
                document.getElementById('onedrive-connected-status').style.display = 'block';

                // Let the superadmin replace the suggested friendly name first.
                document.getElementById('connection-account-name').focus();
                document.getElementById('connection-account-name').select();

                // Show success message
                customAlert(
                    'Microsoft account connected successfully!\n\n' +
                    'Name this connection, set its base folder path, and click "Save Connection".',
                    'Account Connected'
                );

                // Remove event listener
                window.removeEventListener('message', messageHandler);

            } else if (event.data.type === 'onedrive_error') {
                console.error('❌ [ONEDRIVE] OAuth error:', event.data.error);
                customAlert('OneDrive connection failed: ' + event.data.error, 'Error');

                // Remove event listener
                window.removeEventListener('message', messageHandler);
            }
        };

        // Add message listener
        window.addEventListener('message', messageHandler);

        console.log('🔗 [ONEDRIVE] Waiting for OAuth callback...');

    } catch (error) {
        console.error('❌ [ONEDRIVE] Error connecting OneDrive:', error);
        await customAlert('Failed to connect OneDrive: ' + error.message, 'Error');
    }
}

/**
 * Initialize OneDrive connections management
 */
function initOnedriveConnectionsManagement() {
    console.log('🔧 [ONEDRIVE] Initializing connections management...');

    // Add Connection button - triggers OAuth immediately
    const addBtn = document.getElementById('add-onedrive-connection-btn');
    if (addBtn) {
        addBtn.addEventListener('click', showAddConnectionForm);
    }

    // Cancel button
    const cancelBtn = document.getElementById('cancel-connection-form-btn');
    if (cancelBtn) {
        cancelBtn.addEventListener('click', hideConnectionForm);
    }

    // Save connection form
    const saveForm = document.getElementById('save-connection-form');
    if (saveForm) {
        saveForm.addEventListener('submit', saveConnection);
    }

    console.log('✅ [ONEDRIVE] Connections management initialized');
}

// Expose functions to window
window.loadOnedriveConnections = loadOnedriveConnections;
window.showAddConnectionForm = showAddConnectionForm;
window.hideConnectionForm = hideConnectionForm;
window.saveConnection = saveConnection;
window.handleOnedriveOAuthCallback = handleOnedriveOAuthCallback;
window.connectNewOneDrive = connectNewOneDrive;
window.initOnedriveConnectionsManagement = initOnedriveConnectionsManagement;

console.log('✅ [LOAD] onedrive-connections.js fully loaded');


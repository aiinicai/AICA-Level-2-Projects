// Authentication Module

// Flag to prevent duplicate dashboard initialization
let dashboardInitialized = false;

function getAuthRedirectUrl() {
    return `${window.location.origin}${window.location.pathname}`;
}

function clearAuthHash() {
    if (!window.location.hash) {
        return;
    }

    const hash = window.location.hash;
    const authKeys = [
        'access_token',
        'refresh_token',
        'provider_token',
        'expires_in',
        'token_type',
        'error'
    ];
    const isAuthHash = hash === '#' || authKeys.some((key) => hash.includes(key));

    if (isAuthHash) {
        window.history.replaceState({}, document.title, window.location.pathname + window.location.search);
    }
}

async function initAuth() {
    console.log('?? Initializing authentication...');
    setupPasswordLogin();

    // Check if user is already logged in
    const { data: { session } } = await supabaseClient.auth.getSession();
    clearAuthHash();

    if (session) {
        console.log('? User logged in:', session.user.email);
        currentUser = session.user;
        await onUserLoggedIn(session);
    } else {
        console.log('? No user session found');
        showAuthSection();
    }

    // Listen for auth changes
    supabaseClient.auth.onAuthStateChange(async (event, session) => {
        console.log('Auth state changed:', event);

        if (event === 'SIGNED_IN' && session) {
            clearAuthHash();
            currentUser = session.user;
            await onUserLoggedIn(session);
        } else if (event === 'SIGNED_OUT') {
            currentUser = null;
            dashboardInitialized = false;
            showAuthSection();
        }
    });
}

function showAuthSection() {
    document.getElementById('loading-screen').style.display = 'none';
    document.getElementById('auth-section').style.display = 'block';
    document.getElementById('dashboard-section').style.display = 'none';
}

function showDashboard() {
    document.getElementById('loading-screen').style.display = 'none';
    document.getElementById('auth-section').style.display = 'none';
    document.getElementById('dashboard-section').style.display = 'block';
}

function setButtonLoading(button, isLoading, loadingText) {
    if (!button) {
        return;
    }
    if (isLoading) {
        button.classList.add('is-loading');
        button.disabled = true;
        button.dataset.originalText = button.textContent;
        if (loadingText) {
            button.textContent = loadingText;
        }
    } else {
        button.classList.remove('is-loading');
        button.disabled = false;
        if (button.dataset.originalText) {
            button.textContent = button.dataset.originalText;
            delete button.dataset.originalText;
        }
    }
}

function setupPasswordLogin() {
    const form = document.getElementById('password-login-form');
    if (!form) {
        return;
    }

    form.addEventListener('submit', async (event) => {
        event.preventDefault();

        const email = document.getElementById('password-login-email')?.value.trim();
        const password = document.getElementById('password-login-password')?.value;
        const submitButton = document.getElementById('password-login-btn');

        if (!email || !password) {
            await customAlert('Email and password are required', 'Login Error');
            return;
        }

        try {
            setButtonLoading(submitButton, true, 'Signing in...');
            const { error } = await supabaseClient.auth.signInWithPassword({
                email,
                password
            });

            if (error) throw error;

            form.reset();
        } catch (error) {
            console.error('Password login error:', error);
            await customAlert('Failed to login: ' + error.message, 'Login Error');
        } finally {
            setButtonLoading(submitButton, false);
        }
    });
}

async function enforcePasswordReset(session) {
    const mustChange = Boolean(session?.user?.user_metadata?.must_change_password);
    if (!mustChange) {
        return false;
    }

    const updated = await showPasswordResetModal();
    if (!updated) {
        return false;
    }

    await supabaseClient.auth.signOut();
    await customAlert('Password updated. Please sign in with your new password.', 'Password Updated');
    return true;
}

function isAzureProvider(session) {
    const provider = session?.user?.app_metadata?.provider;
    const providers = session?.user?.app_metadata?.providers || [];
    return provider === 'azure' || providers.includes('azure');
}

function showPasswordResetModal() {
    const modal = document.getElementById('password-reset-modal');
    const form = document.getElementById('password-reset-form');
    const errorEl = document.getElementById('password-reset-error');
    const newPasswordInput = document.getElementById('password-reset-new');
    const confirmInput = document.getElementById('password-reset-confirm');

    if (!modal || !form || !errorEl || !newPasswordInput || !confirmInput) {
        console.error('Password reset modal elements missing');
        return Promise.resolve(false);
    }

    document.getElementById('loading-screen').style.display = 'none';
    document.getElementById('auth-section').style.display = 'none';
    document.getElementById('dashboard-section').style.display = 'none';

    modal.style.display = 'block';
    errorEl.style.display = 'none';
    form.reset();

    return new Promise((resolve) => {
        form.onsubmit = async (event) => {
            event.preventDefault();
            errorEl.style.display = 'none';

            const newPassword = newPasswordInput.value.trim();
            const confirmPassword = confirmInput.value.trim();

            if (newPassword.length < 8) {
                errorEl.textContent = 'Password must be at least 8 characters.';
                errorEl.style.display = 'block';
                return;
            }
            if (newPassword !== confirmPassword) {
                errorEl.textContent = 'Passwords do not match.';
                errorEl.style.display = 'block';
                return;
            }

            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) submitBtn.disabled = true;

            try {
                const { error } = await supabaseClient.auth.updateUser({
                    password: newPassword,
                    data: { must_change_password: false }
                });

                if (error) throw error;

                modal.style.display = 'none';
                form.reset();
                if (submitBtn) submitBtn.disabled = false;
                resolve(true);
            } catch (error) {
                console.error('Password reset error:', error);
                errorEl.textContent = error.message || 'Failed to update password.';
                errorEl.style.display = 'block';
                if (submitBtn) submitBtn.disabled = false;
            }
        };
    });
}

function showOnedriveModal() {
    console.log('📋 showOnedriveModal called - redirecting to Settings');

    if (currentUserRole !== 'super_admin') {
        console.log('⚠️ Not super admin, skipping Settings modal');
        return;
    }

    const modal = document.getElementById('settings-modal');
    if (modal) {
        console.log('✅ Showing Settings modal (OneDrive tab)');
        modal.style.display = 'block';
        // Switch to OneDrive tab
        switchSettingsTab('onedrive');
    } else {
        console.error('❌ Settings modal element not found!');
    }
}

function hideOnedriveModal() {
    console.log('📋 hideOnedriveModal called - hiding Settings');

    const modal = document.getElementById('settings-modal');
    if (modal) {
        console.log('✅ Hiding Settings modal');
        modal.style.display = 'none';
    } else {
        console.error('❌ Settings modal element not found!');
    }
}

window.showOnedriveModal = showOnedriveModal;
window.hideOnedriveModal = hideOnedriveModal;
window.openSettingsModal = openSettingsModal;
window.closeSettingsModal = closeSettingsModal;
window.switchSettingsTab = switchSettingsTab;

async function onUserLoggedIn(session) {
    if (dashboardInitialized) {
        console.log('?? [AUTH] Dashboard already initialized, skipping duplicate setup');
        return;
    }

    const passwordResetHandled = await enforcePasswordReset(session);
    if (passwordResetHandled) {
        return;
    }

    console.log('??? [AUTH] User logged in, setting up dashboard...');
    console.log('? [AUTH] Current user:', currentUser);

    // Update UI with user email
    console.log('? [AUTH] Setting user email in UI...');
    document.getElementById('user-email').textContent = currentUser.email;

    // Ensure profile exists in database
    console.log('? [AUTH] Ensuring user profile exists...');
    await ensureUserProfile(session);
    await ensureTenantMembership();

    // Fetch user profile including role
    console.log('? [AUTH] Fetching user profile with role...');
    await fetchUserProfile();

    if (isAzureProvider(session) && currentUserRole !== 'super_admin') {
        await supabaseClient.auth.signOut();
        dashboardInitialized = false;
        showAuthSection();
        await customAlert('Admins must sign in with email and password.', 'Login Restricted');
        return;
    }

    // Show dashboard
    console.log('? [AUTH] Showing dashboard section...');
    showDashboard();

    // OneDrive modal logic - DISABLED (user will open Settings manually)
    // Modal will only show when user clicks Settings button
    console.log('? [AUTH] OneDrive modal auto-popup disabled - user will use Settings button');

    // Initialize event listeners
    console.log('? [AUTH] About to call initAgentListeners()...');
    console.log('? [AUTH] initAgentListeners function exists:', typeof initAgentListeners);
    initAgentListeners();
    console.log('? [AUTH] initAgentListeners() completed');
    initTaskListeners();

    // Load agents
    console.log('? [AUTH] Loading agents...');
    await loadAgents();
    console.log('??? [AUTH] Dashboard setup complete! ???');

    // Mark dashboard as initialized
    dashboardInitialized = true;
    console.log('? [AUTH] Dashboard initialization flag set - future calls will be skipped');
}

async function ensureUserProfile(session) {
    let profile = null;

    try {
        // Check if profile exists
        const { data: profileData, error: fetchError } = await supabaseClient
            .from('profiles')
            .select('*')
            .eq('id', currentUser.id)
            .single();

        if (fetchError && fetchError.code === 'PGRST116') {
            // Profile doesn't exist, create it
            console.log('Creating user profile...');
            const { data, error } = await supabaseClient
                .from('profiles')
                .insert({
                    id: currentUser.id,
                    email: currentUser.email,
                    display_name: currentUser.user_metadata?.full_name || currentUser.email.split('@')[0]
                })
                .select()
                .single();

            if (error) {
                console.error('Error creating profile:', error);
            } else {
                profile = data;
                console.log('✅ Profile created');
            }
        } else if (profileData) {
            profile = profileData;
            console.log('✅ Profile exists');
        } else if (fetchError) {
            console.error('Error fetching profile:', fetchError);
        }
    } catch (error) {
        console.error('Error ensuring profile:', error);
    }

    return profile;
}

async function ensureTenantMembership() {
    try {
        await apiRequest('/api/tenant/provision', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: '{}'
        }, 'Preparing workspace');
    } catch (error) {
        console.error('Unable to provision tenant membership:', error);
        throw error;
    }
}

// Login button
// Microsoft OAuth login button removed (replaced with email/password only)
// Kept for reference in case needed for OneDrive connection in admin settings
/*
document.getElementById('login-btn').addEventListener('click', async () => {
    try {
        console.log('Initiating Microsoft login...');

        const { data, error } = await supabaseClient.auth.signInWithOAuth({
            provider: 'azure',
            options: {
                scopes: 'openid profile email offline_access Files.Read Files.Read.All',
                redirectTo: window.location.origin
            }
        });

        if (error) throw error;

        console.log('Login initiated:', data);
    } catch (error) {
        console.error('Login error:', error);
        customAlert('Failed to login: ' + error.message, 'Login Error');
    }
});
*/

// Connect OneDrive button
const connectOnedriveBtn = document.getElementById('connect-onedrive-btn');
if (connectOnedriveBtn) {
    connectOnedriveBtn.addEventListener('click', async () => {
        try {
            console.log('Connecting OneDrive via Microsoft OAuth...');

            const { data, error } = await supabaseClient.auth.signInWithOAuth({
                provider: 'azure',
                options: {
                    scopes: 'openid profile email offline_access Files.Read Files.Read.All',
                    redirectTo: getAuthRedirectUrl(),
                    queryParams: {
                        prompt: 'consent'
                    }
                }
            });

            if (error) throw error;

            console.log('OneDrive connect initiated:', data);
        } catch (error) {
            console.error('OneDrive connect error:', error);
            customAlert('Failed to connect OneDrive: ' + error.message, 'OneDrive Connection Error');
        }
    });
}

// Logout button
document.getElementById('logout-btn').addEventListener('click', async () => {
    try {
        console.log('Logging out...');
        const { error } = await supabaseClient.auth.signOut();
        if (error) throw error;
        console.log('? Logged out');
    } catch (error) {
        console.error('Logout error:', error);
        customAlert('Failed to logout: ' + error.message, 'Logout Error');
    }
});

// Fetch user profile including role
async function fetchUserProfile() {
    try {
        console.log('?? Fetching user profile with role...');

        // Get token directly from supabase session
        const { data: { session }, error: sessionError } = await supabaseClient.auth.getSession();
        if (sessionError) throw sessionError;
        if (!session) throw new Error('No session found');

        const token = session.access_token;
        console.log('? Got access token');

        const response = await fetch(`${API_URL}/api/auth/profile`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        console.log('?? Profile response status:', response.status);

        if (!response.ok) {
            const errorText = await response.text();
            console.error('? Profile fetch failed:', errorText);
            throw new Error('Failed to fetch profile');
        }

        const profile = await response.json();
        console.log('? Profile data received:', profile);

        currentUserRole = profile.role;
        console.log('? Current user role set to:', currentUserRole);

        // Update UI with role
        const roleElement = document.getElementById('user-role');
        console.log('?? Role element found:', roleElement ? 'YES' : 'NO');

        if (roleElement) {
            const roleText = profile.role === 'super_admin' ? 'Super Admin' : 'Admin';
            const roleClass = 'user-role ' + profile.role.replace('_', '-');

            roleElement.textContent = roleText;
            roleElement.className = roleClass;

            console.log('? Role badge updated:', roleText, '| Class:', roleClass);
        } else {
            console.error('? Role element not found in DOM');
        }

        // Show/hide UI elements based on role
        updateUIForRole(profile.role);

        console.log('? User profile loaded successfully');
    } catch (error) {
        console.error('? Error fetching user profile:', error);
        // Default to admin role if fetch fails
        currentUserRole = 'admin';
        updateUIForRole('admin');
        console.log('?? Defaulted to admin role due to error');
    }
}

// Update UI based on user role.
//
// Both tenant roles configure and run work. Tenant integrations and user
// management remain superadmin-only.
function updateUIForRole(role) {
    const isSuperadmin = role === 'super_admin';
    const createAgentBtn = document.getElementById('create-agent-btn');
    const createTaskBtn = document.getElementById('create-task-btn');
    const settingsBtn = document.getElementById('settings-btn');
    const navTasksBtn = document.getElementById('nav-tasks-btn');

    document.body.classList.toggle('role-admin', !isSuperadmin);
    document.body.classList.toggle('role-superadmin', isSuperadmin);

    if (createAgentBtn) createAgentBtn.style.display = 'inline-flex';
    if (createTaskBtn) createTaskBtn.style.display = 'inline-flex';

    if (settingsBtn) {
        settingsBtn.style.display = isSuperadmin ? 'inline-flex' : 'none';
        if (isSuperadmin && !settingsBtn.dataset.bound) {
            // Guard the binding: updateUIForRole can run more than once per
            // session, and an unguarded listener would stack duplicates.
            settingsBtn.dataset.bound = 'true';
            settingsBtn.addEventListener('click', () => openSettingsModal('onedrive'));
        }
    }

    // Tasks is the run surface: every check is started from a task row. It is
    // therefore the admin's main page, not a superadmin-only one. This reverses
    // an earlier decision made when tasks were pure configuration.
    if (navTasksBtn) navTasksBtn.style.display = '';

    // Tasks remains the admin's daily landing page. A new superadmin starts on
    // Agents so the tenant can be configured for the first time.
    if (typeof showWorkspacePage === 'function') {
        const needsFirstAgent = isSuperadmin && currentAgents.length === 0;
        showWorkspacePage(needsFirstAgent ? 'agents' : 'tasks');
    }

    // The empty state must name the real blocker and the person who can clear
    // it, with no button, rather than offering an action that ends in a 403.
    const emptyState = document.getElementById('empty-state');
    if (emptyState) {
        const heading = emptyState.querySelector('h3');
        const body = emptyState.querySelector('p');
        const cta = emptyState.querySelector('button');
        if (heading) heading.textContent = 'No agents yet';
        if (body) body.textContent = 'An agent holds the standards to check against. Create one, then add a task to it on the Tasks page.';
        if (cta) cta.style.display = '';
    }
}

// Settings Modal Functions
function openSettingsModal(tabName = 'onedrive') {
    const modal = document.getElementById('settings-modal');
    modal.style.display = 'block';

    // Switch to specified tab
    switchSettingsTab(tabName);

    // Load content based on tab
    if (tabName === 'users') {
        loadUsers();
    } else if (tabName === 'codex') {
        loadCodexIntegration();
    } else if (tabName === 'onedrive') {
        // Load OneDrive connections list
        if (typeof loadOnedriveConnections === 'function') {
            loadOnedriveConnections();
        }
        // Initialize connections management
        if (typeof initOnedriveConnectionsManagement === 'function') {
            initOnedriveConnectionsManagement();
        }
    }

    // Setup user form submission
    const form = document.getElementById('create-user-form');
    form.onsubmit = async (e) => {
        e.preventDefault();
        await createNewUser();
    };

    // Setup tab switching
    const tabButtons = modal.querySelectorAll('.settings-tab');
    tabButtons.forEach(btn => {
        btn.onclick = () => {
            const tab = btn.getAttribute('data-tab');
            switchSettingsTab(tab);
            if (tab === 'users') {
                loadUsers();
            } else if (tab === 'codex') {
                loadCodexIntegration();
            } else if (tab === 'onedrive') {
                // Load OneDrive connections
                if (typeof loadOnedriveConnections === 'function') {
                    loadOnedriveConnections();
                }
            }
        };
    });

    // Setup close button
    const closeBtn = modal.querySelector('.close');
    if (closeBtn) {
        closeBtn.onclick = closeSettingsModal;
    }
}

function closeSettingsModal() {
    const modal = document.getElementById('settings-modal');
    if (modal) modal.style.display = 'none';
}

function switchSettingsTab(tabName) {
    console.log(`Switching to tab: ${tabName}`);

    // Update tab buttons
    const tabButtons = document.querySelectorAll('.settings-tab');
    tabButtons.forEach(btn => {
        if (btn.getAttribute('data-tab') === tabName) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    // Update tab content
    const tabContents = document.querySelectorAll('.settings-tab-content');
    tabContents.forEach(content => {
        content.style.display = 'none';
    });

    const activeTab = document.getElementById(`${tabName}-tab`);
    if (activeTab) {
        activeTab.style.display = 'block';
        console.log(`✅ ${tabName} tab is now visible`);
    } else {
        console.error(`❌ Tab element not found: ${tabName}-tab`);
    }
}

function isUserManagementModalOpen() {
    const modal = document.getElementById('settings-modal');
    const usersTab = document.getElementById('users-tab');
    return modal && modal.style.display === 'block' && usersTab && usersTab.style.display !== 'none';
}

function setButtonLoading(button, isLoading, label) {
    if (!button) {
        return;
    }

    if (isLoading) {
        if (!button.dataset.originalText) {
            button.dataset.originalText = button.textContent;
        }
        if (label) {
            button.textContent = label;
        }
        button.classList.add('is-loading');
        button.disabled = true;
        return;
    }

    button.classList.remove('is-loading');
    button.disabled = false;
    if (button.dataset.originalText) {
        button.textContent = button.dataset.originalText;
        delete button.dataset.originalText;
    }
}

async function loadUsers() {
    try {
        const { data: { session } } = await supabaseClient.auth.getSession();
        if (!session) throw new Error('Not authenticated');

        const response = await fetch(`${API_URL}/api/users`, {
            headers: {
                'Authorization': `Bearer ${session.access_token}`
            }
        });

        if (!response.ok) {
            throw new Error('Failed to load users');
        }

        const users = await response.json();
        displayUsers(users);
    } catch (error) {
        console.error('Error loading users:', error);
        customAlert('Failed to load users: ' + error.message, 'Error');
    }
}

function displayUsers(users) {
    const usersList = document.getElementById('users-list');

    if (!users || users.length === 0) {
        usersList.innerHTML = '<p style="color: var(--text-muted); text-align: center; padding: 20px;">No users found</p>';
        return;
    }

    usersList.innerHTML = users.map(user => `
        <div class="user-item">
            <div class="user-item-info">
                <div class="user-item-email">${escapeHtml(user.email)}</div>
                <div class="user-item-meta">
                    <span class="user-item-badge ${user.role.replace('_', '-')}">${user.role === 'super_admin' ? 'Super Admin' : 'Admin'}</span>
                    <span>Created ${timeAgo(user.created_at)}</span>
                    ${user.display_name ? `<span>${escapeHtml(user.display_name)}</span>` : ''}
                </div>
            </div>
            <div class="user-item-actions">
                ${user.id !== currentUser.id ? `<button class="btn btn-danger btn-small" onclick="deleteUser('${user.id}', '${escapeHtml(user.email)}', this)">Delete</button>` : '<span style="color: var(--text-muted); font-size: 12px;">You</span>'}
            </div>
        </div>
    `).join('');
}

async function createNewUser() {
    const email = document.getElementById('new-user-email').value.trim();
    const displayName = document.getElementById('new-user-display-name').value.trim();
    const role = document.getElementById('new-user-role').value;

    if (!email) {
        await customAlert('Email is required', 'Validation Error');
        return;
    }

    const submitBtn = document.querySelector('#create-user-form button[type="submit"]');
    setButtonLoading(submitBtn, true, 'Creating...');

    try {
        const { data: { session } } = await supabaseClient.auth.getSession();
        if (!session) throw new Error('Not authenticated');

        const response = await fetch(`${API_URL}/api/users`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${session.access_token}`
            },
            body: JSON.stringify({
                email,
                display_name: displayName,
                role
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to create user');
        }

        closeSettingsModal();
        await customAlert('User created. Temporary password emailed.', 'Success');

        // Clear form
        document.getElementById('create-user-form').reset();

        // Reload users list
        await loadUsers();
    } catch (error) {
        console.error('Error creating user:', error);
        await customAlert('Failed to create user: ' + error.message, 'Error');
    } finally {
        setButtonLoading(submitBtn, false);
    }
}

async function deleteUser(userId, userEmail, buttonEl) {
    const wasOpen = isUserManagementModalOpen();
    if (wasOpen) {
        closeSettingsModal();
    }

    const confirmed = await customConfirm(
        `Are you sure you want to delete user "${userEmail}"? This action cannot be undone.`,
        'Delete User'
    );

    if (!confirmed) {
        if (wasOpen) {
            openUserManagementModal();
        }
        return;
    }

    setButtonLoading(buttonEl, true, 'Deleting...');

    try {
        const { data: { session } } = await supabaseClient.auth.getSession();
        if (!session) throw new Error('Not authenticated');

        const response = await fetch(`${API_URL}/api/users/${userId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${session.access_token}`
            }
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to delete user');
        }

        await customAlert('User deleted successfully!', 'Success');

        // Reload users list
        await loadUsers();
    } catch (error) {
        console.error('Error deleting user:', error);
        await customAlert('Failed to delete user: ' + error.message, 'Error');
    } finally {
        setButtonLoading(buttonEl, false);
    }
}

// Make deleteUser available globally
window.deleteUser = deleteUser;

// Close settings modal when clicking outside
window.onclick = function(event) {
    const settingsModal = document.getElementById('settings-modal');
    if (event.target === settingsModal) {
        closeSettingsModal();
    }
};

// OneDrive Base Path Management
async function loadOneDriveBasePath() {
    try {
        const { data: profile, error } = await supabaseClient
            .from('profiles')
            .select('onedrive_base_path')
            .eq('id', currentUser.id)
            .single();

        if (error) {
            console.error('Error loading base path:', error);
            return;
        }

        const basePath = profile?.onedrive_base_path;
        const basePathInput = document.getElementById('onedrive-base-path');
        const currentPathDisplay = document.getElementById('current-path-display');
        const currentBasePathDiv = document.getElementById('current-base-path');

        if (basePath) {
            // Set input value
            if (basePathInput) basePathInput.value = basePath;
            
            // Show current path
            if (currentPathDisplay) currentPathDisplay.textContent = basePath;
            if (currentBasePathDiv) currentBasePathDiv.style.display = 'block';
        } else {
            // No base path set
            if (basePathInput) basePathInput.value = '';
            if (currentBasePathDiv) currentBasePathDiv.style.display = 'none';
        }
    } catch (error) {
        console.error('Error in loadOneDriveBasePath:', error);
    }
}

async function saveOneDriveBasePath(basePath) {
    try {
        // Validate path starts with /
        if (basePath && !basePath.startsWith('/')) {
            await customAlert('Base path must start with / (e.g., /Documents/TaskChecker)', 'Invalid Path');
            return;
        }

        // Update in database
        const { error } = await supabaseClient
            .from('profiles')
            .update({ onedrive_base_path: basePath })
            .eq('id', currentUser.id);

        if (error) {
            console.error('Error saving base path:', error);
            await customAlert('Failed to save base path: ' + error.message, 'Error');
            return;
        }

        // Update display
        const currentPathDisplay = document.getElementById('current-path-display');
        const currentBasePathDiv = document.getElementById('current-base-path');

        if (basePath) {
            if (currentPathDisplay) currentPathDisplay.textContent = basePath;
            if (currentBasePathDiv) currentBasePathDiv.style.display = 'block';
            await customAlert('Base folder path saved successfully!', 'Success');
        } else {
            if (currentBasePathDiv) currentBasePathDiv.style.display = 'none';
            await customAlert('Base folder path cleared successfully!', 'Success');
        }
    } catch (error) {
        console.error('Error in saveOneDriveBasePath:', error);
        await customAlert('Failed to save base path. Please try again.', 'Error');
    }
}

// Setup base path form handlers
function setupBasePathHandlers() {
    const basePathForm = document.getElementById('base-path-form');
    const clearBasePathBtn = document.getElementById('clear-base-path-btn');

    if (basePathForm) {
        basePathForm.onsubmit = async (e) => {
            e.preventDefault();
            const basePathInput = document.getElementById('onedrive-base-path');
            const basePath = basePathInput?.value?.trim();
            await saveOneDriveBasePath(basePath);
        };
    }

    if (clearBasePathBtn) {
        clearBasePathBtn.onclick = async () => {
            const confirmed = await customConfirm(
                'Are you sure you want to clear the base folder path?',
                'Clear Base Path'
            );
            
            if (confirmed) {
                const basePathInput = document.getElementById('onedrive-base-path');
                if (basePathInput) basePathInput.value = '';
                await saveOneDriveBasePath('');
            }
        };
    }
}

// Make functions globally available
window.loadOneDriveBasePath = loadOneDriveBasePath;
window.saveOneDriveBasePath = saveOneDriveBasePath;
window.setupBasePathHandlers = setupBasePathHandlers;

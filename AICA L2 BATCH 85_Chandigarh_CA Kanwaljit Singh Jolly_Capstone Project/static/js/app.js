// Main App Initialization

document.addEventListener('DOMContentLoaded', async () => {
    console.log('🚀 Task Checker Agent Platform starting...');

    try {
        // Initialize authentication
        await initAuth();

        console.log('✅ App initialized successfully');
    } catch (error) {
        console.error('❌ App initialization error:', error);

        // Show error screen
        document.getElementById('loading-screen').innerHTML = `
            <div style="text-align: center; padding: 40px;">
                <h2 style="color: white; margin-bottom: 16px;">⚠️ Initialization Error</h2>
                <p style="color: white; margin-bottom: 24px;">${escapeHtml(error.message)}</p>
                <button class="btn btn-primary" onclick="location.reload()">
                    Reload Page
                </button>
            </div>
        `;
    }
});

// Global error handler
window.addEventListener('error', (event) => {
    console.error('Global error:', event.error);
});

// Global unhandled promise rejection handler
window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled promise rejection:', event.reason);
});

// Utility: Show notification
function showNotification(message, type = 'info') {
    // Simple console log for now - could be enhanced with toast notifications
    console.log(`[${type.toUpperCase()}] ${message}`);
}

// Utility: Format date
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString();
}

// Utility: Format time ago
function timeAgo(dateString) {
    const seconds = Math.floor((new Date() - new Date(dateString)) / 1000);

    let interval = seconds / 31536000;
    if (interval > 1) return Math.floor(interval) + ' years ago';

    interval = seconds / 2592000;
    if (interval > 1) return Math.floor(interval) + ' months ago';

    interval = seconds / 86400;
    if (interval > 1) return Math.floor(interval) + ' days ago';

    interval = seconds / 3600;
    if (interval > 1) return Math.floor(interval) + ' hours ago';

    interval = seconds / 60;
    if (interval > 1) return Math.floor(interval) + ' minutes ago';

    return Math.floor(seconds) + ' seconds ago';
}

console.log('📦 App.js loaded');

/**
 * Inline OneDrive explorer used by every agent and task file picker.
 * The configured connection base path is the explorer root.
 */

class FileSelector {
    constructor(containerId, options = {}) {
        this.containerId = containerId;
        this.options = {
            label: options.label || 'Select Files',
            allowMultiple: options.allowMultiple !== false,
            fileTypes: options.fileTypes || [],
            ...options
        };

        this.selectedFiles = [];
        this.currentFolder = null;
        this.baseFolder = '/';
        this.currentConnection = null;
        this.connections = [];
        this.files = [];
        this.requestSequence = 0;
        this.connectionLoadPromise = null;

        this.render();
    }

    async render() {
        const container = document.getElementById(this.containerId);
        if (!container) return;

        container.innerHTML = `
            <div class="file-selector">
                <label class="file-selector-label">${this.escape(this.options.label)}</label>

                <div class="file-selector-step">
                    <label for="${this.containerId}-connection">1. Select OneDrive Account</label>
                    <select id="${this.containerId}-connection" class="file-selector-dropdown">
                        <option value="">Loading connections...</option>
                    </select>
                </div>

                <section id="${this.containerId}-browser" class="drive-explorer" style="display: none;" aria-label="Browse OneDrive files">
                    <div class="drive-explorer-toolbar">
                        <div>
                            <span class="drive-explorer-step">2. Browse and select</span>
                            <p>Open a folder by its name or double-click its row. Check a folder to select everything inside it.</p>
                        </div>
                        <button type="button" class="drive-explorer-refresh">Refresh</button>
                    </div>
                    <nav id="${this.containerId}-breadcrumbs" class="drive-explorer-breadcrumbs" aria-label="Current OneDrive folder"></nav>
                    <div class="drive-explorer-table" role="table" aria-label="OneDrive folder contents">
                        <div class="drive-explorer-header" role="row">
                            <span role="columnheader">Select</span>
                            <span role="columnheader">Name</span>
                            <span class="drive-modified" role="columnheader">Modified</span>
                            <span class="drive-size" role="columnheader">Size</span>
                        </div>
                        <div id="${this.containerId}-items" class="drive-explorer-items" aria-live="polite"></div>
                    </div>
                </section>

                <div id="${this.containerId}-selected" class="selected-files-display" style="display: none;" aria-live="polite">
                    <strong>Selected</strong>
                    <div id="${this.containerId}-selected-list" class="selected-files-list"></div>
                </div>
            </div>
        `;

        this.setupListeners();
        await this.loadConnections();
    }

    escape(value) {
        return String(value ?? '')
            .replaceAll('&', '&amp;')
            .replaceAll('<', '&lt;')
            .replaceAll('>', '&gt;')
            .replaceAll('"', '&quot;')
            .replaceAll("'", '&#039;');
    }

    normalizePath(value) {
        const parts = [];
        String(value || '/').replaceAll('\\', '/').split('/').forEach(part => {
            if (!part || part === '.') return;
            if (part === '..') parts.pop();
            else parts.push(part);
        });
        return '/' + parts.join('/');
    }

    async loadConnections() {
        if (this.connectionLoadPromise) return this.connectionLoadPromise;
        this.connectionLoadPromise = this.fetchConnections();
        try {
            return await this.connectionLoadPromise;
        } finally {
            this.connectionLoadPromise = null;
        }
    }

    async fetchConnections() {
        const dropdown = document.getElementById(this.containerId + '-connection');
        try {
            const token = await getAccessToken();
            const response = await fetch(API_URL + '/api/onedrive/connections', {
                headers: { 'Authorization': 'Bearer ' + token }
            });
            if (!response.ok) throw new Error('Failed to load OneDrive accounts');

            const data = await response.json();
            this.connections = data.connections || [];
            if (dropdown) {
                dropdown.innerHTML = '<option value="">Select OneDrive account...</option>' +
                    this.connections.map(connection =>
                        `<option value="${this.escape(connection.id)}">${this.escape(connection.account_email || connection.account_name)}</option>`
                    ).join('');
            }
        } catch (error) {
            console.error('Error loading OneDrive connections:', error);
            if (dropdown) dropdown.innerHTML = '<option value="">Could not load OneDrive accounts</option>';
        }
    }

    async openConnection(connectionId, preserveSelections = false, targetFolder = null) {
        const connection = this.connections.find(item => String(item.id) === String(connectionId));
        if (!connection) return;

        this.currentConnection = connectionId;
        this.baseFolder = this.normalizePath(connection.base_folder_path || '/');
        if (!preserveSelections) {
            this.selectedFiles = [];
            this.updateSelectedDisplay();
        }

        const browser = document.getElementById(this.containerId + '-browser');
        if (browser) browser.style.display = 'block';
        await this.loadDirectory(targetFolder || this.baseFolder);
    }

    async loadDirectory(folderPath) {
        if (!this.currentConnection) return;
        const sequence = ++this.requestSequence;
        const targetPath = this.normalizePath(folderPath || this.baseFolder);
        this.currentFolder = targetPath;
        this.renderBreadcrumbs();
        this.renderMessage('Loading folder contents…', 'loading');

        try {
            const token = await getAccessToken();
            const url = API_URL + '/api/onedrive/files?recursive=false&connection_id=' +
                encodeURIComponent(this.currentConnection) + '&folder=' + encodeURIComponent(targetPath);
            const response = await fetch(url, {
                headers: { 'Authorization': 'Bearer ' + token }
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(data.error || 'Failed to load folder contents');
            if (sequence !== this.requestSequence) return;

            this.baseFolder = this.normalizePath(data.base_path || this.baseFolder);
            this.currentFolder = this.normalizePath(data.folder_path || targetPath);
            this.files = (data.files || []).filter(item => {
                if (item.isFolder || this.options.fileTypes.length === 0) return true;
                const dot = item.name.lastIndexOf('.');
                const extension = dot >= 0 ? item.name.slice(dot).toLowerCase() : '';
                return this.options.fileTypes.includes(extension);
            }).sort((left, right) => {
                if (Boolean(left.isFolder) !== Boolean(right.isFolder)) return left.isFolder ? -1 : 1;
                return String(left.name).localeCompare(String(right.name), undefined, { sensitivity: 'base' });
            });

            this.renderBreadcrumbs();
            this.renderItems();
        } catch (error) {
            if (sequence !== this.requestSequence) return;
            console.error('Error loading OneDrive folder:', error);
            this.files = [];
            this.renderMessage(error.message || 'Could not load this folder.', 'error');
        }
    }

    renderMessage(message, state) {
        const list = document.getElementById(this.containerId + '-items');
        const table = list?.closest('.drive-explorer-table');
        if (table) table.setAttribute('aria-busy', state === 'loading' ? 'true' : 'false');
        if (list) list.innerHTML = `<p class="drive-explorer-message ${state === 'error' ? 'is-error' : ''}">${this.escape(message)}</p>`;
    }

    renderBreadcrumbs() {
        const container = document.getElementById(this.containerId + '-breadcrumbs');
        if (!container || !this.currentFolder) return;

        const atRoot = this.normalizePath(this.currentFolder) === this.normalizePath(this.baseFolder);
        const table = container.nextElementSibling;
        container.hidden = atRoot;
        table?.classList.toggle('at-root', atRoot);
        if (atRoot) {
            container.innerHTML = '';
            return;
        }

        const baseParts = this.baseFolder.split('/').filter(Boolean);
        const currentParts = this.currentFolder.split('/').filter(Boolean);
        const crumbs = [{ label: baseParts.at(-1) || 'OneDrive', path: this.baseFolder }];
        let path = this.baseFolder === '/' ? '' : this.baseFolder;
        currentParts.slice(baseParts.length).forEach(part => {
            path += '/' + part;
            crumbs.push({ label: part, path: this.normalizePath(path) });
        });

        container.innerHTML = crumbs.map((crumb, index) => {
            const current = index === crumbs.length - 1;
            const item = current
                ? `<span aria-current="location">${this.escape(crumb.label)}</span>`
                : `<button type="button" data-path="${this.escape(crumb.path)}">${this.escape(crumb.label)}</button>`;
            return (index ? '<span class="drive-breadcrumb-separator" aria-hidden="true">/</span>' : '') + item;
        }).join('');
    }

    icon(isFolder) {
        return isFolder
            ? '<svg viewBox="0 0 20 20" aria-hidden="true" focusable="false"><path d="M2.5 5.5h5l1.5 2h8.5v8.5h-15z"/><path d="M2.5 5.5v-2h5l1.5 2"/></svg>'
            : '<svg viewBox="0 0 20 20" aria-hidden="true" focusable="false"><path d="M5 2.5h6l4 4v11H5z"/><path d="M11 2.5v4h4"/></svg>';
    }

    renderItems() {
        const list = document.getElementById(this.containerId + '-items');
        const table = list?.closest('.drive-explorer-table');
        if (!list) return;
        if (table) table.setAttribute('aria-busy', 'false');
        if (!this.files.length) {
            this.renderMessage('This folder is empty.', 'empty');
            return;
        }

        list.innerHTML = this.files.map(item => {
            const path = this.escape(item.path);
            const name = this.escape(item.name);
            const isFolder = Boolean(item.isFolder);
            const checked = this.selectedFiles.includes(item.path) ? 'checked' : '';
            const selectionCells = `<span class="drive-select-cell" role="cell"><input type="checkbox" value="${path}" ${checked} aria-label="Select ${name}"></span>`;
            const nameControl = isFolder
                ? `<button type="button" class="drive-item-name" data-open-path="${path}" title="Open folder">${this.icon(true)}<span>${name}</span></button>`
                : `<span class="drive-item-name">${this.icon(false)}<span>${name}</span></span>`;

            return `<div class="drive-explorer-row ${isFolder ? 'is-folder' : ''}" role="row" data-folder-path="${isFolder ? path : ''}">
                ${selectionCells}
                <span class="drive-name-cell" role="cell">${nameControl}</span>
                <span class="drive-modified" role="cell">${this.escape(this.formatDate(item.lastModified))}</span>
                <span class="drive-size" role="cell">${this.escape(isFolder ? this.itemCount(item.childCount) : this.formatFileSize(item.size))}</span>
            </div>`;
        }).join('');
    }

    itemCount(value) {
        const count = Number(value || 0);
        return count + (count === 1 ? ' item' : ' items');
    }

    handleSelection(input) {
        if (input.checked && !this.selectedFiles.includes(input.value)) {
            if (!this.options.allowMultiple) this.selectedFiles = [];
            this.selectedFiles.push(input.value);
        } else if (!input.checked) {
            this.selectedFiles = this.selectedFiles.filter(path => path !== input.value);
        }
        if (!this.options.allowMultiple) this.renderItems();
        this.updateSelectedDisplay();
    }

    setupListeners() {
        document.getElementById(this.containerId + '-connection')?.addEventListener('change', event => {
            if (event.target.value) this.openConnection(event.target.value);
            else this.reset(false);
        });

        document.querySelector('#' + this.containerId + '-browser .drive-explorer-refresh')?.addEventListener('click', () => {
            this.loadDirectory(this.currentFolder || this.baseFolder);
        });

        document.getElementById(this.containerId + '-breadcrumbs')?.addEventListener('click', event => {
            const button = event.target.closest('button[data-path]');
            if (button) this.loadDirectory(button.dataset.path);
        });

        const items = document.getElementById(this.containerId + '-items');
        items?.addEventListener('change', event => {
            if (event.target.matches('input[type="checkbox"]')) this.handleSelection(event.target);
        });
        items?.addEventListener('click', event => {
            const button = event.target.closest('button[data-open-path]');
            if (button) this.loadDirectory(button.dataset.openPath);
        });
        items?.addEventListener('dblclick', event => {
            if (event.target.closest('input, button')) return;
            const row = event.target.closest('.drive-explorer-row.is-folder');
            if (row?.dataset.folderPath) this.loadDirectory(row.dataset.folderPath);
        });
    }

    updateSelectedDisplay() {
        const selectedDisplay = document.getElementById(this.containerId + '-selected');
        const selectedList = document.getElementById(this.containerId + '-selected-list');
        if (selectedDisplay) selectedDisplay.style.display = this.selectedFiles.length ? 'block' : 'none';

        const renderTags = (list, paths) => {
            if (!list) return;
            list.innerHTML = paths.length ? paths.map(path => {
                const label = this.relativePath(path);
                return `<div class="selected-file-tag" title="${this.escape(path)}"><span>${this.escape(label)}</span>` +
                    `<button type="button" class="remove-file-btn" data-path="${this.escape(path)}" aria-label="Remove ${this.escape(label)}">×</button></div>`;
            }).join('') : '<span class="selected-files-empty">None selected</span>';
            list.querySelectorAll('.remove-file-btn').forEach(button => {
                button.addEventListener('click', () => this.removeFile(button.dataset.path));
            });
        };

        renderTags(selectedList, this.selectedFiles);
    }

    relativePath(path) {
        const base = this.baseFolder === '/' ? '/' : this.baseFolder + '/';
        return path.startsWith(base) ? path.slice(base.length) || path.split('/').pop() : path;
    }

    removeFile(filePath) {
        this.selectedFiles = this.selectedFiles.filter(path => path !== filePath);
        this.renderItems();
        this.updateSelectedDisplay();
    }

    formatDate(value) {
        if (!value) return '—';
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return '—';
        return date.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' });
    }

    formatFileSize(bytes) {
        const size = Number(bytes || 0);
        if (size < 1024) return size + ' B';
        if (size < 1024 * 1024) return (size / 1024).toFixed(size < 10240 ? 1 : 0) + ' KB';
        return (size / (1024 * 1024)).toFixed(1) + ' MB';
    }

    getSelectedFiles() {
        return [...this.selectedFiles];
    }

    setSelectedFiles(files) {
        this.selectedFiles = Array.isArray(files) ? [...files] : [];
        this.renderItems();
        this.updateSelectedDisplay();
    }

    async preselectFolderAndFiles(folderPath, files) {
        this.selectedFiles = Array.isArray(files) ? [...files] : [];
        if (!this.connections.length) await this.loadConnections();

        const connection = this.connections.find(item => item.is_active) || this.connections[0];
        if (!connection) {
            this.updateSelectedDisplay();
            return;
        }

        const dropdown = document.getElementById(this.containerId + '-connection');
        if (dropdown) dropdown.value = connection.id;
        await this.openConnection(connection.id, true, folderPath || connection.base_folder_path || '/');
        this.updateSelectedDisplay();
    }

    async loadFiles(folderPath, connectionId = this.currentConnection) {
        if (connectionId) this.currentConnection = connectionId;
        await this.loadDirectory(folderPath);
    }

    reset(clearAccount = true) {
        this.requestSequence += 1;
        this.selectedFiles = [];
        this.currentFolder = null;
        this.currentConnection = null;
        this.files = [];
        if (clearAccount) {
            const dropdown = document.getElementById(this.containerId + '-connection');
            if (dropdown) dropdown.value = '';
        }
        const browser = document.getElementById(this.containerId + '-browser');
        if (browser) browser.style.display = 'none';
        this.updateSelectedDisplay();
    }
}

window.FileSelector = FileSelector;

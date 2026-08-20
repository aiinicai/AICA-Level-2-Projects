document.addEventListener('DOMContentLoaded', () => {
  // Theme Sync Listener
  window.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'THEME_CHANGE') {
      document.documentElement.setAttribute('data-theme', event.data.theme);
    }
  });

  let allClients = [];

  // DOM Elements
  const clientGrid = document.getElementById('client-grid');
  const inputSearchClient = document.getElementById('input-search-client');

  // Modal Elements
  const modalClient = document.getElementById('modal-client');
  const formClient = document.getElementById('form-client');
  const modalClientTitle = document.getElementById('modal-client-title');
  const inputClientId = document.getElementById('input-client-id');
  const inputClientName = document.getElementById('input-client-name');
  const inputClientTradeName = document.getElementById('input-client-trade-name');
  const inputClientGstin = document.getElementById('input-client-gstin');
  const selectClientStatus = document.getElementById('select-client-status');
  const btnOpenAddClientModal = document.getElementById('btn-open-add-client-modal');
  const btnCloseClientModal = document.getElementById('btn-close-client-modal');

  // --- CLIENT DIRECTORY FUNCTIONS ---
  async function loadClients() {
    try {
      const res = await fetch('/api/gst_tool/clients');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      allClients = data.clients || [];
      renderClientGrid(allClients);
    } catch (err) {
      console.error('Failed to load clients:', err);
      if (clientGrid) {
        clientGrid.innerHTML = `<div style="color:var(--danger-text); padding:1rem;">Error loading clients from database.</div>`;
      }
    }
  }

  function renderClientGrid(clients) {
    if (!clientGrid) return;
    clientGrid.innerHTML = '';

    const searchTerm = inputSearchClient ? inputSearchClient.value.toLowerCase().trim() : '';
    const filtered = clients.filter(
      (c) =>
        c.name.toLowerCase().includes(searchTerm) ||
        (c.trade_name && c.trade_name.toLowerCase().includes(searchTerm)) ||
        c.gstin.toLowerCase().includes(searchTerm)
    );

    if (filtered.length === 0) {
      clientGrid.innerHTML = `
        <div style="grid-column: 1/-1; text-align: center; padding: 3rem 1rem; color: var(--text-muted); background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 14px;">
          No client profiles found. Click "Add New Client" to register a client profile.
        </div>
      `;
      return;
    }

    filtered.forEach((client) => {
      const card = document.createElement('div');
      card.className = 'client-card';

      const statusBadge = client.status === 'Active'
        ? `<span class="badge badge-success">Active</span>`
        : `<span class="badge badge-danger">Inactive</span>`;

      card.innerHTML = `
        <div>
          <div class="client-card-header">
            <div style="width: 100%;">
              <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px;">
                <div class="client-name">${client.name}</div>
                ${statusBadge}
              </div>
              <div style="font-size: 0.825rem; color: var(--text-muted); margin-bottom: 8px;">
                Trade Name: <strong>${client.trade_name || client.name}</strong>
              </div>
              <span class="gstin-badge">${client.gstin}</span>
            </div>
          </div>
        </div>
        <div class="client-card-actions" style="margin-top: 1.25rem;">
          <div>
            <button class="btn-secondary btn-sm btn-edit-client" data-id="${client.id}">Edit</button>
            <button class="btn-secondary btn-sm btn-delete-client" data-id="${client.id}" style="color:var(--danger-text);">Delete</button>
          </div>
          <button class="btn-primary btn-sm btn-launch-workspace" data-id="${client.id}">
            Launch Workspace &nearr;
          </button>
        </div>
      `;

      // Launch Workspace in NEW Tab
      card.querySelector('.btn-launch-workspace')?.addEventListener('click', () => {
        window.open(`/modules/gst_tool/workspace.html?client_id=${client.id}`, '_blank');
      });

      card.querySelector('.btn-edit-client')?.addEventListener('click', () => {
        openEditClientModal(client);
      });

      card.querySelector('.btn-delete-client')?.addEventListener('click', async () => {
        if (confirm(`Delete client "${client.name}" (${client.gstin}) and all associated GST data?`)) {
          await deleteClient(client.id);
        }
      });

      clientGrid.appendChild(card);
    });
  }

  if (inputSearchClient) {
    inputSearchClient.addEventListener('input', () => renderClientGrid(allClients));
  }

  // --- MODAL DIALOG FUNCTIONS ---
  function openAddClientModal() {
    if (modalClientTitle) modalClientTitle.textContent = 'Add New Client Profile';
    if (inputClientId) inputClientId.value = '';
    if (inputClientName) inputClientName.value = '';
    if (inputClientTradeName) inputClientTradeName.value = '';
    if (inputClientGstin) inputClientGstin.value = '';
    if (selectClientStatus) selectClientStatus.value = 'Active';
    if (modalClient) modalClient.classList.add('active');
  }

  function openEditClientModal(client) {
    if (modalClientTitle) modalClientTitle.textContent = 'Edit Client Profile';
    if (inputClientId) inputClientId.value = client.id.toString();
    if (inputClientName) inputClientName.value = client.name;
    if (inputClientTradeName) inputClientTradeName.value = client.trade_name || '';
    if (inputClientGstin) inputClientGstin.value = client.gstin;
    if (selectClientStatus) selectClientStatus.value = client.status || 'Active';
    if (modalClient) modalClient.classList.add('active');
  }

  function closeClientModal() {
    if (modalClient) modalClient.classList.remove('active');
  }

  if (btnOpenAddClientModal) btnOpenAddClientModal.addEventListener('click', openAddClientModal);
  if (btnCloseClientModal) btnCloseClientModal.addEventListener('click', closeClientModal);

  if (formClient) {
    formClient.addEventListener('submit', async (e) => {
      e.preventDefault();
      const id = inputClientId ? inputClientId.value : '';
      const name = inputClientName ? inputClientName.value.trim() : '';
      const tradeName = inputClientTradeName ? inputClientTradeName.value.trim() || name : name;
      const gstin = inputClientGstin ? inputClientGstin.value.trim().toUpperCase() : '';
      const status = selectClientStatus ? selectClientStatus.value : 'Active';

      try {
        if (id) {
          const res = await fetch(`/api/gst_tool/clients/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, trade_name: tradeName, gstin, status })
          });
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
        } else {
          const res = await fetch('/api/gst_tool/clients', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, trade_name: tradeName, gstin, status })
          });
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
        }

        closeClientModal();
        await loadClients();
      } catch (err) {
        alert(`Failed to save client profile: ${err.message}`);
      }
    });
  }

  async function deleteClient(id) {
    try {
      const res = await fetch(`/api/gst_tool/clients/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await loadClients();
    } catch (err) {
      alert(`Failed to delete client: ${err.message}`);
    }
  }

  // Initial Load
  loadClients();
});

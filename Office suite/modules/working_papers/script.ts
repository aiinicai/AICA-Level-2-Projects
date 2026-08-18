interface ClientItem {
  id: number;
  name: string;
  trade_name: string;
  gstin: string;
  status: string;
  created_at: string;
}

document.addEventListener('DOMContentLoaded', () => {
  // Theme Sync Listener
  window.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'THEME_CHANGE') {
      document.documentElement.setAttribute('data-theme', event.data.theme);
    }
  });

  let allClients: ClientItem[] = [];

  // DOM Elements
  const clientGrid = document.getElementById('client-grid') as HTMLElement;
  const inputSearchClient = document.getElementById('input-search-client') as HTMLInputElement;

  // Modal Elements
  const modalClient = document.getElementById('modal-client') as HTMLElement;
  const formClient = document.getElementById('form-client') as HTMLFormElement;
  const modalClientTitle = document.getElementById('modal-client-title') as HTMLElement;
  const inputClientId = document.getElementById('input-client-id') as HTMLInputElement;
  const inputClientName = document.getElementById('input-client-name') as HTMLInputElement;
  const btnOpenAddClientModal = document.getElementById('btn-open-add-client-modal') as HTMLButtonElement;
  const btnCloseClientModal = document.getElementById('btn-close-client-modal') as HTMLButtonElement;

  // --- CLIENT DIRECTORY FUNCTIONS ---
  async function loadClients() {
    try {
      const res = await fetch('/api/gst_tool/clients');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      allClients = data.clients || [];
      renderClientGrid(allClients);
    } catch (err) {
      console.error('Failed to load clients from GST Tool backend:', err);
      allClients = [
        { id: 1, name: "Acme Enterprises Private Limited", trade_name: "Acme Enterprises Private Limited", gstin: "27AAAAA0000A1Z5", status: "Active", created_at: new Date().toISOString() },
        { id: 2, name: "Tata Consultancy Services Limited", trade_name: "Tata Consultancy Services Limited", gstin: "27AAACT2727Q1ZW", status: "Active", created_at: new Date().toISOString() }
      ];
      renderClientGrid(allClients);
    }
  }

  function renderClientGrid(clients: ClientItem[]) {
    if (!clientGrid) return;
    clientGrid.innerHTML = '';

    const searchTerm = inputSearchClient ? inputSearchClient.value.toLowerCase().trim() : '';
    const filtered = clients.filter((c) => c.name.toLowerCase().includes(searchTerm));

    if (filtered.length === 0) {
      clientGrid.innerHTML = `
        <div style="grid-column: 1/-1; text-align: center; padding: 3rem 1rem; color: var(--text-muted); background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 14px;">
          No entity profiles found. Click "Add New Entity" to register an entity name.
        </div>
      `;
      return;
    }

    filtered.forEach((client) => {
      const card = document.createElement('div');
      card.className = 'client-card';

      card.innerHTML = `
        <div>
          <div class="client-card-header">
            <div style="width: 100%;">
              <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px;">
                <div class="client-name">${client.name}</div>
                <span class="badge badge-success">Active</span>
              </div>
            </div>
          </div>
        </div>
        <div class="client-card-actions" style="margin-top: 1.25rem;">
          <div>
            <button class="btn-secondary btn-sm btn-edit-client" data-id="${client.id}">Rename</button>
            <button class="btn-secondary btn-sm btn-delete-client" data-id="${client.id}" style="color:var(--danger-text);">Delete</button>
          </div>
          <button class="btn-primary btn-sm btn-launch-workspace" data-id="${client.id}">
            Launch Workspace &nearr;
          </button>
        </div>
      `;

      // Launch Workspace in NEW Tab
      card.querySelector('.btn-launch-workspace')?.addEventListener('click', () => {
        window.open(`/modules/working_papers/workspace.html?client_id=${client.id}`, '_blank');
      });

      card.querySelector('.btn-edit-client')?.addEventListener('click', () => {
        openEditClientModal(client);
      });

      card.querySelector('.btn-delete-client')?.addEventListener('click', async () => {
        if (confirm(`Delete entity "${client.name}"?`)) {
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
    if (modalClientTitle) modalClientTitle.textContent = 'Add New Entity';
    if (inputClientId) inputClientId.value = '';
    if (inputClientName) inputClientName.value = '';
    modalClient.classList.add('active');
  }

  function openEditClientModal(client: ClientItem) {
    if (modalClientTitle) modalClientTitle.textContent = 'Rename Entity';
    if (inputClientId) inputClientId.value = client.id.toString();
    if (inputClientName) inputClientName.value = client.name;
    modalClient.classList.add('active');
  }

  function closeClientModal() {
    modalClient.classList.remove('active');
  }

  if (btnOpenAddClientModal) btnOpenAddClientModal.addEventListener('click', openAddClientModal);
  if (btnCloseClientModal) btnCloseClientModal.addEventListener('click', closeClientModal);

  if (formClient) {
    formClient.addEventListener('submit', async (e) => {
      e.preventDefault();
      const id = inputClientId.value;
      const name = inputClientName.value.trim();
      if (!name) return;

      const tradeName = name;
      const autoGstin = id ? undefined : `27NOGSTIN${Math.floor(1000 + Math.random() * 9000)}A1Z5`;

      try {
        if (id) {
          const res = await fetch(`/api/gst_tool/clients/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, trade_name: tradeName })
          });
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
        } else {
          const res = await fetch('/api/gst_tool/clients', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, trade_name: tradeName, gstin: autoGstin, status: 'Active' })
          });
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
        }

        closeClientModal();
        await loadClients();
      } catch (err) {
        alert(`Failed to save entity profile: ${(err as Error).message}`);
      }
    });
  }

  async function deleteClient(id: number) {
    try {
      const res = await fetch(`/api/gst_tool/clients/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await loadClients();
    } catch (err) {
      alert(`Failed to delete entity: ${(err as Error).message}`);
    }
  }

  // Initial Load
  loadClients();
});

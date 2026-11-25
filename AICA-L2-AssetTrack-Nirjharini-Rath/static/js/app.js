let currentTab = "dashboard";
let currentCategoryFilter = "";
let cachedVendors = [];

function showToast(msg) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 3000);
}

function openModal(id) { document.getElementById(id).classList.add("open"); }
function closeModal(id) { document.getElementById(id).classList.remove("open"); }

async function api(url, options = {}) {
  const res = await fetch(url, options);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

async function uploadPhoto(inputId) {
  const inp = document.getElementById(inputId);
  if (!inp || !inp.files || !inp.files[0]) return null;
  const fd = new FormData();
  fd.append("file", inp.files[0]);
  const res = await api("/api/uploads", { method: "POST", body: fd });
  return res.url;
}

function switchTab(tab) {
  currentTab = tab;
  document.querySelectorAll(".tab-view").forEach((el) => (el.style.display = "none"));
  document.getElementById(`view-${tab}`).style.display = "block";
  document.querySelectorAll("[data-tab]").forEach((btn) => btn.classList.toggle("active", btn.dataset.tab === tab));
  const titles = { dashboard: "Dashboard", assets: "Fixed Assets", maintenance: "Maintenance Log", vendors: "Vendors", stationery: "Stationery & Stock" };
  document.getElementById("pageTitle").textContent = titles[tab] || "Dashboard";
  if (tab === "dashboard") loadDashboard();
  if (tab === "assets") loadAssets();
  if (tab === "maintenance") loadMaintenance();
  if (tab === "vendors") loadVendors();
  if (tab === "stationery") loadStationery();
}

async function loadDashboard() {
  const data = await api("/api/dashboard");
  const k = data.kpis;
  document.getElementById("kpiGrid").innerHTML = `
    <div class="kpi-card"><div class="kpi-label">Total Fixed Assets</div><div class="kpi-value">${k.total_assets}</div><div class="kpi-sub">${k.operational_assets} operational · ${k.attention_assets} attention</div></div>
    <div class="kpi-card"><div class="kpi-label">Portfolio Value</div><div class="kpi-value">${Number(k.total_value).toLocaleString()}</div><div class="kpi-sub">Local SQLite inventory</div></div>
    <div class="kpi-card"><div class="kpi-label">Open Maintenance</div><div class="kpi-value">${k.open_maintenance}</div><div class="kpi-sub">Scheduled &amp; in progress</div></div>
    <div class="kpi-card"><div class="kpi-label">Low-Stock Items</div><div class="kpi-value" style="color:${k.low_stock_count > 0 ? 'var(--red)' : 'var(--green)'}">${k.low_stock_count}</div><div class="kpi-sub">Below reorder threshold</div></div>
  `;

  const mAlerts = data.maintenance_alerts || [];
  document.getElementById("maintAlertSummary").textContent = `${mAlerts.length} due`;
  document.getElementById("maintAlertsList").innerHTML = mAlerts.length
    ? mAlerts.map((a) => `
        <div class="alert-item">
          <div>
            <span class="badge ${a.severity === "RED" ? "badge-red" : a.severity === "ORANGE" ? "badge-orange" : "badge-yellow"}">${a.label}</span>
            <strong style="margin-left:8px;"><a href="/assets/${a.asset_id}" style="color:inherit;text-decoration:none;">${a.asset_name}</a></strong> (${a.asset_tag}) · ${a.location}
            <div style="font-size:12px;color:var(--muted);">Due: ${a.next_maintenance_date} · Vendor: ${a.vendor_name || "Unassigned"}</div>
          </div>
          ${a.wa_url ? `<a class="btn btn-sm btn-wa" href="${a.wa_url}" target="_blank" rel="noopener">💬 WhatsApp Link ↗</a>` : ""}
        </div>`).join("")
    : `<div style="color:var(--muted);font-size:13.5px;">No upcoming or overdue maintenance items.</div>`;

  const sAlerts = data.low_stock_alerts || [];
  document.getElementById("stockAlertSummary").textContent = `${sAlerts.length} low`;
  document.getElementById("stockAlertsList").innerHTML = sAlerts.length
    ? sAlerts.map((s) => `
        <div class="alert-item">
          <div>
            <span class="badge badge-red">LOW STOCK</span>
            <strong style="margin-left:8px;">${s.item_name}</strong>
            <div style="font-size:12px;color:var(--muted);">${s.current_stock} ${s.unit} left (min ${s.minimum_reorder_threshold}) · ${s.vendor_name || "No Vendor"}</div>
          </div>
          ${s.wa_url ? `<a class="btn btn-sm btn-wa" href="${s.wa_url}" target="_blank" rel="noopener">💬 Reorder on WhatsApp ↗</a>` : ""}
        </div>`).join("")
    : `<div style="color:var(--muted);font-size:13.5px;">All stationery stock levels are healthy.</div>`;
}

async function refreshVendorSelects() {
  const res = await api("/api/vendors");
  cachedVendors = res.items;
  const opts = `<option value="">— None —</option>` + cachedVendors.map((v) => `<option value="${v.id}">${v.name}</option>`).join("");
  ["assetVendorId", "maintVendorId", "stockVendorId"].forEach((id) => { const el = document.getElementById(id); if (el) el.innerHTML = opts; });
}

function setCategoryFilter(cat) {
  currentCategoryFilter = cat;
  document.querySelectorAll("#categoryFilterPills .pill").forEach((p) => p.classList.toggle("active", p.dataset.cat === cat));
  loadAssets();
}

async function quickStatus(id, st) {
  await api(`/api/assets/${id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status: st }) });
  showToast(`Status updated to ${st}`);
}

async function loadAssets() {
  const q = document.getElementById("assetSearch")?.value || "";
  const st = document.getElementById("assetStatusFilter")?.value || "";
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (st) params.set("status", st);
  if (currentCategoryFilter) params.set("category", currentCategoryFilter);
  const res = await api(`/api/assets?${params.toString()}`);
  const statuses = ["OPERATIONAL", "NEEDS_REPAIR", "IN_MAINTENANCE", "DECOMMISSIONED"];

  document.getElementById("assetsTableBody").innerHTML = res.items.length
    ? res.items.map((a) => `
        <tr class="clickable-row" onclick="if(!event.target.closest('select,button,a')) window.location.href='/assets/${a.id}'">
          <td>${a.photos && a.photos[0] ? `<img src="${a.photos[0]}" class="thumb" alt="asset" />` : "—"}</td>
          <td><a href="/assets/${a.id}" style="color:var(--primary);text-decoration:none;font-weight:700;"><code>${a.asset_tag}</code></a></td>
          <td><strong>${a.name}</strong></td>
          <td>${a.category}</td>
          <td>${a.location}</td>
          <td>${a.vendor_name || "-"}</td>
          <td>${a.next_maintenance_date || "-"}</td>
          <td><select class="input" style="padding:5px 8px;font-size:12px;" onchange="quickStatus('${a.id}', this.value)">${statuses.map((s) => `<option value="${s}" ${a.status === s ? "selected" : ""}>${s}</option>`).join("")}</select></td>
          <td style="white-space:nowrap;">
            <a class="btn btn-sm" href="/qr/print?asset_id=${a.id}" target="_blank" rel="noopener">🏷️ QR</a>
            ${a.wa_url ? `<a class="btn btn-sm btn-wa" href="${a.wa_url}" target="_blank" rel="noopener">💬</a>` : ""}
            <button class="btn btn-sm btn-danger" onclick="deleteAsset('${a.id}')">Delete</button>
          </td>
        </tr>`).join("")
    : `<tr><td colspan="9" style="text-align:center;color:var(--muted);">No assets found.</td></tr>`;

  document.getElementById("assetsCardGrid").innerHTML = res.items.map((a) => `
    <div class="m-card" onclick="if(!event.target.closest('select,button,a')) window.location.href='/assets/${a.id}'">
      <div class="m-card-top"><div><code>${a.asset_tag}</code><div style="font-weight:700;">${a.name}</div></div><span class="badge badge-slate">${a.status}</span></div>
      <div class="m-card-meta">${a.location} · ${a.category}</div>
      <div class="m-card-actions"><a class="btn btn-sm" href="/qr/print?asset_id=${a.id}" target="_blank" rel="noopener">🏷️ QR</a><a class="btn btn-sm btn-primary" href="/assets/${a.id}">Details</a></div>
    </div>`).join("");
}

async function openAssetModal() {
  await refreshVendorSelects();
  document.getElementById("assetForm").reset();
  openModal("assetModal");
}

async function submitAssetForm(e) {
  e.preventDefault();
  const photo = await uploadPhoto("assetPhotoInput");
  const costRaw = document.getElementById("assetPurchaseCost").value;
  await api("/api/assets", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      asset_tag: document.getElementById("assetTag").value || null,
      name: document.getElementById("assetName").value,
      category: document.getElementById("assetCategory").value,
      location: document.getElementById("assetLocation").value,
      vendor_id: document.getElementById("assetVendorId").value || null,
      purchase_cost: costRaw ? parseFloat(costRaw) : null,
      purchase_date: document.getElementById("assetPurchaseDate").value || null,
      warranty_end_date: document.getElementById("assetWarrantyEnd").value || null,
      maintenance_cycle: document.getElementById("assetMaintCycle").value,
      photos: photo ? [photo] : [],
      notes: document.getElementById("assetNotes").value || null,
    }),
  });
  closeModal("assetModal");
  showToast("Asset saved & QR ready.");
  currentTab === "assets" ? loadAssets() : loadDashboard();
}

async function deleteAsset(id) {
  if (!confirm("Delete this asset?")) return;
  await api(`/api/assets/${id}`, { method: "DELETE" });
  loadAssets();
}

async function loadMaintenance() {
  const res = await api("/api/maintenance");
  document.getElementById("maintenanceTableBody").innerHTML = res.items.length
    ? res.items.map((m) => `
        <tr>
          <td>${m.photos && m.photos[0] ? `<img src="${m.photos[0]}" class="thumb" alt="maint" />` : "—"}</td>
          <td>${m.scheduled_date}</td>
          <td><strong>${m.asset_name}</strong> <code>${m.asset_tag}</code></td>
          <td>${m.vendor_name || "Independent"}</td>
          <td>${m.description}</td>
          <td>${m.cost != null ? Number(m.cost).toLocaleString() : "-"}</td>
          <td><span class="badge ${m.status === "COMPLETED" ? "badge-green" : "badge-orange"}">${m.status}</span></td>
          <td>
            ${m.status !== "COMPLETED" ? `<button class="btn btn-sm btn-accent" onclick="completeMaint('${m.id}')">✓ Complete</button>` : ""}
            <button class="btn btn-sm btn-danger" onclick="deleteMaint('${m.id}')">Delete</button>
          </td>
        </tr>`).join("")
    : `<tr><td colspan="8" style="text-align:center;color:var(--muted);">No maintenance records yet.</td></tr>`;
}

async function openMaintenanceModal() {
  await refreshVendorSelects();
  const aRes = await api("/api/assets");
  document.getElementById("maintAssetId").innerHTML = aRes.items.map((a) => `<option value="${a.id}">${a.asset_tag} — ${a.name}</option>`).join("");
  document.getElementById("maintenanceForm").reset();
  document.getElementById("maintScheduledDate").value = new Date().toISOString().slice(0, 10);
  openModal("maintenanceModal");
}

async function submitMaintenanceForm(e) {
  e.preventDefault();
  const photo = await uploadPhoto("maintPhotoInput");
  const costRaw = document.getElementById("maintCost").value;
  await api("/api/maintenance", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      asset_id: document.getElementById("maintAssetId").value,
      vendor_id: document.getElementById("maintVendorId").value || null,
      scheduled_date: document.getElementById("maintScheduledDate").value,
      status: document.getElementById("maintStatus").value,
      cost: costRaw ? parseFloat(costRaw) : null,
      description: document.getElementById("maintDescription").value,
      photos: photo ? [photo] : [],
    }),
  });
  closeModal("maintenanceModal");
  loadMaintenance();
  showToast("Maintenance logged.");
}

async function completeMaint(id) {
  await api(`/api/maintenance/${id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status: "COMPLETED", completed_date: new Date().toISOString().slice(0, 10) }) });
  loadMaintenance();
  showToast("Marked completed.");
}

async function deleteMaint(id) {
  if (!confirm("Delete this record?")) return;
  await api(`/api/maintenance/${id}`, { method: "DELETE" });
  loadMaintenance();
}

async function loadVendors() {
  const res = await api("/api/vendors");
  document.getElementById("vendorsTableBody").innerHTML = res.items.length
    ? res.items.map((v) => `
        <tr>
          <td><strong>${v.name}</strong></td>
          <td><span class="badge badge-slate">${v.vendor_type}</span></td>
          <td>${v.contact_person || "-"}</td>
          <td>${v.phone}</td>
          <td>
            ${v.wa_url ? `<a class="btn btn-sm btn-wa" href="${v.wa_url}" target="_blank" rel="noopener">💬 WhatsApp ↗</a>` : ""}
            <button class="btn btn-sm btn-danger" onclick="deleteVendor('${v.id}')">Delete</button>
          </td>
        </tr>`).join("")
    : `<tr><td colspan="5" style="text-align:center;color:var(--muted);">No vendors yet.</td></tr>`;
}

function openVendorModal() { document.getElementById("vendorForm").reset(); openModal("vendorModal"); }

async function submitVendorForm(e) {
  e.preventDefault();
  await api("/api/vendors", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: document.getElementById("vendorName").value,
      vendor_type: document.getElementById("vendorType").value,
      contact_person: document.getElementById("vendorContact").value || null,
      phone: document.getElementById("vendorPhone").value,
      address: document.getElementById("vendorAddress").value || null,
    }),
  });
  closeModal("vendorModal");
  loadVendors();
  showToast("Vendor saved.");
}

async function deleteVendor(id) {
  if (!confirm("Delete this vendor?")) return;
  await api(`/api/vendors/${id}`, { method: "DELETE" });
  loadVendors();
}

async function loadStationery() {
  const res = await api("/api/stationery");
  document.getElementById("stationeryTableBody").innerHTML = res.items.length
    ? res.items.map((s) => `
        <tr>
          <td><strong>${s.item_name}</strong></td>
          <td>${s.category}</td>
          <td><div class="stock-control"><button class="stock-btn" onclick="adjStock('${s.id}', -1)">−</button><strong>${s.current_stock}</strong> ${s.unit}<button class="stock-btn" onclick="adjStock('${s.id}', 1)">+</button></div></td>
          <td>${s.minimum_reorder_threshold} ${s.unit}</td>
          <td>${s.is_low_stock ? '<span class="badge badge-red">REORDER</span>' : '<span class="badge badge-green">OK</span>'}</td>
          <td>${s.vendor_name || "-"}</td>
          <td>
            ${s.wa_url ? `<a class="btn btn-sm btn-wa" href="${s.wa_url}" target="_blank" rel="noopener">💬 Reorder ↗</a>` : ""}
            <button class="btn btn-sm btn-danger" onclick="deleteStationery('${s.id}')">Delete</button>
          </td>
        </tr>`).join("")
    : `<tr><td colspan="7" style="text-align:center;color:var(--muted);">No stationery items yet.</td></tr>`;
}

async function openStationeryModal() { await refreshVendorSelects(); document.getElementById("stationeryForm").reset(); openModal("stationeryModal"); }

async function submitStationeryForm(e) {
  e.preventDefault();
  await api("/api/stationery", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      item_name: document.getElementById("stockName").value,
      category: document.getElementById("stockCategory").value,
      current_stock: parseInt(document.getElementById("stockQty").value, 10),
      unit: document.getElementById("stockUnit").value,
      minimum_reorder_threshold: parseInt(document.getElementById("stockThreshold").value, 10),
      preferred_vendor_id: document.getElementById("stockVendorId").value || null,
    }),
  });
  closeModal("stationeryModal");
  loadStationery();
  showToast("Item saved.");
}

async function adjStock(id, delta) {
  await api(`/api/stationery/${id}/adjust`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ delta }) });
  loadStationery();
}

async function deleteStationery(id) {
  if (!confirm("Delete this item?")) return;
  await api(`/api/stationery/${id}`, { method: "DELETE" });
  loadStationery();
}

document.querySelectorAll("[data-tab]").forEach((btn) => btn.addEventListener("click", () => switchTab(btn.dataset.tab)));
loadDashboard();

// dashboard.js - SOP Editor and PDF Generator

let sopData = {
  title: "Standard Operating Procedure",
  description: "Auto-generated step-by-step documentation.",
  creator: "SOP Builder User",
  date: new Date().toISOString().split('T')[0],
  steps: []
};

// DOM Elements
const stepsListContainer = document.getElementById("sop-steps-list");
const stepsCountEl = document.getElementById("sop-steps-count");
const titleInput = document.getElementById("sop-title-display");
const descInput = document.getElementById("sop-desc-display");
const creatorInput = document.getElementById("sop-creator-display");
const dateInput = document.getElementById("sop-date-display");

const addSectionBtn = document.getElementById("add-section-btn");
const importBtn = document.getElementById("import-btn");
const jsonInput = document.getElementById("json-input");
const exportJsonBtn = document.getElementById("export-json-btn");
const exportPdfBtn = document.getElementById("export-pdf-btn");

// Lightbox Elements
const lightbox = document.getElementById("lightbox");
const lightboxImg = document.getElementById("lightbox-img");
const lightboxCaption = document.getElementById("lightbox-caption");
const lightboxCloseBtn = document.getElementById("lightbox-close-btn");

// Initialize on Load
document.addEventListener("DOMContentLoaded", () => {
  loadData();

  // Bind Navbar actions
  addSectionBtn.addEventListener("click", addSectionNote);
  importBtn.addEventListener("click", () => jsonInput.click());
  jsonInput.addEventListener("change", importJSON);
  exportJsonBtn.addEventListener("click", exportJSON);
  exportPdfBtn.addEventListener("click", exportPDF);

  // Bind Lightbox close
  lightboxCloseBtn.addEventListener("click", closeLightbox);
  lightbox.addEventListener("click", (e) => {
    if (e.target === lightbox) closeLightbox();
  });

  // Bind header changes
  titleInput.addEventListener("input", () => {
    sopData.title = titleInput.value;
    saveData();
  });
  descInput.addEventListener("input", () => {
    sopData.description = descInput.value;
    saveData();
  });
  creatorInput.addEventListener("input", () => {
    sopData.creator = creatorInput.value;
    saveData();
  });
  dateInput.addEventListener("input", () => {
    sopData.date = dateInput.value;
    saveData();
  });
});

// Load from chrome.storage.local
function loadData() {
  chrome.storage.local.get(["docTitle", "docCreator", "docDescription", "steps"], (data) => {
    sopData.title = data.docTitle || "Standard Operating Procedure";
    sopData.description = data.docDescription || "Auto-generated step-by-step documentation.";
    sopData.creator = data.docCreator || "SOP Builder User";
    sopData.date = new Date().toISOString().split('T')[0];
    
    const rawSteps = data.steps || [];
    // Ensure all steps have a type ('step' or 'section')
    sopData.steps = rawSteps.map(step => ({
      type: step.image !== undefined ? 'step' : 'section',
      ...step
    }));

    // Update Header Inputs
    titleInput.value = sopData.title;
    descInput.value = sopData.description;
    creatorInput.value = sopData.creator;
    dateInput.value = sopData.date;

    renderSteps();
  });
}

// Save back to chrome.storage.local
function saveData() {
  chrome.storage.local.set({
    docTitle: sopData.title,
    docDescription: sopData.description,
    docCreator: sopData.creator,
    steps: sopData.steps
  });
  updateStepCountLabel();
}

function updateStepCountLabel() {
  const stepsOnly = sopData.steps.filter(s => s.type === 'step').length;
  stepsCountEl.innerText = `${stepsOnly} Step${stepsOnly === 1 ? "" : "s"}`;
}

// Render steps and sections list
function renderSteps() {
  stepsListContainer.innerHTML = "";

  if (sopData.steps.length === 0) {
    stepsListContainer.innerHTML = `
      <div class="empty-state" id="empty-state">
        <svg viewBox="0 0 24 24" width="48" height="48" fill="currentColor"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-2 10H7v-2h10v2z"/></svg>
        <h3>No Steps Recorded Yet</h3>
        <p>Start a recording from the extension popup to capture steps, or import a saved JSON session.</p>
      </div>
    `;
    updateStepCountLabel();
    return;
  }

  let stepIdxCounter = 1;
  let sectionIdxCounter = 1;

  sopData.steps.forEach((item, index) => {
    const isStep = item.type === 'step';
    const card = document.createElement("div");
    card.className = isStep ? "step-card" : "section-note-card";
    card.dataset.index = index;

    if (isStep) {
      // Step Card HTML template
      card.innerHTML = `
        <div class="card-sidebar">
          <span class="step-badge">Step ${stepIdxCounter++}</span>
          <div class="reorder-actions">
            <button class="reorder-btn move-up-btn" title="Move Up"><svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M7.41 15.41L12 10.83l4.59 4.58L18 14l-6-6-6 6z"/></svg></button>
            <button class="reorder-btn move-down-btn" title="Move Down"><svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6z"/></svg></button>
            <button class="reorder-btn delete-btn" title="Delete Step"><svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg></button>
          </div>
        </div>
        <div class="step-details">
          <input type="text" class="editable-step-title" value="${item.title || ''}" placeholder="Step Heading title">
          <textarea class="editable-step-desc" rows="3" placeholder="Explain the actions taken in this step...">${item.description || ''}</textarea>
        </div>
        <div class="step-screenshot-wrapper">
          ${item.image ? `<img src="${item.image}" alt="${item.title}" class="step-screenshot">` : `<div class="step-screenshot-fallback">No screenshot captured</div>`}
        </div>
      `;

      // Bind screenshot zoom lightbox event
      const imgWrapper = card.querySelector(".step-screenshot-wrapper");
      if (item.image) {
        imgWrapper.addEventListener("click", () => openLightbox(item.image, item.title));
      }
    } else {
      // Section Divider/Note Card HTML template
      card.innerHTML = `
        <div class="card-sidebar">
          <span class="section-badge">Section</span>
          <div class="reorder-actions">
            <button class="reorder-btn move-up-btn" title="Move Up"><svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M7.41 15.41L12 10.83l4.59 4.58L18 14l-6-6-6 6z"/></svg></button>
            <button class="reorder-btn move-down-btn" title="Move Down"><svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6z"/></svg></button>
            <button class="reorder-btn delete-btn" title="Delete Section"><svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg></button>
          </div>
        </div>
        <div class="step-details">
          <input type="text" class="editable-step-title editable-section-title" value="${item.title || ''}" placeholder="Section Title">
          <textarea class="editable-step-desc" rows="3" placeholder="Write section details, observations, or prerequisites...">${item.description || ''}</textarea>
        </div>
      `;
    }

    // Bind Edit Listeners
    const cardTitle = card.querySelector(".editable-step-title");
    const cardDesc = card.querySelector(".editable-step-desc");

    cardTitle.addEventListener("input", () => {
      sopData.steps[index].title = cardTitle.value;
      saveData();
    });

    cardDesc.addEventListener("input", () => {
      sopData.steps[index].description = cardDesc.value;
      saveData();
    });

    // Bind Reordering & Deleting buttons
    card.querySelector(".move-up-btn").addEventListener("click", () => moveStep(index, -1));
    card.querySelector(".move-down-btn").addEventListener("click", () => moveStep(index, 1));
    card.querySelector(".delete-btn").addEventListener("click", () => deleteStep(index));

    stepsListContainer.appendChild(card);
  });

  updateStepCountLabel();
}

// Reordering logic
function moveStep(index, offset) {
  const targetIndex = index + offset;
  if (targetIndex < 0 || targetIndex >= sopData.steps.length) return;

  // Swap elements
  const temp = sopData.steps[index];
  sopData.steps[index] = sopData.steps[targetIndex];
  sopData.steps[targetIndex] = temp;

  saveData();
  renderSteps();

  // Scroll to targeted element after render
  const cards = stepsListContainer.querySelectorAll(".step-card, .section-note-card");
  if (cards[targetIndex]) {
    cards[targetIndex].scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
}

// Delete logic
function deleteStep(index) {
  if (confirm("Are you sure you want to delete this item?")) {
    sopData.steps.splice(index, 1);
    saveData();
    renderSteps();
  }
}

// Section Note generation
function addSectionNote() {
  const newSection = {
    id: Date.now(),
    type: 'section',
    title: "New Section Note",
    description: "Write summary descriptions or divider overview details here..."
  };

  sopData.steps.push(newSection);
  saveData();
  renderSteps();

  // Scroll to bottom
  window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
}

// Lightbox handlers
function openLightbox(src, caption) {
  lightbox.style.display = "block";
  lightboxImg.src = src;
  lightboxCaption.innerText = caption || "";
}

function closeLightbox() {
  lightbox.style.display = "none";
}

// JSON Import
function importJSON(e) {
  const file = e.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = function(evt) {
    try {
      const data = JSON.parse(evt.target.result);
      if (data.title && Array.isArray(data.steps)) {
        sopData = data;
        
        // Sync to storage
        chrome.storage.local.set({
          docTitle: sopData.title,
          docDescription: sopData.description || "",
          docCreator: sopData.creator || "",
          steps: sopData.steps
        }, () => {
          loadData();
          alert("SOP document successfully imported!");
        });
      } else {
        alert("Invalid SOP JSON structure.");
      }
    } catch(err) {
      alert("Error parsing JSON file.");
    }
  };
  reader.readAsText(file);
}

// JSON Export
function exportJSON() {
  const jsonString = JSON.stringify(sopData, null, 2);
  const blob = new Blob([jsonString], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  
  const a = document.createElement("a");
  a.href = url;
  a.download = `${sopData.title.replace(/[^a-z0-9]/gi, '_').toLowerCase()}_sop.json`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// PDF Generation
function exportPDF() {
  const printArea = document.getElementById("sop-print-area");
  
  // Set options for html2pdf
  const filename = `${sopData.title.replace(/[^a-z0-9]/gi, '_').toLowerCase()}.pdf`;
  const opt = {
    margin:       [12, 12, 12, 12], // [top, left, bottom, right] in mm
    filename:     filename,
    image:        { type: 'jpeg', quality: 0.98 },
    html2canvas:  { scale: 2, useCORS: true, logging: false },
    jsPDF:        { unit: 'mm', format: 'a4', orientation: 'portrait' },
    pagebreak:    { mode: ['css', 'legacy'], avoid: ['.step-card', '.section-note-card'] }
  };

  // Temporarily apply print view modifications if necessary,
  // but CSS media queries in dashboard.css handle standard printing perfectly!
  // Start html2pdf generation process
  exportPdfBtn.disabled = true;
  exportPdfBtn.innerText = "Generating PDF...";

  html2pdf().set(opt).from(printArea).save().then(() => {
    exportPdfBtn.disabled = false;
    exportPdfBtn.innerHTML = `
      <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M20 2H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-8.5 7.5c0 .83-.67 1.5-1.5 1.5H9v2H7.5V7H10c.83 0 1.5.67 1.5 1.5v1zm5 2c0 .83-.67 1.5-1.5 1.5h-2.5V7H15c.83 0 1.5.67 1.5 1.5v3zm4-3H19v1h1.5V11H19v2h-1.5V7h3v1.5zM9 10v-1.5h1V10H9zm5.5 2v-3.5h1V12h-1zM4 6H2v14c0 1.1.9 2 2 2h14v-2H4V6z"/></svg>
      <span>Save SOP as PDF</span>
    `;
  }).catch(err => {
    console.error("PDF generation failed:", err);
    alert("Could not generate PDF. Please try again.");
    exportPdfBtn.disabled = false;
    exportPdfBtn.innerHTML = `
      <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M20 2H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-8.5 7.5c0 .83-.67 1.5-1.5 1.5H9v2H7.5V7H10c.83 0 1.5.67 1.5 1.5v1zm5 2c0 .83-.67 1.5-1.5 1.5h-2.5V7H15c.83 0 1.5.67 1.5 1.5v3zm4-3H19v1h1.5V11H19v2h-1.5V7h3v1.5zM9 10v-1.5h1V10H9zm5.5 2v-3.5h1V12h-1zM4 6H2v14c0 1.1.9 2 2 2h14v-2H4V6z"/></svg>
      <span>Save SOP as PDF</span>
    `;
  });
}

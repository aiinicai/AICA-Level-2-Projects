// popup.js - SOP Maker Popup Logic

let state = {
  isRecording: false,
  isPaused: false,
  steps: []
};
let timerInterval = null;

// DOM Elements
const stateDot = document.getElementById("state-dot");
const stateTxt = document.getElementById("state-txt");
const stepsCnt = document.getElementById("steps-cnt");
const timerVal = document.getElementById("timer-val");

const primaryBtn = document.getElementById("primary-btn");
const primaryBtnTxt = document.getElementById("primary-btn-txt");
const secondaryActions = document.getElementById("secondary-actions");
const pauseBtn = document.getElementById("pause-btn");
const pauseBtnTxt = document.getElementById("pause-btn-txt");
const stopBtn = document.getElementById("stop-btn");

const docTitleInput = document.getElementById("doc-title");
const docCreatorInput = document.getElementById("doc-creator");
const settingsSection = document.getElementById("settings-section");
const dashboardBtn = document.getElementById("dashboard-btn");

// Initialize
document.addEventListener("DOMContentLoaded", () => {
  // Load saved metadata defaults
  chrome.storage.local.get(["docTitle", "docCreator"], (result) => {
    if (result.docTitle) docTitleInput.value = result.docTitle;
    if (result.docCreator) docCreatorInput.value = result.docCreator;
  });

  // Save changes to metadata as user types
  docTitleInput.addEventListener("input", () => {
    chrome.storage.local.set({ docTitle: docTitleInput.value });
  });
  docCreatorInput.addEventListener("input", () => {
    chrome.storage.local.set({ docCreator: docCreatorInput.value });
  });

  // Get current status from Background Script
  chrome.runtime.sendMessage({ type: "GET_STATUS" }, (response) => {
    if (response) {
      state = response;
      updateUI();
    }
  });

  // Button Listeners
  primaryBtn.addEventListener("click", startRecording);
  pauseBtn.addEventListener("click", togglePause);
  stopBtn.addEventListener("click", stopRecording);
  dashboardBtn.addEventListener("click", openDashboard);
});

// Watch for status changes in storage
chrome.storage.onChanged.addListener((changes) => {
  if (changes.isRecording || changes.isPaused || changes.steps) {
    chrome.runtime.sendMessage({ type: "GET_STATUS" }, (response) => {
      if (response) {
        state = response;
        updateUI();
      }
    });
  }
});

function updateUI() {
  stepsCnt.innerText = state.steps ? state.steps.length : 0;

  if (state.isRecording) {
    primaryBtn.style.display = "none";
    secondaryActions.style.display = "grid";
    
    // Disable inputs during recording
    docTitleInput.disabled = true;
    docCreatorInput.disabled = true;
    docTitleInput.style.opacity = "0.5";
    docCreatorInput.style.opacity = "0.5";

    if (state.isPaused) {
      stateTxt.innerText = "Paused";
      stateDot.className = "status-dot active-pause";
      pauseBtnTxt.innerText = "Resume";
      pauseBtn.innerHTML = `<svg class="btn-icon" viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M8 5v14l11-7z"/></svg><span>Resume</span>`;
      stopTimer();
    } else {
      stateTxt.innerText = "Recording";
      stateDot.className = "status-dot active-rec";
      pauseBtnTxt.innerText = "Pause";
      pauseBtn.innerHTML = `<svg class="btn-icon" viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg><span>Pause</span>`;
      startTimer();
    }
  } else {
    primaryBtn.style.display = "flex";
    secondaryActions.style.display = "none";
    
    docTitleInput.disabled = false;
    docCreatorInput.disabled = false;
    docTitleInput.style.opacity = "1";
    docCreatorInput.style.opacity = "1";

    stateTxt.innerText = "Idle";
    stateDot.className = "status-dot";
    timerVal.innerText = "00:00";
    stopTimer();
  }
}

function startTimer() {
  stopTimer();
  
  function updateTime() {
    chrome.storage.local.get("recordingStartTime", (data) => {
      if (!data.recordingStartTime) return;
      const elapsed = Math.floor((Date.now() - data.recordingStartTime) / 1000);
      const m = String(Math.floor(elapsed / 60)).padStart(2, "0");
      const s = String(elapsed % 60).padStart(2, "0");
      timerVal.innerText = `${m}:${s}`;
    });
  }

  updateTime();
  timerInterval = setInterval(updateTime, 1000);
}

function stopTimer() {
  if (timerInterval) {
    clearInterval(timerInterval);
    timerInterval = null;
  }
}

function startRecording() {
  const docTitle = docTitleInput.value || "Standard Operating Procedure";
  const docCreator = docCreatorInput.value || "SOP Builder User";
  
  // Set starting time in storage
  chrome.storage.local.set({ recordingStartTime: Date.now() }, () => {
    chrome.runtime.sendMessage({
      type: "START_RECORDING",
      docTitle,
      docCreator
    }, (response) => {
      if (response && response.success) {
        state = response.state;
        updateUI();
      }
    });
  });
}

function togglePause() {
  const type = state.isPaused ? "RESUME_RECORDING" : "PAUSE_RECORDING";
  chrome.runtime.sendMessage({ type }, (response) => {
    if (response && response.success) {
      state = response.state;
      updateUI();
    }
  });
}

function stopRecording() {
  chrome.runtime.sendMessage({ type: "STOP_RECORDING" }, (response) => {
    if (response && response.success) {
      state = response.state;
      updateUI();
      window.close(); // Close the popup
    }
  });
}

function openDashboard() {
  chrome.tabs.create({
    url: chrome.runtime.getURL("dashboard/dashboard.html")
  });
  window.close();
}

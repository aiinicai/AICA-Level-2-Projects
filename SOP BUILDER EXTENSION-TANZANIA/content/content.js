// content.js - SOP Maker Content Script

let isRecording = false;
let isPaused = false;
let widgetEl = null;
let timerInterval = null;

// Get element details
function getUniqueSelector(el) {
  if (!el || el.nodeType !== Node.ELEMENT_NODE) return "";
  if (el.id) return `#${el.id}`;
  let path = [];
  while (el && el.nodeType === Node.ELEMENT_NODE) {
    let selector = el.nodeName.toLowerCase();
    if (el.className && typeof el.className === 'string') {
      const classes = el.className.trim().split(/\s+/).filter(c => c && !c.startsWith('sop-'));
      if (classes.length > 0) selector += `.${classes[0]}`;
    }
    let sib = el, sibIndex = 1;
    while (sib = sib.previousElementSibling) {
      if (sib.nodeName.toLowerCase() === el.nodeName.toLowerCase()) {
        sibIndex++;
      }
    }
    if (sibIndex > 1) {
      selector += `:nth-of-type(${sibIndex})`;
    }
    path.unshift(selector);
    el = el.parentNode;
  }
  return path.join(" > ");
}

function getElementLabel(element) {
  // Traverse up to find a clickable container (up to 3 levels)
  let current = element;
  for (let i = 0; i < 3; i++) {
    if (!current) break;
    const tag = current.tagName.toLowerCase();
    if (tag === 'a' || tag === 'button' || current.getAttribute('role') === 'button' || current.onclick) {
      element = current;
      break;
    }
    current = current.parentElement;
  }

  const tag = element.tagName.toLowerCase();
  let text = "";
  let type = "element";

  if (tag === "input") {
    type = "input field";
    text = element.placeholder || element.ariaLabel || element.name || element.value || element.id || "";
  } else if (tag === "button" || element.getAttribute('role') === 'button') {
    type = "button";
    text = element.innerText || element.textContent || element.ariaLabel || element.title || element.value || "";
  } else if (tag === "a") {
    type = "link";
    text = element.innerText || element.textContent || element.ariaLabel || element.title || "";
  } else if (tag === "img") {
    type = "image";
    text = element.alt || element.title || "image";
  } else if (tag === "select") {
    type = "dropdown list";
    text = element.name || element.id || "";
  } else {
    text = element.innerText || element.textContent || "";
    if (text.length > 50) {
      text = text.substring(0, 50) + "...";
    }
  }

  text = text.trim().replace(/\s+/g, ' ');
  if (!text) {
    text = element.className && typeof element.className === 'string' ? `.${element.className.trim().split(' ')[0]}` : tag;
  }
  
  return {
    label: text,
    type: type,
    tagName: tag,
    id: element.id || "",
    className: typeof element.className === 'string' ? element.className : "",
    selector: getUniqueSelector(element)
  };
}

// Draw visual ripple feedback
function createRipple(clientX, clientY) {
  const ripple = document.createElement("div");
  ripple.className = "sop-click-ripple";
  ripple.style.left = `${clientX - 15}px`;
  ripple.style.top = `${clientY - 15}px`;
  document.body.appendChild(ripple);
  
  setTimeout(() => {
    ripple.remove();
  }, 600);
}

// Injected Toolbar Logic
function createWidget() {
  if (widgetEl) return;

  widgetEl = document.createElement("div");
  widgetEl.id = "sop-recorder-widget";
  widgetEl.className = "sop-widget-container";
  widgetEl.innerHTML = `
    <div class="sop-widget-status">
      <span class="sop-widget-dot red-pulse"></span>
      <span class="sop-widget-text">Recording</span>
    </div>
    <div class="sop-widget-stats">
      <span class="sop-widget-steps" id="sop-widget-steps-txt">0 Steps</span>
      <span class="sop-widget-divider">|</span>
      <span class="sop-widget-timer" id="sop-widget-timer-txt">00:00</span>
    </div>
    <div class="sop-widget-actions">
      <button id="sop-widget-pause-btn" class="sop-widget-btn" title="Pause Recording">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>
      </button>
      <button id="sop-widget-stop-btn" class="sop-widget-btn stop" title="Stop Recording">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M6 6h12v12H6V6z"/></svg>
      </button>
    </div>
  `;
  document.body.appendChild(widgetEl);

  // Button Listeners
  document.getElementById("sop-widget-pause-btn").addEventListener("click", togglePause);
  document.getElementById("sop-widget-stop-btn").addEventListener("click", stopRecording);

  updateWidgetUI();
  startTimer();
}

function removeWidget() {
  if (widgetEl) {
    widgetEl.remove();
    widgetEl = null;
  }
  stopTimer();
}

function updateWidgetUI() {
  if (!widgetEl) return;

  const statusText = widgetEl.querySelector(".sop-widget-text");
  const statusDot = widgetEl.querySelector(".sop-widget-dot");
  const pauseBtn = document.getElementById("sop-widget-pause-btn");

  chrome.storage.local.get(["isRecording", "isPaused", "steps"], (data) => {
    const steps = data.steps || [];
    document.getElementById("sop-widget-steps-txt").innerText = `${steps.length} Step${steps.length === 1 ? "" : "s"}`;

    if (data.isPaused) {
      statusText.innerText = "Paused";
      statusDot.className = "sop-widget-dot orange-pulse";
      pauseBtn.innerHTML = `<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>`;
      pauseBtn.title = "Resume Recording";
    } else {
      statusText.innerText = "Recording";
      statusDot.className = "sop-widget-dot red-pulse";
      pauseBtn.innerHTML = `<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>`;
      pauseBtn.title = "Pause Recording";
    }
  });
}

function startTimer() {
  stopTimer();
  timerInterval = setInterval(() => {
    chrome.storage.local.get(["recordingStartTime", "isPaused"], (data) => {
      if (data.isPaused || !data.recordingStartTime) return;
      const elapsed = Math.floor((Date.now() - data.recordingStartTime) / 1000);
      const m = String(Math.floor(elapsed / 60)).padStart(2, "0");
      const s = String(elapsed % 60).padStart(2, "0");
      
      const timerTxt = document.getElementById("sop-widget-timer-txt");
      if (timerTxt) timerTxt.innerText = `${m}:${s}`;
    });
  }, 1000);
}

function stopTimer() {
  if (timerInterval) {
    clearInterval(timerInterval);
    timerInterval = null;
  }
}

function togglePause(e) {
  e.stopPropagation();
  chrome.storage.local.get("isPaused", (data) => {
    const type = data.isPaused ? "RESUME_RECORDING" : "PAUSE_RECORDING";
    chrome.runtime.sendMessage({ type }, (response) => {
      if (response && response.success) {
        updateWidgetUI();
      }
    });
  });
}

function stopRecording(e) {
  e.stopPropagation();
  chrome.runtime.sendMessage({ type: "STOP_RECORDING" }, (response) => {
    if (response && response.success) {
      removeWidget();
    }
  });
}

// Global click interception
document.addEventListener("click", (event) => {
  // Prevent recording clicks inside the widget
  if (event.target.closest("#sop-recorder-widget") || event.target.closest(".sop-click-ripple")) {
    return;
  }

  // Check state before recording click
  chrome.storage.local.get(["isRecording", "isPaused"], (data) => {
    if (data.isRecording && !data.isPaused) {
      // 1. Draw yellow ripple animation
      createRipple(event.clientX, event.clientY);

      // 2. Extract context info of click target
      const elementInfo = getElementLabel(event.target);

      // 3. Send click info to background to trigger screenshot annotation
      chrome.runtime.sendMessage({
        type: "RECORD_CLICK",
        x: event.clientX,
        y: event.clientY,
        viewportWidth: window.innerWidth,
        viewportHeight: window.innerHeight,
        devicePixelRatio: window.devicePixelRatio,
        elementInfo: elementInfo,
        pageUrl: window.location.href,
        pageTitle: document.title
      });
      
      // Update step count UI shortly after
      setTimeout(updateWidgetUI, 300);
    }
  });
}, true); // capturing phase

// Listen for updates from Background Worker
chrome.runtime.onMessage.addListener((message) => {
  if (message.type === "STATUS_CHANGED") {
    if (message.state.isRecording) {
      createWidget();
      updateWidgetUI();
    } else {
      removeWidget();
    }
  }
});

// Initialize on load
chrome.storage.local.get(["isRecording", "isPaused"], (data) => {
  if (data.isRecording) {
    createWidget();
    updateWidgetUI();
  }
});

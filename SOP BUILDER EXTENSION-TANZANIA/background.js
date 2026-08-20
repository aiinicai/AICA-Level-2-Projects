// background.js - SOP Maker Extension Service Worker

let recordingState = {
  isRecording: false,
  isPaused: false,
  steps: []
};

// Helper: Initialize/Sync state from storage
function initState() {
  chrome.storage.local.get(["isRecording", "isPaused", "steps"], (result) => {
    recordingState.isRecording = result.isRecording || false;
    recordingState.isPaused = result.isPaused || false;
    recordingState.steps = result.steps || [];
    updateBadge();
  });
}

// Helper: Save state to storage
function saveState() {
  chrome.storage.local.set({
    isRecording: recordingState.isRecording,
    isPaused: recordingState.isPaused,
    steps: recordingState.steps
  }, () => {
    updateBadge();
    // Notify active tabs about status change
    chrome.tabs.query({}, (tabs) => {
      tabs.forEach((tab) => {
        if (tab.id) {
          chrome.tabs.sendMessage(tab.id, { type: "STATUS_CHANGED", state: recordingState }).catch(() => {
            // Ignore error for tabs where content script isn't loaded
          });
        }
      });
    });
  });
}

// Helper: Update extension icon badge
function updateBadge() {
  if (recordingState.isRecording) {
    if (recordingState.isPaused) {
      chrome.action.setBadgeText({ text: "II" });
      chrome.action.setBadgeBackgroundColor({ color: "#F59E0B" }); // Amber
    } else {
      chrome.action.setBadgeText({ text: "REC" });
      chrome.action.setBadgeBackgroundColor({ color: "#EF4444" }); // Red
    }
  } else {
    chrome.action.setBadgeText({ text: "" });
  }
}

// Helper: Convert Blob to Base64 in Service Worker
async function blobToBase64(blob) {
  const buffer = await blob.arrayBuffer();
  const bytes = new Uint8Array(buffer);
  const chunks = [];
  const chunkSize = 0xffff;
  for (let i = 0; i < bytes.length; i += chunkSize) {
    chunks.push(String.fromCharCode.apply(null, bytes.subarray(i, i + chunkSize)));
  }
  return 'data:' + blob.type + ';base64,' + btoa(chunks.join(''));
}

// Process screenshot and overlay marker
async function processScreenshot(dataUrl, clickData) {
  try {
    const response = await fetch(dataUrl);
    const blob = await response.blob();
    const imageBitmap = await createImageBitmap(blob);

    const canvas = new OffscreenCanvas(imageBitmap.width, imageBitmap.height);
    const ctx = canvas.getContext("2d");

    // Draw base screenshot
    ctx.drawImage(imageBitmap, 0, 0);

    // Calculate actual coordinate scale factor
    const scaleX = imageBitmap.width / clickData.viewportWidth;
    const scaleY = imageBitmap.height / clickData.viewportHeight;

    const x = clickData.x * scaleX;
    const y = clickData.y * scaleY;
    const dpr = clickData.devicePixelRatio || 1;

    // Radius of outer glow circle
    const glowRadius = 35 * dpr;
    const markerRadius = 15 * dpr;
    const centerRadius = 5 * dpr;

    // 1. Draw soft outer yellow glow
    const glowGrad = ctx.createRadialGradient(x, y, markerRadius, x, y, glowRadius);
    glowGrad.addColorStop(0, "rgba(254, 240, 138, 0.6)"); // soft yellow translucent
    glowGrad.addColorStop(0.5, "rgba(254, 240, 138, 0.2)");
    glowGrad.addColorStop(1, "rgba(254, 240, 138, 0)");
    ctx.fillStyle = glowGrad;
    ctx.beginPath();
    ctx.arc(x, y, glowRadius, 0, 2 * Math.PI);
    ctx.fill();

    // 2. Draw outer yellow ring
    ctx.strokeStyle = "rgba(234, 179, 8, 0.85)"; // solid yellow border
    ctx.lineWidth = 3 * dpr;
    ctx.beginPath();
    ctx.arc(x, y, markerRadius, 0, 2 * Math.PI);
    ctx.stroke();

    // 3. Draw translucent yellow filling for center target
    ctx.fillStyle = "rgba(254, 240, 138, 0.4)";
    ctx.beginPath();
    ctx.arc(x, y, markerRadius, 0, 2 * Math.PI);
    ctx.fill();

    // 4. Draw yellow solid center dot
    ctx.fillStyle = "rgba(234, 179, 8, 1)";
    ctx.beginPath();
    ctx.arc(x, y, centerRadius, 0, 2 * Math.PI);
    ctx.fill();

    // 5. Draw step number badge pill (Step [N]) near click point
    const stepNumber = recordingState.steps.length + 1;
    const label = `Step ${stepNumber}`;
    ctx.font = `bold ${Math.max(12, 11 * dpr)}px sans-serif`;
    
    // Measure text
    const textMetrics = ctx.measureText(label);
    const textWidth = textMetrics.width;
    const textHeight = Math.max(12, 11 * dpr);
    
    const paddingX = 8 * dpr;
    const paddingY = 4 * dpr;
    
    const badgeW = textWidth + paddingX * 2;
    const badgeH = textHeight + paddingY * 2;
    
    // Position badge slightly offset from the marker center
    let badgeX = x + markerRadius + 10 * dpr;
    let badgeY = y - badgeH / 2;
    
    // Make sure badge fits on screen
    if (badgeX + badgeW > imageBitmap.width) {
      badgeX = x - markerRadius - badgeW - 10 * dpr;
    }
    if (badgeY < 0) {
      badgeY = 10 * dpr;
    }
    if (badgeY + badgeH > imageBitmap.height) {
      badgeY = imageBitmap.height - badgeH - 10 * dpr;
    }

    // Draw rounded badge background
    ctx.fillStyle = "#1E293B"; // Dark slate
    ctx.strokeStyle = "#FACC15"; // Yellow border
    ctx.lineWidth = 1.5 * dpr;
    
    ctx.beginPath();
    if (ctx.roundRect) {
      ctx.roundRect(badgeX, badgeY, badgeW, badgeH, 4 * dpr);
    } else {
      ctx.rect(badgeX, badgeY, badgeW, badgeH);
    }
    ctx.fill();
    ctx.stroke();

    // Draw badge text in yellow
    ctx.fillStyle = "#FACC15";
    ctx.textBaseline = "middle";
    ctx.fillText(label, badgeX + paddingX, badgeY + badgeH / 2);

    // Convert back to base64
    const newBlob = await canvas.convertToBlob({ type: "image/jpeg", quality: 0.85 });
    const annotatedDataUrl = await blobToBase64(newBlob);
    return annotatedDataUrl;
  } catch (error) {
    console.error("Screenshot processing error:", error);
    return dataUrl; // fallback to original screenshot
  }
}

// Listen for messages
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "GET_STATUS") {
    sendResponse(recordingState);
  } 
  
  else if (message.type === "START_RECORDING") {
    recordingState.isRecording = true;
    recordingState.isPaused = false;
    recordingState.steps = [];
    
    // Save metadata
    chrome.storage.local.set({
      docTitle: message.docTitle || "Standard Operating Procedure",
      docCreator: message.docCreator || "SOP Builder User",
      docDescription: message.docDescription || "Auto-generated step-by-step documentation."
    });

    saveState();
    sendResponse({ success: true, state: recordingState });
  } 
  
  else if (message.type === "PAUSE_RECORDING") {
    recordingState.isPaused = true;
    saveState();
    sendResponse({ success: true, state: recordingState });
  } 
  
  else if (message.type === "RESUME_RECORDING") {
    recordingState.isPaused = false;
    saveState();
    sendResponse({ success: true, state: recordingState });
  } 
  
  else if (message.type === "STOP_RECORDING") {
    recordingState.isRecording = false;
    recordingState.isPaused = false;
    saveState();
    
    // Open the Dashboard
    chrome.tabs.create({
      url: chrome.runtime.getURL("dashboard/dashboard.html")
    });
    
    sendResponse({ success: true, state: recordingState });
  } 
  
  else if (message.type === "RECORD_CLICK") {
    if (!recordingState.isRecording || recordingState.isPaused) {
      sendResponse({ status: "ignored" });
      return true;
    }

    // Capture tab screenshot instantly
    chrome.tabs.captureVisibleTab(null, { format: "png" }, async (dataUrl) => {
      if (chrome.runtime.lastError || !dataUrl) {
        console.warn("Screenshot capture failed:", chrome.runtime.lastError);
        // Save step without screenshot
        const step = {
          id: Date.now(),
          timestamp: new Date().toISOString(),
          title: `Click on ${message.elementInfo.label}`,
          description: `Click the ${message.elementInfo.type} element: "${message.elementInfo.label}"`,
          elementInfo: message.elementInfo,
          pageUrl: message.pageUrl,
          pageTitle: message.pageTitle,
          image: "" // Empty image fallback
        };
        recordingState.steps.push(step);
        saveState();
        return;
      }

      // Annotate screenshot
      const annotatedImage = await processScreenshot(dataUrl, message);

      const step = {
        id: Date.now(),
        timestamp: new Date().toISOString(),
        title: `Click on ${message.elementInfo.label}`,
        description: `Click the ${message.elementInfo.type} element: "${message.elementInfo.label}"`,
        elementInfo: message.elementInfo,
        pageUrl: message.pageUrl,
        pageTitle: message.pageTitle,
        image: annotatedImage
      };

      recordingState.steps.push(step);
      saveState();
    });

    sendResponse({ status: "processing" });
  }

  return true; // Keep message channel open for async responses
});

// Initialize on load
chrome.runtime.onInstalled.addListener(() => {
  initState();
});

initState();

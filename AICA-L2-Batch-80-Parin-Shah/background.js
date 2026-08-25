// Keep track of tabs that have been temporarily unlocked
let unlockedTabs = new Set();

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.url) {
    chrome.storage.local.get(['lockedSites'], function(result) {
      const lockedSites = result.lockedSites || [];
      
      // Check if the current URL matches any locked site
      const isLocked = lockedSites.some(site => changeInfo.url.includes(site));
      
      if (isLocked && !unlockedTabs.has(tabId)) {
        // Redirect to the authentication screen
        const authUrl = chrome.runtime.getURL(`auth.html?target=${encodeURIComponent(changeInfo.url)}&tabId=${tabId}`);
        chrome.tabs.update(tabId, { url: authUrl });
      }
    });
  }
});

// Listen for messages from the auth page to unlock the tab
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === "unlockTab") {
    unlockedTabs.add(message.tabId);
    // Remove the unlock status when the tab is closed
    chrome.tabs.onRemoved.addListener(function listener(closedTabId) {
      if (closedTabId === message.tabId) {
        unlockedTabs.delete(message.tabId);
        chrome.tabs.onRemoved.removeListener(listener);
      }
    });
    sendResponse({ success: true });
  }
});
const urlParams = new URLSearchParams(window.location.search);
const targetUrl = urlParams.get('target');
const tabId = parseInt(urlParams.get('tabId'));

// Listen for page load to trigger automatically
window.addEventListener('DOMContentLoaded', () => {
    chrome.storage.local.get(['savedCredentialId'], (result) => {
        if (result.savedCredentialId) {
            triggerBiometric(result.savedCredentialId);
        } else {
            document.getElementById('errorMsg').innerText = "Please register biometrics in the extension popup first.";
        }
    });
});

// Fallback button just in case the prompt gets dismissed
document.getElementById('unlockBtn').addEventListener('click', () => {
    chrome.storage.local.get(['savedCredentialId'], (result) => {
        if (result.savedCredentialId) triggerBiometric(result.savedCredentialId);
    });
});

async function triggerBiometric(credentialIdArray) {
  try {
    const challenge = new Uint8Array(32);
    crypto.getRandomValues(challenge);

    const publicKeyCredentialRequestOptions = {
      challenge: challenge,
      // FORCE WINDOWS HELLO BY SPECIFYING THE CREDENTIAL AND TRANSPORT
      allowCredentials: [{
        id: new Uint8Array(credentialIdArray),
        type: 'public-key',
        transports: ['internal'] 
      }],
      userVerification: "required"
    };

    const assertion = await navigator.credentials.get({
      publicKey: publicKeyCredentialRequestOptions
    });

    if (assertion) {
      chrome.runtime.sendMessage({ action: "unlockTab", tabId: tabId }, (response) => {
        if (response.success) {
          window.location.href = targetUrl; 
        }
      });
    }
  } catch (err) {
    document.getElementById('errorMsg').innerText = "Authentication failed or canceled.";
  }
}
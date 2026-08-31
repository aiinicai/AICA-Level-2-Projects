document.getElementById('addSiteBtn').addEventListener('click', () => {
  const site = document.getElementById('siteInput').value.trim();
  if (site) {
    chrome.storage.local.get(['lockedSites'], (result) => {
      const sites = result.lockedSites || [];
      sites.push(site);
      chrome.storage.local.set({ lockedSites: sites }, () => {
        document.getElementById('status').innerText = `${site} locked!`;
      });
    });
  }
});

document.getElementById('registerBioBtn').addEventListener('click', async () => {
  try {
    const challenge = new Uint8Array(32);
    crypto.getRandomValues(challenge);

    const publicKeyCredentialCreationOptions = {
      challenge: challenge,
      rp: { name: "BioLock Extension" },
      user: {
        id: Uint8Array.from("user123", c => c.charCodeAt(0)),
        name: "user@extension",
        displayName: "Extension User"
      },
      pubKeyCredParams: [{ alg: -7, type: "public-key" }],
      authenticatorSelection: {
        authenticatorAttachment: "platform",
        userVerification: "required"
      },
      timeout: 60000
    };

    const credential = await navigator.credentials.create({
      publicKey: publicKeyCredentialCreationOptions
    });

    // CONVERT AND SAVE THE CREDENTIAL ID
    const credentialIdArray = Array.from(new Uint8Array(credential.rawId));
    chrome.storage.local.set({ 
        biometricEnabled: true, 
        savedCredentialId: credentialIdArray 
    });
    
    document.getElementById('status').innerText = "Biometrics registered!";
    
  } catch (err) {
    document.getElementById('status').innerText = "Error: " + err.message;
  }
});
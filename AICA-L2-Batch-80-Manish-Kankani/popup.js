const startBtn = document.getElementById('startBtn');
const optScreen = document.getElementById('optScreen');
const optMic = document.getElementById('optMic');
const optCamera = document.getElementById('optCamera');

function updateButtonState() {
  const any = optScreen.checked || optMic.checked || optCamera.checked;
  startBtn.disabled = !any;
  startBtn.textContent = any ? 'Start Recording' : 'Pick at least one source';
}

[optScreen, optMic, optCamera].forEach((el) => el.addEventListener('change', updateButtonState));
updateButtonState();

startBtn.addEventListener('click', async () => {
  const options = {
    screen: optScreen.checked,
    mic: optMic.checked,
    camera: optCamera.checked
  };
  await chrome.storage.local.set({ recorderOptions: options });
  chrome.tabs.create({ url: chrome.runtime.getURL('recorder.html') });
  window.close();
});

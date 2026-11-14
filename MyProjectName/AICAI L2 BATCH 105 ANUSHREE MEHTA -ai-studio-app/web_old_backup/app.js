// Generations Connect - Progressive Web App Client
const state = {
  currentProfile: 'senior', // senior, child, parent, landing
  theme: 'light',
  medications: [
    { id: 'm1', name: 'Lisinopril', dosage: '10 mg', time: '8:00 AM', notes: 'Take with a glass of water after breakfast', status: 'taken', takenAt: '8:15 AM' },
    { id: 'm2', name: 'Metoprolol Tartrate', dosage: '25 mg', time: '8:00 AM', notes: 'Take with morning meal', status: 'taken', takenAt: '8:15 AM' },
    { id: 'm3', name: 'Omega-3 Wild Fish Oil', dosage: '1,000 mg', time: '1:00 PM', notes: 'Take with lunch', status: 'overdue' },
    { id: 'm4', name: 'Calcium & Vitamin D3', dosage: '500 mg / 400 IU', time: '8:00 PM', notes: 'Take with evening tea', status: 'pending' }
  ],
  sleepRecords: [
    { day: 'Mon', hours: 7.5, stars: 4 },
    { day: 'Tue', hours: 6.8, stars: 3 },
    { day: 'Wed', hours: 8.2, stars: 5 },
    { day: 'Thu', hours: 7.0, stars: 4 },
    { day: 'Fri', hours: 7.8, stars: 5 },
    { day: 'Sat', hours: 6.5, stars: 3 },
    { day: 'Sun', hours: 8.0, stars: 5 }
  ],
  diaryEntries: [
    { id: 'd1', date: 'Today, Oct 31', emoji: '😊', mood: 'Joyful & Connected', text: 'Leo showed me his drawing of our secret garden story! My joint stiffness felt lighter after our talk.', voiceSec: 42 }
  ],
  currentStory: {
    title: 'The Time-Traveling Bicycle of Willow Creek',
    theme: 'Mystery & Invention',
    buddy: 'Leo (Age 8)',
    turns: [
      {
        turnNum: 1,
        text: 'In the attic above the old bicycle shop, Eleanor and Leo uncovered an antique two-seater tandem covered in a dusty velvet drape. When Leo gently tapped the brass handlebar bell, it rang with a melodic chime that caused the floorboards to shimmer in iridescent indigo light!',
        chosen: 'Pedal forward toward 1965'
      },
      {
        turnNum: 2,
        text: 'Together they pressed their feet to the pedals. Whoosh! The attic walls dissolved into a warm summer breeze over a 1960s county fair! Vintage music played from a carousel, and children in retro hats cheered.',
        choices: ['Join the carousel parade', 'Taste the famous blueberry pie', 'Look for young Eleanor’s house']
      }
    ]
  },
  childPoints: 340,
  missions: [
    { id: 'ms1', title: 'Draw a flower for Grandma Eleanor', desc: 'Pick the sunflower outline and paint it', pts: 50, done: false },
    { id: 'ms2', title: 'Play Find the Pairs Game', desc: 'Train memory skills with buddy tiles', pts: 35, done: true },
    { id: 'ms3', title: 'Co-Write Chapter 3', desc: 'Pick the twist for the Time-Traveling Bicycle', pts: 40, done: false }
  ],
  friendRequests: [
    { id: 'fr1', name: 'Arthur Campbell (Age 76)', interests: ['Antique Clocks', 'Chess & Puzzles', 'Woodworking'], bio: 'Former watchmaker who loves riddles and building wooden gliders.', status: 'pending' },
    { id: 'fr2', name: 'Eleanor Vance (Age 73)', interests: ['Botanical Gardening', 'Fantasy Stories', 'Watercolor Painting'], bio: 'Retired elementary science teacher.', status: 'approved' }
  ],
  lastUndoneMed: null
};

// PWA Install Prompt
let deferredInstallPrompt = null;
window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  deferredInstallPrompt = e;
  const installBtn = document.getElementById('installAppBtn');
  if (installBtn) installBtn.style.display = 'inline-flex';
});

// Service Worker Registration
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('./sw.js').catch(console.error);
}

// Web Speech API Text-to-Speech
function speakText(text) {
  if (!('speechSynthesis' in window)) {
    showToast('Speech synthesis not supported on this browser.');
    return;
  }
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 0.9;
  utterance.pitch = 1.0;
  
  const buttons = document.querySelectorAll('.btn-read-aloud');
  buttons.forEach(btn => btn.classList.add('speaking'));
  
  utterance.onend = () => {
    buttons.forEach(btn => btn.classList.remove('speaking'));
  };
  utterance.onerror = () => {
    buttons.forEach(btn => btn.classList.remove('speaking'));
  };

  window.speechSynthesis.speak(utterance);
}

function stopSpeaking() {
  if ('speechSynthesis' in window) {
    window.speechSynthesis.cancel();
    document.querySelectorAll('.btn-read-aloud').forEach(btn => btn.classList.remove('speaking'));
  }
}

// Notification Request & Trigger
async function requestNotificationPermission() {
  if (!('Notification' in window)) {
    showToast('Notifications not supported by this browser.');
    return false;
  }
  const perm = await Notification.requestPermission();
  return perm === 'granted';
}

function sendMedicationNotification(title, body) {
  if ('Notification' in window && Notification.permission === 'granted') {
    new Notification(title, {
      body: body,
      icon: './icon-192.png',
      badge: './icon-192.png',
      vibrate: [200, 100, 200]
    });
  } else {
    showToast(`🔔 Notification: ${title} - ${body}`);
  }
}

function showToast(msg) {
  const toast = document.getElementById('toastNotice');
  if (!toast) return;
  toast.innerText = msg;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 3500);
}

// Tab and Profile Navigation
function setProfile(profile) {
  state.currentProfile = profile;
  document.documentElement.setAttribute('data-profile', profile);
  renderApp();
  showToast(`Switched to ${profile.toUpperCase()} profile`);
}

function toggleTheme() {
  state.theme = state.theme === 'light' ? 'dark' : 'light';
  document.documentElement.setAttribute('data-theme', state.theme);
  const icon = document.getElementById('themeToggleBtn');
  if (icon) icon.innerText = state.theme === 'light' ? '🌙' : '☀️';
}

// Render Main Views
function renderApp() {
  const container = document.getElementById('appContent');
  if (!container) return;

  if (state.currentProfile === 'landing') {
    container.innerHTML = renderLandingView();
  } else if (state.currentProfile === 'senior') {
    container.innerHTML = renderSeniorHome();
  } else if (state.currentProfile === 'child') {
    container.innerHTML = renderChildView();
  } else if (state.currentProfile === 'parent') {
    container.innerHTML = renderParentView();
  }
}

// ------------------------------------
// SENIOR VIEWS
// ------------------------------------
function renderSeniorHome() {
  const taken = state.medications.filter(m => m.status === 'taken').length;
  const total = state.medications.length;
  const overdue = state.medications.find(m => m.status === 'overdue');
  const pct = Math.round((taken / total) * 100);

  return `
    <div class="card" style="background: var(--primary-light); border-color: var(--primary);">
      <h2 class="card-title">Good Afternoon, Eleanor! 🌸</h2>
      <p class="card-subtitle">Connected with Leo (Age 8) • Willow Creek Adventure</p>
      <button class="btn-read-aloud" onclick="speakText('Good afternoon Eleanor. You have taken ${taken} of ${total} medicines today. Tap any shortcut to begin.')">
        🔊 Read today's summary aloud
      </button>
    </div>

    ${overdue ? `
    <div class="card" style="background: var(--warning-bg); border-color: var(--warning);">
      <div style="display: flex; align-items: center; gap: 14px;">
        <span style="font-size: 32px;">⚠️</span>
        <div>
          <h3 style="font-size: 20px; font-weight: 800; color: #78350f;">Reminder: Afternoon Dose</h3>
          <p style="color: #92400e;">${overdue.name} (${overdue.time}) is ready to take.</p>
        </div>
      </div>
    </div>` : ''}

    <div class="card">
      <div class="progress-container">
        <div>
          <h3 class="card-title">Today's Medicine Progress</h3>
          <p class="card-subtitle">${taken} of ${total} doses taken today</p>
        </div>
        <div class="circle-progress">
          <svg viewBox="0 0 36 36">
            <path stroke="var(--border-color)" stroke-width="3.5" fill="none"
              d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
            <path stroke="var(--primary)" stroke-dasharray="${pct}, 100" stroke-width="3.5" stroke-linecap="round" fill="none"
              d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
          </svg>
          <div class="circle-progress-val">${pct}%</div>
        </div>
      </div>
    </div>

    <h3 style="font-size: 22px; font-weight: 700; margin: 20px 0 10px;">Quick Shortcuts</h3>
    <div class="shortcut-grid">
      <div class="shortcut-tile" onclick="renderSeniorMedicines()">
        <span class="tile-icon">💊</span>
        <div>
          <div class="tile-title">Medicines</div>
          <div class="tile-sub">${taken} of ${total} taken</div>
        </div>
      </div>
      <div class="shortcut-tile" onclick="renderSeniorDiary()">
        <span class="tile-icon">📖</span>
        <div>
          <div class="tile-title">Daily Diary</div>
          <div class="tile-sub">Record mood & voice</div>
        </div>
      </div>
      <div class="shortcut-tile" onclick="renderSeniorSleep()">
        <span class="tile-icon">🌙</span>
        <div>
          <div class="tile-title">Sleep Log</div>
          <div class="tile-sub">Weekly chart & hours</div>
        </div>
      </div>
      <div class="shortcut-tile" onclick="renderSeniorStories()">
        <span class="tile-icon">✨</span>
        <div>
          <div class="tile-title">Stories with Leo</div>
          <div class="tile-sub">Co-write Chapter 3</div>
        </div>
      </div>
      <div class="shortcut-tile" onclick="renderSeniorGames()">
        <span class="tile-icon">🎨</span>
        <div>
          <div class="tile-title">Games & Art</div>
          <div class="tile-sub">Memory pairs & paint</div>
        </div>
      </div>
      <div class="shortcut-tile" onclick="renderSeniorPhoto()">
        <span class="tile-icon">📷</span>
        <div>
          <div class="tile-title">Photo Studio</div>
          <div class="tile-sub">Medicinal plants & origin</div>
        </div>
      </div>
      <div class="shortcut-tile" onclick="renderSeniorBreathing()">
        <span class="tile-icon">🧘</span>
        <div>
          <div class="tile-title">Calm Breathing</div>
          <div class="tile-sub">1-min guided exercise</div>
        </div>
      </div>
    </div>
  `;
}

function renderSeniorMedicines() {
  const container = document.getElementById('appContent');
  container.innerHTML = `
    <div class="card">
      <h2 class="card-title">Today's Schedule & Reminders</h2>
      <p class="card-subtitle">Large touch targets with automatic dose push notifications</p>
      
      <div style="background: var(--surface-variant); padding: 14px; border-radius: var(--radius-md); margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center;">
        <div>
          <strong>🔔 Browser Push Reminders</strong>
          <div style="font-size: 15px; color: var(--text-muted);">Receive device chime and alerts on schedule</div>
        </div>
        <button class="btn-outline" style="min-height: 44px; padding: 6px 14px; font-size: 16px;" onclick="testPushNotification()">Test Push in 5s</button>
      </div>

      ${state.medications.map(med => `
        <div class="med-card ${med.status}">
          <div class="med-header">
            <div>
              <div style="font-size: 22px; font-weight: 800;">${med.name}</div>
              <div style="font-size: 18px; color: var(--primary); font-weight: 600;">${med.dosage} • ${med.time}</div>
            </div>
            <span class="med-badge badge-${med.status}">${med.status}</span>
          </div>
          <div style="font-size: 17px; color: var(--text-muted);">${med.notes}</div>
          <div style="margin-top: 10px;">
            ${med.status === 'taken' ? `
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="color: var(--success); font-weight: 700; font-size: 19px;">✓ Taken at ${med.takenAt || '8:15 AM'}</span>
                <button class="btn-outline" style="min-height: 48px; padding: 6px 16px;" onclick="undoMed('${med.id}')">Undo</button>
              </div>
            ` : `
              <button class="btn-primary" onclick="takeMed('${med.id}')">✓ I Took It</button>
            `}
          </div>
        </div>
      `).join('')}

      <button class="btn-outline" style="width: 100%; margin-top: 10px;" onclick="openAddMedModal()">+ Add New Medication</button>
    </div>
  `;
}

function takeMed(id) {
  const m = state.medications.find(x => x.id === id);
  if (m) {
    state.lastUndoneMed = { ...m };
    m.status = 'taken';
    m.takenAt = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    renderSeniorMedicines();
    showToast(`Marked ${m.name} as taken! Undo available.`);
  }
}

function undoMed(id) {
  const m = state.medications.find(x => x.id === id);
  if (m) {
    m.status = 'pending';
    m.takenAt = null;
    renderSeniorMedicines();
    showToast(`Restored ${m.name} to pending.`);
  }
}

function testPushNotification() {
  requestNotificationPermission().then(() => {
    showToast('Scheduling test notification for 5 seconds...');
    setTimeout(() => {
      sendMedicationNotification('Time for Lisinopril (10 mg)', 'Scheduled for morning routine. Take with a glass of water.');
    }, 5000);
  });
}

// ------------------------------------
// SLEEP LOG WITH CANVAS BAR CHART
// ------------------------------------
function renderSeniorSleep() {
  const container = document.getElementById('appContent');
  container.innerHTML = `
    <div class="card">
      <h2 class="card-title">Sleep & Rest Health</h2>
      <p class="card-subtitle">Weekly pattern with 8-hour target baseline</p>
      
      <div style="margin: 16px 0;">
        <canvas id="sleepCanvas" width="600" height="200" style="width: 100%; height: 200px;"></canvas>
      </div>

      <div style="background: var(--surface-variant); padding: 16px; border-radius: var(--radius-md); margin-top: 14px;">
        <strong>7-Day Average: 7.4 hours / night</strong>
        <p style="color: var(--text-muted); font-size: 16px;">Consistent restorative sleep helps daytime focus and joint comfort.</p>
      </div>

      <button class="btn-primary" style="margin-top: 20px;" onclick="showToast('Sleep logged for last night: 8.0 hrs!')">Log Last Night's Sleep</button>
    </div>
  `;

  setTimeout(drawSleepChart, 50);
}

function drawSleepChart() {
  const canvas = document.getElementById('sleepCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const w = canvas.width;
  const h = canvas.height;
  ctx.clearRect(0, 0, w, h);

  const barCount = state.sleepRecords.length;
  const spacing = w / barCount;
  const barW = spacing * 0.55;

  // 8hr target dashed line
  const targetY = h - (8 / 10) * (h - 30);
  ctx.strokeStyle = '#e76f51';
  ctx.setLineDash([8, 6]);
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(0, targetY);
  ctx.lineTo(w, targetY);
  ctx.stroke();
  ctx.setLineDash([]);

  // Bars
  state.sleepRecords.forEach((rec, i) => {
    const barH = (rec.hours / 10) * (h - 40);
    const x = i * spacing + (spacing - barW) / 2;
    const y = h - barH - 24;

    ctx.fillStyle = '#14535c';
    ctx.beginPath();
    ctx.roundRect(x, y, barW, barH, 8);
    ctx.fill();

    // Labels
    ctx.fillStyle = '#4b676c';
    ctx.font = 'bold 15px system-ui';
    ctx.textAlign = 'center';
    ctx.fillText(rec.day, x + barW / 2, h - 6);
  });
}

// ------------------------------------
// AI STORY HELPER
// ------------------------------------
function renderSeniorStories() {
  const container = document.getElementById('appContent');
  const story = state.currentStory;
  const lastTurn = story.turns[story.turns.length - 1];

  container.innerHTML = `
    <div class="card">
      <h2 class="card-title">${story.title}</h2>
      <p class="card-subtitle">Co-writing with ${story.buddy} • Theme: ${story.theme}</p>
      
      <button class="btn-read-aloud" onclick="speakText('${story.turns.map(t => t.text).join(' ')}')">
        🔊 Read entire story aloud
      </button>

      ${story.turns.map(t => `
        <div style="background: var(--surface-variant); padding: 18px; border-radius: var(--radius-md); margin-bottom: 12px;">
          <div style="font-weight: 800; color: var(--primary); margin-bottom: 6px;">Chapter ${t.turnNum}</div>
          <p style="font-size: 19px; line-height: 1.6;">${t.text}</p>
          ${t.chosen ? `<div style="margin-top: 8px; font-weight: 700; color: var(--secondary);">Co-Author Choice: “${t.chosen}”</div>` : ''}
        </div>
      `).join('')}

      <div style="margin-top: 20px;">
        <h3 style="font-size: 20px; font-weight: 700; margin-bottom: 10px;">What should happen next?</h3>
        ${lastTurn.choices ? lastTurn.choices.map((c, i) => `
          <button class="btn-primary" style="margin-bottom: 10px;" onclick="advanceStory('${c}')">${i + 1}. ${c}</button>
        `).join('') : ''}
      </div>
    </div>
  `;
}

function advanceStory(choice) {
  showToast('Weaving next heartwarming adventure...');
  setTimeout(() => {
    state.currentStory.turns.push({
      turnNum: state.currentStory.turns.length + 1,
      text: `Following the choice to "${choice}", Eleanor and Leo were welcomed by the smiling carousel master who handed Leo a brass ring. The whole fairground began to sparkle with joy!`,
      choices: ['Board the painted carousel lion', 'Search for the hidden garden', 'Invite the friendly clown for tea'],
      chosen: choice
    });
    state.childPoints += 25;
    renderSeniorStories();
    speakText(`Chapter ${state.currentStory.turns.length}. Following the choice to ${choice}...`);
  }, 800);
}

// ------------------------------------
// GAMES: FIND PAIRS & SHARED CANVAS
// ------------------------------------
const memoryEmojis = ['🌻', '🦋', '🎨', '📖', '☕', '🐶'];
let memoryCards = [];
let flippedIndices = [];
let matchedCount = 0;

function renderSeniorGames() {
  const container = document.getElementById('appContent');
  container.innerHTML = `
    <div class="card">
      <h2 class="card-title">Generations Play Hub</h2>
      <p class="card-subtitle">Find the Pairs & Shared Art Canvas</p>

      <div style="display: flex; gap: 10px; margin-bottom: 16px;">
        <button class="btn-primary" style="flex: 1;" onclick="initMemoryGame()">Find the Pairs</button>
        <button class="btn-outline" style="flex: 1;" onclick="renderCanvasGame()">Shared Canvas</button>
      </div>

      <div id="gameArea"></div>
    </div>
  `;
  initMemoryGame();
}

function initMemoryGame() {
  const area = document.getElementById('gameArea');
  if (!area) return;
  memoryCards = [...memoryEmojis, ...memoryEmojis].sort(() => Math.random() - 0.5);
  flippedIndices = [];
  matchedCount = 0;

  area.innerHTML = `
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
      <strong>Match all 6 pairs!</strong>
      <span id="matchScore">0 / 6 Matched</span>
    </div>
    <div class="memory-grid" id="memoryGrid">
      ${memoryCards.map((em, idx) => `
        <div class="memory-card" id="card_${idx}" onclick="flipCard(${idx})">❓</div>
      `).join('')}
    </div>
  `;
}

function flipCard(idx) {
  if (flippedIndices.length >= 2 || flippedIndices.includes(idx)) return;
  const cardEl = document.getElementById(`card_${idx}`);
  cardEl.innerText = memoryCards[idx];
  cardEl.classList.add('flipped');
  flippedIndices.push(idx);

  if (flippedIndices.length === 2) {
    const [first, second] = flippedIndices;
    if (memoryCards[first] === memoryCards[second]) {
      matchedCount++;
      document.getElementById('matchScore').innerText = `${matchedCount} / 6 Matched`;
      flippedIndices = [];
      if (matchedCount === 6) {
        showToast('🎉 Congratulations! You found all pairs! +50 Points');
      }
    } else {
      setTimeout(() => {
        document.getElementById(`card_${first}`).innerText = '❓';
        document.getElementById(`card_${second}`).innerText = '❓';
        document.getElementById(`card_${first}`).classList.remove('flipped');
        document.getElementById(`card_${second}`).classList.remove('flipped');
        flippedIndices = [];
      }, 900);
    }
  }
}

function renderCanvasGame() {
  const area = document.getElementById('gameArea');
  if (!area) return;
  area.innerHTML = `
    <div class="paint-canvas-container">
      <canvas id="sharedCanvas" width="600" height="280"></canvas>
      <div class="canvas-controls">
        <div style="display: flex; gap: 8px;">
          <div class="palette-color" style="background: #e76f51;" onclick="setPaintColor('#e76f51')"></div>
          <div class="palette-color" style="background: #14535c;" onclick="setPaintColor('#14535c')"></div>
          <div class="palette-color" style="background: #ffb703;" onclick="setPaintColor('#ffb703')"></div>
          <div class="palette-color" style="background: #7c3aed;" onclick="setPaintColor('#7c3aed')"></div>
          <div class="palette-color" style="background: #10b981;" onclick="setPaintColor('#10b981')"></div>
        </div>
        <button class="btn-outline" style="min-height: 40px; padding: 4px 12px;" onclick="clearCanvas()">Clear</button>
      </div>
    </div>
    <button class="btn-primary" style="margin-top: 14px;" onclick="showToast('Shared painting sent to Leo! +40 Points')">Send Painting to Leo</button>
  `;
  initCanvas();
}

let canvasColor = '#e76f51';
function setPaintColor(c) { canvasColor = c; }
function clearCanvas() {
  const c = document.getElementById('sharedCanvas');
  if (c) c.getContext('2d').clearRect(0, 0, c.width, c.height);
}

function initCanvas() {
  const canvas = document.getElementById('sharedCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  let isDrawing = false;

  // Pre-drawn template outline (Sunflower)
  ctx.strokeStyle = '#9ca3af';
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.arc(300, 130, 45, 0, Math.PI * 2);
  ctx.stroke();

  canvas.addEventListener('mousedown', (e) => { isDrawing = true; draw(e); });
  canvas.addEventListener('mousemove', draw);
  window.addEventListener('mouseup', () => isDrawing = false);

  canvas.addEventListener('touchstart', (e) => { isDrawing = true; drawTouch(e); });
  canvas.addEventListener('touchmove', drawTouch);
  window.addEventListener('touchend', () => isDrawing = false);

  function draw(e) {
    if (!isDrawing) return;
    const rect = canvas.getBoundingClientRect();
    const x = (e.clientX - rect.left) * (canvas.width / rect.width);
    const y = (e.clientY - rect.top) * (canvas.height / rect.height);
    ctx.fillStyle = canvasColor;
    ctx.beginPath();
    ctx.arc(x, y, 10, 0, Math.PI * 2);
    ctx.fill();
  }

  function drawTouch(e) {
    if (!isDrawing || !e.touches[0]) return;
    const touch = e.touches[0];
    const rect = canvas.getBoundingClientRect();
    const x = (touch.clientX - rect.left) * (canvas.width / rect.width);
    const y = (touch.clientY - rect.top) * (canvas.height / rect.height);
    ctx.fillStyle = canvasColor;
    ctx.beginPath();
    ctx.arc(x, y, 10, 0, Math.PI * 2);
    ctx.fill();
  }
}

// ------------------------------------
// PHOTO STUDIO
// ------------------------------------
function renderSeniorPhoto() {
  const container = document.getElementById('appContent');
  container.innerHTML = `
    <div class="card">
      <h2 class="card-title">Intergenerational Photo Studio</h2>
      <p class="card-subtitle">AI analysis of medicinal properties, history & heritage learning</p>

      <div style="display: flex; gap: 10px; overflow-x: auto; padding: 10px 0;">
        <button class="btn-outline" onclick="analyzePhoto('Chamomile')">🌼 Chamomile</button>
        <button class="btn-outline" onclick="analyzePhoto('Lavender')">🪻 Lavender</button>
        <button class="btn-outline" onclick="analyzePhoto('Aloe Vera')">🪴 Aloe Vera</button>
        <button class="btn-outline" onclick="analyzePhoto('Pocket Compass')">🧭 Brass Compass</button>
      </div>

      <div id="photoResult" style="margin-top: 16px;">
        <div style="background: var(--surface-variant); padding: 20px; border-radius: var(--radius-md);">
          <h3 style="font-size: 22px; font-weight: 800; color: var(--primary);">German Chamomile (Matricaria chamomilla)</h3>
          <p style="font-size: 16px; color: var(--text-muted); margin-bottom: 12px;">Medicinal Flora • Botanical Origins</p>
          
          <button class="btn-read-aloud" onclick="speakText('Chamomile contains apigenin, an antioxidant that binds to brain receptors that promote calm and sleep. Traditionally used to soothe digestion.')">
            🔊 Read medicinal facts aloud
          </button>

          <div style="margin-top: 12px;">
            <strong>🌿 Health & Medicinal Properties:</strong>
            <p style="font-size: 17px; line-height: 1.5;">Contains apigenin, an antioxidant that binds to brain receptors to ease tension and improve restorative sleep.</p>
          </div>

          <div style="margin-top: 12px;">
            <strong>🍵 Household Uses:</strong>
            <p style="font-size: 17px; line-height: 1.5;">Warm nighttime tea, calming skin wash, companion plant in organic gardens.</p>
          </div>

          <div style="margin-top: 12px; background: var(--primary-light); padding: 14px; border-radius: 12px;">
            <strong>💬 Conversation for Eleanor & Leo:</strong>
            <p>“Ask your buddy: Did your family have a special warm tea or herbal remedy when you had a restless night or a tummy ache?”</p>
          </div>
        </div>
      </div>
    </div>
  `;
}

function analyzePhoto(name) {
  showToast(`Analyzing ${name}...`);
  setTimeout(() => renderSeniorPhoto(), 400);
}

// ------------------------------------
// CALM BREATHING (1-MINUTE GUIDED EXERCISE)
// ------------------------------------
let breathingState = 'idle'; // 'idle', 'running', 'paused', 'completed'
let breathingSecondsLeft = 60;
let breathingInterval = null;
let breathingVoiceEnabled = true;
let currentCycleTime = 0; // 0 to 9 in each 10s cycle

function updateActiveNav(name) {
  document.querySelectorAll('.nav-link, .bottom-tab').forEach(el => {
    if (el.innerText.toLowerCase().includes(name.toLowerCase())) {
      el.classList.add('active');
    } else {
      el.classList.remove('active');
    }
  });
}

function renderSeniorBreathing() {
  updateActiveNav('breathe');
  const container = document.getElementById('appContent');
  if (!container) return;

  const cycleNum = Math.min(6, Math.floor((60 - breathingSecondsLeft) / 10) + 1);
  const cycleSec = (60 - breathingSecondsLeft) % 10;
  
  let phase = 'inhale';
  let phaseText = 'Breathe In...';
  let phaseSub = 'Inhale slowly through your nose (4s)';
  
  if (breathingState === 'idle') {
    phaseText = 'Ready to Relax?';
    phaseSub = 'Tap Start for 1 minute of gentle breathing';
  } else if (breathingState === 'completed') {
    phaseText = 'Session Complete! 🌸';
    phaseSub = 'Wonderful! +15 Calmness Points awarded';
  } else {
    if (cycleSec < 4) {
      phase = 'inhale';
      phaseText = 'Breathe In...';
      phaseSub = 'Feel your chest and abdomen rise';
    } else if (cycleSec < 6) {
      phase = 'hold';
      phaseText = 'Hold Gently...';
      phaseSub = 'Rest comfortably for 2 seconds';
    } else {
      phase = 'exhale';
      phaseText = 'Slowly Release...';
      phaseSub = 'Exhale gently through your mouth (4s)';
    }
  }

  container.innerHTML = `
    <div class="card" style="background: #f0fdfa; border-color: #5eead4;">
      <h2 class="card-title" style="color: #0f766e;">🧘 Calm Breathing Exercise</h2>
      <p class="card-subtitle" style="color: #115e59;">1-minute guided deep breathing to relieve anxiety and soothe tension</p>
      <button class="btn-read-aloud" onclick="speakText('Welcome to calm breathing. Follow the expanding and contracting circle. Inhale for four seconds, hold for two, and exhale for four seconds.')">
        🔊 Read instructions aloud
      </button>
    </div>

    <div class="breathing-box">
      <div style="display: flex; justify-content: space-between; align-items: center; width: 100%; max-width: 480px; margin-bottom: 8px;">
        <span style="font-size: 19px; font-weight: 700; color: var(--primary);">
          ${breathingState === 'completed' ? 'All 6 Cycles Finished' : `Cycle ${cycleNum} of 6`}
        </span>
        <span style="font-size: 20px; font-weight: 800; color: #0d9488; background: var(--primary-light); padding: 4px 14px; border-radius: 20px;">
          ⏱️ ${breathingSecondsLeft}s remaining
        </span>
      </div>

      <div class="breathing-visual-stage">
        <div class="breathing-ring-outer"></div>
        <div class="breathing-orb ${breathingState === 'running' ? phase : ''}" id="breathingOrb">
          <div class="breathing-phase-text" id="phaseTitle">${phaseText}</div>
          <div class="breathing-sub-text" id="phaseDesc">${phaseSub}</div>
        </div>
      </div>

      <div style="margin-top: 10px; width: 100%; max-width: 480px;">
        ${breathingState === 'idle' ? `
          <button class="btn-primary" style="width: 100%; min-height: 64px; font-size: 22px; background: #0d9488;" onclick="startBreathing()">
            ▶ Start 1-Minute Breathing
          </button>
        ` : breathingState === 'running' ? `
          <div style="display: flex; gap: 12px;">
            <button class="btn-primary" style="flex: 2; min-height: 64px; font-size: 20px; background: #e76f51;" onclick="pauseBreathing()">
              ⏸ Pause
            </button>
            <button class="btn-outline" style="flex: 1; min-height: 64px; font-size: 19px;" onclick="resetBreathing()">
              🔄 Reset
            </button>
          </div>
        ` : breathingState === 'paused' ? `
          <div style="display: flex; gap: 12px;">
            <button class="btn-primary" style="flex: 2; min-height: 64px; font-size: 20px; background: #0d9488;" onclick="resumeBreathing()">
              ▶ Resume Exercise
            </button>
            <button class="btn-outline" style="flex: 1; min-height: 64px; font-size: 19px;" onclick="resetBreathing()">
              🔄 Reset
            </button>
          </div>
        ` : `
          <button class="btn-primary" style="width: 100%; min-height: 64px; font-size: 22px; background: #0d9488;" onclick="startBreathing()">
            🌿 Breathe Again (1 Min)
          </button>
        `}

        <button class="btn-outline" style="width: 100%; min-height: 52px; font-size: 17px; margin-top: 12px;" onclick="toggleBreathingVoice()">
          ${breathingVoiceEnabled ? '🔊 Voice Prompts: ON' : '🔈 Voice Prompts: OFF'}
        </button>
      </div>
    </div>

    <div class="card" style="margin-top: 20px; background: var(--surface-variant);">
      <div style="display: flex; align-items: flex-start; gap: 14px;">
        <span style="font-size: 32px;">🩺</span>
        <div>
          <h3 style="font-size: 20px; font-weight: 800; color: var(--primary); margin-bottom: 4px;">Why 1-Minute Deep Breathing Works</h3>
          <p style="font-size: 17px; color: var(--text-muted); line-height: 1.55;">
            Six rhythmic 10-second cycles stimulate your parasympathetic nervous system via the vagus nerve. 
            This naturally slows your resting heart rate, reduces muscle tension, and lowers cortisol stress markers within 60 seconds.
          </p>
        </div>
      </div>
    </div>
  `;
}

function startBreathing() {
  breathingSecondsLeft = 60;
  breathingState = 'running';
  currentCycleTime = 0;
  playTone(440, 0.2);
  if (breathingVoiceEnabled) speakText('Breathe in slowly.');
  
  clearInterval(breathingInterval);
  breathingInterval = setInterval(breathingTick, 1000);
  renderSeniorBreathing();
}

function pauseBreathing() {
  breathingState = 'paused';
  clearInterval(breathingInterval);
  renderSeniorBreathing();
}

function resumeBreathing() {
  breathingState = 'running';
  clearInterval(breathingInterval);
  breathingInterval = setInterval(breathingTick, 1000);
  renderSeniorBreathing();
}

function resetBreathing() {
  breathingState = 'idle';
  breathingSecondsLeft = 60;
  clearInterval(breathingInterval);
  renderSeniorBreathing();
}

function toggleBreathingVoice() {
  breathingVoiceEnabled = !breathingVoiceEnabled;
  renderSeniorBreathing();
}

function breathingTick() {
  breathingSecondsLeft--;
  currentCycleTime = (currentCycleTime + 1) % 10;

  if (breathingSecondsLeft <= 0) {
    clearInterval(breathingInterval);
    breathingState = 'completed';
    breathingSecondsLeft = 0;
    state.childPoints += 15;
    playTone(523.25, 0.5);
    if (breathingVoiceEnabled) speakText('Wonderful job. You completed one minute of calm breathing.');
    showToast('🌿 Calm Breathing Completed! +15 Points');
    renderSeniorBreathing();
    return;
  }

  // Voice cues at phase transitions
  if (breathingVoiceEnabled) {
    if (currentCycleTime === 0) {
      playTone(440, 0.15); // A4
      speakText('Breathe in.');
    } else if (currentCycleTime === 4) {
      playTone(554.37, 0.15); // C#5
      speakText('Hold.');
    } else if (currentCycleTime === 6) {
      playTone(392.00, 0.15); // G4
      speakText('Slowly breathe out.');
    }
  }

  renderSeniorBreathing();
}

// Gentle serene audio chime
function playTone(freq, dur) {
  try {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) return;
    const ctx = new AudioContext();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(freq, ctx.currentTime);
    gain.gain.setValueAtTime(0.08, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + dur);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + dur);
  } catch (e) {
    // Audio context may be restricted before user gesture
  }
}

// ------------------------------------
// CHILD & PARENT VIEWS
// ------------------------------------
function renderChildView() {
  return `
    <div class="card" style="background: #f3e8ff; border-color: #c084fc;">
      <h2 class="card-title" style="color: #581c87;">Level 4: Story Explorer 🚀</h2>
      <p class="card-subtitle" style="color: #6b21a8;">${state.childPoints} Star Points • 60 pts to Level 5</p>
      <div style="background: #ddd6fe; height: 12px; border-radius: 6px; overflow: hidden;">
        <div style="background: #7c3aed; height: 100%; width: 75%;"></div>
      </div>
    </div>

    <div class="card">
      <h3 class="card-title">Daily Missions 🎯</h3>
      ${state.missions.map(m => `
        <div style="background: ${m.done ? 'var(--success-bg)' : 'var(--surface-variant)'}; padding: 14px; border-radius: var(--radius-md); margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
          <div>
            <strong>${m.done ? '✓ ' : ''}${m.title}</strong>
            <div style="font-size: 15px; color: var(--text-muted);">${m.desc}</div>
          </div>
          ${!m.done ? `<button class="btn-primary" style="min-height: 44px; width: auto; padding: 8px 16px;" onclick="completeMission('${m.id}')">+${m.pts}★</button>` : '<span style="color: var(--success); font-weight: 700;">Completed</span>'}
        </div>
      `).join('')}
    </div>
  `;
}

function completeMission(id) {
  const m = state.missions.find(x => x.id === id);
  if (m) {
    m.done = true;
    state.childPoints += m.pts;
    renderApp();
    showToast(`Mission Accomplished! +${m.pts} Points!`);
  }
}

function renderParentView() {
  return `
    <div class="card" style="background: #eff6ff; border-color: #93c5fd;">
      <h2 class="card-title" style="color: #1e3a8a;">🛡️ Parent Safety Dashboard</h2>
      <p class="card-subtitle" style="color: #1d4ed8;">Children can only interact with verified buddies approved by you.</p>
    </div>

    <div class="card">
      <h3 class="card-title">Pending Friendship Approvals</h3>
      ${state.friendRequests.filter(r => r.status === 'pending').map(r => `
        <div style="border: 1px solid var(--border-color); padding: 16px; border-radius: var(--radius-md); margin-bottom: 12px;">
          <div style="font-weight: 800; font-size: 20px;">${r.name}</div>
          <div style="color: var(--primary); font-weight: 600;">Interests: ${r.interests.join(', ')}</div>
          <p style="font-size: 16px; color: var(--text-muted); margin: 6px 0;">${r.bio}</p>
          <div style="display: flex; gap: 10px; margin-top: 10px;">
            <button class="btn-primary" style="flex: 1; background: var(--success);" onclick="approveRequest('${r.id}')">Approve Connection</button>
            <button class="btn-outline" style="flex: 1;" onclick="declineRequest('${r.id}')">Decline</button>
          </div>
        </div>
      `).join('')}
    </div>
  `;
}

function approveRequest(id) {
  const r = state.friendRequests.find(x => x.id === id);
  if (r) {
    r.status = 'approved';
    renderApp();
    showToast('Safety Approved! Connection is now active.');
  }
}

function declineRequest(id) {
  const r = state.friendRequests.find(x => x.id === id);
  if (r) {
    r.status = 'declined';
    renderApp();
    showToast('Request declined.');
  }
}

// Initial boot
window.addEventListener('DOMContentLoaded', () => {
  renderApp();
});

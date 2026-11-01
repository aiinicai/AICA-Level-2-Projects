// Generations Connect - Progressive Web App Client
const state = {
  currentProfile: 'landing', // senior, child, parent, landing (everyone starts on the simple Login page)
  theme: 'light',
  voiceModeEnabled: true, // Voice mode is DEFAULT setting
  registeredUsers: [
    { phone: '9876543210', name: 'Eleanor Vance', role: 'senior', lockType: 'passcode', passcode: '1234' },
    { phone: '9123456780', name: 'Leo Miller', role: 'child', lockType: 'pattern', pattern: [1, 2, 3, 6] },
    { phone: '9988776655', name: 'Sarah Vance', role: 'parent', lockType: 'face', passcode: '' }
  ],
  currentUser: null, // set by the age-based login: { name, age, role }
  gallery: [],       // photos posted from Photo Studio: { id, owner, dataUrl, caption, date }
  buddyListOpen: false,
  authActiveTab: 'login', // 'login' or 'register'
  authLockType: 'passcode', // 'passcode', 'face', 'pattern'
  enteredPin: '',
  selectedPattern: [],
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
  lastUndoneMed: null,
  seniorMilestones: [
    {
      id: 'sm_med_routine',
      title: 'Morning Sunshine',
      category: 'meds',
      desc: 'Take morning doses consistently with breakfast',
      icon: '🌅',
      unlocked: true,
      progress: 1,
      target: 1,
      date: 'Yesterday',
      affirmation: 'Your regular morning routine sets a calm, energizing foundation for the whole day.'
    },
    {
      id: 'sm_med_7day',
      title: '7-Day Golden Rhythm',
      category: 'meds',
      desc: 'Complete all scheduled doses for 7 days in a row',
      icon: '✨',
      unlocked: false,
      progress: 6,
      target: 7,
      date: null,
      affirmation: 'Consistency is your greatest wellness ally. You are just one day away from this golden milestone!'
    },
    {
      id: 'sm_med_hydration',
      title: 'Hydration Guardian',
      category: 'meds',
      desc: 'Always take medications with a full glass of water',
      icon: '💧',
      unlocked: true,
      progress: 5,
      target: 5,
      date: '3 days ago',
      affirmation: 'Nourishing your body with plenty of water protects your kidneys and aids gentle absorption.'
    },
    {
      id: 'sm_med_evening',
      title: 'Evening Serenity',
      category: 'meds',
      desc: 'Take your evening wellness doses before winding down',
      icon: '🌙',
      unlocked: true,
      progress: 5,
      target: 5,
      date: 'Oct 29',
      affirmation: 'A thoughtful evening routine prepares your body for peaceful, restorative sleep.'
    },
    {
      id: 'sm_diary_first',
      title: 'Reflective Soul',
      category: 'diary',
      desc: 'Record your daily feelings and moments of gratitude',
      icon: '🌸',
      unlocked: true,
      progress: 3,
      target: 3,
      date: 'Oct 30',
      affirmation: 'Reflecting on your day nurtures emotional peace and celebrates life\'s small joys.'
    },
    {
      id: 'sm_diary_voice',
      title: 'Voice of Wisdom',
      category: 'diary',
      desc: 'Record 3 spoken voice memoirs shared with young buddy',
      icon: '🎙️',
      unlocked: true,
      progress: 3,
      target: 3,
      date: 'Oct 28',
      affirmation: 'The sound of your voice carries comfort, family history, and timeless love to young ears.'
    },
    {
      id: 'sm_diary_reflections',
      title: 'Memoir Keeper',
      category: 'diary',
      desc: 'Write 7 thoughtful journal reflections',
      icon: '📖',
      unlocked: false,
      progress: 5,
      target: 7,
      date: null,
      affirmation: 'Every thought and memory you record is a cherished bridge between generations.'
    },
    {
      id: 'sm_breath_first',
      title: 'Gentle Breath',
      category: 'breath',
      desc: 'Complete a 1-minute guided deep breathing exercise',
      icon: '🌿',
      unlocked: true,
      progress: 1,
      target: 1,
      date: 'Today',
      affirmation: 'Taking one quiet minute to breathe deeply slows the heart and calms the wandering mind.'
    },
    {
      id: 'sm_breath_vagus',
      title: 'Vagus Harmony',
      category: 'breath',
      desc: 'Complete 5 mindful breathing sessions',
      icon: '🧘',
      unlocked: true,
      progress: 5,
      target: 5,
      date: 'Yesterday',
      affirmation: 'Deep belly breathing activates your vagal response, gently easing tension and soothing the body.'
    },
    {
      id: 'sm_breath_harbor',
      title: 'Sanctuary of Peace',
      category: 'breath',
      desc: 'Practice 10 mindful breathing exercises across the month',
      icon: '🕊️',
      unlocked: false,
      progress: 7,
      target: 10,
      date: null,
      affirmation: 'You are cultivating a steady sanctuary of stillness within yourself each day.'
    },
    {
      id: 'sm_wellness_trio',
      title: 'Daily Harmony Trio',
      category: 'wellness',
      desc: 'Complete medicines, diary reflection, and calm breathing in one day',
      icon: '🌺',
      unlocked: true,
      progress: 3,
      target: 3,
      date: 'Today',
      affirmation: 'Caring for your body, heart, and breath creates a wonderful day of holistic balance.'
    },
    {
      id: 'sm_wellness_beacon',
      title: 'Inspiring Beacon',
      category: 'wellness',
      desc: 'Inspire your buddy Leo by celebrating 8 wellness milestones',
      icon: '⭐',
      unlocked: true,
      progress: 8,
      target: 8,
      date: 'Today',
      affirmation: 'Leo says: "Grandma Eleanor, your badges make me so proud of how well you take care of yourself!"'
    }
  ]
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

  document.body.classList.toggle('logged-out', state.currentProfile === 'landing' || !state.currentUser);
  const badge = document.getElementById('profileBadgeText');
  if (badge) {
    const u = state.currentUser;
    const mode = { senior: 'Senior', child: 'Kids', parent: 'Parent' }[state.currentProfile];
    badge.innerText = u && mode ? `${mode} Mode • ${u.name} (${u.age})` : 'Welcome';
  }

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
  // Kids and parents never land on the senior home (it has Medicines); send them to their own home.
  if (state.currentUser && state.currentProfile !== 'senior') { renderApp(); return ''; }
  if (typeof recordNav === 'function') recordNav(renderSeniorHome);
  updateActiveNav('home');
  const container = document.getElementById('appContent');
  const taken = state.medications.filter(m => m.status === 'taken').length;
  const total = state.medications.length;
  const overdue = state.medications.find(m => m.status === 'overdue');
  const pct = Math.round((taken / total) * 100);
  const unlockedBadges = state.seniorMilestones.filter(m => m.unlocked).length;

  const html = `
    <div class="card" style="background: var(--primary-light); border-color: var(--primary);">
      <h2 class="card-title">Hello, ${gcEsc(firstName())}! 🌸</h2>
      <p class="card-subtitle">Your day at a glance • Tap any shortcut below</p>
      <button class="btn-read-aloud" onclick="speakText('Hello ${gcEsc(firstName())}. You have taken ${taken} of ${total} medicines today, and celebrated ${unlockedBadges} wellness milestones. Tap any shortcut below to begin.')">
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

    <!-- Senior Milestones Positive Reinforcement Card -->
    <div class="card" style="background: #fffbeb; border: 2px solid #fde68a; cursor: pointer;" onclick="renderSeniorMilestones()">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
        <div style="display: flex; align-items: center; gap: 12px;">
          <span style="font-size: 32px; background: #fef3c7; border-radius: 50%; padding: 8px;">🌟</span>
          <div>
            <h3 style="font-size: 22px; font-weight: 800; color: #78350f; margin: 0;">Senior Milestones & Encouragement</h3>
            <p style="color: #b45309; font-size: 16px; margin: 2px 0 0;">${unlockedBadges} of ${state.seniorMilestones.length} Badges Celebrated • 7-Day Consistency</p>
          </div>
        </div>
        <span style="font-weight: 800; font-size: 18px; color: #d97706;">View Badges ❯</span>
      </div>
      <p style="font-size: 17px; color: #92400e; font-style: italic; margin-top: 8px;">
        “Consistency is a quiet form of self-love. Eleanor, your steady rhythm of taking medicines, writing memories, and calm breathing inspires Leo every day.”
      </p>
    </div>

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
      <div class="shortcut-tile" onclick="renderSeniorMilestones()">
        <span class="tile-icon">🏆</span>
        <div>
          <div class="tile-title">Milestones</div>
          <div class="tile-sub">${unlockedBadges} Badges</div>
        </div>
      </div>
      <div class="shortcut-tile" onclick="renderSeniorDiary()">
        <span class="tile-icon">📖</span>
        <div>
          <div class="tile-title">Daily Diary</div>
          <div class="tile-sub">Record mood & voice</div>
        </div>
      </div>
      <div class="shortcut-tile" onclick="renderSeniorBreathing()">
        <span class="tile-icon">🧘</span>
        <div>
          <div class="tile-title">Calm Breathing</div>
          <div class="tile-sub">1-min guided exercise</div>
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
          <div class="tile-sub">Snap & post to gallery</div>
        </div>
      </div>
      <div class="shortcut-tile" onclick="renderMusicStudio()">
        <span class="tile-icon">🎵</span>
        <div>
          <div class="tile-title">Music Studio</div>
          <div class="tile-sub">Sitar & Tabla</div>
        </div>
      </div>
      <div class="shortcut-tile" onclick="renderMakeBuddy()">
        <span class="tile-icon">💗</span>
        <div>
          <div class="tile-title">Make a Buddy</div>
          <div class="tile-sub">Little Hearts</div>
        </div>
      </div>
      <div class="shortcut-tile" onclick="setProfile('parent')">
        <span class="tile-icon">🛡️</span>
        <div>
          <div class="tile-title">Safety Hub</div>
          <div class="tile-sub">Approvals & Buddies</div>
        </div>
      </div>
      <div class="shortcut-tile" onclick="webLogOff()">
        <span class="tile-icon">🚪</span>
        <div>
          <div class="tile-title">Log Off</div>
          <div class="tile-sub">Switch User Account</div>
        </div>
      </div>
    </div>
  `;
  if (container) container.innerHTML = html;
  if (state.voiceModeEnabled && !state._spokeSeniorWelcome) {
    speakText(`Hello ${firstName()}. Welcome to Generations Connect. You have taken ${taken} of ${total} medicines today. Tap any shortcut below.`);
    state._spokeSeniorWelcome = true;
  }
  return html;
}


function renderSeniorMedicines() {
  if (state.currentProfile === 'child') { goHome(); return; } // medicines are not part of the kids login
  if (typeof recordNav === 'function') recordNav(renderSeniorMedicines);
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

function renderSeniorMilestones() {
  if (typeof recordNav === 'function') recordNav(renderSeniorMilestones);
  const container = document.getElementById('appContent');
  if (!container) return;
  const unlocked = state.seniorMilestones.filter(m => m.unlocked).length;
  const total = state.seniorMilestones.length;

  container.innerHTML = `
    <div class="card" style="background: #FFFDF9; border: 2.5px solid #D4AF37;">
      <h2 class="card-title" style="color: #4A6B53;">🏆 Senior Milestones & Encouragement</h2>
      <p class="card-subtitle">Gentle recognition for your daily wellness habits • ${unlocked} of ${total} Badges Unlocked</p>
      <button class="btn-read-aloud" onclick="speakText('Senior Milestones. You have celebrated ${unlocked} of ${total} wellness milestones. Eleanor, your steady rhythm of taking medicines, writing reflections, and calm breathing inspires Leo every day.')">
        🔊 Read milestones aloud
      </button>
    </div>

    <div class="card" style="background: #FFFDF9; border: 2.5px solid var(--border-color);">
      <h3 style="font-size: 20px; font-weight: 800; margin-bottom: 14px;">Badges & Gentle Encouragement</h3>
      <div style="display: flex; flex-direction: column; gap: 14px;">
        ${state.seniorMilestones.map(m => `
          <div style="border: 2px solid ${m.unlocked ? '#4A6B53' : 'var(--border-color)'}; background: ${m.unlocked ? '#E8F0EA' : 'var(--surface-variant)'}; border-radius: 16px; padding: 16px;">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
              <div style="display: flex; align-items: center; gap: 12px;">
                <span style="font-size: 32px; background: #fff; border-radius: 50%; padding: 6px; box-shadow: 0 2px 6px rgba(0,0,0,0.1);">${m.icon}</span>
                <div>
                  <h4 style="font-size: 19px; font-weight: 800; margin: 0; color: #1C271E;">${m.title}</h4>
                  <p style="font-size: 15px; color: var(--text-muted); margin: 2px 0 0;">${m.desc}</p>
                </div>
              </div>
              <span style="font-weight: 800; font-size: 15px; color: ${m.unlocked ? '#15803D' : '#64748B'};">
                ${m.unlocked ? `Unlocked ✓ ${m.date || ''}` : `${m.progress}/${m.target}`}
              </span>
            </div>
            <p style="font-size: 15px; color: #4A6B53; font-style: italic; margin: 8px 0 0; background: rgba(255,255,255,0.7); padding: 8px 12px; border-radius: 8px;">
              “${m.affirmation}”
            </p>
          </div>
        `).join('')}
      </div>
    </div>
  `;
}

function advanceWebMilestone(id, amount = 1) {
  const m = state.seniorMilestones.find(x => x.id === id);
  if (m) {
    m.progress = Math.min(m.target, m.progress + amount);
    if (m.progress >= m.target && !m.unlocked) {
      m.unlocked = true;
      m.date = 'Today';
      showToast(`🌟 Milestone Celebrated: ${m.title}!`);
      playTone(523.25, 0.4);
    }
  }
}

function takeMed(id) {
  const m = state.medications.find(x => x.id === id);
  if (m) {
    state.lastUndoneMed = { ...m };
    m.status = 'taken';
    m.takenAt = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    advanceWebMilestone('sm_med_routine', 1);
    advanceWebMilestone('sm_med_7day', 1);
    renderSeniorMedicines();
    showToast(`Marked ${m.name} as taken! Milestone progress updated.`);
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
// DAILY DIARY & MEMOIRS
// ------------------------------------
let selectedDiaryMood = '😊';
let selectedDiaryMoodLabel = 'Joyful & Grateful';

function selectDiaryMood(emoji, label) {
  selectedDiaryMood = emoji;
  selectedDiaryMoodLabel = label;
  document.querySelectorAll('.diary-mood-btn').forEach(btn => {
    if (btn.innerText.includes(emoji)) {
      btn.style.background = 'var(--primary)';
      btn.style.color = '#fff';
    } else {
      btn.style.background = 'var(--surface-variant)';
      btn.style.color = 'var(--text-main)';
    }
  });
}

function renderSeniorDiary() {
  updateActiveNav('diary');
  const container = document.getElementById('appContent');
  if (!container) return;

  container.innerHTML = `
    <div class="card" style="background: #fdf4ff; border-color: #f0abfc;">
      <h2 class="card-title" style="color: #86198f;">📖 Daily Diary & Reflections</h2>
      <p class="card-subtitle" style="color: #701a75;">Preserving your memories, reflections, and sharing warmth with Leo</p>
      <button class="btn-read-aloud" onclick="speakText('Daily diary. What made you smile today? Record your thoughts or listen to your past entries.')">
        🔊 Read prompt aloud
      </button>
    </div>

    <div class="card">
      <h3 style="font-size: 22px; font-weight: 800; margin-bottom: 12px;">How are you feeling today, Eleanor?</h3>
      
      <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px;">
        <button class="diary-mood-btn" style="flex: 1; min-height: 52px; font-size: 20px; border-radius: 12px; border: 1px solid var(--border-color); background: var(--primary); color: #fff; cursor: pointer;" onclick="selectDiaryMood('😊', 'Joyful & Grateful')">😊 Joyful</button>
        <button class="diary-mood-btn" style="flex: 1; min-height: 52px; font-size: 20px; border-radius: 12px; border: 1px solid var(--border-color); background: var(--surface-variant); cursor: pointer;" onclick="selectDiaryMood('😌', 'Peaceful & Calm')">😌 Peaceful</button>
        <button class="diary-mood-btn" style="flex: 1; min-height: 52px; font-size: 20px; border-radius: 12px; border: 1px solid var(--border-color); background: var(--surface-variant); cursor: pointer;" onclick="selectDiaryMood('🌻', 'Inspired')">🌻 Inspired</button>
        <button class="diary-mood-btn" style="flex: 1; min-height: 52px; font-size: 20px; border-radius: 12px; border: 1px solid var(--border-color); background: var(--surface-variant); cursor: pointer;" onclick="selectDiaryMood('🥱', 'Resting')">🥱 Resting</button>
      </div>

      <div style="background: var(--surface-variant); padding: 16px; border-radius: var(--radius-md); margin-bottom: 14px;">
        <label style="font-weight: 700; font-size: 18px; display: block; margin-bottom: 6px;">Today's Reflection Prompt:</label>
        <p style="font-size: 19px; color: var(--primary); font-weight: 600;">“What is a small moment of beauty or gratitude you noticed today?”</p>
      </div>

      <textarea id="diaryInputText" rows="4" style="width: 100%; font-size: 19px; padding: 14px; border-radius: 14px; border: 2px solid var(--border-color); font-family: inherit; margin-bottom: 14px;" placeholder="Write your reflection here or dictate your thoughts..."></textarea>

      <div style="display: flex; gap: 10px;">
        <button class="btn-primary" style="flex: 2;" onclick="saveDiaryEntryWeb()">
          💾 Save & Share with Leo (+20 pts)
        </button>
        <button class="btn-outline" style="flex: 1;" onclick="dictateDiaryVoice()">
          🎙️ Dictate
        </button>
      </div>
    </div>

    <div class="card">
      <h3 class="card-title">Cherished Past Reflections</h3>
      ${state.diaryEntries.map(e => `
        <div style="background: var(--surface-variant); padding: 18px; border-radius: var(--radius-md); margin-bottom: 12px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <div style="font-size: 24px;">${e.emoji} <strong style="font-size: 20px; color: var(--text-main);">${e.mood}</strong></div>
            <span style="font-size: 15px; color: var(--text-muted);">${e.date}</span>
          </div>
          <p style="font-size: 18px; line-height: 1.55; margin-bottom: 10px;">“${e.text}”</p>
          <button class="btn-read-aloud" style="min-height: 44px; padding: 6px 14px; font-size: 16px;" onclick="speakText('${e.text.replace(/'/g, "\\'")}')">
            🔊 Listen to memory
          </button>
        </div>
      `).join('')}
    </div>
  `;
}

function saveDiaryEntryWeb() {
  const input = document.getElementById('diaryInputText');
  const text = input ? input.value.trim() : '';
  if (!text) {
    showToast('Please type or dictate a short reflection to save.');
    return;
  }
  const dateStr = 'Today, ' + new Date().toLocaleDateString([], { month: 'short', day: 'numeric' });
  state.diaryEntries.unshift({
    id: 'd_' + Date.now(),
    date: dateStr,
    emoji: selectedDiaryMood,
    mood: selectedDiaryMoodLabel,
    text: text,
    voiceSec: 30
  });
  advanceWebMilestone('sm_diary_first', 1);
  advanceWebMilestone('sm_diary_reflections', 1);
  state.childPoints += 20;
  showToast('Diary entry saved and shared with buddy Leo! 🌸');
  playTone(523.25, 0.4);
  renderSeniorDiary();
}

function dictateDiaryVoice() {
  const input = document.getElementById('diaryInputText');
  if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
    if (input) input.value = "The warm sunshine on the garden flowers reminded me of my childhood summers in Oregon.";
    showToast('Sample dictation added. (Speech API active in Chrome/Edge)');
    return;
  }
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const recognition = new SpeechRecognition();
  recognition.lang = 'en-US';
  showToast('Listening... Speak your thoughts now.');
  recognition.onresult = (e) => {
    const transcript = e.results[0][0].transcript;
    if (input) input.value = transcript;
    showToast('Voice transcribed successfully!');
  };
  recognition.start();
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
  if (typeof recordNav === 'function') recordNav(renderSeniorPhoto);
  const container = document.getElementById('appContent');
  if (!container) return;
  const me = state.currentUser;
  const mine = state.gallery.filter(g => me && g.owner === me.name);

  container.innerHTML = `
    <div class="card">
      <h2 class="card-title">📷 Photo Studio</h2>
      <p class="card-subtitle">Take a photo or choose one, add a few words, then post it to Your Gallery.</p>
      <div class="photo-actions">
        <label class="btn-primary photo-pick">📷 Take a photo
          <input type="file" accept="image/*" capture="environment" hidden onchange="handlePhotoPicked(this)">
        </label>
        <label class="btn-outline photo-pick">🖼️ Choose from device
          <input type="file" accept="image/*" hidden onchange="handlePhotoPicked(this)">
        </label>
      </div>
      <div id="photoPreview"></div>
    </div>

    <div class="card" id="yourGallery">
      <h2 class="card-title">🖼️ Your Gallery</h2>
      ${mine.length === 0
        ? '<p class="card-subtitle">Nothing posted yet. Snap your first photo above!</p>'
        : `<div class="gallery-grid">${mine.map(g => `
            <figure class="gallery-item">
              <img src="${g.dataUrl}" alt="${gcEsc(g.caption || 'Posted photo')}">
              <figcaption>
                <strong>${gcEsc(g.caption || 'Untitled')}</strong>
                <span>${gcEsc(g.date)}</span>
                <button class="btn-outline gallery-del" onclick="deletePhoto('${g.id}')">🗑 Remove</button>
              </figcaption>
            </figure>`).join('')}</div>`}
    </div>

    <div class="card">
      <h3 class="card-title">🌿 Learn about a plant or keepsake</h3>
      <p class="card-subtitle">Heritage facts to talk about with a buddy</p>
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
            <strong>💬 Conversation starter:</strong>
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

    ${ambientPanelHtml()}

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
// KIDS & SENIOR MUSIC STUDIO (Piano, Kalimba, Sitar, Tabla)
// ------------------------------------
let activeInstrument = 'piano';
let isMusicRecording = false;
let recordedMusicEvents = [];
let recordingStartTime = null;
let musicRecordSecondsLeft = 60;
let musicRecordInterval = null;
let isMelodyPlayingBack = false;

const pianoNotes = [
  { name: 'C4', label: 'C', freq: 261.63, isBlack: false },
  { name: 'C#4', label: 'C#', freq: 277.18, isBlack: true, left: '9%' },
  { name: 'D4', label: 'D', freq: 293.66, isBlack: false },
  { name: 'D#4', label: 'D#', freq: 311.13, isBlack: true, left: '23%' },
  { name: 'E4', label: 'E', freq: 329.63, isBlack: false },
  { name: 'F4', label: 'F', freq: 349.23, isBlack: false },
  { name: 'F#4', label: 'F#', freq: 369.99, isBlack: true, left: '52%' },
  { name: 'G4', label: 'G', freq: 392.00, isBlack: false },
  { name: 'G#4', label: 'G#', freq: 415.30, isBlack: true, left: '66%' },
  { name: 'A4', label: 'A', freq: 440.00, isBlack: false },
  { name: 'A#4', label: 'A#', freq: 466.16, isBlack: true, left: '80%' },
  { name: 'B4', label: 'B', freq: 493.88, isBlack: false },
  { name: 'C5', label: 'C5', freq: 523.25, isBlack: false }
];

const kalimbaTines = [
  { note: 'D4', freq: 293.66, height: 140 },
  { note: 'B4', freq: 493.88, height: 160 },
  { note: 'G4', freq: 392.00, height: 180 },
  { note: 'E4', freq: 329.63, height: 200 },
  { note: 'C4', freq: 261.63, height: 220 },
  { note: 'D4', freq: 293.66, height: 200 },
  { note: 'F4', freq: 349.23, height: 180 },
  { note: 'A4', freq: 440.00, height: 160 },
  { note: 'C5', freq: 523.25, height: 140 }
];

const sitarFrets = [
  { swara: 'Sa', note: 'C4', freq: 261.63 },
  { swara: 'Re (Komal)', note: 'Db4', freq: 277.18 },
  { swara: 'Re', note: 'D4', freq: 293.66 },
  { swara: 'Ga', note: 'E4', freq: 329.63 },
  { swara: 'Ma (Teevra)', note: 'F#4', freq: 369.99 },
  { swara: 'Pa', note: 'G4', freq: 392.00 },
  { swara: 'Dha', note: 'A4', freq: 440.00 },
  { swara: 'Ni', note: 'B4', freq: 493.88 },
  { swara: 'Sa’', note: 'C5', freq: 523.25 }
];

const tablaBols = [
  { bol: 'Ghe (Bass Drop)', drum: 'bayan', freq: 140, type: 'bayan' },
  { bol: 'Kat (Damped Bass)', drum: 'bayan', freq: 90, type: 'bayan-tap' },
  { bol: 'Tin (Open Rim)', drum: 'dayan', freq: 440, type: 'dayan' },
  { bol: 'Na (Rim Sharp)', drum: 'dayan', freq: 523, type: 'dayan' },
  { bol: 'Tun (Resonant Open)', drum: 'dayan', freq: 349, type: 'dayan' },
  { bol: 'Dha (Both Together)', drum: 'both', freq: 140, type: 'both' }
];

function playInstrumentSound(inst, label, freq, type) {
  try {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) return;
    const ctx = new AudioContext();
    const now = ctx.currentTime;

    if (inst === 'piano') {
      const osc1 = ctx.createOscillator();
      const osc2 = ctx.createOscillator();
      const gain = ctx.createGain();
      osc1.type = 'triangle';
      osc2.type = 'sine';
      osc1.frequency.setValueAtTime(freq, now);
      osc2.frequency.setValueAtTime(freq * 2, now);
      gain.gain.setValueAtTime(0.2, now);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + 1.2);
      osc1.connect(gain);
      osc2.connect(gain);
      gain.connect(ctx.destination);
      osc1.start(now);
      osc2.start(now);
      osc1.stop(now + 1.2);
      osc2.stop(now + 1.2);
    } else if (inst === 'kalimba') {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(freq, now);
      gain.gain.setValueAtTime(0.25, now);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + 1.5);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(now);
      osc.stop(now + 1.5);
    } else if (inst === 'sitar') {
      // Sitar with jawari buzz and pitch bend
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      const filter = ctx.createBiquadFilter();
      osc.type = 'sawtooth';
      // subtle meend bend
      osc.frequency.setValueAtTime(freq * 0.98, now);
      osc.frequency.exponentialRampToValueAtTime(freq, now + 0.08);
      filter.type = 'bandpass';
      filter.frequency.setValueAtTime(freq * 2.2, now);
      filter.Q.setValueAtTime(4, now);
      gain.gain.setValueAtTime(0.18, now);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + 1.4);
      osc.connect(filter);
      filter.connect(gain);
      gain.connect(ctx.destination);
      osc.start(now);
      osc.stop(now + 1.4);
    } else if (inst === 'tabla') {
      if (type === 'bayan' || type === 'both') {
        // Bass drop: start high (150Hz) and glide down to 68Hz
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(145, now);
        osc.frequency.exponentialRampToValueAtTime(65, now + 0.18);
        gain.gain.setValueAtTime(0.4, now);
        gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.6);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(now);
        osc.stop(now + 0.6);
      }
      if (type === 'dayan' || type === 'both' || type === 'dayan-tap') {
        // Treble rim bell ping
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(freq || 392, now);
        gain.gain.setValueAtTime(0.28, now);
        gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.45);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(now);
        osc.stop(now + 0.45);
      }
    }

    // If recording, log event
    if (isMusicRecording) {
      const eventTime = Date.now() - recordingStartTime;
      recordedMusicEvents.push({ inst, label, freq, type, time: eventTime });
      const counterEl = document.getElementById('recordedNotesCount');
      if (counterEl) counterEl.innerText = `${recordedMusicEvents.length} notes recorded`;
    }
  } catch (e) {
    console.error('Audio playback error', e);
  }
}

function startMusicRecording() {
  isMusicRecording = true;
  recordedMusicEvents = [];
  recordingStartTime = Date.now();
  musicRecordSecondsLeft = 60;
  clearInterval(musicRecordInterval);

  musicRecordInterval = setInterval(() => {
    musicRecordSecondsLeft--;
    const timerEl = document.getElementById('musicRecordTimer');
    if (timerEl) timerEl.innerText = `⏱️ ${musicRecordSecondsLeft}s left`;
    if (musicRecordSecondsLeft <= 0) {
      stopMusicRecording();
      showToast('60-second song composition finished! Tap Play or Gift.');
    }
  }, 1000);

  renderMusicStudio(activeInstrument);
  showToast('🔴 Recording started! Play notes on any instrument.');
}

function stopMusicRecording() {
  isMusicRecording = false;
  clearInterval(musicRecordInterval);
  renderMusicStudio(activeInstrument);
}

function playRecordedMelody() {
  if (recordedMusicEvents.length === 0) {
    showToast('No notes recorded yet. Tap Start 1-Min Recording!');
    return;
  }
  isMelodyPlayingBack = true;
  showToast(`▶ Playing back ${recordedMusicEvents.length} notes...`);

  recordedMusicEvents.forEach(evt => {
    setTimeout(() => {
      playInstrumentSound(evt.inst, evt.label, evt.freq, evt.type);
    }, evt.time);
  });

  const lastNoteTime = recordedMusicEvents[recordedMusicEvents.length - 1].time + 1200;
  setTimeout(() => {
    isMelodyPlayingBack = false;
    showToast('Playback complete! 🎶');
  }, lastNoteTime);
}

function giftMelodyToEleanor() {
  if (recordedMusicEvents.length === 0) {
    showToast('Play and record a few notes first before gifting!');
    return;
  }
  state.childPoints += 35;
  state.diaryEntries.unshift({
    id: 'd_song_' + Date.now(),
    date: 'Today, Just Now',
    emoji: '🎶',
    mood: 'Peaceful Melody from Leo',
    text: `Leo composed and gifted a special 1-minute melody using the ${activeInstrument.toUpperCase()}! It has ${recordedMusicEvents.length} notes. Playing it brought warmth to my morning.`
  });
  showToast('🎁 Melody gifted to Grandma Eleanor! +35 Star Points ⭐');
  playTone(523.25, 0.4);
}

function renderMusicStudio(selectedInst = 'piano') {
  activeInstrument = selectedInst;
  updateActiveNav('music');
  const container = document.getElementById('appContent');
  if (!container) return;

  let instrumentContent = '';

  if (activeInstrument === 'piano') {
    const whiteKeys = pianoNotes.filter(n => !n.isBlack);
    const blackKeys = pianoNotes.filter(n => n.isBlack);
    instrumentContent = `
      <div class="piano-keyboard">
        ${whiteKeys.map(k => `
          <div class="piano-white-key" onclick="playInstrumentSound('piano', '${k.name}', ${k.freq})">
            <span>${k.label}</span>
          </div>
        `).join('')}
        ${blackKeys.map(k => `
          <div class="piano-black-key" style="left: ${k.left};" onclick="playInstrumentSound('piano', '${k.name}', ${k.freq})">
            <span>${k.label}</span>
          </div>
        `).join('')}
      </div>
    `;
  } else if (activeInstrument === 'kalimba') {
    instrumentContent = `
      <div class="kalimba-body">
        <div class="kalimba-soundhole"></div>
        ${kalimbaTines.map(t => `
          <div class="kalimba-tine" style="height: ${t.height}px;" onclick="playInstrumentSound('kalimba', '${t.note}', ${t.freq})">
            <span>${t.note}</span>
          </div>
        `).join('')}
      </div>
    `;
  } else if (activeInstrument === 'sitar') {
    instrumentContent = `
      <div class="sitar-neck">
        <div style="color: #FDE68A; font-weight: 800; text-align: center; margin-bottom: 12px; font-size: 18px;">
          🪕 Indian Classical Sitar • Raag Yaman Notes
        </div>
        <div class="sitar-frets-grid">
          ${sitarFrets.map(f => `
            <div class="sitar-fret-btn" onclick="playInstrumentSound('sitar', '${f.swara}', ${f.freq})">
              <div style="font-size: 20px; font-weight: 800; color: #78350F;">${f.swara}</div>
              <div style="font-size: 13px; color: #92400E;">${f.note}</div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  } else if (activeInstrument === 'tabla') {
    instrumentContent = `
      <div class="tabla-stage">
        <!-- Bayan (Bass Drum) -->
        <div class="drum-container">
          <div class="bayan-drum" onclick="playInstrumentSound('tabla', 'Ghe', 140, 'bayan')">
            <div class="bayan-syahi">Ghe</div>
          </div>
          <strong style="color: var(--primary);">Bāyān (Bass Drum)</strong>
          <span style="font-size: 14px; color: var(--text-muted);">Deep resonating bass drop</span>
        </div>

        <!-- Dayan (Treble Drum) -->
        <div class="drum-container">
          <div class="dayan-drum" onclick="playInstrumentSound('tabla', 'Tin', 440, 'dayan')">
            <div class="dayan-syahi">Tin</div>
          </div>
          <strong style="color: #78350F;">Dāyān (Treble Drum)</strong>
          <span style="font-size: 14px; color: var(--text-muted);">Tuned metallic rim ring</span>
        </div>
      </div>

      <div class="tabla-bol-chips">
        ${tablaBols.map(b => `
          <div class="bol-chip" onclick="playInstrumentSound('tabla', '${b.bol}', ${b.freq}, '${b.type}')">
            ${b.bol}
          </div>
        `).join('')}
      </div>
    `;
  }

  container.innerHTML = `
    <div class="card" style="background: #FFFDF9; border-color: var(--border-color);">
      <!-- Sacred Mandala SVG Watermark -->
      <svg class="mandala-watermark" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="45" fill="none" stroke="#4A6B53" stroke-width="1" />
        <circle cx="50" cy="50" r="32" fill="none" stroke="#D4AF37" stroke-width="1.5" />
        <circle cx="50" cy="50" r="20" fill="none" stroke="#C86446" stroke-width="1" />
        <line x1="50" y1="5" x2="50" y2="95" stroke="#4A6B53" stroke-width="1" />
        <line x1="5" y1="50" x2="95" y2="50" stroke="#4A6B53" stroke-width="1" />
      </svg>

      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
        <h2 class="card-title" style="color: var(--primary); margin-bottom: 0;">🎶 Intergenerational Music Studio</h2>
        <span style="background: var(--primary-light); color: var(--primary); padding: 4px 12px; border-radius: var(--radius-pill); font-weight: 700; font-size: 14px;">
          Authentic Sound Synthesizer
        </span>
      </div>
      <p class="card-subtitle">Play Indian Sitar & Tabla, Kalimba, or Piano. Compose a 1-minute song to gift Grandma Eleanor.</p>

      <!-- Instrument Tabs -->
      <div class="instrument-selector">
        <button class="instrument-tab-btn ${activeInstrument === 'piano' ? 'active' : ''}" onclick="renderMusicStudio('piano')">
          🎹 Piano
        </button>
        <button class="instrument-tab-btn ${activeInstrument === 'kalimba' ? 'active' : ''}" onclick="renderMusicStudio('kalimba')">
          🎶 Kalimba
        </button>
        <button class="instrument-tab-btn ${activeInstrument === 'sitar' ? 'active' : ''}" onclick="renderMusicStudio('sitar')">
          🪕 Indian Sitar
        </button>
        <button class="instrument-tab-btn ${activeInstrument === 'tabla' ? 'active' : ''}" onclick="renderMusicStudio('tabla')">
          🥁 Indian Tabla
        </button>
      </div>

      <!-- Playable Instrument Stage -->
      <div class="instrument-stage">
        ${instrumentContent}
      </div>

      <!-- 60-Second Song Composer & Recorder -->
      <div class="recorder-card">
        <div>
          <div class="recorder-indicator">
            ${isMusicRecording ? '<span class="recording-dot"></span> <span style="color: #DC2626;">Recording Live...</span>' : '<span>🎙️ 1-Minute Song Composer</span>'}
          </div>
          <div style="font-size: 14px; color: var(--text-muted); margin-top: 2px;">
            <span id="musicRecordTimer">⏱️ ${musicRecordSecondsLeft}s remaining</span> • <span id="recordedNotesCount">${recordedMusicEvents.length} notes</span>
          </div>
        </div>

        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
          ${!isMusicRecording ? `
            <button class="btn-primary" style="min-height: 44px; width: auto; padding: 8px 16px; background: #DC2626;" onclick="startMusicRecording()">
              ● Record Song
            </button>
          ` : `
            <button class="btn-primary" style="min-height: 44px; width: auto; padding: 8px 16px; background: #1C271E;" onclick="stopMusicRecording()">
              ■ Stop
            </button>
          `}

          <button class="btn-outline" style="min-height: 44px; padding: 8px 16px;" onclick="playRecordedMelody()" ${recordedMusicEvents.length === 0 ? 'disabled' : ''}>
            ▶ Play
          </button>

          <button class="btn-primary" style="min-height: 44px; width: auto; padding: 8px 18px; background: #C86446;" onclick="giftMelodyToEleanor()">
            🎁 Gift to Eleanor (+35★)
          </button>
        </div>
      </div>
    </div>
  `;
}

// ------------------------------------
// CHILD & PARENT VIEWS
// ------------------------------------
function renderChildView() {
  return `
    <div class="card" style="background: #F3E8FF; border: 2.5px solid #C084FC;">
      <h2 class="card-title" style="color: #581c87;">Level 4: Story Explorer 🚀</h2>
      <p class="card-subtitle" style="color: #6b21a8;">${state.childPoints} Star Points • 60 pts to Level 5</p>
      <div style="background: #ddd6fe; height: 12px; border-radius: 6px; overflow: hidden;">
        <div style="background: #7c3aed; height: 100%; width: 75%;"></div>
      </div>
    </div>

    <div class="shortcut-grid" style="margin-bottom: 20px;">
      <div class="shortcut-tile" onclick="renderMath()">
        <span class="tile-icon">🔢</span>
        <div><div class="tile-title">Math</div><div class="tile-sub">Mental & Kumon</div></div>
      </div>
      <div class="shortcut-tile" onclick="renderSeniorPhoto()">
        <span class="tile-icon">📷</span>
        <div><div class="tile-title">Photo Studio</div><div class="tile-sub">Snap & post</div></div>
      </div>
      <div class="shortcut-tile" onclick="renderMakeBuddy()">
        <span class="tile-icon">🧓</span>
        <div><div class="tile-title">Make a Buddy</div><div class="tile-sub">Grandpals</div></div>
      </div>
      <div class="shortcut-tile" onclick="renderMusicStudio('piano')">
        <span class="tile-icon">🎵</span>
        <div><div class="tile-title">Music Studio</div><div class="tile-sub">Sitar & Tabla</div></div>
      </div>
      <div class="shortcut-tile" onclick="document.getElementById('dailyMissions').scrollIntoView({ behavior: 'smooth' })">
        <span class="tile-icon">🎯</span>
        <div><div class="tile-title">Missions</div><div class="tile-sub">Earn star points</div></div>
      </div>
      <div class="shortcut-tile" onclick="renderSeniorGames()">
        <span class="tile-icon">🎮</span>
        <div><div class="tile-title">Games</div><div class="tile-sub">Memory & paint</div></div>
      </div>
    </div>
    <div class="card">
      <h3 class="card-title" id="dailyMissions">Daily Missions 🎯</h3>
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
    saveFriendRequests();
    renderApp();
    showToast('Safety Approved! Connection is now active.');
  }
}

function declineRequest(id) {
  const r = state.friendRequests.find(x => x.id === id);
  if (r) {
    r.status = 'declined';
    saveFriendRequests();
    renderApp();
    showToast('Request declined.');
  }
}

// ------------------------------------
// NAVIGATION HISTORY & CORNER CONTROLS
// ------------------------------------
const navHistory = [];

function recordNav(fn) {
  if (navHistory.length === 0 || navHistory[navHistory.length - 1] !== fn) {
    navHistory.push(fn);
  }
}

function historyBackOrHome() {
  if (navHistory.length > 1) {
    navHistory.pop(); // Pop current view
    const prevFn = navHistory[navHistory.length - 1];
    if (typeof prevFn === 'function') {
      prevFn();
      return;
    }
  }
  goHome();
}

// Home for whichever profile is logged in (children and parents have their own home view).
function goHome() {
  if (state.currentProfile === 'senior') renderSeniorHome();
  else renderApp();
}

// ------------------------------------
// DEFAULT VOICE MODE TOGGLE
// ------------------------------------
function toggleWebVoiceMode() {
  state.voiceModeEnabled = !state.voiceModeEnabled;
  const btn = document.getElementById('voiceToggleBtn');
  if (btn) {
    btn.innerText = state.voiceModeEnabled ? '🔊 Voice: ON' : '🔇 Voice: OFF';
    btn.style.background = state.voiceModeEnabled ? 'rgba(255,255,255,0.3)' : 'rgba(0,0,0,0.2)';
  }
  if (state.voiceModeEnabled) {
    speakText('Voice mode is now turned on.');
    showToast('Voice mode ON (Default)');
  } else {
    stopSpeaking();
    showToast('Voice mode turned OFF');
  }
}

// ------------------------------------
// AUTHENTICATION (MOBILE, PASSCODE, FACE, PATTERN)
// ------------------------------------
function openAuthModal() {
  state.enteredPin = '';
  state.selectedPattern = [];
  let overlay = document.getElementById('authModalOverlay');
  if (!overlay) {
    overlay = document.createElement('div');
    overlay.id = 'authModalOverlay';
    overlay.className = 'auth-overlay';
    document.body.appendChild(overlay);
  }
  renderAuthModalContent();
}

function closeAuthModal() {
  const overlay = document.getElementById('authModalOverlay');
  if (overlay) overlay.remove();
}

function switchAuthTab(tab) {
  state.authActiveTab = tab;
  state.enteredPin = '';
  state.selectedPattern = [];
  renderAuthModalContent();
}

function switchAuthLockType(type) {
  state.authLockType = type;
  state.enteredPin = '';
  state.selectedPattern = [];
  renderAuthModalContent();
}

function pressPinKeypad(digit) {
  if (state.enteredPin.length < 4) {
    state.enteredPin += digit;
    renderAuthModalContent();
    if (state.enteredPin.length === 4) {
      setTimeout(submitPinLogin, 250);
    }
  }
}

function clearPinKeypad() {
  state.enteredPin = '';
  renderAuthModalContent();
}

function submitPinLogin() {
  const user = state.registeredUsers.find(u => u.lockType === 'passcode' && (u.passcode === state.enteredPin || state.enteredPin === '1234'));
  if (user || state.enteredPin === '1234') {
    const loggedIn = user || state.registeredUsers[0];
    state.currentUser = loggedIn;
    setProfile(loggedIn.role);
    closeAuthModal();
    showToast(`Welcome back, ${loggedIn.name}! Passcode verified.`);
    if (state.voiceModeEnabled) speakText(`Welcome back, ${loggedIn.name}. You are logged in with your passcode.`);
  } else {
    showToast('Incorrect Passcode. Try 1234 or your registered PIN.');
    state.enteredPin = '';
    renderAuthModalContent();
  }
}

function simulateFaceLogin() {
  const scanBox = document.querySelector('.face-scan-box');
  if (scanBox) {
    scanBox.style.borderColor = '#10B981';
  }
  showToast('Scanning face biometric features...');
  setTimeout(() => {
    const user = state.registeredUsers.find(u => u.lockType === 'face') || state.registeredUsers[0];
    state.currentUser = user;
    setProfile(user.role);
    closeAuthModal();
    showToast(`Face biometric match confirmed! Welcome, ${user.name}`);
    if (state.voiceModeEnabled) speakText(`Biometric match verified. Welcome, ${user.name}`);
  }, 1200);
}

function tapPatternDotWeb(dot) {
  if (!state.selectedPattern.includes(dot)) {
    state.selectedPattern.push(dot);
    renderAuthModalContent();
  }
}

function clearPatternWeb() {
  state.selectedPattern = [];
  renderAuthModalContent();
}

function submitPatternLogin() {
  if (state.selectedPattern.length < 3) {
    showToast('Connect at least 3 dots for pattern lock');
    return;
  }
  const user = state.registeredUsers.find(u => u.lockType === 'pattern') || state.registeredUsers[0];
  state.currentUser = user;
  setProfile(user.role);
  closeAuthModal();
  showToast(`Screen pattern verified! Welcome, ${user.name}`);
  if (state.voiceModeEnabled) speakText(`Pattern confirmed. Welcome, ${user.name}`);
}

function submitWebRegister(e) {
  if (e) e.preventDefault();
  const phone = document.getElementById('regPhoneInput')?.value.trim();
  const name = document.getElementById('regNameInput')?.value.trim();
  const role = document.getElementById('regRoleSelect')?.value || 'senior';
  const lockType = document.getElementById('regLockSelect')?.value || 'passcode';
  const code = document.getElementById('regCodeInput')?.value.trim() || '1234';

  if (!phone || phone.length < 8) {
    showToast('Please enter a valid mobile number');
    return;
  }
  if (!name) {
    showToast('Please enter your full name');
    return;
  }

  const newUser = {
    phone: phone,
    name: name,
    role: role,
    lockType: lockType,
    passcode: code,
    pattern: [1, 2, 5, 8]
  };

  state.registeredUsers.push(newUser);
  state.currentUser = newUser;
  setProfile(role);
  closeAuthModal();
  showToast(`Account registered for ${name} (${phone})! Logged in.`);
  if (state.voiceModeEnabled) speakText(`Account registered. Welcome to Generations Connect, ${name}!`);
}

function webLogOff() {
  state.currentUser = null;
  state.currentProfile = 'landing';
  state.buddyListOpen = false;
  state._spokeSeniorWelcome = false;
  navHistory.length = 0;
  document.documentElement.setAttribute('data-profile', 'senior');
  stopSpeaking();
  renderApp();
  window.scrollTo({ top: 0 });
  showToast('Logged off. See you soon!');
}

function renderAuthModalContent() {
  const overlay = document.getElementById('authModalOverlay');
  if (!overlay) return;

  const isLogin = state.authActiveTab === 'login';

  overlay.innerHTML = `
    <div class="auth-modal-card">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
        <h2 style="font-size: 24px; font-weight: 800; color: #1C271E; margin: 0;">🔐 Mobile Access & Security</h2>
        <button onclick="closeAuthModal()" style="background: none; border: none; font-size: 26px; cursor: pointer;">✕</button>
      </div>

      <div class="auth-tabs">
        <button class="auth-tab-btn ${isLogin ? 'active' : ''}" onclick="switchAuthTab('login')">Sign In</button>
        <button class="auth-tab-btn ${!isLogin ? 'active' : ''}" onclick="switchAuthTab('register')">New User Register</button>
      </div>

      ${isLogin ? `
        <!-- LOGIN TAB -->
        <div style="margin-bottom: 14px;">
          <label style="font-weight: 700; font-size: 16px; display: block; margin-bottom: 6px;">Select Lock Method:</label>
          <div class="auth-method-selector">
            <button class="auth-method-btn ${state.authLockType === 'passcode' ? 'active' : ''}" onclick="switchAuthLockType('passcode')">🔢 Passcode</button>
            <button class="auth-method-btn ${state.authLockType === 'face' ? 'active' : ''}" onclick="switchAuthLockType('face')">👁️ Face Lock</button>
            <button class="auth-method-btn ${state.authLockType === 'pattern' ? 'active' : ''}" onclick="switchAuthLockType('pattern')">〰️ Pattern</button>
          </div>
        </div>

        ${state.authLockType === 'passcode' ? `
          <div style="text-align: center; margin: 10px 0;">
            <p style="font-size: 16px; color: var(--text-muted); margin-bottom: 10px;">Enter 4-digit mobile passcode (Default: 1234)</p>
            <div class="pin-display-container">
              <div class="pin-dot ${state.enteredPin.length >= 1 ? 'filled' : ''}"></div>
              <div class="pin-dot ${state.enteredPin.length >= 2 ? 'filled' : ''}"></div>
              <div class="pin-dot ${state.enteredPin.length >= 3 ? 'filled' : ''}"></div>
              <div class="pin-dot ${state.enteredPin.length >= 4 ? 'filled' : ''}"></div>
            </div>

            <div class="keypad-grid">
              ${[1,2,3,4,5,6,7,8,9].map(n => `<button class="keypad-btn" onclick="pressPinKeypad('${n}')">${n}</button>`).join('')}
              <button class="keypad-btn" style="font-size: 16px; color: #DC2626;" onclick="clearPinKeypad()">CLR</button>
              <button class="keypad-btn" onclick="pressPinKeypad('0')">0</button>
              <button class="keypad-btn" style="font-size: 16px; color: #15803D;" onclick="submitPinLogin()">OK</button>
            </div>
          </div>
        ` : ''}

        ${state.authLockType === 'face' ? `
          <div style="text-align: center; margin: 14px 0;">
            <p style="font-size: 16px; color: var(--text-muted); margin-bottom: 12px;">Position face within the viewfinder</p>
            <div class="face-scan-box">
              <div class="face-scanner-line"></div>
              <span style="font-size: 64px;">👤</span>
              <span style="font-size: 14px; font-weight: 700; color: var(--primary); margin-top: 8px;">Look At Camera</span>
            </div>
            <button class="btn-primary" style="margin-top: 14px;" onclick="simulateFaceLogin()">👁️ Scan & Unlock</button>
          </div>
        ` : ''}

        ${state.authLockType === 'pattern' ? `
          <div style="text-align: center; margin: 10px 0;">
            <p style="font-size: 16px; color: var(--text-muted); margin-bottom: 8px;">Connect dots in order: ${state.selectedPattern.join(' ➔ ') || 'Tap at least 3 dots'}</p>
            <div class="pattern-grid">
              ${[1,2,3,4,5,6,7,8,9].map(num => `
                <div class="pattern-dot ${state.selectedPattern.includes(num) ? 'selected' : ''}" onclick="tapPatternDotWeb(${num})">${num}</div>
              `).join('')}
            </div>
            <div style="display: flex; gap: 10px; margin-top: 12px;">
              <button class="btn-outline" style="flex: 1;" onclick="clearPatternWeb()">Clear</button>
              <button class="btn-primary" style="flex: 2;" onclick="submitPatternLogin()">Unlock</button>
            </div>
          </div>
        ` : ''}
      ` : `
        <!-- REGISTER TAB -->
        <form onsubmit="submitWebRegister(event)" style="display: flex; flex-direction: column; gap: 14px;">
          <div>
            <label style="font-weight: 700; font-size: 16px; display: block; margin-bottom: 4px;">Mobile Phone Number</label>
            <input type="tel" id="regPhoneInput" placeholder="e.g. 9876543210" required style="width: 100%; font-size: 18px; padding: 12px; border-radius: 12px; border: 2px solid var(--border-color);" />
          </div>

          <div>
            <label style="font-weight: 700; font-size: 16px; display: block; margin-bottom: 4px;">Full Name</label>
            <input type="text" id="regNameInput" placeholder="e.g. Robert Smith" required style="width: 100%; font-size: 18px; padding: 12px; border-radius: 12px; border: 2px solid var(--border-color);" />
          </div>

          <div>
            <label style="font-weight: 700; font-size: 16px; display: block; margin-bottom: 4px;">Profile Role</label>
            <select id="regRoleSelect" style="width: 100%; font-size: 18px; padding: 12px; border-radius: 12px; border: 2px solid var(--border-color);">
              <option value="senior">👴 Senior (Large Text, Voice-First)</option>
              <option value="child">🧒 Child (Points, Badges, Missions)</option>
              <option value="parent">🛡️ Parent (Safety & Approvals)</option>
            </select>
          </div>

          <div>
            <label style="font-weight: 700; font-size: 16px; display: block; margin-bottom: 4px;">Security Lock Method</label>
            <select id="regLockSelect" style="width: 100%; font-size: 18px; padding: 12px; border-radius: 12px; border: 2px solid var(--border-color);">
              <option value="passcode">Mobile Passcode (PIN)</option>
              <option value="face">Face Lock Biometrics</option>
              <option value="pattern">Screen Pattern Lock</option>
            </select>
          </div>

          <div>
            <label style="font-weight: 700; font-size: 16px; display: block; margin-bottom: 4px;">Set Passcode / Security PIN</label>
            <input type="password" id="regCodeInput" placeholder="e.g. 1234" maxlength="6" style="width: 100%; font-size: 18px; padding: 12px; border-radius: 12px; border: 2px solid var(--border-color);" />
          </div>

          <button type="submit" class="btn-primary" style="margin-top: 10px;">Register & Login</button>
        </form>
      `}
    </div>
  `;
}

// Initial boot
window.addEventListener('DOMContentLoaded', () => {
  renderApp();
});

// ------------------------------------
// COLOUR PALETTES (header "Colors" menu) + page-actions visibility
// ------------------------------------
const PALETTES = [
  { id: 'mustard', name: 'Mustard Yellow', swatch: '#E1AD01' },
  { id: 'salmon', name: 'Salmon Pink', swatch: '#E9857B' },
  { id: 'slate', name: 'Greyish Blue', swatch: '#6F8BA8' },
  { id: 'pearl', name: 'Pearl White', swatch: '#F3F0E8' },
  { id: 'sage', name: 'Light Sage Green', swatch: '#9DB89A' },
  { id: 'original', name: 'Original (per profile)', swatch: '#4A6B53' }
];

function applyPalette(id) {
  const html = document.documentElement;
  if (id === 'original') html.removeAttribute('data-palette');
  else html.setAttribute('data-palette', id);
  try { localStorage.setItem('gc_palette', id); } catch (e) {}
  renderPaletteMenu();
}

function renderPaletteMenu() {
  const menu = document.getElementById('paletteMenu');
  if (!menu) return;
  const current = document.documentElement.getAttribute('data-palette') || 'original';
  menu.innerHTML = PALETTES.map(p => `
    <button class="palette-option ${p.id === current ? 'active' : ''}" role="menuitemradio" aria-checked="${p.id === current}" onclick="applyPalette('${p.id}')">
      <span class="theme-swatch" style="background:${p.swatch}"></span>${p.name}${p.id === current ? ' ✓' : ''}
    </button>`).join('');
}

function togglePaletteMenu(force) {
  const menu = document.getElementById('paletteMenu');
  const btn = document.getElementById('paletteBtn');
  if (!menu) return;
  const open = typeof force === 'boolean' ? force : menu.hidden;
  menu.hidden = !open;
  btn.setAttribute('aria-expanded', String(open));
}
document.addEventListener('click', (e) => {
  if (!e.target.closest('#paletteMenu') && !e.target.closest('#paletteBtn')) togglePaletteMenu(false);
});

// The Back / Top / Log Off row is hidden on the Home screen, which already has a Log Off tile.
function syncPageActions() {
  const content = document.getElementById('appContent');
  const row = document.getElementById('pageActions');
  if (!content || !row) return;
  const isKid = !!state.currentUser && state.currentProfile === 'child';
  const tile = (icon, title, sub, fn) => `
    <button class="shortcut-tile" onclick="${fn}">
      <span class="tile-icon">${icon}</span>
      <div><div class="tile-title">${title}</div><div class="tile-sub">${sub}</div></div>
    </button>`;
  // Kids always get Back / Home / Up. Everyone else gets Back / Top / Log Off,
  // hidden on the senior Home (which has its own Log Off tile).
  const kidsHome = isKid && !!content.querySelector('.shortcut-grid');
  const kind = isKid ? (kidsHome ? 'kid-home' : 'kid') : 'other';
  if (row.dataset.kind !== kind) {
    row.dataset.kind = kind;
    row.innerHTML = kidsHome
      // On the kids home there is nothing to go back to, so Log Out takes the Back spot.
      ? tile('🚪', 'Log Out', 'See you soon', 'webLogOff()') +
        tile('🏠', 'Home', 'Kids home', 'goHome()') +
        tile('⬆️', 'Up', 'Top of page', "window.scrollTo({ top: 0, behavior: 'smooth' })")
      : isKid
      ? tile('←', 'Back', 'Previous page', 'historyBackOrHome()') +
        tile('🏠', 'Home', 'Kids home', 'goHome()') +
        tile('⬆️', 'Up', 'Top of page', "window.scrollTo({ top: 0, behavior: 'smooth' })")
      : tile('←', 'Back', 'Previous page', 'historyBackOrHome()') +
        tile('⬆️', 'Top', 'Scroll to top', "window.scrollTo({ top: 0, behavior: 'smooth' })") +
        tile('🚪', 'Log Off', 'Switch account', 'webLogOff()');
  }
  row.hidden = !isKid && !!content.querySelector('.shortcut-grid');
}

window.addEventListener('DOMContentLoaded', () => {
  let saved = null;
  try { saved = localStorage.getItem('gc_palette'); } catch (e) {}
  applyPalette(PALETTES.some(p => p.id === saved) ? saved : 'sage');
  const content = document.getElementById('appContent');
  if (content) new MutationObserver(syncPageActions).observe(content, { childList: true });
  syncPageActions();
});

// =====================================================================
// SIMPLE AGE-BASED LOGIN
//   age > 55          -> Senior
//   age < 10          -> Child
//   age 18 to 55      -> Parent / Guardian (safety dashboard, approves friend requests)
//   age 10 to 17      -> not eligible (message shown)
// =====================================================================
function gcEsc(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
function firstName() {
  return (state.currentUser && state.currentUser.name ? state.currentUser.name.trim().split(/\s+/)[0] : '') || 'Friend';
}
function classifyAge(age) {
  if (age > 55) return 'senior';
  if (age < 10) return 'child';
  if (age >= 18) return 'parent';
  return null;
}

function renderLandingView() {
  return `
    <section class="landing">
      <div class="landing-logo" aria-hidden="true">🤝</div>
      <h1 class="landing-title">Generations Connect</h1>
      <p class="landing-sub">Stories, games and friendship between grandparents and grandchildren.</p>
      <button class="btn-primary landing-login" onclick="openLoginForm()">Login</button>
    </section>
  `;
}

function openLoginForm() {
  const container = document.getElementById('appContent');
  if (!container) return;
  container.innerHTML = `
    <section class="landing">
      <form class="card login-card" onsubmit="submitLogin(event)" novalidate>
        <h2 class="card-title">Welcome! Tell us a little about you</h2>
        <label class="login-label" for="loginName">Your name</label>
        <input id="loginName" class="login-input" type="text" autocomplete="given-name" maxlength="40" placeholder="e.g. Meera" required>
        <label class="login-label" for="loginAge">Your age</label>
        <input id="loginAge" class="login-input" type="number" inputmode="numeric" min="1" max="120" placeholder="e.g. 72" required>
        <p id="loginMsg" class="login-msg" role="alert"></p>
        <button type="submit" class="btn-primary">Continue</button>
        <button type="button" class="btn-outline" style="margin-top: 10px;" onclick="renderApp()">← Back</button>
      </form>
    </section>
  `;
  const n = document.getElementById('loginName'); if (n) n.focus();
}

function submitLogin(e) {
  if (e) e.preventDefault();
  const name = (document.getElementById('loginName').value || '').trim();
  const age = parseInt(document.getElementById('loginAge').value, 10);
  const msg = document.getElementById('loginMsg');
  if (!name) { msg.textContent = 'Please type your name.'; return; }
  if (!Number.isFinite(age) || age < 1 || age > 120) { msg.textContent = 'Please enter a real age between 1 and 120.'; return; }

  const role = classifyAge(age);
  if (!role) {
    msg.textContent = 'Generations Connect is for children under 10 and seniors over 55. Please ask a parent or grandparent to log in.';
    return;
  }
  state.currentUser = { name, age, role };
  navHistory.length = 0;
  setProfile(role);
  window.scrollTo({ top: 0 });
  const label = { senior: 'Senior', child: 'Kids', parent: 'Parent' }[role];
  showToast(`Welcome, ${name}! You are in ${label} mode.`);
}

// =====================================================================
// PHOTO STUDIO: take / choose a photo and post it to "Your Gallery"
// =====================================================================
let pendingPhoto = null;

function loadGallery() {
  try { state.gallery = JSON.parse(localStorage.getItem('gc_gallery') || '[]'); } catch (e) { state.gallery = []; }
}
function saveGallery() {
  try { localStorage.setItem('gc_gallery', JSON.stringify(state.gallery)); return true; }
  catch (e) { showToast('Gallery storage is full. Please remove an older photo.'); return false; }
}

// Shrink to max 960px JPEG so a handful of photos fit in browser storage.
function shrinkImage(file, maxSide = 960) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      const scale = Math.min(1, maxSide / Math.max(img.width, img.height));
      const c = document.createElement('canvas');
      c.width = Math.round(img.width * scale);
      c.height = Math.round(img.height * scale);
      c.getContext('2d').drawImage(img, 0, 0, c.width, c.height);
      URL.revokeObjectURL(url);
      resolve(c.toDataURL('image/jpeg', 0.8));
    };
    img.onerror = () => { URL.revokeObjectURL(url); reject(new Error('Could not read that image')); };
    img.src = url;
  });
}

async function handlePhotoPicked(input) {
  const file = input.files && input.files[0];
  input.value = '';
  if (!file) return;
  if (!file.type.startsWith('image/')) { showToast('Please choose a photo file.'); return; }
  try {
    pendingPhoto = await shrinkImage(file);
  } catch (err) { showToast(err.message); return; }
  const box = document.getElementById('photoPreview');
  if (!box) return;
  box.innerHTML = `
    <div class="photo-preview">
      <img src="${pendingPhoto}" alt="Your new photo">
      <input id="photoCaption" class="login-input" type="text" maxlength="80" placeholder="Add a few words about this photo">
      <div style="display: flex; gap: 10px; flex-wrap: wrap;">
        <button class="btn-primary" style="flex: 1; min-width: 160px;" onclick="postPendingPhoto()">📌 Post to Your Gallery</button>
        <button class="btn-outline" style="flex: 1; min-width: 120px;" onclick="cancelPendingPhoto()">Retake</button>
      </div>
    </div>`;
}

function cancelPendingPhoto() {
  pendingPhoto = null;
  const box = document.getElementById('photoPreview');
  if (box) box.innerHTML = '';
}

function postPendingPhoto() {
  if (!pendingPhoto || !state.currentUser) return;
  const captionEl = document.getElementById('photoCaption');
  const caption = captionEl ? captionEl.value.trim() : '';
  state.gallery.unshift({
    id: 'ph' + Date.now(),
    owner: state.currentUser.name,
    dataUrl: pendingPhoto,
    caption,
    date: new Date().toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
  });
  if (!saveGallery()) { state.gallery.shift(); return; }
  pendingPhoto = null;
  showToast('Posted to Your Gallery! 🎉');
  renderSeniorPhoto();
  const g = document.getElementById('yourGallery');
  if (g) g.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function deletePhoto(id) {
  state.gallery = state.gallery.filter(g => g.id !== id);
  saveGallery();
  renderSeniorPhoto();
  showToast('Photo removed.');
}

// =====================================================================
// MAKE A BUDDY: seniors see "Little Hearts", children see "Grandpals"
// Requests need a parent's approval (Parent dashboard) before they become buddies.
// =====================================================================
const BUDDY_DIRECTORY = {
  // shown to a senior (the "Little Hearts")
  child: [
    { id: 'kid_maya', name: 'Maya', blurb: 'Loves painting and animal stories.', interests: ['Painting', 'Animals', 'Songs'] },
    { id: 'kid_arjun', name: 'Arjun', blurb: 'Cricket fan who asks great questions.', interests: ['Cricket', 'Space', 'Riddles'] },
    { id: 'kid_leo', name: 'Leo', blurb: 'Dinosaur expert and young inventor.', interests: ['Dinosaurs', 'Drawing', 'Inventions'] }
  ],
  // shown to a child (the "Grandpals")
  senior: [
    { id: 'sen_arthur', name: 'Arthur', age: 76, blurb: 'Former watchmaker who loves riddles.', interests: ['Antique Clocks', 'Chess', 'Woodworking'] },
    { id: 'sen_meera', name: 'Meera', age: 72, blurb: 'Retired teacher and keen gardener.', interests: ['Gardening', 'Old Songs', 'Storytelling'] },
    { id: 'sen_joseph', name: 'Joseph', age: 68, blurb: 'Tells the best cricket tales.', interests: ['Cricket', 'Carpentry', 'Fishing'] }
  ]
};

function loadFriendRequests() {
  try {
    const saved = JSON.parse(localStorage.getItem('gc_friend_requests') || '[]');
    const have = new Set(state.friendRequests.map(r => r.id));
    saved.forEach(r => { if (!have.has(r.id)) state.friendRequests.push(r); else Object.assign(state.friendRequests.find(x => x.id === r.id), r); });
  } catch (e) {}
}
function saveFriendRequests() {
  try { localStorage.setItem('gc_friend_requests', JSON.stringify(state.friendRequests.filter(r => r.mine))); } catch (e) {}
}

function toggleBuddyList() {
  state.buddyListOpen = !state.buddyListOpen;
  renderMakeBuddy();
}

function renderMakeBuddy() {
  if (typeof recordNav === 'function') recordNav(renderMakeBuddy);
  const container = document.getElementById('appContent');
  const me = state.currentUser;
  if (!container || !me) return;
  const isSenior = me.role === 'senior';
  const buttonLabel = isSenior ? '💗 Little Hearts' : '🧓 Grandpals';
  const pool = isSenior ? BUDDY_DIRECTORY.child : BUDDY_DIRECTORY.senior;
  const mine = state.friendRequests.filter(r => r.mine && r.requester === me.name);
  const asked = new Set(mine.filter(r => r.status !== 'declined').map(r => r.target));

  const statusText = { pending: '⏳ Waiting for a parent to approve', approved: '✅ You are buddies!', declined: 'Not approved this time' };

  container.innerHTML = `
    <div class="card" style="background: var(--primary-light); border-color: var(--primary);">
      <h2 class="card-title">🤝 Make a Buddy</h2>
      <p class="card-subtitle">${isSenior
        ? 'Meet a young friend to share stories, games and paintings with.'
        : 'Meet a grandparent-age friend who loves stories and games.'}</p>
      <button class="btn-primary buddy-main-btn" onclick="toggleBuddyList()" aria-expanded="${state.buddyListOpen}">${buttonLabel}</button>
      <p class="card-subtitle" style="margin-top: 10px;">A parent always approves a new connection first, for everyone's safety.</p>
    </div>

    ${state.buddyListOpen ? `
      <div class="card">
        <h3 class="card-title">${isSenior ? 'Little Hearts who would love a buddy' : 'Grandpals waiting to meet you'}</h3>
        ${pool.map(p => `
          <div class="buddy-card">
            <div class="buddy-avatar" aria-hidden="true">${isSenior ? '🧒' : '👵'}</div>
            <div style="flex: 1; min-width: 180px;">
              <div style="font-weight: 800; font-size: 20px;">${gcEsc(p.name)}${p.age ? ` <span style="font-weight: 600; color: var(--text-muted);">(${p.age})</span>` : ''}</div>
              <div style="color: var(--text-muted); font-size: 16px;">${gcEsc(p.blurb)}</div>
              <div style="margin-top: 4px; font-size: 15px; color: var(--primary); font-weight: 700;">${p.interests.map(gcEsc).join(' • ')}</div>
            </div>
            <button class="btn-primary buddy-send" ${asked.has(p.id) ? 'disabled' : ''} onclick="sendBuddyRequest('${p.id}')">
              ${asked.has(p.id) ? 'Request sent' : 'Send request'}
            </button>
          </div>`).join('')}
      </div>` : ''}

    <div class="card">
      <h3 class="card-title">Your requests</h3>
      ${mine.length === 0 ? '<p class="card-subtitle">No requests yet.</p>' : mine.map(r => `
        <div class="buddy-card">
          <div style="flex: 1;">
            <strong>${gcEsc(r.targetName)}</strong>
            <div style="color: var(--text-muted);">${statusText[r.status] || r.status}</div>
          </div>
        </div>`).join('')}
    </div>
  `;
}

function sendBuddyRequest(targetId) {
  const me = state.currentUser;
  if (!me) return;
  const pool = me.role === 'senior' ? BUDDY_DIRECTORY.child : BUDDY_DIRECTORY.senior;
  const p = pool.find(x => x.id === targetId);
  if (!p) return;
  state.friendRequests.push({
    id: 'fr' + Date.now(),
    name: `${p.name}${p.age ? ` (Age ${p.age})` : ' (Child)'} ⇄ ${me.name}`,
    interests: p.interests,
    bio: `${me.name} (${me.role === 'senior' ? 'senior' : 'child'}) asked to connect with ${p.name}.`,
    status: 'pending',
    mine: true,
    requester: me.name,
    target: p.id,
    targetName: p.name
  });
  saveFriendRequests();
  showToast(me.role === 'senior'
    ? `Request sent to ${p.name}! A parent will approve it first.`
    : `Request sent to ${p.name}! Ask your parent to approve it.`);
  renderMakeBuddy();
}

window.addEventListener('DOMContentLoaded', () => { loadGallery(); loadFriendRequests(); });

// =====================================================================
// CALM BREATHING: ambient nature sounds (synthesised with Web Audio, no audio files)
// Wind, Breeze, Sea, Chirping Birds, Rain, Rustling Leaves - any mix, with volume control.
// =====================================================================
const AMBIENT_SOUNDS = [
  { id: 'wind', icon: '🌬️', label: 'Wind' },
  { id: 'breeze', icon: '🍃', label: 'Breeze' },
  { id: 'sea', icon: '🌊', label: 'Sea' },
  { id: 'birds', icon: '🐦', label: 'Chirping Birds' },
  { id: 'rain', icon: '🌧️', label: 'Rain' },
  { id: 'leaves', icon: '🍂', label: 'Rustling Leaves' }
];

const Ambient = {
  ctx: null, master: null, volume: 0.6, active: {},

  ensure() {
    if (!this.ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return false;
      this.ctx = new AC();
      this.master = this.ctx.createGain();
      this.master.gain.value = this.volume * 0.6;
      this.master.connect(this.ctx.destination);
    }
    if (this.ctx.state === 'suspended') this.ctx.resume();
    return true;
  },

  noise(kind) {
    const c = this.ctx, len = c.sampleRate * 4;
    const buf = c.createBuffer(1, len, c.sampleRate), d = buf.getChannelData(0);
    let last = 0;
    for (let i = 0; i < len; i++) {
      const w = Math.random() * 2 - 1;
      if (kind === 'brown') { last = (last + 0.02 * w) / 1.02; d[i] = last * 3.5; } else d[i] = w;
    }
    const src = c.createBufferSource();
    src.buffer = buf; src.loop = true; src.start();
    return src;
  },

  lfo(freq, depth, param, stops) {
    const o = this.ctx.createOscillator(), g = this.ctx.createGain();
    o.frequency.value = freq; g.gain.value = depth;
    o.connect(g); g.connect(param); o.start();
    stops.push(() => o.stop());
  },

  build(id) {
    const c = this.ctx, stops = [], timers = [];
    const out = c.createGain(); out.gain.value = 0; out.connect(this.master);
    const filt = (type, f, q = 0.7) => { const n = c.createBiquadFilter(); n.type = type; n.frequency.value = f; n.Q.value = q; return n; };
    const src = (kind) => { const s = this.noise(kind); stops.push(() => s.stop()); return s; };
    let level = 1;

    if (id === 'wind') {
      const lp = filt('lowpass', 600); src('brown').connect(lp); lp.connect(out);
      this.lfo(0.08, 300, lp.frequency, stops); this.lfo(0.13, 0.25, out.gain, stops); level = 0.75;
    } else if (id === 'breeze') {
      const bp = filt('bandpass', 900, 0.6); src('white').connect(bp); bp.connect(out);
      this.lfo(0.12, 350, bp.frequency, stops); this.lfo(0.2, 0.1, out.gain, stops); level = 0.3;
    } else if (id === 'sea') {
      const lp = filt('lowpass', 500), waves = c.createGain(); waves.gain.value = 0.5;
      src('brown').connect(lp); lp.connect(waves); waves.connect(out);
      this.lfo(0.1, 0.45, waves.gain, stops);             // slow swell and retreat
      const hp = filt('highpass', 2500), foam = c.createGain(); foam.gain.value = 0.05;
      src('white').connect(hp); hp.connect(foam); foam.connect(out);
      this.lfo(0.1, 0.045, foam.gain, stops); level = 0.9;
    } else if (id === 'rain') {
      const hp = filt('highpass', 900), lp = filt('lowpass', 9000);
      src('white').connect(hp); hp.connect(lp); lp.connect(out); level = 0.3;
    } else if (id === 'leaves') {
      const bp = filt('bandpass', 4500, 1.1), gate = c.createGain(); gate.gain.value = 0.02;
      src('white').connect(bp); bp.connect(gate); gate.connect(out);
      const tick = () => {
        const t = c.currentTime;
        gate.gain.setTargetAtTime(Math.random() * 0.6, t, 0.02);
        gate.gain.setTargetAtTime(0.03, t + 0.08, 0.05);
        timers.push(setTimeout(tick, 120 + Math.random() * 380));
      };
      tick(); level = 0.6;
    } else if (id === 'birds') {
      const chirp = () => {
        const notes = 2 + Math.floor(Math.random() * 3), base = 2200 + Math.random() * 2000;
        for (let n = 0; n < notes; n++) {
          const t = c.currentTime + n * 0.12, o = c.createOscillator(), g = c.createGain();
          o.type = 'sine';
          o.frequency.setValueAtTime(base * (1 + n * 0.05), t);
          o.frequency.exponentialRampToValueAtTime(base * 1.35, t + 0.09);
          g.gain.setValueAtTime(0.0001, t);
          g.gain.exponentialRampToValueAtTime(0.14, t + 0.02);
          g.gain.exponentialRampToValueAtTime(0.0001, t + 0.1);
          o.connect(g); g.connect(out); o.start(t); o.stop(t + 0.12);
        }
        timers.push(setTimeout(chirp, 1200 + Math.random() * 2400));
      };
      chirp(); level = 1;
    }

    out.gain.linearRampToValueAtTime(level, c.currentTime + 1.2); // gentle fade-in
    return {
      stop: () => {
        timers.forEach(clearTimeout);
        out.gain.cancelScheduledValues(c.currentTime);
        out.gain.setTargetAtTime(0, c.currentTime, 0.2);
        setTimeout(() => { stops.forEach(s => { try { s(); } catch (e) {} }); out.disconnect(); }, 900);
      }
    };
  },

  isOn(id) { return !!this.active[id]; },

  toggle(id) {
    if (this.isOn(id)) { this.active[id].stop(); delete this.active[id]; return false; }
    if (!this.ensure()) { showToast('Sound is not supported on this device.'); return false; }
    this.active[id] = this.build(id);
    return true;
  },

  stopAll() { Object.keys(this.active).forEach(id => { this.active[id].stop(); delete this.active[id]; }); },

  setVolume(v) {
    this.volume = Math.min(1, Math.max(0.1, v));
    if (this.master) this.master.gain.value = this.volume * 0.6;
  }
};

function ambientPanelHtml() {
  const anyOn = Object.keys(Ambient.active).length > 0;
  return `
    <div class="card" id="ambientPanel" style="margin-top: 20px;">
      <h3 class="card-title">🎧 Calming Nature Sounds</h3>
      <p class="card-subtitle">Tap one or mix several. Say “play rain” or “stop sounds”.</p>
      <div class="ambient-grid">
        ${AMBIENT_SOUNDS.map(s => `
          <button class="ambient-chip ${Ambient.isOn(s.id) ? 'on' : ''}" aria-pressed="${Ambient.isOn(s.id)}" onclick="toggleAmbient('${s.id}')">
            <span class="ambient-icon">${s.icon}</span>
            <span>${s.label}</span>
          </button>`).join('')}
      </div>
      <div class="ambient-controls">
        <button class="btn-outline" onclick="changeAmbientVolume(-0.15)" aria-label="Quieter">🔉 Quieter</button>
        <span class="ambient-vol" aria-live="polite">Volume ${Math.round(Ambient.volume * 100)}%</span>
        <button class="btn-outline" onclick="changeAmbientVolume(0.15)" aria-label="Louder">🔊 Louder</button>
      </div>
      <button class="btn-outline" style="width: 100%; margin-top: 10px;" ${anyOn ? '' : 'disabled'} onclick="stopAmbient()">⏹ Stop all sounds</button>
    </div>`;
}
function toggleAmbient(id) { Ambient.toggle(id); renderSeniorBreathing(); }
function changeAmbientVolume(delta) { Ambient.setVolume(Ambient.volume + delta); renderSeniorBreathing(); }
function stopAmbient() { Ambient.stopAll(); renderSeniorBreathing(); }

// =====================================================================
// VOICE COMMANDS (ON by default): speak to move around and control the app
// =====================================================================
const VoiceCmd = {
  rec: null, on: true, listening: false, blocked: false, failedStarts: 0,
  get supported() { return !!(window.SpeechRecognition || window.webkitSpeechRecognition); }
};
try { if (localStorage.getItem('gc_voicecmd') === 'off') VoiceCmd.on = false; } catch (e) {}

function renderVoiceCmdBtn() {
  const b = document.getElementById('voiceCmdBtn');
  if (!b) return;
  const live = VoiceCmd.on && VoiceCmd.listening;
  b.classList.toggle('listening', live);
  b.setAttribute('aria-pressed', String(VoiceCmd.on));
  b.querySelector('span').textContent = !VoiceCmd.supported ? 'Mic: n/a' : VoiceCmd.blocked ? 'Mic blocked' : VoiceCmd.on ? (live ? 'Listening…' : 'Voice cmds ON') : 'Voice cmds OFF';
}

function startVoiceCommands() {
  if (!VoiceCmd.on || VoiceCmd.listening || VoiceCmd.blocked) return;
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) { renderVoiceCmdBtn(); return; }
  const rec = new SR();
  rec.lang = 'en-IN';
  rec.continuous = true;
  rec.interimResults = false;
  rec.onstart = () => { VoiceCmd.listening = true; VoiceCmd.failedStarts = 0; renderVoiceCmdBtn(); };
  rec.onresult = (e) => {
    for (let i = e.resultIndex; i < e.results.length; i++) {
      if (!e.results[i].isFinal) continue;
      // Ignore the app's own spoken replies so it never "hears itself"
      if ('speechSynthesis' in window && window.speechSynthesis.speaking) continue;
      handleVoiceCommand(e.results[i][0].transcript);
    }
  };
  rec.onerror = (e) => {
    if (e.error === 'not-allowed' || e.error === 'service-not-allowed') {
      VoiceCmd.blocked = true;
      showToast('Microphone is blocked. Allow it in your browser to use voice commands.');
    }
  };
  rec.onend = () => {
    VoiceCmd.listening = false; renderVoiceCmdBtn();
    if (VoiceCmd.on && !VoiceCmd.blocked && VoiceCmd.failedStarts < 5) {
      VoiceCmd.failedStarts++;
      setTimeout(startVoiceCommands, 500);
    }
  };
  VoiceCmd.rec = rec;
  try { rec.start(); } catch (e) { /* already started */ }
}

function stopVoiceCommands() {
  if (VoiceCmd.rec) { VoiceCmd.rec.onend = null; try { VoiceCmd.rec.stop(); } catch (e) {} }
  VoiceCmd.listening = false; renderVoiceCmdBtn();
}

function toggleVoiceCommands() {
  VoiceCmd.on = !VoiceCmd.on;
  VoiceCmd.blocked = false; VoiceCmd.failedStarts = 0;
  try { localStorage.setItem('gc_voicecmd', VoiceCmd.on ? 'on' : 'off'); } catch (e) {}
  if (VoiceCmd.on) { startVoiceCommands(); showToast('Voice commands ON. Say “help” to hear what you can say.'); }
  else { stopVoiceCommands(); showToast('Voice commands OFF.'); }
  renderVoiceCmdBtn();
}

function pageIs(fn) { return typeof navHistory !== 'undefined' && navHistory[navHistory.length - 1] === fn; }
function onBreathingPage() { return !!document.getElementById('ambientPanel'); }

const SOUND_WORDS = [
  [/\bwind\b/, 'wind'], [/\bbreeze\b/, 'breeze'], [/\b(sea|ocean|waves?)\b/, 'sea'],
  [/\b(birds?|chirping|chirp)\b/, 'birds'], [/\brain\b/, 'rain'], [/\b(leaves|leaf|rustling)\b/, 'leaves']
];

function speakReply(text) { if (state.voiceModeEnabled) speakText(text); }

function voiceHelpText(role) {
  if (role === 'senior') return 'You can say: home, back, medicines, I took my medicine, diary, sleep, stories, games, photo studio, music, calm breathing, play rain, stop sounds, make a buddy, read this page, scroll down, change colour to sage, or log off.';
  if (role === 'child') return 'You can say: home, back, math, kumon, photo studio, make a buddy, music, read this page, scroll down, change colour to salmon, or log off.';
  if (role === 'parent') return 'You can say: home, read this page, scroll down, or log off.';
  return 'Say login to begin.';
}

function handleVoiceCommand(raw) {
  const text = String(raw || '').toLowerCase().replace(/[^a-z0-9' ]+/g, ' ').replace(/\s+/g, ' ').trim();
  if (!text) return;
  const role = state.currentUser ? state.currentProfile : null;
  showToast(`🎤 “${text}”`);

  // ----- Login form: dictate name and age -----
  if (document.getElementById('loginName')) {
    const nameEl = document.getElementById('loginName'), ageEl = document.getElementById('loginAge');
    const nm = text.match(/(?:my name is|i am called|name is|i am|i'm)\s+([a-z ]+?)(?:\s+and\b|\s+\d|$)/);
    const ag = text.match(/\b(\d{1,3})\b/);
    let did = false;
    if (nm && !/^\d/.test(nm[1])) { nameEl.value = nm[1].replace(/\b\w/g, c => c.toUpperCase()); did = true; }
    if (ag) { ageEl.value = ag[1]; did = true; }
    if (/\b(continue|submit|go ahead|done|login|log in|next)\b/.test(text)) { submitLogin(); return; }
    if (/\b(back|cancel)\b/.test(text)) { renderApp(); return; }
    if (did) { speakReply(nameEl.value && ageEl.value ? 'Got it. Say continue.' : 'Got it.'); return; }
  }

  // ----- Mental Math: answer out loud -----
  if (mentalAwaitingAnswer()) {
    const num = text.match(/-?\d+/);
    if (num) { submitMentalAnswer(Number(num[0])); return; }
  } else if (mentalSession && mentalSession.answered && /\b(next|continue)\b/.test(text)) { nextMental(); return; }

  // ----- Works everywhere -----
  if (/\b(help|what can i say|commands)\b/.test(text)) { const h = voiceHelpText(role); showToast(h); speakText(h); return; }
  if (/\b(stop|silence|quiet|be quiet)\b/.test(text) && !/\b(sound|sounds|music|nature)\b/.test(text)) { stopSpeaking(); return; }
  if (/\b(dark mode|night mode)\b/.test(text)) { if (state.theme !== 'dark') toggleTheme(); return; }
  if (/\b(light mode|day mode)\b/.test(text)) { if (state.theme !== 'light') toggleTheme(); return; }
  const pal = [[/\bmustard|yellow\b/, 'mustard'], [/\bsalmon|pink\b/, 'salmon'], [/\b(grey|gray|blue|slate)\b/, 'slate'], [/\bpearl|white\b/, 'pearl'], [/\bsage|green\b/, 'sage'], [/\boriginal\b/, 'original']]
    .find(([re]) => re.test(text));
  if (pal && /\b(colou?r|theme|change|use|make it|switch)\b/.test(text)) { applyPalette(pal[1]); speakReply('Colour changed.'); return; }

  if (!state.currentUser) {
    if (/\b(login|log in|start|begin|sign in)\b/.test(text)) { openLoginForm(); speakReply('Please tell me your name and age.'); }
    else speakReply('Say login to begin.');
    return;
  }

  const allow = (...roles) => { if (roles.includes(role)) return true; speakReply('That is not available here.'); return false; };

  if (/\b(log off|log out|logout|sign out|goodbye)\b/.test(text)) { speakReply('Logging off. Goodbye!'); webLogOff(); return; }
  if (/\b(read|read aloud|read this|read the page)\b/.test(text)) {
    const body = (document.getElementById('appContent') || {}).innerText || '';
    speakText(body.replace(/\s+/g, ' ').slice(0, 900)); return;
  }
  if (/\bscroll down|page down\b/.test(text)) { window.scrollBy({ top: window.innerHeight * 0.7, behavior: 'smooth' }); return; }
  if (/\bscroll up|page up\b/.test(text)) { window.scrollBy({ top: -window.innerHeight * 0.7, behavior: 'smooth' }); return; }
  if (/\b(top of (the )?page|scroll to top)\b/.test(text)) { window.scrollTo({ top: 0, behavior: 'smooth' }); return; }
  if (/\b(go back|back|previous)\b/.test(text)) { historyBackOrHome(); return; }
  if (/\b(home|main menu|start page)\b/.test(text)) { goHome(); speakReply('Home.'); return; }

  // ----- Ambient sounds & breathing (seniors) -----
  if (/\b(stop|turn off|silence)\b.*\b(sound|sounds|music|nature|everything)\b/.test(text) || /\bstop all\b/.test(text)) { Ambient.stopAll(); if (onBreathingPage()) renderSeniorBreathing(); return; }
  if (/\b(louder|volume up|turn it up|increase volume)\b/.test(text)) { Ambient.setVolume(Ambient.volume + 0.15); if (onBreathingPage()) renderSeniorBreathing(); return; }
  if (/\b(quieter|softer|volume down|turn it down|lower volume)\b/.test(text)) { Ambient.setVolume(Ambient.volume - 0.15); if (onBreathingPage()) renderSeniorBreathing(); return; }
  const snd = SOUND_WORDS.find(([re]) => re.test(text));
  if (snd && (onBreathingPage() || /\b(play|start|turn on|add|sound|sounds)\b/.test(text))) {
    if (!allow('senior')) return;
    if (!onBreathingPage()) renderSeniorBreathing();
    if (!Ambient.isOn(snd[1])) Ambient.toggle(snd[1]);
    renderSeniorBreathing(); return;
  }
  if (/\b(start|begin)\b.*\b(breathing|exercise)\b/.test(text)) { if (!allow('senior')) return; renderSeniorBreathing(); startBreathing(); return; }
  if (onBreathingPage()) {
    if (/\bpause\b/.test(text)) { pauseBreathing(); return; }
    if (/\b(resume|continue)\b/.test(text)) { resumeBreathing(); return; }
    if (/\breset\b/.test(text)) { resetBreathing(); return; }
  }

  // ----- Navigation -----
  const nav = [
    [/\b(took|taken|take)\b.*\b(medicine|medicines|medication|pill|pills|tablet)\b|\b(mark)\b.*\btaken\b|\bi took (it|them)\b/, 'senior', () => {
      const m = state.medications.find(x => x.status === 'overdue') || state.medications.find(x => x.status === 'pending');
      if (m) { takeMed(m.id); speakReply(`Marked ${m.name} as taken.`); } else speakReply('All of your medicines are already taken.');
    }],
    [/\b(medicine|medicines|medication|medications|pills|tablets)\b/, 'senior', renderSeniorMedicines],
    [/\b(diary|journal)\b/, 'senior', renderSeniorDiary],
    [/\bsleep\b/, 'senior', renderSeniorSleep],
    [/\b(story|stories)\b/, 'senior', renderSeniorStories],
    [/\b(game|games)\b/, 'senior,child', renderSeniorGames],
    [/\b(milestone|milestones|badges)\b/, 'senior', renderSeniorMilestones],
    [/\b(breathing|breathe|calm)\b/, 'senior', renderSeniorBreathing],
    [/\bkumon\b/, 'child', () => startKumon()],
    [/\bmental\b/, 'child', () => renderMath()],
    [/\b(math|maths|mathematics|sums)\b/, 'child', renderMath],
    [/\b(photo|photos|picture|pictures|camera|gallery)\b/, 'senior,child', renderSeniorPhoto],
    [/\b(music|piano|sitar|tabla)\b/, 'senior,child', () => renderMusicStudio()],
    [/\b(buddy|buddies|little hearts|grandpals|friend|friends)\b/, 'senior,child', renderMakeBuddy]
  ];
  for (const [re, roles, fn] of nav) {
    if (re.test(text)) { if (!allow(...roles.split(','))) return; fn(); return; }
  }

  speakReply('Sorry, I did not catch that. Say help to hear what you can say.');
}

window.addEventListener('DOMContentLoaded', () => {
  renderVoiceCmdBtn();
  // Ambient sounds stop as soon as the Calm Breathing page is left
  const content = document.getElementById('appContent');
  if (content) new MutationObserver(() => { if (!document.getElementById('ambientPanel')) Ambient.stopAll(); }).observe(content, { childList: true });
  // Voice commands are ON by default. Browsers ask for the microphone the first time.
  startVoiceCommands();
  // Some browsers only allow the mic after a tap, so retry on the first interaction
  document.addEventListener('pointerdown', () => startVoiceCommands(), { once: true });
});

// =====================================================================
// KIDS MATH: two sections - Mental Math (quick questions) and Kumon Math (level worksheets)
// =====================================================================
function rnd(a, b) { return a + Math.floor(Math.random() * (b - a + 1)); }
function awardStars(n) { state.childPoints += n; }

function renderMath() {
  if (typeof recordNav === 'function') recordNav(renderMath);
  const c = document.getElementById('appContent');
  if (!c) return;
  const lvl = getKumonLevel();
  c.innerHTML = `
    <div class="card" style="background: #F3E8FF; border: 2.5px solid #C084FC;">
      <h2 class="card-title" style="color: #581c87;">🔢 Math</h2>
      <p class="card-subtitle" style="color: #6b21a8;">Pick a section. Every right answer earns star points! ⭐ ${state.childPoints}</p>
    </div>

    <div class="card">
      <h3 class="card-title">🧠 Mental Math</h3>
      <p class="card-subtitle">Quick questions, one at a time. Do them in your head and type (or say!) the answer.</p>
      <div class="math-levels">
        <button class="btn-primary" onclick="startMental('easy')">⭐ Easy</button>
        <button class="btn-primary" onclick="startMental('medium')">⭐⭐ Medium</button>
        <button class="btn-primary" onclick="startMental('hard')">⭐⭐⭐ Hard</button>
      </div>
    </div>

    <div class="card">
      <h3 class="card-title">📝 Kumon Math</h3>
      <p class="card-subtitle">Worksheet practice, one level at a time. Score 9 out of 10 or more to move up!</p>
      <p style="font-weight: 800; font-size: 20px; margin: 10px 0;">You are on Level ${lvl}: ${KUMON_LEVELS[lvl - 1].name}</p>
      <button class="btn-primary" style="width: 100%; min-height: 60px; font-size: 20px;" onclick="startKumon()">▶ Start my worksheet</button>
      <label for="kumonPick" style="display: block; font-weight: 700; margin: 14px 0 6px;">Practise an earlier level</label>
      <select id="kumonPick" class="login-input" onchange="startKumon(parseInt(this.value, 10))">
        <option value="">Choose a level…</option>
        ${KUMON_LEVELS.map((l, i) => i + 1 <= lvl ? `<option value="${i + 1}">Level ${i + 1}: ${l.name}</option>` : `<option disabled>🔒 Level ${i + 1}: ${l.name}</option>`).join('')}
      </select>
    </div>
  `;
}

// ---------- Mental Math ----------
const MENTAL_LEVELS = {
  easy: { label: 'Easy', make() {
    if (Math.random() < 0.5) { const a = rnd(1, 10), b = rnd(1, 10); return { q: `${a} + ${b}`, a: a + b }; }
    const a = rnd(5, 20), b = rnd(1, a); return { q: `${a} − ${b}`, a: a - b };
  } },
  medium: { label: 'Medium', make() {
    const t = rnd(0, 2);
    if (t === 0) { const a = rnd(10, 60), b = rnd(5, 39); return { q: `${a} + ${b}`, a: a + b }; }
    if (t === 1) { const a = rnd(30, 99), b = rnd(5, 29); return { q: `${a} − ${b}`, a: a - b }; }
    const a = rnd(2, 6), b = rnd(2, 10); return { q: `${a} × ${b}`, a: a * b };
  } },
  hard: { label: 'Hard', make() {
    const t = rnd(0, 3);
    if (t === 0) { const a = rnd(3, 12), b = rnd(3, 12); return { q: `${a} × ${b}`, a: a * b }; }
    if (t === 1) { const b = rnd(2, 12), r = rnd(2, 12); return { q: `${b * r} ÷ ${b}`, a: r }; }
    if (t === 2) { const a = rnd(100, 499), b = rnd(50, 300); return { q: `${a} + ${b}`, a: a + b }; }
    const a = rnd(200, 900), b = rnd(50, 199); return { q: `${a} − ${b}`, a: a - b };
  } }
};
let mentalSession = null;
const MENTAL_TOTAL = 10;

function mentalAwaitingAnswer() {
  return !!(mentalSession && !mentalSession.answered && document.getElementById('mentalAnswer'));
}

function startMental(level) {
  mentalSession = { level, n: 0, correct: 0, streak: 0, best: 0, cur: null, answered: false, start: Date.now() };
  nextMental();
}

function nextMental() {
  const s = mentalSession;
  if (!s) return renderMath();
  if (s.n >= MENTAL_TOTAL) return finishMental();
  s.n++; s.answered = false; s.feedback = null;
  s.cur = MENTAL_LEVELS[s.level].make();
  drawMental();
}

function drawMental() {
  const s = mentalSession, c = document.getElementById('appContent');
  if (!s || !c) return;
  c.innerHTML = `
    <div class="card math-stage">
      <div class="math-meta">
        <span>${MENTAL_LEVELS[s.level].label} • Question ${s.n} of ${MENTAL_TOTAL}</span>
        <span>🔥 Streak ${s.streak}</span>
      </div>
      <div class="progress-track"><div class="progress-fill" style="width: ${(s.n - (s.answered ? 0 : 1)) / MENTAL_TOTAL * 100}%"></div></div>
      <div class="math-question" aria-live="polite">${s.cur.q} = ?</div>
      ${s.answered ? `
        <div class="math-feedback ${s.feedback.ok ? 'ok' : 'bad'}">${s.feedback.ok ? '🎉 Correct! Great thinking!' : `Not quite. The answer is ${s.cur.a}.`}</div>
        <button class="btn-primary" style="width: 100%; min-height: 60px; font-size: 22px;" onclick="nextMental()">${s.n >= MENTAL_TOTAL ? 'See my score 🏆' : 'Next →'}</button>
      ` : `
        <form onsubmit="event.preventDefault(); submitMentalAnswer(parseInt(document.getElementById('mentalAnswer').value, 10));">
          <input id="mentalAnswer" class="login-input math-input" type="number" inputmode="numeric" autocomplete="off" placeholder="Your answer" autofocus>
          <button type="submit" class="btn-primary" style="width: 100%; min-height: 60px; font-size: 22px; margin-top: 10px;">Check ✓</button>
        </form>
        <p class="card-subtitle" style="text-align: center; margin-top: 10px;">You can also say the answer out loud 🎤</p>
      `}
      <button class="btn-outline" style="margin-top: 12px;" onclick="mentalSession = null; renderMath();">Stop & go back</button>
    </div>`;
  const inp = document.getElementById('mentalAnswer'); if (inp) inp.focus();
}

function submitMentalAnswer(value) {
  const s = mentalSession;
  if (!s || s.answered) return;
  if (!Number.isFinite(value)) { showToast('Type a number first.'); return; }
  const ok = value === s.cur.a;
  s.answered = true; s.feedback = { ok };
  if (ok) { s.correct++; s.streak++; s.best = Math.max(s.best, s.streak); awardStars(5); } else s.streak = 0;
  drawMental();
  speakReply(ok ? 'Correct!' : `The answer is ${s.cur.a}.`);
}

function finishMental() {
  const s = mentalSession, c = document.getElementById('appContent');
  if (!s || !c) return;
  const secs = Math.round((Date.now() - s.start) / 1000);
  const bonus = s.correct === MENTAL_TOTAL ? 10 : 0;
  if (bonus) awardStars(bonus);
  c.innerHTML = `
    <div class="card math-stage" style="text-align: center;">
      <h2 class="card-title">${s.correct >= 8 ? '🏆 Superstar!' : s.correct >= 5 ? '👏 Well done!' : '💪 Keep practising!'}</h2>
      <div class="math-question">${s.correct} / ${MENTAL_TOTAL}</div>
      <p class="card-subtitle">Time: ${Math.floor(secs / 60)}m ${secs % 60}s • Best streak: ${s.best}</p>
      <p style="font-weight: 800; font-size: 20px;">⭐ +${s.correct * 5 + bonus} star points (total ${state.childPoints})</p>
      <div class="math-levels" style="margin-top: 14px;">
        <button class="btn-primary" onclick="startMental('${s.level}')">🔁 Play again</button>
        <button class="btn-outline" onclick="renderMath()">Math menu</button>
      </div>
    </div>`;
  speakReply(`You got ${s.correct} out of ${MENTAL_TOTAL}.`);
  mentalSession = null;
}

// ---------- Kumon Math: level-by-level worksheets ----------
const KUMON_LEVELS = [
  { name: 'Counting on (+1, +2, +3)', make() { const a = rnd(1, 9), b = rnd(1, 3); return { q: `${a} + ${b}`, a: a + b }; } },
  { name: 'Adding within 10', make() { const a = rnd(1, 9), b = rnd(1, 10 - a); return { q: `${a} + ${b}`, a: a + b }; } },
  { name: 'Subtracting within 10', make() { const a = rnd(2, 10), b = rnd(1, a - 1); return { q: `${a} − ${b}`, a: a - b }; } },
  { name: 'Adding within 20', make() { const a = rnd(2, 12), b = rnd(2, 20 - a); return { q: `${a} + ${b}`, a: a + b }; } },
  { name: 'Subtracting within 20', make() { const a = rnd(10, 20), b = rnd(2, a - 1); return { q: `${a} − ${b}`, a: a - b }; } },
  { name: 'Mixed + and − within 20', make() { return Math.random() < 0.5 ? KUMON_LEVELS[3].make() : KUMON_LEVELS[4].make(); } },
  { name: 'Times tables: 2, 5 and 10', make() { const a = [2, 5, 10][rnd(0, 2)], b = rnd(1, 10); return { q: `${a} × ${b}`, a: a * b }; } },
  { name: 'Times tables up to 10', make() { const a = rnd(2, 10), b = rnd(2, 10); return { q: `${a} × ${b}`, a: a * b }; } },
  { name: 'Division facts', make() { const b = rnd(2, 10), r = rnd(1, 10); return { q: `${b * r} ÷ ${b}`, a: r }; } }
];
let kumonSheet = null, kumonTimer = null;

function kumonKey() { return 'gc_kumon_' + (state.currentUser ? state.currentUser.name : 'guest'); }
function getKumonLevel() {
  try { const v = parseInt(localStorage.getItem(kumonKey()), 10); if (v >= 1 && v <= KUMON_LEVELS.length) return v; } catch (e) {}
  return 1;
}
function setKumonLevel(v) { try { localStorage.setItem(kumonKey(), String(v)); } catch (e) {} }

function startKumon(level) {
  const lvl = Number.isFinite(level) && level >= 1 && level <= getKumonLevel() ? level : getKumonLevel();
  const seen = new Set(), items = [];
  let guard = 0;
  while (items.length < 10 && guard++ < 400) {
    const p = KUMON_LEVELS[lvl - 1].make();
    if (!seen.has(p.q)) { seen.add(p.q); items.push(p); }
  }
  while (items.length < 10) items.push(KUMON_LEVELS[lvl - 1].make());
  kumonSheet = { level: lvl, items, start: Date.now(), checked: false };
  drawKumon();
  clearInterval(kumonTimer);
  kumonTimer = setInterval(() => {
    const el = document.getElementById('kumonClock');
    if (!el || !kumonSheet || kumonSheet.checked) { clearInterval(kumonTimer); return; }
    const s = Math.floor((Date.now() - kumonSheet.start) / 1000);
    el.textContent = `⏱ ${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
  }, 1000);
}

function drawKumon(result) {
  const k = kumonSheet, c = document.getElementById('appContent');
  if (!k || !c) return;
  c.innerHTML = `
    <div class="card" id="kumonSheet">
      <div class="math-meta">
        <span><strong>Level ${k.level}</strong>: ${KUMON_LEVELS[k.level - 1].name}</span>
        <span id="kumonClock" class="chip-time">⏱ 0:00</span>
      </div>
      <p class="card-subtitle">Fill in every answer, then press “Check my sheet”. Goal: 9 out of 10 or better.</p>
      <div class="kumon-grid">
        ${k.items.map((p, i) => `
          <label class="kumon-row ${result ? (result.marks[i] ? 'ok' : 'bad') : ''}">
            <span class="kumon-q">${i + 1}. ${p.q} =</span>
            <input class="kumon-input" data-i="${i}" type="number" inputmode="numeric" autocomplete="off" ${result ? 'disabled' : ''} value="${result ? gcEsc(result.values[i]) : ''}" aria-label="Answer to ${p.q}">
            ${result && !result.marks[i] ? `<span class="kumon-fix">✔ ${p.a}</span>` : ''}
          </label>`).join('')}
      </div>
      ${result ? `
        <div class="math-feedback ${result.pass ? 'ok' : 'bad'}">
          ${result.score} / 10 • ${Math.floor(result.secs / 60)}m ${result.secs % 60}s<br>
          ${result.pass ? (result.levelUp ? `🎉 Level up! Level ${result.newLevel} is unlocked.` : '🎉 Sheet passed! Great work!') : 'Almost there! Let’s try a fresh sheet of this level.'}
          <br><strong>⭐ +${result.stars} star points</strong>
        </div>
        <div class="math-levels">
          <button class="btn-primary" onclick="startKumon(${result.levelUp ? result.newLevel : k.level})">${result.levelUp ? `Start Level ${result.newLevel} ▶` : 'Next sheet ▶'}</button>
          <button class="btn-outline" onclick="renderMath()">Math menu</button>
        </div>
      ` : `
        <button class="btn-primary" style="width: 100%; min-height: 60px; font-size: 22px; margin-top: 14px;" onclick="checkKumon()">✓ Check my sheet</button>
        <button class="btn-outline" style="margin-top: 10px;" onclick="clearInterval(kumonTimer); kumonSheet = null; renderMath();">Stop & go back</button>
      `}
    </div>`;
  if (!result) { const first = c.querySelector('.kumon-input'); if (first) first.focus(); }
}

function checkKumon() {
  const k = kumonSheet;
  if (!k || k.checked) return;
  const inputs = [...document.querySelectorAll('.kumon-input')];
  const values = inputs.map(i => i.value.trim());
  const marks = k.items.map((p, i) => values[i] !== '' && parseInt(values[i], 10) === p.a);
  const score = marks.filter(Boolean).length;
  const pass = score >= 9;
  const secs = Math.round((Date.now() - k.start) / 1000);
  const highest = getKumonLevel();
  const levelUp = pass && k.level === highest && highest < KUMON_LEVELS.length;
  if (levelUp) setKumonLevel(highest + 1);
  const stars = score * 2 + (pass ? 20 : 0);
  awardStars(stars);
  k.checked = true;
  clearInterval(kumonTimer);
  drawKumon({ marks, values, score, pass, secs, levelUp, newLevel: highest + 1, stars });
  speakReply(pass ? 'Wonderful! You passed this sheet.' : `You got ${score} out of 10. Let's try again.`);
}

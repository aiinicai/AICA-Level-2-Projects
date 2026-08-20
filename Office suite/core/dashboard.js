document.addEventListener('DOMContentLoaded', () => {
  const sidebar = document.getElementById('sidebar');
  const btnToggleSidebar = document.getElementById('btn-toggle-sidebar');
  const modulesList = document.getElementById('modules-list');
  const toolFrame = document.getElementById('tool-frame');
  const welcomeView = document.getElementById('welcome-view');
  const activeToolTitle = document.getElementById('active-tool-title');
  const activeToolBadge = document.getElementById('active-tool-badge');
  const btnRefresh = document.getElementById('btn-refresh');
  const btnOpenTab = document.getElementById('btn-open-tab');

  // Theme Toggle Elements
  const btnThemeToggle = document.getElementById('btn-theme-toggle');
  const themeIconSun = document.getElementById('theme-icon-sun');
  const themeIconMoon = document.getElementById('theme-icon-moon');

  let currentActiveModule = null;
  let currentTheme = 'dark';

  // --- Theme Management ---
  function initTheme() {
    const savedTheme = localStorage.getItem('office_suite_theme');
    if (savedTheme === 'light' || savedTheme === 'dark') {
      currentTheme = savedTheme;
    } else {
      currentTheme = window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
    }
    applyTheme(currentTheme);
  }

  function applyTheme(theme) {
    currentTheme = theme;
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('office_suite_theme', theme);

    if (theme === 'light') {
      if (themeIconSun) themeIconSun.style.display = 'none';
      if (themeIconMoon) themeIconMoon.style.display = 'block';
    } else {
      if (themeIconSun) themeIconSun.style.display = 'block';
      if (themeIconMoon) themeIconMoon.style.display = 'none';
    }

    notifyIframeTheme(theme);
  }

  function notifyIframeTheme(theme) {
    if (toolFrame && toolFrame.contentWindow) {
      try {
        toolFrame.contentWindow.postMessage({ type: 'THEME_CHANGE', theme: theme }, '*');
      } catch (err) {
        console.warn('Could not postMessage theme to iframe:', err);
      }
    }
  }

  if (btnThemeToggle) {
    btnThemeToggle.addEventListener('click', () => {
      const nextTheme = currentTheme === 'dark' ? 'light' : 'dark';
      applyTheme(nextTheme);
    });
  }

  // Re-send theme to iframe when loaded
  if (toolFrame) {
    toolFrame.addEventListener('load', () => {
      notifyIframeTheme(currentTheme);
    });
  }

  // --- Sidebar & Layout Actions ---
  if (btnToggleSidebar && sidebar) {
    btnToggleSidebar.addEventListener('click', () => {
      sidebar.classList.toggle('collapsed');
    });
  }

  if (btnRefresh && toolFrame) {
    btnRefresh.addEventListener('click', () => {
      if (toolFrame.src && toolFrame.src !== 'about:blank') {
        toolFrame.src = toolFrame.src;
      }
    });
  }

  if (btnOpenTab) {
    btnOpenTab.addEventListener('click', () => {
      if (currentActiveModule && currentActiveModule.entry_ui) {
        window.open(currentActiveModule.entry_ui, '_blank');
      }
    });
  }

  // SVG Icon Map Helper
  function getIconSVG(iconName) {
    const icons = {
      sparkles: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"></path></svg>`,
      grid: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>`,
      fileText: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line></svg>`,
      table: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 3H5a2 2 0 0 0-2 2v4m6-6h10a2 2 0 0 1 2 2v4M9 3v18m0 0h10a2 2 0 0 0 2-2V9M9 21H5a2 2 0 0 1-2-2V9m0 0h18"></path></svg>`
    };

    return icons[iconName] || icons.sparkles;
  }

  // Fetch registered modules from dynamic backend
  async function loadModules() {
    try {
      const response = await fetch('/api/modules');
      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}`);
      }

      const data = await response.json();
      renderModuleList(data.modules || []);
    } catch (err) {
      console.error('Failed to fetch modules:', err);
      if (modulesList) {
        modulesList.innerHTML = `
          <li style="padding: 12px; color: #ef4444; font-size: 0.85rem; text-align: center;">
            Failed to load modules from server.
          </li>
        `;
      }
    }
  }

  // Render modules into sidebar
  function renderModuleList(modules) {
    if (!modulesList) return;
    modulesList.innerHTML = '';

    if (modules.length === 0) {
      modulesList.innerHTML = `
        <li style="padding: 12px; color: var(--text-muted); font-size: 0.85rem; text-align: center;">
          No active modules detected in /modules.
        </li>
      `;
      return;
    }

    modules.forEach((mod) => {
      const li = document.createElement('li');
      li.className = 'module-item';
      li.setAttribute('data-module-id', mod.id);

      li.innerHTML = `
        <div class="module-icon">
          ${getIconSVG(mod.icon)}
        </div>
        <div class="module-details">
          <span class="module-name">${mod.name}</span>
          <span class="module-desc">${mod.description}</span>
        </div>
      `;

      li.addEventListener('click', () => selectModule(mod, li));
      modulesList.appendChild(li);
    });
  }

  // Select module and render inside iframe
  function selectModule(mod, element) {
    currentActiveModule = mod;

    // Update active highlight in sidebar
    document.querySelectorAll('.module-item').forEach((item) => {
      item.classList.remove('active');
    });
    element.classList.add('active');

    // Update top header bar
    if (activeToolTitle) activeToolTitle.textContent = mod.name;
    if (activeToolBadge) activeToolBadge.textContent = mod.api_base;

    // Toggle viewport visibility
    if (mod.entry_ui && toolFrame && welcomeView) {
      toolFrame.src = mod.entry_ui;
      toolFrame.classList.add('active');
      welcomeView.classList.add('hidden');
    } else if (toolFrame && welcomeView) {
      toolFrame.classList.remove('active');
      welcomeView.classList.remove('hidden');
    }
  }

  // Initialize
  initTheme();
  loadModules();
});

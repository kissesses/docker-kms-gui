const PyKmsApp = (function() {
  let refreshTimer = null;

  function formatUptime(seconds) {
    const d = Math.floor(seconds / 86400);
    const h = Math.floor((seconds % 86400) / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    const parts = [];
    if (d) parts.push(d + 'd');
    if (h) parts.push(h + 'h');
    if (m) parts.push(m + 'm');
    parts.push(s + 's');
    return parts.join(' ');
  }

  function showToast(message, type) {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = 'toast' + (type ? ' ' + type : '');
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(function() {
      toast.style.opacity = '0';
      toast.style.transition = 'opacity 0.2s';
      setTimeout(function() { toast.remove(); }, 200);
    }, 2500);
  }

  function convertTimestamps() {
    document.querySelectorAll('.convert_timestamp').forEach(function(el) {
      const raw = el.textContent.trim();
      if (!raw) return;
      const unix = parseInt(raw, 10);
      const date = !isNaN(unix) && String(unix) === raw
        ? new Date(unix * 1000)
        : new Date(raw);
      if (!isNaN(date.getTime())) {
        el.textContent = date.toLocaleString();
      }
    });
  }

  function updateThemeIcons(isLight) {
    const darkIcon = document.getElementById('theme-icon-dark');
    const lightIcon = document.getElementById('theme-icon-light');
    if (darkIcon) darkIcon.style.display = isLight ? 'none' : 'block';
    if (lightIcon) lightIcon.style.display = isLight ? 'block' : 'none';
    document.querySelector('meta[name="theme-color"]')?.setAttribute(
      'content', isLight ? '#f1f5f9' : '#070b14'
    );
  }

  function initTheme() {
    const toggle = document.getElementById('theme-toggle');
    const saved = localStorage.getItem('pykms-theme') || 'dark';
    const isLight = saved === 'light';
    document.documentElement.classList.toggle('light', isLight);
    updateThemeIcons(isLight);

    if (toggle) {
      toggle.addEventListener('click', function() {
        const nowLight = document.documentElement.classList.toggle('light');
        localStorage.setItem('pykms-theme', nowLight ? 'light' : 'dark');
        updateThemeIcons(nowLight);
      });
    }
  }

  function initMobileNav() {
    const btn = document.getElementById('mobile-menu-toggle');
    const nav = document.getElementById('mobile-nav');
    if (btn && nav) {
      btn.addEventListener('click', function() {
        const isOpen = nav.classList.toggle('open');
        btn.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
      });
    }
  }

  function setServerStatus(online, label) {
    ['status-dot', 'status-dot-mobile'].forEach(function(id) {
      const dot = document.getElementById(id);
      if (dot) dot.classList.toggle('live', online);
    });
    ['status-text', 'status-text-mobile'].forEach(function(id) {
      const el = document.getElementById(id);
      if (el) el.textContent = label;
    });
  }

  function updateDistBar(data) {
    const total = data.count_clients || 0;
    if (total <= 0) return;
    const winPct = Math.round((data.count_clients_windows / total) * 1000) / 10;
    const officePct = Math.round((data.count_clients_office / total) * 1000) / 10;
    const winEl = document.getElementById('dist-win');
    const officeEl = document.getElementById('dist-office');
    if (winEl) winEl.style.width = winPct + '%';
    if (officeEl) officeEl.style.width = officePct + '%';
  }

  function refreshStats() {
    return fetch('/api/v1/stats')
      .then(function(r) { return r.json(); })
      .then(function(data) {
        if (data.error) {
          setServerStatus(false, 'Offline');
          return;
        }
        setServerStatus(true, 'Online · ' + (data.count_clients || 0) + ' clients');
        document.querySelectorAll('[data-stat]').forEach(function(el) {
          const key = el.getAttribute('data-stat');
          if (data[key] !== undefined) el.textContent = data[key];
        });
        const uptimeEl = document.getElementById('stat-uptime');
        if (uptimeEl && data.uptime_seconds !== undefined) {
          uptimeEl.textContent = formatUptime(data.uptime_seconds);
        }
        updateDistBar(data);
        drawClientChart(data.chart_windows || 0, data.chart_office || 0);
      })
      .catch(function() { setServerStatus(false, 'Unreachable'); });
  }

  function initCommon() {
    convertTimestamps();
    initTheme();
    initMobileNav();
    refreshStats();
  }

  function drawClientChart(windows, office) {
    const canvas = document.getElementById('client-chart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const total = windows + office;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (total <= 0) return;
    const cx = canvas.width / 2;
    const cy = canvas.height / 2;
    const r = Math.min(cx, cy) - 8;
    let start = -Math.PI / 2;
    const slices = [
      { v: windows, c: '#38bdf8' },
      { v: office, c: '#6366f1' }
    ];
    slices.forEach(function(s) {
      if (s.v <= 0) return;
      const angle = (s.v / total) * Math.PI * 2;
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.arc(cx, cy, r, start, start + angle);
      ctx.closePath();
      ctx.fillStyle = s.c;
      ctx.fill();
      start += angle;
    });
    ctx.beginPath();
    ctx.arc(cx, cy, r * 0.55, 0, Math.PI * 2);
    ctx.fillStyle = getComputedStyle(document.body).getPropertyValue('--bg-surface') || '#121a2b';
    ctx.fill();
  }

  function initClientsLive() {
    initClientsTable();
    setInterval(refreshStats, 30000);
  }

  function initActivationsLive() {
    initCommon();
    function refreshActivations() {
      fetch('/api/v1/activations')
        .then(function(r) { return r.json(); })
        .then(function(data) {
          if (!data.summary) return;
          document.querySelectorAll('[data-act-stat]').forEach(function(el) {
            const key = el.getAttribute('data-act-stat');
            if (data.summary[key] !== undefined) el.textContent = data.summary[key];
          });
        })
        .catch(function() {});
    }
    refreshActivations();
    setInterval(refreshActivations, 30000);
  }

  function initDashboard() {
    initCommon();
    refreshStats();
    setInterval(refreshStats, 30000);
  }

  function filterClients() {
    const query = (document.getElementById('client-search')?.value || '').toLowerCase();
    const appFilter = (document.getElementById('client-filter-app')?.value || '').toLowerCase();
    let visible = 0;
    document.querySelectorAll('.client-row').forEach(function(row) {
      const text = [
        row.dataset.name, row.dataset.ip, row.dataset.app,
        row.dataset.status, row.textContent.toLowerCase()
      ].join(' ');
      const matches = (!query || text.includes(query)) &&
                      (!appFilter || row.dataset.app === appFilter);
      row.classList.toggle('hidden', !matches);
      if (matches) visible++;
    });
    const counter = document.getElementById('client-filter-count');
    if (counter) {
      const total = document.querySelectorAll('.client-row').length;
      counter.textContent = visible < total ? 'Showing ' + visible + ' of ' + total : '';
    }
  }

  function sortClients(column) {
    const grid = document.getElementById('clients-grid');
    if (!grid) return;
    const cards = Array.from(grid.querySelectorAll('.client-row'));

    cards.sort(function(a, b) {
      let aVal;
      let bVal;
      if (column === 'requestCount' || column === 'lastRequestTime') {
        aVal = parseInt(a.dataset[column === 'requestCount' ? 'requestCount' : 'lastRequest'], 10) || 0;
        bVal = parseInt(b.dataset[column === 'requestCount' ? 'requestCount' : 'lastRequest'], 10) || 0;
        return bVal - aVal;
      }
      if (column === 'machineName') {
        aVal = a.dataset.machineName || '';
        bVal = b.dataset.machineName || '';
      } else if (column === 'licenseStatus') {
        aVal = a.dataset.licenseStatus || '';
        bVal = b.dataset.licenseStatus || '';
      } else {
        aVal = a.textContent.trim();
        bVal = b.textContent.trim();
      }
      return aVal.localeCompare(bVal);
    });

    cards.forEach(function(card) { grid.appendChild(card); });
  }

  function initClientsTable() {
    initCommon();

    const search = document.getElementById('client-search');
    const filter = document.getElementById('client-filter-app');
    const sort = document.getElementById('client-sort');
    if (search) search.addEventListener('input', filterClients);
    if (filter) filter.addEventListener('change', filterClients);
    if (sort) {
      sort.addEventListener('change', function() { sortClients(sort.value); });
      sortClients(sort.value);
    }
    filterClients();

    const refreshSelect = document.getElementById('auto-refresh');
    if (refreshSelect) {
      refreshSelect.addEventListener('change', function() {
        if (refreshTimer) { clearInterval(refreshTimer); refreshTimer = null; }
        const seconds = parseInt(refreshSelect.value, 10);
        if (seconds > 0) {
          refreshTimer = setInterval(function() { window.location.reload(); }, seconds * 1000);
        }
      });
    }
  }

  function copyGvlk(el) {
    const text = el.textContent.trim();
    navigator.clipboard.writeText(text).then(function() {
      el.classList.add('copied');
      showToast('Copied to clipboard', 'success');
      setTimeout(function() { el.classList.remove('copied'); }, 1200);
    }).catch(function() { showToast('Copy failed', 'error'); });
  }

  function toggleCategorySection(toggle) {
    const section = toggle.closest('.category-section');
    const body = section?.querySelector('.category-section-body');
    if (!body) return;
    const isOpen = toggle.getAttribute('aria-expanded') !== 'false';
    toggle.setAttribute('aria-expanded', isOpen ? 'false' : 'true');
    body.classList.toggle('open', !isOpen);
  }

  function filterProducts() {
    const query = (document.getElementById('product-search')?.value || '').toLowerCase();
    const typeFilter = (document.getElementById('product-filter-type')?.value || '').toLowerCase();

    document.querySelectorAll('.product-row').forEach(function(row) {
      const text = row.dataset.search || row.textContent.toLowerCase();
      const type = row.dataset.type || '';
      const matchesSearch = !query || text.includes(query);
      const matchesType = !typeFilter || type === typeFilter;
      row.classList.toggle('hidden', !(matchesSearch && matchesType));
    });

    document.querySelectorAll('.product-category').forEach(function(cat) {
      const visible = cat.querySelectorAll('.product-row:not(.hidden)').length;
      const matchesType = !typeFilter || (cat.dataset.type || '') === typeFilter;
      cat.classList.toggle('hidden', !matchesType || (visible === 0 && (query || typeFilter)));
      if (query && visible > 0) {
        const body = cat.querySelector('.category-section-body');
        const toggle = cat.querySelector('.category-toggle');
        if (body) body.classList.add('open');
        if (toggle) toggle.setAttribute('aria-expanded', 'true');
      }
    });
  }

  function initProducts() {
    initCommon();

    document.querySelectorAll('.category-toggle').forEach(function(toggle) {
      toggle.addEventListener('click', function() { toggleCategorySection(toggle); });
    });

    document.querySelectorAll('.gvlk-key').forEach(function(el) {
      el.addEventListener('click', function() { copyGvlk(el); });
      el.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') { e.preventDefault(); copyGvlk(el); }
      });
    });

    const search = document.getElementById('product-search');
    const typeFilter = document.getElementById('product-filter-type');
    if (search) search.addEventListener('input', filterProducts);
    if (typeFilter) typeFilter.addEventListener('change', filterProducts);
  }

  return {
    initCommon: initCommon,
    initDashboard: initDashboard,
    initClientsTable: initClientsTable,
    initClientsLive: initClientsLive,
    initActivationsLive: initActivationsLive,
    initProducts: initProducts,
    showToast: showToast,
    convertTimestamps: convertTimestamps
  };
})();

document.addEventListener('DOMContentLoaded', function() {
  PyKmsApp.convertTimestamps();
});

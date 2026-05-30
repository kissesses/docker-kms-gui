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
      const date = new Date(raw);
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
      })
      .catch(function() { setServerStatus(false, 'Unreachable'); });
  }

  function initCommon() {
    convertTimestamps();
    initTheme();
    initMobileNav();
    refreshStats();
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

  function sortClients(column, direction) {
    const tbody = document.querySelector('#clients-table tbody');
    if (!tbody) return;
    const rows = Array.from(tbody.querySelectorAll('.client-row'));
    const colIndex = Array.from(document.querySelectorAll('#clients-table th')).findIndex(function(th) {
      return th.dataset.sort === column;
    });
    if (colIndex < 0) return;

    rows.sort(function(a, b) {
      const aText = a.children[colIndex]?.textContent.trim() || '';
      const bText = b.children[colIndex]?.textContent.trim() || '';
      const aNum = parseFloat(aText);
      const bNum = parseFloat(bText);
      let cmp = (!isNaN(aNum) && !isNaN(bNum)) ? aNum - bNum : aText.localeCompare(bText);
      return direction === 'asc' ? cmp : -cmp;
    });
    rows.forEach(function(row) { tbody.appendChild(row); });
  }

  function initClientsTable() {
    initCommon();

    const search = document.getElementById('client-search');
    const filter = document.getElementById('client-filter-app');
    if (search) search.addEventListener('input', filterClients);
    if (filter) filter.addEventListener('change', filterClients);
    filterClients();

    document.querySelectorAll('#clients-table th.sortable').forEach(function(th) {
      th.addEventListener('click', function() {
        const col = th.dataset.sort;
        const isAsc = th.classList.contains('sort-asc');
        document.querySelectorAll('#clients-table th.sortable').forEach(function(h) {
          h.classList.remove('sort-asc', 'sort-desc');
        });
        const dir = isAsc ? 'desc' : 'asc';
        th.classList.add('sort-' + dir);
        sortClients(col, dir);
      });
    });

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

  function toggleCategory(header) {
    const body = header.nextElementSibling;
    const isOpen = header.classList.toggle('open');
    if (body) body.classList.toggle('open', isOpen);
    header.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
  }

  function filterProducts() {
    const query = (document.getElementById('product-search')?.value || '').toLowerCase();
    document.querySelectorAll('.product-row').forEach(function(row) {
      const text = row.dataset.search || row.textContent.toLowerCase();
      row.classList.toggle('hidden', query && !text.includes(query));
    });
    document.querySelectorAll('.product-category').forEach(function(cat) {
      const visible = cat.querySelectorAll('.product-row:not(.hidden)').length;
      cat.style.display = visible === 0 && query ? 'none' : '';
      if (query && visible > 0) {
        const header = cat.querySelector('.category-header');
        const body = cat.querySelector('.category-body');
        if (header && body) {
          header.classList.add('open');
          body.classList.add('open');
          header.setAttribute('aria-expanded', 'true');
        }
      }
    });
  }

  function initProducts() {
    initCommon();

    document.querySelectorAll('.category-header').forEach(function(header) {
      header.addEventListener('click', function() { toggleCategory(header); });
      header.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleCategory(header); }
      });
    });

    document.querySelectorAll('.gvlk-key').forEach(function(el) {
      el.addEventListener('click', function() { copyGvlk(el); });
      el.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') { e.preventDefault(); copyGvlk(el); }
      });
    });

    const search = document.getElementById('product-search');
    if (search) search.addEventListener('input', filterProducts);
  }

  return {
    initCommon: initCommon,
    initDashboard: initDashboard,
    initClientsTable: initClientsTable,
    initProducts: initProducts,
    showToast: showToast,
    convertTimestamps: convertTimestamps
  };
})();

document.addEventListener('DOMContentLoaded', function() {
  PyKmsApp.convertTimestamps();
});

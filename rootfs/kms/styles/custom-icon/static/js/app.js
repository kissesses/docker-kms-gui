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

  function initTheme() {
    const toggle = document.getElementById('theme-toggle');
    const saved = localStorage.getItem('pykms-theme') || 'dark';
    document.documentElement.classList.toggle('light', saved === 'light');

    if (toggle) {
      toggle.textContent = saved === 'light' ? 'Dark mode' : 'Light mode';
      toggle.addEventListener('click', function() {
        const isLight = document.documentElement.classList.toggle('light');
        localStorage.setItem('pykms-theme', isLight ? 'light' : 'dark');
        toggle.textContent = isLight ? 'Dark mode' : 'Light mode';
      });
    }
  }

  function initMobileNav() {
    const btn = document.getElementById('mobile-menu-toggle');
    const nav = document.getElementById('mobile-nav');
    if (btn && nav) {
      btn.addEventListener('click', function() {
        nav.classList.toggle('hidden');
      });
    }
  }

  function initDashboard() {
    convertTimestamps();
    initTheme();
    initMobileNav();

    function refreshStats() {
      fetch('/api/v1/stats')
        .then(function(r) { return r.json(); })
        .then(function(data) {
          if (data.error) return;
          document.querySelectorAll('[data-stat]').forEach(function(el) {
            const key = el.getAttribute('data-stat');
            if (data[key] !== undefined) {
              el.textContent = data[key];
            }
          });
          const uptimeEl = document.getElementById('stat-uptime');
          if (uptimeEl && data.uptime_seconds !== undefined) {
            uptimeEl.textContent = formatUptime(data.uptime_seconds);
          }
        })
        .catch(function() {});
    }

    refreshStats();
    setInterval(refreshStats, 30000);
  }

  function filterClients() {
    const query = (document.getElementById('client-search')?.value || '').toLowerCase();
    const appFilter = (document.getElementById('client-filter-app')?.value || '').toLowerCase();
    document.querySelectorAll('.client-row').forEach(function(row) {
      const text = [
        row.dataset.name,
        row.dataset.ip,
        row.dataset.app,
        row.dataset.status,
        row.textContent.toLowerCase()
      ].join(' ');
      const matchesQuery = !query || text.includes(query);
      const matchesApp = !appFilter || row.dataset.app === appFilter;
      row.classList.toggle('hidden', !(matchesQuery && matchesApp));
    });
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
      let cmp;
      if (!isNaN(aNum) && !isNaN(bNum)) {
        cmp = aNum - bNum;
      } else {
        cmp = aText.localeCompare(bText);
      }
      return direction === 'asc' ? cmp : -cmp;
    });

    rows.forEach(function(row) { tbody.appendChild(row); });
  }

  function initClientsTable() {
    convertTimestamps();
    initTheme();
    initMobileNav();

    const search = document.getElementById('client-search');
    const filter = document.getElementById('client-filter-app');
    if (search) search.addEventListener('input', filterClients);
    if (filter) filter.addEventListener('change', filterClients);

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
        if (refreshTimer) {
          clearInterval(refreshTimer);
          refreshTimer = null;
        }
        const seconds = parseInt(refreshSelect.value, 10);
        if (seconds > 0) {
          refreshTimer = setInterval(function() {
            window.location.reload();
          }, seconds * 1000);
        }
      });
    }
  }

  return {
    initDashboard: initDashboard,
    initClientsTable: initClientsTable,
    convertTimestamps: convertTimestamps
  };
})();

document.addEventListener('DOMContentLoaded', function() {
  PyKmsApp.convertTimestamps();
});

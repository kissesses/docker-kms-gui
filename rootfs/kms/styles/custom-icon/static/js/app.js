const PyKmsApp = (function() {
  let refreshTimer = null;
  let shellReady = false;
  let statsTimer = null;

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

  function fetchJson(url, timeoutMs) {
    const ms = timeoutMs || 10000;
    const controller = new AbortController();
    const timer = setTimeout(function() { controller.abort(); }, ms);
    return fetch(url, { credentials: 'same-origin', signal: controller.signal })
      .then(function(r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .finally(function() { clearTimeout(timer); });
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
      'content', isLight ? '#e5e5ea' : '#000000'
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
    const toggle = document.getElementById('mobile-nav-toggle');
    const nav = document.getElementById('mobile-nav');
    if (!toggle || !nav) return;

    function closeNav() {
      nav.hidden = true;
      nav.classList.remove('open');
      toggle.setAttribute('aria-expanded', 'false');
    }

    function openNav() {
      nav.hidden = false;
      nav.classList.add('open');
      toggle.setAttribute('aria-expanded', 'true');
    }

    toggle.addEventListener('click', function() {
      if (nav.classList.contains('open')) closeNav();
      else openNav();
    });
    nav.querySelectorAll('.nav-link').forEach(function(link) {
      link.addEventListener('click', closeNav);
    });
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape') closeNav();
    });
  }

  function setServerStatus(online, label) {
    const dot = document.getElementById('status-dot');
    const el = document.getElementById('status-text');
    const dotM = document.getElementById('status-dot-mobile');
    const elM = document.getElementById('status-text-mobile');
    const pill = document.getElementById('server-status');
    const pillM = document.getElementById('server-status-mobile');
    if (dot) dot.classList.toggle('live', online);
    if (el) el.textContent = label;
    if (dotM) dotM.classList.toggle('live', online);
    if (elM) elM.textContent = label;
    if (pill) pill.title = label;
    if (pillM) pillM.title = label;
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
    fetchJson('/api/v1/stats')
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

  function startStatsPolling(intervalMs) {
    if (statsTimer) return;
    statsTimer = setInterval(refreshStats, intervalMs || 30000);
  }

  function initCommon() {
    convertTimestamps();
    if (!shellReady) {
      shellReady = true;
      initTheme();
      initMobileNav();
    }
    refreshStats();
    startStatsPolling(30000);
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
      { v: windows, c: '#0a84ff' },
      { v: office, c: '#5ac8fa' }
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
    ctx.fillStyle = getComputedStyle(document.body).getPropertyValue('--glass-bg') || 'rgba(28,28,30,0.58)';
    ctx.fill();
  }

  function initClientsLive() {
    initClientsTable();
  }

  function initActivationsLive() {
    initCommon();
    function refreshActivations() {
      fetchJson('/api/v1/activations')
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
  }

  function filterClients() {
    const query = (document.getElementById('client-search')?.value || '').toLowerCase();
    const appFilter = (document.getElementById('client-filter-app')?.value || '').toLowerCase();
    const statusFilter = (document.getElementById('client-filter-status')?.value || '').toLowerCase();
    const healthFilter = (document.getElementById('client-filter-health')?.value || '').toLowerCase();
    let visible = 0;
    document.querySelectorAll('.client-row').forEach(function(row) {
      const text = [
        row.dataset.name, row.dataset.ip, row.dataset.app,
        row.dataset.status, row.textContent.toLowerCase()
      ].join(' ');
      const status = row.dataset.status || '';
      const matchesStatus = !statusFilter ||
        (statusFilter === 'notify' && status.includes('notifications')) ||
        (statusFilter === 'activated' && status.includes('activated')) ||
        status.includes(statusFilter);
      const matches = (!query || text.includes(query)) &&
                      (!appFilter || row.dataset.app === appFilter) &&
                      matchesStatus &&
                      (!healthFilter || row.dataset.health === healthFilter);
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

  function initClientSessionModal() {
    const modal = document.getElementById('client-modal');
    const body = document.getElementById('client-modal-body');
    const title = document.getElementById('client-modal-title');
    if (!modal || !body) return;

    function closeModal() {
      modal.hidden = true;
      modal.setAttribute('aria-hidden', 'true');
      body.innerHTML = '';
    }

    modal.querySelector('.modal-close')?.addEventListener('click', closeModal);
    modal.addEventListener('click', function(e) {
      if (e.target === modal) closeModal();
    });

    document.querySelectorAll('.client-session-btn').forEach(function(btn) {
      btn.addEventListener('click', function() {
        const clientId = btn.dataset.clientId;
        const appId = btn.dataset.appId;
        const machine = btn.dataset.machineName || 'Client';
        title.textContent = machine;
        body.innerHTML = '<p class="panel-desc">Loading session…</p>';
        modal.hidden = false;
        modal.setAttribute('aria-hidden', 'false');
        fetchJson('/api/v1/clients/' + encodeURIComponent(clientId) + '/' + encodeURIComponent(appId) + '/session')
          .then(function(data) {
            if (data.error) {
              body.innerHTML = '<div class="alert alert-error">' + data.error + '</div>';
              return;
            }
            body.innerHTML = renderClientSession(data);
            convertTimestamps();
          })
          .catch(function() {
            body.innerHTML = '<div class="alert alert-error">Failed to load session</div>';
          });
      });
    });
  }

  function renderClientSession(data) {
    function rows(obj) {
      return Object.keys(obj || {}).map(function(key) {
        return '<div class="info-row"><dt>' + key + '</dt><dd class="mono">' + (obj[key] ?? '—') + '</dd></div>';
      }).join('');
    }
    return ''
      + '<section class="modal-section"><h3 class="panel-subtitle">Received from client</h3><dl class="info-list">' + rows(data.received_from_client) + '</dl></section>'
      + '<section class="modal-section"><h3 class="panel-subtitle">Sent to client</h3><dl class="info-list">' + rows(data.sent_to_client) + '</dl></section>'
      + '<section class="modal-section"><h3 class="panel-subtitle">Schedule</h3><dl class="info-list">' + rows(data.schedule) + '</dl></section>';
  }

  function initClientsTable() {
    initCommon();
    initClientSessionModal();

    const search = document.getElementById('client-search');
    const filter = document.getElementById('client-filter-app');
    const statusFilter = document.getElementById('client-filter-status');
    const healthFilter = document.getElementById('client-filter-health');
    const sort = document.getElementById('client-sort');
    if (search) search.addEventListener('input', filterClients);
    if (filter) filter.addEventListener('change', filterClients);
    if (statusFilter) statusFilter.addEventListener('change', filterClients);
    if (healthFilter) healthFilter.addEventListener('change', filterClients);
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

    bindGvlkCopy(document.querySelectorAll('.gvlk-key'));

    const search = document.getElementById('product-search');
    const typeFilter = document.getElementById('product-filter-type');
    if (search) search.addEventListener('input', filterProducts);
    if (typeFilter) typeFilter.addEventListener('change', filterProducts);
  }

  function bindGvlkCopy(elements) {
    elements.forEach(function(el) {
      el.addEventListener('click', function() { copyGvlk(el); });
      el.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') { e.preventDefault(); copyGvlk(el); }
      });
    });
  }

  function sortKeyRows(mode) {
    const tbody = document.getElementById('keys-tbody');
    if (!tbody) return;
    const rows = Array.from(tbody.querySelectorAll('.keys-row'));
    const typeOrder = { windows: 0, office: 1, other: 2 };

    rows.sort(function(a, b) {
      if (mode === 'default') {
        return parseInt(a.dataset.defaultIndex, 10) - parseInt(b.dataset.defaultIndex, 10);
      }
      if (mode === 'name') {
        return (a.dataset.name || '').localeCompare(b.dataset.name || '');
      }
      if (mode === 'category') {
        const cat = (a.dataset.category || '').localeCompare(b.dataset.category || '');
        return cat !== 0 ? cat : (a.dataset.name || '').localeCompare(b.dataset.name || '');
      }
      if (mode === 'type') {
        const ta = typeOrder[a.dataset.type] ?? 9;
        const tb = typeOrder[b.dataset.type] ?? 9;
        if (ta !== tb) return ta - tb;
        const cat = (a.dataset.category || '').localeCompare(b.dataset.category || '');
        return cat !== 0 ? cat : (a.dataset.name || '').localeCompare(b.dataset.name || '');
      }
      return 0;
    });

    rows.forEach(function(row) { tbody.appendChild(row); });
  }

  function filterKeys() {
    const query = (document.getElementById('keys-search')?.value || '').toLowerCase();
    const typeFilter = (document.getElementById('keys-filter-type')?.value || '').toLowerCase();
    let visible = 0;

    document.querySelectorAll('.keys-row').forEach(function(row) {
      const text = row.dataset.search || row.textContent.toLowerCase();
      const type = row.dataset.type || '';
      const matchesSearch = !query || text.includes(query);
      const matchesType = !typeFilter || type === typeFilter;
      const show = matchesSearch && matchesType;
      row.classList.toggle('hidden', !show);
      if (show) visible += 1;
    });

    const countEl = document.getElementById('keys-count');
    if (countEl) {
      const label = countEl.dataset.label || '{n} shown';
      countEl.textContent = label.replace('{n}', String(visible));
    }
  }

  function initKeys() {
    initCommon();

    const tbody = document.getElementById('keys-tbody');
    if (tbody) {
      Array.from(tbody.querySelectorAll('.keys-row')).forEach(function(row, index) {
        row.dataset.defaultIndex = String(index);
      });
    }

    bindGvlkCopy(document.querySelectorAll('.gvlk-key'));

    document.querySelectorAll('.keys-copy-btn').forEach(function(btn) {
      btn.addEventListener('click', function() {
        const keyEl = btn.closest('.keys-row')?.querySelector('.gvlk-key');
        if (keyEl) copyGvlk(keyEl);
      });
    });

    const search = document.getElementById('keys-search');
    const typeFilter = document.getElementById('keys-filter-type');
    const sortSelect = document.getElementById('keys-sort');

    if (search) search.addEventListener('input', filterKeys);
    if (typeFilter) typeFilter.addEventListener('change', filterKeys);
    if (sortSelect) {
      sortSelect.addEventListener('change', function() {
        sortKeyRows(sortSelect.value || 'default');
        filterKeys();
      });
    }

    filterKeys();
  }

  function initLoginKeysPicker(labels) {
    labels = labels || {};
    const openBtn = document.getElementById('open-keys-picker');
    const modal = document.getElementById('keys-picker-modal');
    if (!openBtn || !modal) return;

    const search = document.getElementById('keys-picker-search');
    const typeFilter = document.getElementById('keys-picker-type');
    const list = document.getElementById('keys-picker-list');
    const status = document.getElementById('keys-picker-status');
    const result = document.getElementById('keys-picker-result');
    const nameEl = document.getElementById('keys-picker-name');
    const metaEl = document.getElementById('keys-picker-meta');
    const keyEl = document.getElementById('keys-picker-key');
    const copyBtn = document.getElementById('keys-picker-copy');

    let keysCache = Array.isArray(labels.keys) ? labels.keys : null;
    let loading = false;
    let selectedIndex = -1;

    function closeModal() {
      modal.hidden = true;
      modal.setAttribute('aria-hidden', 'true');
    }

    function openModal() {
      modal.hidden = false;
      modal.setAttribute('aria-hidden', 'false');
      loadKeys();
      if (search) {
        search.value = '';
        setTimeout(function() { search.focus(); }, 50);
      }
    }

    function setStatus(text) {
      if (status) status.textContent = text || '';
    }

    function loadKeys() {
      if (keysCache && keysCache.length) {
        renderList();
        return;
      }
      if (loading) return;
      loading = true;
      setStatus(labels.loading || 'Loading…');
      fetchJson('/api/v1/keys/public')
        .then(function(data) {
          keysCache = Array.isArray(data) ? data : [];
          if (!keysCache.length) {
            setStatus(labels.empty || 'No products found');
            if (list) list.innerHTML = '';
            if (result) result.hidden = true;
            return;
          }
          renderList();
        })
        .catch(function() {
          setStatus(labels.error || 'Could not load keys');
          if (list) list.innerHTML = '';
          if (result) result.hidden = true;
        })
        .finally(function() { loading = false; });
    }

    function filteredKeys() {
      if (!keysCache) return [];
      const q = (search?.value || '').toLowerCase();
      const type = typeFilter?.value || '';
      return keysCache.filter(function(row) {
        if (type && row.type !== type) return false;
        if (!q) return true;
        const hay = (row.category + ' ' + row.name + ' ' + row.gvlk).toLowerCase();
        return hay.includes(q);
      });
    }

    function selectKey(row, index) {
      selectedIndex = index;
      if (!row || !result || !keyEl) {
        if (result) result.hidden = true;
        return;
      }
      list?.querySelectorAll('.keys-picker-item').forEach(function(el, i) {
        el.classList.toggle('selected', i === index);
      });
      if (nameEl) nameEl.textContent = row.name;
      if (metaEl) metaEl.textContent = row.category;
      keyEl.textContent = row.gvlk;
      keyEl.classList.remove('copied');
      result.hidden = false;
    }

    function renderList() {
      if (!list) return;
      const rows = filteredKeys();
      list.innerHTML = '';
      selectedIndex = -1;
      if (result) result.hidden = true;

      if (!rows.length) {
        setStatus(labels.empty || 'No products found');
        return;
      }

      setStatus((labels.visible || '{n}').replace('{n}', String(rows.length)));

      rows.forEach(function(row, index) {
        const li = document.createElement('li');
        li.className = 'keys-picker-item';
        li.setAttribute('role', 'option');
        li.tabIndex = 0;
        li.innerHTML = '<span class="keys-picker-item-name"></span><span class="keys-picker-item-cat"></span>';
        li.querySelector('.keys-picker-item-name').textContent = row.name;
        li.querySelector('.keys-picker-item-cat').textContent = row.category;
        li.addEventListener('click', function() { selectKey(row, index); });
        li.addEventListener('keydown', function(e) {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            selectKey(row, index);
          }
        });
        list.appendChild(li);
      });

      selectKey(rows[0], 0);
    }

    openBtn.addEventListener('click', openModal);
    modal.querySelector('.modal-close')?.addEventListener('click', closeModal);
    modal.addEventListener('click', function(e) {
      if (e.target === modal) closeModal();
    });
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape' && !modal.hidden) closeModal();
    });

    if (search) search.addEventListener('input', renderList);
    if (typeFilter) typeFilter.addEventListener('change', renderList);
    if (keyEl) {
      keyEl.addEventListener('click', function() { copyGvlk(keyEl); });
      keyEl.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') { e.preventDefault(); copyGvlk(keyEl); }
      });
    }
    if (copyBtn && keyEl) {
      copyBtn.addEventListener('click', function() { copyGvlk(keyEl); });
    }
  }

  return {
    initCommon: initCommon,
    initDashboard: initDashboard,
    initClientsTable: initClientsTable,
    initClientsLive: initClientsLive,
    initActivationsLive: initActivationsLive,
    initProducts: initProducts,
    initKeys: initKeys,
    initLoginKeysPicker: initLoginKeysPicker,
    showToast: showToast,
    convertTimestamps: convertTimestamps
  };
})();

document.addEventListener('DOMContentLoaded', function() {
  PyKmsApp.convertTimestamps();
});

/**
 * URAAS — Dashboard Core Logic
 * Handles real-time updates via Socket.IO, analytics visualization, and crawler controls.
 */

const socket = io();
let archiveData = {}, charts = {}, networkEdgeData = null;
let yearDataCache = null, yearStackedCache = null, facultyDataCache = null;
let sdgData = null, trendsData = null, keywordData = null;
let analyticsLoaded = false, sdgLoaded = false, kwLoaded = false, trendsLoaded = false;
let currentAtab = 'overview';

// Global Color Palette
const COLORS = [
  '#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', 
  '#06b6d4', '#f97316', '#14b8a6', '#6366f1', '#84cc16', 
  '#e11d48', '#0ea5e9', '#a855f7', '#ec4899', '#64748b'
];

Chart.defaults.color = '#64748b';
Chart.defaults.borderColor = 'rgba(255, 255, 255, 0.04)';
Chart.defaults.font.family = "'Inter', sans-serif";

/**
 * UI Helpers
 */
const $ = (id) => document.getElementById(id);

const esc = (s) => String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

function safeFetch(url, ok, err) {
  return fetch(url)
    .then(r => {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    })
    .then(ok)
    .catch(e => {
      console.error(url, e);
      if (err) err(e);
    });
}

function destroyChart(id) {
  if (charts[id]) {
    try { charts[id].destroy(); } catch (e) { }
    delete charts[id];
  }
}

/**
 * Theme Management
 */
function toggleTheme() {
  const d = document.documentElement;
  const dark = d.getAttribute('data-theme') === 'dark';
  d.setAttribute('data-theme', dark ? 'light' : 'dark');
  $('icon-moon').classList.toggle('hidden', !dark);
  $('icon-sun').classList.toggle('hidden', dark);
  Chart.defaults.color = dark ? '#475569' : '#64748b';
  Object.values(charts).forEach(c => {
    try { c.update(); } catch (e) { }
  });
  localStorage.setItem('uraas-theme', dark ? 'light' : 'dark');
}

/**
 * Toast Notifications
 */
function showToast(msg, type = 'info', ms = 4000) {
  const c = $('toast-container');
  if (!c) return;
  const d = document.createElement('div');
  const icons = { success: '✓', error: '✕', info: 'ℹ', warning: '⚠' };
  d.className = `toast toast-${type}`;
  d.innerHTML = `<span style="font-size:16px; font-weight:bold">${icons[type] || ''}</span><span>${esc(msg)}</span>`;
  c.appendChild(d);
  setTimeout(() => {
    d.style.opacity = '0';
    d.style.transform = 'translateX(20px)';
    setTimeout(() => d.remove(), 350);
  }, ms);
}

// Map legacy 'toast' name
const toast = showToast;

/**
 * Tab Management
 */
function switchTab(name, btn) {
  document.querySelectorAll('.tab-content').forEach(e => e.classList.add('hidden'));
  document.querySelectorAll('.tab-btn[id^="tab-btn-"]').forEach(e => e.classList.remove('active'));
  const target = $('tab-' + name);
  if (target) target.classList.remove('hidden');
  if (btn) btn.classList.add('active');
  else {
    const b = $('tab-btn-' + name);
    if (b) b.classList.add('active');
  }
  
  if (name === 'analytics' && !analyticsLoaded) {
    analyticsLoaded = true;
    loadAnalyticsOverview();
  }
  if (name === 'archive') renderTree(archiveData);
  if (name === 'search') loadSearchFaculties();
}

function switchAtab(name, btn) {
  currentAtab = name;
  document.querySelectorAll('.atab-content').forEach(e => e.classList.add('hidden'));
  document.querySelectorAll('[id^="atab-btn-"]').forEach(e => e.classList.remove('active'));
  const t = $('atab-' + name);
  if (t) t.classList.remove('hidden');
  if (btn) btn.classList.add('active');
  
  if (name === 'sdg') loadSDGTab();
  if (name === 'trends') loadTrendsTab();
  if (name === 'compare') loadCompareDDs();
  if (name === 'language') loadLanguageTab();
  if (name === 'special') loadSpecialTab();
  if (name === 'staff') loadStaffDirectory();
  if (name === 'network') { /* Network tab handled by interactions */ }
}

/**
 * Analytics Data Loading
 */
function getInstitutionParam() {
  const sel = $('global-institution-select');
  return sel && sel.value ? '?institution=' + encodeURIComponent(sel.value) : '';
}

function withInst(url) {
  const inst = getInstitutionParam();
  if (!inst) return url;
  return url.includes('?') ? url + inst.replace('?', '&') : url + inst;
}

function applyGlobalInstitutionFilter() {
  invalidateCaches();
  const inst = getInstitutionParam();
  const sdgCsv = $('sdg-csv-btn'); if (sdgCsv) sdgCsv.href = '/api/analytics/sdg-alignment/export.csv' + inst;
  const specCsv = $('special-csv-btn'); if (specCsv) specCsv.href = '/api/analytics/special-collections/export.csv' + inst;
  
  if (currentAtab === 'overview') loadAnalyticsOverview();
  else if (currentAtab === 'sdg') { sdgLoaded = false; loadSDGTab(); }
  else if (currentAtab === 'trends') { trendsLoaded = false; loadTrendsTab(); }
  else if (currentAtab === 'language') { loadLanguageTab(); }
  else if (currentAtab === 'special') { loadSpecialTab(); }
  else if (currentAtab === 'staff') { loadStaffDirectory(); }
}

function invalidateCaches() {
  yearDataCache = yearStackedCache = facultyDataCache = null;
}

function loadAnalyticsOverview() {
  loadFacultiesDropdown();
  loadImpactCards();
  reloadYearChart();
  reloadFacultyChart();
  reloadOAChart();
  reloadAuthorsChart();
  loadFacultyOAChart();
  loadGrowthChart();
  loadTimelineChart();
  fetchOverview();
  fetchRecentPapers();
}

function loadFacultiesDropdown() {
  safeFetch('/api/analytics/faculties', data => {
    const selects = ['cmp-faculty-a', 'cmp-faculty-b', 'cmp-faculty-c', 'dept-cmp-faculty', 'search-faculty'];
    selects.forEach(id => {
      const sel = $(id);
      if (!sel) return;
      const current = sel.value;
      const first = sel.options[0];
      sel.innerHTML = '';
      if (first) sel.appendChild(first);
      data.forEach(f => {
        const opt = document.createElement('option');
        opt.value = f;
        opt.textContent = f.replace('Faculty of ', '').replace('College of ', '');
        sel.appendChild(opt);
      });
      if (current) sel.value = current;
    });
  });
}

/**
 * Counter Animation
 */
function animCount(el, target, suffix = '') {
  if (!el || isNaN(target)) return;
  const dur = 1000, start = performance.now();
  (function tick(now) {
    const p = Math.min((now - start) / dur, 1);
    const ease = 1 - Math.pow(1 - p, 3);
    const v = Math.round(ease * target);
    el.textContent = v.toLocaleString() + suffix;
    if (p < 1) requestAnimationFrame(tick);
  })(start);
}

/**
 * Impact Metrics
 */
function loadImpactCards() {
  safeFetch(withInst('/api/analytics/impact-metrics'), d => {
    const impactCards = $('impact-cards');
    if (!impactCards) return;
    impactCards.innerHTML = [
      { l: 'DOI Coverage', v: d.doi_rate + '%', c: 'var(--accent)' },
      { l: 'Open Access', v: d.oa_rate + '%', c: 'var(--success)' },
      { l: 'PDF Coverage', v: d.pdf_rate + '%', c: 'var(--warning)' },
      { l: 'Years Covered', v: d.years_covered, c: '#60a5fa' },
    ].map(x => `
      <div class="surface rounded-xl p-4 stat-card">
        <p class="section-label">${x.l}</p>
        <p class="text-2xl font-bold" style="color:${x.c}">${x.v}</p>
      </div>
    `).join('');
  });

  if (!$('adv-metrics-cards')) {
    $('impact-cards').insertAdjacentHTML('afterend', '<div class="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-5" id="adv-metrics-cards"></div>');
  }
  
  const advMetrics = [
    { id: 'tk_vitality', l: 'TK Vitality Score', c: '#a855f7', api: '/api/analytics/tk-vitality-score', f: d => d.score + '/100' },
    { id: 'ling_div', l: 'Linguistic Diversity', c: '#ec4899', api: '/api/analytics/linguistic-diversity-index', f: d => d.index },
    { id: 'pat_vel', l: 'Patent Velocity', c: '#14b8a6', api: '/api/analytics/patent-velocity', f: d => (d.avg_days_to_patent ? (d.avg_days_to_patent / 365).toFixed(1) : '0') + ' yrs' },
    { id: 'docid_cov', l: 'DocID™ Coverage', c: '#6366f1', api: '/api/analytics/docid-coverage', f: d => d.coverage_percent + '%' }
  ];
  
  const advContainer = $('adv-metrics-cards');
  if (advContainer) advContainer.innerHTML = '';
  advMetrics.forEach(metric => {
    safeFetch(withInst(metric.api), d => {
      if (advContainer) advContainer.insertAdjacentHTML('beforeend',
        `<div id="${metric.id}-card" class="surface rounded-xl p-4 stat-card" style="border: 1px solid ${metric.c}30; background: ${metric.c}0a">
          <p class="section-label" style="color:${metric.c}">${metric.l}</p>
          <p class="text-2xl font-bold" style="color:${metric.c}">${metric.f(d)}</p>
        </div>`
      );
    });
  });
}

/**
 * Chart Loading Functions
 */
function reloadYearChart() {
  const mode = $('year-chart-mode').value;
  if (mode === 'stacked') {
    if (yearStackedCache) { renderStackedYear(yearStackedCache); return; }
    safeFetch(withInst('/api/analytics/papers-by-year-faculty'), d => { yearStackedCache = d; renderStackedYear(d); });
  } else {
    if (yearDataCache) { renderSimpleYear(yearDataCache); return; }
    safeFetch(withInst('/api/analytics/publications-by-year'), d => { yearDataCache = d; renderSimpleYear(d); });
  }
}

function renderSimpleYear(data) {
  destroyChart('year'); if (!data || !data.length) return;
  charts['year'] = new Chart($('chart-year'), {
    type: 'bar',
    data: {
      labels: data.map(d => d.year),
      datasets: [{ label: 'Papers', data: data.map(d => d.count), backgroundColor: 'rgba(59, 130, 246, 0.7)', borderRadius: 6 }]
    },
    options: {
      plugins: { legend: { display: false } },
      scales: { x: { grid: { display: false } }, y: { beginAtZero: true } },
      onClick: (e, el) => {
        if (el[0]) {
          switchTab('search', $('tab-btn-search'));
          $('search-year-from').value = data[el[0].index].year;
          $('search-year-to').value = data[el[0].index].year;
          runSearch();
        }
      }
    }
  });
}

function renderStackedYear(data) {
  destroyChart('year'); if (!data || !data.length) return;
  const years = [...new Set(data.map(d => d.year))].sort();
  const facs = [...new Set(data.map(d => d.faculty))];
  charts['year'] = new Chart($('chart-year'), {
    type: 'bar',
    data: {
      labels: years,
      datasets: facs.map((f, i) => ({
        label: f.replace('Faculty of ', '').replace('College of ', ''),
        data: years.map(y => { const r = data.find(d => d.year === y && d.faculty === f); return r ? r.count : 0; }),
        backgroundColor: COLORS[i % COLORS.length],
        borderRadius: 2
      }))
    },
    options: {
      plugins: { legend: { position: 'bottom', labels: { font: { size: 10 }, padding: 10 } } },
      scales: { x: { stacked: true, grid: { display: false } }, y: { stacked: true, beginAtZero: true } }
    }
  });
}

function reloadFacultyChart() {
  const type = $('faculty-chart-type').value;
  if (facultyDataCache) { renderFacultyChart(facultyDataCache, type); return; }
  safeFetch(withInst('/api/analytics/papers-by-faculty'), d => { facultyDataCache = d; renderFacultyChart(d, type); });
}

function renderFacultyChart(data, type) {
  destroyChart('faculty'); if (!data || !data.length) return;
  const labels = data.map(d => d.faculty.replace('Faculty of ', '').replace('College of ', ''));
  charts['faculty'] = new Chart($('chart-faculty'), {
    type, data: { labels, datasets: [{ data: data.map(d => d.count), backgroundColor: COLORS, borderRadius: type === 'bar' ? 6 : 0 }] },
    options: {
      indexAxis: type === 'bar' ? 'y' : undefined,
      plugins: { legend: { display: type === 'doughnut', position: 'bottom' } },
      scales: type === 'bar' ? { x: { beginAtZero: true }, y: { grid: { display: false } } } : {},
      cutout: type === 'doughnut' ? '70%' : undefined
    }
  });
}

function reloadOAChart() {
  const type = $('oa-chart-type').value;
  safeFetch(withInst('/api/analytics/open-access-breakdown'), data => {
    destroyChart('oa');
    charts['oa'] = new Chart($('chart-oa'), {
      type, data: {
        labels: data.map(d => d.label),
        datasets: [{ data: data.map(d => d.value), backgroundColor: ['#10b981', '#ef4444', '#64748b'], borderRadius: type === 'bar' ? 6 : 0 }]
      },
      options: {
        plugins: { legend: { display: type === 'doughnut', position: 'bottom' } },
        scales: type === 'bar' ? { x: { grid: { display: false } }, y: { beginAtZero: true } } : {},
        cutout: type === 'doughnut' ? '70%' : undefined
      }
    });
  });
}

function reloadAuthorsChart() {
  const limit = $('authors-limit').value;
  safeFetch(withInst('/api/analytics/top-authors?limit=' + limit), data => {
    destroyChart('authors');
    charts['authors'] = new Chart($('chart-authors'), {
      type: 'bar', data: {
        labels: data.map(d => d.author),
        datasets: [{ label: 'Papers', data: data.map(d => d.count), backgroundColor: 'rgba(59, 130, 246, 0.7)', borderRadius: 6 }]
      },
      options: {
        indexAxis: 'y', plugins: { legend: { display: false } },
        scales: { x: { beginAtZero: true }, y: { grid: { display: false } } }
      }
    });
  });
}

function loadFacultyOAChart() {
  safeFetch(withInst('/api/analytics/faculty-oa-breakdown'), data => {
    destroyChart('faculty-oa');
    const sorted = data.sort((a, b) => (b.oa + b.restricted) - (a.oa + a.restricted)).slice(0, 10);
    charts['faculty-oa'] = new Chart($('chart-faculty-oa'), {
      type: 'bar',
      data: {
        labels: sorted.map(d => d.faculty.replace('Faculty of ', '').replace('College of ', '')),
        datasets: [
          { label: 'Open Access', data: sorted.map(d => d.oa), backgroundColor: 'rgba(16, 185, 129, 0.7)', borderRadius: 4 },
          { label: 'Restricted', data: sorted.map(d => d.restricted), backgroundColor: 'rgba(239, 68, 68, 0.5)', borderRadius: 4 }
        ]
      },
      options: { indexAxis: 'y', plugins: { legend: { position: 'bottom' } }, scales: { x: { beginAtZero: true }, y: { grid: { display: false } } } }
    });
  });
}

function loadGrowthChart() {
  safeFetch(withInst('/api/analytics/growth-rate'), data => {
    destroyChart('growth'); if (!data || !data.length) return;
    charts['growth'] = new Chart($('chart-growth'), {
      type: 'line', data: {
        labels: data.map(d => d.session || ''),
        datasets: [{ label: 'Papers Added', data: data.map(d => d.count), borderColor: '#6366f1', backgroundColor: 'rgba(99, 102, 241, 0.1)', fill: true, tension: 0.4 }]
      },
      options: { plugins: { legend: { display: false } }, scales: { x: { display: false }, y: { beginAtZero: true } } }
    });
  });
}

function loadTimelineChart() {
  safeFetch(withInst('/api/analytics/timeline'), data => {
    destroyChart('timeline'); if (!data || !data.length) return;
    charts['timeline'] = new Chart($('chart-timeline'), {
      type: 'line', data: {
        labels: data.map(d => d.date),
        datasets: [{ label: 'Total Papers', data: data.map(d => d.total), borderColor: '#10b981', backgroundColor: 'rgba(16, 185, 129, 0.1)', fill: true, tension: 0.4 }]
      },
      options: { plugins: { legend: { display: false } }, scales: { x: { display: false }, y: { beginAtZero: true } } }
    });
  });
}

/**
 * SDG Alignment
 */
const SDG_COLORS = { 'SDG 1': '#E5243B', 'SDG 2': '#DDA63A', 'SDG 3': '#4C9F38', 'SDG 4': '#C5192D', 'SDG 5': '#FF3A21', 'SDG 6': '#26BDE2', 'SDG 7': '#FCC30B', 'SDG 8': '#A21942', 'SDG 9': '#FD6925', 'SDG 10': '#DD1367', 'SDG 11': '#FD9D24', 'SDG 12': '#BF8B2E', 'SDG 13': '#3F7E44', 'SDG 14': '#0A97D9', 'SDG 15': '#56C02B', 'SDG 16': '#00689D', 'SDG 17': '#19486A' };

function loadSDGTab() {
  if (sdgLoaded) return;
  safeFetch(withInst('/api/analytics/sdg-alignment'), data => {
    sdgLoaded = true; sdgData = data;
    const loading = $('sdg-loading'), grid = $('sdg-grid');
    if (loading) loading.classList.add('hidden');
    if (grid) grid.classList.remove('hidden');
    renderSDGGrid(data);
  });
}

function renderSDGGrid(data) {
  const grid = $('sdg-grid'); if (!grid) return;
  if (!data || !data.length) {
    grid.innerHTML = '<p class="col-span-full text-center py-10 text-sm">No SDG data found.</p>';
    return;
  }
  const maxCount = Math.max(...data.map(d => d.count));
  grid.innerHTML = data.map((item, idx) => {
    const sdgNum = item.sdg.match(/SDG (\d+)/)?.[1] || (idx + 1);
    const color = SDG_COLORS['SDG ' + sdgNum] || '#6366f1';
    const barWidth = Math.max(10, Math.round(item.count / maxCount * 100));
    return `
      <div class="sdg-card surface" style="border-color:${color}40; background:${color}08" onclick="openSDGPanel(${idx})">
        <div style="font-size:12px; font-weight:700; color:${color}; opacity:0.8; margin-bottom:4px">SDG ${sdgNum}</div>
        <p style="font-size:11px; font-weight:600; color:${color}; line-height:1.2; height:2.4em; overflow:hidden">${esc(item.sdg)}</p>
        <div class="flex items-end justify-between mt-2">
          <span style="font-size:1.5rem; font-weight:800; color:${color}">${item.count}</span>
          <span class="text-[10px]" style="color:${color}; opacity:0.6">papers</span>
        </div>
        <div style="margin-top:8px; height:4px; border-radius:4px; background:${color}20">
          <div style="width:${barWidth}%; height:100%; background:${color}; border-radius:4px;"></div>
        </div>
      </div>
    `;
  }).join('');
}

function openSDGPanel(idx) {
  if (!sdgData || !sdgData[idx]) return;
  const item = sdgData[idx];
  const panel = $('sdg-papers-panel'), title = $('sdg-panel-title'), list = $('sdg-papers-list');
  title.textContent = item.sdg + ' — ' + item.count + ' papers';
  list.innerHTML = (item.papers || []).map(p => `
    <div class="row-hover p-3 rounded-lg cursor-pointer" onclick="openPaperModal(${p.id})">
      <p class="text-sm font-medium">${esc(p.title)}</p>
      <div class="flex items-center gap-2 mt-1">
        <span class="text-xs text-muted">Score: ${p.score}</span>
        ${(p.keywords || []).slice(0, 3).map(k => `<span class="chip text-[10px] py-0.5 px-2">${esc(k)}</span>`).join('')}
      </div>
    </div>`).join('') || '<p class="text-xs text-center py-4">No paper details available.</p>';
  panel.classList.remove('hidden');
  panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function closeSdgPanel() { $('sdg-papers-panel')?.classList.add('hidden'); }

/**
 * Research Trends
 */
function loadTrendsTab() {
  if (trendsLoaded) return;
  safeFetch(withInst('/api/analytics/research-trends'), data => {
    trendsLoaded = true; trendsData = data;
    renderTrendsChips();
    renderTrendsLeaderboard();
  });
}

function renderTrendsChips() {
  const el = $('trends-chips'); if (!el || !trendsData) return;
  el.innerHTML = trendsData.map((t, i) => `<button class="chip ${i === 0 ? 'active' : ''}" onclick="selectTrend(${i}, this)">${esc(t.topic)} <span style="opacity:0.6">(${t.total})</span></button>`).join('');
  selectTrend(0, el.querySelector('.chip'));
}

function renderTrendsLeaderboard() {
  const el = $('trends-leaderboard'); if (!el || !trendsData) return;
  const maxTotal = Math.max(...trendsData.map(t => t.total));
  el.innerHTML = trendsData.map((t, i) => `
    <div class="flex items-center gap-3 py-2">
      <span class="text-xs mono w-6 text-right text-muted">${i + 1}</span>
      <span class="text-sm font-medium flex-1">${esc(t.topic)}</span>
      <div class="flex-1 max-w-[120px] h-2 rounded bg-slate-800">
        <div style="width:${t.total / maxTotal * 100}%; height:100%; background:${COLORS[i % COLORS.length]}; border-radius:4px"></div>
      </div>
      <span class="text-xs font-bold mono" style="color:${COLORS[i % COLORS.length]}; min-width:30px; text-align:right">${t.total}</span>
    </div>`).join('');
}

function selectTrend(idx, btn) {
  document.querySelectorAll('#trends-chips .chip').forEach(c => c.classList.remove('active'));
  if (btn) btn.classList.add('active');
  const t = trendsData[idx];
  destroyChart('trends');
  charts['trends'] = new Chart($('chart-trends'), {
    type: 'line',
    data: {
      labels: t.by_year.map(d => d.year),
      datasets: [{ label: t.topic, data: t.by_year.map(d => d.count), borderColor: COLORS[idx % COLORS.length], backgroundColor: COLORS[idx % COLORS.length] + '10', fill: true, tension: 0.4 }]
    },
    options: { plugins: { legend: { display: false } }, scales: { x: { grid: { display: false } }, y: { beginAtZero: true } } }
  });
}

/**
 * Collaboration Network (D3.js)
 */
let netTimer = null, curNetAuthor = null, d3Sim = null;
function debNetSearch() { clearTimeout(netTimer); netTimer = setTimeout(searchNetAuthor, 300); }

function searchNetAuthor() {
  const q = $('network-search-input').value.trim();
  const sugg = $('network-suggestions');
  if (q.length < 2) { sugg.innerHTML = ''; $('network-result').classList.add('hidden'); return; }
  safeFetch(withInst('/api/analytics/authors-search?q=' + encodeURIComponent(q) + '&limit=8'), authors => {
    if (!authors.length) { sugg.innerHTML = '<p class="text-xs p-2 text-muted">No researchers found</p>'; return; }
    sugg.innerHTML = authors.map(a => `<button class="chip" onclick="loadNetForAuthor('${esc(a.name).replace(/'/g, "\\'")}')">${esc(a.name)} <span style="opacity:0.6">(${a.papers})</span></button>`).join('');
  });
}

function loadNetForAuthor(name) {
  curNetAuthor = name;
  $('network-suggestions').innerHTML = '';
  $('network-search-input').value = name;
  $('network-researcher-name').textContent = name + ' — Collaboration Graph';
  $('network-result').classList.remove('hidden');
  safeFetch(withInst('/api/analytics/author-network?author=' + encodeURIComponent(name)), data => {
    networkEdgeData = data.edges;
    renderD3Net(data, name);
    renderNetTable(data, name);
  });
}

function renderD3Net(data, center) {
  const svg = d3.select('#network-svg');
  svg.selectAll('*').remove();
  const cont = $('network-graph-container');
  const W = cont.offsetWidth || 700, H = 420;
  svg.attr('viewBox', `0 0 ${W} ${H}`);
  
  if (!data.nodes || data.nodes.length <= 1) {
    svg.append('text').attr('x', W / 2).attr('y', H / 2).attr('text-anchor', 'middle').attr('fill', '#64748b').text('No collaborations found.');
    return;
  }
  
  const nodes = data.nodes.map(n => ({ ...n, x: W / 2, y: H / 2 }));
  const links = data.edges.map(e => ({ ...e }));
  
  const lnk = svg.append('g').selectAll('line').data(links).enter().append('line').attr('stroke', 'rgba(59, 130, 246, 0.2)').attr('stroke-width', d => Math.max(1, Math.min(d.weight, 5)));
  
  const nd = svg.append('g').selectAll('g').data(nodes).enter().append('g').style('cursor', 'pointer')
    .call(d3.drag().on('start', (ev, d) => { if (!ev.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; }).on('drag', (ev, d) => { d.fx = ev.x; d.fy = ev.y; }).on('end', (ev, d) => { if (!ev.active) sim.alphaTarget(0); d.fx = null; d.fy = null; }));
    
  nd.append('circle').attr('r', d => d.id === center ? 20 : 12).attr('fill', d => d.id === center ? '#3b82f6' : '#8b5cf6').attr('stroke', '#fff').attr('stroke-width', 1.5);
  nd.append('text').attr('text-anchor', 'middle').attr('dy', '.35em').attr('font-size', '10px').attr('fill', '#fff').text(d => d.id.split(' ').pop());
  nd.on('click', (ev, d) => { if (d.id !== center) loadNetForAuthor(d.id); });
  
  const sim = d3.forceSimulation(nodes).force('link', d3.forceLink(links).id(d => d.id).distance(100)).force('charge', d3.forceManyBody().strength(-200)).force('center', d3.forceCenter(W / 2, H / 2))
    .on('tick', () => { lnk.attr('x1', d => d.source.x).attr('y1', d => d.source.y).attr('x2', d => d.target.x).attr('y2', d => d.target.y); nd.attr('transform', d => `translate(${d.x},${d.y})`); });
  d3Sim = sim;
}

function renderNetTable(data, center) {
  const el = $('network-table'); if (!el) return;
  el.innerHTML = `<p class="section-label mt-4">Co-authors (${data.edges.length})</p><div class="grid grid-cols-2 lg:grid-cols-4 gap-2">` +
    data.edges.map(e => {
      const c = e.source === center ? e.target : e.source;
      return `<div class="surface p-3 rounded-lg cursor-pointer row-hover" onclick="loadNetForAuthor('${esc(c).replace(/'/g, "\\'")}')"><p class="text-xs font-bold">${esc(c)}</p><p class="text-[10px] text-accent">${e.weight} joint papers</p></div>`;
    }).join('') + '</div>';
}

/**
 * Comparator Engine
 */
let selectedInstitutions = [];
function addInstitutionToComparison() {
  const input = $('comp-institution-input');
  const value = input.value.trim();
  if (!value || selectedInstitutions.includes(value) || selectedInstitutions.length >= 10) return;
  selectedInstitutions.push(value);
  input.value = '';
  renderSelectedInstitutions();
}
function quickAddInstitution(ror) {
  if (!ror || selectedInstitutions.includes(ror) || selectedInstitutions.length >= 10) return;
  selectedInstitutions.push(ror);
  renderSelectedInstitutions();
}
function removeInstitution(ror) {
  selectedInstitutions = selectedInstitutions.filter(r => r !== ror);
  renderSelectedInstitutions();
}
function renderSelectedInstitutions() {
  const container = $('comp-selected-institutions'); if (!container) return;
  if (selectedInstitutions.length === 0) { container.innerHTML = '<p class="text-xs text-muted">No institutions selected.</p>'; return; }
  container.innerHTML = selectedInstitutions.map(ror => `<div class="chip active">${ror.split('/').pop()} <button onclick="removeInstitution('${ror}')" class="ml-1">×</button></div>`).join('');
}
function runComparison() {
  if (selectedInstitutions.length < 2) { toast('Add at least 2 institutions', 'warning'); return; }
  const btn = $('comp-run-btn'); btn.disabled = true;
  fetch('/api/comparator/compare', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ror_ids: selectedInstitutions }) })
    .then(r => r.json()).then(data => { renderComparisonResults(data); $('comp-results').classList.remove('hidden'); })
    .finally(() => btn.disabled = false);
}
function renderComparisonResults(data) {
  const tbody = $('comp-table-body');
  tbody.innerHTML = data.institutions.map(inst => `
    <tr class="row-hover border-b border-white/5">
      <td class="py-3 px-2 font-medium">${inst.name}</td>
      <td class="py-3 px-2 text-right">${inst.metrics.total_papers.toLocaleString()}</td>
      <td class="py-3 px-2 text-right">${inst.metrics.total_authors.toLocaleString()}</td>
      <td class="py-3 px-2 text-right">${inst.metrics.oa_rate}%</td>
      <td class="py-3 px-2 text-right">${inst.metrics.tk_rate}%</td>
      <td class="py-3 px-2 text-right">${inst.metrics.patents}</td>
      <td class="py-3 px-2 text-right">${inst.metrics.growth_rate}%</td>
    </tr>`).join('');
}

/**
 * Special Collections
 */
function loadSpecialTab() {
  $('special-loading').classList.remove('hidden');
  $('special-content').classList.add('hidden');
  safeFetch(withInst('/api/analytics/special-collections'), data => {
    $('special-loading').classList.add('hidden');
    $('special-content').classList.remove('hidden');
    
    // Stats
    const statsEl = $('special-stats');
    statsEl.innerHTML = `
      <div class="surface rounded-xl p-5 stat-card">
        <p class="section-label">Total Special Items</p>
        <p class="text-3xl font-bold" style="color:var(--accent)">${data.total_special_items}</p>
        <p class="text-xs mt-1 text-muted">${Math.round(data.total_special_items / data.total_repository_items * 100) || 0}% of repository</p>
      </div>
      <div class="surface rounded-xl p-5 stat-card">
        <p class="section-label">Categories Tracked</p>
        <p class="text-3xl font-bold" style="color:var(--success)">${data.summary.length}</p>
      </div>
      <div class="surface rounded-xl p-5 stat-card">
        <p class="section-label">Classification Status</p>
        <p class="text-3xl font-bold" style="color:var(--warning)">OPTIMIZED</p>
      </div>
    `;
    
    // Categories
    const catEl = $('special-categories');
    catEl.innerHTML = data.summary.map(cat => `
      <div class="surface rounded-xl p-5">
        <div class="flex justify-between items-center mb-4">
          <p class="section-label mb-0">${esc(cat.category)}</p>
          <span class="badge-oa">${cat.count} items</span>
        </div>
        <div class="space-y-2" style="max-height:300px; overflow-y:auto">
          ${cat.top_papers.map(p => `
            <div class="row-hover p-2.5 rounded-lg cursor-pointer border-b" style="border-color:var(--border)" onclick="openPaperModal(${p.id})">
              <p class="text-sm font-medium">${esc(p.title)}</p>
              <div class="flex gap-1 mt-1 flex-wrap">
                ${p.matches.slice(0, 3).map(m => `<span class="chip text-[10px] py-0.5 px-1.5">${esc(m)}</span>`).join('')}
              </div>
            </div>
          `).join('')}
          ${cat.count === 0 ? '<p class="text-xs text-center py-4 text-muted">No items found.</p>' : ''}
        </div>
      </div>
    `).join('');
  });
}

/**
 * Crawler Management
 */
function startCrawler() {
  const s = $('btn-start'); if (s) s.disabled = true;
  const inst = $('crawler-institution').value;
  const t = Math.min(Math.max(parseInt($('target-count').value) || 20, 1), 250);
  const boost = $('boost-special').checked;
  const scOnly = $('sc-only').checked;
  
  appendLog('// Starting crawler for ' + inst + ' — target: ' + t + ' papers' + (scOnly ? ' [SC ONLY]' : ''));
  toast('Mining started for ' + inst, 'info');
  updateCrawlerUI({ status: 'initializing' });
  
  fetch('/api/crawler/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ target: t, institution: inst, boost_special: boost, sc_only: scOnly })
  })
  .then(r => r.json())
  .then(d => {
    if (s) s.disabled = false;
    if (d.status !== 'success') {
      appendLog('// Error: ' + d.message);
      toast(d.message, 'error');
      if (d.message !== 'Crawler already running') updateCrawlerUI({ status: 'stopped' });
    }
  })
  .catch(() => {
    if (s) s.disabled = false;
    updateCrawlerUI({ status: 'stopped' });
  });
}

function stopCrawler() {
  fetch('/api/crawler/stop', { method: 'POST' })
    .then(r => r.json())
    .then(d => toast(d.message, d.status === 'success' ? 'warning' : 'error'));
}

function updateCrawlerUI(d) {
  const badge = $('crawler-badge'), s = $('btn-start'), st = $('btn-stop'), bar = $('crawler-progress');
  if (d.status === 'running') {
    if (badge) {
      badge.innerHTML = '<span class="live-dot"></span>Running';
      badge.style.background = 'rgba(16,197,94,0.12)';
      badge.style.color = '#10b981';
    }
    s?.classList.add('hidden');
    st?.classList.remove('hidden');
    bar?.classList.add('active');
  } else if (d.status === 'initializing') {
    if (badge) badge.textContent = '⟳ Init…';
    s?.classList.add('hidden');
    st?.classList.remove('hidden');
    bar?.classList.add('active');
  } else {
    if (badge) badge.textContent = '●Idle';
    s?.classList.remove('hidden');
    st?.classList.add('hidden');
    bar?.classList.remove('active');
    setTimeout(() => {
      fetchOverview(); fetchArchive(); fetchRecentPapers(); invalidateCaches();
      if (analyticsLoaded) loadAnalyticsOverview();
    }, 2000);
  }
}

function appendLog(text, termId = 'terminal-log') {
  const term = $(termId); if (!term) return;
  const d = document.createElement('div');
  const t = new Date().toLocaleTimeString('en', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
  d.innerHTML = `<span class="text-slate-500">[${t}]</span> ${esc(text)}`;
  
  if (/\[OK\]|stored|success/i.test(text)) d.style.color = '#4ade80';
  else if (/error|ERROR|\[ERR\]/i.test(text)) d.style.color = '#f87171';
  else if (/skip|duplicate|warn/i.test(text)) d.style.color = '#fbbf24';
  
  term.appendChild(d);
  term.scrollTop = term.scrollHeight;
  while (term.children.length > 200) term.removeChild(term.firstChild);
}

socket.on('crawl_status', updateCrawlerUI);
socket.on('terminal_output', d => appendLog(d.line));
socket.on('crawl_progress', d => { if (d.title) appendLog('[OK] ' + d.title); });

/**
 * Archive Directory
 */
function fetchArchive() {
  const inst = $('archive-institution-select')?.value || '';
  safeFetch('/api/papers/tree' + (inst ? '?institution=' + inst : ''), d => {
    archiveData = d.data || {};
    renderTree(archiveData);
  });
}

function renderTree(data, q = '') {
  const c = $('tree-container'); if (!c) return;
  if (!data || !Object.keys(data).length) {
    c.innerHTML = '<p class="text-sm py-10 text-center text-muted">No papers indexed yet.</p>';
    return;
  }
  
  let html = '', total = 0;
  for (const [fac, depts] of Object.entries(data)) {
    let fhtml = '', fc = 0;
    for (const [dept, papers] of Object.entries(depts)) {
      const filtered = q ? papers.filter(p => (p.title || '').toLowerCase().includes(q) || (p.doi || '').toLowerCase().includes(q)) : papers;
      if (!filtered.length) continue;
      fc += filtered.length; total += filtered.length;
      fhtml += `
        <div class="tree-node mb-4">
          <div class="flex items-center gap-2 mb-2">
            <span class="text-xs font-bold text-accent">${esc(dept)}</span>
            <span class="text-[10px] px-1.5 rounded bg-slate-800 text-slate-400 font-mono">${filtered.length}</span>
          </div>
          <ul class="space-y-1.5 ml-2">
            ${filtered.map(p => `
              <li class="row-hover p-2.5 rounded-lg cursor-pointer" onclick="openPaperModal(${p.id})">
                <p class="text-sm font-medium leading-tight">${esc(p.title || 'Untitled')}</p>
                <div class="flex justify-between items-center mt-1.5">
                  <span class="text-[10px] font-mono text-muted">${(p.doi || '').substring(0, 30)}</span>
                  <span class="${p.has_local_pdf ? 'badge-oa' : 'badge-restricted'} text-[9px]">${p.has_local_pdf ? 'PDF' : 'LINK'}</span>
                </div>
              </li>`).join('')}
          </ul>
        </div>`;
    }
    if (fc > 0) {
      html += `
        <div class="mb-6">
          <div class="flex items-center gap-2 border-b border-white/5 pb-2 mb-3">
            <span class="text-sm font-bold text-slate-200">${esc(fac)}</span>
            <span class="text-[10px] font-bold px-2 py-0.5 rounded-full bg-accent/10 text-accent">${fc}</span>
          </div>
          ${fhtml}
        </div>`;
    }
  }
  c.innerHTML = html || '<p class="text-sm text-center py-10 text-muted">No results found.</p>';
  const b = $('total-papers-badge'); if (b) b.textContent = total.toLocaleString() + ' papers';
}

/**
 * Paper Details Modal
 */
function openPaperModal(id) {
  $('paper-modal').classList.add('open');
  $('modal-body').innerHTML = '<div class="flex justify-center py-12"><div class="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin"></div></div>';
  
  Promise.all([
    fetch('/api/papers/' + id).then(r => r.json()),
    fetch('/api/citations/' + id).then(r => r.json()).catch(() => ({ citation_count: 0 }))
  ]).then(([p, cit]) => {
    $('modal-title').textContent = p.title;
    const authors = (p.authors || []).map(a => esc(a.name)).join('; ');
    
    const fileBtn = p.file?.has_local_pdf
      ? `<a href="${p.file.download_url}" class="btn-primary text-sm">Download PDF</a>`
      : (p.pdf_url ? `<a href="${p.pdf_url}" target="_blank" class="btn-primary text-sm">View PDF</a>` : '');
      
    $('modal-body').innerHTML = `
      <div class="space-y-6">
        <div class="flex gap-2 flex-wrap">${fileBtn} ${p.doi ? `<a href="https://doi.org/${p.doi}" target="_blank" class="btn-ghost text-xs">View DOI</a>` : ''}</div>
        
        <div class="surface p-5 rounded-xl space-y-3">
          <p class="section-label mb-2">Metadata</p>
          ${metadataRow('Title', p.title)}
          ${metadataRow('Authors', authors)}
          ${metadataRow('Date', p.publication_date?.split('T')[0] || '—')}
          ${metadataRow('DOI', p.doi || '—')}
          ${metadataRow('Source', p.source_repository || '—')}
          ${metadataRow('Citations', cit.citation_count)}
        </div>

        ${p.abstract ? `
          <div class="surface p-5 rounded-xl">
            <p class="section-label mb-2">Abstract</p>
            <p class="text-sm leading-relaxed text-slate-300">${esc(p.abstract)}</p>
          </div>` : ''}
      </div>`;
  }).catch(err => {
    $('modal-body').innerHTML = `<p class="text-sm text-center py-10">Failed to load: ${err.message}</p>`;
  });
}

function metadataRow(l, v) {
  return `<div class="flex text-xs border-b border-white/5 pb-2 last:border-0 last:pb-0">
    <span class="w-24 text-muted flex-shrink-0 font-bold uppercase tracking-wider">${l}</span>
    <span class="text-slate-200">${esc(v)}</span>
  </div>`;
}

function closePaperModal() { $('paper-modal').classList.remove('open'); }

/**
 * Search Functions
 */
function runAdvancedSearch() {
  const q = ($('search-q').value || '').trim();
  const sort = $('search-sort').value || 'relevance';
  const yf = $('search-year-from').value, yt = $('search-year-to').value;
  const oa = $('search-oa-only').checked;
  
  let url = `/api/search/advanced?limit=50&q=${encodeURIComponent(q)}&sort=${sort}`;
  if (yf) url += '&year_from=' + yf;
  if (yt) url += '&year_to=' + yt;
  if (oa) url += '&oa_only=true';
  
  const el = $('search-results'), cnt = $('search-result-count');
  el.innerHTML = '<div class="flex justify-center py-12"><div class="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin"></div></div>';
  
  safeFetch(url, data => {
    const items = data.results || [];
    if (cnt) cnt.textContent = `${data.total || 0} results in ${data.took_ms || 0}ms`;
    
    if (!items.length) {
      el.innerHTML = '<p class="text-sm text-center py-10 text-muted">No results found.</p>';
      return;
    }
    
    el.innerHTML = items.map(i => `
      <div class="surface rounded-xl p-5 row-hover cursor-pointer mb-3" onclick="openPaperModal(${i.id})">
        <div class="flex justify-between items-start gap-4">
          <div class="flex-1">
            <p class="text-base font-bold text-slate-100">${esc(i.title)}</p>
            <p class="text-xs text-muted mt-1">${(i.authors || []).slice(0, 5).join(', ')}</p>
            ${i.abstract ? `<p class="text-xs text-slate-400 mt-2 line-clamp-2 italic">${esc(i.abstract)}</p>` : ''}
          </div>
          <div class="text-right">
            <span class="${i.is_oa ? 'badge-oa' : 'badge-restricted'}">${i.is_oa ? 'OA' : 'RES'}</span>
            <p class="text-xs text-muted mt-2">${i.year || ''}</p>
          </div>
        </div>
      </div>`).join('');
  });
}

function runSearch() { runAdvancedSearch(); }

function loadSearchFaculties() {
  safeFetch('/api/analytics/faculties', facs => {
    const sel = $('search-faculty');
    if (sel && sel.options.length <= 1) facs.forEach(f => {
      const o = document.createElement('option');
      o.value = f; o.textContent = f.replace('Faculty of ', '');
      sel.appendChild(o);
    });
  });
}

/**
 * Dashboard Data Fetchers
 */
function fetchOverview() {
  safeFetch('/api/analytics/overview', d => {
    // Header Stats
    animCount($('stat-total'), d.total_papers);
    animCount($('stat-authors'), d.total_authors);
    animCount($('stat-oa'), d.open_access_papers);
    
    // Impact Cards
    animCount($('ic-total'), d.total_papers);
    animCount($('ic-authors'), d.total_authors);
    animCount($('ic-faculties'), d.total_faculties);
    animCount($('ic-oa'), d.open_access_papers);
    animCount($('ic-oa-rate'), d.oa_percentage, '%');
    animCount($('ic-pdfs'), d.papers_with_local_pdf);
  });
}

function fetchRecentPapers() {
  safeFetch('/api/analytics/recent-papers?limit=5', data => {
    const el = $('recent-papers');
    if (!el) return;
    el.innerHTML = data.map(p => `
      <div class="row-hover p-3 rounded-lg cursor-pointer border-b border-white/5 last:border-0" onclick="openPaperModal(${p.id})">
        <div class="flex justify-between items-start mb-1">
          <p class="text-sm font-semibold text-slate-100 line-clamp-1">${esc(p.title)}</p>
          <span class="${p.is_oa ? 'badge-oa' : 'badge-restricted'} text-[9px] px-1.5 py-0.5 ml-2">${p.is_oa ? 'OA' : 'RES'}</span>
        </div>
        <div class="flex justify-between items-center">
          <p class="text-[10px] text-slate-400 font-medium">${esc((p.authors || []).join(', '))}</p>
          <p class="text-[9px] text-slate-500 font-mono uppercase tracking-wider">${p.doi ? 'DOI Indexed' : 'Local Only'}</p>
        </div>
      </div>
    `).join('') || '<p class="text-xs text-center py-6 text-muted italic">No papers recently harvested.</p>';
  });
}

function loadCrawlerInstitutions() {
  safeFetch('/api/institutions', data => {
    const sel = $('crawler-institution');
    if (!sel) return;
    const current = sel.value;
    sel.innerHTML = '';
    
    // Grouping by region for better UX
    const groups = { 'Nigeria': [], 'Africa': [] };
    data.forEach(inst => {
      const region = ['unilag', 'covenant', 'ui'].includes(inst.short_name.toLowerCase()) ? 'Nigeria' : 'Africa';
      groups[region].push(inst);
    });

    for (const [region, insts] of Object.entries(groups)) {
      const group = document.createElement('optgroup');
      group.label = region === 'Nigeria' ? '🇳🇬 Nigeria' : '🌍 Africa';
      insts.forEach(inst => {
        const opt = document.createElement('option');
        opt.value = inst.short_name.toLowerCase();
        opt.textContent = `${inst.name} (${inst.short_name})`;
        group.appendChild(opt);
      });
      sel.appendChild(group);
    }
    if (current) sel.value = current;
  });
}

/**
 * Initializers
 */
document.addEventListener('DOMContentLoaded', () => {
  // Restore theme
  const savedTheme = localStorage.getItem('uraas-theme') || 'dark';
  document.documentElement.setAttribute('data-theme', savedTheme);
  
  fetchOverview();
  fetchArchive();
  fetchRecentPapers();
  loadCrawlerInstitutions();
  
  // Stats Auto-Refresh
  setInterval(() => {
    const badge = $('crawler-badge');
    if (badge && badge.textContent.includes('Running')) {
      fetchOverview(); fetchRecentPapers();
      if (analyticsLoaded) { invalidateCaches(); loadAnalyticsOverview(); }
    }
  }, 30000);
});

// Keyboard Shortcuts
document.addEventListener('keydown', e => {
  if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) return;
  if (e.key === '1') switchTab('crawler');
  if (e.key === '2') switchTab('archive');
  if (e.key === '3') switchTab('search');
  if (e.key === '4') switchTab('analytics');
  if (e.key === '5') switchTab('comparator');
  if (e.key === 'Escape') { closePaperModal(); }
  if (e.key === 't' || e.key === 'T') toggleTheme();
});

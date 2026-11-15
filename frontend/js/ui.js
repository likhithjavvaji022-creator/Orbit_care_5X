export const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
export const DIV_ORDER = ['radiation', 'earth_distance', 'gravity', 'life_support', 'mental_health'];
export const DIV_NAMES = { radiation: 'Radiation', earth_distance: 'Distance', gravity: 'Gravity', life_support: 'Closed Ecosystem', mental_health: 'Isolation & Stress' };
export const DIV_COLORS = { total: '#22d3ee', radiation: '#f472b6', earth_distance: '#a78bfa', gravity: '#fb923c', life_support: '#34d399', mental_health: '#60a5fa' };
export const src = (s) => `<span class="src ${esc(s)}" title="Data source">${esc(s || 'SIMULATED')}</span>`;
export const pill = (st) => `<span class="pill ${esc(st)}">${esc(st)}</span>`;
export const fmt = (n, d = 1) => (n === null || n === undefined || Number.isNaN(n)) ? '--' : Number(n).toFixed(d);
export const loading = (t = 'Loading...') => `<div class="loading" role="status">${esc(t)}</div>`;
export function errorPanel(root, err, retry) {
  const d = document.createElement('div');
  d.className = 'err'; d.setAttribute('role', 'alert');
  d.innerHTML = `<b>Backend unavailable or request failed.</b><p>${esc(err && err.message ? err.message : err)}</p><button class="primary">Retry</button>`;
  d.querySelector('button').onclick = retry;
  root.replaceChildren(d);
}
export const notConnected = (title, blurb) => `<h1>${esc(title)}</h1><p class="sub">${esc(blurb || '')}</p>
<div class="nc"><b>Not connected yet</b> &mdash; planned in a later milestone. No data is shown here and none is fabricated.</div>`;
export function drawChart(canvas, assessments, existing) {
  if (existing) existing.destroy();
  if (!window.Chart) { canvas.replaceWith(Object.assign(document.createElement('p'), { className: 'muted', textContent: 'Chart library failed to load.' })); return null; }
  const labels = assessments.map((a) => a.mission_day);
  const ds = [{ label: 'Total', data: assessments.map((a) => a.total.score), borderColor: DIV_COLORS.total, borderWidth: 4, tension: .2, pointRadius: 2 }];
  for (const k of DIV_ORDER) ds.push({ label: DIV_NAMES[k], data: assessments.map((a) => a.divisions[k] ? a.divisions[k].score : null), borderColor: DIV_COLORS[k], borderWidth: 1.5, tension: .2, pointRadius: 0, spanGaps: true });
  Chart.defaults.color = '#9db3d6';
  return new Chart(canvas, { type: 'line', data: { labels, datasets: ds }, options: { responsive: true, maintainAspectRatio: false, animation: false,
    scales: { y: { min: 0, max: 100, title: { display: true, text: 'Score (0-100)' }, grid: { color: '#1e3358' } }, x: { title: { display: true, text: 'mission_day' }, grid: { color: '#1e3358' } } },
    plugins: { legend: { labels: { color: '#e8f1ff' } } } } });
}
export function breakdown(a) {
  return `<div class="bars">${DIV_ORDER.map((k) => { const d = a.divisions[k] || {}; const s = d.score;
    return `<div>${esc(DIV_NAMES[k])}</div><div class="bar ${esc(d.status)}" role="img" aria-label="${esc(DIV_NAMES[k])} ${fmt(s)}"><i style="width:${s == null ? 0 : s}%"></i></div><div class="fv">${fmt(s)} ${esc(d.grade || '')} ${pill(d.status || 'NO_DATA')}${src(a.source)}</div>`; }).join('')}</div>`;
}

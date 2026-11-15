import { notConnected, esc } from './ui.js';
import * as mission from './pages/mission-control.js';
import * as hud from './pages/hud.js';
import * as guards from './pages/guards.js';

const SECTIONS = [
  { id: 'mission-control', title: 'Mission Control', page: mission },
  { id: 'space-weather', title: 'Space Weather', dyn: './pages/spaceweather.js' },
  { id: 'radiation-guard', title: 'Radiation Guard', page: guards, opts: { key: 'radiation' } },
  { id: 'crew-health', title: 'Crew Health', page: hud, opts: { mode: 'crew' } },
  { id: 'mental-health-guard', title: 'Mental Health Guard', page: guards, opts: { key: 'mental_health' } },
  { id: 'gravity-guard', title: 'Gravity Health Guard', page: guards, opts: { key: 'gravity' } },
  { id: 'life-support-guard', title: 'Life Support Guard', page: guards, opts: { key: 'life_support' } },
  { id: 'earth-distance-guard', title: 'Earth Distance Guard', page: guards, opts: { key: 'earth_distance' } },
  { id: 'ai-risk', title: 'AI Risk Analysis', dyn: './pages/ai-risk.js' },
  { id: 'flight-surgeon-hud', title: 'Flight Surgeon HUD', page: hud, opts: { mode: 'hud' } },
  { id: 'mission-simulator', title: 'Mission Simulator', dyn: './pages/simulator.js' },
  { id: 'alerts', title: 'Alerts Centre', dyn: './pages/alerts.js' },
  { id: 'reports', title: 'Reports & Analytics', dyn: './pages/reports.js' },
  { id: 'settings', title: 'Settings', dyn: './pages/settings.js' },
];

const view = document.getElementById('view');
const nav = document.getElementById('nav');
const sidebar = document.getElementById('sidebar');
const drawerBtn = document.getElementById('drawerBtn');
let cleanup = null;
let routeToken = 0;

nav.innerHTML = SECTIONS.map((s, i) => `<a href="#/${s.id}" data-id="${s.id}">${i + 1}. ${esc(s.title)}${s.sub ? `<small>${esc(s.sub)}</small>` : ''}</a>`).join('');
drawerBtn.onclick = () => { const o = sidebar.classList.toggle('open'); drawerBtn.setAttribute('aria-expanded', o); };

function route() {
  const id = (location.hash.replace(/^#\/?/, '') || SECTIONS[0].id);
  const sec = SECTIONS.find((s) => s.id === id) || SECTIONS[0];
  if (typeof cleanup === 'function') { try { cleanup(); } catch (_) { /* ignore */ } }
  cleanup = null;
  sidebar.classList.remove('open'); drawerBtn.setAttribute('aria-expanded', 'false');
  nav.querySelectorAll('a').forEach((a) => (a.dataset.id === sec.id ? a.setAttribute('aria-current', 'page') : a.removeAttribute('aria-current')));
  document.title = sec.title + ' - ORBITCARE 5X';
  const token = ++routeToken;
  if (sec.page) {
    cleanup = sec.page.render(view, sec.opts || {}) || null;
    if (cleanup && typeof cleanup.then === 'function') { const p = cleanup; cleanup = null; p.then((c) => { if (token === routeToken) cleanup = c; else if (typeof c === 'function') c(); }).catch(() => {}); }
  } else if (sec.dyn) {
    view.innerHTML = '<p class="loading">Loading...</p>';
    import(sec.dyn).then((m) => { if (token !== routeToken) return; view.innerHTML = ''; return Promise.resolve(m.render(view)).then((c) => { if (token === routeToken) cleanup = c || null; else if (typeof c === 'function') c(); }); })
      .catch((e) => { if (token === routeToken) view.innerHTML = notConnected(sec.title, sec.sub || '') + (e && e.message ? '<p class="muted">' + esc(e.message) + '</p>' : ''); });
  } else {
    view.innerHTML = notConnected(sec.title, sec.sub || '');
  }
  window.scrollTo(0, 0);
}
window.addEventListener('hashchange', route);
route();



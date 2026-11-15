import { get } from '../api.js';
import { esc, loading, errorPanel } from '../ui.js';

const SEV = ['critical', 'warning', 'info'];

export async function render(el) {
  let filter = 'all';
  async function load() {
    el.innerHTML = `<h1>Alerts Centre</h1>${loading('Loading alerts...')}`;
    try {
      const [al, sw] = await Promise.all([get('/api/alerts'), get('/api/spaceweather').catch((e) => ({ status: 'FAILED', error: e.message }))]);
      draw(al.items || [], sw);
    } catch (e) { errorPanel(el, e, load); }
  }
  function draw(items, sw) {
    const seen = new Set();
    const uniq = items.filter((a) => { const k = [a.astronaut_id, a.code, a.day].join('|'); if (seen.has(k)) return false; seen.add(k); return true; });
    const shown = uniq.filter((a) => filter === 'all' || a.severity === filter);
    const p = sw && sw.data && sw.data.proton_flux;
    let h = `<h1>Alerts Centre</h1><p class="sub">De-duplicated rule alerts. Screening aids, not diagnoses.</p>`;
    if (p && p.sep_active) h += `<div class="err" role="alert"><b>SHELTER BANNER: NOAA S1 threshold reached</b> (proton flux ${esc(p.value)} pfu, &ge;10 pfu at &ge;10 MeV). Follow mission shelter procedures.</div>`;
    else if (sw && sw.status === 'FAILED') h += `<div class="warn">Space-weather status unavailable (${esc(sw.error)}); shelter banner cannot be evaluated.</div>`;
    h += `<div class="row panel">${['all', ...SEV].map((s) => `<button data-f="${s}" class="${filter === s ? 'primary' : ''}">${s}${s === 'all' ? ' (' + uniq.length + ')' : ' (' + uniq.filter((a) => a.severity === s).length + ')'}</button>`).join('')}</div>`;
    h += shown.length ? `<div class="panel"><table><thead><tr><th>Severity</th><th>Astronaut</th><th>Day</th><th>Code</th><th>Message</th><th>Created</th></tr></thead><tbody>${shown.map((a) => `<tr><td><span class="pill ${a.severity === 'critical' ? 'RED' : a.severity === 'warning' ? 'YELLOW' : 'GREEN'}">${esc(a.severity)}</span></td><td>${esc(a.astronaut_id)}</td><td>${esc(a.day)}</td><td>${esc(a.code)}</td><td>${esc(a.message)}</td><td>${esc(a.created_at)}</td></tr>`).join('')}</tbody></table></div>`
      : `<div class="empty"><b>No alerts${filter === 'all' ? '' : ' at severity ' + esc(filter)}.</b></div>`;
    el.innerHTML = h;
    el.querySelectorAll('[data-f]').forEach((b) => { b.onclick = () => { filter = b.dataset.f; draw(items, sw); }; });
  }
  await load();
}

import { get, api, postFile } from '../api.js';
import { esc, loading, errorPanel } from '../ui.js';

const W_KEYS = ['radiation', 'life_support', 'mental_health', 'gravity', 'earth_distance'];

export async function render(el) {
  async function load() {
    el.innerHTML = `<h1>Settings</h1>${loading()}`;
    try { draw(await get('/api/settings')); } catch (e) { errorPanel(el, e, load); }
  }
  function draw(s) {
    const m = s.mission;
    el.innerHTML = `<h1>Settings</h1><p class="sub">Changes apply to assessments computed after saving; existing assessments are not recalculated.</p><div id="msg" role="status"></div>
<form class="panel" id="wf"><h2>Grading weights</h2><div class="row">${W_KEYS.map((k) => `<label>${esc(k)} <input type="number" step="0.01" min="0" max="1" name="${k}" value="${s.weights[k]}" style="width:80px"></label>`).join('')}</div><p>Sum: <b id="wsum"></b> (must be 1.00)</p><button class="primary" type="submit">Save weights</button></form>
<form class="panel" id="mf"><h2>Mission</h2><div class="row"><label>Name <input name="name" value="${esc(m.name)}"></label><label>Start (ISO UTC) <input name="start" value="${esc(m.start)}"></label><label>Planned days <input type="number" min="1" name="planned_days" value="${esc(m.planned_days)}" style="width:80px"></label></div><button class="primary" type="submit">Save mission</button></form>
<form class="panel" id="tf"><h2>Thresholds</h2><details><summary>Show all grading thresholds</summary>${Object.entries(s.thresholds).map(([g, d]) => `<fieldset style="border:1px solid var(--line);border-radius:8px;margin:8px 0"><legend>${esc(g)}</legend><div class="row">${Object.entries(d).map(([k, v]) => `<label>${esc(k)} <input type="number" step="any" data-g="${esc(g)}" data-k="${esc(k)}" value="${v}" style="width:90px"></label>`).join('')}</div></fieldset>`).join('')}</details><button class="primary" type="submit">Save thresholds</button></form>
<div class="panel"><h2>Backup &amp; restore</h2><div class="row"><a class="btn" href="/api/backup" download>Download backup JSON</a><label>Restore from backup <input type="file" id="rf" accept=".json,application/json"></label></div></div>
<div class="panel"><h2>Reset demo data</h2><p class="muted">Deletes all telemetry, assessments, alerts and crew. Settings are kept.</p><button id="reset" style="border-color:var(--red)">Reset demo data</button></div>`;
    const msg = (t, bad) => { el.querySelector('#msg').innerHTML = `<div class="${bad ? 'err' : 'warn'}" ${bad ? 'role="alert"' : ''}>${esc(t)}</div>`; };
    const put = async (body, label) => { try { await api('/api/settings', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }); msg(label + ' saved.'); } catch (e) { msg(e.message, true); } };
    const wf = el.querySelector('#wf');
    const sum = () => { const t = W_KEYS.reduce((a, k) => a + Number(wf[k].value || 0), 0); el.querySelector('#wsum').textContent = t.toFixed(2); };
    wf.oninput = sum; sum();
    wf.onsubmit = (e) => { e.preventDefault(); const w = {}; W_KEYS.forEach((k) => { w[k] = Number(wf[k].value); }); put({ weights: w }, 'Weights'); };
    const mf = el.querySelector('#mf');
    mf.onsubmit = (e) => { e.preventDefault(); put({ mission: { name: mf.name.value, start: mf.start.value, planned_days: Number(mf.planned_days.value) } }, 'Mission'); };
    el.querySelector('#tf').onsubmit = (e) => { e.preventDefault(); const t = {}; el.querySelectorAll('[data-g]').forEach((i) => { (t[i.dataset.g] ||= {})[i.dataset.k] = Number(i.value); }); put({ thresholds: t }, 'Thresholds'); };
    el.querySelector('#rf').onchange = async (e) => {
      const f = e.target.files[0]; if (!f) return;
      if (!window.confirm('Restore will REPLACE all current data with the backup. Continue?')) { e.target.value = ''; return; }
      try { const body = JSON.parse(await f.text()); const r = await api('/api/restore', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }); msg('Restored: ' + JSON.stringify(r.counts)); load(); } catch (err) { msg('Restore failed: ' + err.message, true); }
    };
    el.querySelector('#reset').onclick = async () => {
      if (!window.confirm('Delete ALL demo telemetry, assessments and alerts? This cannot be undone.')) return;
      try { const r = await api('/api/telemetry', { method: 'DELETE' }); msg('Demo data reset: ' + JSON.stringify(r.deleted)); } catch (err) { msg(err.message, true); }
    };
  }
  await load();
}

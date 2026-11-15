import { get } from '../api.js';
import { esc, fmt, pill, loading, errorPanel, DIV_ORDER, DIV_NAMES, breakdown } from '../ui.js';

const PRINT_CSS = `@media print{.sidebar,.mobilebar,.noprint,#footer{display:none!important}body,.shell,.main,.panel{background:#fff!important;color:#000!important}.shell{display:block!important}.main{margin:0!important;padding:0!important}.panel{border:1px solid #999!important}table{color:#000!important}.pill,.src{border:1px solid #000;color:#000!important;background:#fff!important}.printonly{display:block!important}}.printonly{display:none}`;

export async function render(el) {
  if (!document.getElementById('rep-print')) { const s = document.createElement('style'); s.id = 'rep-print'; s.textContent = PRINT_CSS; document.head.appendChild(s); }
  async function load() {
    el.innerHTML = `<h1>Reports &amp; Analytics</h1>${loading()}`;
    try {
      const [latest, crew] = await Promise.all([get('/api/assessments/latest'), get('/api/crew')]);
      draw(latest.items || [], crew.items || []);
    } catch (e) { errorPanel(el, e, load); }
  }
  function draw(items, crew) {
    const names = Object.fromEntries(crew.map((c) => [c.astronaut_id, c.name]));
    let h = `<h1>Reports &amp; Analytics</h1><p class="sub">Exports of stored assessments. Screening aids only.</p>
<div class="panel noprint row"><label>Astronaut <select id="aid"><option value="">All</option>${items.map((a) => `<option>${esc(a.astronaut_id)}</option>`).join('')}</select></label>
<a class="btn primary" id="csv" href="/api/reports/assessments.csv" download>Download assessments CSV</a>
<button id="pdf" class="primary">Print / Save as PDF</button></div>
<div class="printonly"><h2>ORBITCARE 5X Crew Health Report</h2><p>Generated ${esc(new Date().toISOString())}</p></div>`;
    if (!items.length) h += `<div class="empty"><b>No assessments yet.</b><p>Upload telemetry on Mission Control or ingest data first; nothing is fabricated.</p></div>`;
    for (const a of items) {
      const t = a.total;
      h += `<div class="panel"><h2>${esc(names[a.astronaut_id] || a.astronaut_id)} <small class="muted">${esc(a.astronaut_id)} | day ${esc(a.mission_day)}</small></h2>
<p><b>Total ${fmt(t.score)} ${esc(t.grade || '')}</b> ${pill(t.status)} | Change vs Day 1 ${fmt(t.delta_from_day1)}${t.capped ? ' | <b>Bottleneck cap applied</b>' : ''}${t.penalty ? ' | Compound penalty ' + esc(t.penalty) : ''}</p>${breakdown(a)}
<table><thead><tr><th>Division</th><th>Deductions</th></tr></thead><tbody>${DIV_ORDER.map((k) => `<tr><td>${esc(DIV_NAMES[k])}</td><td>${(a.divisions[k].factors || []).map((f) => esc(f.label) + ' (-' + fmt(f.deduction) + ')').join('; ') || '--'}</td></tr>`).join('')}</tbody></table></div>`;
    }
    h += `<div class="panel"><b>Not a medical device.</b> ORBITCARE 5X is not a medical device or diagnostic system. This report contains an illustrative screening metric, not a medical diagnosis, and does not replace clinical judgement by a flight surgeon. Demo data is SIMULATED.</div>`;
    el.innerHTML = h;
    const sel = el.querySelector('#aid'), csv = el.querySelector('#csv');
    if (sel) sel.onchange = () => { csv.href = '/api/reports/assessments.csv' + (sel.value ? '?astronaut_id=' + encodeURIComponent(sel.value) : ''); };
    el.querySelector('#pdf').onclick = () => window.print();
  }
  await load();
}

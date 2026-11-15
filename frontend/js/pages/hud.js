import { get } from '../api.js';
import { esc, DIV_ORDER, DIV_NAMES, src, pill, fmt, loading, errorPanel, drawChart, breakdown } from '../ui.js';

export function render(root, opts = {}) {
  const hudMode = opts.mode === 'hud';
  const title = hudMode ? 'Flight Surgeon HUD' : 'Crew Health &amp; Mental Health Guard';
  let chart = null, dead = false, astro = null;

  async function load() {
    root.innerHTML = `<h1>${title}</h1>${loading('Loading crew assessments...')}`;
    try {
      const latest = (await get('/api/assessments/latest')).items || [];
      if (dead) return;
      if (!latest.length) { root.innerHTML = `<h1>${title}</h1><div class="empty"><b>No assessments yet.</b><br>Upload telemetry on Mission Control first.</div>`; return; }
      if (!astro || !latest.some((l) => l.astronaut_id === astro)) astro = latest[0].astronaut_id;
      const traj = (await get('/api/assessments?astronaut_id=' + encodeURIComponent(astro))).items || [];
      if (dead) return;
      draw(latest, traj.length ? traj : [latest.find((l) => l.astronaut_id === astro)]);
    } catch (e) { if (!dead) errorPanel(root, e, load); }
  }

  function draw(latest, traj) {
    const a = traj[traj.length - 1], t = a.total, dl = t.delta_from_day1;
    let h = `<div class="${hudMode ? 'hud' : ''}"><h1>${title}</h1><p class="sub">Readiness &amp; Condition Index &mdash; Illustrative screening metric, not a medical diagnosis. Defer to the flight surgeon and mission procedures.</p>
      <div class="row panel"><label>Astronaut <select id="astro">${latest.map((l) => `<option ${l.astronaut_id === astro ? 'selected' : ''}>${esc(l.astronaut_id)}</option>`).join('')}</select></label>
      <span>Day ${a.mission_day} &middot; scenario ${esc(a.scenario_label)}</span>${src(a.source)}<span class="muted">${esc(a.timestamp)}</span></div>
      <div class="panel"><div class="total"><div class="badge st-${esc(t.status)}"><div class="big">${fmt(t.score)}</div><div class="lt">Grade ${esc(t.grade)}</div>${pill(t.status)}</div>
      <div><div>Total Mission Grade ${src(a.source)}</div><div>Delta from Day 1: <b class="delta ${dl < 0 ? 'neg' : 'pos'}">${dl > 0 ? '+' : ''}${fmt(dl)}</b></div>
      ${t.capped ? '<span class="flag bad">Capped by bottleneck</span>' : ''}${t.penalty < 0 ? `<span class="flag warn">${fmt(t.penalty, 0)} compounding</span>` : ''}</div></div></div>
      <div class="panel"><h2>5-Division Breakdown</h2>${breakdown(a)}</div>
      <div class="panel"><h2>Contributing factors</h2><div class="grid g2">${DIV_ORDER.map((k) => { const d = a.divisions[k] || {}; const f = d.factors || [];
        return `<div><b>${esc(DIV_NAMES[k])}</b> ${pill(d.status || 'NO_DATA')}${f.length ? `<ul class="clean">${f.map((x) => `<li>${esc(x.label)}: ${esc(x.value)} <span class="delta neg">${fmt(x.deduction, 1)}</span></li>`).join('')}</ul>` : '<div class="muted">No deductions.</div>'}</div>`; }).join('')}</div></div>
      <div class="panel"><h2>Interaction watch (hypotheses)</h2>${(a.interaction_flags || []).length ? a.interaction_flags.map((f) => `<div><span class="flag warn">${esc(f.pair.map((p) => DIV_NAMES[p] || p).join(' + '))}</span> <span class="muted">${esc(f.label)}</span></div>`).join('') : '<span class="muted">No interaction flags. (Hypotheses from HRP hazard descriptions, not validated coefficients.)</span>'}</div>
      <div class="panel"><h2>Grade Trajectory Overlay</h2><div class="chartbox"><canvas id="ch" role="img" aria-label="Grade trajectory"></canvas></div></div></div>`;
    root.innerHTML = h;
    root.querySelector('#astro').onchange = (e) => { astro = e.target.value; load(); };
    chart = drawChart(root.querySelector('#ch'), traj, chart);
  }

  load();
  return () => { dead = true; if (chart) chart.destroy(); };
}

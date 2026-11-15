import { get, postJson, postFile } from '../api.js';
import { esc, DIV_ORDER, DIV_NAMES, src, pill, fmt, loading, errorPanel, drawChart } from '../ui.js';

const PLANNED_DAYS = 32; // illustrative default planned duration (ESTIMATE)

export function render(root) {
  let timer = null, chart = null, dead = false;
  let astro = null, report = null, streamMsg = '';
  const stop = () => { if (timer) { clearInterval(timer); timer = null; } };

  async function load() {
    root.innerHTML = `<h1>Mission Control</h1>${loading('Loading mission data from API...')}`;
    try {
      const crew = (await get('/api/crew')).items || [];
      const latest = (await get('/api/assessments/latest')).items || [];
      if (dead) return;
      if (!astro || !crew.concat(latest).some((c) => c.astronaut_id === astro)) astro = (latest[0] || crew[0] || {}).astronaut_id || null;
      const traj = astro ? (await get('/api/assessments?astronaut_id=' + encodeURIComponent(astro))).items || [] : [];
      if (dead) return;
      draw(crew, latest, traj);
    } catch (e) { if (!dead) errorPanel(root, e, load); }
  }

  function draw(crew, latest, traj) {
    const cur = traj.length ? traj[traj.length - 1] : (latest.find((l) => l.astronaut_id === astro) || null);
    const ids = [...new Set(crew.map((c) => c.astronaut_id).concat(latest.map((l) => l.astronaut_id)))];
    const day = cur ? cur.mission_day : 0;
    let h = `<h1>Mission Control</h1><p class="sub">Readiness &amp; Condition Index &mdash; Illustrative screening metric, not a medical diagnosis.</p>`;
    h += `<div class="panel"><div class="row"><div><b>Mission day ${day || '--'} of ${PLANNED_DAYS}</b>${src(cur ? cur.source : 'ESTIMATE')} <span class="muted">(planned duration ${PLANNED_DAYS} d: illustrative default${cur ? '; MET from latest telemetry' : ''})</span></div><span class="spacer"></span>
      <label>Astronaut <select id="astro">${ids.length ? ids.map((i) => `<option ${i === astro ? 'selected' : ''}>${esc(i)}</option>`).join('') : '<option>none</option>'}</select></label></div>
      <div class="bar" style="margin-top:10px" aria-label="Mission progress"><i style="width:${Math.min(100, day / PLANNED_DAYS * 100)}%;background:var(--cyan)"></i></div></div>`;
    h += `<div class="panel"><h2>Workflow A upload</h2><div class="row"><input type="file" id="file" accept=".csv,.json" aria-label="Telemetry file"><button class="primary" id="up">Upload &amp; run 7-stage pipeline</button>
      <button id="stream" aria-pressed="${!!timer}">Live Simulation Stream: ${timer ? 'ON' : 'OFF'}</button><button id="reset" title="DELETE /api/telemetry">Reset demo data</button></div>
      <p class="muted" id="smsg" role="status">${esc(streamMsg)}</p><div id="report">${reportHtml()}</div></div>`;
    if (!cur) {
      h += `<div class="empty"><b>No telemetry yet.</b><br>Upload data/sample/workflow_a_31_scenarios.csv or start the Live Simulation Stream.</div>`;
    } else {
      const t = cur.total, dl = t.delta_from_day1;
      h += `<div class="panel"><h2>Total Mission Grade</h2><div class="total"><div class="badge st-${esc(t.status)}"><div class="big">${fmt(t.score)}</div><div class="lt">Grade ${esc(t.grade)}</div>${pill(t.status)}</div>
        <div><div>Delta from Day 1: <b class="delta ${dl < 0 ? 'neg' : 'pos'}">${dl > 0 ? '+' : ''}${fmt(dl)}</b>${src(cur.source)}</div>
        <div>Weighted: ${fmt(t.weighted)}${src(cur.source)}</div>
        <div>${t.capped ? '<span class="flag bad">Capped by bottleneck (a division &lt; 35: total cannot exceed D)</span>' : ''}${t.penalty < 0 ? `<span class="flag warn">${fmt(t.penalty, 0)} compounding (3+ divisions YELLOW/RED)</span>` : ''}${!t.capped && t.penalty >= 0 ? '<span class="muted">No cap or compounding penalty applied.</span>' : ''}</div></div></div>`;
      h += `<div class="panel"><h2>Five Hazards</h2><div class="grid g5">${DIV_ORDER.map((k) => { const d = cur.divisions[k] || {};
        return `<div class="tile st-${esc(d.status)}"><div class="name">${esc(DIV_NAMES[k])}</div><div><span class="score">${fmt(d.score)}</span><span class="letter">${esc(d.grade || '')}</span></div>${pill(d.status || 'NO_DATA')}${src(cur.source)}</div>`; }).join('')}</div></div>`;
      if ((cur.interaction_flags || []).length) h += `<div class="panel"><h2>Interaction watch</h2>${cur.interaction_flags.map((f) => `<span class="flag warn">${esc(f.pair.map((p) => DIV_NAMES[p] || p).join(' + '))}</span>`).join('')}<p class="muted">${esc(cur.interaction_flags[0].label || 'Hypothesis from HRP hazard descriptions')}</p></div>`;
    }
    h += `<div class="panel"><h2>Grade Trajectory Overlay</h2>${traj.length ? `<div class="chartbox"><canvas id="ch" role="img" aria-label="Grade trajectory"></canvas></div>` : '<div class="empty">No trajectory yet.</div>'}</div>`;
    h += `<div class="panel"><h2>Crew</h2>${latest.length ? `<table><tr><th>Astronaut</th><th>Day</th><th>Total</th><th>Grade</th><th>Source</th></tr>${latest.map((l) => `<tr><td>${esc(l.astronaut_id)}</td><td>${l.mission_day}</td><td>${fmt(l.total.score)}</td><td>${esc(l.total.grade)}</td><td>${src(l.source)}</td></tr>`).join('')}</table>` : '<span class="muted">No crew assessments yet.</span>'}</div>`;
    root.innerHTML = h;
    if (traj.length) chart = drawChart(root.querySelector('#ch'), traj, chart);
    wire(cur);
  }

  function reportHtml() {
    if (!report) return '';
    const r = report;
    return `<p><b>Received ${r.received}</b> &middot; accepted <b>${r.accepted}</b> &middot; rejected <b>${(r.rejected || []).length}</b> &middot; suspect <b>${(r.suspect || []).length}</b> ${src('USER-ENTERED')}</p>
      ${(r.rejected || []).length ? `<details><summary>Rejected rows</summary><ul class="clean">${r.rejected.map((x) => `<li>row ${x.row}: ${esc(x.reason)}</li>`).join('')}</ul></details>` : ''}
      ${(r.suspect || []).length ? `<details><summary>Suspect values</summary><ul class="clean">${r.suspect.map((x) => `<li>row ${x.row} ${esc(x.metric)}: ${esc(x.reason)}</li>`).join('')}</ul></details>` : ''}
      <table><tr><th>#</th><th>Stage</th><th>In</th><th>Out</th><th>Rejected</th><th>Last run</th><th>Notes</th></tr>${(r.pipeline || []).map((s) => `<tr><td>${s.stage}</td><td>${esc(s.name)}</td><td>${s.records_in}</td><td>${s.records_out}</td><td>${s.rejected}</td><td>${esc(s.last_run)}</td><td>${esc(s.notes)}</td></tr>`).join('')}</table>`;
  }

  function wire(cur) {
    const q = (s) => root.querySelector(s);
    q('#astro').onchange = (e) => { astro = e.target.value; load(); };
    q('#up').onclick = async () => {
      const f = q('#file').files[0];
      if (!f) { q('#smsg').textContent = 'Choose a .csv or .json file first.'; return; }
      q('#up').disabled = true; q('#smsg').textContent = 'Uploading...';
      try { report = await postFile('/api/telemetry/upload', f); streamMsg = 'Upload complete.'; await load(); }
      catch (e) { q('#up').disabled = false; q('#smsg').textContent = 'Upload failed: ' + e.message; }
    };
    q('#reset').onclick = async () => {
      if (!confirm('Delete all demo telemetry?')) return;
      try { await api_delete(); report = null; streamMsg = 'Demo data reset.'; await load(); } catch (e) { q('#smsg').textContent = 'Reset failed: ' + e.message; }
    };
    q('#stream').onclick = () => {
      if (timer) { stop(); streamMsg = 'Stream stopped.'; } else { timer = setInterval(tick, 4000); streamMsg = 'Stream running (every 4 s)...'; tick(); }
      const b = q('#stream'); b.setAttribute('aria-pressed', !!timer); b.textContent = 'Live Simulation Stream: ' + (timer ? 'ON' : 'OFF'); q('#smsg').textContent = streamMsg;
    };
  }

  let busy = false;
  async function tick() {
    if (busy || dead) return; busy = true;
    try {
      const id = astro || 'SIM-A1';
      const hist = (await get('/api/assessments?astronaut_id=' + encodeURIComponent(id))).items || [];
      const day = (hist.length ? hist[hist.length - 1].mission_day : 0) + 1;
      const row = await get(`/api/telemetry/simulate?astronaut_id=${encodeURIComponent(id)}&day=${day}&scenario_id=${(day - 1) % 32}`);
      report = await postJson('/api/telemetry/ingest', { rows: [row] });
      streamMsg = `Streamed day ${day} (SIMULATED).`;
      if (!dead) await load();
    } catch (e) { stop(); streamMsg = 'Stream stopped: ' + e.message; if (!dead) await load(); }
    finally { busy = false; }
  }
  async function api_delete() { const { api } = await import('../api.js'); return api('/api/telemetry', { method: 'DELETE' }); }

  load();
  return () => { dead = true; stop(); if (chart) chart.destroy(); };
}

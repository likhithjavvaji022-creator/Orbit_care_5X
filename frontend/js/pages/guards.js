import { get } from '../api.js';
import { esc, src, pill, fmt, loading, errorPanel } from '../ui.js';

const TABS = [
  ['radiation', 'radiation-guard', 'Radiation'], ['mental_health', 'mental-health-guard', 'Mental Health'],
  ['gravity', 'gravity-guard', 'Gravity Health'], ['life_support', 'life-support-guard', 'Life Support'],
  ['earth_distance', 'earth-distance-guard', 'Earth Distance'],
];
const NOTE = 'Readiness & Condition Index - illustrative screening metric, not a medical diagnosis. Defer to the flight surgeon and mission procedures.';
const NOEXPOSE = 'Not exposed by the API (no deduction, or metric is not graded); no value is invented.';

// Each guard: metrics = [{label, codes:[factor codes], unit, note}], series = [{label, codes}] for trend (right axis).
const CFG = {
  radiation: { title: 'Radiation Guard', blurb: 'Cumulative dose against the 600 mSv career limit (illustrative).',
    metrics: [
      { label: 'Cumulative dose', codes: ['CUM_DOSE'], f: 'cum_dose_msv', unit: 'mSv', empty: 'No dose deduction recorded (dose 0 or missing).' },
      { label: 'Proton flux', codes: ['PROTON_FLUX'], f: 'proton_flux_pfu', unit: 'pfu', empty: 'Below the 10 pfu threshold (or not reported); value not exposed.' },
      { label: 'Solar flare', codes: ['FLARE_ACTIVE'], f: 'flare_active', unit: '', empty: 'No active flare flagged.', bool: true }],
    series: [{ label: 'Cumulative dose (mSv)', codes: [], f: 'cum_dose_msv' }, { label: 'Proton flux (pfu)', codes: [], f: 'proton_flux_pfu' }],
    foot: 'Dose is from dose records, never converted from NOAA flux.' },
  mental_health: { title: 'Mental Health Guard', blurb: 'Sleep, HRV vs baseline, fatigue and stress.',
    metrics: [
      { label: 'Sleep', codes: ['SLEEP_SEVERE', 'SLEEP_LOW'], f: 'sleep_h', unit: 'h', empty: 'Sleep at or above 6 h (value not exposed).' },
      { label: 'HRV drop vs baseline', codes: ['HRV_DROP'], f: 'hrv_rmssd_ms', f2: 'hrv_baseline_ms', unit: 'ms', empty: 'No HRV drop below baseline (raw HRV and baseline not exposed).' },
      { label: 'Fatigue (0-10)', codes: ['FATIGUE'], f: 'fatigue', unit: '', empty: 'At or below 5 (value not exposed).' },
      { label: 'Stress (0-10)', codes: ['STRESS'], f: 'stress', unit: '', empty: 'At or below 5 (value not exposed).' }],
    series: [{ label: 'Sleep (h)', codes: [], f: 'sleep_h' }, { label: 'HRV RMSSD (ms)', codes: [], f: 'hrv_rmssd_ms' }, { label: 'HRV baseline (ms)', codes: [], f: 'hrv_baseline_ms' },
      { label: 'Fatigue', codes: [], f: 'fatigue' }, { label: 'Stress', codes: [], f: 'stress' }],
    foot: 'HRV baseline is a personal baseline; the API exposes only the % drop when it deducts.' },
  gravity: { title: 'Gravity Health Guard', blurb: 'Exercise-loading index against target, and vestibular balance score.',
    metrics: [
      { label: 'Exercise-loading index / target (ratio, deducts below 0.80)', codes: ['LOADING_LOW'], f: 'loading_index', f2: 'loading_target', unit: '', empty: 'Loading at or above 80% of target (ratio not exposed).' },
      { label: 'Balance score (0-100, deducts below 85)', codes: ['BALANCE_LOW'], f: 'balance_score', unit: '', empty: 'Balance at or above 85 (value not exposed).' }],
    series: [{ label: 'Loading index', codes: [], f: 'loading_index' }, { label: 'Loading target', codes: [], f: 'loading_target' }, { label: 'Balance score', codes: [], f: 'balance_score' }],
    foot: 'Tracks exercise loading as a countermeasure indicator only; this is not a bone-health measurement.' },
  life_support: { title: 'Life Support Guard', blurb: 'Cabin O2, CO2 (5000 ppm line), pressure, scrubber state.',
    metrics: [
      { label: 'CO2 (limit 5000 ppm)', codes: ['CO2_HIGH'], f: 'cabin_co2_ppm', unit: 'ppm', empty: 'At or below 5000 ppm (value not exposed).' },
      { label: 'O2 (19.5-23.5 %)', codes: ['O2_OUT_OF_RANGE'], f: 'cabin_o2_pct', unit: '%', empty: 'Within range (value not exposed).' },
      { label: 'Pressure (97-103 kPa)', codes: ['PRESSURE_OUT_OF_RANGE'], f: 'cabin_pressure_kpa', unit: 'kPa', empty: 'Within range (value not exposed).' },
      { label: 'Scrubber state', codes: ['SCRUBBER_DEGRADED', 'SCRUBBER_OFFLINE'], f: 'scrubber_state', unit: '', empty: 'Nominal (or not reported).' },
      { label: 'Temperature', codes: [], f: 'cabin_temp_c', unit: 'C', empty: NOEXPOSE + ' Not part of the score.' },
      { label: 'Humidity', codes: [], f: 'cabin_humidity_pct', unit: '%', empty: NOEXPOSE + ' Not part of the score.' }],
    series: [{ label: 'CO2 (ppm)', codes: [], f: 'cabin_co2_ppm', limit: 5000 }, { label: 'O2 (%)', codes: [], f: 'cabin_o2_pct' }, { label: 'Pressure (kPa)', codes: [], f: 'cabin_pressure_kpa' }, { label: 'Temp (C)', codes: [], f: 'cabin_temp_c' }, { label: 'Humidity (%)', codes: [], f: 'cabin_humidity_pct' }],
    foot: 'Raw values come from stored telemetry; temperature and humidity are informational and not part of the score.' },
  earth_distance: { title: 'Earth Distance Guard', blurb: 'Communication latency tier and open medical flags.',
    metrics: [
      { label: 'Latency (s)', codes: ['LATENCY_TIER2', 'LATENCY_TIER3'], f: 'latency_s', unit: 's', empty: 'Tier 1, or no other division degraded (latency only appears when it deducts).' },
      { label: 'Open medical flags', codes: ['OPEN_MEDICAL_FLAGS'], f: 'open_medical_flags', unit: '', empty: 'None open (or not reported).' }],
    series: [{ label: 'Latency (s)', codes: [], f: 'latency_s' }, { label: 'Open flags', codes: [], f: 'open_medical_flags' }],
    foot: 'Tier 1 < 2 s, tier 2 2-60 s, tier 3 > 60 s.' },
};
const COLORS = ['#f472b6', '#facc15', '#60a5fa', '#34d399', '#fb923c', '#a78bfa'];

const factorOf = (div, codes) => ((div && div.factors) || []).find((f) => codes.includes(f.code));
const valueOf = (div, codes) => { const f = factorOf(div, codes); return f ? f.value : null; };

const STALE_MS = 48 * 3600 * 1000;
// latest non-null raw value for a field, flagged stale if its row is >48 h older than the newest row
function rawLatest(raw, f) {
  if (!raw.length || !f) return null;
  const newest = Date.parse(raw[raw.length - 1].timestamp);
  for (let i = raw.length - 1; i >= 0; i--) {
    const v = raw[i][f];
    if (v != null && v !== '') return { v, row: raw[i], stale: newest - Date.parse(raw[i].timestamp) > STALE_MS };
  }
  return null;
}

function tabs(key) {
  return `<nav class="gtabs" aria-label="Guards">${TABS.map(([k, id, t]) => `<a href="#/${id}" ${k === key ? 'aria-current="page"' : ''}>${esc(t)}</a>`).join('')}</nav>`;
}

function csvDose(traj) {
  const rows = ['mission_day,timestamp,cum_dose_msv,source'];
  for (const a of traj) { const v = valueOf(a.divisions.radiation, ['CUM_DOSE']); rows.push([a.mission_day, a.timestamp, v == null ? '' : v, a.source].join(',')); }
  return rows.join('\n');
}

function triage(a) {
  const ed = a.divisions.earth_distance || {};
  const lat = valueOf(ed, ['LATENCY_TIER2', 'LATENCY_TIER3']);
  const tier = ed.factors && ed.factors.some((f) => f.code === 'LATENCY_TIER3') ? 3 : ed.factors && ed.factors.some((f) => f.code === 'LATENCY_TIER2') ? 2 : null;
  const open = valueOf(ed, ['OPEN_MEDICAL_FLAGS']) || 0;
  const bad = Object.values(a.divisions).filter((d) => d.key !== 'earth_distance' && (d.status === 'YELLOW' || d.status === 'RED'));
  const steps = [];
  if (bad.some((d) => d.status === 'RED')) steps.push('At least one division is RED: treat as urgent. Alert the crew medical officer and attempt contact with the flight surgeon now.');
  else if (bad.length) steps.push('Degraded division(s): ' + bad.map((d) => d.name).join(', ') + '. Review the guard tab for each and log observations.');
  else steps.push('No other division is degraded. Continue routine monitoring.');
  if (tier === 3) steps.push('Tier 3 delay (>60 s): real-time consultation is not possible. Send a structured written report and follow the pre-agreed mission procedures while awaiting reply.');
  else if (tier === 2) steps.push('Tier 2 delay (2-60 s): conversation is possible but delayed. Send a concise report and wait for acknowledgement between messages.');
  else steps.push('Latency tier is tier 1 or not flagged: normal two-way contact expected.');
  if (open > 0) steps.push(open + ' open medical flag(s): review and report each to the flight surgeon.');
  steps.push('Record symptoms, time of onset and measurements, and keep the log ready to transmit.');
  steps.push('Follow the onboard medical checklists. This tool gives no medication or dosage guidance. All treatment decisions belong to the flight surgeon.');
  return { steps, tier, lat };
}

export async function renderGuard(root, key) {
  const cfg = CFG[key];
  let chart = null, dead = false, astro = null, raw = [];
  async function load() {
    root.innerHTML = `<h1>${esc(cfg.title)}</h1>${tabs(key)}${loading('Loading assessments...')}`;
    try {
      const latest = (await get('/api/assessments/latest')).items || [];
      if (dead) return;
      if (!latest.length) { root.innerHTML = `<h1>${esc(cfg.title)}</h1>${tabs(key)}<div class="empty"><b>No assessments yet.</b><br>Upload telemetry on Mission Control first.</div>`; return; }
      if (!astro || !latest.some((l) => l.astronaut_id === astro)) astro = latest[0].astronaut_id;
      const traj = (await get('/api/assessments?astronaut_id=' + encodeURIComponent(astro))).items || [];
      if (dead) return;
      try { raw = (await get('/api/telemetry?astronaut_id=' + encodeURIComponent(astro))).items || []; } catch (e) { raw = []; }
      if (dead) return;
      draw(latest, traj.length ? traj : [latest.find((l) => l.astronaut_id === astro)]);
    } catch (e) { if (!dead) errorPanel(root, e, load); }
  }
  function draw(latest, traj) {
    const a = traj[traj.length - 1], d = a.divisions[key];
    if (!d) { root.innerHTML = `<h1>${esc(cfg.title)}</h1>${tabs(key)}<div class="empty">This division is missing from the assessment.</div>`; return; }
    const noData = d.status === 'NO_DATA';
    const rows = cfg.metrics.map((m) => {
      const f = factorOf(d, m.codes);
      const rl = rawLatest(raw, m.f), rl2 = m.f2 ? rawLatest(raw, m.f2) : null;
      let val;
      if (rl) {
        const shown = m.bool ? (rl.v ? 'Active' : 'Inactive') : esc(typeof rl.v === 'number' ? fmt(rl.v, 2) : rl.v) + (m.unit ? ' ' + esc(m.unit) : '') + (rl2 ? ' (baseline ' + esc(fmt(rl2.v, 1)) + ')' : '');
        val = '<b>' + shown + '</b> ' + src(rl.row.source) + (rl.stale ? ' <span class="flag warn" title="Health record more than 48 h older than the latest row">stale &gt;48 h (day ' + esc(rl.row.mission_day) + ')</span>' : '');
      } else if (noData) val = '<span class="muted">NO_DATA - required inputs missing</span>';
      else if (f) val = `<b>${m.bool ? 'Active' : esc(f.value) + (m.unit ? ' ' + esc(m.unit) : '')}</b>`;
      else val = `<span class="muted">${esc(m.empty)}</span>`;
      return `<tr><td>${esc(m.label)}</td><td>${val}</td><td>${f ? `<span class="delta neg">-${fmt(f.deduction, 1)}</span>` : '--'}</td></tr>`;
    }).join('');
    const ftab = (d.factors || []).length
      ? `<table><thead><tr><th>Code</th><th>Factor</th><th>Value</th><th>Deduction</th></tr></thead><tbody>${d.factors.map((f) => `<tr><td>${esc(f.code)}</td><td>${esc(f.label)}</td><td>${esc(f.value)}</td><td class="delta neg">-${fmt(f.deduction, 2)}</td></tr>`).join('')}</tbody></table>`
      : '<div class="muted">No deductions at this reading.</div>';
    let extra = '';
    if (key === 'radiation') {
      const dose = valueOf(d, ['CUM_DOSE']) || 0, pct = Math.min(100, dose / 6);
      const fs = d.factors || [];
      extra = `<div class="panel"><h2>Cumulative dose vs 600 mSv limit</h2>
        <div class="bar ${pct >= 80 ? 'RED' : pct >= 50 ? 'YELLOW' : 'GREEN'}" role="img" aria-label="Dose ${fmt(dose)} of 600 mSv"><i style="width:${pct}%"></i></div>
        <p>${fmt(dose)} mSv of 600 mSv (${fmt(pct)}%) ${src(a.source)}</p>
        <p>Proton factor: ${fs.some((f) => f.code === 'PROTON_FLUX') ? '<span class="flag bad">Proton flux at or above 10 pfu</span>' : '<span class="muted">not triggered</span>'}
        Flare factor: ${fs.some((f) => f.code === 'FLARE_ACTIVE') ? '<span class="flag warn">Flare active</span>' : '<span class="muted">not triggered</span>'}</p>
        <button id="csv">Export dose series (CSV)</button></div>`;
    }
    if (key === 'earth_distance') {
      const t = triage(a);
      extra = `<div class="panel"><h2>Latency tier</h2><p>Tier 1 &lt; 2 s &middot; Tier 2 2-60 s &middot; Tier 3 &gt; 60 s. Current: <b>${t.tier ? 'Tier ' + t.tier + ' (' + fmt(t.lat, 0) + ' s)' : 'tier not exposed (tier 1, or no other division degraded)'}</b> ${src(a.source)}</p></div>
        <div class="panel"><h2>Offline triage guide</h2><p class="muted">Rule-based checklist for when Earth contact is delayed. No medications or dosages.</p>
        <button id="tri" class="primary">Launch offline triage</button><div id="triout" hidden></div></div>`;
    }
    root.innerHTML = `<h1>${esc(cfg.title)}</h1>${tabs(key)}<p class="sub">${esc(cfg.blurb)} ${esc(NOTE)}</p>
      <div class="row panel"><label>Astronaut <select id="astro">${latest.map((l) => `<option ${l.astronaut_id === astro ? 'selected' : ''}>${esc(l.astronaut_id)}</option>`).join('')}</select></label>
        <span>Day ${esc(a.mission_day)} &middot; ${esc(a.scenario_label)}</span>${src(a.source)}</div>
      <div class="panel"><div class="total"><div class="badge st-${esc(d.status)}"><div class="big">${fmt(d.score)}</div><div class="lt">${esc(d.grade || '--')}</div>${pill(d.status)}</div>
        <div><div>${esc(d.name)} sub-score ${src(a.source)}</div><div class="muted">Division sub-score (0-100), letter and status.</div></div></div></div>
      ${extra}
      <div class="panel"><h2>Metrics</h2><table><thead><tr><th>Metric</th><th>Value</th><th>Deduction</th></tr></thead><tbody>${rows}</tbody></table><p class="muted">${esc(cfg.foot)}</p></div>
      <div class="panel"><h2>Factors table</h2>${ftab}</div>
      <div class="panel"><h2>Trend</h2><div class="chartbox"><canvas id="ch" role="img" aria-label="${esc(cfg.title)} trend"></canvas></div></div>`;
    root.querySelector('#astro').onchange = (e) => { astro = e.target.value; load(); };
    const csv = root.querySelector('#csv');
    if (csv) csv.onclick = () => { const u = URL.createObjectURL(new Blob([csvDose(traj)], { type: 'text/csv' })); const l = document.createElement('a'); l.href = u; l.download = 'dose_series.csv'; l.click(); URL.revokeObjectURL(u); };
    const tri = root.querySelector('#tri');
    if (tri) tri.onclick = () => { const o = root.querySelector('#triout'); o.hidden = !o.hidden; o.innerHTML = '<ol>' + triage(a).steps.map((s) => `<li>${esc(s)}</li>`).join('') + '</ol>'; };
    drawTrend(traj);
  }
  function drawTrend(traj) {
    const canvas = root.querySelector('#ch');
    if (chart) chart.destroy();
    if (!window.Chart) { canvas.replaceWith(Object.assign(document.createElement('p'), { className: 'muted', textContent: 'Chart library failed to load.' })); return; }
    const rawByTs = {}; raw.forEach((r) => { rawByTs[r.timestamp] = r; });
    const ds = [{ label: 'Division score', data: traj.map((a) => (a.divisions[key] ? a.divisions[key].score : null)), borderColor: '#22d3ee', borderWidth: 3, tension: .2, pointRadius: 2, yAxisID: 'y' }];
    cfg.series.forEach((s, i) => {
      ds.push({ label: s.label, data: traj.map((a) => { const r = rawByTs[a.timestamp]; return r && typeof r[s.f] === 'number' ? r[s.f] : null; }), borderColor: COLORS[i % COLORS.length], borderWidth: 1.5, pointRadius: 2, tension: .2, spanGaps: false, yAxisID: 'y1' });
      if (s.limit) ds.push({ label: s.label.split(' ')[0] + ' limit', data: traj.map(() => s.limit), borderColor: '#ff4d4d', borderDash: [6, 4], pointRadius: 0, yAxisID: 'y1' });
    });
    Chart.defaults.color = '#9db3d6';
    chart = new Chart(canvas, { type: 'line', data: { labels: traj.map((a) => a.mission_day), datasets: ds }, options: { responsive: true, maintainAspectRatio: false, animation: false,
      scales: { y: { min: 0, max: 100, title: { display: true, text: 'Score' }, grid: { color: '#1e3358' } }, y1: { position: 'right', title: { display: true, text: 'Raw value (stored telemetry)' }, grid: { drawOnChartArea: false } }, x: { title: { display: true, text: 'mission_day' }, grid: { color: '#1e3358' } } },
      plugins: { legend: { labels: { color: '#e8f1ff' } } } } });
  }
  load();
  return () => { dead = true; if (chart) chart.destroy(); };
}

export function render(root, opts = {}) { return renderGuard(root, opts.key || 'radiation'); }

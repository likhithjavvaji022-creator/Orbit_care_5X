import { postJson } from '../api.js';
import { esc, fmt, pill, DIV_ORDER, DIV_NAMES } from '../ui.js';

const FIELDS = [
  ['Radiation', [['cum_dose_msv', 'Cumulative dose (mSv)', 0, 1000, 1, 0], ['proton_flux_pfu', 'Proton flux (pfu)', 0, 100, 1, 0], ['flare_active', 'Solar flare active', 'bool', 0]]],
  ['Isolation & Stress', [['sleep_h', 'Sleep (h)', 0, 12, 0.1, 8], ['hrv_rmssd_ms', 'HRV RMSSD (ms)', 0, 150, 1, 60], ['hrv_baseline_ms', 'HRV baseline (ms)', 20, 150, 1, 60], ['fatigue', 'Fatigue (0-10)', 0, 10, 0.1, 2], ['stress', 'Stress (0-10)', 0, 10, 0.1, 2]]],
  ['Gravity', [['loading_index', 'Loading index', 0, 2, 0.01, 1], ['loading_target', 'Loading target', 0.5, 2, 0.01, 1], ['balance_score', 'Balance score (0-100)', 0, 100, 1, 95]]],
  ['Closed Ecosystem', [['cabin_o2_pct', 'Cabin O2 (%)', 15, 30, 0.1, 21], ['cabin_co2_ppm', 'Cabin CO2 (ppm)', 0, 10000, 50, 500], ['cabin_pressure_kpa', 'Cabin pressure (kPa)', 80, 120, 0.5, 101], ['scrubber_state', 'Scrubber state', 'select', 'nominal']]],
  ['Distance', [['latency_s', 'Comm latency (s)', 0, 1500, 1, 1], ['open_medical_flags', 'Open medical flags', 0, 6, 1, 0]]],
];

export async function render(el) {
  const vals = { astronaut_id: 'WHAT-IF', mission_day: 10, scenario_id: 0, scenario_label: 'what-if', timestamp: '2026-11-10T00:00:00Z', source: 'SIMULATED', cabin_temp_c: 22, cabin_humidity_pct: 45 };
  for (const [, fs] of FIELDS) for (const f of fs) vals[f[0]] = f[2] === 'bool' ? f[3] : f[2] === 'select' ? f[3] : f[5];
  const ctl = (f) => {
    const [k, label, a, b, step] = f;
    if (a === 'bool') return `<label class="row"><input type="checkbox" data-k="${k}"> ${esc(label)}</label>`;
    if (a === 'select') return `<label>${esc(label)} <select data-k="${k}"><option>nominal</option><option>degraded</option><option>offline</option></select></label>`;
    return `<label style="display:block">${esc(label)}: <b data-v="${k}">${vals[k]}</b><input type="range" data-k="${k}" min="${a}" max="${b}" step="${step}" value="${vals[k]}" style="width:100%"></label>`;
  };
  el.innerHTML = `<h1>Mission Simulator</h1>
<p class="sub"><span class="src SIMULATED">SIMULATED</span> What-if sandbox. Values below are hypothetical, are not stored, and do not change any crew record. Uses the current grading weights and thresholds from Settings.</p>
<div class="grid g2"><div class="panel"><h2>Hazard inputs</h2>${FIELDS.map(([t, fs]) => `<fieldset style="border:1px solid var(--line);border-radius:8px;margin-bottom:10px"><legend>${esc(t)}</legend>${fs.map(ctl).join('')}</fieldset>`).join('')}<button id="rst">Reset to nominal</button></div>
<div class="panel" id="out" aria-live="polite"><p class="loading">Calculating...</p></div></div>`;
  const out = el.querySelector('#out');
  let timer = null, seq = 0, dead = false;
  async function calc() {
    const my = ++seq;
    try {
      const a = await postJson('/api/simulate/assess', { row: vals });
      if (dead || my !== seq) return;
      const t = a.total;
      out.innerHTML = `<h2>SIMULATED result <small class="muted">(what-if, not stored)</small></h2>
<div class="panel" style="text-align:center"><div style="font-size:2.4rem"><b>${fmt(t.score)}</b> ${esc(t.grade || '')} ${pill(t.status)}</div>
<div class="muted">Weighted ${fmt(t.weighted)} | Compound penalty ${esc(t.penalty)} | Change vs Day 1 ${fmt(t.delta_from_day1)}</div>
${t.capped ? '<div class="err" role="alert"><b>Bottleneck cap applied:</b> a division is below the red line, so the total cannot exceed Grade D.</div>' : ''}
${t.penalty ? '<div class="warn">Compound penalty: 3 or more divisions are not GREEN.</div>' : ''}</div>
<table><thead><tr><th>Division</th><th>Score</th><th>Status</th><th>Main deductions</th></tr></thead><tbody>${DIV_ORDER.map((k) => { const d = a.divisions[k]; return `<tr><td>${esc(DIV_NAMES[k])}</td><td>${fmt(d.score)} ${esc(d.grade || '')}</td><td>${pill(d.status)}</td><td>${(d.factors || []).map((f) => esc(f.label) + ' (-' + fmt(f.deduction) + ')').join('; ') || '--'}</td></tr>`; }).join('')}</tbody></table>
${(a.interaction_flags || []).length ? `<p class="muted">Interaction hypotheses: ${a.interaction_flags.map((f) => esc(f.pair.join(' + '))).join(', ')} (Hypothesis from HRP hazard descriptions)</p>` : ''}
<p class="muted">${esc(a.label)}</p>`;
    } catch (e) { if (!dead && my === seq) out.innerHTML = `<div class="err" role="alert"><b>Calculation failed.</b><p>${esc(e.message)}</p></div>`; }
  }
  const sched = () => { clearTimeout(timer); timer = setTimeout(calc, 100); };
  el.querySelectorAll('[data-k]').forEach((i) => {
    i.oninput = i.onchange = () => {
      const k = i.dataset.k;
      vals[k] = i.type === 'checkbox' ? (i.checked ? 1 : 0) : i.type === 'range' ? Number(i.value) : i.value;
      const v = el.querySelector(`[data-v="${k}"]`); if (v) v.textContent = vals[k];
      sched();
    };
  });
  el.querySelector('#rst').onclick = () => { for (const [, fs] of FIELDS) for (const f of fs) { const d = f[2] === 'bool' || f[2] === 'select' ? f[3] : f[5]; vals[f[0]] = d; const i = el.querySelector(`[data-k="${f[0]}"]`); if (i.type === 'checkbox') i.checked = !!d; else i.value = d; const v = el.querySelector(`[data-v="${f[0]}"]`); if (v) v.textContent = d; } calc(); };
  calc();
  return () => { dead = true; clearTimeout(timer); };
}

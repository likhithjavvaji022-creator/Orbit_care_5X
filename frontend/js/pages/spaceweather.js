import { get, postJson } from '../api.js';
import { esc, fmt, loading, errorPanel } from '../ui.js';

const SIM = {
  S1: { label: 'S1 (minor)', flux: 10, note: 'Rehearsal at the NOAA S1 threshold (10 pfu).' },
  S3: { label: 'S3 (strong)', flux: 1000, note: 'Rehearsal at the NOAA S3 threshold (1000 pfu).' },
};
const age = (s) => s == null ? '--' : s < 90 ? Math.round(s) + ' s' : Math.round(s / 60) + ' min';

export async function render(el) {
  let sim = null;
  async function load(refresh) {
    el.innerHTML = `<h1>Space Weather</h1>${loading('Fetching NOAA SWPC data...')}`;
    try {
      const sw = refresh ? await postJson('/api/spaceweather/refresh', {}) : await get('/api/spaceweather');
      draw(sw);
    } catch (e) { errorPanel(el, e, () => load(true)); }
  }
  function draw(sw) {
    const d = sw.data, st = sw.status;
    const badge = `<span class="pill ${st === 'LIVE' ? 'GREEN' : st === 'CACHED' ? 'YELLOW' : 'RED'}">${esc(st)}</span>`;
    let h = `<h1>Space Weather</h1><p class="sub">NOAA SWPC GOES observations. No forecasting of solar events; flux is never converted to astronaut dose.</p>
    <div class="panel row">${badge}
      <span>Fetched at: <b>${esc(sw.fetched_at || 'never')}</b></span><span>Age: <b>${esc(age(sw.age_s))}</b></span>
      ${sw.stale ? '<span class="pill RED" title="Older than 30 minutes">STALE (&gt;30 min)</span>' : ''}
      <button class="primary" id="sw-retry">${st === 'FAILED' ? 'Retry' : 'Refresh'}</button></div>`;
    if (sw.error) h += `<div class="err" role="alert"><b>${st === 'FAILED' ? 'NOAA data unavailable.' : 'Last refresh failed; showing cached values.'}</b><p>Reason: ${esc(sw.error)}</p></div>`;
    if (!d) h += `<div class="empty"><b>No space-weather data.</b> Nothing is shown rather than inventing values.</div>`;
    else {
      const p = d.proton_flux || {}, x = d.xray_flux || {}, k = d.kp || {}, sc = d.scales || {};
      if (p.sep_active) h += `<div class="err" role="alert"><b>SHELTER ADVISORY: NOAA S1 threshold reached</b> &mdash; ${esc(p.sep_label || '>=10 pfu at >=10 MeV')}. Follow mission shelter procedures.</div>`;
      h += `<div class="grid"><div class="panel"><h3>Proton flux (&ge;10 MeV)</h3><div class="big">${fmt(p.value, 2)} <small>${esc(p.unit || '')}</small></div><div class="muted">Observed ${esc(p.observed_at || '--')} &middot; ${esc(p.satellite || '')}</div></div>
      <div class="panel"><h3>X-ray flux (0.1-0.8 nm)</h3><div class="big">${x.value == null ? '--' : Number(x.value).toExponential(2)} <small>${esc(x.unit || '')}</small></div><div class="muted">Observed ${esc(x.observed_at || '--')}</div></div>
      <div class="panel"><h3>Planetary Kp</h3><div class="big">${fmt(k.value, 2)}</div><div class="muted">Observed ${esc(k.observed_at || '--')}</div></div></div>
      <div class="panel"><h3>NOAA scales (current)</h3><p>${['R', 'S', 'G'].map((n) => { const v = sc[n] || {}; return `<b>${n}${esc(v.scale ?? '--')}</b> ${esc(v.text || '')}`; }).join(' &nbsp;|&nbsp; ')}</p><p class="muted">Observed ${esc(sc.observed_at || '--')}</p></div>`;
    }
    h += `<div class="panel" id="sim"><h3>Storm rehearsal <span class="src SIMULATED">SIMULATED</span></h3>
      <p class="muted">Training scenario only. Not live data, not a forecast; separate from the values above.</p>
      <div class="row"><button id="sim-S1">Rehearse S1</button><button id="sim-S3">Rehearse S3</button><button id="sim-off">Clear</button></div>`;
    if (sim) h += `<div class="warn" role="status"><span class="src SIMULATED">SIMULATED</span> ${esc(SIM[sim].label)}: proton flux ${SIM[sim].flux} pfu. ${esc(SIM[sim].note)} Rehearse shelter procedures; this is not a real event.</div>`;
    h += `</div>`;
    el.innerHTML = h;
    el.querySelector('#sw-retry').onclick = () => load(true);
    for (const k of ['S1', 'S3']) el.querySelector('#sim-' + k).onclick = () => { sim = k; draw(sw); };
    el.querySelector('#sim-off').onclick = () => { sim = null; draw(sw); };
  }
  await load(false);
}

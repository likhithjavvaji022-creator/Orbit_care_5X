import { get } from '../api.js';
import { esc, DIV_ORDER, DIV_NAMES, pill, fmt, src, loading, errorPanel } from '../ui.js';

export async function render(el) {
  async function load() {
    el.innerHTML = `<h1>AI Risk Analysis</h1>${loading('Loading assessments...')}`;
    try {
      const items = (await get('/api/assessments/latest')).items || [];
      let h = `<h1>AI Risk Analysis</h1><p class="sub">Explainable rule-and-statistics engine. Early-warning screening, not a diagnosis. Defer to the flight surgeon.</p>`;
      if (!items.length) { el.innerHTML = h + `<div class="empty"><b>No assessments yet.</b> Upload telemetry first.</div>`; return; }
      h += `<div class="panel"><table><thead><tr><th>Astronaut</th><th>Day</th><th>Total</th>${DIV_ORDER.map((k) => `<th>${esc(DIV_NAMES[k])}</th>`).join('')}<th>Source</th></tr></thead><tbody>${items.map((a) => `<tr>
        <td>${esc(a.astronaut_id)}</td><td>${esc(a.mission_day)}</td><td><b>${fmt(a.total.score)}</b> ${esc(a.total.grade || '')} ${pill(a.total.status)}${a.total.capped ? ' <span class="muted">(capped)</span>' : ''}</td>
        ${DIV_ORDER.map((k) => { const d = a.divisions[k] || {}; return `<td>${fmt(d.score)} ${pill(d.status || 'NO_DATA')}</td>`; }).join('')}<td>${src(a.source)}</td></tr>`).join('')}</tbody></table></div>`;
      for (const a of items) {
        const rows = DIV_ORDER.flatMap((k) => ((a.divisions[k] || {}).factors || []).map((f) => `<li><b>${esc(DIV_NAMES[k])}</b>: ${esc(f.label)} (value ${esc(f.value)}) lowered the score by ${fmt(f.deduction, 1)} points.</li>`));
        const fl = a.interaction_flags || [];
        h += `<div class="panel"><h3>${esc(a.astronaut_id)} &mdash; why this score</h3>
          ${rows.length ? `<ul>${rows.join('')}</ul>` : '<p class="muted">No deduction factors: all divisions nominal.</p>'}
          <h4>Interaction watch <span class="muted">(hypotheses)</span></h4>
          ${fl.length ? `<ul>${fl.map((f) => `<li>${esc((f.pair || []).map((p) => DIV_NAMES[p] || p).join(' + '))}: <i>${esc(f.label)}</i></li>`).join('')}</ul>` : '<p class="muted">No interaction flags.</p>'}</div>`;
      }
      el.innerHTML = h;
    } catch (e) { errorPanel(el, e, load); }
  }
  await load();
}

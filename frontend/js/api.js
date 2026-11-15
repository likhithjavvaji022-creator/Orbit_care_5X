export async function api(path, opts = {}) {
  let res;
  try {
    res = await fetch(path, opts);
  } catch (e) {
    throw new Error('Cannot reach the backend API (' + path + '): ' + (e && e.message ? e.message : e));
  }
  let body = null;
  try { body = await res.json(); } catch (_) { /* non-JSON */ }
  if (!res.ok) {
    const d = body && body.detail;
    throw new Error((typeof d === 'string' ? d : d ? JSON.stringify(d) : 'HTTP ' + res.status) + ' (' + path + ')');
  }
  return body;
}
export const get = (p) => api(p);
export const postJson = (p, data) => api(p, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
export const postFile = (p, file) => { const f = new FormData(); f.append('file', file); return api(p, { method: 'POST', body: f }); };

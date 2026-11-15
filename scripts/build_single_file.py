#!/usr/bin/env python3
"""Build dist/orbitcare5x.html: one self-contained file (CSS, Chart.js, all JS modules inlined).

ES modules are rewritten into a tiny inline module registry (works from file://).
API base: window.ORBITCARE_API_BASE (from ?api=...) is prepended to every API path
by text-rewriting the bundled api.js / reports.js (frontend/ is never modified).
Usage: python scripts/build_single_file.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FE = ROOT / "frontend"
OUT = ROOT / "dist" / "orbitcare5x.html"

BASE_EXPR = "(window.ORBITCARE_API_BASE||'')"


def key_of(spec):
    return Path(spec).name.rsplit(".", 1)[0]


IMPORT_RE = re.compile(r"^import\s+(.+?)\s+from\s+['\"]([^'\"]+)['\"];?[ \t]*$", re.M)
EXPORT_DECL_RE = re.compile(r"^export\s+((?:async\s+)?function\s*\*?\s*|const\s+|let\s+|var\s+|class\s+)([A-Za-z_$][\w$]*)", re.M)


def convert(name, src):
    exports = []
    src = src.lstrip("﻿")

    def imp(m):
        clause, spec = m.group(1).strip(), m.group(2)
        if clause.startswith("* as "):
            return "const %s = __req(%r);" % (clause[5:].strip(), key_of(spec))
        clause = re.sub(r"\s+as\s+", ": ", clause)
        return "const %s = __req(%r);" % (clause, key_of(spec))

    src = IMPORT_RE.sub(imp, src)

    def exp(m):
        exports.append(m.group(2))
        return m.group(1) + m.group(2)

    src = EXPORT_DECL_RE.sub(exp, src)
    # dynamic imports
    src = re.sub(r"\bimport\(\s*([^)]+?)\s*\)", r"__imp(\1)", src)
    if re.search(r"^\s*(import|export)\s", src, re.M):
        sys.exit("unhandled import/export syntax in " + name)
    tail = "".join("__exp.%s = %s;\n" % (e, e) for e in exports)
    return "function(__exp, __req, __imp){\n%s\n%s}" % (src, tail)


def main():
    mods = {}
    for p in sorted((FE / "js").rglob("*.js")):
        if p.name == "app.js":
            continue
        text = p.read_text(encoding="utf-8")
        k = key_of(p.name)
        assert k not in mods, "duplicate module basename " + k
        if p.name == "api.js":
            assert "fetch(path, opts)" in text
            text = text.replace("fetch(path, opts)", "fetch(%s + path, opts)" % BASE_EXPR)
        if p.name == "reports.js":
            # get()/api() already prefix the base; only direct links need it
            text = re.sub(r"(\.href = )'(/api/[^']*)'", lambda m: "%s%s + '%s'" % (m.group(1), BASE_EXPR, m.group(2)), text)
            text = re.sub(r'href="(/api/[^"]*)"', lambda m: 'href="${%s}%s"' % (BASE_EXPR, m.group(1)), text)
            text = re.sub(r"href='(/api/[^']*)'", lambda m: "href='${%s}%s'" % (BASE_EXPR, m.group(1)), text)
        mods[k] = convert(p.name, text)
    app = convert("app.js", (FE / "js" / "app.js").read_text(encoding="utf-8"))

    registry = ",\n".join("%r: %s" % (k, v) for k, v in mods.items())
    runtime = """(function(){
'use strict';
var q = new URLSearchParams(location.search).get('api');
window.ORBITCARE_API_BASE = q ? q.replace(/\\/+$/, '') : '';
var bar = document.createElement('div');
bar.id = 'offline-banner'; bar.setAttribute('role', 'status');
bar.style.cssText = 'position:sticky;top:0;z-index:9999;padding:8px 14px;font:600 13px/1.4 system-ui,sans-serif;text-align:center;background:#fbbf24;color:#1f1300;';
bar.textContent = window.ORBITCARE_API_BASE
  ? 'Single-file build - API: ' + window.ORBITCARE_API_BASE
  : 'Offline single-file build \\u2014 connect to an ORBITCARE 5X server for data';
document.body.insertBefore(bar, document.body.firstChild);
var defs = {%s};
var cache = {};
function req(k){
  k = String(k).split('/').pop().replace(/\\.js$/, '');
  if (cache[k]) return cache[k];
  if (!defs[k]) throw new Error('Module not found: ' + k);
  var exp = cache[k] = {};
  defs[k](exp, req, imp);
  return exp;
}
function imp(s){ try { return Promise.resolve(req(s)); } catch (e) { return Promise.reject(e); } }
var appFn = %s;
appFn({}, req, imp);
})();""" % (registry, app)

    css = (FE / "css" / "theme.css").read_text(encoding="utf-8")
    chart = (FE / "vendor" / "chart.umd.min.js").read_text(encoding="utf-8")
    html = (FE / "index.html").read_text(encoding="utf-8")

    def esc_script(s):
        return re.sub(r"</(script)", r"<\\/\1", s, flags=re.I)

    html = re.sub(r'<link rel="stylesheet" href="/css/theme.css">', lambda m: "<style>\n" + css.replace("</style", "<\\/style") + "\n</style>", html)
    html = re.sub(r'<script src="/vendor/chart.umd.min.js"></script>', lambda m: "<script>\n" + esc_script(chart) + "\n</script>", html)
    html = re.sub(r'<script type="module" src="/js/app.js"></script>', lambda m: "<script>\n" + esc_script(runtime) + "\n</script>", html)
    assert "/css/theme.css" not in html.split("<style>")[0] and "/js/app.js" not in html[:3000] and "/vendor/" not in html[:3000], "external reference left"
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(html, encoding="utf-8", newline="\n")
    print("wrote %s (%d KB)" % (OUT, OUT.stat().st_size // 1024))


if __name__ == "__main__":
    main()

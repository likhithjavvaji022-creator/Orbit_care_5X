import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
md_path = ROOT / "ORBITCARE_COMPLETE_CODEBASE.md"
txt_path = ROOT / "ORBITCARE_COMPLETE_CODEBASE.txt"
html_path = ROOT / "ORBITCARE_COMPLETE_CODEBASE.html"

content = md_path.read_text(encoding="utf-8")

# 1. Write the TXT version
txt_path.write_text(content, encoding="utf-8")
print(f"Wrote {txt_path.name} ({txt_path.stat().st_size / 1024:.1f} KB)")

# 2. Parse Markdown into structured HTML
sections = re.split(r"\n## File:\s*(?:`?)([^`\r\n]+)(?:`?)\r?\n", content)
header_part = sections[0].strip()

toc_items = []
file_sections_html = []

for i in range(1, len(sections), 2):
    filename = sections[i].strip()
    code_block = sections[i + 1]

    # Handle triple backticks or single backtick fences
    code_text = code_block.strip()
    lang = "text"
    if code_text.startswith("```"):
        first_line, rest = code_text.split("\n", 1)
        lang = first_line.lstrip("`").strip() or "text"
        code = rest.rsplit("```", 1)[0].rstrip()
    elif code_text.startswith("`"):
        first_line, rest = code_text.split("\n", 1)
        lang = first_line.lstrip("`").strip() or "text"
        code = rest.rsplit("`", 1)[0].rstrip()
    else:
        code = code_text

    file_id = "file_" + re.sub(r"[^a-zA-Z0-9_-]", "_", filename)
    escaped_filename = html.escape(filename)
    escaped_lang = html.escape(lang)
    escaped_code = html.escape(code)
    line_count = len(code.splitlines())

    toc_items.append(
        f'<li><a href="#{file_id}">{escaped_filename}</a> <span class="badge">{escaped_lang}</span></li>'
    )

    file_sections_html.append(
        f"""
    <section class="code-card" id="{file_id}">
      <div class="card-header">
        <h3>{escaped_filename}</h3>
        <span class="meta">{line_count} lines &middot; {escaped_lang}</span>
      </div>
      <pre><code>{escaped_code}</code></pre>
    </section>
"""
    )

toc_html = "\n".join(toc_items)
cards_html = "\n".join(file_sections_html)

html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ORBITCARE 5X &mdash; Complete Consolidated Codebase</title>
  <style>
    :root {{
      --bg: #050b1a;
      --card-bg: #0b1630;
      --border: #1e3358;
      --text: #e8f1ff;
      --muted: #9db3d6;
      --cyan: #22d3ee;
      --code-bg: #070f24;
      --badge-bg: #101f40;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.6;
      padding: 24px;
    }}
    .container {{
      max-width: 1400px;
      margin: 0 auto;
    }}
    header {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 24px;
      margin-bottom: 24px;
    }}
    header h1 {{
      color: var(--cyan);
      font-size: 26px;
      margin-bottom: 8px;
    }}
    header p {{
      color: var(--muted);
      font-size: 14px;
    }}
    .layout {{
      display: grid;
      grid-template-columns: 320px 1fr;
      gap: 24px;
      align-items: start;
    }}
    @media (max-width: 960px) {{
      .layout {{ grid-template-columns: 1fr; }}
    }}
    .toc-card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 16px;
      position: sticky;
      top: 24px;
      max-height: calc(100vh - 48px);
      overflow-y: auto;
    }}
    .toc-card h2 {{
      font-size: 16px;
      color: var(--cyan);
      margin-bottom: 12px;
      border-bottom: 1px solid var(--border);
      padding-bottom: 8px;
    }}
    .toc-card ul {{
      list-style: none;
    }}
    .toc-card li {{
      margin-bottom: 8px;
      font-size: 13px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
    }}
    .toc-card a {{
      color: var(--muted);
      text-decoration: none;
      word-break: break-all;
    }}
    .toc-card a:hover {{
      color: var(--cyan);
      text-decoration: underline;
    }}
    .badge {{
      background: var(--badge-bg);
      color: var(--cyan);
      border: 1px solid var(--border);
      border-radius: 4px;
      padding: 1px 6px;
      font-size: 11px;
      text-transform: uppercase;
      font-weight: 600;
      flex-shrink: 0;
    }}
    .code-card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 12px;
      margin-bottom: 24px;
      overflow: hidden;
    }}
    .card-header {{
      background: #091226;
      border-bottom: 1px solid var(--border);
      padding: 12px 18px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .card-header h3 {{
      font-size: 15px;
      color: var(--cyan);
      font-family: monospace;
    }}
    .card-header .meta {{
      font-size: 12px;
      color: var(--muted);
    }}
    pre {{
      background: var(--code-bg);
      padding: 16px;
      overflow-x: auto;
      font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
      font-size: 13px;
      line-height: 1.5;
      color: #e2e8f0;
    }}
    code {{
      white-space: pre;
    }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>ORBITCARE 5X &mdash; Complete Consolidated Repository Codebase</h1>
      <p>Source Repository: https://github.com/likhithjavvaji022-creator/Orbit_care_5X.git</p>
      <p>All source files consolidated into a single document with the 12th section (NASA Research) removed.</p>
    </header>
    <div class="layout">
      <aside class="toc-card">
        <h2>Quick File Index</h2>
        <ul>
          {toc_html}
        </ul>
      </aside>
      <main>
        {cards_html}
      </main>
    </div>
  </div>
</body>
</html>
"""

html_path.write_text(html_template, encoding="utf-8")
print(f"Wrote {html_path.name} ({html_path.stat().st_size / 1024:.1f} KB)")

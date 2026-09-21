import re, glob, html, asyncio
import markdown
from playwright.async_api import async_playwright

CSS = """
@page { size: Letter; margin: 18mm 16mm 18mm 16mm; }
body { font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; font-size: 10.5pt; line-height: 1.45; color: #1a1e1c; }
section.tab { page-break-before: always; }
section.tab:first-of-type { page-break-before: auto; }
h1 { font-size: 20pt; margin: 0 0 4pt; letter-spacing: -0.01em; }
h1 + p { color: #545b57; margin-top: 0; }
h2 { font-size: 13.5pt; margin: 18pt 0 6pt; padding-bottom: 3pt; border-bottom: 1px solid #d7dbd6; page-break-after: avoid; }
p { margin: 5pt 0; }
code { font-family: "Cascadia Mono", Consolas, "DejaVu Sans Mono", monospace; font-size: 9pt; background: #f1f3f0; padding: 0 3px; border-radius: 3px; }
pre { background: #f4f5f3; border: 1px solid #d7dbd6; border-radius: 6px; padding: 8pt 10pt; font-size: 8.6pt; line-height: 1.35; white-space: pre-wrap; word-break: break-word; page-break-inside: avoid; }
pre code { background: none; padding: 0; font-size: inherit; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0 10pt; font-size: 9.4pt; page-break-inside: auto; }
th, td { border: 1px solid #d7dbd6; padding: 4pt 6pt; vertical-align: top; text-align: left; }
th { background: #eef0ec; font-weight: 600; }
tr { page-break-inside: avoid; }
ul, ol { margin: 4pt 0 6pt; padding-left: 20pt; }
li { margin: 2pt 0; }
a { color: #0e5a8a; text-decoration: none; }
.mermaid { text-align: center; margin: 8pt 0 6pt; page-break-inside: avoid; }
.mermaid svg { max-width: 100%; height: auto; }
.tabnav { font-size: 9pt; color: #545b57; margin-bottom: 8pt; }
footer.pf { position: fixed; bottom: 0; right: 0; font-size: 8pt; color: #888; }
"""

def md_to_html(text):
    # keep mermaid blocks out of the markdown converter
    blocks = []
    def stash(m):
        blocks.append(m.group(1)); return f"\n\nMERMAIDBLOCK{len(blocks)-1}\n\n"
    text = re.sub(r"```mermaid\n(.*?)```", stash, text, flags=re.S)
    out = markdown.markdown(text, extensions=["tables", "fenced_code"])
    for i, b in enumerate(blocks):
        out = out.replace(f"<p>MERMAIDBLOCK{i}</p>", f'<pre class="mermaid">{html.escape(b)}</pre>')
    return out

files = sorted(glob.glob("*.md"))
sections = []
for i, f in enumerate(files):
    body = md_to_html(open(f, encoding="utf-8").read())
    tag = "Pipeline & Assignments" if i == 0 else f"Tab {i} of 5"
    sections.append(f'<section class="tab"><div class="tabnav">C2C Pipeline Build Guide · {tag}</div>{body}</section>')

page = f"""<!doctype html><html><head><meta charset="utf-8"><title>C2C Pipeline Build Guide</title>
<style>{CSS}</style></head><body>
{''.join(sections)}
<script type="module">
import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
mermaid.initialize({{ startOnLoad: false, theme: 'neutral', flowchart: {{ htmlLabels: true, curve: 'basis' }}, sequence: {{ useMaxWidth: true }} }});
await mermaid.run({{ querySelector: '.mermaid' }});
window.__mermaid_done = true;
</script>
</body></html>"""
open("guide.html", "w", encoding="utf-8").write(page)

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page()
        await pg.goto("file://" + __import__("os").path.abspath("guide.html"))
        await pg.wait_for_function("window.__mermaid_done === true", timeout=60000)
        n = await pg.evaluate("document.querySelectorAll('.mermaid svg').length")
        print("mermaid svgs rendered:", n)
        await pg.pdf(path="Pipeline & Assignments.pdf", format="Letter", print_background=True,
                     display_header_footer=True,
                     header_template="<div></div>",
                     footer_template="<div style='font-size:8px;color:#888;width:100%;text-align:right;padding-right:16mm;'>C2C Pipeline Build Guide · <span class='pageNumber'></span> / <span class='totalPages'></span></div>",
                     margin={"top": "16mm", "bottom": "16mm", "left": "16mm", "right": "16mm"})
        await b.close()
asyncio.run(main())

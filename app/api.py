from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from agent.generators.python_pytest import build_test_file
import agent.llm as llm
from agent.runner import run_pytest_with_coverage


class GenerateRequest(BaseModel):
    filename: str = "user_module.py"
    code: str


app = FastAPI(title="Test Case Generator Bot")


@app.post("/generate")
def generate(req: GenerateRequest):
    test_code = build_test_file(req.code, req.filename.replace(".py", ""), llm.generate_pytest_tests)
    # Run in-memory: write to temp dir inside runner
    # Here we must pass a filesystem path to the runner, so we write to a temp file.
    import tempfile, pathlib

    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td) / req.filename
        p.write_text(req.code, encoding="utf-8")
        result = run_pytest_with_coverage(str(p), test_code)

    return {
        "provider": llm.LAST_PROVIDER,
        "tests": test_code,
        "returncode": result["returncode"],
        "stdout": result["stdout"],
        "stderr": result["stderr"],
        "coverage": result["coverage"].get("totals", {}),
    }


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    # Polished, responsive UI (no external deps)
    html = (
        """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1"/>
    <title>Test Case Generator</title>
    <style>
      :root { --bg:#0b0d12; --panel:#12151c; --muted:#8892a6; --fg:#e6edf3; --accent:#6aa8ff; --chip:#1b2130; --border:#1f2430; --code:#0e1117; --ok:#2ecc71; --warn:#f39c12; --err:#e74c3c; }
      * { box-sizing:border-box }
      body { margin:0; padding:24px; color:var(--fg); background:linear-gradient(180deg,#0b0d12 0%, #0a0c11 100%); font-family:ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial }
      .container { max-width:1200px; margin:0 auto }
      .header { display:flex; align-items:center; justify-content:space-between; margin-bottom:20px }
      .title { font-size:28px; font-weight:700 }
      .badge { padding:4px 10px; border-radius:999px; background:var(--chip); color:var(--muted); font-size:12px }
      .card { background:var(--panel); border:1px solid var(--border); border-radius:12px; padding:16px }
      .stack { display:grid; gap:12px }
      label { font-size:13px; color:var(--muted) }
      input[type=text] { width:100%; padding:10px 12px; border-radius:8px; border:1px solid var(--border); background:#0c0f15; color:var(--fg) }
      textarea { width:100%; height:320px; padding:12px; border-radius:8px; border:1px solid var(--border); background:#0c0f15; color:var(--fg); font-family:ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace; font-size:14px }
      .toolbar { display:flex; gap:10px; align-items:center }
      .btn { border:1px solid transparent; border-radius:10px; padding:10px 14px; background:var(--accent); color:#061126; font-weight:600; cursor:pointer }
      .btn.sec { background:transparent; border-color:var(--border); color:var(--fg) }
      .grid { display:grid; grid-template-columns:1fr 1fr; gap:16px }
      @media (max-width:920px){ .grid { grid-template-columns:1fr } }
      h3 { margin:0 0 10px 0; font-size:16px; font-weight:600; color:var(--muted) }
      pre { background:var(--code); color:var(--fg); padding:14px; border-radius:10px; border:1px solid var(--border); overflow:auto }
      .chips{ display:flex; gap:8px; flex-wrap:wrap }
      .chip{ background:var(--chip); color:var(--fg); border:1px solid var(--border); border-radius:999px; padding:4px 10px; font-size:12px }
      .status.ok{ color:var(--ok)} .status.warn{ color:var(--warn)} .status.err{ color:var(--err)}
      .right{ text-align:right }
      .hint{ color:var(--muted); font-size:12px }
    </style>
  </head>
  <body>
    <div class="container stack">
      <div class="header">
        <div class="title">Test Case Generator</div>
        <div class="badge" id="provider">provider: -</div>
      </div>

      <div class="card stack">
        <div class="stack">
          <label for="filename">Filename</label>
          <input id="filename" type="text" value="user_module.py" />
        </div>
        <div class="stack">
          <label for="code">Paste Python code</label>
          <textarea id="code" placeholder="e.g.\ndef add(a,b):\n    return a+b\n\nprint(add(2,3))"></textarea>
          <div class="toolbar">
            <button class="btn" onclick="run()" id="runBtn">Generate Tests</button>
            <button class="btn sec" onclick="clearAll()">Clear</button>
            <span class="hint">Tip: UI stores your last code locally.</span>
          </div>
        </div>
      </div>

      <div class="grid">
        <div class="card">
          <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;">
            <h3>Generated tests</h3>
            <button class="btn sec" onclick="copyTests()">Copy</button>
          </div>
          <pre id="tests"></pre>
        </div>
        <div class="card stack">
          <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;">
            <h3>Run output</h3>
            <div class="chips" id="summary"></div>
          </div>
          <pre id="out"></pre>
        </div>
      </div>

      <div class="right hint">Made with FastAPI • pytest • coverage</div>
    </div>

    <script>
      const codeEl = document.getElementById('code');
      const fileEl = document.getElementById('filename');
      const testsEl = document.getElementById('tests');
      const outEl = document.getElementById('out');
      const providerEl = document.getElementById('provider');
      const runBtn = document.getElementById('runBtn');
      const summaryEl = document.getElementById('summary');

      // Restore last session
      codeEl.value = localStorage.getItem('tcg_code') || '';
      fileEl.value = localStorage.getItem('tcg_file') || 'user_module.py';

      function setBusy(b){ runBtn.disabled = b; runBtn.textContent = b ? 'Generating…' : 'Generate Tests'; }
      function clearAll(){ testsEl.textContent = ''; outEl.textContent = ''; codeEl.value = ''; localStorage.removeItem('tcg_code'); }
      async function copyTests(){ try { await navigator.clipboard.writeText(testsEl.textContent || ''); runBtn.textContent='Copied!'; setTimeout(()=>setBusy(false)|| (runBtn.textContent='Generate Tests'),800);} catch(e){} }

      async function run(){
        const filename = (fileEl.value || 'user_module.py').trim();
        const code = codeEl.value || '';
        localStorage.setItem('tcg_code', code);
        localStorage.setItem('tcg_file', filename);
        testsEl.textContent = ''; outEl.textContent = ''; summaryEl.innerHTML=''; providerEl.textContent='provider: -';
        setBusy(true);
        try {
          const res = await fetch('/generate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ filename, code })});
          const data = await res.json();
          testsEl.textContent = data.tests || '';
          providerEl.textContent = `provider: ${data.provider || '-'}`;
          const rc = Number(data.returncode || 0);
          const statusCls = rc === 0 ? 'ok' : (rc === 1 ? 'warn' : 'err');
          const cov = data.coverage || {};
          summaryEl.innerHTML = `
            <span class=chip>status: <span class="status ${statusCls}">${rc === 0 ? 'passed' : 'errors'}</span></span>
            <span class=chip>covered: ${cov.covered_lines ?? '-'} / ${cov.num_statements ?? '-'}</span>
            <span class=chip>coverage: ${cov.percent_covered_display ?? '-'}%</span>
          `;
          outEl.textContent = `stdout:\n${data.stdout || ''}\n\nstderr:\n${data.stderr || ''}`;
        } catch (e){
          outEl.textContent = 'Request failed: ' + (e?.message || e);
        } finally { setBusy(false); }
      }
    </script>
  </body>
 </html>
"""
    )
    return HTMLResponse(content=html, status_code=200)



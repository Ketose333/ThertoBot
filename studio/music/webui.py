#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.webui_shell import render_page

WORKSPACE = Path('/home/user/.openclaw/workspace')
PRESETS_PATH = WORKSPACE / 'studio' / 'music' / 'strudel_presets.json'

DEFAULT_PRESETS = {
    'breakcore-fsharp-starter': """stack(
  s(\"bd*2 [bd bd bd] [~ bd]\").gain(0.95),
  s(\"[~ sd]*2\").gain(0.7),
  s(\"hh*8\").gain(0.3),
  note(\"[f#4 f#5]*2 [c#5 e5 g#5] [f#5 c#5]\")
    .sound(\"sawtooth\")
    .lpf(sine.slow(8).range(600, 3200))
    .gain(0.18)
).fast(1.75)""",
    'hard-glitch': """stack(
  s(\"[bd*4, bd*8]\").gain(1),
  s(\"sd*2\").sometimesBy(0.4, rev).gain(0.55),
  s(\"hh*16\").degradeBy(0.25).gain(0.22),
  note(\"<f#5 c#6 g#5 e5>\").sound(\"square\").gain(0.16)
).fast(2.2)""",
}


def _load_presets() -> dict[str, str]:
    if not PRESETS_PATH.exists():
        PRESETS_PATH.parent.mkdir(parents=True, exist_ok=True)
        PRESETS_PATH.write_text(json.dumps(DEFAULT_PRESETS, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        return dict(DEFAULT_PRESETS)
    try:
        data = json.loads(PRESETS_PATH.read_text(encoding='utf-8'))
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items() if str(k).strip()}
    except Exception:
        pass
    return dict(DEFAULT_PRESETS)


def _save_presets(presets: dict[str, str]) -> None:
    PRESETS_PATH.parent.mkdir(parents=True, exist_ok=True)
    PRESETS_PATH.write_text(json.dumps(presets, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def _page(body: str) -> bytes:
    return render_page(
        title='Music UI',
        heading='뮤직 생성 UI',
        desc='Strudel 프리셋 선택/편집/저장/재생을 shorts/image와 같은 UI 톤으로 맞춘 버전이야.',
        badges=['Studio 연동', 'Preset CRUD', 'Strudel Play/Stop'],
        body_html=body,
    )


def _form(presets: dict[str, str]) -> str:
    presets_json = json.dumps(presets, ensure_ascii=False)
    return f'''
<div class="section">
  <h3>기본 제어</h3>
  <div class="row-3">
    <div>
      <label>프리셋 선택</label>
      <select id="preset"></select>
    </div>
    <div>
      <label>재생</label>
      <button type="button" id="play">Play</button>
    </div>
    <div>
      <label>정지</label>
      <button type="button" class="sub" id="stop">Stop</button>
    </div>
  </div>
  <div id="msg" class="msg">ready</div>
</div>

<div class="section">
  <h3>프리셋 관리</h3>
  <div class="row">
    <div>
      <label>새 프리셋 이름</label>
      <input id="newName" placeholder="예: melodic-rush" />
      <button type="button" class="sub" id="newPreset">새 프리셋 생성</button>
    </div>
    <div>
      <label>현재 프리셋 저장</label>
      <button type="button" class="sub" id="savePreset">프리셋 저장(메모리)</button>
      <button type="button" id="saveAll">전체 저장(파일 반영)</button>
    </div>
  </div>
  <label>코드 편집</label>
  <textarea id="code" class="code-editor"></textarea>
</div>

<div class="section">
  <h3>저장 경로</h3>
  <pre>{html.escape(str(PRESETS_PATH))}</pre>
</div>

<script src="https://unpkg.com/@strudel/web@1.3.0"></script>
<script>
let presets = {presets_json};
const sel = document.getElementById('preset');
const code = document.getElementById('code');
const msg = document.getElementById('msg');

function setMsg(text, bad=false) {{
  msg.style.color = bad ? '#ff9f7a' : '#9fafd9';
  msg.textContent = text;
}}

function renderList() {{
  const prev = sel.value;
  sel.innerHTML = '';
  Object.keys(presets).forEach((k) => {{
    const o = document.createElement('option');
    o.value = k; o.textContent = k; sel.appendChild(o);
  }});
  if (prev && presets[prev]) sel.value = prev;
  if (!sel.value && sel.options.length) sel.value = sel.options[0].value;
  code.value = presets[sel.value] || '';
}}

sel.addEventListener('change', () => {{
  code.value = presets[sel.value] || '';
  setMsg(`선택: ${{sel.value}}`);
}});
renderList();

let inited = false;
async function init() {{
  if (!inited) {{
    await initStrudel();
    inited = true;
  }}
}}

document.getElementById('play').addEventListener('click', async () => {{
  try {{
    await init();
    // eslint-disable-next-line no-eval
    eval(`${{code.value}}.play()`);
    setMsg('재생 중');
  }} catch (e) {{
    setMsg('실행 오류: ' + e.message, true);
  }}
}});

document.getElementById('stop').addEventListener('click', () => {{
  try {{
    if (typeof hush === 'function') hush();
    setMsg('정지');
  }} catch (e) {{
    setMsg('정지 오류: ' + e.message, true);
  }}
}});

document.getElementById('newPreset').addEventListener('click', () => {{
  const name = (document.getElementById('newName').value || '').trim();
  if (!name) return setMsg('새 프리셋 이름을 입력해줘', true);
  presets[name] = presets[sel.value] || 'stack(\\n  s("bd*4")\\n)';
  renderList();
  sel.value = name;
  code.value = presets[name];
  setMsg(`생성됨: ${{name}}`);
}});

document.getElementById('savePreset').addEventListener('click', () => {{
  if (!sel.value) return setMsg('프리셋이 없어', true);
  presets[sel.value] = code.value;
  setMsg(`저장됨(메모리): ${{sel.value}}`);
}});

document.getElementById('saveAll').addEventListener('click', async () => {{
  try {{
    if (sel.value) presets[sel.value] = code.value;
    const body = new URLSearchParams();
    body.set('presets_json', JSON.stringify(presets));
    const r = await fetch('/save', {{
      method:'POST',
      headers:{{'content-type':'application/x-www-form-urlencoded'}},
      body,
    }});
    const data = await r.json();
    if (!data.ok) return setMsg('저장 실패: ' + (data.error || ''), true);
    setMsg('파일 저장 완료');
  }} catch (e) {{
    setMsg('저장 오류: ' + e.message, true);
  }}
}});
</script>
'''


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: str | bytes, ctype: str = 'text/html; charset=utf-8') -> None:
        b = body if isinstance(body, (bytes, bytearray)) else body.encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):  # noqa: N802
        if self.path != '/':
            self._send(404, 'not found', 'text/plain; charset=utf-8')
            return
        self._send(200, _page(_form(_load_presets())))

    def do_POST(self):  # noqa: N802
        if self.path != '/save':
            self._send(404, json.dumps({'ok': False, 'error': 'not found'}), 'application/json; charset=utf-8')
            return
        length = int(self.headers.get('Content-Length', '0') or 0)
        raw = self.rfile.read(length).decode('utf-8', errors='replace')
        form = parse_qs(raw)
        try:
            payload = json.loads((form.get('presets_json', ['{}'])[0] or '{}'))
            if not isinstance(payload, dict):
                raise ValueError('invalid payload')
            presets = {str(k): str(v) for k, v in payload.items() if str(k).strip()}
            _save_presets(presets)
            self._send(200, json.dumps({'ok': True}), 'application/json; charset=utf-8')
        except Exception as e:
            self._send(400, json.dumps({'ok': False, 'error': str(e)}), 'application/json; charset=utf-8')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--host', default='0.0.0.0')
    ap.add_argument('--port', type=int, default=8795)
    args = ap.parse_args()
    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f'[studio-music] http://{args.host}:{args.port}')
    httpd.serve_forever()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

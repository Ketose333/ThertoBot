#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import subprocess
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs


def _val(form: dict[str, list[str]], key: str, default: str = "") -> str:
    return (form.get(key, [default])[0] or default).strip()


def _extract_json(text: str) -> dict:
    i = text.find("{")
    if i < 0:
        return {}
    try:
        return json.loads(text[i:])
    except Exception:
        return {}


def _fmt_kst(ms: int | None) -> str:
    if ms is None:
        return '-'
    try:
        dt = datetime.fromtimestamp(ms / 1000, tz=timezone.utc).astimezone()
        return dt.strftime('%m-%d %H:%M')
    except Exception:
        return str(ms)


def _due_label(ms: int | None, now_ms: int) -> str:
    if ms is None:
        return '-'
    d = int((ms - now_ms) / 1000)
    if d <= 0:
        return '지금/지연'
    m = d // 60
    if m < 1:
        return f'{d}s'
    if m < 60:
        return f'{m}m'
    h = m // 60
    if h < 24:
        return f'{h}h {m%60}m'
    return f'{h//24}d {h%24}h'


def gateway_call(method: str, params: dict) -> tuple[bool, dict, str]:
    cmd = [
        "openclaw",
        "gateway",
        "call",
        method,
        "--timeout",
        "150000",
        "--params",
        json.dumps(params, ensure_ascii=False),
    ]
    p = subprocess.run(cmd, text=True, capture_output=True)
    out = (p.stdout or "") + ("\n" + p.stderr if p.stderr else "")
    data = _extract_json(out)
    return (p.returncode == 0), data, out[-1500:]


RECOVERY_TARGET_NAMES = [
    "youtube-watch-uploads-10m",
    "daily-ops-checkin-1200",
]


def run_recovery_bundle() -> tuple[bool, str]:
    ok, data, raw = gateway_call("cron.list", {"includeDisabled": True})
    if not ok:
        return False, f"복구 실패(cron.list): {raw[-250:]}"

    jobs = data.get("jobs", [])
    by_name = {str(j.get("name", "")): str(j.get("id", "")) for j in jobs}

    selected_ids: list[str] = []
    missing_names: list[str] = []
    for name in RECOVERY_TARGET_NAMES:
        jid = by_name.get(name)
        if jid:
            selected_ids.append(jid)
        else:
            missing_names.append(name)

    if not selected_ids:
        return False, "복구 대상 작업을 찾지 못했어."

    success = 0
    failed = 0
    for jid in selected_ids:
        rok, _, _ = gateway_call("cron.run", {"jobId": jid, "runMode": "force"})
        if rok:
            success += 1
        else:
            failed += 1

    msg = f"비상복구 실행: 성공 {success} / 실패 {failed}"
    if missing_names:
        msg += f" | 미등록: {', '.join(missing_names)}"
    return True, msg


def build_job(form: dict[str, list[str]]) -> dict:
    session_target = _val(form, "sessionTarget", "isolated")
    payload_kind = _val(form, "payloadKind", "agentTurn")
    schedule_kind = _val(form, "scheduleKind", "cron")
    message = _val(form, "message")

    if not message:
        raise ValueError("메시지는 필수야.")

    if schedule_kind == "cron":
        expr = _val(form, "cronExpr")
        if not expr:
            raise ValueError("cron 표현식이 비어있어.")
        schedule = {"kind": "cron", "expr": expr, "tz": _val(form, "tz", "Asia/Seoul")}
    elif schedule_kind == "at":
        at = _val(form, "at")
        if not at:
            raise ValueError("at 시간(ISO)이 필요해.")
        schedule = {"kind": "at", "at": at}
    else:
        every_ms = int(_val(form, "everyMs", "3600000"))
        schedule = {"kind": "every", "everyMs": every_ms}

    if payload_kind == "systemEvent":
        payload = {"kind": "systemEvent", "text": message}
    else:
        payload = {
            "kind": "agentTurn",
            "message": message,
            "model": _val(form, "model", "openai-codex/gpt-5.3-codex"),
            "thinking": _val(form, "thinking", "low"),
        }

    if session_target == "main" and payload_kind != "systemEvent":
        raise ValueError("main 세션은 systemEvent만 가능해.")
    if session_target == "isolated" and payload_kind != "agentTurn":
        raise ValueError("isolated 세션은 agentTurn만 가능해.")

    job = {
        "name": _val(form, "name", "unnamed-job"),
        "schedule": schedule,
        "payload": payload,
        "sessionTarget": session_target,
        "enabled": _val(form, "enabled", "on") == "on",
    }

    delivery_mode = _val(form, "deliveryMode", "")
    delivery_channel = _val(form, "deliveryChannel", "")
    delivery_to = _val(form, "deliveryTo", "")
    if delivery_mode:
        job["delivery"] = {"mode": delivery_mode}
        if delivery_channel:
            job["delivery"]["channel"] = delivery_channel
        if delivery_to:
            job["delivery"]["to"] = delivery_to

    return job


def render_page(alert: str = "") -> bytes:
    ok, data, raw = gateway_call("cron.list", {"includeDisabled": True})
    jobs = data.get("jobs", []) if ok else []

    now_ms = int(time.time() * 1000)
    rows = []
    enabled_count = 0
    disabled_count = 0
    problem_count = 0
    cron_count = 0
    every_count = 0
    at_count = 0
    timeline_items: list[tuple[str, int | None, bool]] = []
    issue_rows = []
    cards = []
    for j in jobs:
        jid_raw = str(j.get("id", ""))
        jid = html.escape(jid_raw)
        name = html.escape(str(j.get("name", "(no name)")))
        enabled = bool(j.get("enabled", True))
        schedule_obj = j.get("schedule", {})
        sk = str(schedule_obj.get("kind", ""))
        if sk == "cron":
            cron_count += 1
        elif sk == "every":
            every_count += 1
        elif sk == "at":
            at_count += 1
        schedule = html.escape(json.dumps(schedule_obj, ensure_ascii=False))
        state = j.get("state", {}) or {}
        last_status_raw = str(state.get("lastStatus", "-"))
        last_status = html.escape(last_status_raw)
        next_run_ms = state.get("nextRunAtMs")
        timeline_items.append((str(j.get("name", "(no name)")), next_run_ms, enabled))
        if enabled:
            enabled_count += 1
        else:
            disabled_count += 1
        next_run = html.escape(f"{_fmt_kst(next_run_ms)} ({_due_label(next_run_ms, now_ms)})")
        delivery = j.get("delivery", {}) or {}
        payload = j.get("payload", {}) or {}
        session_target = str(j.get("sessionTarget", ""))
        btn_toggle = "비활성화" if enabled else "활성화"

        delivery_mode = str(delivery.get("mode", "-"))
        delivery_channel = str(delivery.get("channel", ""))
        delivery_to = str(delivery.get("to", ""))
        delivery_view = html.escape(f"{delivery_mode} | {delivery_channel or '-'} | {delivery_to or '-'}")

        issues: list[str] = []
        if enabled and last_status_raw.lower() not in {"ok", "-"}:
            issues.append(f"lastStatus={last_status_raw}")
        if enabled and next_run_ms is None:
            issues.append("nextRunAtMs 없음")
        if enabled and isinstance(next_run_ms, (int, float)) and next_run_ms < (now_ms - 5 * 60 * 1000):
            issues.append("nextRun 지연(과거 시각)")
        if enabled and delivery.get("mode") == "announce" and not delivery.get("to"):
            issues.append("announce인데 delivery.to 없음")
        if enabled and delivery.get("mode") == "announce" and delivery_channel == "discord" and delivery_to and not delivery_to.startswith("user:") and not delivery_to.startswith("channel:"):
            issues.append("discord target 형식 불명확(to 권장: user:ID)")
        if enabled and payload.get("kind") == "agentTurn" and delivery.get("mode") == "none":
            issues.append("알림 미전송 모드(mode=none)")
        if enabled and session_target == "main" and payload.get("kind") == "systemEvent":
            issues.append("main systemEvent(별도 알림 아님)")

        if issues:
            problem_count += 1
        issue_badges = " ".join([f"<span class='badge'>{html.escape(x)}</span>" for x in issues]) if issues else "-"

        rows.append(
            f"<tr class='job-row' data-name='{name.lower()}' data-enabled={'on' if enabled else 'off'} data-last='{last_status.lower()}'>"
            f"<td>{name}</td>"
            f"<td>{'on' if enabled else 'off'}</td>"
            f"<td><code>{schedule}</code></td>"
            f"<td>{last_status}</td>"
            f"<td>{next_run}</td>"
            f"<td>{delivery_view}</td>"
            f"<td>"
            f"<form method='post' action='/run' style='display:inline'><input type='hidden' name='id' value='{jid}'><button>즉시실행</button></form> "
            f"<form method='post' action='/toggle' style='display:inline'><input type='hidden' name='id' value='{jid}'><input type='hidden' name='enabled' value={'0' if enabled else '1'}><button>{btn_toggle}</button></form> "
            f"<form method='post' action='/remove' style='display:inline' onsubmit=\"return confirm('정말 삭제할까?')\"><input type='hidden' name='id' value='{jid}'><button style='background:#4a1d1d'>삭제</button></form>"
            f"</td>"
            f"</tr>"
        )

        if issues:
            issue_rows.append(
                f"<tr><td>{name}</td><td>{' / '.join(html.escape(x) for x in issues)}</td></tr>"
            )

    if not rows:
        rows.append("<tr><td colspan='7'>작업 없음</td></tr>")

    if not issue_rows:
        issue_rows.append("<tr><td colspan='2'>문제 의심 항목 없음</td></tr>")

    # visual summary cards + timeline
    cards = [
        ("전체", len(jobs), "#3b82f6"),
        ("활성", enabled_count, "#22c55e"),
        ("비활성", disabled_count, "#64748b"),
        ("cron", cron_count, "#a78bfa"),
        ("every", every_count, "#f59e0b"),
        ("at", at_count, "#06b6d4"),
    ]
    card_html = ''.join(
        f"<div class='stat'><div class='k'>{html.escape(k)}</div><div class='v' style='color:{c}'>{v}</div></div>"
        for k, v, c in cards
    )

    tl_sorted = sorted([x for x in timeline_items if x[1] is not None], key=lambda x: x[1])[:9]
    if tl_sorted:
        base = now_ms
        maxv = max(max(ms - base, 1) for _, ms, _ in tl_sorted)
        tl_rows = []
        for name_raw, ms, en in tl_sorted:
            assert ms is not None
            width = max(6, int(((ms - base) / maxv) * 100))
            width = min(100, width)
            name = html.escape(name_raw)
            color = '#22c55e' if en else '#64748b'
            tl_rows.append(
                f"<div class='tl-row'><div class='tl-name'>{name}</div><div class='tl-bar-wrap'><div class='tl-bar' style='width:{width}%;background:{color}'></div></div><div class='tl-when'>{html.escape(_fmt_kst(ms))}</div></div>"
            )
        timeline_html = ''.join(tl_rows)
    else:
        timeline_html = "<div class='muted'>예정 실행 시각 데이터가 없어.</div>"

    alert_html = f"<div class='alert'>{html.escape(alert)}</div>" if alert else ""
    err_html = ""
    if not ok:
        err_html = f"<pre class='err'>{html.escape(raw)}</pre>"

    body = f"""
<!doctype html>
<html lang='ko'>
<head>
<meta charset='utf-8'>
<title>Taeyul Cron Manager</title>
<style>
body{{font-family:system-ui,sans-serif;background:#0f1520;color:#e9eef5;margin:0;padding:20px}}
.panel{{background:#182131;border:1px solid #2b3a52;border-radius:12px;padding:16px;margin-bottom:16px}}
h1,h2{{margin:0 0 12px}}
.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}}
.full{{grid-column:1/-1}}
input,select,textarea,button{{width:100%;box-sizing:border-box;background:#0f1725;color:#e9eef5;border:1px solid #344862;border-radius:8px;padding:9px}}
button{{cursor:pointer}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th,td{{border:1px solid #30435f;padding:8px;vertical-align:top}}
.alert{{background:#143321;border:1px solid #2aa748;padding:10px;border-radius:8px;margin-bottom:12px}}
.err{{white-space:pre-wrap;background:#2a1616;padding:10px;border-radius:8px}}
.badge{{display:inline-block;background:#4a1d1d;border:1px solid #8e3b3b;color:#ffd9d9;border-radius:999px;padding:2px 8px;font-size:12px;margin:2px}}
.stats{{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:8px}}
.stat{{background:#0f1725;border:1px solid #30435f;border-radius:10px;padding:10px}}
.stat .k{{font-size:12px;color:#a9b7cf}}
.stat .v{{font-size:20px;font-weight:700}}
.tl-row{{display:grid;grid-template-columns:240px 1fr 90px;gap:10px;align-items:center;margin:8px 0}}
.tl-name{{font-size:12px;color:#d7e2f2;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.tl-bar-wrap{{height:10px;background:#0b1220;border:1px solid #2a3a54;border-radius:999px;overflow:hidden}}
.tl-bar{{height:100%}}
.tl-when{{font-size:12px;color:#a9b7cf;text-align:right}}
.muted{{color:#9fb0cb;font-size:13px}}
</style>
</head>
<body>
<h1>리마인더 / 크론 관리자</h1>
{alert_html}
<div class='panel'>
  <h2>요약 그래프</h2>
  <div class='stats'>{card_html}</div>
</div>

<div class='panel'>
  <h2>다음 실행 타임라인 (상위 8)</h2>
  {timeline_html}
</div>

<div class='panel'>
  <h2>비상복구</h2>
  <form method='post' action='/recover' onsubmit="return confirm('유튜브/점검 묶음 즉시실행할까?')" style='max-width:320px'>
    <button style='background:#173b2a;border-color:#2aa748'>비상복구 실행 (유튜브/점검)</button>
  </form>
  <div class='muted' style='margin-top:8px'>youtube-watch / daily-ops-checkin 묶음 실행</div>
</div>

<div class='panel'>
  <h2>문제 의심 항목</h2>
  <table>
    <thead><tr><th>이름</th><th>이슈</th></tr></thead>
    <tbody>{''.join(issue_rows)}</tbody>
  </table>
</div>

<div class='panel'>
  <h2>작업 목록 ({len(jobs)})</h2>
  <div class='grid' style='margin-bottom:10px'>
    <input id='jobSearch' placeholder='작업 검색 (이름/스케줄/상태)'>
    <select id='enabledFilter'>
      <option value='all'>전체</option>
      <option value='on'>활성(on)</option>
      <option value='off'>비활성(off)</option>
    </select>
  </div>
  <table id='jobsTable'>
    <thead><tr><th>이름</th><th>enabled</th><th>schedule</th><th>last</th><th>nextRunAtMs</th><th>delivery</th><th>액션</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
  {err_html}
</div>
<script>
(function(){{
  const q = document.getElementById('jobSearch');
  const f = document.getElementById('enabledFilter');
  const rows = Array.from(document.querySelectorAll('#jobsTable .job-row'));
  function apply(){{
    const keyword = (q?.value || '').toLowerCase().trim();
    const enabled = (f?.value || 'all');
    for (const row of rows){{
      const txt = (row.innerText || '').toLowerCase();
      const rowEnabled = row.dataset.enabled || '';
      const okKeyword = !keyword || txt.includes(keyword);
      const okEnabled = (enabled === 'all') || (rowEnabled === enabled);
      row.style.display = (okKeyword && okEnabled) ? '' : 'none';
    }}
  }}
  q?.addEventListener('input', apply);
  f?.addEventListener('change', apply);
}})();
</script>
</body>
</html>
"""
    return body.encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    def _read_form(self) -> dict[str, list[str]]:
        ln = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(ln).decode("utf-8", errors="replace")
        return parse_qs(raw, keep_blank_values=True)

    def _respond_html(self, body: bytes, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self._respond_html(render_page())

    def do_POST(self):
        form = self._read_form()
        path = self.path
        alert = ""

        try:
            if path == "/remove":
                jid = _val(form, "id")
                ok, _, raw = gateway_call("cron.remove", {"jobId": jid})
                alert = f"삭제 완료: {jid}" if ok else f"삭제 실패: {raw[-300:]}"
            elif path == "/run":
                jid = _val(form, "id")
                ok, _, raw = gateway_call("cron.run", {"jobId": jid})
                alert = f"즉시실행 요청 완료: {jid}" if ok else f"실행 실패: {raw[-300:]}"
            elif path == "/toggle":
                jid = _val(form, "id")
                enabled = _val(form, "enabled") == "1"
                ok, _, raw = gateway_call("cron.update", {"jobId": jid, "patch": {"enabled": enabled}})
                alert = f"상태 변경 완료: {jid} -> {'on' if enabled else 'off'}" if ok else f"상태 변경 실패: {raw[-300:]}"
            elif path == "/recover":
                ok, msg = run_recovery_bundle()
                alert = msg if ok else f"{msg}"
            else:
                alert = "지원하지 않는 액션"
        except Exception as e:
            alert = f"실패: {e}"

        self._respond_html(render_page(alert=alert))


def main() -> int:
    ap = argparse.ArgumentParser(description="Taeyul cron web manager")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8767)
    args = ap.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"CRON_WEBUI:http://{args.host}:{args.port}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

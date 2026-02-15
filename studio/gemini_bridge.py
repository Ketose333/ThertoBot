#!/usr/bin/env python3
import argparse
import json
import os
import sys
import urllib.error
import urllib.request


def _force_utf8_stdio() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def call_gemini(api_key: str, prompt: str, model: str = "gemini-2.0-flash") -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    body = {"contents": [{"parts": [{"text": prompt}]}]}

    req = urllib.request.Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini API failed ({e.code}): {err}") from e

    candidates = payload.get("candidates") or []
    if not candidates:
        raise RuntimeError(f"No candidates in Gemini response: {json.dumps(payload, ensure_ascii=False)[:700]}")

    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts).strip()
    if not text:
        raise RuntimeError(f"No text in Gemini response: {json.dumps(payload, ensure_ascii=False)[:700]}")
    return text


def main() -> int:
    _force_utf8_stdio()

    parser = argparse.ArgumentParser(description="Minimal Gemini text bridge (UTF-8 safe)")
    parser.add_argument("prompt", nargs="?", help="Prompt text. If omitted, reads stdin.")
    parser.add_argument("--model", default="gemini-2.0-flash", help="Gemini model id")
    args = parser.parse_args()

    api_key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
    if not api_key:
        print("Missing GEMINI_API_KEY (or GOOGLE_API_KEY)", file=sys.stderr)
        return 2

    prompt = args.prompt if args.prompt is not None else sys.stdin.read()
    prompt = (prompt or "").strip()
    if not prompt:
        print("Prompt is empty", file=sys.stderr)
        return 2

    try:
        text = call_gemini(api_key, prompt, model=args.model)
    except Exception as e:
        print(str(e), file=sys.stderr)
        return 1

    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

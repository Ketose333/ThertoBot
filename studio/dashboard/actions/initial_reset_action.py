#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess


def _run_workspace(no_latest: bool, reason: str) -> int:
    cmd = ['bash', '/home/user/.openclaw/workspace/utility/git/initial_reset_with_latest.sh']
    if no_latest:
        cmd.append('--no-latest')

    env = dict(os.environ)
    if reason:
        env['TAEYUL_INITIAL_RESET_REASON'] = reason

    p = subprocess.run(cmd, text=True, capture_output=True, cwd='/home/user/.openclaw/workspace', env=env)
    out = ((p.stdout or '') + ('\n' + p.stderr if p.stderr else '')).strip()
    print(out.splitlines()[-1] if out else '')
    return p.returncode


def _run_tcg(reason: str) -> int:
    repo = '/home/user/.openclaw/workspace/tcg'
    cmd = [
        'bash', '-lc',
        "set -euo pipefail; "
        "cd /home/user/.openclaw/workspace/tcg; "
        "CURRENT_BRANCH=\"$(git rev-parse --abbrev-ref HEAD)\"; "
        "git checkout --orphan temp_initial; "
        "git add -A; "
        "git commit -m 'chore: initial commit'; "
        "git branch -D \"$CURRENT_BRANCH\"; "
        "git branch -m \"$CURRENT_BRANCH\"; "
        "git push --force-with-lease origin \"$CURRENT_BRANCH\"; "
        "echo done: tcg initial reset completed"
    ]
    env = dict(os.environ)
    if reason:
        env['TAEYUL_INITIAL_RESET_REASON'] = reason
    p = subprocess.run(cmd, text=True, capture_output=True, cwd=repo, env=env)
    out = ((p.stdout or '') + ('\n' + p.stderr if p.stderr else '')).strip()
    print(out.splitlines()[-1] if out else '')
    return p.returncode


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--target', choices=['workspace', 'tcg'], default='workspace')
    ap.add_argument('--no-latest', action='store_true')
    ap.add_argument('--reason', default='')
    args = ap.parse_args()

    if args.target == 'tcg':
        # tcg는 현재 트리 그대로 단일 커밋으로 재작성.
        return _run_tcg(args.reason)

    return _run_workspace(args.no_latest, args.reason)


if __name__ == '__main__':
    raise SystemExit(main())

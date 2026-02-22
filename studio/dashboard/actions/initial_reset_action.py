#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--no-latest', action='store_true')
    ap.add_argument('--reason', default='')
    args = ap.parse_args()

    cmd = ['bash', '/home/user/.openclaw/workspace/utility/git/initial_reset_with_latest.sh']
    if args.no_latest:
        cmd.append('--no-latest')

    env = dict(os.environ)
    if args.reason:
        env['TAEYUL_INITIAL_RESET_REASON'] = args.reason

    p = subprocess.run(cmd, text=True, capture_output=True, cwd='/home/user/.openclaw/workspace', env=env)
    out = ((p.stdout or '') + ('\n' + p.stderr if p.stderr else '')).strip()
    print(out.splitlines()[-1] if out else '')
    return p.returncode


if __name__ == '__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from datetime import datetime
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Sync avatar file into OpenClaw allowed media directory (~/.openclaw/media)."
    )
    p.add_argument(
        "--src",
        default="/home/user/.openclaw/workspace/avatars/taeyul.png",
        help="Source avatar path (default: workspace avatars/taeyul.png)",
    )
    p.add_argument(
        "--dest-dir",
        default="/home/user/.openclaw/media/avatars",
        help="Destination directory allowed by message tool",
    )
    p.add_argument(
        "--topic",
        default="taeyul_avatar",
        help="Topic slug for timestamped file name",
    )
    p.add_argument(
        "--canonical-name",
        default="taeyul.png",
        help="Canonical filename to keep updated in dest dir",
    )
    p.add_argument(
        "--no-timestamp-copy",
        action="store_true",
        help="Skip creating timestamped snapshot copy",
    )
    return p.parse_args()


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def main() -> int:
    args = parse_args()

    src = Path(args.src).expanduser().resolve()
    if not src.exists() or not src.is_file():
        raise SystemExit(f"[ERROR] source file not found: {src}")

    dest_dir = Path(args.dest_dir).expanduser().resolve()
    dest_dir.mkdir(parents=True, exist_ok=True)

    copied = []

    canonical = dest_dir / args.canonical_name
    ensure_parent(canonical)
    shutil.copy2(src, canonical)
    copied.append(canonical)

    if not args.no_timestamp_copy:
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        snap_name = f"{ts}_{args.topic}_v1{src.suffix.lower() or '.png'}"
        snapshot = dest_dir / snap_name
        shutil.copy2(src, snapshot)
        copied.append(snapshot)

    print("[OK] synced avatar file(s):")
    for p in copied:
        print(str(p))

    print("\n[NOTE] Use one of the above paths in message tool filePath.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

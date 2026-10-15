"""Stable, JSON-emitting command-line entry point."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .core import Error, apply, export_packet, reconcile, validate


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Offline, chapter-bound EPUB 3 short-alt approval control")
    parser.add_argument("--version", action="version", version=f"altfreeze {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    export = commands.add_parser("export", help="Create an offline review packet from an EPUB")
    export.add_argument("epub", type=Path)
    export.add_argument("--out", type=Path, required=True, help="New packet directory; parent must exist")
    for command in ("check", "apply", "reconcile"):
        sub = commands.add_parser(command, help={"check": "Validate source binding and decisions", "apply": "Write separate EPUB, receipt and next baseline", "reconcile": "Reopen changed source decisions for review"}[command])
        sub.add_argument("epub", type=Path, help="Exact original EPUB for this packet")
        sub.add_argument("packet", type=Path)
        sub.add_argument("--decisions", type=Path, help="Reviewer JSON returned by review.html; defaults to packet/decisions.json")
        if command == "check":
            sub.add_argument("--allow-incomplete", action="store_true", help="Validate a saved draft without approving output")
        else:
            sub.add_argument("--out", type=Path, required=True, help="New output directory; parent must exist")
        if command == "reconcile":
            sub.add_argument("revised_epub", type=Path, help="Vendor-returned revision of the same publication")
    args = parser.parse_args(argv)
    try:
        if args.command == "export":
            result = export_packet(args.epub, args.out)
            summary = {"source_sha256": result["source_sha256"], "occurrences": len(result["items"]), "output": str(args.out)}
        elif args.command == "check":
            _, snapshot, decisions = validate(args.epub, args.packet, args.decisions, complete=not args.allow_incomplete)
            summary = {"source_sha256": snapshot["source_sha256"], "occurrences": len(decisions["items"]), "complete_required": not args.allow_incomplete}
        elif args.command == "apply":
            result = apply(args.epub, args.packet, args.out, args.decisions)
            summary = {"output_sha256": result["output_sha256"], "changed_entries": result["changed_entries"], "output": str(args.out)}
        else:
            result = reconcile(args.epub, args.packet, args.revised_epub, args.out, args.decisions)
            summary = {**result["summary"], "output": str(args.out)}
        print(json.dumps({"ok": True, "command": args.command, **summary}, ensure_ascii=True))
        return 0
    except (Error, OSError, UnicodeError, RecursionError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

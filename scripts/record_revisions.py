"""Record approved edits to files pinned by the import receipt.

Every file listed in manifest/import_receipt.json keeps a hash chain: the
imported hash, then one entry in manifest/revisions.json per approved edit. Run
this after editing pinned files, with a reason a reviewer can read:

    python scripts/record_revisions.py --reason "Why these files changed" docs/ data/modules.json

Only changed files under the given paths are recorded. Nothing else is touched.
"""
from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="+", help="Files or folders to record, relative to the repository root")
    parser.add_argument("--reason", required=True)
    parser.add_argument("--date", default=date.today().isoformat())
    args = parser.parse_args(argv)
    if len(args.reason.strip()) < 10:
        parser.error("give a reason of at least 10 characters")
    date.fromisoformat(args.date)
    receipt = json.loads((ROOT / "manifest/import_receipt.json").read_text(encoding="utf-8"))
    rev_path = ROOT / "manifest/revisions.json"
    log = json.loads(rev_path.read_text(encoding="utf-8"))
    chain_end = {f["path"]: f["sha256"] for f in receipt["files"]}
    for rev in log["revisions"]:
        if chain_end.get(rev["path"]) != rev["previous_sha256"]:
            print(f"Revision chain already broken for {rev['path']}; fix it before recording more", file=sys.stderr)
            return 3
        chain_end[rev["path"]] = rev["sha256"]
    prefixes = [p.rstrip("/") for p in args.paths]
    selected = [p for p in chain_end if any(p == q or p.startswith(q + "/") for q in prefixes)]
    added = 0
    for path in sorted(selected):
        file = ROOT / path
        if not file.is_file():
            print(f"Pinned file is missing and cannot be recorded: {path}", file=sys.stderr)
            return 3
        current = hashlib.sha256(file.read_bytes()).hexdigest()
        if current != chain_end[path]:
            log["revisions"].append({"path": path, "previous_sha256": chain_end[path], "sha256": current,
                                     "date": args.date, "reason": args.reason.strip()})
            added += 1
    rev_path.write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Recorded {added} revision(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

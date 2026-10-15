"""Condense a source-review report into the published link-check record.

The record says, per source and per authority, whether the recorded URL opened
on the day of the run. Opening is HTTP 200 with a complete body. It is a link
check only and never changes a legal review date.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

METHOD = ("Each recorded source URL was requested once. A source counts as opened when the server "
          "returned HTTP 200 with a complete response body. This confirms the link works on that day; "
          "it is not a legal review and does not show that the law is unchanged.")


def condense(report: dict, run_url: str | None = None) -> dict:
    if report.get("kind") != "source_identity_review_report":
        raise ValueError("not a source review report")
    if report.get("selection", {}).get("is_partial_selection"):
        raise ValueError("partial runs cannot be recorded; run the full inventory")
    sources, authorities = {}, {}
    for result in report["results"]:
        opened = result["status"] != "fetch_failed"
        error = result["evidence"].get("error") or {}
        reason = None if opened else (error.get("kind") or "fetch_failed")
        for identity in result["identities"]:
            entry = {"url": result["url"], "result": "opened" if opened else "failed"}
            if reason:
                entry["reason"] = reason
                if error.get("message"):
                    entry["detail"] = str(error["message"])[:160]
            sources[identity["source_id"]] = entry
            for aid in identity.get("authority_ids", []):
                # An authority opens if any of its recorded sources opened.
                if opened:
                    authorities[aid] = "opened"
                else:
                    authorities.setdefault(aid, "failed")
    counts = {"opened": sum(1 for s in sources.values() if s["result"] == "opened"),
              "failed": sum(1 for s in sources.values() if s["result"] == "failed")}
    return {"schema_version": 1, "kind": "link_check", "checked_on": report["as_of"],
            "started_at": report.get("started_at"), "finished_at": report.get("finished_at"),
            "run_url": run_url, "method": METHOD, "counts": counts,
            "authorities": dict(sorted(authorities.items())), "sources": dict(sorted(sources.items()))}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    server, repo, run = (os.environ.get(k) for k in ("GITHUB_SERVER_URL", "GITHUB_REPOSITORY", "GITHUB_RUN_ID"))
    run_url = f"{server}/{repo}/actions/runs/{run}" if server and repo and run else None
    try:
        record = condense(json.loads(args.report.read_text(encoding="utf-8")), run_url)
    except (OSError, ValueError, KeyError) as exc:
        print(f"Link check record error: {exc}", file=sys.stderr)
        return 3
    # One source per line keeps diffs readable and the file printable in a job log.
    head = {k: v for k, v in record.items() if k not in ("authorities", "sources")}
    lines = ["{"] + [f"  {json.dumps(k)}: {json.dumps(v, ensure_ascii=False)}," for k, v in head.items()]
    for name in ("authorities", "sources"):
        items = list(record[name].items())
        lines.append(f'  "{name}": {{')
        lines += [f"    {json.dumps(k)}: {json.dumps(v, ensure_ascii=False)}{',' if i < len(items) - 1 else ''}"
                  for i, (k, v) in enumerate(items)]
        lines.append("  }," if name == "authorities" else "  }")
    lines.append("}")
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(record["counts"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

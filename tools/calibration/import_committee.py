"""Turn the grading committee's results into draft ratings on the rating page.

    python3 tools/calibration/import_committee.py RESULTS.json [--feedback FILE]

RESULTS.json is the committee workflow's return value: a list of {batch, opus, fable, chair},
each holding {"models": [...]} with per-model scores, reasons, issues (pinned to a panel and a
spot inside it), summary and, for the chair, disputes. For each model the chair's grade becomes a
"draft" entry: its scores, reasons, issues (pins converted to sheet pixels) and summary as the
notes, plus a `committee` snapshot (each member's scores, the chair's original grade) that's never
edited, so the person's changes can be measured against it. A model the person has already
touched keeps their ratings; only its `committee` snapshot is added.
"""

import argparse
import json
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Panel content boxes on a review sheet (tools/review_sheet.py): x0, y0, width, height.
PANELS = {
    1: (0, 52, 480, 480), 2: (480, 52, 480, 480), 3: (960, 52, 480, 480), 4: (1440, 52, 480, 480),
    5: (0, 554, 960, 480), 6: (960, 554, 960, 480),
    7: (0, 1056, 480, 480), 8: (480, 1056, 480, 480), 9: (960, 1056, 480, 480), 10: (1440, 1056, 480, 480),
    11: (0, 1558, 480, 480), 12: (480, 1558, 480, 480),
}


def pin(issue):
    x0, y0, w, h = PANELS[issue["panel"]]
    fx = min(1.0, max(0.0, issue["fx"]))
    fy = min(1.0, max(0.0, issue["fy"]))
    out = {
        "x": round(x0 + fx * w), "y": round(y0 + fy * h),
        "type": issue["type"], "severity": issue["severity"], "note": issue["note"],
        "panel": issue["panel"], "region": issue.get("region"), "by": issue.get("by", "chair"),
    }
    return out


def touched(entry):
    return entry.get("status") in ("done", "skipped") or (entry.get("status") != "draft" and (
        entry.get("scores") or entry.get("issues") or entry.get("notes")))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results", type=Path)
    ap.add_argument("--feedback", type=Path, default=ROOT / "assets/blender/proto/calibration/feedback.json")
    a = ap.parse_args()

    results = json.loads(a.results.read_text())
    try:
        data = json.loads(a.feedback.read_text())
    except (OSError, ValueError):
        data = {"version": 1, "items": {}}
    items = data.setdefault("items", {})

    drafted = kept = 0
    for r in results:
        if not r or not r.get("chair"):
            continue
        members = {who: {m["id"]: m for m in (r.get(who) or {}).get("models", [])} for who in ("opus", "fable")}
        for m in r["chair"]["models"]:
            sid = m["id"]
            scores = {k: v for k, v in m["scores"].items() if v is not None}
            committee = {
                "scores": {who: {k: v for k, v in g[sid]["scores"].items() if v is not None} for who, g in members.items() if sid in g},
                "chair": m,
                "members": {who: g[sid] for who, g in members.items() if sid in g},
            }
            old = items.get(sid, {})
            if touched(old):
                old["committee"] = committee
                kept += 1
                continue
            notes = m["summary"]
            if m.get("disputes"):
                notes += "\n\nCommittee disagreements: " + m["disputes"]
            items[sid] = {
                "status": "draft",
                "scores": scores,
                "reasons": {k: v for k, v in m["reasons"].items() if v and (k != "cohesion" or "cohesion" in scores)},
                "issues": [pin(i) for i in m["issues"]],
                "notes": notes,
                "committee": committee,
            }
            drafted += 1

    a.feedback.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=a.feedback.parent, suffix=".tmp")
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, a.feedback)
    print(f"{drafted} drafts written, {kept} already rated (committee snapshot added) -> {a.feedback}")


if __name__ == "__main__":
    main()

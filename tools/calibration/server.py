"""Local page for rating model review sheets, the human half of calibrating the model grader.

    python3 tools/calibration/server.py [--sheets DIR] [--feedback FILE] [--port 5194]

Serves tools/calibration/index.html at http://127.0.0.1:<port>/. It lists the review sheets in
--sheets (<name>-<which>.png plus the metrics .json that tools/review_sheet.py writes next to
each), and saves each rating to --feedback as it's made (one JSON object keyed by sheet id).
The sheets are rendered from the game data, so they stay local: the server only listens on
127.0.0.1 and nothing here is meant to be committed except the feedback file.
"""

import argparse
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SHEET_ID = re.compile(r"^[A-Za-z0-9_.-]+$")


def load_assemblies():
    path = ROOT / "src/viewer/assemblies.json"
    return {a["name"]: len(a["pieces"]) for a in json.loads(path.read_text())}


def load_kinds():
    path = ROOT / "reference/models/catalogue.json"
    try:
        return {m["name"]: m["kind"] for m in json.loads(path.read_text())}
    except (OSError, ValueError):
        return {}


def make_handler(sheets: Path, feedback: Path):
    assemblies = load_assemblies()
    kinds = load_kinds()

    def items():
        out = []
        for png in sorted(sheets.glob("*.png")):
            sid = png.stem
            name, _, which = sid.rpartition("-")
            metrics = {}
            meta = png.with_suffix(".json")
            if meta.exists():
                m = json.loads(meta.read_text())
                metrics = {
                    "triangles": m.get("triangles"),
                    "silhouette_iou": m.get("silhouette_iou"),
                    "height_to_width": m.get("height_to_width"),
                    "max_height_px": m.get("max_height_px"),
                    "colour_dE_mean": m.get("colour_dE_mean"),
                    "height_error_px_mean": m.get("height_error_px_mean"),
                }
            pieces = assemblies.get(name, 0)
            kind = "assembly" if pieces else kinds.get(name, "ship" if name.startswith("ship-") else "enemy")
            out.append({"id": sid, "name": name, "which": which, "kind": kind, "pieces": pieces, "sheet": f"sheets/{png.name}", "metrics": metrics})
        return out

    def read_feedback():
        try:
            return json.loads(feedback.read_text())
        except (OSError, ValueError):
            return {"version": 1, "items": {}}

    def write_feedback(data):
        feedback.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=feedback.parent, suffix=".tmp")
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2, sort_keys=True)
            f.write("\n")
        os.replace(tmp, feedback)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, code, body, ctype="application/json"):
            data = body if isinstance(body, bytes) else json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            path = self.path.split("?")[0]
            if path in ("/", "/index.html"):
                return self.send(200, (HERE / "index.html").read_bytes(), "text/html; charset=utf-8")
            if path == "/api/items":
                return self.send(200, items())
            if path == "/api/feedback":
                return self.send(200, read_feedback())
            if path.startswith("/sheets/"):
                name = path[len("/sheets/"):]
                file = sheets / name
                if SHEET_ID.match(name) and name.endswith(".png") and file.is_file():
                    return self.send(200, file.read_bytes(), "image/png")
            self.send(404, {"error": "not found"})

        def do_PUT(self):
            path = self.path.split("?")[0]
            if not path.startswith("/api/feedback/"):
                return self.send(404, {"error": "not found"})
            sid = path[len("/api/feedback/"):]
            if not SHEET_ID.match(sid):
                return self.send(400, {"error": "bad id"})
            try:
                entry = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            except ValueError:
                return self.send(400, {"error": "bad json"})
            data = read_feedback()
            entry["updatedAt"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            data.setdefault("items", {})[sid] = entry
            write_feedback(data)
            self.send(200, {"ok": True, "updatedAt": entry["updatedAt"]})

    return Handler


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheets", type=Path, required=True)
    ap.add_argument("--feedback", type=Path, default=ROOT / "assets/blender/proto/calibration/feedback.json")
    ap.add_argument("--port", type=int, default=5194)
    a = ap.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", a.port), make_handler(a.sheets.resolve(), a.feedback.resolve()))
    print(f"Rating page: http://127.0.0.1:{a.port}/  (feedback -> {a.feedback})", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()

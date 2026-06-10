from __future__ import annotations

import cgi
import json
import mimetypes
import shutil
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from ctf_agent.challenge import ChallengeSpec
from ctf_agent.workspace import create_workspace

WEB_ROOT = Path(__file__).resolve().parent.parent / "web"


class CTFWebHandler(BaseHTTPRequestHandler):
    workspaces_root: Path = Path("workspaces")
    server_version = "CTFAgentWeb/0.1"

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[web] {self.address_string()} - {format % args}")

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path) -> None:
        if not path.is_file():
            self.send_error(404)
            return
        content = path.read_bytes()
        mime, _ = mimetypes.guess_type(str(path))
        self.send_response(200)
        self.send_header("Content-Type", mime or "application/octet-stream")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index.html"):
            self._send_file(WEB_ROOT / "index.html")
            return
        if path == "/style.css":
            self._send_file(WEB_ROOT / "style.css")
            return
        if path == "/app.js":
            self._send_file(WEB_ROOT / "app.js")
            return
        if path == "/health":
            self._send_json(200, {"ok": True})
            return

        self.send_error(404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/create":
            self.send_error(404)
            return

        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            self._send_json(400, {"ok": False, "error": "multipart/form-data required"})
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        environ = {
            "REQUEST_METHOD": "POST",
            "CONTENT_TYPE": content_type,
            "CONTENT_LENGTH": str(length),
        }
        form = cgi.FieldStorage(fp=io_bytes(raw), environ=environ, keep_blank_values=True)

        payload_raw = form.getvalue("payload")
        if not payload_raw:
            self._send_json(400, {"ok": False, "error": "payload missing"})
            return

        try:
            data = json.loads(payload_raw)
            spec = ChallengeSpec.from_dict(data)
        except (json.JSONDecodeError, ValueError, KeyError) as exc:
            self._send_json(400, {"ok": False, "error": str(exc)})
            return

        uploaded_paths: list[Path] = []
        tmp_dir: Path | None = None

        file_items = form["files"] if "files" in form else None
        if file_items is not None:
            if not isinstance(file_items, list):
                file_items = [file_items]
            tmp_dir = Path(tempfile.mkdtemp(prefix="ctf-upload-"))
            for item in file_items:
                if not item.filename:
                    continue
                dest = tmp_dir / Path(item.filename).name
                dest.write_bytes(item.file.read())
                uploaded_paths.append(dest)

        try:
            ws = create_workspace(
                spec,
                root=self.workspaces_root,
                files=uploaded_paths or None,
            )
            self._send_json(200, {"ok": True, "path": str(ws.resolve())})
        except Exception as exc:
            self._send_json(500, {"ok": False, "error": str(exc)})
        finally:
            if tmp_dir and tmp_dir.exists():
                shutil.rmtree(tmp_dir, ignore_errors=True)


def io_bytes(data: bytes):
    import io

    return io.BytesIO(data)


def run_web_server(host: str, port: int, workspaces: Path) -> None:
    workspaces.mkdir(parents=True, exist_ok=True)
    CTFWebHandler.workspaces_root = workspaces.resolve()

    server = ThreadingHTTPServer((host, port), CTFWebHandler)
    url = f"http://{host}:{port}"
    print(f"CTF Agent web UI: {url}")
    print(f"Workspaces: {workspaces.resolve()}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()

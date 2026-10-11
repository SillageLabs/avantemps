"""API de lecture et interface statique LOCALES ; pas de déploiement Internet."""
from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .storage import list_versions, load_latest

WEB_ROOT = Path(__file__).resolve().parent.parent / "web"
ASSETS = {"/": ("index.html", "text/html; charset=utf-8"),
          "/app.js": ("app.js", "text/javascript; charset=utf-8"),
          "/styles.css": ("styles.css", "text/css; charset=utf-8")}


class Handler(BaseHTTPRequestHandler):
    data_dir = Path("var/data")

    def send_payload(self, status: int, payload: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy",
                         "default-src 'none'; script-src 'self'; style-src 'self'; "
                         "connect-src 'self'; img-src 'self'; base-uri 'none'; "
                         "form-action 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(payload)

    def json_response(self, status: int, body: dict | list) -> None:
        self.send_payload(status, json.dumps(body, ensure_ascii=False).encode("utf-8"),
                          "application/json; charset=utf-8")

    def do_GET(self) -> None:  # noqa: N802 — interface stdlib
        url = urlsplit(self.path)
        try:
            if url.path == "/api/health":
                self.json_response(200, {"status": "ok", "has_data": load_latest(self.data_dir) is not None})
                return
            if url.path == "/api/roni/latest":
                data = load_latest(self.data_dir)
                if data is None:
                    self.json_response(503, {"error": "Aucune observation importée. Exécuter python3 -m avantemps.ingest."})
                    return
                self.json_response(200, {k: data[k] for k in ("id", "index_name", "source_url", "explanation_url",
                                                            "retrieved_at_utc", "note", "summary")})
                return
            if url.path == "/api/roni/history":
                raw = parse_qs(url.query).get("limit", ["24"])[0]
                try:
                    limit = int(raw)
                except ValueError:
                    self.json_response(400, {"error": "limit doit être un entier"})
                    return
                if not 1 <= limit <= 120:
                    self.json_response(400, {"error": "limit doit être entre 1 et 120"})
                    return
                data = load_latest(self.data_dir)
                if data is None:
                    self.json_response(503, {"error": "Aucune observation importée"})
                    return
                self.json_response(200, {"snapshot_id": data["id"], "records": data["records"][-limit:],
                                         "unit": data["unit"]})
                return
            if url.path == "/api/roni/versions":
                self.json_response(200, {"versions": list_versions(self.data_dir)})
                return
            if url.path in ASSETS:
                filename, mime = ASSETS[url.path]
                self.send_payload(200, (WEB_ROOT / filename).read_bytes(), mime)
                return
            self.json_response(404, {"error": "Chemin inconnu"})
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            self.json_response(500, {"error": "Archive illisible ; vérifier les journaux locaux"})

    def log_message(self, format: str, *args: object) -> None:
        super().log_message(format, *args)


def main() -> None:
    parser = argparse.ArgumentParser(description="AVANTEMPS — serveur local en lecture seule")
    parser.add_argument("--data-dir", type=Path, default=Path("var/data"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18767)
    args = parser.parse_args()
    if args.host not in ("127.0.0.1", "localhost", "::1"):
        parser.error("Ce prototype ne peut écouter que sur l'interface locale.")
    handler = type("AvantempsHandler", (Handler,), {"data_dir": args.data_dir})
    with ThreadingHTTPServer((args.host, args.port), handler) as server:
        print(f"AVANTEMPS : http://{args.host}:{args.port}/", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()

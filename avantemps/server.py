"""API de consultation locale, sans alertes ni exposition publique."""
from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .freshness import assess_freshness
from .changes import diff_snapshots
from .territories import get_territory, list_territories
from .storage import SHA_RE, list_versions, load_latest, load_snapshot

WEB_ROOT = Path(__file__).resolve().parent.parent / "web"
ASSETS = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
}


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

    def revision_response(self, query: str) -> None:
        params = parse_qs(query)
        before_values = params.get("before", [])
        after_values = params.get("after", [])
        if len(before_values) > 1 or len(after_values) > 1:
            self.json_response(400, {"error": "Paramètre répété"})
            return
        if bool(before_values) != bool(after_values):
            self.json_response(400, {"error": "Fournir before ET after, ou aucun"})
            return

        if before_values:
            before_id, after_id = before_values[0], after_values[0]
            if not SHA_RE.fullmatch(before_id) or not SHA_RE.fullmatch(after_id):
                self.json_response(400, {"error": "Identifiant SHA-256 invalide"})
                return
        else:
            latest = load_latest(self.data_dir)
            if latest is None:
                self.json_response(503, {"error": "Aucune archive NOAA chargée"})
                return
            after_id = latest["id"]
            prior = [v for v in list_versions(self.data_dir) if v["id"] != after_id]
            if not prior:
                self.json_response(200, {"status": "insufficient_versions", "comparison": None})
                return
            before_id = prior[0]["id"]

        try:
            before = load_snapshot(self.data_dir, before_id)
            after = load_snapshot(self.data_dir, after_id)
        except FileNotFoundError:
            self.json_response(404, {"error": "Version inconnue"})
            return
        self.json_response(200, {"status": "ok", "comparison": diff_snapshots(before, after)})

    def do_GET(self) -> None:  # noqa: N802 — protocole HTTP stdlib
        url = urlsplit(self.path)
        try:
            if url.path == "/api/verification/status":
                self.json_response(200, {
                    "status": "not_evaluated",
                    "territory_id": "nouvelle-caledonie",
                    "metric": "RPSS",
                    "result": None,
                    "publication_authorized": False,
                    "scientific_review": "not_performed",
                    "method_documentation": "https://github.com/SillageLabs/avantemps/blob/main/docs/hindcast-verification.md",
                    "message": "Aucun jeu de hindcasts régionaux indépendamment validé : AVANTEMPS n'affiche ni score de qualité ni probabilité de risque."
                })
                return
            if url.path == "/api/territories":
                self.json_response(200, {
                    "territories": list_territories(),
                    "note": "Profils documentaires non actualisés en direct",
                })
                return
            if url.path.startswith("/api/territories/"):
                key = url.path.removeprefix("/api/territories/")
                result = get_territory(key)
                if result is None:
                    self.json_response(404, {"error": "Territoire non étudié ou inconnu"})
                else:
                    self.json_response(200, result)
                return
            if url.path == "/api/health":
                self.json_response(200, {"status": "ok", "has_data": load_latest(self.data_dir) is not None})
                return
            if url.path == "/api/roni/latest":
                data = load_latest(self.data_dir)
                if data is None:
                    self.json_response(503, {"error": "Aucune observation importée. Exécuter python3 -m avantemps.ingest."})
                    return
                payload = {k: data[k] for k in (
                    "id", "index_name", "source_url", "explanation_url",
                    "retrieved_at_utc", "last_checked_at_utc", "note", "summary"
                )}
                payload["freshness"] = assess_freshness(data)
                self.json_response(200, payload)
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
            if url.path == "/api/roni/changes":
                self.revision_response(url.query)
                return
            if url.path in ASSETS:
                filename, mime = ASSETS[url.path]
                self.send_payload(200, (WEB_ROOT / filename).read_bytes(), mime)
                return
            self.json_response(404, {"error": "Chemin inconnu"})
        except (OSError, ValueError, KeyError, UnicodeDecodeError, json.JSONDecodeError):
            self.json_response(500, {"error": "Archive invalide ou illisible ; vérifier les journaux locaux"})

    def log_message(self, format: str, *args: object) -> None:
        super().log_message(format, *args)


def main() -> None:
    parser = argparse.ArgumentParser(description="AVANTEMPS — serveur local en lecture seule")
    parser.add_argument("--data-dir", type=Path, default=Path("var/data"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18767)
    args = parser.parse_args()
    if args.host not in ("127.0.0.1", "localhost", "::1"):
        parser.error("Ce prototype ne peut écouter que sur l'interface locale")
    handler = type("AvantempsHandler", (Handler,), {"data_dir": args.data_dir})
    with ThreadingHTTPServer((args.host, args.port), handler) as server:
        print(f"AVANTEMPS : http://{args.host}:{args.port}/", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()

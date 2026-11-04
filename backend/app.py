"""
Student Service Queue System - Backend REST API
================================================
Studi Kasus 3 - UTS Cloud Computing (Ujian Chunin)

REST API sederhana tanpa framework (hanya Python standard library).
Data antrean disimpan ke file JSON di dalam Docker Named Volume
(default: /var/lib/backend_data/queue.json -> volume `queue-db-data`).

Endpoint:
    GET    /queue            -> daftar antrean
    POST   /queue            -> ambil nomor antrean baru (body JSON)
    DELETE /queue?index=0    -> panggil / selesaikan antrean pada index X
    GET    /health           -> health check (dipakai Jenkins & Docker)
"""

import json
import os
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8000"))
DATA_DIR = os.environ.get("DATA_DIR", "/var/lib/backend_data")
DATA_FILE = os.path.join(DATA_DIR, "queue.json")
APP_VERSION = os.environ.get("APP_VERSION", "dev")
MAX_BODY_BYTES = 10 * 1024

# Kode layanan LAA -> prefix nomor tiket (contoh: A001, K002)
SERVICES = {
    "akademik": {"prefix": "A", "label": "Akademik (LAA)"},
    "keuangan": {"prefix": "K", "label": "Keuangan"},
    "kemahasiswaan": {"prefix": "M", "label": "Kemahasiswaan"},
    "umum": {"prefix": "U", "label": "Informasi Umum"},
}

_lock = threading.Lock()


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _empty_store():
    return {"last_number": 0, "last_called": None, "queue": []}


def load_store():
    """Baca queue.json dari volume. Jika belum ada / rusak, mulai dari kosong."""
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or not isinstance(data.get("queue"), list):
            return _empty_store()
        data.setdefault("last_number", 0)
        data.setdefault("last_called", None)
        return data
    except (FileNotFoundError, json.JSONDecodeError):
        return _empty_store()


def save_store(data):
    """Tulis secara atomic (tulis ke file sementara lalu rename)."""
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp_path = DATA_FILE + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, DATA_FILE)


class QueueHandler(BaseHTTPRequestHandler):
    server_version = "QueueAPI/1.0"

    # ---------- helper ----------
    def _send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _error(self, status, message):
        self._send_json(status, {"status": "error", "code": status, "message": message})

    def _route(self):
        parsed = urlparse(self.path)
        return parsed.path.rstrip("/") or "/", parse_qs(parsed.query)

    def log_message(self, fmt, *args):
        print("[%s] %s - %s" % (_now(), self.address_string(), fmt % args), flush=True)

    # ---------- HTTP methods ----------
    def do_OPTIONS(self):
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def do_GET(self):
        path, _ = self._route()
        if path == "/health":
            return self._health()
        if path == "/queue":
            with _lock:
                data = load_store()
            return self._send_json(200, {
                "status": "success",
                "count": len(data["queue"]),
                "last_called": data["last_called"],
                "data": data["queue"],
            })
        if path == "/":
            return self._send_json(200, {
                "service": "Student Service Queue API",
                "version": APP_VERSION,
                "endpoints": ["GET /queue", "POST /queue", "DELETE /queue?index=0", "GET /health"],
            })
        return self._error(404, "Endpoint '%s' tidak ditemukan" % path)

    def do_POST(self):
        path, _ = self._route()
        if path != "/queue":
            if path in ("/health", "/"):
                return self._error(405, "Method POST tidak diizinkan pada '%s'" % path)
            return self._error(404, "Endpoint '%s' tidak ditemukan" % path)

        try:
            length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            return self._error(400, "Header Content-Length tidak valid")
        if length <= 0:
            return self._error(400, "Body request kosong, kirim JSON {\"name\": ..., \"service\": ...}")
        if length > MAX_BODY_BYTES:
            return self._error(413, "Body request terlalu besar")

        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return self._error(400, "Format JSON tidak valid")
        if not isinstance(payload, dict):
            return self._error(400, "Body JSON harus berupa object")

        name = payload.get("name")
        if not isinstance(name, str) or not name.strip():
            return self._error(400, "Field 'name' wajib diisi")
        name = name.strip()
        if len(name) > 100:
            return self._error(400, "Field 'name' maksimal 100 karakter")

        nim = payload.get("nim", "")
        if nim is None:
            nim = ""
        if not isinstance(nim, str) or (nim.strip() and not nim.strip().isdigit()) or len(nim.strip()) > 20:
            return self._error(400, "Field 'nim' harus berupa angka (maks. 20 digit)")
        nim = nim.strip()

        service = payload.get("service", "akademik")
        if service not in SERVICES:
            return self._error(400, "Field 'service' harus salah satu dari: %s" % ", ".join(SERVICES))

        with _lock:
            data = load_store()
            data["last_number"] += 1
            entry = {
                "ticket": "%s%03d" % (SERVICES[service]["prefix"], data["last_number"]),
                "number": data["last_number"],
                "name": name,
                "nim": nim,
                "service": service,
                "service_label": SERVICES[service]["label"],
                "created_at": _now(),
            }
            data["queue"].append(entry)
            save_store(data)
            position = len(data["queue"])

        return self._send_json(201, {
            "status": "success",
            "message": "Nomor antrean %s berhasil diambil" % entry["ticket"],
            "position": position,
            "data": entry,
        })

    def do_DELETE(self):
        path, query = self._route()
        if path != "/queue":
            if path in ("/health", "/"):
                return self._error(405, "Method DELETE tidak diizinkan pada '%s'" % path)
            return self._error(404, "Endpoint '%s' tidak ditemukan" % path)

        if "index" not in query:
            return self._error(400, "Parameter 'index' wajib diisi, contoh: /queue?index=0")
        try:
            index = int(query["index"][0])
        except ValueError:
            return self._error(400, "Parameter 'index' harus berupa bilangan bulat")
        if index < 0:
            return self._error(400, "Parameter 'index' tidak boleh negatif")

        with _lock:
            data = load_store()
            if index >= len(data["queue"]):
                return self._error(404, "Antrean pada index %d tidak ditemukan (jumlah antrean: %d)"
                                   % (index, len(data["queue"])))
            removed = data["queue"].pop(index)
            removed["called_at"] = _now()
            # index 0 = antrean terdepan dipanggil ke loket
            if index == 0:
                data["last_called"] = removed
            save_store(data)
            remaining = len(data["queue"])

        action = "dipanggil" if index == 0 else "dihapus dari antrean"
        return self._send_json(200, {
            "status": "success",
            "message": "Antrean %s (%s) %s" % (removed["ticket"], removed["name"], action),
            "remaining": remaining,
            "data": removed,
        })

    # ---------- health ----------
    def _health(self):
        try:
            os.makedirs(DATA_DIR, exist_ok=True)
            writable = os.access(DATA_DIR, os.W_OK)
        except OSError:
            writable = False
        status = 200 if writable else 503
        self._send_json(status, {
            "status": "ok" if writable else "degraded",
            "version": APP_VERSION,
            "storage": DATA_FILE,
            "storage_writable": writable,
            "time": _now(),
        })


def run():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(DATA_FILE):
        save_store(_empty_store())
    server = ThreadingHTTPServer((HOST, PORT), QueueHandler)
    print("Queue API v%s listening on http://%s:%d (data: %s)" % (APP_VERSION, HOST, PORT, DATA_FILE), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    run()

"""Unit test API antrean (dijalankan di stage 'Syntax Check' Jenkins).

Jalankan:  python -m unittest discover -s backend/tests -v
"""

import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

TMP_DIR = tempfile.mkdtemp()
os.environ["DATA_DIR"] = TMP_DIR
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import app  # noqa: E402


class QueueApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), app.QueueHandler)
        cls.base = "http://127.0.0.1:%d" % cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        app.save_store(app._empty_store())

    def request(self, method, path, body=None, raw=None):
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        req = urllib.request.Request(self.base + path, data=data, method=method,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_health(self):
        status, body = self.request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")

    def test_full_flow(self):
        status, body = self.request("GET", "/queue")
        self.assertEqual((status, body["count"]), (200, 0))

        status, body = self.request("POST", "/queue", {"name": "Budi", "nim": "1301220001", "service": "akademik"})
        self.assertEqual(status, 201)
        self.assertEqual(body["data"]["ticket"], "A001")
        status, body = self.request("POST", "/queue", {"name": "Sari", "service": "keuangan"})
        self.assertEqual(body["data"]["ticket"], "K002")
        self.assertEqual(body["position"], 2)

        status, body = self.request("DELETE", "/queue?index=0")
        self.assertEqual(status, 200)
        self.assertEqual(body["data"]["name"], "Budi")

        status, body = self.request("GET", "/queue")
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["last_called"]["ticket"], "A001")

        # data tersimpan di file JSON
        with open(app.DATA_FILE, encoding="utf-8") as f:
            self.assertEqual(json.load(f)["queue"][0]["name"], "Sari")

    def test_number_keeps_increasing_after_delete(self):
        self.request("POST", "/queue", {"name": "A"})
        self.request("DELETE", "/queue?index=0")
        _, body = self.request("POST", "/queue", {"name": "B"})
        self.assertEqual(body["data"]["number"], 2)

    def test_post_errors(self):
        self.assertEqual(self.request("POST", "/queue", raw=b"{bukan json")[0], 400)
        self.assertEqual(self.request("POST", "/queue", ["list"])[0], 400)
        self.assertEqual(self.request("POST", "/queue", {"name": "  "})[0], 400)
        self.assertEqual(self.request("POST", "/queue", {"name": "X", "nim": "abc"})[0], 400)
        self.assertEqual(self.request("POST", "/queue", {"name": "X", "service": "parkir"})[0], 400)

    def test_delete_errors(self):
        self.assertEqual(self.request("DELETE", "/queue")[0], 400)
        self.assertEqual(self.request("DELETE", "/queue?index=abc")[0], 400)
        self.assertEqual(self.request("DELETE", "/queue?index=-1")[0], 400)
        self.assertEqual(self.request("DELETE", "/queue?index=0")[0], 404)

    def test_unknown_route(self):
        self.assertEqual(self.request("GET", "/tidak-ada")[0], 404)
        self.assertEqual(self.request("POST", "/health", {})[0], 405)


if __name__ == "__main__":
    unittest.main()

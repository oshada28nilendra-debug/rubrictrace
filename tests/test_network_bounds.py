import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from rubrictrace import core, provider


class SlowHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        self.rfile.read(int(self.headers["Content-Length"]))
        self.send_response(200)
        self.end_headers()
        try:
            for _ in range(100):
                self.wfile.write(b"x")
                self.wfile.flush()
                time.sleep(0.025)
        except (OSError, ValueError):
            pass


class NetworkBounds(unittest.TestCase):
    def test_slow_drip_respects_absolute_deadline(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), SlowHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            m = provider.Model(
                "simulated", endpoint=f"http://127.0.0.1:{server.server_port}/v1", timeout=0.12
            )
            start = time.monotonic()
            with self.assertRaises(core.Error):
                m.complete({})
            self.assertLess(time.monotonic() - start, 1)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

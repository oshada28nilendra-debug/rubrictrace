import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch
from rubrictrace import core, provider
from rubrictrace.files import read_json
from tests.test_core_review import assessment


class Handler(BaseHTTPRequestHandler):
    status = 200
    payload = b'{"choices":[{"message":{"content":"{\\"items\\":[]}"}}],"usage":{"prompt_tokens":3,"completion_tokens":2}}'
    seen = []

    def log_message(self, *args):
        pass

    def do_POST(self):
        self.seen.append(
            (
                self.path,
                self.headers.get("Authorization"),
                json.loads(self.rfile.read(int(self.headers["Content-Length"]))),
            )
        )
        self.send_response(self.status)
        self.send_header("Location", "/must-not-follow")
        self.end_headers()
        try:
            self.wfile.write(self.payload)
        except (BrokenPipeError, ConnectionResetError):
            pass


class ProviderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.endpoint = f"http://127.0.0.1:{cls.server.server_port}/v1"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        Handler.status = 200
        Handler.payload = b'{"choices":[{"message":{"content":"{\\"items\\":[]}"}}],"usage":{"prompt_tokens":3,"completion_tokens":2}}'
        Handler.seen.clear()

    def test_http_contract_budget(self):
        m = provider.Model("test-double", endpoint=self.endpoint, max_calls=1)
        self.assertEqual(m.complete({"answer": "fictional"}), {"items": []})
        self.assertEqual(m.usage["prompt_tokens"], 3)
        self.assertEqual(Handler.seen[0][0], "/v1/chat/completions")
        with self.assertRaises(core.Error):
            m.complete({})
        self.assertEqual(len(Handler.seen), 1)

    def test_auth_environment(self):
        with patch.dict(os.environ, {"RUBRICTRACE_API_KEY": "fixture-not-a-real-credential"}):
            provider.Model("test-double", endpoint=self.endpoint).complete({})
        self.assertEqual(Handler.seen[0][1], "Bearer fixture-not-a-real-credential")
        self.assertNotIn("fixture-not-a-real-credential", json.dumps(Handler.seen[0][2]))

    def test_error_body_and_redirect(self):
        for status in [401, 429, 500, 302]:
            Handler.status = status
            Handler.payload = b"PRIVATE SERVER ERROR"
            with self.assertRaises(core.Error) as e:
                provider.Model("test-double", endpoint=self.endpoint).complete({})
            self.assertNotIn("PRIVATE", str(e.exception))
        self.assertEqual(len(Handler.seen), 4)

    def test_malformed(self):
        for raw in [b"not JSON", b"{}", b'{"choices":[]}', b'{"choices":[{"message":{"content":"[]"}}]}']:
            Handler.payload = raw
            with self.assertRaises(core.Error):
                provider.Model("test-double", endpoint=self.endpoint).complete({})

    def test_response_limit(self):
        Handler.payload = b"x" * 128001
        with self.assertRaises(core.Error):
            provider.Model("test-double", endpoint=self.endpoint).complete({})

    def test_remote_consent(self):
        for endpoint in [
            "http://example.com/v1",
            "https://example.com/v1",
            "http://user:pw@localhost",
            "http://localhost/?key=x",
            "file:///tmp/model",
            "http://localhost:bad/v1",
        ]:
            with self.assertRaises(core.Error):
                provider.Model("x", endpoint=endpoint)
        self.assertEqual(provider.Model("x", endpoint="https://example.com/v1", allow_remote=True).calls, 0)

    def test_header_injection(self):
        with patch.dict(os.environ, {"RUBRICTRACE_API_KEY": "bad\nheader"}):
            with self.assertRaises(core.Error):
                provider.Model("x", endpoint=self.endpoint).complete({})
        self.assertFalse(Handler.seen)

    def test_context_and_config(self):
        for kwargs in [{"timeout": 0}, {"timeout": float("nan")}, {"max_calls": 21}, {"max_calls": True}]:
            with self.assertRaises(core.Error):
                provider.Model("x", **kwargs)
        with self.assertRaises(core.Error):
            provider.Model("x", endpoint=self.endpoint).complete({"answer": "x" * 24001})
        self.assertFalse(Handler.seen)

    def test_unavailable(self):
        s = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        port = s.server_port
        s.server_close()
        with self.assertRaises(core.Error):
            provider.Model("x", endpoint=f"http://127.0.0.1:{port}/v1", timeout=1).complete({})

    def test_partial_failure_retains_all_rows(self):
        m = provider.Model("test-double", endpoint=self.endpoint, max_calls=1)
        p = core.make_pack(assessment(), provider.propose(assessment(), m), "live_model")
        self.assertEqual(len(p["suggestions"]), 4)
        self.assertEqual(sum(r["status"] == "blocked" for r in p["suggestions"]), 2)
        self.assertEqual(m.calls, 1)


class CLITests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, "-m", "rubrictrace", *map(str, args)], capture_output=True, text=True, timeout=15
        )

    def test_json_duplicates_and_size(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "a.json"
            for value in ['{"a":1,"a":2}', '{"a":NaN}', "x" * 2000001]:
                p.write_text(value)
                with self.assertRaises(core.Error):
                    read_json(p)

    @unittest.skipIf(os.name == "nt", "POSIX symlink/FIFO boundary")
    def test_symlink_and_fifo(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "a.json"
            p.write_text("{}")
            s = Path(tmp) / "link"
            s.symlink_to(p)
            with self.assertRaises(core.Error):
                read_json(s)
            p = Path(tmp) / "pipe"
            os.mkfifo(p)
            with self.assertRaises(core.Error):
                read_json(p)

    def test_end_to_end_stale_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "assessment.json"
            source.write_text(json.dumps(assessment()))
            out = root / "pack"
            result = self.run_cli("prepare", source, "--out", out)
            self.assertEqual(result.returncode, 0, result.stderr)
            rev = json.loads((out / "review-template.json").read_text())
            args = [
                "export",
                "--assessment",
                source,
                "--pack",
                out / "pack.json",
                "--review",
                out / "review-template.json",
                "--out",
                root / "bad",
            ]
            self.assertEqual(self.run_cli(*args).returncode, 2)
            self.assertFalse((root / "bad").exists())
            rev.update(reviewer="SCRIPTED-fixture", confirmed=True)
            for d in rev["decisions"]:
                d.update(
                    action="override",
                    level="missing",
                    note="Scripted fixture decision",
                    feedback="Review the rubric.",
                )
            rp = root / "review.json"
            rp.write_text(json.dumps(rev))
            args = [
                "export",
                "--assessment",
                source,
                "--pack",
                out / "pack.json",
                "--review",
                rp,
                "--out",
                root / "final",
            ]
            self.assertEqual(self.run_cli(*args).returncode, 0)
            a = assessment()
            a["submissions"][0]["text"] += "Changed"
            source.write_text(json.dumps(a))
            args[-1] = root / "stale"
            self.assertEqual(self.run_cli(*args).returncode, 2)
            self.assertFalse((root / "stale").exists())

    def test_fixture_label_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "a.json"
            source.write_text(json.dumps(assessment()))
            f = root / "responses.json"
            f.write_text("{}")
            args = ["prepare", source, "--fixture", f, "--out", root / "pack"]
            self.assertEqual(self.run_cli(*args).returncode, 0)
            self.assertEqual(json.loads((root / "pack/pack.json").read_text())["mode"], "fixture")
            self.assertEqual(self.run_cli(*args).returncode, 2)


if __name__ == "__main__":
    unittest.main()

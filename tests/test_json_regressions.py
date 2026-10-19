import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from rubrictrace import core, provider
from rubrictrace.files import loads

ROOT = Path(__file__).resolve().parents[1]


class JSONRegressions(unittest.TestCase):
    def test_simulated_live_response_becomes_blocked_rows(self):
        a = json.loads((ROOT / "fixtures/assessment.json").read_text())
        for raw in ['{"items":[],"unused":1e999}', '{"items":[],"unused":"\\ud800"}']:
            envelope = json.dumps({"choices": [{"message": {"content": raw}}]}).encode()
            with patch("rubrictrace.provider.request_bytes", return_value=(200, {}, envelope)):
                m = provider.Model("labelled-http-test-double", max_calls=2)
                responses = provider.propose(a, m)
            p = core.make_pack(a, responses, "live_model")
            self.assertTrue(all(r["status"] == "blocked" for r in p["suggestions"]))
            self.assertEqual(core.validate_pack(p), p)
            json.dumps(responses, ensure_ascii=False, allow_nan=False).encode()

    def test_nonfinite_and_surrogate_rejected_everywhere(self):
        for raw in ['{"unused":1e999}', '{"unused":"\\ud800"}', '{"\\udfff":1}', '[{"unused":[1e999]}]']:
            with self.subTest(raw=raw), self.assertRaises(core.Error):
                loads(raw)

    def test_fixture_rejected_before_output_and_no_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for i, raw in enumerate(['{"unused":1e999}', '{"unused":"\\ud800"}']):
                f = root / f"bad-{i}.json"
                f.write_text(raw)
                out = root / f"pack-{i}"
                result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "rubrictrace",
                        "prepare",
                        str(ROOT / "fixtures/assessment.json"),
                        "--fixture",
                        str(f),
                        "--out",
                        str(out),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertFalse(out.exists())

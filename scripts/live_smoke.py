"""Real local inference with fictional data and explicitly SCRIPTED moderation."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rubrictrace.core import Error, make_pack  # noqa: E402
from rubrictrace.files import read_json  # noqa: E402
from rubrictrace.httpio import request_bytes  # noqa: E402
from rubrictrace.provider import Model, propose  # noqa: E402
from rubrictrace.report import create_output, render_pack, write_json, write_results  # noqa: E402
from rubrictrace.review import finalize, template  # noqa: E402
from download_model import MODEL_SHA, RUNTIME_SHA  # noqa: E402


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1048576):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if os.environ.get("RUBRICTRACE_API_KEY"):
        raise Error("Unset RUBRICTRACE_API_KEY for this key-free local smoke")
    out = create_output(args.out)
    runtime = args.runtime_root.resolve()
    binary = runtime / "llama-b11718/llama-server"
    if sha(runtime / "model.gguf") != MODEL_SHA or sha(runtime / "runtime.tar.gz") != RUNTIME_SHA:
        raise Error("Runtime/model checksum mismatch")
    command = [
        str(binary),
        "-m",
        str(runtime / "model.gguf"),
        "--host",
        "127.0.0.1",
        "--port",
        "18082",
        "-c",
        "4096",
        "-np",
        "1",
        "-t",
        "4",
        "-ngl",
        "0",
        "--no-webui",
    ]
    env = dict(os.environ)
    env["LD_LIBRARY_PATH"] = str(binary.parent)
    record = {
        "status": "failed",
        "runtime": "llama.cpp b11718",
        "model": "Qwen3-4B Q4_K_M",
        "runtime_archive_sha256": RUNTIME_SHA,
        "model_sha256": MODEL_SHA,
        "executable_sha256": sha(binary),
        "command": command,
        "fixture": "Authored fictional short answers; not a classroom benchmark",
        "review": "SCRIPTED fixture decisions; not an actual teacher review",
        "paid_api_calls": 0,
    }
    with (out / "runtime.log").open("w") as log:
        process = subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 45
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise Error("Local runtime exited during startup")
                try:
                    status, _, _ = request_bytes("http://127.0.0.1:18082/health", timeout=2)
                    if status == 200:
                        break
                except Error:
                    pass
                time.sleep(0.25)
            else:
                raise Error("Local runtime readiness timeout")
            a = read_json(ROOT / "fixtures/assessment.json")
            model = Model("Qwen3-4B-Q4_K_M", max_calls=2)
            responses = propose(a, model)
            p = make_pack(a, responses, "live_model")
            write_json(
                out / "trace.json", {"responses": responses, "calls": model.calls, "usage": model.usage}
            )
            write_json(out / "pack.json", p)
            (out / "review.html").write_text(render_pack(p), encoding="utf-8")
            record.update(
                calls=model.calls,
                usage=model.usage,
                suggested=sum(r["status"] == "suggested" for r in p["suggestions"]),
                blocked=sum(r["status"] == "blocked" for r in p["suggestions"]),
            )
            if model.calls != 2 or record["blocked"]:
                raise Error("Inference failed or call count differs")
            for row in p["suggestions"][:2]:
                if row["status"] != "suggested" or row["level"] != "clear":
                    raise Error("Strong-answer suggestions did not satisfy authored fixture gate")
            expected = {
                ("S001", "cause"): "clear",
                ("S001", "mitigation"): "clear",
                ("S002", "cause"): "partial",
                ("S002", "mitigation"): "missing",
            }
            r = template(p)
            r.update(reviewer="SCRIPTED-fixture-reviewer", confirmed=True)
            for d, suggestion in zip(r["decisions"], p["suggestions"]):
                level = expected[(d["submission_id"], d["criterion_id"])]
                d.update(
                    action="accept"
                    if suggestion["status"] == "suggested" and suggestion["level"] == level
                    else "override",
                    level=level,
                    note="Scripted known-fixture decision; not actual teacher judgement.",
                    feedback="Compare your answer with the stated rubric descriptors.",
                )
            result = finalize(p, r)
            if [s["points"] for s in result["results"]] != [5, 1]:
                raise Error("Fixture scores differ")
            write_json(out / "scripted-review.json", r)
            write_results(result, out / "export")
            record.update(
                status="passed", scores=[5, 1], moderation=result["moderation"], pack_digest=p["digest"]
            )
        except Error as e:
            record["error"] = str(e)
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            write_json(out / "verification.json", record)
    print(json.dumps(record, indent=2))
    return 0 if record["status"] == "passed" else 3


if __name__ == "__main__":
    raise SystemExit(main())

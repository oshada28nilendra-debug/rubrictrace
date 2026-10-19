"""Run and retain actual local release checks; no model or paid API calls."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    results = []

    def run(name, cmd, *, cwd=ROOT, env=None):
        r = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=180)
        (out / f"{name}.log").write_text(r.stdout + r.stderr, encoding="utf-8")
        results.append({"name": name, "command": cmd, "exit_code": r.returncode})
        if r.returncode:
            raise RuntimeError(f"Release check failed: {name}; inspect retained log")

    commands = [
        ("tests", [sys.executable, "-m", "unittest", "-v"]),
        ("lint", [sys.executable, "-m", "ruff", "check", "."]),
        ("format", [sys.executable, "-m", "ruff", "format", "--check", "."]),
        ("compile", [sys.executable, "-m", "compileall", "-q", "rubrictrace", "scripts", "tests"]),
        ("wheel", [sys.executable, "-m", "build", "--wheel"]),
    ]
    try:
        for name, cmd in commands:
            run(name, cmd)
        wheel = next((ROOT / "dist").glob("*.whl"))
        with tempfile.TemporaryDirectory(prefix="rubrictrace-installed-") as tmp:
            tmp = Path(tmp)
            target = tmp / "installed"
            run(
                "install",
                [sys.executable, "-m", "pip", "install", "--no-deps", "--target", str(target), str(wheel)],
            )
            env = dict(os.environ)
            env["PYTHONPATH"] = str(target)
            run("installed-help", [sys.executable, "-m", "rubrictrace", "--help"], cwd=tmp, env=env)
            pack = tmp / "pack"
            run(
                "installed-prepare",
                [
                    sys.executable,
                    "-m",
                    "rubrictrace",
                    "prepare",
                    str(ROOT / "fixtures/assessment.json"),
                    "--fixture",
                    str(ROOT / "delivery/offline-demo/fixture-responses.json"),
                    "--out",
                    str(pack),
                ],
                cwd=tmp,
                env=env,
            )
            review = json.loads((pack / "review-template.json").read_text())
            review.update(reviewer="SCRIPTED-installed-fixture", confirmed=True)
            for d in review["decisions"]:
                d.update(action="accept", feedback="Scripted fixture feedback.")
                if d["submission_id"] == "S002":
                    d.update(
                        action="override",
                        level="partial" if d["criterion_id"] == "cause" else "missing",
                        note="Scripted fixture judgement.",
                    )
            rp = tmp / "review.json"
            rp.write_text(json.dumps(review))
            run(
                "installed-export",
                [
                    sys.executable,
                    "-m",
                    "rubrictrace",
                    "export",
                    "--assessment",
                    str(ROOT / "fixtures/assessment.json"),
                    "--pack",
                    str(pack / "pack.json"),
                    "--review",
                    str(rp),
                    "--out",
                    str(tmp / "export"),
                ],
                cwd=tmp,
                env=env,
            )
            final = json.loads((tmp / "export/results.json").read_text())
            if [s["points"] for s in final["results"]] != [5, 1]:
                raise RuntimeError("Installed scores differ")
            (out / "installed-results.json").write_text(json.dumps(final, indent=2) + "\n")
        record = {
            "status": "passed",
            "python": platform.python_version(),
            "checks": results,
            "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
            "installed_scores": [5, 1],
            "mode": "offline and simulated integration; genuine inference recorded separately",
        }
        (out / "verification.json").write_text(json.dumps(record, indent=2) + "\n")
        print(json.dumps(record, indent=2))
    except Exception:
        (out / "verification.json").write_text(
            json.dumps({"status": "failed", "checks": results}, indent=2) + "\n"
        )
        raise


if __name__ == "__main__":
    main()

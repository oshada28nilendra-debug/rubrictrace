"""Authored offline fixture with SCRIPTED moderation, not a live model."""

import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rubrictrace.files import read_json  # noqa: E402
from rubrictrace.report import create_output, write_json  # noqa: E402


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    out = create_output(args.out).resolve()
    a = read_json(ROOT / "fixtures/assessment.json")
    responses = {
        s["id"]: {
            "items": [
                {
                    "criterion_id": c["id"],
                    "level": "clear",
                    "quote": s["text"],
                    "reason": "DELIBERATELY GENEROUS SCRIPTED FIXTURE. Teacher review may disagree.",
                }
                for c in a["rubric"]
            ]
        }
        for s in a["submissions"]
    }
    write_json(out / "fixture-responses.json", responses)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "rubrictrace",
            "prepare",
            str(ROOT / "fixtures/assessment.json"),
            "--fixture",
            str(out / "fixture-responses.json"),
            "--out",
            str(out / "pack"),
        ],
        check=True,
    )
    r = read_json(out / "pack/review-template.json")
    r.update(reviewer="SCRIPTED-fixture-marker", confirmed=True)
    for d in r["decisions"]:
        if d["submission_id"] == "S001":
            d.update(
                action="accept", feedback="The retry cause and duplicate-handling strategy are explained."
            )
        else:
            d.update(
                action="override",
                level="partial" if d["criterion_id"] == "cause" else "missing",
                note="Scripted fixture judgement; not an actual teacher.",
                feedback="Explain the lost acknowledgement and a suitable mitigation.",
            )
    write_json(out / "scripted-review.json", r)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "rubrictrace",
            "export",
            "--assessment",
            str(ROOT / "fixtures/assessment.json"),
            "--pack",
            str(out / "pack/pack.json"),
            "--review",
            str(out / "scripted-review.json"),
            "--out",
            str(out / "export"),
        ],
        check=True,
    )
    result = read_json(out / "export/results.json")
    assert [s["points"] for s in result["results"]] == [5, 1]
    assert result["moderation"]["overridden"] == 2
    print(json.dumps({"mode": "scripted_offline_fixture", "scores": [5, 1], "overridden": 2}))


if __name__ == "__main__":
    main()

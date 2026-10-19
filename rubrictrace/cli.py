"""Local review preparation and explicit export."""

import argparse
import sys
from pathlib import Path
from .core import Error, digest, make_pack, validate_assessment
from .files import read_json
from .provider import Model, propose
from .report import create_output, render_pack, write_json, write_results
from .review import finalize, template


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="rubrictrace", description="Teacher-moderated formative feedback; never automatic final grades."
    )
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare", help="Private review pack; no final marks")
    prep.add_argument("assessment")
    prep.add_argument("--out", required=True)
    mode = prep.add_mutually_exclusive_group()
    mode.add_argument("--model")
    mode.add_argument("--fixture", help="SCRIPTED test double responses, NOT a live model")
    prep.add_argument("--endpoint", default="http://127.0.0.1:18082/v1")
    prep.add_argument(
        "--allow-remote-model",
        action="store_true",
        help="Consent to answer transfer to chosen HTTPS provider; charges may apply",
    )
    prep.add_argument("--max-calls", type=int, default=10)
    prep.add_argument("--timeout", type=float, default=120)
    exp = sub.add_parser("export", help="Recheck original input, teacher decisions and scores")
    for name in ["assessment", "pack", "review", "out"]:
        exp.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        assessment = validate_assessment(read_json(args.assessment))
        if args.command == "prepare":
            if Path(args.out).exists():
                raise Error("Output directory must be new")
            if args.model:
                model = Model(
                    args.model,
                    endpoint=args.endpoint,
                    allow_remote=args.allow_remote_model,
                    max_calls=args.max_calls,
                    timeout=args.timeout,
                )
                responses = propose(assessment, model)
                mode, calls, usage = "live_model", model.calls, model.usage
            elif args.fixture:
                responses, mode, calls, usage = read_json(args.fixture), "fixture", 0, {}
            else:
                responses, mode, calls, usage = {}, "manual", 0, {}
            pack = make_pack(assessment, responses, mode)
            out = create_output(args.out)
            write_json(out / "pack.json", pack)
            write_json(out / "review-template.json", template(pack))
            write_json(
                out / "trace.json", {"mode": mode, "calls": calls, "usage": usage, "responses": responses}
            )
            (out / "review.html").write_text(render_pack(pack), encoding="utf-8")
            blocked = sum(r["status"] == "blocked" for r in pack["suggestions"])
            print(
                f"Prepared {mode} review pack; {calls} model requests; {blocked} blocked rows. No final grades."
            )
            return 3 if blocked else 0
        pack = read_json(args.pack)
        if not isinstance(pack, dict) or digest(assessment) != pack.get("assessment_digest"):
            raise Error("Original assessment changed or pack invalid; prepare a fresh pack")
        result = finalize(pack, read_json(args.review))
        write_results(result, args.out)
        print(f"Exported {len(result['results'])} teacher-reviewed results; no LMS publication performed.")
        return 0
    except (Error, OSError) as e:
        print("rubrictrace: " + str(e), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

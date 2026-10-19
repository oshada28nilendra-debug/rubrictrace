"""Explicit teacher moderation, independent of model arithmetic."""

import copy
from decimal import Decimal, ROUND_HALF_UP
from .core import Error, digest, exact, text, validate_pack


def template(pack):
    validate_pack(pack)
    return {
        "schema": 1,
        "pack_digest": pack["digest"],
        "reviewer": "",
        "confirmed": False,
        "decisions": [
            {
                "submission_id": r["submission_id"],
                "criterion_id": r["criterion_id"],
                "action": "pending",
                "level": r["level"],
                "feedback": "",
                "note": "",
            }
            for r in pack["suggestions"]
        ],
    }


def finalize(pack, review):
    validate_pack(pack)
    exact(review, {"schema", "pack_digest", "reviewer", "confirmed", "decisions"})
    if type(review["schema"]) is not int or review["schema"] != 1 or review["confirmed"] is not True:
        raise Error("Explicit review confirmation is required")
    text(review["reviewer"], 120)
    if review["pack_digest"] != pack["digest"]:
        raise Error("Stale review: pack digest differs")
    if not isinstance(review["decisions"], list) or len(review["decisions"]) != len(pack["suggestions"]):
        raise Error("Review must decide every criterion")
    decisions = {}
    for d in review["decisions"]:
        exact(d, {"submission_id", "criterion_id", "action", "level", "feedback", "note"})
        text(d["submission_id"], 64)
        text(d["criterion_id"], 64)
        key = (d["submission_id"], d["criterion_id"])
        if key in decisions:
            raise Error("Duplicate review decision")
        decisions[key] = d
    a = pack["assessment"]
    maximum = sum(max(level["points"] for level in c["levels"]) for c in a["rubric"])
    stats = {
        "accepted": 0,
        "overridden": 0,
        "withheld": 0,
        "criteria": {
            c["id"]: {
                "accepted": 0,
                "overridden": 0,
                "withheld": 0,
                "model_suggested": 0,
                "overrode_suggestion": 0,
            }
            for c in a["rubric"]
        },
    }
    by_student = {s["id"]: [] for s in a["submissions"]}
    criteria = {c["id"]: c for c in a["rubric"]}
    for suggestion in pack["suggestions"]:
        key = (suggestion["submission_id"], suggestion["criterion_id"])
        if key not in decisions:
            raise Error("Missing or unknown review decision")
        d = decisions[key]
        action = d["action"]
        if not isinstance(action, str) or action not in {"accept", "override", "withhold"}:
            raise Error("Every criterion needs accept, override or withhold")
        text(d["feedback"], 2400, blank=action == "withhold")
        text(d["note"], 1600, blank=action == "accept")
        levels = {level["id"]: level["points"] for level in criteria[key[1]]["levels"]}
        if action == "accept" and (suggestion["status"] != "suggested" or d["level"] != suggestion["level"]):
            raise Error("Accept requires unchanged validated suggestion; use override for edits")
        if action != "withhold" and (not isinstance(d["level"], str) or d["level"] not in levels):
            raise Error("Unknown teacher-selected level")
        if action == "withhold" and d["level"] is not None:
            raise Error("A withheld criterion has no level")
        statkey = {"accept": "accepted", "override": "overridden", "withhold": "withheld"}[action]
        stats[statkey] += 1
        cs = stats["criteria"][key[1]]
        cs[statkey] += 1
        if suggestion["status"] == "suggested":
            cs["model_suggested"] += 1
            if action == "override":
                cs["overrode_suggestion"] += 1
        by_student[key[0]].append(
            {
                "criterion_id": key[1],
                "action": action,
                "level": d["level"],
                "points": levels[d["level"]] if action != "withhold" else None,
                "feedback": d["feedback"],
            }
        )
    results = []
    for sid, rows in by_student.items():
        withheld = any(r["action"] == "withhold" for r in rows)
        points = None if withheld else sum(r["points"] for r in rows)
        percentage = (
            None
            if withheld
            else str(
                (Decimal(points) * 100 / Decimal(maximum)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            )
        )
        results.append(
            {
                "submission_id": sid,
                "status": "withheld" if withheld else "reviewed",
                "points": points,
                "maximum": maximum,
                "percentage": percentage,
                "criteria": rows,
            }
        )
    for cs in stats["criteria"].values():
        cs["override_rate"] = (
            str((Decimal(cs["overrode_suggestion"]) / cs["model_suggested"]).quantize(Decimal("0.001")))
            if cs["model_suggested"]
            else None
        )
    return {
        "schema": 1,
        "title": a["title"],
        "pack_digest": pack["digest"],
        "review_digest": digest(review),
        "reviewer": review["reviewer"],
        "results": results,
        "moderation": stats,
        "audit": {"pack": copy.deepcopy(pack), "review": copy.deepcopy(review)},
    }

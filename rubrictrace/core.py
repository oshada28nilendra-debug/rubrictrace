"""Finite assessment schema and exact quotation integrity."""

import copy
import hashlib
import json
import re


class Error(Exception):
    """Expected operational or validation error."""


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def exact(obj, keys):
    if not isinstance(obj, dict) or set(obj) != set(keys):
        raise Error("Missing or unsupported fields")


def text(value, maximum, *, blank=False):
    if not isinstance(value, str) or len(value) > maximum or (not blank and not value.strip()):
        raise Error("Invalid text field or text limit exceeded")
    if any(ord(c) < 32 and c not in "\n\r\t" for c in value) or any(
        0xD800 <= ord(c) <= 0xDFFF for c in value
    ):
        raise Error("Unsupported control or Unicode surrogate")
    return value


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", value):
        raise Error("Use an opaque alphanumeric ID up to 64 characters")
    return value


def unique(items):
    ids = [identifier(i.get("id")) if isinstance(i, dict) else None for i in items]
    if None in ids or len(ids) != len(set(ids)):
        raise Error("Duplicate or invalid IDs")


def validate_assessment(a):
    exact(a, {"schema", "title", "prompt", "rubric", "submissions"})
    if type(a["schema"]) is not int or a["schema"] != 1:
        raise Error("Unsupported assessment schema")
    text(a["title"], 200)
    text(a["prompt"], 4000)
    if not isinstance(a["rubric"], list) or not 1 <= len(a["rubric"]) <= 8:
        raise Error("Assessment needs 1–8 rubric criteria")
    unique(a["rubric"])
    for c in a["rubric"]:
        exact(c, {"id", "description", "levels"})
        text(c["description"], 1200)
        if not isinstance(c["levels"], list) or not 2 <= len(c["levels"]) <= 6:
            raise Error("Each criterion needs 2–6 levels")
        unique(c["levels"])
        for level in c["levels"]:
            exact(level, {"id", "points", "description"})
            text(level["description"], 1200)
            if type(level["points"]) is not int or not 0 <= level["points"] <= 100:
                raise Error("Level points must be integers from 0 to 100")
        scores = [level["points"] for level in c["levels"]]
        if min(scores) != 0 or max(scores) == 0:
            raise Error("Each criterion requires zero and a positive maximum")
    if not isinstance(a["submissions"], list) or not 1 <= len(a["submissions"]) <= 100:
        raise Error("Assessment needs 1–100 submissions")
    unique(a["submissions"])
    for s in a["submissions"]:
        exact(s, {"id", "text"})
        text(s["text"], 8000, blank=True)
    if len(canonical(a).encode()) > 2_000_000:
        raise Error("Assessment exceeds 2 MB")
    return a


def answer_passages(answer):
    """Finite contiguous answer passages; never rubric-derived evidence."""
    pieces = [m.group().strip() for m in re.finditer(r"[^\n.!?]+[.!?]*|[.!?]+", answer)]
    pieces = [p for p in pieces if p]
    if len(pieces) > 32:
        pieces = [answer[i : i + 500] for i in range(0, len(answer), 500)]
    return [{"id": f"a{i + 1}", "text": p} for i, p in enumerate(pieces)]


def _row(s, c, response, mode):
    row = {
        "submission_id": s["id"],
        "criterion_id": c["id"],
        "status": "abstained",
        "level": None,
        "quote": "",
        "span": None,
        "reason": "No validated suggestion; review manually.",
        "answer_digest": digest(s["text"]),
    }
    if mode == "manual":
        return row
    if isinstance(response, dict) and "error" in response:
        row.update(status="blocked", reason="Model request failed or budget exhausted; review manually.")
        return row
    try:
        exact(response, {"items"})
        if not isinstance(response["items"], list) or len(response["items"]) > 16:
            raise Error("Invalid suggestion collection")
        candidates = [
            x for x in response["items"] if isinstance(x, dict) and x.get("criterion_id") == c["id"]
        ]
        if len(candidates) != 1:
            raise Error("Missing or duplicated criterion")
        x = candidates[0]
        if set(x) == {"criterion_id", "level", "evidence_id", "reason"}:
            passages = {p["id"]: p["text"] for p in answer_passages(s["text"])}
            evidence_id = x["evidence_id"]
            if evidence_id is None and x["level"] is None:
                quote = ""
            elif not isinstance(evidence_id, str) or evidence_id not in passages:
                raise Error("Unknown answer evidence ID")
            else:
                quote = passages[evidence_id]
            x = {
                "criterion_id": x["criterion_id"],
                "level": x["level"],
                "quote": quote,
                "reason": x["reason"],
            }
        exact(x, {"criterion_id", "level", "quote", "reason"})
        text(x["reason"], 1600)
        if x["level"] is None:
            row["reason"] = x["reason"]
            return row
        if not isinstance(x["level"], str) or x["level"] not in [level["id"] for level in c["levels"]]:
            raise Error("Unknown rubric level")
        quote = text(x["quote"], 8000)
        start = s["text"].find(quote)
        if start < 0:
            raise Error("Quotation is absent from the answer")
        row.update(
            status="suggested",
            level=x["level"],
            quote=quote,
            span={"start": start, "end": start + len(quote)},
            reason=x["reason"],
        )
    except Error as e:
        row["reason"] = "Suggestion rejected: " + str(e)
    return row


def make_pack(assessment, responses, mode):
    validate_assessment(assessment)
    if (
        not isinstance(mode, str)
        or mode not in {"manual", "fixture", "live_model"}
        or not isinstance(responses, dict)
    ):
        raise Error("Invalid preparation mode")
    a = copy.deepcopy(assessment)
    p = {
        "schema": 1,
        "mode": mode,
        "assessment": a,
        "assessment_digest": digest(a),
        "suggestions": [
            _row(s, c, responses.get(s["id"]), mode) for s in a["submissions"] for c in a["rubric"]
        ],
    }
    p["digest"] = digest(p)
    # Match write_json's actual formatted bytes, not only canonical hash bytes.
    if len((json.dumps(p, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode()) > 2_000_000:
        raise Error("Review pack exceeds 2 MB; use a smaller batch or shorter evidence quotes")
    return p


def validate_pack(p):
    exact(p, {"schema", "mode", "assessment", "assessment_digest", "suggestions", "digest"})
    if (
        type(p["schema"]) is not int
        or p["schema"] != 1
        or not isinstance(p["mode"], str)
        or p["mode"] not in {"manual", "fixture", "live_model"}
    ):
        raise Error("Invalid review pack")
    a = validate_assessment(p["assessment"])
    if p["assessment_digest"] != digest(a) or p["digest"] != digest(
        {k: v for k, v in p.items() if k != "digest"}
    ):
        raise Error("Pack content changed; prepare a fresh pack and review")
    expected = [(s, c) for s in a["submissions"] for c in a["rubric"]]
    if not isinstance(p["suggestions"], list) or len(p["suggestions"]) != len(expected):
        raise Error("Incomplete suggestion matrix")
    for row, (s, c) in zip(p["suggestions"], expected):
        exact(
            row,
            {"submission_id", "criterion_id", "status", "level", "quote", "span", "reason", "answer_digest"},
        )
        if (row["submission_id"], row["criterion_id"], row["answer_digest"]) != (
            s["id"],
            c["id"],
            digest(s["text"]),
        ):
            raise Error("Evidence source mismatch")
        text(row["reason"], 1800)
        if row["status"] == "suggested":
            if p["mode"] == "manual":
                raise Error("Manual packs cannot contain model suggestions")
            rebuilt = _row(
                s,
                c,
                {"items": [{k: row[k] for k in ["criterion_id", "level", "quote", "reason"]}]},
                "fixture",
            )
            if rebuilt != row:
                raise Error("Evidence span or level is invalid")
        elif (
            not isinstance(row["status"], str)
            or row["status"] not in {"abstained", "blocked"}
            or row["level"] is not None
            or row["quote"] != ""
            or row["span"] is not None
        ):
            raise Error("Invalid abstention")
    return p

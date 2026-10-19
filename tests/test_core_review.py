import copy
import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
from rubrictrace import core, review, report

ROOT = Path(__file__).resolve().parents[1]


def assessment():
    return json.loads((ROOT / "fixtures/assessment.json").read_text())


def responses(a):
    return {
        s["id"]: {
            "items": [
                {
                    "criterion_id": c["id"],
                    "level": c["levels"][-1]["id"],
                    "quote": s["text"],
                    "reason": "Inspect this scripted suggestion.",
                }
                for c in a["rubric"]
            ]
        }
        for s in a["submissions"]
    }


def pack():
    a = assessment()
    return core.make_pack(a, responses(a), "fixture")


def accepted(p):
    r = review.template(p)
    r.update(reviewer="SCRIPTED-fixture-marker", confirmed=True)
    for d in r["decisions"]:
        d.update(action="accept", feedback="Reviewed fictional feedback.")
    return r


class CoreTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(core.validate_assessment(assessment()), assessment())

    def test_duplicate_ids(self):
        for field in ["rubric", "submissions"]:
            a = assessment()
            a[field].append(copy.deepcopy(a[field][0]))
            with self.assertRaises(core.Error):
                core.validate_assessment(a)

    def test_unsafe_ids(self):
        for value in ["../secret", "=1+1", "", "student@example.com"]:
            a = assessment()
            a["submissions"][0]["id"] = value
            with self.assertRaises(core.Error):
                core.validate_assessment(a)

    def test_points(self):
        for value in [-1, 101, True, 1.5, "2"]:
            a = assessment()
            a["rubric"][0]["levels"][0]["points"] = value
            with self.assertRaises(core.Error):
                core.validate_assessment(a)

    def test_rubric_range(self):
        for points in [[1, 2, 3], [0, 0, 0]]:
            a = assessment()
            for level, point in zip(a["rubric"][0]["levels"], points):
                level["points"] = point
            with self.assertRaises(core.Error):
                core.validate_assessment(a)

    def test_blank_answer(self):
        a = assessment()
        a["submissions"][0]["text"] = ""
        p = core.make_pack(a, {}, "manual")
        self.assertTrue(all(x["level"] is None for x in p["suggestions"]))

    def test_schema_and_bounds(self):
        for change in [{"schema": True}, {"extra": "bad"}, {"submissions": []}, {"prompt": ""}]:
            a = assessment()
            a.update(change)
            with self.assertRaises(core.Error):
                core.validate_assessment(a)
        a = assessment()
        a["submissions"][0]["text"] = "x" * 8001
        with self.assertRaises(core.Error):
            core.validate_assessment(a)

    def test_unicode_offsets(self):
        a = assessment()
        a["submissions"][0]["text"] = "é🙂 retry é🙂 retry"
        r = responses(a)
        r["S001"]["items"][0]["quote"] = "é🙂"
        p = core.make_pack(a, r, "fixture")
        self.assertEqual(p["suggestions"][0]["span"], {"start": 0, "end": 2})
        self.assertEqual(core.validate_pack(p), p)

    def test_invented_quote(self):
        a = assessment()
        r = responses(a)
        r["S001"]["items"][0]["quote"] = "Invented text"
        p = core.make_pack(a, r, "fixture")
        self.assertEqual(p["suggestions"][0]["status"], "abstained")

    def test_bad_model_fields(self):
        for changes in [{"level": "excellent"}, {"score": 100}, {"reason": ""}, {"quote": ""}]:
            a = assessment()
            r = responses(a)
            r["S001"]["items"][0].update(changes)
            self.assertEqual(core.make_pack(a, r, "fixture")["suggestions"][0]["status"], "abstained")

    def test_duplicate_suggestions(self):
        a = assessment()
        r = responses(a)
        r["S001"]["items"].append(r["S001"]["items"][0])
        self.assertEqual(core.make_pack(a, r, "fixture")["suggestions"][0]["status"], "abstained")

    def test_missing_model_rows(self):
        p = core.make_pack(assessment(), {}, "live_model")
        self.assertEqual(len(p["suggestions"]), 4)
        self.assertTrue(all(x["status"] == "abstained" for x in p["suggestions"]))

    def test_tampered_pack(self):
        for field in ["source", "span", "level"]:
            t = pack()
            if field == "source":
                t["assessment"]["prompt"] += "changed"
            elif field == "span":
                t["suggestions"][0]["span"]["start"] = 9
            else:
                t["suggestions"][0]["level"] = "fake"
            t["digest"] = core.digest({k: v for k, v in t.items() if k != "digest"})
            with self.assertRaises(core.Error):
                core.validate_pack(t)

    def test_manual_is_not_ai(self):
        p = core.make_pack(assessment(), {}, "manual")
        self.assertEqual(p["mode"], "manual")
        self.assertTrue(all(x["level"] is None for x in p["suggestions"]))


class ReviewTests(unittest.TestCase):
    def test_pending(self):
        p = pack()
        r = review.template(p)
        self.assertFalse(r["confirmed"])
        with self.assertRaises(core.Error):
            review.finalize(p, r)

    def test_confirmation_alias_complete(self):
        p = pack()
        for change in [{"confirmed": False}, {"confirmed": 1}, {"reviewer": ""}, {"decisions": []}]:
            r = accepted(p)
            r.update(change)
            with self.assertRaises(core.Error):
                review.finalize(p, r)

    def test_stale_digest(self):
        p = pack()
        r = accepted(p)
        r["pack_digest"] = "0" * 64
        with self.assertRaises(core.Error):
            review.finalize(p, r)

    def test_score_and_override(self):
        p = pack()
        r = accepted(p)
        r["decisions"][2].update(action="override", level="partial", note="Acknowledgement not explained.")
        r["decisions"][3].update(action="override", level="missing", note="Not a relevant mitigation.")
        result = review.finalize(p, r)
        self.assertEqual([s["points"] for s in result["results"]], [5, 1])
        self.assertEqual([s["percentage"] for s in result["results"]], ["100.00", "20.00"])
        self.assertEqual(result["moderation"]["overridden"], 2)
        self.assertEqual(result["moderation"]["criteria"]["cause"]["override_rate"], "0.500")

    def test_override_note_and_level(self):
        p = pack()
        for change in [{"level": "fake", "note": "reason"}, {"level": "missing", "note": ""}]:
            r = accepted(p)
            r["decisions"][0].update(action="override", **change)
            with self.assertRaises(core.Error):
                review.finalize(p, r)

    def test_accept_no_silent_edit(self):
        p = pack()
        r = accepted(p)
        r["decisions"][0]["level"] = "missing"
        with self.assertRaises(core.Error):
            review.finalize(p, r)

    def test_withhold_no_partial_grade(self):
        p = pack()
        r = accepted(p)
        r["decisions"][0].update(action="withhold", level=None, note="Second marker needed")
        s = review.finalize(p, r)["results"][0]
        self.assertIsNone(s["points"])
        self.assertIsNone(s["percentage"])
        self.assertEqual(s["status"], "withheld")

    def test_duplicate_decisions(self):
        p = pack()
        r = accepted(p)
        r["decisions"][1] = r["decisions"][0]
        with self.assertRaises(core.Error):
            review.finalize(p, r)

    def test_manual_override(self):
        p = core.make_pack(assessment(), {}, "manual")
        r = accepted(p)
        with self.assertRaises(core.Error):
            review.finalize(p, r)
        for d in r["decisions"]:
            d.update(action="override", level="missing", note="Manually checked fixture")
        self.assertEqual(review.finalize(p, r)["results"][0]["points"], 0)

    def test_html_inert(self):
        a = assessment()
        a["title"] = "</title><script>alert(1)</script>"
        a["submissions"][0]["text"] = '<img src=x onerror="alert(1)">'
        p = core.make_pack(a, responses(a), "fixture")
        html = report.render_pack(p)
        self.assertNotIn("<script", html)
        self.assertNotIn("<img", html)
        self.assertIn("&lt;img", html)
        self.assertLess(html.index("<h3>Student response"), html.index("<h3>AI suggestion"))
        self.assertIn("No final score", html)

    def test_exports_and_overwrite(self):
        p = pack()
        r = accepted(p)
        r["decisions"][0]["feedback"] = '=HYPERLINK("https://invalid.example")'
        result = review.finalize(p, r)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "export"
            report.write_results(result, out)
            rows = list(csv.DictReader(io.StringIO((out / "scores.csv").read_text())))
            self.assertEqual(rows[0]["submission_id"], "S001")
            self.assertTrue(rows[0]["feedback"].startswith("'="))
            self.assertEqual(json.loads((out / "results.json").read_text())["results"][0]["points"], 5)
            with self.assertRaises(core.Error):
                report.write_results(result, out)


class LimitTests(unittest.TestCase):
    def test_quote_heavy_pack_stays_readable(self):
        a = assessment()
        criterion = a["rubric"][0]
        a["rubric"] = [dict(copy.deepcopy(criterion), id=f"c{i}") for i in range(8)]
        a["submissions"] = [{"id": f"S{i:03d}", "text": "x" * 8000} for i in range(100)]
        with self.assertRaises(core.Error):
            core.make_pack(a, responses(a), "fixture")

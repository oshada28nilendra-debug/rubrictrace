import unittest
from rubrictrace import core
from tests.test_core_review import assessment


class PassageTests(unittest.TestCase):
    def test_model_selects_actual_answer_passage(self):
        a = assessment()
        r = {
            "S001": {
                "items": [
                    {
                        "criterion_id": "cause",
                        "level": "clear",
                        "evidence_id": "a1",
                        "reason": "Lost acknowledgement causes retry.",
                    }
                ]
            }
        }
        p = core.make_pack(a, r, "live_model")
        self.assertEqual(p["suggestions"][0]["status"], "suggested")
        self.assertEqual(
            p["suggestions"][0]["quote"],
            "A lost acknowledgement can trigger a retry and deliver the same message again.",
        )
        self.assertEqual(core.validate_pack(p), p)

    def test_unknown_evidence_abstains(self):
        a = assessment()
        for evidence in ["a99", {}, True, None]:
            r = {
                "S001": {
                    "items": [
                        {
                            "criterion_id": "cause",
                            "level": "clear",
                            "evidence_id": evidence,
                            "reason": "Reason",
                        }
                    ]
                }
            }
            self.assertEqual(core.make_pack(a, r, "live_model")["suggestions"][0]["status"], "abstained")

    def test_unicode_repeated_and_punctuation_only(self):
        a = assessment()
        a["submissions"][0]["text"] = "é🙂. é🙂."
        r = {
            "S001": {
                "items": [
                    {"criterion_id": "cause", "level": "clear", "evidence_id": "a2", "reason": "Reason"}
                ]
            }
        }
        p = core.make_pack(a, r, "live_model")
        self.assertEqual(p["suggestions"][0]["quote"], "é🙂.")
        self.assertEqual(p["suggestions"][0]["span"], {"start": 0, "end": 3})

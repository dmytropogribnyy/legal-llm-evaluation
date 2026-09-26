import unittest

from legal_eval.dataset import CATEGORIES, build_cases


def corpus():
    documents = []
    for i in range(12):
        context = f"Contract {i}. A stated condition."
        qas = [{"id": f"contract-{i}__{cat}", "question": cat, "is_impossible": bool(i % 2),
                "answers": [] if i % 2 else
                [{"text": "A stated condition.", "answer_start": context.index("A stated")}]}
               for cat in CATEGORIES]
        documents.append({"title": f"contract-{i}", "paragraphs": [{"context": context, "qas": qas}]})
    return {"data": documents}


class DatasetTests(unittest.TestCase):
    def test_contract_split_is_disjoint_and_repeatable(self):
        cases, _ = build_cases(corpus(), {"sha256": "fixture"})
        again, _ = build_cases(corpus(), {"sha256": "fixture"})
        self.assertEqual(cases, again)
        self.assertEqual(len(cases), 30)
        dev = {c["contract_sha256"] for c in cases if c["split"] == "development"}
        holdout = {c["contract_sha256"] for c in cases if c["split"] == "holdout"}
        self.assertEqual(len(dev), 3)
        self.assertEqual(len(holdout), 7)
        self.assertFalse(dev & holdout)
        for split, minimum in (("development", 1), ("holdout", 2)):
            for category in CATEGORIES:
                for present in (False, True):
                    self.assertGreaterEqual(sum(c["split"] == split and c["category"] == category
                                                and c["reference_present"] == present for c in cases),
                                            minimum)

    def test_invalid_gold_offset_is_rejected(self):
        raw = corpus()
        for document in raw["data"]:
            answers = document["paragraphs"][0]["qas"][0]["answers"]
            if answers:
                answers[0]["answer_start"] = 0
        with self.assertRaises(ValueError):
            build_cases(raw, {"sha256": "fixture"})

    def test_identical_contracts_are_not_split_across_groups(self):
        raw = corpus()
        raw["data"] = [raw["data"][0]] * 12
        with self.assertRaises(ValueError):
            build_cases(raw, {"sha256": "fixture"})


if __name__ == "__main__":
    unittest.main()

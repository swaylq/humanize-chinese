"""The AI-side prompt lengths must track the human control corpora.

The first version of prompts.py set target lengths by genre intuition, and the
mismatch silently invalidated the experiment: an academic prompt asking for 700
characters against real abstracts of ~305 produced an AUC that measured length
rather than writing, and three of six scenes ended up with too little overlap
to compare at all. This test makes that failure loud.
"""
import json
import pathlib
import statistics
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evals" / "corpus"))

from prompts import SCENES  # noqa: E402

CORPUS = ROOT / "evals" / "corpus"


def human_lengths(scene):
    p = CORPUS / f"human_{scene}.jsonl"
    if not p.exists():
        return None
    return sorted(json.loads(l)["cn_chars"]
                  for l in p.read_text(encoding="utf-8").splitlines() if l.strip())


class PromptLengthTests(unittest.TestCase):
    def test_target_sits_inside_the_human_band(self):
        checked = 0
        for scene in SCENES:
            lens = human_lengths(scene)
            if not lens:
                continue  # workplace has no human control, by design
            checked += 1
            target = SCENES[scene]["target_chars"]
            with self.subTest(scene=scene):
                self.assertGreaterEqual(
                    target, lens[0],
                    f"{scene} 目标 {target} 低于人类语料最短 {lens[0]}")
                self.assertLessEqual(
                    target, lens[-1],
                    f"{scene} 目标 {target} 高于人类语料最长 {lens[-1]}")
        self.assertGreater(checked, 0, "没有任何人类对照组，测试没有意义")

    def test_target_is_close_to_the_human_median(self):
        # within 25% of the median — enough overlap for a matched comparison
        for scene in SCENES:
            lens = human_lengths(scene)
            if not lens:
                continue
            med = statistics.median(lens)
            target = SCENES[scene]["target_chars"]
            with self.subTest(scene=scene):
                ratio = target / med
                self.assertTrue(
                    0.75 <= ratio <= 1.25,
                    f"{scene} 目标 {target} 与人类中位数 {med:.0f} 相差 {ratio:.2f} 倍")

    def test_instruction_quotes_a_range_around_the_target(self):
        import re
        for scene, cfg in SCENES.items():
            with self.subTest(scene=scene):
                m = re.search(r"(\d{3,4})\s*-\s*(\d{3,4})\s*字", cfg["instruction"])
                self.assertIsNotNone(
                    m, f"{scene} 的提示词没写字数区间，模型会自由发挥")
                lo, hi = int(m.group(1)), int(m.group(2))
                t = cfg["target_chars"]
                self.assertLessEqual(lo, t, f"{scene} 区间下限 {lo} > 目标 {t}")
                self.assertGreaterEqual(hi, t, f"{scene} 区间上限 {hi} < 目标 {t}")

    def test_every_scene_has_ten_topics(self):
        for scene, cfg in SCENES.items():
            with self.subTest(scene=scene):
                self.assertEqual(len(cfg["topics"]), 10)
                self.assertEqual(len(set(cfg["topics"])), 10, "题目有重复")


if __name__ == "__main__":
    unittest.main()

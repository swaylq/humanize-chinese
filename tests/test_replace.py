"""Tests for scripts/replace_cn.py — the skill's stage ③.

The constraints under test exist because the first version of this script was
jury-scored at 2.0/5: unrestricted word-level swaps produced 越来越深化 and
各方面地评估. Phrase-level + clause-boundary + candidate blocklist brought the
same sample to 4.0 with zero majority defects. These tests pin that shape.
"""
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "pipeline"))

import guards  # noqa: E402
import replace_cn  # noqa: E402


class SceneRoutingTests(unittest.TestCase):
    def test_repo_examples_route_sensibly(self):
        expect = {"sample_academic.txt": "academic",
                  "sample_social.txt": "general",   # formal caricature, no strong markers
                  "sample_general.txt": "general",
                  "sample_workplace.txt": "general"}
        for name, want in expect.items():
            text = (ROOT / "examples" / name).read_text(encoding="utf-8")
            with self.subTest(name=name):
                self.assertEqual(replace_cn.detect_scene(text), want)

    def test_academic_needs_a_strong_marker(self):
        # 显著/机制/实验 alone must not trigger academic — any formal prose has them
        t = "这个方案效果显著，机制清晰，实验也验证过了。" * 3
        self.assertNotEqual(replace_cn.detect_scene(t), "academic")
        t2 = "本文提出一种新方法。实验结果显著，机制清晰，样本充足，文献支持。"
        self.assertEqual(replace_cn.detect_scene(t2), "academic")


class SafetyTests(unittest.TestCase):
    def test_word_level_entries_are_refused(self):
        # 日益→越来越 welded onto the next verb was the flagship failure
        t = "人工智能在教育领域的应用正在日益深化，态势明显。"
        out, _ = replace_cn.apply_replacements(t, "general")
        self.assertIn("日益深化", out, "≤3 字词级替换必须被拒绝")

    def test_mid_clause_match_is_skipped(self):
        # phrase preceded directly by a hanzi must not be replaced
        t = "这个结论也具有重要意义得到了认可。"
        out, _ = replace_cn.apply_replacements(t, "academic")
        self.assertIn("具有重要意义", out)

    def test_clause_start_match_is_replaced(self):
        t = "本文旨在探讨人工智能的应用机制。"
        out, edits = replace_cn.apply_replacements(t, "academic")
        self.assertNotIn("本文旨在", out)
        self.assertTrue(edits)

    def test_quoted_text_is_untouched(self):
        t = "他说：「综上所述，一切照旧。」这是他的原话。"
        out, _ = replace_cn.apply_replacements(t, "general")
        self.assertIn("「综上所述，一切照旧。」", out)

    def test_blocklisted_candidates_never_appear(self):
        t = ("与此同时，市场发生了变化。" * 4)
        out, _ = replace_cn.apply_replacements(t, "general", seed=1)
        for bad in replace_cn._BAD_CANDIDATES:
            self.assertNotIn(bad, out)

    def test_facts_survive_process(self):
        recs = [json.loads(l) for l in
                (ROOT / "evals" / "corpus" / "ai2026_full.jsonl")
                .read_text(encoding="utf-8").splitlines()[:40] if l.strip()]
        for r in recs:
            out, info = replace_cn.process(r["text"])
            with self.subTest(id=r["id"]):
                if info["reverted"]:
                    self.assertEqual(out, r["text"])
                else:
                    self.assertEqual(guards.numbers(r["text"]), guards.numbers(out))
                    self.assertEqual(guards.latin_tokens(r["text"]),
                                     guards.latin_tokens(out))
                    self.assertEqual(len(guards.paragraphs(r["text"])),
                                     len(guards.paragraphs(out)))

    def test_deterministic_with_seed(self):
        t = (ROOT / "examples" / "sample_academic.txt").read_text(encoding="utf-8")
        a, _ = replace_cn.process(t, seed=42)
        b, _ = replace_cn.process(t, seed=42)
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()

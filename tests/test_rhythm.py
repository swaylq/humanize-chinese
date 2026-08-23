"""Unit tests for stage 3 (scripts/pipeline/rhythm.py).

The first test is the important one: every edit the module can make must be
punctuation-only. If that invariant holds, stage 3 cannot damage meaning no
matter how the heuristics are tuned.
"""
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "pipeline"))

import rhythm  # noqa: E402


SAMPLES = [
    "人工智能在教育领域的应用正在日益深化，本研究探讨其应用机制及其效果。"
    "研究表明，智能化系统结合大数据分析与机器学习算法，能够评估学生学习状况。"
    "这种新型教学模式正在改变教育生态，我们需要更多实证研究来验证它。",
    "本季度订单量环比增长 12%，其中 9 个点来自老客复购，剩下的来自新渠道。"
    "客服工单量下降了 30%，主要因为自助退款上线，但是退款金额同比上升了 8%。",
]


class InvariantTests(unittest.TestCase):
    def test_polish_is_punctuation_only(self):
        for i, s in enumerate(SAMPLES):
            with self.subTest(sample=i):
                out, _ = rhythm.polish(s)
                self.assertTrue(
                    rhythm.verify_invariant(s, out),
                    f"non-punctuation change:\n{s}\n-->\n{out}")

    def test_invariant_on_repo_examples(self):
        for f in sorted((ROOT / "examples").glob("*.txt")):
            with self.subTest(name=f.name):
                text = f.read_text(encoding="utf-8")
                out, _ = rhythm.polish(text)
                self.assertTrue(rhythm.verify_invariant(text, out), f.name)

    def test_invariant_on_real_human_corpus(self):
        corpus = ROOT / "evals" / "corpus" / "human_abstract.jsonl"
        if not corpus.exists():
            self.skipTest("control corpus not built")
        for line in corpus.read_text(encoding="utf-8").splitlines()[:30]:
            if not line.strip():
                continue
            text = json.loads(line)["text"]
            out, _ = rhythm.polish(text)
            self.assertTrue(rhythm.verify_invariant(text, out))

    def test_paragraph_count_preserved(self):
        text = "第一段的内容在这里，写得比较长一些。\n\n第二段的内容在这里，也写得长一些。"
        out, _ = rhythm.polish(text)
        self.assertEqual(text.count("\n\n"), out.count("\n\n"))


class SafetyTests(unittest.TestCase):
    def test_never_splits_after_subordinator_head(self):
        # 「虽然A，但是B」 must stay one sentence — splitting after 虽然A
        # leaves a fragment.
        s = "虽然这套方案在测试环境跑通了，但是上线之后压力一大就出问题。"
        self.assertEqual(find := rhythm.find_split_candidates(s), [],
                         f"unsafe split offered at {find}")

    def test_never_splits_after_preposition(self):
        # 「通过优化业务流程」 is an adverbial, not a sentence. The first version
        # of rhythm.py split here and produced a fragment; this pins the fix.
        for s in [
            "通过优化业务流程，我们提升了工作效率并支持了公司的核心战略。",
            "根据学生的实时表现动态调整，这个平台能提供个性化的学习体验。",
            "基于高精度重力数据的反演结果，我们构建了详细的地下密度模型。",
            "随着技术条件的逐步成熟，这套方法开始在更多的场景里得到应用。",
        ]:
            with self.subTest(s=s[:12]):
                self.assertEqual(
                    rhythm.find_split_candidates(s), [],
                    f"offered a fragment-producing split in: {s}")

    def test_label_prefix_does_not_defeat_the_head_check(self):
        # Regression: the H1 acceptance jury caught stage 3 emitting
        # "案例：在一个项目中。我们需要开发一款新的移动应用". A short label plus a
        # colon hid the dependent head from the guard.
        for s in [
            "案例：在一个项目中，我们需要开发一款新的移动应用来支撑业务。",
            "反思：通过这个经验，我认识到产品愿景是决策的核心依据。",
            "反思：在这个过程中，我学会了如何倾听不同团队的意见。",
            "案例：在负责一个新产品的开发时，我发现市场竞争异常激烈。",
        ]:
            with self.subTest(s=s[:14]):
                self.assertEqual(
                    rhythm.find_split_candidates(s), [],
                    f"label prefix let a fragment split through: {s}")

    def test_label_prefix_still_allows_safe_splits(self):
        # The label must not make the whole sentence untouchable — only the
        # head test changes.
        s = "案例：这套方案在测试环境跑得很顺利，但是上线之后压力一大就出问题了。"
        self.assertTrue(rhythm.find_split_candidates(s))

    def test_never_splits_inside_quotes(self):
        s = "他说「这个方案不行，我们再想想」，然后就挂了电话没有再联系我们。"
        for i in rhythm.find_split_candidates(s):
            self.assertNotIn(s[i - 1], "行想", f"split inside quote at {i}")

    def test_never_splits_thousands_separator(self):
        s = "去年的总量是 1,200 吨，今年的总量下降到了 900 吨左右的水平。"
        for i in rhythm.find_split_candidates(s):
            self.assertFalse(s[i] == "," and s[i - 1].isdigit())

    def test_splits_before_sentence_initial_connective(self):
        s = "这套方案在测试环境跑得很顺利，但是上线之后压力一大就出问题了。"
        self.assertTrue(rhythm.find_split_candidates(s),
                        "should offer a split before 但是")

    def test_semicolon_always_splittable(self):
        s = "技术的成熟度和可靠性仍有待提高；教育工作者的数字化素养也需要同步提升。"
        self.assertTrue(rhythm.find_split_candidates(s))

    def test_too_short_clause_rejected(self):
        s = "他走了，我留下。"
        self.assertEqual(rhythm.find_split_candidates(s), [])


class EffectTests(unittest.TestCase):
    def test_rhythm_improves_or_holds(self):
        for i, s in enumerate(SAMPLES):
            with self.subTest(sample=i):
                before = rhythm.metrics(s)
                out, _ = rhythm.polish(s)
                after = rhythm.metrics(out)
                self.assertGreaterEqual(round(after["cv"], 6),
                                        round(before["cv"], 6) - 1e-9)

    def test_toggles_are_honoured(self):
        s = SAMPLES[0]
        off, edits = rhythm.polish(s, enable_split=False, enable_merge=False)
        self.assertEqual(off, s)
        self.assertEqual(edits, [])

    def test_already_good_text_is_left_alone(self):
        # High CV and plenty of short sentences: nothing to do.
        s = "他走了。留下一屋子没收的碗。第二天早上，房东来敲门，说租约到期了要么续要么搬。我说搬。"
        out, edits = rhythm.polish(s)
        self.assertEqual(out, s)
        self.assertEqual(edits, [])


if __name__ == "__main__":
    unittest.main()

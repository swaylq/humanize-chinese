"""Offline tests for stage ④'s scope guard (scripts/pipeline/stage4_proofread.py).

The guard is what turns 稍微改的好读一点 into an enforceable contract: light
smoothing passes, wholesale rewriting is discarded. Calibration history is in
the module docstring — these tests pin the floor's behaviour at both ends.
"""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "pipeline"))
sys.path.insert(0, str(ROOT / "evals" / "corpus"))

from stage4_proofread import check, scope_ok  # noqa: E402

BASE = ("写代码的时候,\"完成\"这个概念是被工具喂到你嘴里的。编译过了，测试绿了，"
        "CI 跑通，合并，上线，监控没报警，你可以关电脑。做产品之后这条链断了。"
        "PRD 写完不算完，评审过了不算完，开发做完上线了还是不算完。")


class ScopeGuardTests(unittest.TestCase):
    def test_punctuation_fix_passes(self):
        fixed = BASE.replace('时候,"', '时候，"')
        self.assertEqual(check(BASE, fixed), [])

    def test_light_smoothing_passes(self):
        # a couple of word-level touch-ups — the new mandate
        smoothed = (BASE.replace('时候,"', '时候，"')
                        .replace("是被工具喂到你嘴里的", "是工具直接递到你手上的")
                        .replace("这条链断了", "这条链就断了"))
        ok, ratio = scope_ok(BASE, smoothed)
        self.assertTrue(ok, f"轻手顺句被误拒（相似度 {ratio:.3f}）")
        self.assertEqual(check(BASE, smoothed), [])

    def test_wholesale_rewrite_is_rejected(self):
        rewrite = ("程序员的完成感来自工具链的反馈闭环，而产品工作缺乏此类信号，"
                   "需求的边界因此变得模糊，验收标准也随之难以确立。")
        self.assertTrue(check(BASE, rewrite), "整段重写必须被拒")

    def test_truncation_is_rejected(self):
        self.assertTrue(check(BASE, BASE[:60]))

    def test_identity_passes(self):
        self.assertEqual(check(BASE, BASE), [])

    def test_number_loss_is_rejected(self):
        a = "本季度订单量环比增长 12%，其中 9 个点来自老客复购。"
        b = "本季度订单量环比明显增长，其中相当部分来自老客复购。"
        self.assertTrue(check(a, b))


if __name__ == "__main__":
    unittest.main()

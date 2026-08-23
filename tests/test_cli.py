"""CLI wiring tests for the v6 front door.

These run the real dispatcher as a subprocess. Only the offline paths are
exercised — anything needing OPENROUTER_API_KEY is asserted on its error
message instead, so the suite stays runnable with no network and no key.
"""
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "scripts" / "humanize.py"


def run(args, env=None, stdin=None):
    e = dict(os.environ)
    e["PYTHONHASHSEED"] = "0"
    if env:
        e.update(env)
    e.pop("OPENROUTER_API_KEY", None) if env and env.get("_nokey") else None
    return subprocess.run([sys.executable, str(DISPATCH), *args],
                          capture_output=True, text=True, env=e, input=stdin)


class DispatcherTests(unittest.TestCase):
    def test_list_includes_new_subcommands(self):
        p = run(["--list"])
        self.assertEqual(p.returncode, 0)
        self.assertIn("rewrite", p.stdout)
        self.assertIn("write", p.stdout)

    def test_usage_mentions_legacy(self):
        p = run(["--help"])
        self.assertIn("--legacy", p.stdout)

    def test_unknown_subcommand_fails_clearly(self):
        p = run(["nonsense"])
        self.assertEqual(p.returncode, 2)
        self.assertIn("unknown subcommand", p.stderr)


class OfflineRewriteTests(unittest.TestCase):
    def _tmp(self, text):
        fh = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                         encoding="utf-8")
        fh.write(text)
        fh.close()
        return fh.name

    def test_offline_rewrite_splits_where_safe(self):
        src = self._tmp("这套方案在测试环境跑得很顺利，但是上线之后压力一大就出问题了。"
                        "技术的成熟度仍有待提高；运维的经验也需要同步积累起来。")
        out = src + ".out"
        p = run(["rewrite", src, "-o", out])
        self.assertEqual(p.returncode, 0, p.stderr)
        text = pathlib.Path(out).read_text(encoding="utf-8")
        self.assertIn("仍有待提高。", text, "semicolon should become a full stop")

    def test_offline_rewrite_explains_when_it_does_nothing(self):
        # A single short sentence offers no safe split.
        src = self._tmp("今天天气不错。")
        p = run(["rewrite", src, "-o", src + ".out"])
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("没有可以安全修改的地方", p.stderr)
        self.assertIn("--llm", p.stderr, "should point at the LLM stage")

    def test_offline_rewrite_never_changes_non_punctuation(self):
        sys.path.insert(0, str(ROOT / "scripts" / "pipeline"))
        import rhythm
        for f in sorted((ROOT / "examples").glob("*.txt")):
            with self.subTest(name=f.name):
                out = tempfile.mktemp(suffix=".txt")
                p = run(["rewrite", str(f), "-o", out, "-q"])
                self.assertEqual(p.returncode, 0, p.stderr)
                self.assertTrue(rhythm.verify_invariant(
                    f.read_text(encoding="utf-8"),
                    pathlib.Path(out).read_text(encoding="utf-8")))

    def test_stdin_is_accepted(self):
        p = run(["rewrite", "-", "-q"], stdin="今天的会开得很久，我们最后还是没有定下方案。")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("今天的会", p.stdout)


class GuardrailTests(unittest.TestCase):
    def test_llm_without_key_fails_with_instructions(self):
        env = dict(os.environ)
        env.pop("OPENROUTER_API_KEY", None)
        p = subprocess.run(
            [sys.executable, str(DISPATCH), "rewrite",
             str(ROOT / "examples" / "sample_general.txt"), "--llm"],
            capture_output=True, text=True, env=env)
        self.assertEqual(p.returncode, 2)
        self.assertIn("OPENROUTER_API_KEY", p.stderr)
        self.assertIn("secret exec", p.stderr)

    def test_legacy_prints_deprecation_with_evidence(self):
        p = run(["rewrite", str(ROOT / "examples" / "sample_general.txt"),
                 "--legacy", "--quick", "-o", tempfile.mktemp(suffix=".txt")])
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("已弃用", p.stderr)
        # the notice must carry the measurement, not just an opinion
        self.assertIn("2.0", p.stderr)
        self.assertIn("0.645", p.stderr)


if __name__ == "__main__":
    unittest.main()

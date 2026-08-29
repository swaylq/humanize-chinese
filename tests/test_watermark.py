"""Tests for scripts/watermark_cn.py.

Most of these pin behaviour that the English-language cleaners get wrong. The
project this repo would otherwise have copied (watermarks-remover, 14k stars)
runs NFKC and maps U+3000 to an ASCII space; both are correct for English and
both corrupt Chinese, so the corruption cases are tested first and hardest.

The rest pin the Layer B estimator, whose only claim is a proportion: the
fraction of the original's keyed scoring windows still standing. That number
is checked against hand-computable cases here and against an actual watermark
detector in evals/watermark_sim.py.
"""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import watermark_cn as wm  # noqa: E402


class ChineseTypographySurvives(unittest.TestCase):
    """The cases where a naive port of an English cleaner does damage."""

    def test_fullwidth_punctuation_is_not_touched(self):
        # NFKC would turn ： into : and （） into (), which is corruption, not
        # cleaning — and a visible sign the text went through a machine.
        t = "他说：「这不对。」（真的）——他叹了口气；然后走了！"
        out, stats = wm.clean_text(t)
        self.assertEqual(out, t)
        self.assertEqual(stats["removed_count"] + stats["replaced_count"], 0)

    def test_ideographic_space_indent_is_not_touched(self):
        # U+3000 doubled is the standard Chinese paragraph indent. Every
        # English cleaner lists it as a space homoglyph and rewrites it.
        t = "　　这是一段。\n\n　　这是另一段。"
        out, _ = wm.clean_text(t)
        self.assertEqual(out, t)
        self.assertIn("　　", out)

    def test_fullwidth_latin_is_kept_unless_asked(self):
        t = "Ｇｉｔ 仓库"                      # Ｇｉｔ 仓库
        self.assertEqual(wm.clean_text(t)[0], t)
        self.assertEqual(wm.clean_text(t, fullwidth_latin=True)[0], "Git 仓库")

    def test_ideographic_variation_sequence_is_kept(self):
        # 葛 + VS17 selects a real glyph. Stripped as a "variation selector",
        # the character silently changes shape.
        t = "葛\U000E0100 城"
        self.assertEqual(wm.clean_text(t)[0], t)

    def test_emoji_sequences_are_kept(self):
        t = "一家人 \U0001F468‍\U0001F469‍\U0001F467 在 ❤️ 里"
        self.assertEqual(wm.clean_text(t)[0], t)


class CarriersAreRemoved(unittest.TestCase):
    def test_zero_width_family(self):
        t = "这是​一段﻿中文⁠文本"
        out, stats = wm.clean_text(t)
        self.assertEqual(out, "这是一段中文文本")
        self.assertEqual(stats["removed"]["zero_width"], 3)

    def test_bidi_controls(self):
        t = "正常‮反转‬文本"
        out, stats = wm.clean_text(t)
        self.assertEqual(out, "正常反转文本")
        self.assertEqual(stats["removed"]["bidi"], 2)
        # ...unless the document genuinely mixes in an RTL script.
        self.assertEqual(wm.clean_text(t, keep_bidi=True)[0], t)

    def test_tag_characters(self):
        t = "文本\U000E0041\U000E0042"
        self.assertEqual(wm.clean_text(t)[0], "文本")

    def test_orphan_variation_selector(self):
        # Same codepoint as the IVS case above, but after ASCII rather than a
        # hanzi, where it selects nothing and is a carrier.
        t = "ab\U000E0100cd"
        self.assertEqual(wm.clean_text(t)[0], "abcd")

    def test_space_homoglyphs_that_are_not_chinese_typography(self):
        t = "这里有 一个 不该有的空格"
        out, stats = wm.clean_text(t)
        self.assertEqual(out, "这里有 一个 不该有的空格")
        self.assertEqual(stats["replaced"]["space"], 2)

    def test_private_use_and_noncharacters(self):
        t = "文本﷐字￿符"
        self.assertEqual(wm.clean_text(t)[0], "文本字符")

    def test_clean_is_idempotent(self):
        t = "　　这​是⼀段 话。"
        once, _ = wm.clean_text(t)
        twice, stats = wm.clean_text(once)
        self.assertEqual(once, twice)
        self.assertEqual(stats["removed_count"] + stats["replaced_count"], 0)


class HanziLookalikes(unittest.TestCase):
    """The carrier class only Chinese has, and no English cleaner looks for."""

    def test_kangxi_radical_folds_to_the_unified_ideograph(self):
        out, stats = wm.clean_text("⼀个人")          # ⼀个人
        self.assertEqual(out, "一个人")               # 一个人
        self.assertEqual(stats["replaced"]["lookalike"], 1)

    def test_cjk_radical_supplement_folds(self):
        self.assertEqual(wm.clean_text("⻳兔赛跑")[0], "龟兔赛跑")

    def test_compatibility_ideograph_folds(self):
        self.assertEqual(wm.clean_text("豈有此理")[0], "豈有此理")

    def test_supplementary_compatibility_ideograph_folds(self):
        self.assertEqual(wm.clean_text("\U0002F800也是")[0], "丽也是")

    def test_unified_ideographs_inside_the_compat_block_are_left_alone(self):
        # U+FA0E, U+FA11 and friends live in the compatibility block but are
        # unified ideographs with no decomposition — folding them would be a
        # bug, and per-character NFKC declines to.
        for cp in (0xFA0E, 0xFA0F, 0xFA11, 0xFA13, 0xFA1F, 0xFA23, 0xFA27):
            with self.subTest(cp=hex(cp)):
                self.assertIsNone(wm._lookalike_target(chr(cp)))
                self.assertEqual(wm.clean_text(chr(cp))[0], chr(cp))

    def test_ordinary_hanzi_are_never_folded(self):
        t = "一龟豈丽的普通中文句子，没有任何替身。"
        self.assertEqual(wm.clean_text(t)[0], t)


class InspectReports(unittest.TestCase):
    def test_clean_text_reports_nothing(self):
        report = wm.inspect_text("　　一段干净的中文。")
        self.assertEqual(report["total"], 0)
        self.assertEqual(report["hits"], [])

    def test_hits_carry_codepoint_kind_and_render_target(self):
        report = wm.inspect_text("这​是⼀段话")
        kinds = {h["codepoint"]: h for h in report["hits"]}
        self.assertEqual(kinds["U+200B"]["kind"], "zero_width")
        self.assertEqual(kinds["U+2F00"]["kind"], "lookalike")
        self.assertEqual(kinds["U+2F00"]["renders_as"], "一")
        self.assertEqual(report["total"], 2)

    def test_inspect_and_clean_agree(self):
        t = "　　这​是‮一⼀段 话。"
        report = wm.inspect_text(t)
        _out, stats = wm.clean_text(t)
        self.assertEqual(report["total"],
                         stats["removed_count"] + stats["replaced_count"])


class SurvivalMeter(unittest.TestCase):
    def test_identical_text_survives_completely(self):
        t = "人工智能在教育领域的应用正在不断深化。"
        r = wm.ngram_survival(t, t)
        self.assertEqual(r["headline"], 1.0)
        self.assertAlmostEqual(r["z_ratio"], 1.0, places=6)

    def test_disjoint_text_survives_not_at_all(self):
        r = wm.ngram_survival("人工智能在教育领域的应用正在不断深化。",
                              "昨天下午我去菜市场买了两斤排骨和一把青菜。")
        self.assertEqual(r["headline"], 0.0)
        self.assertEqual(r["z_ratio"], 0.0)

    def test_whitespace_only_edits_do_not_count_as_removal(self):
        # Stage 3 moves punctuation and line breaks. Counting those as broken
        # windows would flatter every rewrite in the repo.
        base = "人工智能在教育领域的应用正在不断深化"
        r = wm.ngram_survival(base, base[:6] + "\n\n" + base[6:])
        self.assertEqual(r["headline"], 1.0)

    def test_half_the_text_verbatim_is_half_survival_but_z_falls_less(self):
        # Deleting half a marked passage without editing a character leaves
        # survival at 0.5 and z at 0.5/sqrt(0.5) = 0.71 of what it was: a
        # detector reading half as much text was never as confident.
        t = "".join(chr(0x4E00 + i) for i in range(400))
        r = wm.ngram_survival(t, t[:200])
        self.assertAlmostEqual(r["headline"], 0.5, places=1)
        self.assertAlmostEqual(r["z_ratio"], 0.707, places=2)
        self.assertGreater(r["z_ratio"], r["headline"])

    def test_padding_with_unmarked_text_dilutes_below_survival(self):
        t = "".join(chr(0x4E00 + i) for i in range(400))
        pad = "".join(chr(0x6000 + i) for i in range(400))
        r = wm.ngram_survival(t, t + pad)
        self.assertAlmostEqual(r["headline"], 1.0, places=2)
        self.assertLess(r["z_ratio"], 0.75)

    def test_every_reported_width_is_a_proportion(self):
        r = wm.ngram_survival("人工智能在教育领域的应用正在不断深化。",
                              "人工智能用在教育上，这几年确实铺开了。")
        for row in r["widths"]:
            with self.subTest(width=row["width"]):
                self.assertLessEqual(row["kept"], row["total"])
                self.assertTrue(0.0 <= row["survival"] <= 1.0)
        # Wider windows break more easily, so survival is non-increasing.
        survivals = [row["survival"] for row in r["widths"]]
        self.assertEqual(survivals, sorted(survivals, reverse=True))


class CommandLine(unittest.TestCase):
    def test_inspect_clean_survive_round_trip(self):
        import subprocess
        import tempfile
        script = str(ROOT / "scripts" / "watermark_cn.py")
        with tempfile.TemporaryDirectory() as d:
            dirty = pathlib.Path(d) / "dirty.txt"
            clean = pathlib.Path(d) / "clean.txt"
            dirty.write_text("　　这​是⼀段话。", encoding="utf-8")

            r = subprocess.run([sys.executable, script, "inspect", str(dirty)],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0)
            self.assertIn("U+200B", r.stdout)
            self.assertIn("U+2F00", r.stdout)

            r = subprocess.run([sys.executable, script, "clean", str(dirty),
                                "-o", str(clean)],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0)
            self.assertEqual(clean.read_text(encoding="utf-8"),
                             "　　这是一段话。")

            r = subprocess.run([sys.executable, script, "survive",
                                str(dirty), str(clean)],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0)
            self.assertIn("存活率", r.stdout)

    def test_dispatcher_exposes_the_subcommand(self):
        import subprocess
        r = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "humanize.py"), "--list"],
            capture_output=True, text=True)
        self.assertIn("watermark", r.stdout)


if __name__ == "__main__":
    unittest.main()

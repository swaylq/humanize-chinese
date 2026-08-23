#!/usr/bin/env python3
"""v6 rewriter CLI — the front door for the three-stage pipeline.

    ./humanize rewrite draft.txt                 # offline, no API key
    ./humanize rewrite draft.txt --llm -o out.txt # LLM rewrite + rhythm
    ./humanize write "写一篇讲复利的科普" -o out.txt  # write it clean from scratch
    ./humanize rewrite draft.txt --legacy         # the v5 rewriter, deprecated

Why the default changed in v6
-----------------------------
v5's offline rewriter chased a detector score using synonym substitution,
inserted filler sentences and clause reordering. Measured on 2026-08-24 by a
three-model fluency jury, its output scored a median 2.0 out of 5 with six
majority-backed broken sentences ("各个层面地评判", "更好地推进的必由之路"),
while the same jury gave the v6 pipeline 4.0-5.0 with none.

Meanwhile the detector those techniques optimise for has stopped working: on
length- and topic-matched academic abstracts it separates 2024 models from real
human papers at AUC 0.956 but 2026 models at only 0.645, where 0.5 is a coin
flip. Damaging Chinese to move a number that no longer measures anything is a
bad trade, so it is no longer what this command does by default.

The offline default now does only what can be done without risk: sentence
rhythm, by moving punctuation. On text an LLM wrote, that is often nothing at
all — AI prose has no clause boundary that can be split without leaving a
fragment. When that happens this command says so instead of inventing changes.
"""
from __future__ import annotations

import argparse
import os
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve()
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "pipeline"))

import rhythm  # noqa: E402

LEGACY_NOTICE = """\
注意：--legacy 走的是 v5 改写器，已弃用。
  实测（2026-08-24，三模型通顺度评审团）：v5 产物中位数 2.0/5，6 处多数票病句；
  v6 流水线同样本 4.0-5.0，零病句。
  它优化的检测器对 2026 年的模型也已接近失效（AUC 0.645，0.5 是抛硬币）。
  保留它只为兼容既有脚本，不建议用于新工作。
"""

NOTHING_TO_DO = """\
没有可以安全修改的地方，已原样输出。

这不是失败。离线这一档只做一件事：调整断句节奏，而且只移动标点、
不换词不插句不调序（去掉标点后字符序列必须完全相同，程序会校验）。
这段文字里找不到能安全断开的位置 —— AI 写的句子结构均匀、缺少能独立成句的子句，
硬断会产生残句。

要真正去掉 AI 腔，用需要 API key 的那两档：
  ./humanize rewrite {name} --llm      让模型定点拆模板句式，再做节奏
  ./humanize write "<写作要求>"          从零写，人味在写的时候就有
"""


def run_legacy(argv: list[str]) -> int:
    sys.stderr.write(LEGACY_NOTICE)
    target = ROOT / "scripts" / "humanize_cn.py"
    return subprocess.run([sys.executable, str(target), *argv]).returncode


def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    if "--legacy" in argv:
        argv.remove("--legacy")
        return run_legacy(argv)

    ap = argparse.ArgumentParser(
        description="v6 去 AI 腔改写（三段流水线）",
        epilog="旧版 v5 改写器：加 --legacy（已弃用）")
    ap.add_argument("file", nargs="?", help="输入文件；- 表示标准输入")
    ap.add_argument("-o", "--output")
    ap.add_argument("--llm", action="store_true",
                    help="启用第 2 段：LLM 定点去 AI 腔（需要 OPENROUTER_API_KEY）")
    ap.add_argument("--write", metavar="BRIEF",
                    help="不改写，按写作要求从零写一篇（第 1→2→3 段）")
    ap.add_argument("--scene", default="general",
                    help="文体：general/academic/social/workplace/blog/novel")
    ap.add_argument("--chars", type=int, default=600, help="--write 的目标字数")
    ap.add_argument("-m", "--model", default="anthropic/claude-opus-5")
    ap.add_argument("--trace", help="把每段的输入输出写成 JSON")
    ap.add_argument("--no-fluency-gate", action="store_true",
                    help="跳过通顺度评审团（默认开启，是 H1 的硬门槛）")
    ap.add_argument("-q", "--quiet", action="store_true")
    ap.add_argument("--legacy", action="store_true",
                    help="改用 v5 旧改写器（已弃用，见上方说明）")
    args = ap.parse_args(argv)

    # --write and --llm both need the network path; hand off to run.py so there
    # is exactly one implementation of the pipeline.
    if args.write or args.llm:
        if not os.environ.get("OPENROUTER_API_KEY"):
            sys.stderr.write(
                "需要 OPENROUTER_API_KEY。用法：\n"
                "  secret exec OPENROUTER_API_KEY -- ./humanize rewrite <文件> --llm\n")
            return 2
        cmd = [sys.executable, str(ROOT / "scripts" / "pipeline" / "run.py"),
               "-m", args.model, "--scene", args.scene]
        cmd += ["--write", args.write, "--chars", str(args.chars)] if args.write \
            else ["--in", args.file or "-"]
        if args.output:
            cmd += ["-o", args.output]
        if args.trace:
            cmd += ["--trace", args.trace]
        if args.no_fluency_gate:
            cmd += ["--no-fluency-gate"]
        if not args.quiet:
            cmd += ["-v"]
        return subprocess.run(cmd).returncode

    # ---- offline default: stage 3 only ---------------------------------
    if not args.file:
        ap.error("需要输入文件（或用 --write 从零写）")
    text = (sys.stdin.read() if args.file == "-"
            else pathlib.Path(args.file).read_text(encoding="utf-8")).strip()

    before = rhythm.metrics(text)
    out, edits = rhythm.polish(text)
    after = rhythm.metrics(out)

    if not rhythm.verify_invariant(text, out):
        sys.stderr.write("保义校验失败，已放弃全部改动（这是个 bug，请报告）\n")
        out, edits = text, []

    if not args.quiet:
        if edits:
            sys.stderr.write(f"断句节奏 {len(edits)} 处改动：\n")
            for e in edits:
                sys.stderr.write(f"  · {e}\n")
            sys.stderr.write(
                f"句长变异系数 {before['cv']:.3f} -> {after['cv']:.3f}"
                f"（目标 ≥{rhythm.CV_TARGET}）· "
                f"短句占比 {before['short_fraction']:.1%} -> "
                f"{after['short_fraction']:.1%}"
                f"（目标 ≥{rhythm.SHORT_FRACTION_TARGET:.0%}）\n")
        else:
            sys.stderr.write(NOTHING_TO_DO.format(
                name=args.file if args.file != "-" else "<文件>"))

    if args.output:
        pathlib.Path(args.output).write_text(out + "\n", encoding="utf-8")
        if not args.quiet:
            sys.stderr.write(f"-> {args.output}\n")
    else:
        sys.stdout.write(out + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

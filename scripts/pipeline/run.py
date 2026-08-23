#!/usr/bin/env python3
"""The v6 pipeline entry point — runs the three stages in series.

    # de-AI an existing draft (stages 2 and 3)
    secret exec OPENROUTER_API_KEY -- python3 scripts/pipeline/run.py \
        --in draft.txt -o clean.txt

    # write something new, then clean it (stages 1, 2 and 3)
    secret exec OPENROUTER_API_KEY -- python3 scripts/pipeline/run.py \
        --write "写一篇关于信用卡分期的科普短文" --scene general -o out.txt

    # skip a stage
    ... --stages 23        # default when --in is used
    ... --stages 3         # offline, no API key needed

Stage 1 (skills/write-cn)      LLM writes with the AI register designed out
Stage 2 (skills/deai-rewrite)  LLM removes what stage 1 still left in
Stage 3 (rhythm.py)            punctuation-only rhythm pass, offline

Every stage's input and output is kept in the trace (--trace FILE), which is
what H2 in projects/v6-refactor/GOAL.md means by 每段的输入输出都留痕可查.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve()
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "evals" / "corpus"))
sys.path.insert(0, str(HERE.parent))

import guards  # noqa: E402
import rhythm  # noqa: E402
from normalize import normalize_punct  # noqa: E402

WRITE_SKILL = ROOT / "skills" / "write-cn" / "SKILL.md"


def _load_skill(path: pathlib.Path) -> str:
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            text = text[end + 4:]
    return text.strip()


def stage1_write(brief: str, *, scene: str, model: str, chars: int) -> str:
    from models import chat
    skill = _load_skill(WRITE_SKILL)
    system = (
        skill
        + "\n\n---\n\n你现在按上面这份说明写作。只输出正文，"
          "不要标题、不要小标题、不要 markdown 标记、不要解释。"
    )
    prompt = (f"文体：{scene}\n长度：约 {chars} 个汉字\n\n写作要求：{brief}")
    raw = chat(model, prompt, system=system, max_tokens=16000).strip()
    # Models mix halfwidth , and ; into Chinese prose (observed 2026-08-24:
    # "付72元合理;到了第十二个月,"). Left alone it reads sloppy and it also
    # skews the detector's comma-density feature. Normalise once, here.
    return normalize_punct(raw)


def stage2_rewrite(text: str, *, model: str, verbose: bool) -> tuple[str, str]:
    from stage2_rewrite import rewrite
    return rewrite(text, model=model, verbose=verbose)


def stage3_polish(text: str) -> tuple[str, list[str]]:
    return rhythm.polish(text)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--in", dest="infile", help="existing draft to clean")
    src.add_argument("--write", dest="brief", help="brief for stage 1")
    ap.add_argument("-o", "--output", default=None)
    ap.add_argument("--stages", default=None,
                    help="which stages to run, e.g. 123 / 23 / 3")
    ap.add_argument("--scene", default="general")
    ap.add_argument("--chars", type=int, default=600)
    ap.add_argument("-m", "--model", default="anthropic/claude-opus-5")
    ap.add_argument("--trace", default=None, help="write a JSON trace here")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    stages = args.stages or ("123" if args.brief else "23")
    trace: list[dict] = []

    def note(stage, before, after, detail):
        trace.append({"stage": stage, "in_chars": guards.cn_chars(before or ""),
                      "out_chars": guards.cn_chars(after), "detail": detail,
                      "input": before, "output": after})
        if args.verbose:
            print(f"[stage {stage}] {guards.cn_chars(before or '')} -> "
                  f"{guards.cn_chars(after)} 字 · {detail}", file=sys.stderr)

    # ---- stage 1 --------------------------------------------------------
    if "1" in stages:
        if not args.brief:
            print("--stages 包含 1 时必须给 --write", file=sys.stderr)
            return 2
        text = stage1_write(args.brief, scene=args.scene, model=args.model,
                            chars=args.chars)
        note(1, None, text, f"按 write-cn 生成（{args.scene}）")
    else:
        text = pathlib.Path(args.infile).read_text(encoding="utf-8").strip()

    # ---- stage 2 --------------------------------------------------------
    if "2" in stages:
        before = text
        text, status = stage2_rewrite(text, model=args.model,
                                      verbose=args.verbose)
        text = normalize_punct(text)
        note(2, before, text,
             "定点去 AI 腔" if status == "rewritten" else "守卫未通过，保留原文")

    # ---- stage 3 --------------------------------------------------------
    if "3" in stages:
        before = text
        text, edits = stage3_polish(text)
        ok = rhythm.verify_invariant(before, text)
        note(3, before, text,
             f"断句节奏 {len(edits)} 处改动，保义校验 {'通过' if ok else '失败'}"
             + (f"：{'; '.join(edits)}" if edits else ""))
        if not ok:
            print("stage 3 保义校验失败，已回退", file=sys.stderr)
            text = before

    m = rhythm.metrics(text)
    if args.verbose:
        print(f"[final] 句长变异系数 {m['cv']:.3f}（目标 ≥{rhythm.CV_TARGET}）· "
              f"短句占比 {m['short_fraction']:.1%}"
              f"（目标 ≥{rhythm.SHORT_FRACTION_TARGET:.0%}）", file=sys.stderr)

    if args.trace:
        pathlib.Path(args.trace).write_text(
            json.dumps({"stages": stages, "trace": trace, "metrics": m},
                       ensure_ascii=False, indent=1), encoding="utf-8")
        if args.verbose:
            print(f"trace -> {args.trace}", file=sys.stderr)

    if args.output:
        pathlib.Path(args.output).write_text(text + "\n", encoding="utf-8")
        print(f"-> {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

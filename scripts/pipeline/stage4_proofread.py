#!/usr/bin/env python3
"""Stage ④: proofread — fix wrong words, broken sentences and punctuation,
change nothing else.

    secret exec OPENROUTER_API_KEY -- python3 scripts/pipeline/stage4_proofread.py in.txt -o out.txt

"Change nothing else" is enforced mechanically, not requested politely:

  scope_ok() diffs the two texts character by character. Proofreading is spot
  surgery — a punctuation fix changes one character in a thousand — so if less
  than SCOPE_MIN of the text survives unchanged, the model has drifted into
  rewriting and the whole edit is rejected. On top of that, guards.check()
  requires every number, Latin token and paragraph to survive exactly.

  Reject → retry once with the violation quoted → still bad → return the input
  untouched. The pipeline's standing rule: refusing to edit beats overstepping.
"""
from __future__ import annotations

import argparse
import difflib
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve()
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "evals" / "corpus"))
sys.path.insert(0, str(HERE.parent))

import guards  # noqa: E402

SKILL_PATH = ROOT / "skills" / "proofread-cn" / "SKILL.md"
DEFAULT_MODEL = "anthropic/claude-opus-5"

# At least this share of characters must be identical (contiguous-match
# ratio). Calibrated twice: at the original errors-only mandate this was 0.88;
# when sway widened stage ④ to also smooth awkward phrasing (2026-08-24,
# "稍微改的好读一点"), lightly rewording a couple of clunky sentences in a
# 400-char text lands around 0.85, so the floor moved to 0.78. Wholesale
# rewriting still scores far below and still gets discarded.
SCOPE_MIN = 0.78


def load_skill(path: pathlib.Path = SKILL_PATH) -> str:
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            text = text[end + 4:]
    return text.strip()


def scope_ok(before: str, after: str) -> tuple[bool, float]:
    ratio = difflib.SequenceMatcher(None, before, after).ratio()
    return ratio >= SCOPE_MIN, ratio


def check(before: str, after: str) -> list[str]:
    """All the reasons this proofread is unacceptable; empty = fine."""
    problems = guards.check(before, after,
                            min_length_ratio=0.90, max_length_ratio=1.10)
    ok, ratio = scope_ok(before, after)
    if not ok:
        problems.append(f"改动范围过大（相似度 {ratio:.2f} < {SCOPE_MIN}）——"
                        "纠错是点状手术，不是重写")
    return problems


def proofread(text: str, *, model: str = DEFAULT_MODEL,
              verbose: bool = False) -> tuple[str, str]:
    """Return (result, status); status is 'proofread' | 'unchanged' | 'reverted'."""
    from models import chat

    system = (load_skill()
              + "\n\n---\n\n你现在按上面这份说明工作。只输出改完的正文，"
                "没有错误就逐字原样返回。不解释、不加前言。")
    prompt = f"请对下面这段中文做纠错顺句（修错词、病句、标点，把拗口和用词不准的地方轻手顺一顺）：\n\n{text}"

    for attempt in range(2):
        try:
            out = chat(model, prompt, system=system, max_tokens=16000).strip()
        except Exception as exc:  # noqa: BLE001
            if verbose:
                print(f"  调用失败: {str(exc)[:140]}", file=sys.stderr)
            return text, "reverted"

        if out == text:
            if verbose:
                print("  无错误，原样返回", file=sys.stderr)
            return text, "unchanged"

        problems = check(text, out)
        if not problems:
            if verbose:
                _, r = scope_ok(text, out)
                print(f"  纠错通过（相似度 {r:.3f}）", file=sys.stderr)
            return out, "proofread"

        if verbose:
            print(f"  第 {attempt + 1} 次越权: {'; '.join(problems)}",
                  file=sys.stderr)
        prompt = (f"你上一次的修改越权了：{'; '.join(problems)}。\n\n"
                  "重做一次。修错词、病句、标点，拗口处轻手顺一顺；"
                  "本来就通顺的句子一个字不许动；大幅重写不允许。\n\n"
                  f"原文：\n\n{text}")

    if verbose:
        print("  两次都越权，返回原文", file=sys.stderr)
    return text, "reverted"


def main() -> int:
    ap = argparse.ArgumentParser(description="第 ④ 段：纠错顺句（错词/病句/标点/拗口处，轻手）")
    ap.add_argument("file")
    ap.add_argument("-o", "--output")
    ap.add_argument("-m", "--model", default=DEFAULT_MODEL)
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    text = pathlib.Path(args.file).read_text(encoding="utf-8").strip()
    out, status = proofread(text, model=args.model, verbose=args.verbose)
    dst = args.output or args.file
    pathlib.Path(dst).write_text(out + "\n", encoding="utf-8")
    print(f"{status} -> {dst}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

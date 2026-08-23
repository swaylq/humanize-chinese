#!/usr/bin/env python3
"""Stage 2 of the v6 pipeline: LLM de-AI rewrite, guarded.

    secret exec OPENROUTER_API_KEY -- python3 scripts/pipeline/stage2_rewrite.py \
        examples/sample_general.txt -o /tmp/out.txt

The skill at skills/deai-rewrite/SKILL.md IS the prompt — it is loaded verbatim
as the system message, so editing the skill changes behaviour with no code
change. That is the point of routing this through a skill rather than a string
literal in Python.

Every rewrite is checked by scripts/pipeline/guards.py before it is accepted.
A rewrite that drops a number, a proper noun, a paragraph, or a quarter of its
length is retried once with the failures quoted back to the model, and if it
fails again the ORIGINAL text is returned unchanged. Refusing to edit beats
shipping a rewrite that lost content — that failure mode is what v6 exists to
end.
"""
from __future__ import annotations

import argparse
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve()
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "evals" / "corpus"))
sys.path.insert(0, str(HERE.parent))

from models import chat  # noqa: E402
import guards  # noqa: E402

SKILL_PATH = ROOT / "skills" / "deai-rewrite" / "SKILL.md"
DEFAULT_MODEL = "anthropic/claude-opus-5"


def load_skill(path: pathlib.Path = SKILL_PATH) -> str:
    text = path.read_text(encoding="utf-8")
    # strip the YAML front matter — it is metadata for the harness, not prompt
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            text = text[end + 4:]
    return text.strip()


def rewrite(text: str, *, model: str = DEFAULT_MODEL,
            skill: str | None = None, verbose: bool = False) -> tuple[str, str]:
    """Return (result_text, status). status is 'rewritten' | 'reverted'."""
    skill = skill or load_skill()
    system = (
        skill
        + "\n\n---\n\n你现在就按上面这份说明工作。用户给你一段中文，"
          "你只输出定点修改之后的正文，不解释、不加前言、不用 markdown 包裹。"
    )

    attempts = []
    prompt = f"请按说明对下面这段中文做定点去 AI 腔修改：\n\n{text}"

    for attempt in range(2):
        try:
            out = chat(model, prompt, system=system, max_tokens=16000).strip()
        except Exception as exc:  # noqa: BLE001
            if verbose:
                print(f"  调用失败: {str(exc)[:160]}", file=sys.stderr)
            return text, "reverted"

        problems = guards.check(text, out)
        attempts.append((out, problems))
        if not problems:
            if verbose:
                print(f"  第 {attempt + 1} 次通过守卫检查", file=sys.stderr)
            return out, "rewritten"

        if verbose:
            print(f"  第 {attempt + 1} 次未通过: {'; '.join(problems)}",
                  file=sys.stderr)
        if attempt == 0:
            prompt = (
                f"你上一次的修改没有通过检查，问题是：{'; '.join(problems)}。\n\n"
                "请重做。特别注意：原文的数字、专有名词、术语一个都不能少，"
                "段落数必须和原文一致，只删套话不删内容。\n\n"
                f"原文：\n\n{text}"
            )

    if verbose:
        print("  两次都未通过，返回原文", file=sys.stderr)
    return text, "reverted"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("input", help="input .txt file, or - for stdin")
    ap.add_argument("-o", "--output", default=None)
    ap.add_argument("-m", "--model", default=DEFAULT_MODEL)
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("--skill", default=None, help="override skill path")
    args = ap.parse_args()

    text = (sys.stdin.read() if args.input == "-"
            else pathlib.Path(args.input).read_text(encoding="utf-8")).strip()

    skill = load_skill(pathlib.Path(args.skill)) if args.skill else None
    out, status = rewrite(text, model=args.model, skill=skill,
                          verbose=args.verbose)

    if args.output:
        pathlib.Path(args.output).write_text(out + "\n", encoding="utf-8")
        print(f"{status} -> {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(out + "\n")
    return 0 if status == "rewritten" else 1


if __name__ == "__main__":
    sys.exit(main())

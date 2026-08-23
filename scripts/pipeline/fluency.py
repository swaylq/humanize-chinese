#!/usr/bin/env python3
"""Fluency jury — the H1 gate.

    secret exec OPENROUTER_API_KEY -- python3 scripts/pipeline/fluency.py \
        original.txt rewritten.txt

Three panel models read the rewrite and answer two questions: how fluent is it
(1-5), and quote any sentence that is actually ungrammatical or has a broken
collocation. The median score is the gate; GOAL.md H1 sets it at 4.0.

Asking for quoted evidence matters — a model asked only for a number will
produce a plausible number. A model asked to quote the broken sentence either
finds one or does not, and the quote can be checked against the text.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import pathlib
import statistics
import sys

HERE = pathlib.Path(__file__).resolve()
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "evals" / "corpus"))

from models import chat, parse_json_loose  # noqa: E402

JURY = [
    "anthropic/claude-opus-5",
    "openai/gpt-5.6-sol",
    "deepseek/deepseek-v4-pro-0813",
]

PROMPT = """你是中文母语的文字编辑。下面这段中文需要你判断它读起来通不通顺。

请只看语言本身，不要评价内容好坏、不要评价它像不像 AI 写的。

评分标准（1-5）：
5 = 完全通顺，看不出任何毛病
4 = 通顺，个别地方略生硬但不算错
3 = 有一两处明显别扭，但能读懂
2 = 多处搭配不当或成分残缺
1 = 大量病句，读不通

**病句**指：语法错误、搭配不当（例如「各个层面地评判」「更好地推进的必由之路」）、
成分残缺、前后不接、指代不明。只列真正的错误，不要列你觉得可以写得更好的地方。

只输出 JSON，不要解释：
{{"score": <1-5 的整数>, "defects": ["原文照抄的病句1", "病句2"]}}
没有病句就给空数组。

待评文本：
---
{text}
---"""


def judge_one(model: str, text: str, retries: int = 2) -> dict | None:
    # A juror that returns malformed JSON silently shrinks the panel, which
    # lowers the majority threshold — observed 2026-08-24 when deepseek emitted
    # a truncated object and long_blog was then judged by two models instead of
    # three. Retry before dropping anyone.
    last = None
    for _ in range(retries):
        try:
            d = parse_json_loose(chat(model, PROMPT.format(text=text),
                                      max_tokens=8000))
            return {"model": model, "score": int(d.get("score", 0)),
                    "defects": [str(x) for x in (d.get("defects") or [])]}
        except Exception as exc:  # noqa: BLE001
            last = exc
    sys.stderr.write(f"  jury {model} failed: {str(last)[:140]}\n")
    return None


def judge_confirmed(text: str, jury: list[str] | None = None) -> dict:
    """judge(), but a marginal pass is confirmed by a second round.

    Measured 2026-08-24 on one stage-2 output: judging the same unchanged text
    four times gave a real collocation error ("做出了更具竞争力的解决方案") in
    three runs and a clean sheet in one. A single round therefore misses a real
    defect about a quarter of the time, which is how that sentence passed the
    gate and then failed the acceptance judge on identical text.

    A clean, confident verdict (median >= 5.0, no defects, no singleton flags)
    ships on one round. Anything marginal gets a second, independent round and
    the defects of both are unioned. Costs 3 extra calls only where it matters.
    """
    first = judge(text, jury)
    confident = (first["median"] >= 5.0 and not first["defects"]
                 and not first.get("singleton_flags"))
    if confident or not first.get("votes"):
        return first

    second = judge(text, jury)
    if not second.get("votes"):
        return first

    merged = list(first["defects"])
    seen = {d["quote"] for d in merged}
    for d in second["defects"]:
        if d["quote"] not in seen:
            merged.append(d)
            seen.add(d["quote"])
    median = min(first["median"], second["median"])
    return {"median": median,
            "scores": first["scores"] + second["scores"],
            "votes": first["votes"] + second["votes"],
            "defects": merged,
            "singleton_flags": first.get("singleton_flags", 0)
                               + second.get("singleton_flags", 0),
            "rounds": 2,
            "passed": median >= 4.0 and not merged}


def judge(text: str, jury: list[str] | None = None) -> dict:
    jury = jury or JURY
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(jury)) as p:
        votes = [v for v in p.map(lambda m: judge_one(m, text), jury) if v]
    if not votes:
        return {"median": 0.0, "votes": [], "defects": [], "passed": False}
    scores = [v["score"] for v in votes]

    # Two filters, both learned from the 2026-08-24 calibration run.
    #
    # 1. A quote must actually occur in the text. Filters hallucinated
    #    evidence, which is the reason we ask for quotes and not just a score.
    # 2. A defect must be flagged by a MAJORITY of the jury. Measured on
    #    v5's Python output, every genuine broken sentence ("各个层面地评判",
    #    "更好地推进的必由之路", "这样一来实现真正意义上的因材施教") was quoted
    #    by all three jurors independently. The flags that appeared only once
    #    were grammatical sentences a juror found flat ("各方协同都起了作用。").
    #    Unanimity separates broken Chinese from taste; letting one juror veto
    #    would fail clean text.
    grounded: list[tuple[str, str]] = []
    for v in votes:
        for d in v["defects"]:
            probe = d.strip().strip("。，、.\"'「」")
            if probe and probe in text:
                grounded.append((v["model"], probe))

    need = len(votes) // 2 + 1
    defects = []
    for model, probe in grounded:
        # count jurors whose quote overlaps this one in either direction
        backers = {m for m, p in grounded if p in probe or probe in p}
        if len(backers) >= need and not any(d["quote"] in probe or probe in d["quote"]
                                            for d in defects):
            defects.append({"quote": probe, "backers": sorted(backers)})

    med = statistics.median(scores)
    return {"median": med, "scores": scores, "votes": votes,
            "defects": defects, "singleton_flags": len(grounded) - len(defects),
            "passed": med >= 4.0 and not defects}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args()

    results = {}
    for f in args.files:
        text = pathlib.Path(f).read_text(encoding="utf-8").strip()
        r = judge(text)
        results[f] = r
        mark = "PASS" if r["passed"] else "FAIL"
        print(f"{mark}  {f}  中位数 {r['median']:.1f}  分数 {r.get('scores')}")
        for d in r["defects"]:
            who = ", ".join(m.split("/")[-1] for m in d["backers"])
            print(f"      病句[{len(d['backers'])}票 {who}]: {d['quote']}")
        if r.get("singleton_flags"):
            print(f"      （另有 {r['singleton_flags']} 处单票标记，按口味分歧忽略）")

    if args.json_out:
        pathlib.Path(args.json_out).write_text(
            json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0 if all(r["passed"] for r in results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Score a v6 corpus file with the existing v5 detector.

    python3 evals/corpus/score_corpus.py evals/corpus/ai_pilot.jsonl

Answers the question GOAL.md opens with: is a detector calibrated on 2022-era
ChatGPT (HC3) still measuring anything on 2026 models? Prints a model x scene
table of fused scores, plus the rule-only and LR-only components so a divergence
between the two layers is visible rather than averaged away.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import statistics
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
os.environ.setdefault("PYTHONHASHSEED", "0")

from detect_cn import calculate_score, detect_patterns  # noqa: E402
from ngram_model import compute_lr_score  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from models import SHORT  # noqa: E402


def score(text: str) -> dict:
    issues, metrics = detect_patterns(text)
    rule = calculate_score(issues, metrics)
    lr = compute_lr_score(text)
    if lr is None:
        return {"rule": rule, "lr": None, "fused": rule}
    return {"rule": rule, "lr": lr["score"],
            "fused": round(0.2 * rule + 0.8 * lr["score"])}


def band(s: float) -> str:
    if s < 25:
        return "LOW"
    if s < 50:
        return "MEDIUM"
    if s < 75:
        return "HIGH"
    return "VERY HIGH"


def load(path: pathlib.Path) -> list[dict]:
    recs = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            recs.append(json.loads(line))
    return recs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("corpus")
    ap.add_argument("--json-out", default=None)
    ap.add_argument("--field", default="text",
                    help="which field to score (text | rewritten)")
    args = ap.parse_args()

    recs = load(pathlib.Path(args.corpus))
    if not recs:
        print("empty corpus")
        return 1

    for r in recs:
        r["scores"] = score(r[args.field])

    scenes = sorted({r["scene"] for r in recs})
    models = sorted({r["model"] for r in recs})

    print(f"\n=== fused score (rule x0.2 + LR x0.8), field={args.field}, "
          f"n={len(recs)} ===")
    head = f"{'model':<10}" + "".join(f"{s:>12}" for s in scenes) + f"{'ALL':>12}"
    print(head)
    print("-" * len(head))
    for m in models:
        row = f"{SHORT.get(m, m):<10}"
        allv = []
        for s in scenes:
            vals = [r["scores"]["fused"] for r in recs
                    if r["model"] == m and r["scene"] == s]
            allv += vals
            row += f"{statistics.mean(vals):>12.1f}" if vals else f"{'-':>12}"
        row += f"{statistics.mean(allv):>12.1f}" if allv else f"{'-':>12}"
        print(row)
    row = f"{'ALL':<10}"
    for s in scenes:
        vals = [r["scores"]["fused"] for r in recs if r["scene"] == s]
        row += f"{statistics.mean(vals):>12.1f}" if vals else f"{'-':>12}"
    allf = [r["scores"]["fused"] for r in recs]
    row += f"{statistics.mean(allf):>12.1f}"
    print("-" * len(head))
    print(row)

    print(f"\n=== layer split (mean over all {len(recs)}) ===")
    for key in ("rule", "lr", "fused"):
        vals = [r["scores"][key] for r in recs if r["scores"][key] is not None]
        if vals:
            print(f"  {key:<6} mean={statistics.mean(vals):6.1f}  "
                  f"median={statistics.median(vals):6.1f}  "
                  f"min={min(vals):3.0f}  max={max(vals):3.0f}")

    print("\n=== band distribution (fused) ===")
    from collections import Counter
    c = Counter(band(r["scores"]["fused"]) for r in recs)
    for b in ("LOW", "MEDIUM", "HIGH", "VERY HIGH"):
        n = c.get(b, 0)
        print(f"  {b:<10} {n:3d}  {100*n/len(recs):5.1f}%  "
              f"{'#' * round(40*n/len(recs))}")

    print("\n=== length ===")
    lens = [r.get("cn_chars", 0) for r in recs]
    print(f"  cn_chars mean={statistics.mean(lens):.0f} "
          f"min={min(lens)} max={max(lens)}")

    if args.json_out:
        pathlib.Path(args.json_out).write_text(
            json.dumps(recs, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\nwrote {args.json_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Compare detector scores across labelled groups; report real separation.

    PYTHONHASHSEED=0 python3 evals/corpus/compare_groups.py \
        human=evals/corpus/human_abstract.jsonl \
        ai2024=evals/corpus/ai2024_abstract.jsonl \
        ai2026=evals/corpus/ai2026_abstract.jsonl

A mean-score table alone cannot tell "the detector works" from "the detector
scores everything in this genre high". So this also prints, for every AI group
against the human group:

  AUC   — probability a random AI sample outscores a random human sample.
          0.5 = coin flip (detector is blind), 1.0 = perfect separation.
  d     — Cohen's d, the gap in standard deviations.
  FPR@T — share of HUMAN texts the tool would flag at threshold T. This is the
          number that decides whether a "降 AIGC" claim is honest: a detector
          that flags half of real papers is not detecting AI.
"""
from __future__ import annotations

import json
import os
import pathlib
import statistics
import sys
from collections import Counter

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


def auc(pos: list[float], neg: list[float]) -> float:
    """P(random pos > random neg), ties counted as half."""
    if not pos or not neg:
        return float("nan")
    wins = 0.0
    for p in pos:
        for n in neg:
            wins += 1.0 if p > n else (0.5 if p == n else 0.0)
    return wins / (len(pos) * len(neg))


def cohen_d(a: list[float], b: list[float]) -> float:
    if len(a) < 2 or len(b) < 2:
        return float("nan")
    va, vb = statistics.variance(a), statistics.variance(b)
    pooled = (((len(a) - 1) * va + (len(b) - 1) * vb) / (len(a) + len(b) - 2)) ** 0.5
    return (statistics.mean(a) - statistics.mean(b)) / pooled if pooled else float("nan")


def band(s: float) -> str:
    return ("LOW" if s < 25 else "MEDIUM" if s < 50
            else "HIGH" if s < 75 else "VERY HIGH")


def main() -> int:
    specs = []
    for arg in sys.argv[1:]:
        if "=" not in arg:
            print(f"usage: name=path.jsonl ... (got {arg!r})", file=sys.stderr)
            return 2
        name, path = arg.split("=", 1)
        specs.append((name, pathlib.Path(path)))
    if not specs:
        print(__doc__)
        return 2

    groups: dict[str, list] = {}
    for name, path in specs:
        recs = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()
                if l.strip()]
        for r in recs:
            r["scores"] = score(r["text"])
        groups[name] = recs
        print(f"scored {len(recs):3d} from {path}", file=sys.stderr)

    print("\n=== group summary (fused score, higher = more AI-looking) ===")
    hdr = (f"{'group':<10}{'n':>5}{'chars':>8}{'mean':>8}{'median':>8}"
           f"{'sd':>7}{'min':>6}{'max':>6}")
    print(hdr)
    print("-" * len(hdr))
    for name, recs in groups.items():
        f = [r["scores"]["fused"] for r in recs]
        c = [r["cn_chars"] for r in recs]
        sd = statistics.stdev(f) if len(f) > 1 else 0.0
        print(f"{name:<10}{len(f):>5}{statistics.mean(c):>8.0f}"
              f"{statistics.mean(f):>8.1f}{statistics.median(f):>8.1f}"
              f"{sd:>7.1f}{min(f):>6.0f}{max(f):>6.0f}")

    if "human" in groups:
        human = [r["scores"]["fused"] for r in groups["human"]]
        print("\n=== separation vs human ===")
        hdr2 = f"{'group':<10}{'AUC':>7}{'d':>7}{'gap':>7}   verdict"
        print(hdr2)
        print("-" * (len(hdr2) + 20))
        for name, recs in groups.items():
            if name == "human":
                continue
            ai = [r["scores"]["fused"] for r in recs]
            a, d = auc(ai, human), cohen_d(ai, human)
            gap = statistics.mean(ai) - statistics.mean(human)
            if a >= 0.90:
                v = "strong separation"
            elif a >= 0.75:
                v = "usable"
            elif a >= 0.65:
                v = "weak"
            else:
                v = "近乎盲猜 / near-blind"
            print(f"{name:<10}{a:>7.3f}{d:>7.2f}{gap:>7.1f}   {v}")

        print("\n=== false-positive rate on HUMAN text at each threshold ===")
        print("(share of real human papers the tool would tell you to 降重)")
        for t in (25, 35, 50, 60, 75):
            fp = sum(1 for s in human if s >= t) / len(human)
            print(f"  score >= {t:>3}:  {100*fp:5.1f}%  "
                  f"{'#' * round(40*fp)}")

    print("\n=== band distribution ===")
    for name, recs in groups.items():
        c = Counter(band(r["scores"]["fused"]) for r in recs)
        parts = "  ".join(f"{b}={c.get(b,0)}"
                          for b in ("LOW", "MEDIUM", "HIGH", "VERY HIGH"))
        print(f"  {name:<10} {parts}")

    # per-model breakdown for groups that have several models
    for name, recs in groups.items():
        models = sorted({r.get("model") for r in recs})
        if len(models) <= 1:
            continue
        print(f"\n=== {name} by model ===")
        for m in models:
            f = [r["scores"]["fused"] for r in recs if r.get("model") == m]
            if not f:
                continue
            extra = ""
            if "human" in groups:
                extra = f"  AUC={auc(f, human):.3f}"
            print(f"  {SHORT.get(m, m):<12} n={len(f):>3} "
                  f"mean={statistics.mean(f):>6.1f} "
                  f"median={statistics.median(f):>6.1f}{extra}")

    print("\n=== layer split (mean) ===")
    print(f"{'group':<10}{'rule':>8}{'LR':>8}{'fused':>8}")
    for name, recs in groups.items():
        r_ = [x["scores"]["rule"] for x in recs]
        l_ = [x["scores"]["lr"] for x in recs if x["scores"]["lr"] is not None]
        f_ = [x["scores"]["fused"] for x in recs]
        print(f"{name:<10}{statistics.mean(r_):>8.1f}"
              f"{statistics.mean(l_) if l_ else float('nan'):>8.1f}"
              f"{statistics.mean(f_):>8.1f}")

    if "human" in groups:
        print("\n=== layer-wise AUC vs human (which layer actually separates) ===")
        for layer in ("rule", "lr", "fused"):
            hv = [r["scores"][layer] for r in groups["human"]
                  if r["scores"][layer] is not None]
            line = f"  {layer:<6}"
            for name, recs in groups.items():
                if name == "human":
                    continue
                av = [r["scores"][layer] for r in recs
                      if r["scores"][layer] is not None]
                line += f"  {name}={auc(av, hv):.3f}"
            print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())

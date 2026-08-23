#!/usr/bin/env python3
"""Extract length-matched human and 2024-model control groups from NLPCC2025.

The human side of NLPCC2025's abstract genre comes from CSL (Chinese Scientific
Literature — CNKI paper abstracts, collected before LLMs were writing papers),
so it is genuine human academic Chinese, which is exactly the control GOAL.md
asks for. The AI side of the same genre was written by GPT-4o / GLM-4-flash /
Qwen-turbo, i.e. the 2024 generation — useful as a middle point between human
and the 2026 panel.

    python3 evals/corpus/build_control.py \
        --genre abstract --min-chars 280 --max-chars 400 --n 60 \
        --out-dir evals/corpus

Writes <out-dir>/human_<genre>.jsonl and <out-dir>/ai2024_<genre>.jsonl in the
same record shape as gen_corpus.py so score_corpus.py can read either.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from normalize import count_cn, normalize_punct, punct_profile  # noqa: E402

DEFAULT_SRC = pathlib.Path.home() / "claudeclaw/humanize/data/processed/nlpcc2025_schema_v1.jsonl"

# Scene name the detector/rewriter use, per genre in the NLPCC schema.
GENRE_TO_SCENE = {
    "abstract": "academic",
    "blog_post": "blog",
    "news_report": "general",
    "story": "novel",
    "qa": "general",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(DEFAULT_SRC))
    ap.add_argument("--genre", default="abstract")
    ap.add_argument("--min-chars", type=int, default=280)
    ap.add_argument("--max-chars", type=int, default=400)
    ap.add_argument("--n", type=int, default=60, help="samples per label")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out-dir", default="evals/corpus")
    args = ap.parse_args()

    src = pathlib.Path(args.src)
    if not src.exists():
        print(f"source corpus not found: {src}", file=sys.stderr)
        return 2

    pools: dict[str, list] = {"human": [], "ai": []}
    scanned = 0
    for line in src.open(encoding="utf-8"):
        if not line.strip():
            continue
        r = json.loads(line)
        scanned += 1
        if r.get("genre") != args.genre:
            continue
        label = r.get("label")
        if label not in pools:
            continue
        text = normalize_punct(r.get("text", ""))
        n = count_cn(text)
        if not (args.min_chars <= n <= args.max_chars):
            continue
        pools[label].append({
            "id": f"{label}-{args.genre}-{len(pools[label]):03d}",
            "scene": GENRE_TO_SCENE.get(args.genre, args.genre),
            "model": "human" if label == "human" else "ai2024-mixed",
            "label": label,
            "topic": None,
            "text": text,
            "cn_chars": n,
            "source": f"nlpcc2025/{r.get('source', '?')}",
            "src_model": r.get("model"),
        })

    print(f"scanned {scanned} records; in-band pool: "
          f"human={len(pools['human'])} ai2024={len(pools['ai'])}", file=sys.stderr)

    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)

    for label, fname in (("human", f"human_{args.genre}.jsonl"),
                         ("ai", f"ai2024_{args.genre}.jsonl")):
        pool = pools[label]
        if len(pool) < args.n:
            print(f"WARNING: only {len(pool)} {label} samples in band, "
                  f"wanted {args.n}", file=sys.stderr)
        pick = rng.sample(pool, min(args.n, len(pool)))
        path = out_dir / fname
        with path.open("w", encoding="utf-8") as fh:
            for i, rec in enumerate(pick):
                rec["id"] = f"{'human' if label == 'human' else 'ai2024'}-{args.genre}-{i:03d}"
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        lens = [r["cn_chars"] for r in pick]
        print(f"wrote {len(pick):3d} -> {path}  "
              f"cn_chars mean={sum(lens)/len(lens):.0f} "
              f"min={min(lens)} max={max(lens)}", file=sys.stderr)
        # prove normalisation ran
        joined = "".join(r["text"] for r in pick)
        print(f"    punct after normalise: {punct_profile(joined)}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())

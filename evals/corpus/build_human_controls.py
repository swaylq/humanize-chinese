#!/usr/bin/env python3
"""Assemble a human control group for each scene, from real published text.

    python3 evals/corpus/build_human_controls.py --out-dir evals/corpus

H4 requires the human side to come from real published corpora, never from a
model. Every source below is named, dated and pre-LLM where that matters, and
each record carries a `provenance` field so a reader can check the claim.

  academic   CSL — CNKI paper abstracts, via NLPCC2025 train (source=csl)
  general    CNewSum — news writing, via NLPCC2025 train (source=cnewsum)
  social     ASAP — Dianping restaurant reviews, via NLPCC2025 train (source=asap)
  blog       CUDRT misc — news/tech commentary (data/human_misc_corpus.jsonl)
  novel      literary fiction (data/human_novel_corpus.jsonl)

  workplace  NO SOURCE. Internal work reports are private by nature; there is
             no public human corpus of them. Rather than substitute something
             that merely looks similar and quietly weaken the comparison, the
             workplace scene ships without a human control and every table says
             so. See --report for the gap printed explicitly.

Only NLPCC records carrying a real `source` are used: its dev/test splits have
no source column, so data/prepare_nlpcc2025.py guessed their genre by keyword
and mislabels (a personal narrative containing 研究菜单 was filed as an academic
abstract). Provenance is required, never inferred.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from normalize import count_cn, normalize_punct  # noqa: E402

DATA = pathlib.Path.home() / "claudeclaw/humanize/data"
NLPCC_TRAIN = DATA / "raw/nlpcc2025/data/train.json"

# scene -> (loader key, length band, provenance string)
SCENES = {
    "academic": ("nlpcc:csl", (280, 400),
                 "CSL 中文科技文献（知网论文摘要），经 NLPCC2025 train 分发，采集早于大模型写作"),
    "general": ("nlpcc:cnewsum", (280, 520),
                "CNewSum 新闻写作语料，经 NLPCC2025 train 分发"),
    "social": ("nlpcc:asap", (250, 460),
               "ASAP 大众点评餐厅评论（真实用户撰写），经 NLPCC2025 train 分发"),
    "blog": ("file:human_misc_corpus.jsonl", (900, 1600),
             "CUDRT 新闻/科技评论语料 data/human_misc_corpus.jsonl"),
    "novel": ("file:human_novel_corpus.jsonl", (700, 1000),
              "中文文学小说正文 data/human_novel_corpus.jsonl"),
}

NO_HUMAN_CONTROL = {
    "workplace": "内部工作汇报本质上不公开，没有可用的真人公开语料。"
                 "宁可留空并在每张表上注明，也不拿相似体裁顶替。",
}


def load_nlpcc(source: str) -> list[str]:
    if not NLPCC_TRAIN.exists():
        return []
    rows = json.load(NLPCC_TRAIN.open(encoding="utf-8"))
    return [r["text"] for r in rows
            if r.get("source") == source and r.get("model") == "human"]


def load_file(name: str) -> list[str]:
    p = DATA / name
    if not p.exists():
        return []
    out = []
    for line in p.open(encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            if str(r.get("label")) in ("0", "human"):
                out.append(r["text"])
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="evals/corpus")
    ap.add_argument("--n", type=int, default=50, help="samples per scene")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--report", action="store_true",
                    help="only print what is available, write nothing")
    args = ap.parse_args()

    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)
    summary = []

    for scene, (key, (lo, hi), provenance) in SCENES.items():
        kind, ref = key.split(":", 1)
        raw = load_nlpcc(ref) if kind == "nlpcc" else load_file(ref)
        pool = []
        for t in raw:
            t = normalize_punct(t)
            n = count_cn(t)
            if lo <= n <= hi:
                pool.append((t, n))

        if not pool:
            summary.append((scene, 0, 0, "语料不可用", provenance))
            print(f"WARNING: {scene} 没有可用样本（源 {key}）", file=sys.stderr)
            continue

        pick = rng.sample(pool, min(args.n, len(pool)))
        mean = sum(n for _, n in pick) / len(pick)
        summary.append((scene, len(pick), mean, f"{lo}-{hi} 字", provenance))

        if not args.report:
            path = out_dir / f"human_{scene}.jsonl"
            with path.open("w", encoding="utf-8") as fh:
                for i, (t, n) in enumerate(pick):
                    fh.write(json.dumps({
                        "id": f"human-{scene}-{i:03d}",
                        "scene": scene, "model": "human", "label": "human",
                        "topic": None, "text": t, "cn_chars": n,
                        "source": key, "provenance": provenance,
                    }, ensure_ascii=False) + "\n")

    print("\n=== 人类对照组 ===")
    hdr = f"{'场景':<12}{'篇数':>6}{'均长':>8}  {'长度带':<12} 来源"
    print(hdr)
    print("-" * 96)
    for scene, n, mean, band, prov in summary:
        print(f"{scene:<12}{n:>6}{mean:>8.0f}  {band:<12} {prov[:46]}")
    for scene, why in NO_HUMAN_CONTROL.items():
        print(f"{scene:<12}{'—':>6}{'—':>8}  {'（无）':<12} {why[:46]}")
    print("-" * 96)
    print(f"有对照组的场景 {len(SCENES)} 个，"
          f"明确无对照组 {len(NO_HUMAN_CONTROL)} 个（见上方原因）")
    return 0


if __name__ == "__main__":
    sys.exit(main())

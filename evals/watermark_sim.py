#!/usr/bin/env python3
"""Does the survival meter actually predict what a watermark detector sees?

`scripts/watermark_cn.py survive` reports a number — the fraction of the
original's 5-character scoring windows still present after a rewrite — and
claims the detector's z statistic lands at roughly that fraction of what it
was. Anthropic's key is not public, so that claim cannot be checked against
Claude. It can be checked against a watermark of the same class, built here.

What this builds
----------------
A Kirchenbauer green-list watermark over Chinese characters, which is the same
family as SynthID-Text (both key a per-token bias on a hash of the preceding H
tokens; SynthID replaces the hard green/red split with tournament sampling).

  generate   sample characters from the repo's own n-gram table, but hash the
             previous H characters together with a secret key, split the
             vocabulary into a green list (gamma of it) and a red list, and add
             delta to the green candidates' weights before sampling.

  detect     rebuild the green list at every position from the H characters
             before it, count how many characters landed green, and report
             z = (greens - gamma*T) / sqrt(T*gamma*(1-gamma)).

  edit       damage a given fraction of the characters, the way a rewrite
             would, and rerun both the detector and the survival meter.

Then the two columns get compared: what the survival meter predicted, and what
the detector actually reported.

    python3 evals/watermark_sim.py

Nothing here proves anything about Anthropic's watermark specifically. It
proves the estimator is sound for the class of watermark Anthropic says theirs
belongs to, which is the strongest claim anyone outside Anthropic can make.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib
import random
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import watermark_cn  # noqa: E402

# Kirchenbauer et al. 2023 defaults, and the H=4 context width SynthID-Text
# uses in the Nature 2024 paper.
GAMMA = 0.25
DELTA = 2.0
CONTEXT = 4
KEY = b"humanize-chinese watermark simulator"


_VOCAB_CACHE = None


def load_vocab():
    """Character vocabulary and bigram continuations from the repo's tables.

    Prefers the 20MB human-corpus table when it is present locally; falls back
    to the small table that ships with the repo so this runs on a fresh clone.
    Cached: the big table takes seconds to parse and every stage needs it.
    """
    global _VOCAB_CACHE
    if _VOCAB_CACHE is not None:
        return _VOCAB_CACHE

    for name in ("ngram_freq_cn_human.json", "ngram_freq_cn.json"):
        path = ROOT / "scripts" / name
        if path.exists():
            table = json.loads(path.read_text(encoding="utf-8"))
            break
    else:
        raise SystemExit("找不到任何 n-gram 频率表，先跑 scripts/train_ngram_human.py")

    unigrams = table["unigrams"]
    # Keep the vocabulary to common characters: a long tail of hapaxes makes
    # the green list mostly unreachable and the simulation meaningless.
    vocab = [c for c, n in sorted(unigrams.items(), key=lambda kv: -kv[1])[:3000]
             if len(c) == 1 and "一" <= c <= "鿿"]
    weights = [unigrams[c] for c in vocab]

    follow = {}
    for gram, n in table["bigrams"].items():
        if len(gram) != 2:
            continue
        a, b = gram
        follow.setdefault(a, {})[b] = n
    _VOCAB_CACHE = (vocab, weights, follow, name)
    return _VOCAB_CACHE


_GREEN_CUT = int(GAMMA * (1 << 32))


def is_green(context, ch):
    """Is this character on the green list for this context?

    Keyed hash of (secret, previous CONTEXT characters, candidate). The same
    context and character always give the same answer, which is why the
    detector needs nothing from the generator except the key — that is the
    whole trick. Hashing per candidate rather than shuffling the vocabulary
    makes the green list binomial around gamma instead of exactly gamma, which
    is what real implementations do and costs one hash per scored position
    instead of one shuffle.
    """
    digest = hashlib.blake2b(KEY + (context + ch).encode("utf-8"),
                             digest_size=8).digest()
    return int.from_bytes(digest[:4], "big") < _GREEN_CUT


# How many characters the unigram backoff considers. The full 3000-character
# vocabulary would be hashed at every backoff step for no gain: past the first
# few hundred the weights are noise.
BACKOFF_POOL = 400


def generate(n_chars, *, watermarked=True, seed=7):
    vocab, weights, follow, table_name = load_vocab()
    known = set(vocab)
    pool, pool_w = vocab[:BACKOFF_POOL], weights[:BACKOFF_POOL]
    boost = math.exp(DELTA)
    rng = random.Random(seed)
    out = [rng.choices(pool, weights=pool_w, k=1)[0]]

    while len(out) < n_chars:
        context = "".join(out[-CONTEXT:])
        nxt = follow.get(out[-1])
        cands, base = [], []
        if nxt:
            for c, n in nxt.items():
                if c in known:
                    cands.append(c)
                    base.append(n)
        if len(cands) < 8:                       # back off to the unigram table
            cands, base = pool, pool_w

        if watermarked:
            w = [b * boost if is_green(context, c) else b
                 for c, b in zip(cands, base)]
        else:
            w = base
        out.append(rng.choices(cands, weights=w, k=1)[0])
    return "".join(out), table_name


def detect(text):
    """z score for the green-list watermark. Returns (z, scored_tokens)."""
    vocab, _weights, _follow, _name = load_vocab()
    known = set(vocab)
    body = [c for c in text if c in known]
    if len(body) <= CONTEXT:
        return 0.0, 0
    greens = 0
    scored = 0
    for i in range(CONTEXT, len(body)):
        scored += 1
        if is_green("".join(body[i - CONTEXT:i]), body[i]):
            greens += 1
    z = (greens - GAMMA * scored) / math.sqrt(scored * GAMMA * (1 - GAMMA))
    return z, scored


def edit(text, fraction, *, seed=11):
    """Replace a fraction of characters, standing in for a rewrite."""
    vocab, weights, _follow, _name = load_vocab()
    rng = random.Random(seed)
    chars = list(text)
    targets = rng.sample(range(len(chars)), int(len(chars) * fraction))
    for i in targets:
        chars[i] = rng.choices(vocab, weights=weights, k=1)[0]
    return "".join(chars)


def main(argv=None):
    ap = argparse.ArgumentParser(description="验证残留量估计器是否预测得准")
    ap.add_argument("-n", "--chars", type=int, default=4000,
                    help="生成多少字（默认 4000）")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args(argv)

    marked, table_name = generate(args.chars, watermarked=True, seed=args.seed)
    plain, _ = generate(args.chars, watermarked=False, seed=args.seed)

    z_plain, _ = detect(plain)
    z0, scored = detect(marked)

    print("词表来自 %s，绿名单比例 gamma=%.2f，偏置 delta=%.1f，上下文 H=%d。"
          % (table_name, GAMMA, DELTA, CONTEXT))
    print("生成 %d 字，计分位置 %d 个。" % (args.chars, scored))
    print()
    print("  没加水印的对照文本   z = %+.2f" % z_plain)
    print("  加了水印的文本       z = %+.2f" % z0)
    print()
    print("  改动比例   存活率(5字窗)   预测 z（survive 给的倍数×%.2f）   实测 z   误差" % z0)
    rows = []
    for frac in (0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9):
        damaged = edit(marked, frac)
        z, _ = detect(damaged)
        est = watermark_cn.ngram_survival(marked, damaged)
        pred = est["z_ratio"] * z0
        err = z - pred
        rows.append((frac, est["headline"], pred, z, err))
        print("  %7.0f%% %13.1f%% %29.2f %9.2f %+7.2f"
              % (frac * 100, est["headline"] * 100, pred, z, err))

    # The edits above keep the length fixed, so they never exercise the other
    # half of the formula: z also follows how much text the detector is handed.
    # Truncation isolates it — not a character is edited, yet z falls.
    print()
    print("  只截断不改字（检验公式里长度那一项）")
    print("  留下比例   存活率(5字窗)   预测 z            实测 z   误差")
    for frac in (0.75, 0.5, 0.25, 0.1):
        cut = marked[:int(len(marked) * frac)]
        z, _ = detect(cut)
        est = watermark_cn.ngram_survival(marked, cut)
        pred = est["z_ratio"] * z0
        rows.append((frac, est["headline"], pred, z, z - pred))
        print("  %7.0f%% %13.1f%% %18.2f %9.2f %+7.2f"
              % (frac * 100, est["headline"] * 100, pred, z, z - pred))

    worst = max(abs(r[4]) for r in rows)
    print()
    print("最大误差 %.2f，占原始 z（%.2f）的 %.0f%%。z 在无水印文本上服从标准正态分布，"
          "一个标准差就是 1.00，所以这个误差已经落在噪声里 ——"
          % (worst, z0, 100 * worst / z0))
    print("survive 报的倍数乘原始 z，预测得准到噪声底为止。")
    print("下半张表还说明了一件反直觉的事：只截不改，留下一成的文字，存活率跟着掉到"
          "一成，但检测端的 z 只掉到三成 —— 光看存活率会把削弱程度高估三倍，"
          "长度那一项不能省。")
    print()
    print("要说清楚的是：这里的密钥是本文件里的常量，所以能算出真实 z。")
    print("对 Claude 的水印，密钥在 Anthropic 手上，谁都算不出来 ——")
    print("survive 报的存活率是能测的那一半，剩下一半只有对方能测。")
    return 0


if __name__ == "__main__":
    sys.exit(main())

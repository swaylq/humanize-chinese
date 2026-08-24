#!/usr/bin/env python3
"""Stage ③ of the skill pipeline: scene-routed phrase replacement, offline.

    ./humanize replace 文本.txt -o 改后.txt --compare
    python3 scripts/replace_cn.py 文本.txt --scene academic

What it does, in order:
  1. detect the scene (academic / social / novel / general) unless told
  2. apply that scene's curated replacement tables from patterns_cn.json
     (academic gets the 120+ academic table on top of the general 220+)
  3. a punctuation-only rhythm pass (scripts/pipeline/rhythm.py)
  4. verify nothing was damaged: numbers, Latin tokens and paragraph count
     must survive untouched, or the whole edit is discarded

Why this is deliberately narrower than the v5 rewriter: v5 also did synonym
swaps from a 38k-word thesaurus, statistical mutations and filler insertion,
and those three are where its broken Chinese came from (measured 2026-08-24:
fluency 2.0/5, 5-17 broken sentences per sample). The curated tables here are
phrase-level template fixes (综上所述→总之, 本文旨在→本文尝试) — the safe kind.
Replacements never fire inside quotes or brackets.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import random
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve()
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE.parent / "pipeline"))

import guards  # noqa: E402
import rhythm  # noqa: E402

PATTERNS = HERE.parent / "patterns_cn.json"

# ---------------------------------------------------------------------------
# scene detection — transparent heuristics, overridable with --scene
# ---------------------------------------------------------------------------

# Two tiers. Weak markers (显著/机制/研究表明) appear in any formal prose —
# the social caricature sample is full of them and was misrouted to academic on
# the first run. Strong markers are the ones that only papers use.
_ACADEMIC_STRONG = ["本文", "本研究", "笔者", "摘要", "参考文献", "文献综述"]
_ACADEMIC_WEAK = ["研究表明", "综上所述", "实验", "文献", "样本", "显著", "机制"]
_SOCIAL_MARKERS = ["姐妹", "宝子", "家人们", "！！", "绝了", "冲鸭", "笔记",
                   "安利", "种草", "打卡", "分享一个"]
_EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")


def detect_scene(text: str) -> str:
    strong = sum(text.count(m) for m in _ACADEMIC_STRONG)
    aca = strong * 2 + sum(text.count(m) for m in _ACADEMIC_WEAK)
    soc = sum(text.count(m) for m in _SOCIAL_MARKERS) + len(_EMOJI.findall(text))
    n = guards.cn_chars(text)
    dialogue = text.count("「") + text.count("“")
    if strong >= 1 and aca >= 4 and aca > soc:
        return "academic"
    if soc >= 3:
        return "social"
    if n >= 1500 and dialogue >= 3:
        return "novel"
    return "general"


# ---------------------------------------------------------------------------
# replacement engine
# ---------------------------------------------------------------------------

_REGEX_CHARS = set("\\^$*+?()[]|{")
_QUOTE_OPEN = "「『（(“"
_QUOTE_CLOSE = "」』）)”"


def _load_tables(scene: str) -> list[tuple[str, list[str], bool]]:
    """Return [(pattern, candidates, is_regex)] for the scene, longest first.

    Routing: academic applies the academic table FIRST (its phrases are more
    specific, e.g. 具有重要的理论意义和实践价值 must beat 具有重要意义), then the
    general table. Everything else gets the general table only — social and
    novel share it because the template phrases they suffer from are the same;
    what differs between those scenes is tone, which is stage ①/②'s job, not a
    lookup table's.
    """
    data = json.loads(PATTERNS.read_text(encoding="utf-8"))
    tables = []
    if scene == "academic":
        tables.append(data["academic_patterns"]["replacements"])
    tables.append(data["replacements"])

    entries = []
    for table in tables:
        for pat, cands in table.items():
            if pat == "description" or not isinstance(cands, list) or not cands:
                continue
            entries.append((pat, cands, any(c in _REGEX_CHARS for c in pat)))
    # longest pattern first so specific phrases beat their substrings
    entries.sort(key=lambda e: len(e[0]), reverse=True)
    return entries


def _quote_depth_map(text: str) -> list[int]:
    depth, out = 0, []
    for ch in text:
        if ch in _QUOTE_OPEN:
            depth += 1
        elif ch in _QUOTE_CLOSE:
            depth = max(0, depth - 1)
        out.append(depth)
    return out


# Learned from a jury run on this script's own first output (median 2.0/5):
# the failures were all ≤3-character word-level swaps fused to a neighbour —
# 日益→越来越 producing 越来越深化, 全方位地→各方面地 producing 各方面地评估.
# Word-level substitution without collocation awareness is exactly the v5
# disease, so this stage refuses it: phrase level only (≥4 chars), and only at
# a clause boundary so nothing gets welded onto the preceding word. Word-level
# work belongs to stage ②, where the LLM can read the collocation.
_MIN_PATTERN_CHARS = 4
_BOUNDARY = set("。！？；：\n，、 \t")
# Candidates the jury flagged as wrong-register or self-colliding.
_BAD_CANDIDATES = {"另一边", "以此达到", "这里有一个值得关注的细节"}


def apply_replacements(text: str, scene: str, seed: int | None = 42
                       ) -> tuple[str, list[str]]:
    """Replace curated template phrases; never inside quotes/brackets."""
    rng = random.Random(seed)
    edits: list[str] = []
    replaced_spans_total = 0

    for pat, cands, is_regex in _load_tables(scene):
        if not is_regex and len(pat) < _MIN_PATTERN_CHARS:
            continue  # word-level swap — stage ② territory
        cands = [c for c in cands if c not in _BAD_CANDIDATES]
        if not cands:
            continue
        try:
            regex = re.compile(pat) if is_regex else re.compile(re.escape(pat))
        except re.error:
            continue
        depths = _quote_depth_map(text)
        out, last, changed = [], 0, 0
        for m in regex.finditer(text):
            if m.start() >= len(depths) or depths[m.start()] != 0:
                continue  # inside quotes — a citation is evidence, not AI tone
            if m.start() > 0 and text[m.start() - 1] not in _BOUNDARY:
                continue  # mid-clause: risk of welding onto the previous word
            choice = rng.choice(cands)
            # regex patterns may carry groups; only literal-safe substitution
            rep = m.expand(choice) if is_regex and "\\" in choice else choice
            out.append(text[last:m.start()]); out.append(rep)
            last = m.end(); changed += 1
        if changed:
            out.append(text[last:])
            text = "".join(out)
            replaced_spans_total += changed
            edits.append(f"{pat[:20]}→ ×{changed}")

    return text, edits


# ---------------------------------------------------------------------------
# entry
# ---------------------------------------------------------------------------

def process(text: str, scene: str = "auto", seed: int | None = 42,
            use_rhythm: bool = True) -> tuple[str, dict]:
    picked = detect_scene(text) if scene == "auto" else scene
    out, edits = apply_replacements(text, picked, seed)

    rhythm_edits: list[str] = []
    if use_rhythm:
        polished, rhythm_edits = rhythm.polish(out)
        if rhythm.verify_invariant(out, polished):
            out = polished
        else:
            rhythm_edits = []

    # the hard gate: facts survive or the whole edit is discarded
    problems = guards.check(text, out, min_length_ratio=0.85,
                            max_length_ratio=1.15)
    if problems:
        return text, {"scene": picked, "reverted": problems,
                      "replacements": 0, "rhythm": 0}
    return out, {"scene": picked, "reverted": None,
                 "replacements": len(edits), "rhythm": len(rhythm_edits),
                 "detail": edits + rhythm_edits}


def _detect_score(path: str) -> str:
    p = subprocess.run([sys.executable, str(HERE.parent / "detect_cn.py"),
                        path, "-s"], capture_output=True, text=True)
    return p.stdout.strip() or "?"


def main() -> int:
    ap = argparse.ArgumentParser(description="按文体路由的词语替换（离线，第 ③ 段）")
    ap.add_argument("file")
    ap.add_argument("-o", "--output")
    ap.add_argument("--scene", default="auto",
                    choices=["auto", "general", "academic", "social", "novel"])
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--no-rhythm", action="store_true")
    ap.add_argument("--compare", action="store_true", help="打印改写前后检测分")
    ap.add_argument("-q", "--quiet", action="store_true")
    args = ap.parse_args()

    text = pathlib.Path(args.file).read_text(encoding="utf-8").strip()
    out, info = process(text, args.scene, args.seed, not args.no_rhythm)

    if not args.quiet:
        if info["reverted"]:
            sys.stderr.write("守卫未通过，已原样返回："
                             + "; ".join(info["reverted"]) + "\n")
        else:
            sys.stderr.write(f"文体={info['scene']} · 替换 {info['replacements']} 组 · "
                             f"断句 {info['rhythm']} 处\n")

    dst = args.output or args.file + ".out"
    pathlib.Path(dst).write_text(out + "\n", encoding="utf-8")
    if not args.quiet:
        sys.stderr.write(f"-> {dst}\n")

    if args.compare:
        before, after = _detect_score(args.file), _detect_score(dst)
        print(f"改写前 {before}  →  改写后 {after}")
    elif not args.output:
        sys.stdout.write(out + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

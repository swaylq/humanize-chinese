#!/usr/bin/env python3
"""Meaning-preservation guards shared by pipeline stages 2 and 3.

H2 in projects/v6-refactor/GOAL.md requires that a rewrite's effect on meaning
be checkable, not asserted. These are the mechanical half of that check — cheap,
deterministic, and they run on every rewrite. The judgement half (fluency,
over-correction) needs a model and lives in the stage scripts.

The guiding rule for the whole v6 rewrite: a rewrite that fails a guard is
reverted. Never shipped with a warning.
"""
from __future__ import annotations

import re

# Digit runs including decimals, percentages and ranges: 12, 3.5, 60%, 2026
_NUM = re.compile(r"\d+(?:[.,]\d+)*%?")
# Latin runs (model names, acronyms, chemical shorthand): GC-MS, GPT, HS-SPME
_LATIN = re.compile(r"[A-Za-z][A-Za-z0-9./-]{1,}")
_CJK = r"一-鿿"


def numbers(text: str) -> list[str]:
    """Every numeric token, normalised so 1,200 and 1200 compare equal."""
    return sorted(n.replace(",", "") for n in _NUM.findall(text))


def latin_tokens(text: str) -> list[str]:
    return sorted(t.upper() for t in _LATIN.findall(text))


def paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]


# The template phrases stage 2 is supposed to delete. Used to predict how much
# a text SHOULD shrink: a fixed length floor punishes a correct rewrite of a
# heavily padded input. examples/sample_general.txt is ~1/3 boilerplate, so an
# honest de-AI pass takes it to ~0.68 — which a flat 0.75 floor would reject
# even though not one claim was lost.
_FILLER = [
    # A: value-inflation skeletons (matched loosely, they carry a clause)
    r"不仅[^，。；]{0,12}更是", r"与其说[^，。；]{0,12}不如说",
    r"真正的[^，。；]{0,10}是", r"这不只是[^，。；]{0,12}这是",
    # B: significance inflation
    r"标志着", r"体现了", r"见证了", r"具有重要(的)?(意义|价值)",
    r"将重新定义", r"为[^，。；]{0,12}提供了有力支撑", r"注入新的活力",
    r"开创[^，。；]{0,10}新局面", r"广阔的发展前景",
    # C: promo register
    r"赋能", r"助力", r"致力于", r"匠心", r"极致", r"深度融合",
    r"全方位(地)?", r"多维度(地)?", r"闭环", r"抓手", r"协同增效",
    r"高质量发展", r"新质生产力", r"数字化转型",
    # D: transition filler
    r"综上所述", r"总而言之", r"归根结底", r"值得注意的是", r"不难发现",
    r"换句话说", r"与此同时", r"由此可见", r"不言而喻", r"众所周知",
    r"不可否认", r"值得一提的是", r"我们有理由相信",
    # E: menu-announcing openers
    r"先说结论", r"一句话总结", r"说白了", r"简单来说", r"划重点",
    # F: all-purpose outlook endings
    r"未来可期", r"让我们拭目以待", r"前景广阔", r"任重而道远",
    r"开创更加美好的未来",
    # G: template openers
    r"随着[^，。；]{0,14}的不断发展", r"在当今[^，。；]{0,12}的时代",
    r"在[^，。；]{0,12}的背景下", r"作为[^，。；]{0,12}的重要组成部分",
    # H: three-part labels
    r"首先[，、]", r"其次[，、]", r"最后[，、]", r"一方面[，、]",
    r"另一方面[，、]", r"第一[，、]", r"第二[，、]", r"第三[，、]",
]
_FILLER_RE = re.compile("|".join(_FILLER))


def filler_ratio(text: str) -> float:
    """Share of the text's Chinese characters sitting inside template phrases."""
    total = cn_chars(text)
    if not total:
        return 0.0
    hit = sum(cn_chars(m.group(0)) for m in _FILLER_RE.finditer(text))
    return min(hit / total, 0.5)


def cn_chars(text: str) -> int:
    return sum(1 for ch in text if "一" <= ch <= "鿿")


def check(original: str, rewritten: str, *,
          min_length_ratio: float = 0.75,
          max_length_ratio: float = 1.25,
          require_same_paragraphs: bool = True) -> list[str]:
    """Return a list of failure reasons. Empty list = the rewrite is safe.

    Length band: a de-AI pass removes filler, so shrinking is expected — but
    losing a quarter of the text means content went with it. Growing past 125%
    means the model added material, which stage 2 is explicitly forbidden to do.
    """
    problems: list[str] = []

    lost_nums = _missing(numbers(original), numbers(rewritten))
    if lost_nums:
        problems.append(f"丢失数字: {', '.join(lost_nums[:8])}")

    lost_latin = _missing(latin_tokens(original), latin_tokens(rewritten))
    if lost_latin:
        problems.append(f"丢失专名/术语: {', '.join(lost_latin[:8])}")

    o_len, r_len = cn_chars(original), cn_chars(rewritten)
    if o_len == 0:
        problems.append("原文没有汉字")
    else:
        ratio = r_len / o_len
        # Allow the shrink the input's own filler justifies, plus 30% slack
        # because deleting a phrase usually takes its punctuation and a
        # connective with it. Never drop the floor below 0.55.
        allowance = filler_ratio(original) * 1.3
        floor = max(min_length_ratio - allowance, 0.55)
        if ratio < floor:
            problems.append(
                f"篇幅缩水过多: {r_len}/{o_len} = {ratio:.2f}"
                f"（套话占比 {filler_ratio(original):.0%}，下限 {floor:.2f}）")
        elif ratio > max_length_ratio:
            problems.append(f"篇幅膨胀（疑似添加内容）: {r_len}/{o_len} = {ratio:.2f}")

    if require_same_paragraphs:
        o_p, r_p = len(paragraphs(original)), len(paragraphs(rewritten))
        if o_p != r_p:
            problems.append(f"段落数变了: {o_p} -> {r_p}")

    if re.search(r"^\s*(以下是|这是|好的|改写后|修改后)", rewritten):
        problems.append("输出带了前言（模型在解释而不是只给正文）")

    return problems


def _missing(before: list[str], after: list[str]) -> list[str]:
    """Tokens present in `before` more often than in `after`."""
    from collections import Counter
    b, a = Counter(before), Counter(after)
    out = []
    for tok, n in b.items():
        if a.get(tok, 0) < n:
            out.append(tok)
    return sorted(out)


def report(original: str, rewritten: str, **kw) -> str:
    problems = check(original, rewritten, **kw)
    if not problems:
        return "OK — 事实与篇幅检查通过"
    return "FAIL — " + "; ".join(problems)


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        sys.exit("usage: guards.py <original.txt> <rewritten.txt>")
    o = open(sys.argv[1], encoding="utf-8").read()
    r = open(sys.argv[2], encoding="utf-8").read()
    print(report(o, r))

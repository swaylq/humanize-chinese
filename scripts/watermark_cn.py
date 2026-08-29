#!/usr/bin/env python3
"""Watermark handling for Chinese text — the two layers, kept apart on purpose.

Since 2026-08-02 every newly launched Claude model stamps a watermark into the
text it generates, on every surface (API, Claude, Claude Code, Bedrock, Vertex,
Foundry). Anthropic has said what class it belongs to: a version of Google
DeepMind's SynthID-Text, which is a keyed bias on token sampling. Google/Gemini
ship the same class. That is one of two very different things people mean when
they say "watermark", and conflating them is why most removal tools either do
nothing or wreck the text:

  Layer A — carriers you can see with a hex dump. Zero-width characters, bidi
    controls, tag characters, exotic spaces. Deterministic to find, lossless to
    remove, and you can prove it worked by looking again. Claude does NOT
    currently use these; other pipelines and copy-paste do, so text still
    arrives carrying them.

  Layer B — the keyed sampling bias. The signal lives in which words were
    chosen, not in any byte you can point at. No local tool can remove it as a
    verifiable operation, and no local tool can certify it is gone, because the
    key is Anthropic's. What actually weakens it is rewriting, which this repo
    already does. What this module adds is a way to measure how much of it a
    given rewrite plausibly left behind.

Why a separate Chinese implementation
-------------------------------------
The English-language cleaners (watermarks-remover, ScrubAI, and the browser
one-liners copied from them) apply two operations that are correct for English
and destructive for Chinese. Measured on this machine, Python 3.9.6,
unicodedata 13.0.0:

  NFKC normalisation
    '他说：「这不对。」（真的）'  ->  '他说:「这不对。」(真的)'
    Fullwidth colon and parentheses become ASCII. Chinese punctuation is
    fullwidth by convention; this is not cleaning, it is corruption, and it is
    itself a visible tell that the text went through a machine.

  U+3000 treated as a space homoglyph
    '　　这是一段。'  ->  '  这是一段。'
    U+3000 IDEOGRAPHIC SPACE doubled is the standard Chinese paragraph indent.
    Rewriting it to two ASCII spaces breaks the indent in every renderer.

Both are off here. What is on instead is a carrier class those tools do not
look for, because it only exists in CJK: characters that are visually identical
to a common hanzi but hold a different codepoint.

  ⼀ U+2F00 KANGXI RADICAL ONE            renders as 一 U+4E00
  ⻳ U+2EF3 CJK RADICAL C-SIMPLIFIED TURTLE renders as 龟 U+9F9F
  豈 U+F900 CJK COMPATIBILITY IDEOGRAPH    renders as 豈 U+8C48

There are 214 Kangxi radicals, 115 CJK radical supplements and 1,002 CJK
compatibility ideographs. Substituting one for its lookalike is invisible on
screen, survives copy-paste, survives every English cleaner, and carries one
bit per occurrence. Whether or not anyone is using that channel today, text
that contains them has been through something, and the fix is free: map each
one to the unified ideograph it renders as.

What this module will not tell you
----------------------------------
Whether Anthropic's detector fires. Nobody outside Anthropic can answer that;
the detection API is announced but not released, and the key is not public. Any
tool claiming a Claude watermark is "removed" is claiming something it cannot
check. This one reports two things it can check — the exact carriers removed,
and the fraction of keyed scoring windows a rewrite left intact — and says the
rest is an estimate.
"""
from __future__ import annotations

import argparse
import math
import pathlib
import sys
import unicodedata
from collections import Counter

# --------------------------------------------------------------------------
# Layer A — carriers
# --------------------------------------------------------------------------

# Invisible or format-only codepoints with no role in Chinese prose. Removing
# one never changes what a reader sees.
_STRIP = frozenset({
    0x00AD,                                     # soft hyphen
    0x034F,                                     # combining grapheme joiner
    0x061C,                                     # Arabic letter mark
    0x115F, 0x1160,                             # Hangul choseong/jungseong filler
    0x17B4, 0x17B5,                             # Khmer inherent vowels
    0x180B, 0x180C, 0x180D, 0x180E, 0x180F,     # Mongolian FVS + vowel separator
    0x200B, 0x200C, 0x200D,                     # ZWSP / ZWNJ / ZWJ
    0x200E, 0x200F,                             # LRM / RLM
    0x202A, 0x202B, 0x202C, 0x202D, 0x202E,     # bidi embeddings and overrides
    0x2060,                                     # word joiner
    0x2061, 0x2062, 0x2063, 0x2064,             # invisible math operators
    0x2066, 0x2067, 0x2068, 0x2069,             # bidi isolates
    0x206A, 0x206B, 0x206C, 0x206D, 0x206E, 0x206F,
    0x3164,                                     # Hangul filler
    0xFEFF,                                     # BOM / ZWNBSP
    0xFFA0,                                     # halfwidth Hangul filler
    0xFFF9, 0xFFFA, 0xFFFB,                     # interlinear annotation
})

_BIDI = frozenset({
    0x061C, 0x200E, 0x200F,
    0x202A, 0x202B, 0x202C, 0x202D, 0x202E,
    0x2066, 0x2067, 0x2068, 0x2069,
})

# Spaces that are not Chinese typography. U+3000 is deliberately absent: two of
# them are the standard paragraph indent, and rewriting it to ASCII breaks the
# indent everywhere it is rendered.
_SPACE_HOMOGLYPHS = {
    0x00A0: " ",   # no-break space
    0x1680: " ",   # Ogham space mark
    0x2000: " ", 0x2001: " ", 0x2002: " ", 0x2003: " ", 0x2004: " ",
    0x2005: " ", 0x2006: " ", 0x2007: " ", 0x2008: " ", 0x2009: " ",
    0x200A: " ",
    0x202F: " ",   # narrow no-break space
    0x205F: " ",   # medium mathematical space
}

# Opt-in: fullwidth Latin is legitimate in Chinese typography, so this is off
# by default and offered as a flag for people who want ASCII identifiers back.
_FULLWIDTH_LATIN = {cp: chr(cp - 0xFEE0) for cp in
                    list(range(0xFF21, 0xFF3B)) + list(range(0xFF41, 0xFF5B))}

# Opt-in: Cyrillic and Greek letters that render as Latin ones.
_CONFUSABLES = {
    0x0410: "A", 0x0412: "B", 0x0415: "E", 0x041A: "K", 0x041C: "M",
    0x041D: "H", 0x041E: "O", 0x0420: "P", 0x0421: "C", 0x0422: "T",
    0x0425: "X", 0x0430: "a", 0x0435: "e", 0x043E: "o", 0x0440: "p",
    0x0441: "c", 0x0443: "y", 0x0445: "x", 0x0456: "i",
    0x0391: "A", 0x0392: "B", 0x0395: "E", 0x0396: "Z", 0x0397: "H",
    0x0399: "I", 0x039A: "K", 0x039C: "M", 0x039D: "N", 0x039F: "O",
    0x03A1: "P", 0x03A4: "T", 0x03A5: "Y", 0x03A7: "X",
}

# Variation selectors: VS1-VS16 and the supplementary VS17-VS256. After a CJK
# ideograph these are an Ideographic Variation Sequence and select a real
# glyph, so they are kept there; anywhere else they are a carrier.
_VS_BMP = range(0xFE00, 0xFE10)
_VS_SUPP = range(0xE0100, 0xE01F0)

_TAG_CHARS = range(0xE0001, 0xE0080)

# Blocks whose members render as an existing unified ideograph.
_LOOKALIKE_BLOCKS = (
    (0x2E80, 0x2EF3),      # CJK Radicals Supplement
    (0x2F00, 0x2FD5),      # Kangxi Radicals
    (0xF900, 0xFAFF),      # CJK Compatibility Ideographs
    (0x2F800, 0x2FA1D),    # CJK Compatibility Ideographs Supplement
)


def _is_cjk_ideograph(cp: int) -> bool:
    return (0x3400 <= cp <= 0x4DBF or 0x4E00 <= cp <= 0x9FFF
            or 0xF900 <= cp <= 0xFAFF or 0x20000 <= cp <= 0x323AF)


def _is_private_use(cp: int) -> bool:
    return (0xE000 <= cp <= 0xF8FF or 0xF0000 <= cp <= 0xFFFFD
            or 0x100000 <= cp <= 0x10FFFD)


def _is_noncharacter(cp: int) -> bool:
    return 0xFDD0 <= cp <= 0xFDEF or (cp & 0xFFFE) == 0xFFFE


def _is_reserved_ignorable(cp: int) -> bool:
    """Unassigned codepoints reserved as default-ignorable.

    Conformant renderers already draw nothing for these, and normalisation
    keeps them, which is exactly what a covert carrier wants. Listed as fixed
    ranges rather than a category-Cn test: unicodedata is pinned per Python
    build (13.0.0 here), and a category rule would delete real characters
    assigned after that version — the way U+180F became Mongolian FVS4 in
    Unicode 14.
    """
    if cp in (0x2065, 0xE0000):
        return True
    return (0xFFF0 <= cp <= 0xFFF8 or 0xE0080 <= cp <= 0xE00FF
            or 0xE01F0 <= cp <= 0xE0FFF)


def _lookalike_target(ch: str) -> str | None:
    """The unified ideograph this character renders as, or None.

    Per-character NFKC rather than whole-text NFKC. On one character the
    mapping is exactly the lookalike relation and nothing else; on a whole
    Chinese document NFKC also flattens fullwidth punctuation to ASCII, which
    is why this module never runs it over the text.
    """
    cp = ord(ch)
    if not any(lo <= cp <= hi for lo, hi in _LOOKALIKE_BLOCKS):
        return None
    folded = unicodedata.normalize("NFKC", ch)
    if len(folded) != 1 or folded == ch:
        return None
    return folded if _is_cjk_ideograph(ord(folded)) else None


def _is_emoji_base(cp: int) -> bool:
    return (0x1F000 <= cp <= 0x1FAFF or 0x2190 <= cp <= 0x25FF
            or 0x2600 <= cp <= 0x27BF or 0x2B00 <= cp <= 0x2BFF
            or cp in (0x203C, 0x2049, 0x2139, 0x2934, 0x2935,
                      0x00A9, 0x00AE, 0x2122, 0x3030, 0x303D, 0x3297, 0x3299)
            or cp in (0x0023, 0x002A) or 0x0030 <= cp <= 0x0039)


def _flag_tag_indices(text: str) -> set:
    """Indices inside a complete subdivision-flag sequence (🏴 + tags + U+E007F)."""
    inside = set()
    i = 0
    while i < len(text):
        if ord(text[i]) != 0x1F3F4:
            i += 1
            continue
        j = i + 1
        while j < len(text) and 0xE0020 <= ord(text[j]) <= 0xE007E:
            j += 1
        if j > i + 1 and j < len(text) and ord(text[j]) == 0xE007F:
            inside.update(range(i + 1, j + 1))
            i = j + 1
        else:
            i += 1
    return inside


# What each finding is called in the report, and how much it means.
KIND_LABELS = {
    "zero_width":    ("零宽字符", "几乎必然是载体"),
    "bidi":          ("双向控制符", "中文里没有正当用途"),
    "tag_char":      ("标签字符", "几乎必然是载体"),
    "variation":     ("变体选择符", "不在汉字后面就是载体"),
    "private_use":   ("私用区", "没有可移植含义"),
    "noncharacter":  ("非字符", "标准禁止出现在交换文本里"),
    "reserved":      ("保留不可见码位", "未分配且渲染为空"),
    "format":        ("其他格式控制符", "不可见"),
    "space":         ("空格同形字", "不是中文排版用的空格"),
    "lookalike":     ("汉字同形替身", "与常用汉字长得一样、码位不同"),
    "fullwidth":     ("全角拉丁字母", "改成半角是可选项"),
    "confusable":    ("西里尔/希腊同形字母", "改成拉丁是可选项"),
}


def _classify(cp: int) -> str:
    if cp in _TAG_CHARS:
        return "tag_char"
    if _is_noncharacter(cp):
        return "noncharacter"
    if _is_reserved_ignorable(cp):
        return "reserved"
    if _is_private_use(cp):
        return "private_use"
    if cp in _VS_BMP or cp in _VS_SUPP or 0x180B <= cp <= 0x180F:
        return "variation"
    if cp in _BIDI:
        return "bidi"
    if cp in (0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF, 0x180E):
        return "zero_width"
    return "format"


def _decide(text, i, prev_kept, flag_tags, *, fullwidth_latin, confusables,
            keep_bidi):
    """Classify one character. Returns (action, output, kind).

    action is keep / strip / replace; kind is None when nothing is wrong.
    """
    ch = text[i]
    cp = ord(ch)
    nxt = text[i + 1] if i + 1 < len(text) else None
    prv = text[i - 1] if i else None

    # Load-bearing invisibles, kept so real text is not corrupted.
    if cp in _VS_BMP or cp in _VS_SUPP:
        if prv is not None and _is_cjk_ideograph(ord(prv)):
            return "keep", ch, None          # Ideographic Variation Sequence
        if cp in (0xFE0E, 0xFE0F) and prv is not None and _is_emoji_base(ord(prv)):
            return "keep", ch, None          # emoji presentation selector
    if cp == 0x200D and prev_kept and nxt and \
            _is_emoji_base(ord(prev_kept)) and _is_emoji_base(ord(nxt)):
        return "keep", ch, None              # emoji ZWJ sequence (👨‍👩‍👧)
    if cp in _TAG_CHARS and i in flag_tags:
        return "keep", ch, None              # 🏴󠁧󠁢󠁳󠁣󠁴󠁿 and friends
    if keep_bidi and cp in _BIDI:
        return "keep", ch, None

    if cp in _STRIP or cp in _VS_BMP or cp in _VS_SUPP or cp in _TAG_CHARS \
            or _is_noncharacter(cp) or _is_reserved_ignorable(cp) \
            or _is_private_use(cp):
        return "strip", "", _classify(cp)

    if cp in _SPACE_HOMOGLYPHS:
        return "replace", _SPACE_HOMOGLYPHS[cp], "space"

    target = _lookalike_target(ch)
    if target is not None:
        return "replace", target, "lookalike"

    if fullwidth_latin and cp in _FULLWIDTH_LATIN:
        return "replace", _FULLWIDTH_LATIN[cp], "fullwidth"
    if confusables and cp in _CONFUSABLES:
        return "replace", _CONFUSABLES[cp], "confusable"

    # Anything else in category Cf is invisible by definition.
    if unicodedata.category(ch) == "Cf":
        return "strip", "", "format"

    return "keep", ch, None


def _walk(text, *, fullwidth_latin=False, confusables=False, keep_bidi=False):
    flag_tags = _flag_tag_indices(text)
    prev_kept = None
    for i in range(len(text)):
        action, out, kind = _decide(
            text, i, prev_kept, flag_tags,
            fullwidth_latin=fullwidth_latin, confusables=confusables,
            keep_bidi=keep_bidi)
        yield i, text[i], action, out, kind
        if action == "strip":
            continue                          # a stripped char is not a base
        if kind is None and ord(text[i]) in _TAG_CHARS:
            continue                          # nor is flag glue
        if kind is None and (ord(text[i]) in _VS_BMP or ord(text[i]) in _VS_SUPP
                             or ord(text[i]) == 0x200D):
            continue                          # nor is emoji glue
        prev_kept = out


def inspect_text(text, *, fullwidth_latin=False, confusables=False,
                 keep_bidi=False):
    """Report every Layer A carrier, grouped by codepoint."""
    found = {}
    for i, ch, action, _out, kind in _walk(
            text, fullwidth_latin=fullwidth_latin, confusables=confusables,
            keep_bidi=keep_bidi):
        if kind is None:
            continue
        found.setdefault((ord(ch), kind), []).append(i)

    hits = []
    for (cp, kind), offsets in sorted(found.items(),
                                      key=lambda kv: (-len(kv[1]), kv[0][0])):
        ch = chr(cp)
        hits.append({
            "codepoint": "U+%04X" % cp,
            "name": unicodedata.name(ch, "<未命名>"),
            "kind": kind,
            "count": len(offsets),
            "offsets": offsets[:8],
            "renders_as": _lookalike_target(ch) or "",
        })
    return {
        "length": len(text),
        "total": sum(h["count"] for h in hits),
        "hits": hits,
    }


def clean_text(text, *, fullwidth_latin=False, confusables=False,
               keep_bidi=False):
    """Strip Layer A carriers. Returns (cleaned_text, stats)."""
    out = []
    removed = Counter()
    replaced = Counter()
    for _i, ch, action, ch_out, kind in _walk(
            text, fullwidth_latin=fullwidth_latin, confusables=confusables,
            keep_bidi=keep_bidi):
        if action == "strip":
            removed[kind] += 1
            continue
        out.append(ch_out)
        if action == "replace":
            replaced[kind] += 1
    result = "".join(out)
    return result, {
        "input_length": len(text),
        "output_length": len(result),
        "removed": dict(removed),
        "replaced": dict(replaced),
        "removed_count": sum(removed.values()),
        "replaced_count": sum(replaced.values()),
    }


# --------------------------------------------------------------------------
# Layer B — how much keyed signal a rewrite left behind
# --------------------------------------------------------------------------

# SynthID-Text scores each token from a hash of the H tokens before it; the
# Nature 2024 paper uses H=4, so the scoring unit is a window of 5 tokens.
# Chinese tokenizers cut CJK into 1-2 character pieces, so 5 characters is the
# closest model-free stand-in. The other widths are reported alongside it
# because H is a vendor choice nobody outside Anthropic knows.
DEFAULT_WIDTHS = (2, 3, 4, 5, 8)
HEADLINE_WIDTH = 5

_SKIP = set(" \t\r\n　")


def _windows(text, width):
    """Character windows over the text, whitespace dropped first.

    Whitespace goes because rhythm edits move punctuation and line breaks
    around; counting those as broken windows would flatter the rewrite.
    """
    body = "".join(c for c in text if c not in _SKIP)
    return Counter(body[i:i + width] for i in range(len(body) - width + 1))


def ngram_survival(before, after, widths=DEFAULT_WIDTHS):
    """Fraction of the original's keyed scoring windows still present.

    A window's score depends only on the characters inside it, not on where it
    sits, so a window that survives anywhere in the output still carries its
    original keyed value. Counting them as a multiset is therefore the right
    comparison, and it is an upper bound on residual signal: it cannot miss a
    surviving window, and it may count one that tokenised differently.
    """
    rows = []
    headline_kept = headline_before = headline_after = 0
    for w in widths:
        src = _windows(before, w)
        dst = _windows(after, w)
        total = sum(src.values())
        kept = sum(min(n, dst[g]) for g, n in src.items())
        rows.append({
            "width": w,
            "total": total,
            "kept": kept,
            "after_total": sum(dst.values()),
            "survival": (kept / total) if total else 0.0,
        })
        if w == HEADLINE_WIDTH:
            headline_kept = kept
            headline_before = total
            headline_after = sum(dst.values())

    headline = next((r["survival"] for r in rows
                     if r["width"] == HEADLINE_WIDTH), None)
    return {
        "before_chars": len(before),
        "after_chars": len(after),
        "widths": rows,
        "headline": headline,
        "z_ratio": _z_ratio(headline_kept, headline_before, headline_after),
    }


def _z_ratio(kept, before_total, after_total):
    """Estimated detector z after the rewrite, as a multiple of z before it.

    For a green-list watermark the detector reports

        z = (greens - gamma*T) / sqrt(T * gamma * (1 - gamma))

    over the T scored positions it can see. A rewrite the attacker performs
    without the key leaves `kept` positions with their original bias and makes
    the rest green only by chance, so the numerator scales with `kept` while
    the denominator follows the length of whatever the detector is handed:

        z_after / z_before = kept / sqrt(T_after * T_before)

    Length matters on its own, which is why this is not simply the survival
    fraction. Cutting a marked passage in half without editing a character
    leaves survival at 0.5 but z at 0.71 of what it was, because a detector
    reading half as much text was never as confident to begin with. Padding
    works the other way: adding unmarked text dilutes the rate and drops z
    further than the surviving windows alone would suggest.
    """
    if not kept or not before_total or not after_total:
        return 0.0
    return kept / math.sqrt(after_total * before_total)


def z_note(survival, z_ratio, before_total=0, after_total=0):
    """Plain-language reading of the two numbers."""
    if survival is None or z_ratio is None:
        return "无法估计。"
    if survival >= 0.8:
        verdict = "几乎没动，检测信号基本原封不动。"
    elif survival >= 0.5:
        verdict = "动了一部分，信号还剩一大半。"
    elif survival >= 0.25:
        verdict = "动得不少，但残留仍然可观。"
    elif survival >= 0.1:
        verdict = "改写幅度够大，残留信号已经很薄。"
    else:
        verdict = "原文的计分窗口基本没剩下什么。"

    # Length moves z on its own, in opposite directions, so name which way.
    if after_total and before_total:
        shift = after_total / before_total
        if shift < 0.95:
            length = "（比存活率高一点，是因为文章变短了：检测端能读的字少了，本来也没那么有把握）"
        elif shift > 1.05:
            length = "（比存活率低一点，是因为文章变长了：新写的部分不带原来的偏置，把信号稀释了）"
        else:
            length = ""
    else:
        length = ""

    return ("原文 %.1f%% 的 5 字计分窗口在改写后仍然原样存在。%s\n"
            "按绿名单水印的检测公式，检测端的 z 值大约会落到原来的 %.2f 倍%s。\n"
            "这是估计，不是判定 —— 只有握着密钥的一方能算出真实的 z。"
            % (survival * 100, verdict, z_ratio, length))


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _read(path):
    if path == "-":
        return sys.stdin.read()
    return pathlib.Path(path).read_text(encoding="utf-8")


def _fmt_inspect(report, *, path):
    lines = []
    if not report["hits"]:
        lines.append("%s：%d 字，没有发现可见层载体。" % (path, report["length"]))
        lines.append("")
        lines.append("这只说明没有零宽字符、同形替身这类能逐个数出来的东西。")
        lines.append("Claude 用的是采样偏置水印，藏在选词里，不可能在这一层被看到；")
        lines.append("那一层要靠改写削弱，用 humanize watermark survive 量它剩多少。")
        return "\n".join(lines)

    lines.append("%s：%d 字，命中 %d 处。" % (path, report["length"], report["total"]))
    lines.append("")
    for h in report["hits"]:
        label, meaning = KIND_LABELS.get(h["kind"], (h["kind"], ""))
        tail = "，渲染成「%s」" % h["renders_as"] if h["renders_as"] else ""
        lines.append("  %s %s ×%d" % (h["codepoint"], h["name"], h["count"]))
        lines.append("    %s%s —— %s" % (label, tail, meaning))
        lines.append("    位置：%s" % ", ".join(str(o) for o in h["offsets"]))
    lines.append("")
    lines.append("清掉：humanize watermark clean %s -o 清理后.txt" % path)
    return "\n".join(lines)


def _fmt_clean(stats, *, path, dest):
    if not stats["removed_count"] and not stats["replaced_count"]:
        return "%s 没有可清理的载体，已原样输出。" % path
    lines = ["删除 %d 个，替换 %d 个。" % (stats["removed_count"], stats["replaced_count"])]
    for kind, n in sorted(stats["removed"].items(), key=lambda kv: -kv[1]):
        lines.append("  删除  %s ×%d" % (KIND_LABELS.get(kind, (kind, ""))[0], n))
    for kind, n in sorted(stats["replaced"].items(), key=lambda kv: -kv[1]):
        lines.append("  替换  %s ×%d" % (KIND_LABELS.get(kind, (kind, ""))[0], n))
    lines.append("字数 %d -> %d。" % (stats["input_length"], stats["output_length"]))
    if dest:
        lines.append("-> %s" % dest)
    return "\n".join(lines)


def _fmt_survive(result):
    lines = ["改写前 %d 字，改写后 %d 字。" %
             (result["before_chars"], result["after_chars"]), ""]
    lines.append("  窗口宽度   原文窗口数   仍然存在   存活率")
    for r in result["widths"]:
        mark = " ←" if r["width"] == HEADLINE_WIDTH else ""
        lines.append("  %6d %12d %10d %8.1f%%%s" %
                     (r["width"], r["total"], r["kept"], r["survival"] * 100, mark))
    lines.append("")
    head = next((r for r in result["widths"]
                 if r["width"] == HEADLINE_WIDTH), None)
    lines.append(z_note(result["headline"], result["z_ratio"],
                        head["total"] if head else 0,
                        head["after_total"] if head else 0))
    return "\n".join(lines)


def main(argv=None):
    argv = list(argv if argv is not None else sys.argv[1:])
    ap = argparse.ArgumentParser(
        prog="humanize watermark",
        description="水印处理：可见层载体清理 + 采样水印残留量估计",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
两层是两回事：

  inspect / clean  处理看得见的载体 —— 零宽字符、双向控制符、标签字符、
                   以及只有中文才有的汉字同形替身（⼀ U+2F00 长得和 一 U+4E00
                   一样）。删掉是确定的操作，删完再看一眼就能验证。
                   Claude 目前不用这一层，但复制粘贴和别的流水线会带进来。

  survive          处理看不见的那层。Claude 从 2026-08-02 起用的是
                   SynthID-Text 那一类的采样偏置水印，信号在选词里，
                   本地任何工具都删不掉也证明不了删掉了 —— 密钥在 Anthropic 手上。
                   能做的是改写，然后量一量原文的计分窗口还剩多少。

例子：
  humanize watermark inspect draft.txt
  humanize watermark clean draft.txt -o clean.txt
  humanize rewrite draft.txt --llm -o out.txt
  humanize watermark survive draft.txt out.txt
""")
    sub = ap.add_subparsers(dest="cmd")

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--fullwidth-latin", action="store_true",
                        help="全角拉丁字母改半角（默认不动，中文排版里它是正当的）")
    common.add_argument("--confusables", action="store_true",
                        help="西里尔/希腊同形字母改拉丁")
    common.add_argument("--keep-bidi", action="store_true",
                        help="保留双向控制符（文里真的夹了阿拉伯语时用）")

    p = sub.add_parser("inspect", parents=[common], help="只报告，不改文件")
    p.add_argument("file", help="输入文件；- 表示标准输入")
    p.add_argument("--json", action="store_true", help="输出 JSON")

    p = sub.add_parser("clean", parents=[common], help="清掉可见层载体")
    p.add_argument("file", help="输入文件；- 表示标准输入")
    p.add_argument("-o", "--output")
    p.add_argument("-q", "--quiet", action="store_true")

    p = sub.add_parser("survive", help="量改写留下了多少采样水印残留")
    p.add_argument("before", help="改写前")
    p.add_argument("after", help="改写后")
    p.add_argument("--json", action="store_true", help="输出 JSON")

    args = ap.parse_args(argv)
    if not args.cmd:
        ap.print_help()
        return 0

    if args.cmd == "inspect":
        text = _read(args.file)
        report = inspect_text(text,
                              fullwidth_latin=args.fullwidth_latin,
                              confusables=args.confusables,
                              keep_bidi=args.keep_bidi)
        if args.json:
            import json
            sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        else:
            sys.stdout.write(_fmt_inspect(report, path=args.file) + "\n")
        return 0

    if args.cmd == "clean":
        text = _read(args.file)
        out, stats = clean_text(text,
                                fullwidth_latin=args.fullwidth_latin,
                                confusables=args.confusables,
                                keep_bidi=args.keep_bidi)
        if args.output:
            pathlib.Path(args.output).write_text(out, encoding="utf-8")
        else:
            sys.stdout.write(out)
        if not args.quiet:
            sys.stderr.write(_fmt_clean(stats, path=args.file,
                                        dest=args.output) + "\n")
        return 0

    if args.cmd == "survive":
        result = ngram_survival(_read(args.before), _read(args.after))
        if args.json:
            import json
            sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        else:
            sys.stdout.write(_fmt_survive(result) + "\n")
        return 0

    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())

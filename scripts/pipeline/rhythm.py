#!/usr/bin/env python3
"""Stage 3: sentence rhythm, by moving punctuation and nothing else.

The whole module obeys one invariant, checked by `verify_invariant()` and by
the unit tests:

    strip every punctuation mark from the input and from the output,
    and the two character sequences must be IDENTICAL.

That makes "不换词、不插句、不调序" a provable property rather than a promise.
v5 broke Chinese because it substituted synonyms, inserted filler sentences and
reordered clauses to chase a detector score; none of those operations can pass
this invariant, so none of them can exist in this file.

Why rhythm is the right — and only — job for the Python stage: measured on
60 real CSL paper abstracts against 60 model abstracts (2026-08-24), the two
categories that actually separate human from machine are sentence-length
variation (fires on <5% of human text, 98.3% of AI text) and short-sentence
fraction (same split). Both are functions of where the sentence boundaries
fall. Every other category either fails to discriminate (comma density fires on
90% of real papers) or cannot be fixed without touching words.

Targets come from the project's own HC3 calibration, in scripts/ngram_model.py:
  sentence-length CV      >= 0.40   (human mean 0.52, AI mean 0.32)
  short-sentence fraction >= 8%     (human mean 24.9%, AI mean 2.6%)
"""
from __future__ import annotations

import re
import statistics

# --------------------------------------------------------------------------
# text geometry
# --------------------------------------------------------------------------

SENT_END = "。！？…"
_PUNCT = "。，、；：！？…—－·「」『』（）()《》〈〉“”‘’\"'\n\r\t "
_PUNCT_RE = re.compile(f"[{re.escape(_PUNCT)}]")

SHORT_SENTENCE_MAX = 10      # < 10 Chinese chars counts as a short sentence
CV_TARGET = 0.40
SHORT_FRACTION_TARGET = 0.08

# Connectives that can legitimately open a Chinese sentence. Promoting the
# comma before one of these to a full stop is safe.
SENTENCE_INITIAL = [
    "但是", "但", "不过", "然而", "可是", "只是",
    "所以", "因此", "于是", "结果", "这样",
    "另外", "此外", "同时", "而且", "并且",
    "后来", "接着", "随后", "然后", "最终", "最后",
    "反过来", "相反", "换个说法",
]

# The first half of a paired connective: the clause is not yet a sentence, so
# the comma after it must never become a full stop.
SUBORDINATOR_HEAD = [
    "虽然", "尽管", "固然", "因为", "由于", "既然",
    "如果", "假如", "倘若", "要是", "即使", "即便", "哪怕",
    "无论", "不管", "不论", "只有", "只要", "除非", "一旦",
    "为了", "以便", "以免", "与其", "宁可", "不但", "不仅",
]

# Prepositions and coverbs that open an ADVERBIAL, not a sentence. A clause
# beginning with one of these is grammatically dependent on the main clause
# that follows, so the comma after it can never become a full stop.
# Found the hard way on 2026-08-24: the first version of this file happily
# produced 「通过优化业务流程。我们提升了工作效率」— a fragment. The paired-
# connective list did not cover it because 通过 has no second half to pair with.
DEPENDENT_HEAD = [
    "通过", "经过", "根据", "按照", "依据", "依照", "本着", "鉴于",
    "借助", "凭借", "利用", "运用", "采用", "结合", "基于", "面向",
    "围绕", "针对", "关于", "对于", "至于", "就", "随着", "伴随",
    "为了", "出于", "考虑到", "受限于", "得益于", "在",
]

# Pronoun / demonstrative openings that mark a clause with its own subject.
SUBJECT_HEAD = [
    "我们", "他们", "她们", "它们", "咱们", "大家",
    "我", "你", "您", "他", "她", "它",
    "这些", "那些", "这种", "那种", "这类", "该", "本文", "本研究",
    "这", "那", "其",
]

_PAIRED_OPEN = "「『（(《〈“‘\""
_PAIRED_CLOSE = "」』）)》〉”’\""


def strip_punct(text: str) -> str:
    return _PUNCT_RE.sub("", text)


def verify_invariant(before: str, after: str) -> bool:
    """True when the two texts differ only in punctuation and whitespace."""
    return strip_punct(before) == strip_punct(after)


def paragraphs(text: str) -> list[str]:
    return re.split(r"(\n\s*\n)", text)


def split_sentences(para: str) -> list[str]:
    """Split into sentences, keeping terminal punctuation attached."""
    out, buf = [], ""
    for ch in para:
        buf += ch
        if ch in SENT_END:
            out.append(buf)
            buf = ""
    if buf.strip():
        out.append(buf)
    return out


def cn_len(s: str) -> int:
    return sum(1 for ch in s if "一" <= ch <= "鿿")


def metrics(text: str) -> dict:
    sents = [s for p in re.split(r"\n\s*\n", text) for s in split_sentences(p)]
    lens = [cn_len(s) for s in sents if cn_len(s) > 0]
    if len(lens) < 2:
        return {"n": len(lens), "cv": 0.0, "short_fraction": 0.0, "mean": 0.0}
    mean = statistics.mean(lens)
    cv = statistics.pstdev(lens) / mean if mean else 0.0
    short = sum(1 for n in lens if n < SHORT_SENTENCE_MAX) / len(lens)
    return {"n": len(lens), "cv": cv, "short_fraction": short, "mean": mean}


# --------------------------------------------------------------------------
# candidate finding
# --------------------------------------------------------------------------

def _depth_map(s: str) -> list[int]:
    """Bracket/quote nesting depth at each index; splits only happen at 0."""
    depth, out, straight = 0, [], False
    for ch in s:
        if ch in _PAIRED_OPEN and ch != '"':
            depth += 1
        elif ch == '"':
            straight = not straight
            depth += 1 if straight else -1
        elif ch in _PAIRED_CLOSE and ch != '"':
            depth = max(0, depth - 1)
        out.append(max(depth, 0))
    return out


def _starts_with(s: str, heads: list[str]) -> str | None:
    for h in heads:
        if s.startswith(h):
            return h
    return None


def find_split_candidates(sentence: str) -> list[int]:
    """Indices of commas inside `sentence` that may safely become full stops.

    A comma qualifies when the clause before it can stand as a sentence and the
    clause after it opens either with a sentence-initial connective or with its
    own subject. Anything ambiguous is left alone — a missed split costs
    nothing, a wrong split produces a fragment.
    """
    depths = _depth_map(sentence)
    out = []
    for i, ch in enumerate(sentence):
        if ch not in "，；":
            continue
        if depths[i] != 0:
            continue
        # a halfwidth comma inside digits is a thousands separator, not a clause
        if i and sentence[i - 1].isdigit() and i + 1 < len(sentence) \
                and sentence[i + 1].isdigit():
            continue

        before = sentence[:i]
        after = sentence[i + 1:].lstrip()
        after_core = after.rstrip(SENT_END + "，；")

        if cn_len(before) < 8 or cn_len(after_core) < 6:
            continue
        # the clause before must not be the open half of a paired connective
        last_clause = re.split(r"[，；]", before)[-1].lstrip()
        if _starts_with(last_clause, SUBORDINATOR_HEAD):
            continue
        if _starts_with(last_clause, DEPENDENT_HEAD):
            continue
        if _starts_with(before.lstrip(), SUBORDINATOR_HEAD) and "，" not in before:
            continue
        # the clause after must be able to open a sentence
        if ch == "；":
            out.append(i)
            continue
        if _starts_with(after, SENTENCE_INITIAL) or _starts_with(after, SUBJECT_HEAD):
            out.append(i)
    return out


def find_merge_candidates(sentences: list[str]) -> list[int]:
    """Indices i where sentence i and i+1 may be joined with a comma.

    Merging is how variance is created in a paragraph made of uniformly short
    sentences: joining two of them leaves the rest short and the joined one
    long, which raises the spread. Guarded so the result stays readable.
    """
    out = []
    for i in range(len(sentences) - 1):
        a, b = sentences[i], sentences[i + 1]
        if not a.rstrip().endswith("。"):
            continue
        if cn_len(a) + cn_len(b) > 45:
            continue
        if cn_len(a) < 4 or cn_len(b) < 4:
            continue
        # do not weld a clause onto a sentence that already has 3+ clauses
        if a.count("，") + b.count("，") >= 3:
            continue
        out.append(i)
    return out


# --------------------------------------------------------------------------
# operations
# --------------------------------------------------------------------------

def apply_split(sentence: str, index: int) -> str:
    return sentence[:index] + "。" + sentence[index + 1:].lstrip()


def apply_merge(a: str, b: str) -> str:
    return a.rstrip().rstrip("。") + "，" + b.lstrip()


def _rebuild(sentences: list[str]) -> str:
    return "".join(sentences)


def _score(text: str) -> float:
    """How far the text is from both targets; lower is better."""
    m = metrics(text)
    return (max(0.0, CV_TARGET - m["cv"]) / CV_TARGET
            + max(0.0, SHORT_FRACTION_TARGET - m["short_fraction"])
            / SHORT_FRACTION_TARGET)


def polish_paragraph(para: str, *, enable_split: bool = True,
                     enable_merge: bool = True,
                     max_edits: int = 6) -> tuple[str, list[str]]:
    """Greedily apply the edit that most improves rhythm, until targets are met."""
    edits: list[str] = []
    current = para

    for _ in range(max_edits):
        if _score(current) <= 0:
            break
        sents = split_sentences(current)
        best = None  # (score, description, new_text)

        if enable_split:
            for si, s in enumerate(sents):
                for ci in find_split_candidates(s):
                    trial = list(sents)
                    trial[si] = apply_split(s, ci)
                    cand = _rebuild(trial)
                    sc = _score(cand)
                    if best is None or sc < best[0]:
                        best = (sc, f"断句: …{s[max(0,ci-6):ci]}｜{s[ci+1:ci+7]}…",
                                cand)

        if enable_merge:
            for mi in find_merge_candidates(sents):
                trial = list(sents)
                merged = apply_merge(trial[mi], trial[mi + 1])
                trial[mi:mi + 2] = [merged]
                cand = _rebuild(trial)
                sc = _score(cand)
                if best is None or sc < best[0]:
                    best = (sc, f"合句: {sents[mi][:8]}…+{sents[mi+1][:8]}…", cand)

        if best is None or best[0] >= _score(current):
            break
        current = best[2]
        edits.append(best[1])

    return current, edits


def polish(text: str, *, enable_split: bool = True, enable_merge: bool = True,
           max_edits_per_para: int = 6) -> tuple[str, list[str]]:
    """Stage 3 entry point. Returns (text, edit descriptions)."""
    parts = paragraphs(text)
    out, all_edits = [], []
    for part in parts:
        if not part.strip() or part.strip("\n \t") == "":
            out.append(part)
            continue
        polished, edits = polish_paragraph(
            part, enable_split=enable_split, enable_merge=enable_merge,
            max_edits=max_edits_per_para)
        out.append(polished)
        all_edits.extend(edits)
    result = "".join(out)

    # Hard stop: if the invariant broke, something in this file is wrong and
    # the safe answer is to change nothing at all.
    if not verify_invariant(text, result):
        return text, ["INVARIANT VIOLATED — 已放弃全部改动"]
    return result, all_edits

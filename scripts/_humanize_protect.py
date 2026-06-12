"""
Protection layer for Humanize-Chinese.
Replaces marked-up spans (LaTeX commands, math blocks, braces etc.)
with opaque placeholders before humanize processing, then restores them.

Design: placeholder-based, zero injection points in replacement functions.
Two wrapper calls: protect() before humanize, restore() after humanize.

Supports:
  - --protect-latex:  LaTeX command/block/math protection
  - --protect-file FILE: user-supplied term list (one per line)
  - extendable: code-level ProtectLayer.add_pattern(rx) for custom regex
"""

import re
import os

# ── Sentinel choice ──
# We use a long ASCII-invisible placeholder pattern that survives all
# humanize pipeline operations (splitting, merging, re.sub, replace).
# \x00 collides with the cascade-protection sentinel in humanize_cn.py
# which strips null bytes at the end of reduce_high_freq_bigrams.
# \ue000–\ue0ff are Unicode Private Use Area chars that survive Chinese text ops.
_SENTINEL = '\ue000'
_PROTECT_PREFIX = _SENTINEL + 'PT'

# ── LaTeX protection patterns ──
# Ordered outermost-first (environments before commands before braces).

_LATEX_PATTERNS = [
    # ── display math ──
    (r'\$\$[^$]*?\$\$',                     'latex-displaymath'),
    (r'\\\[.*?\\\]',                         'latex-displaymath'),
    # ── environments \begin{...} ... \end{...} ──
    (r'\\begin\{[^}]*\}.*?\\end\{[^}]*\}',  'latex-environment'),
    # ── scope braces: {\cmd{arg} text}, {\small text} ──
    # MUST run before command-args so the whole {\color{red} 值得注意的是}
    # is captured as one unit, not split into \color{red} + bare braces.
    # Short Chinese content (<=15 chars, e.g. titles like {\textbf 第一章})
    # is NOT protected — the brace text can be rewritten, only the command
    # itself survives. Long content (paragraph-level) IS protected.
    (r'\{\\[a-zA-Z@]+(?:\*)?(?:\[[^\]]*\])*(?:\{[^}]*\})?[^}]*\}',
                                              'latex-scope-brace'),
    # ── commands with arguments ──
    (r'\\[a-zA-Z@]+(?:\*)?(?:\[[^\]]*\])*(?:\{[^}]*\})+',
                                              'latex-command-args'),
    # ── bare commands (no args, e.g. \clearpage, \\, \&) ──
    (r'\\[a-zA-Z@]+(?:\*)?(?![a-zA-Z@])',   'latex-command-bare'),
    # ── inline math ──
    (r'\\\(.*?\\\)',                         'latex-inline-math'),
    (r'\$[^$]+?\$',                          'latex-inline-math'),
    # ── LaTeX braces {content} ──
    # Captures remaining paired braces that contain LaTeX markers.
    # Matches innermost {non-brace-content} pairs that contain \ or $ inside.
    (r'\{([^{}]*\\(?:[a-zA-Z@]+\*?|\(|\)|\[|\])[^{}]*)\}',
                                              'latex-brace'),
    # ── special chars often in LaTeX tabular ──
    (r'(?<!\\)&',                            'latex-tab-amp'),
    (r'(?<!\\)~',                            'latex-tie'),
]


def _make_placeholder(idx, label=''):
    return f'{_PROTECT_PREFIX}{idx}:{label}{_SENTINEL}'


def protect_latex(text):
    """Replace all LaTeX markup in *text* with sentinel placeholders.

    Returns (protected_text, mapping) where *mapping* is
    {placeholder_str: original_str}.

    Scope-brace gating: {\cmd 短标题} with <=15 Chinese chars inside
    is NOT protected as a whole — the command still gets protected
    by later patterns, but the brace text remains rewriteable.
    Long scope-brace content (paragraph-level) IS fully protected.
    """
    mapping = {}
    idx = 0

    for pattern, label in _LATEX_PATTERNS:
        compiled = re.compile(pattern, re.DOTALL)
        while True:
            m = compiled.search(text)
            if not m:
                break
            original = m.group(0)

            # Scope-brace gating: skip short Chinese content
            if label == 'latex-scope-brace':
                cn_count = sum(1 for c in original if '\u4e00' <= c <= '\u9fff')
                if cn_count <= 6:
                    text = text[:m.start()] + '\ue001' + text[m.start()+1:]
                    continue

            placeholder = _make_placeholder(idx, label)
            mapping[placeholder] = original
            text = text[:m.start()] + placeholder + text[m.end():]
            idx += 1

    # Clean up scope-brace skip markers
    text = text.replace('\ue001', '{')
    return text, mapping


def protect_custom(text, term_list):
    """Replace user-supplied literal terms with sentinel placeholders.

    *term_list* is an iterable of strings. Longer terms matched first.
    """
    mapping = {}
    idx = 0
    sorted_terms = sorted(term_list, key=len, reverse=True)

    for term in sorted_terms:
        if not term:
            continue
        start = 0
        while True:
            pos = text.find(term, start)
            if pos < 0:
                break
            placeholder = _make_placeholder(idx, 'custom')
            mapping[placeholder] = term
            text = text[:pos] + placeholder + text[pos + len(term):]
            idx += 1
            start = pos + len(placeholder)

    return text, mapping


def restore(text, mapping):
    """Replace all sentinel placeholders in *text* with their originals.

    Handles nested replacements: outer placeholders may contain inner
    placeholder text as literal content. Repeated passes ensure all
    levels are resolved.
    """
    if not mapping:
        return text
    # Reverse insertion order: outermost first. This is important when
    # protect_latex matches both $...$ (outer) and \command (inner).
    # Restoring outer → produces inner placeholder text → next pass finds it.
    items = list(mapping.items())
    for _ in range(10):  # safety cap: max nesting depth
        changed = False
        for placeholder, original in items:
            if placeholder in text:
                text = text.replace(placeholder, original)
                changed = True
        if not changed:
            break
    return text


class ProtectLayer:
    """Unified protection layer. Use as context manager or explicit calls."""

    def __init__(self):
        self._mapping = {}
        self._original_text = None

    def wrap(self, text, latex=False, custom_terms=None):
        """Protect *text* and return the wrapped version.

        Args:
            text: input string
            latex: if True, apply LaTeX protection patterns
            custom_terms: optional iterable of literal strings to protect
        """
        self._original_text = text
        total_mapping = {}

        if latex:
            text, mapping = protect_latex(text)
            total_mapping.update(mapping)

        if custom_terms:
            text, mapping = protect_custom(text, custom_terms)
            total_mapping.update(mapping)

        self._mapping = total_mapping
        return text

    def unwrap(self, text):
        """Restore protected spans in *text* from the mapping set by wrap()."""
        if not self._mapping:
            return text
        return restore(text, self._mapping)

    @property
    def mapping(self):
        return dict(self._mapping)


# Convenience: single-call protect+restore for leaf functions
_default_layer = None


def get_layer():
    global _default_layer
    if _default_layer is None:
        _default_layer = ProtectLayer()
    return _default_layer

#!/usr/bin/env python3
"""
Protection Layer for Humanize-Chinese.

Two operating modes:

  1. Built-in mini mode (default):
     Loads scripts/data/mini_dict.json — a sorted flat list of ~68K terms
     from 9 key technical domains. Bisect binary search, no domain scoring.
     ALL matched terms are protected.

  2. Full cache mode (requires external DomainWordsDict JSON cache):
     Loads scripts/data/DomainWordsDict/*.json — per-domain sorted files
     with weighted terms. Supports domain detection + weighted scoring.
     Generate with: python humanize_cn.py --build-dict-cache <source_dir>

Data source: https://github.com/liuhuanyong/DomainWordsDict
"""

import os
import re
import json
import bisect
from collections import defaultdict

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

_MINI_DICT_PATH = os.path.join(_SCRIPT_DIR, 'data', 'mini_dict.json')
_FULL_CACHE_DIR = os.path.join(_SCRIPT_DIR, 'data', 'DomainWordsDict')

_NOISE_DOMAINS = {
    '人物名称', '地点名称', '诗词歌赋', '民间习俗', '世界宗教',
    '新番动漫', '网络游戏', '网络文学', '网络用语', '休闲活动',
    '音乐歌曲', '电影影视', '敏感用词', '组织机构',
    '市场购物', '手机数码', '美容美发', '家居装饰', '餐饮食品',
    '纺织服装', '广告传媒', '办公文教', '人力招聘',
    '航空航天', '安全工程', '期货期权',
}

MIN_WEIGHT_FOR_INDEX = 3
MIN_WEIGHT_FOR_PROTECT = 5
MIN_TERM_LEN = 2
MAX_TERM_LEN = 10
MIN_DOMAIN_SCORE_RATIO = 0.0035
_ASCII_RE = re.compile(r'^[a-zA-Z0-9\s\.\,\-\'\"\(\)\&\/\#]+$')


def _is_noise_term(term):
    if len(term) < MIN_TERM_LEN:
        return True
    if len(term) > MAX_TERM_LEN:
        return True
    if _ASCII_RE.match(term):
        return True
    return False


class ProtectLayer:
    """Protection layer: domain detection + term protection.

    Two modes:
      - Mini (built-in): flat term matching via bisect, no domain scoring.
        Reads scripts/data/mini_dict.json at load time.
      - Full (external cache): domain-aware scoring with weighted terms.
        Reads scripts/data/DomainWordsDict/*.json .
    """

    def __init__(self):
        self._sorted_terms = []   # [(term, domain, weight)] for full mode
        self._mini_terms = []     # flat sorted list for mini mode
        self.domain_terms = defaultdict(list)
        self._full_loaded = False
        self._mini_loaded = False
        self._protected_domains = None
        self._last_scan_result = None
        self._last_scan_text = None

    def _load_mini(self):
        """Load flat sorted list from data/mini_dict.json."""
        if not os.path.isfile(_MINI_DICT_PATH):
            return False
        try:
            with open(_MINI_DICT_PATH, 'r', encoding='utf-8') as f:
                self._mini_terms = json.load(f)
            self._mini_loaded = True
            return True
        except Exception:
            return False

    def _load_full_cache(self):
        """Load from data/DomainWordsDict/*.json (full mode)."""
        if not os.path.isdir(_FULL_CACHE_DIR):
            return False

        raw = defaultdict(dict)
        for fname in os.listdir(_FULL_CACHE_DIR):
            if not fname.endswith('.json'):
                continue
            fpath = os.path.join(_FULL_CACHE_DIR, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception:
                continue
            domain_cn = data.get('domain_cn', '')
            if domain_cn in _NOISE_DOMAINS:
                continue
            if not data.get('sorted'):
                continue
            for term, weight in data.get('terms', []):
                raw[term][domain_cn] = max(raw[term].get(domain_cn, 0), weight)

        if not raw:
            return False

        for term, domain_dict in raw.items():
            for domain, weight in domain_dict.items():
                self._sorted_terms.append((term, domain, weight))
                self.domain_terms[domain].append((term, weight))

        self._sorted_terms.sort(key=lambda x: x[0])
        for domain in self.domain_terms:
            self.domain_terms[domain].sort(key=lambda x: x[1], reverse=True)
        return True

    def load(self):
        """Try full cache first, fall back to built-in mini."""
        if self._full_loaded:
            return

        if self._load_full_cache():
            self._full_loaded = True
            return

        self._load_mini()

    def is_ready(self):
        """Returns True if at least mini dict is available."""
        if self._full_loaded:
            return True
        if self._mini_loaded:
            return True
        return False

    def _scan_text(self, text):
        """Single-pass text scan with bisect binary search.

        In full mode: matches against sorted (term, domain, weight) tuples.
        In mini mode: matches against flat sorted _mini_terms list.

        Returns:
            list of (term, domain, weight, start_pos) tuples.
            In mini mode, domain="" and weight=0 (placeholder).
        """
        matched = []
        n = len(text)

        if self._full_loaded:
            st = self._sorted_terms
            for start in range(n):
                for length in range(MIN_TERM_LEN, MAX_TERM_LEN + 1):
                    end = start + length
                    if end > n:
                        break
                    chunk = text[start:end]
                    pos = bisect.bisect_left(st, (chunk, '', -1))
                    if pos < len(st) and st[pos][0] == chunk:
                        while pos < len(st) and st[pos][0] == chunk:
                            term, domain, weight = st[pos]
                            matched.append((term, domain, weight, start))
                            pos += 1
        else:
            mt = self._mini_terms
            for start in range(n):
                for length in range(MIN_TERM_LEN, MAX_TERM_LEN + 1):
                    end = start + length
                    if end > n:
                        break
                    chunk = text[start:end]
                    pos = bisect.bisect_left(mt, chunk)
                    if pos < len(mt) and mt[pos] == chunk:
                        matched.append((chunk, '', 0, start))

        return matched

    def detect_domains(self, text, top_n=3):
        """Detect text domains. Full mode only (returns [] in mini mode)."""
        if not self._full_loaded:
            if not self._load_full_cache():
                return []

        scan_result = self._scan_text(text)
        self._last_scan_result = scan_result
        self._last_scan_text = text

        domain_scores = defaultdict(float)
        text_len = len(text)
        for term, domain, weight, start in scan_result:
            if not domain:
                continue
            domain_scores[domain] += 1.0 / weight

        if not domain_scores:
            return []

        norm = max(text_len, 1)
        ranked = sorted(domain_scores.items(), key=lambda x: x[1], reverse=True)
        ranked = [(d, round(s / norm, 6)) for d, s in ranked]
        ranked = [(d, s) for d, s in ranked if s >= MIN_DOMAIN_SCORE_RATIO]
        return ranked[:top_n]

    def extract_protected_terms(self, text, domains_or_top_n=3,
                                 min_weight=None):
        """Extract terms to protect.

        Full mode: uses domain detection + weight filtering.
        Mini mode: returns ALL mini-dict terms found in text (no weight filter).
        """
        if min_weight is None:
            min_weight = MIN_WEIGHT_FOR_PROTECT

        if self._full_loaded:
            if isinstance(domains_or_top_n, int):
                detected = self.detect_domains(text, top_n=domains_or_top_n)
                domains = [d for d, _ in detected]
            else:
                if self._last_scan_result is None or self._last_scan_text != text:
                    self._last_scan_result = self._scan_text(text)
                    self._last_scan_text = text
                domains = domains_or_top_n

            self._protected_domains = domains
            domain_set = set(domains)
            seen_terms = set()
            protected = set()
            for term, domain, weight, start in self._last_scan_result:
                if domain in domain_set and weight >= min_weight:
                    if term not in seen_terms:
                        seen_terms.add(term)
                        protected.add(term)
            return protected

        # Mini mode: return ALL matched terms (no weight/domain filtering)
        self._last_scan_result = self._scan_text(text)
        self._last_scan_text = text
        protected = set()
        for term, domain, weight, start in self._last_scan_result:
            protected.add(term)
        return protected


_default_layer = None


def get_layer():
    global _default_layer
    if _default_layer is None:
        _default_layer = ProtectLayer()
        _default_layer.load()
    return _default_layer


# Preload on import for faster first call
get_layer()

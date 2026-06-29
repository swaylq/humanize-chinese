#!/usr/bin/env python3
"""semantic_integrity_check.py — 语义完整度检查独立脚本

零依赖（jieba 可选）。基于以下研究设计多维评估:

  - MeaningBERT (Beauchemin & Saggion, Frontiers in AI 2023)
      评估改写/简化的语义保持，指出 BLEU/SARI 与人类判断相关性差。
  - Towards Human-Preferences Chinese Rewriting Evaluation (ICLR 2026)
      提出 4 维框架: semantic consistency + syntactic structure
      + lexical variation + stylistic fidelity，Spearman ρ=0.61。
  - BERTScore (Zhang et al. 2020)
      用上下文嵌入做 token 级余弦匹配。本脚本用字符 n-gram Jaccard
      做零依赖近似（精度低但可捕捉语义翻转）。
  - REPRO (Yu & Xiong, arXiv 2510.10681 2025)
      用 BERTScore ≥ τ 做语义保持硬过滤。本脚本用多维加权替代。

10 个维度:
  1. length_ratio        长度比
  2. char_overlap        字符保留率
  3. word_overlap        词保留率
  4. keyword_retention   关键词保留率 (TF 简化版 Top-K)
  5. bigram_jaccard      字符 2-gram Jaccard (BERTScore 近似)
  6. trigram_jaccard     字符 3-gram Jaccard
  7. paragraph_ratio     段落数比
  8. sentence_ratio      句子数比
  9. synonym_coverage    词林同义覆盖 (可选, 需 cilin_synonyms.json)
  10. protected_term_retention  术语保留 (可选, 需 protected_terms.json)

外加标点异常检测（针对本项目已知问题）:
  - 省略号滥用（>1 次）
  - 碎片断词（，/、后跟。）
  - 双标点
  - 空句

用法:
  python dev/semantic_integrity_check.py --orig orig.txt --rewrite rewritten.txt
  python dev/semantic_integrity_check.py --orig orig.txt --rewrite rewritten.txt --json
  python dev/semantic_integrity_check.py -o a.txt -r b.txt  # 短参数

退出码:
  0 = ok / suspicious
  1 = failed (语义严重破坏)
  2 = 参数错误
"""

import argparse
import json
import os
import re
import sys
from collections import Counter

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
WEIGHTS_DIR = os.path.join(PROJECT_DIR, 'scripts', 'weights')

# ── jieba 可选分词 ──
try:
    import jieba
    _HAS_JIEBA = True
except ImportError:
    _HAS_JIEBA = False


def _cn_chars(s):
    """提取中文字符列表。"""
    return [c for c in s if '\u4e00' <= c <= '\u9fff']


def _tokenize(text):
    """分词：优先 jieba，否则字符 2-gram fallback。"""
    if _HAS_JIEBA:
        return [w for w in jieba.lcut(text) if len(w) >= 2 or w.isalpha()]
    cn = ''.join(_cn_chars(text))
    return [cn[i:i+2] for i in range(max(len(cn) - 1, 0))]


# ── 词典懒加载 ──
_CILIN_CACHE = None


def _load_cilin():
    """加载 cilin_synonyms.json: {word: [synonyms]} 扁平字典。"""
    global _CILIN_CACHE
    if _CILIN_CACHE is not None:
        return _CILIN_CACHE
    candidates = [
        os.path.join(WEIGHTS_DIR, 'cilin_synonyms.json'),
        os.path.join(PROJECT_DIR, 'scripts', 'cilin_synonyms.json'),
    ]
    for p in candidates:
        if os.path.isfile(p):
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    _CILIN_CACHE = json.load(f)
                return _CILIN_CACHE
            except Exception:
                continue
    _CILIN_CACHE = {}
    return _CILIN_CACHE


# ── 维度 1: 长度比 ──
def metric_length_ratio(orig, rewrite):
    o = len(_cn_chars(orig))
    r = len(_cn_chars(rewrite))
    return r / o if o else 1.0


# ── 维度 2: 字符保留率 ──
def metric_char_overlap(orig, rewrite):
    oc = set(_cn_chars(orig))
    rc = set(_cn_chars(rewrite))
    return len(oc & rc) / len(oc) if oc else 1.0


# ── 维度 3: 词保留率 ──
def metric_word_overlap(orig, rewrite):
    ow = set(_tokenize(orig))
    rw = set(_tokenize(rewrite))
    return len(ow & rw) / len(ow) if ow else 1.0


# ── 维度 4: 关键词保留率 (TF 简化版 Top-K) ──
_STOP_WORDS = {
    '的', '了', '是', '在', '和', '与', '及', '或', '也', '都',
    '这', '那', '一', '不', '没', '为', '对', '由', '从', '把', '被',
    '可以', '能够', '应该', '需要', '进行', '通过', '以及', '并且',
    '然而', '因此', '所以', '由于', '基于', '随着',
}


def metric_keyword_retention(orig, rewrite, top_k=10):
    """取原文词频 Top-K（去停用词），看改写保留多少。"""
    ow = _tokenize(orig)
    rw = set(_tokenize(rewrite))
    counter = Counter(ow)
    keywords = [w for w, _ in counter.most_common(top_k * 3)
                if w not in _STOP_WORDS and len(w) >= 2][:top_k]
    if not keywords:
        return 1.0
    retained = sum(1 for w in keywords if w in rw)
    return retained / len(keywords)


# ── 维度 5/6: 字符 n-gram Jaccard (BERTScore 零依赖近似) ──
def _char_ngrams(s, n=2):
    cn = ''.join(_cn_chars(s))
    if len(cn) < n:
        return set()
    return set(cn[i:i + n] for i in range(len(cn) - n + 1))


def metric_ngram_jaccard(orig, rewrite, n=2):
    g1 = _char_ngrams(orig, n)
    g2 = _char_ngrams(rewrite, n)
    if not g1 or not g2:
        return 0.0
    return len(g1 & g2) / len(g1 | g2)


# ── 维度 7: 段落数比 ──
def metric_paragraph_ratio(orig, rewrite):
    op = [p for p in re.split(r'\n\s*\n', orig) if p.strip()]
    rp = [p for p in re.split(r'\n\s*\n', rewrite) if p.strip()]
    return len(rp) / len(op) if op else 1.0


# ── 维度 8: 句子数比 ──
def metric_sentence_ratio(orig, rewrite):
    os_ = [s for s in re.split(r'[。！？\n]+', orig) if s.strip()]
    rs = [s for s in re.split(r'[。！？\n]+', rewrite) if s.strip()]
    return len(rs) / len(os_) if os_ else 1.0


# ── 维度 9: 词林同义覆盖 ──
def metric_synonym_coverage(orig, rewrite):
    """原文词在改写中是否以同义词形式出现（处理合法同义替换）。"""
    cilin = _load_cilin()
    if not cilin:
        return None
    ow = set(_tokenize(orig))
    rw = set(_tokenize(rewrite))
    covered = 0
    total = 0
    for w in ow:
        if len(w) < 2:
            continue
        total += 1
        if w in rw:
            covered += 1
            continue
        syns = cilin.get(w, [])
        if isinstance(syns, list) and any(s in rw for s in syns):
            covered += 1
    return covered / total if total else 1.0


# ── 维度 10: 术语保留 (需 protected_terms.json) ──
def metric_protected_term_retention(orig, rewrite):
    prot_path = os.path.join(WEIGHTS_DIR, 'protected_terms.json')
    if not os.path.isfile(prot_path):
        return None
    try:
        with open(prot_path, 'r', encoding='utf-8') as f:
            prot = json.load(f)
    except Exception:
        return None
    all_terms = set()
    for terms in prot.values():
        all_terms.update(terms)
    orig_terms = [t for t in all_terms if t in orig]
    if not orig_terms:
        return None
    retained = sum(1 for t in orig_terms if t in rewrite)
    return retained / len(orig_terms)


# ── 标点异常检测（针对本项目已知问题）──
def metric_punctuation_anomaly(rewrite):
    issues = []
    # 省略号滥用
    ellipsis_count = rewrite.count('……')
    if ellipsis_count > 1:
        issues.append(f"省略号 {ellipsis_count} 次（建议 ≤1）")
    # 碎片断词：，/、 后跟 。
    frag = re.findall(r'[，、].{0,3}。', rewrite)
    # 排除正常句号结尾（，后跟短词再。是异常）
    frag_abnormal = [f for f in frag if not re.match(r'^[，、][^，。！？]{2,8}。$', f)]
    if frag_abnormal:
        issues.append(f"疑似碎片断词 {len(frag_abnormal)} 处")
    # 双标点
    double_punct = re.findall(r'[。！？；]{2,}|[，,]{2,}', rewrite)
    if double_punct:
        issues.append(f"双标点 {len(double_punct)} 处")
    # 空句：。后紧跟非空白字符再。
    empty_sent = re.findall(r'。[。]+', rewrite)
    if empty_sent:
        issues.append(f"空句 {len(empty_sent)} 处")
    # 感叹号滥用
    excl = rewrite.count('！')
    if excl > 2:
        issues.append(f"感叹号 {excl} 次（建议 ≤2）")
    return issues


# ── 综合评分 ──
def check_integrity(orig, rewrite):
    """返回多维分数 + 整体判定。

    评分逻辑:
      - 1.0 = ok（所有维度在阈值内）
      - 0.5~0.99 = suspicious（部分维度异常）
      - <0.5 = failed（语义严重破坏）
    """
    if not rewrite or not rewrite.strip():
        return {
            'status': 'failed',
            'reason': '改写为空',
            'score': 0.0,
            'metrics': {},
        }

    metrics = {
        'length_ratio': round(metric_length_ratio(orig, rewrite), 3),
        'char_overlap': round(metric_char_overlap(orig, rewrite), 3),
        'word_overlap': round(metric_word_overlap(orig, rewrite), 3),
        'keyword_retention': round(metric_keyword_retention(orig, rewrite), 3),
        'bigram_jaccard': round(metric_ngram_jaccard(orig, rewrite, 2), 3),
        'trigram_jaccard': round(metric_ngram_jaccard(orig, rewrite, 3), 3),
        'paragraph_ratio': round(metric_paragraph_ratio(orig, rewrite), 3),
        'sentence_ratio': round(metric_sentence_ratio(orig, rewrite), 3),
    }

    # 可选维度
    syn = metric_synonym_coverage(orig, rewrite)
    if syn is not None:
        metrics['synonym_coverage'] = round(syn, 3)

    prot = metric_protected_term_retention(orig, rewrite)
    if prot is not None:
        metrics['protected_term_retention'] = round(prot, 3)

    # 标点异常
    punct_issues = metric_punctuation_anomaly(rewrite)
    if punct_issues:
        metrics['punctuation_issues'] = punct_issues

    # 加权评分
    score = 1.0
    issues = []

    if metrics['length_ratio'] < 0.5:
        score = min(score, 0.5)
        issues.append(f"长度比 {metrics['length_ratio']:.2f} 过短")
    elif metrics['length_ratio'] > 1.5:
        score = min(score, 0.7)
        issues.append(f"长度比 {metrics['length_ratio']:.2f} 过长")

    if metrics['char_overlap'] < 0.6:
        score = min(score, 0.6)
        issues.append(f"字符保留 {metrics['char_overlap']:.2f} 偏低")

    if metrics['word_overlap'] < 0.5:
        score = min(score, 0.6)
        issues.append(f"词保留 {metrics['word_overlap']:.2f} 偏低")

    if metrics['keyword_retention'] < 0.7:
        score = min(score, 0.7)
        issues.append(f"关键词保留 {metrics['keyword_retention']:.2f} 偏低")

    if metrics['paragraph_ratio'] < 0.5 or metrics['paragraph_ratio'] > 2.0:
        score = min(score, 0.7)
        issues.append(f"段落数比 {metrics['paragraph_ratio']:.2f} 异常")

    # trigram Jaccard 过低说明语义结构变化大
    if metrics['trigram_jaccard'] < 0.2:
        score = min(score, 0.7)
        issues.append(f"3-gram Jaccard {metrics['trigram_jaccard']:.2f} 偏低")

    if metrics.get('protected_term_retention', 1.0) < 1.0:
        score = min(score, 0.5)
        issues.append(f"术语保留 {metrics['protected_term_retention']:.2f}（有术语被替换）")

    if punct_issues:
        score = min(score, 0.8)
        issues.append(f"标点异常: {'; '.join(punct_issues)}")

    status = 'ok' if score == 1.0 else ('suspicious' if score >= 0.5 else 'failed')
    reason = '; '.join(issues) if issues else '正常'

    return {
        'status': status,
        'reason': reason,
        'score': round(score, 2),
        'metrics': metrics,
    }


def _format_output(result, orig_len, rewrite_len):
    """人类可读输出。"""
    lines = []
    lines.append(f"状态: {result['status']}")
    lines.append(f"评分: {result['score']}")
    lines.append(f"原因: {result['reason']}")
    lines.append(f"原文字数: {orig_len} | 改写字数: {rewrite_len}")
    lines.append("")
    lines.append("维度明细:")
    for k, v in result['metrics'].items():
        if isinstance(v, list):
            lines.append(f"  {k}:")
            for item in v:
                lines.append(f"    - {item}")
        else:
            lines.append(f"  {k}: {v}")
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='语义完整度检查（零依赖，基于 MeaningBERT + ICLR 2026 多维框架）'
    )
    parser.add_argument('--orig', '-o', type=str, required=True,
                        help='原文文件路径')
    parser.add_argument('--rewrite', '-r', type=str, required=True,
                        help='改写后文件路径')
    parser.add_argument('--json', '-j', action='store_true',
                        help='JSON 输出（便于管道处理）')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='显示详细信息（含建议）')
    args = parser.parse_args()

    if not os.path.isfile(args.orig):
        print(f"错误: 原文文件不存在: {args.orig}", file=sys.stderr)
        sys.exit(2)
    if not os.path.isfile(args.rewrite):
        print(f"错误: 改写文件不存在: {args.rewrite}", file=sys.stderr)
        sys.exit(2)

    with open(args.orig, 'r', encoding='utf-8') as f:
        orig = f.read()
    with open(args.rewrite, 'r', encoding='utf-8') as f:
        rewrite = f.read()

    result = check_integrity(orig, rewrite)
    orig_cn = len(_cn_chars(orig))
    rewrite_cn = len(_cn_chars(rewrite))

    if args.json:
        out = dict(result)
        out['orig_chars'] = orig_cn
        out['rewrite_chars'] = rewrite_cn
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(_format_output(result, orig_cn, rewrite_cn))
        if args.verbose and result['status'] != 'ok':
            print("")
            print("改进建议:")
            if 'length_ratio' in result['reason']:
                print("  - 检查改写是否过度删减或扩写")
            if 'keyword' in result['reason'] or 'word_overlap' in result['reason']:
                print("  - 关键词丢失过多，考虑降低改写强度")
            if '术语' in result['reason']:
                print("  - 启用 --protect 或检查 protected_terms.json")
            if '标点' in result['reason']:
                print("  - 检查 punctuation_humanize 的省略号/感叹号触发")

    # 退出码：failed 返回 1，其余 0
    sys.exit(1 if result['status'] == 'failed' else 0)


if __name__ == '__main__':
    main()

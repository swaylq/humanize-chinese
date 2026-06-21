"""
维度感知策略路由 (Dimension-Aware Strategy Router)

核心模块: 定义改写操作、检测维度、效应权重映射，以及参数映射函数。
纯 Python 实现，零外部依赖。
"""

import json
import os

# ──────────────────────────────────────────────
# 1. 改写操作枚举
# ──────────────────────────────────────────────

REWRITE_OPS = [
    'phrase_replace',
    'synonym_replace',
    'deep_restructure',
    'noise_injection',
    'sentence_len_randomize',
    # 维普对齐新操作 (Phase 2, 通过 rewrite_operations 模块实现)
    'burstiness_engineering',
    'fragment_injection',
    'syntax_pattern_break',
    'info_density_rebalance',
    'punctuation_humanize',
    'ai_vocab_scrub',
]

# ──────────────────────────────────────────────
# 2. 操作参数范围
# ──────────────────────────────────────────────

OP_PARAM_RANGES = {
    'phrase_replace': {
        'bigram_strength': (0.0, 0.5),
    },
    'synonym_replace': {
        'strength': (0.0, 0.6),
    },
    'deep_restructure': {
        'strength': (0.3, 0.6),
        'delete_prob': (0.2, 0.6),
    },
    'noise_injection': {
        'density': (0.0, 0.25),
    },
    'sentence_len_randomize': {
        'merge_rate': (0.0, 0.25),
        'truncate_rate': (0.0, 0.25),
    },
    # 维普对齐新操作参数范围
    'burstiness_engineering': {
        'intensity': (0.0, 0.8),
    },
    'fragment_injection': {
        'intensity': (0.0, 0.5),
    },
    'syntax_pattern_break': {
        'intensity': (0.0, 0.6),
    },
    'info_density_rebalance': {
        'intensity': (0.0, 0.6),
    },
    'punctuation_humanize': {
        'intensity': (0.0, 0.4),
    },
    'ai_vocab_scrub': {
        'intensity': (0.0, 0.8),
    },
}

# ──────────────────────────────────────────────
# 3. 检测指标维度定义
# ──────────────────────────────────────────────

DIMENSION_MAX_SCORES = {
    # 规则层
    'mechanical_connectors': 8,
    'empty_grand_words': 8,
    'ai_high_freq_words': 8,
    'filler_phrases': 4,
    'three_part_structure': 8,
    'semicolon_overuse': 2,
    'dash_overuse': 2,
    'paragraph_uniform_len': 1.5,
    'uniform_sentence_rhythm': 1.5,
    # 统计层
    'sent_len_cv': 14,
    'short_frac': 12,
    'comma_density_low': 8,
    'perplexity': 10,
    'transition_density': 8,
    'emotional_flatness': 4,
    # 维普对齐 8 维语言学特征 (Phase 1)
    'syntax_similarity': 1.0,
    'pattern_repetition': 1.0,
    'mdd_mean': 10.0,
    'coherence_variance': 0.1,
    'coherence_mean': 1.0,
    'ttr_global': 1.0,
    'ttr_variance': 0.1,
    'lexical_entropy': 8.0,
    'comma_period_ratio': 5.0,
    'punctuation_variance': 1.0,
    'density_variance': 0.01,
    'density_mean': 1.0,
    'semantic_jump_std': 0.3,
    'ai_vocab_density': 20.0,
    'fingerprint_score': 1.0,
    'ai_vocab_count': 20.0,
}

# ──────────────────────────────────────────────
# 4. 改写操作 → 影响维度的效应权重映射表
# ──────────────────────────────────────────────

REWRITE_IMPACT_MAP = {
    'phrase_replace': {
        'mechanical_connectors': 0.85,
        'empty_grand_words': 0.85,
        'ai_high_freq_words': 0.80,
        'filler_phrases': 0.75,
        'three_part_structure': 0.0,
        'semicolon_overuse': 0.65,
        'dash_overuse': 0.65,
        'paragraph_uniform_len': 0.0,
        'uniform_sentence_rhythm': 0.0,
        'sent_len_cv': 0.0,
        'short_frac': 0.0,
        'comma_density_low': 0.0,
        'perplexity': 0.0,
        'transition_density': 0.0,
        'emotional_flatness': 0.0,
    },
    'synonym_replace': {
        'mechanical_connectors': 0.0,
        'empty_grand_words': 0.0,
        'ai_high_freq_words': 0.85,
        'filler_phrases': 0.0,
        'three_part_structure': 0.0,
        'semicolon_overuse': 0.0,
        'dash_overuse': 0.0,
        'paragraph_uniform_len': 0.0,
        'uniform_sentence_rhythm': 0.0,
        'sent_len_cv': 0.0,
        'short_frac': 0.0,
        'comma_density_low': 0.0,
        'perplexity': 0.75,
        'transition_density': 0.70,
        'emotional_flatness': 0.0,
    },
    'deep_restructure': {
        'mechanical_connectors': 0.0,
        'empty_grand_words': 0.0,
        'ai_high_freq_words': 0.0,
        'filler_phrases': 0.0,
        'three_part_structure': 0.80,
        'semicolon_overuse': 0.0,
        'dash_overuse': 0.0,
        'paragraph_uniform_len': 0.75,
        'uniform_sentence_rhythm': 0.85,
        'sent_len_cv': 0.85,
        'short_frac': 0.80,
        'comma_density_low': 0.0,
        'perplexity': 0.0,
        'transition_density': 0.0,
        'emotional_flatness': 0.0,
    },
    'noise_injection': {
        'mechanical_connectors': 0.0,
        'empty_grand_words': 0.0,
        'ai_high_freq_words': 0.0,
        'filler_phrases': 0.0,
        'three_part_structure': 0.0,
        'semicolon_overuse': 0.0,
        'dash_overuse': 0.0,
        'paragraph_uniform_len': 0.0,
        'uniform_sentence_rhythm': 0.0,
        'sent_len_cv': 0.0,
        'short_frac': 0.60,
        'comma_density_low': 0.0,
        'perplexity': 0.0,
        'transition_density': 0.0,
        'emotional_flatness': 0.80,
    },
    'sentence_len_randomize': {
        'mechanical_connectors': 0.0,
        'empty_grand_words': 0.0,
        'ai_high_freq_words': 0.0,
        'filler_phrases': 0.0,
        'three_part_structure': 0.0,
        'semicolon_overuse': 0.0,
        'dash_overuse': 0.0,
        'paragraph_uniform_len': 0.0,
        'uniform_sentence_rhythm': 0.85,
        'sent_len_cv': 0.90,
        'short_frac': 0.85,
        'comma_density_low': 0.0,
        'perplexity': 0.0,
        'transition_density': 0.0,
        'emotional_flatness': 0.0,
    },
    # ── 维普对齐新操作 (Phase 2) ──
    'burstiness_engineering': {
        # 现有维度
        'uniform_sentence_rhythm': 0.80,
        'sent_len_cv': 0.85,
        'short_frac': 0.75,
        # 新维度
        'syntax_similarity': 0.0,
        'pattern_repetition': 0.0,
        'mdd_mean': 0.0,
        'coherence_variance': 0.0,
        'coherence_mean': 0.0,
        'ttr_global': 0.0,
        'ttr_variance': 0.0,
        'lexical_entropy': 0.0,
        'comma_period_ratio': 0.0,
        'punctuation_variance': 0.0,
        'density_variance': 0.0,
        'density_mean': 0.0,
        'semantic_jump_std': 0.0,
        'ai_vocab_density': 0.0,
        'fingerprint_score': 0.0,
        'ai_vocab_count': 0.0,
    },
    'fragment_injection': {
        # 现有维度
        'short_frac': 0.60,
        # 新维度
        'coherence_variance': 0.70,
        'coherence_mean': 0.0,
        'density_variance': 0.60,
        'punctuation_variance': 0.50,
        'comma_period_ratio': 0.0,
        'syntax_similarity': 0.0,
        'pattern_repetition': 0.0,
        'mdd_mean': 0.0,
        'ttr_global': 0.0,
        'ttr_variance': 0.0,
        'lexical_entropy': 0.0,
        'density_mean': 0.0,
        'semantic_jump_std': 0.0,
        'ai_vocab_density': 0.0,
        'fingerprint_score': 0.0,
        'ai_vocab_count': 0.0,
    },
    'syntax_pattern_break': {
        # 新维度
        'syntax_similarity': 0.85,
        'pattern_repetition': 0.80,
        # 现有维度
        'uniform_sentence_rhythm': 0.30,
        'sent_len_cv': 0.0,
        'short_frac': 0.0,
        'comma_density_low': 0.0,
        'perplexity': 0.0,
        'transition_density': 0.0,
        'emotional_flatness': 0.0,
        'mechanical_connectors': 0.0,
        'empty_grand_words': 0.0,
        'ai_high_freq_words': 0.0,
        'filler_phrases': 0.0,
        'three_part_structure': 0.0,
        'semicolon_overuse': 0.0,
        'dash_overuse': 0.0,
        'paragraph_uniform_len': 0.0,
        # 其余新维度
        'mdd_mean': 0.0,
        'coherence_variance': 0.0,
        'coherence_mean': 0.0,
        'ttr_global': 0.0,
        'ttr_variance': 0.0,
        'lexical_entropy': 0.0,
        'comma_period_ratio': 0.0,
        'punctuation_variance': 0.0,
        'density_variance': 0.0,
        'density_mean': 0.0,
        'semantic_jump_std': 0.0,
        'ai_vocab_density': 0.0,
        'fingerprint_score': 0.0,
        'ai_vocab_count': 0.0,
    },
    'info_density_rebalance': {
        # 新维度
        'coherence_variance': 0.80,
        'density_variance': 0.85,
        'density_mean': 0.0,
        # 现有维度
        'paragraph_uniform_len': 0.75,
        'uniform_sentence_rhythm': 0.0,
        'sent_len_cv': 0.0,
        'short_frac': 0.0,
        'comma_density_low': 0.0,
        'perplexity': 0.0,
        'transition_density': 0.0,
        'emotional_flatness': 0.0,
        'mechanical_connectors': 0.0,
        'empty_grand_words': 0.0,
        'ai_high_freq_words': 0.0,
        'filler_phrases': 0.0,
        'three_part_structure': 0.0,
        'semicolon_overuse': 0.0,
        'dash_overuse': 0.0,
        # 其余新维度
        'syntax_similarity': 0.0,
        'pattern_repetition': 0.0,
        'mdd_mean': 0.0,
        'coherence_mean': 0.0,
        'ttr_global': 0.0,
        'ttr_variance': 0.0,
        'lexical_entropy': 0.0,
        'comma_period_ratio': 0.0,
        'punctuation_variance': 0.0,
        'semantic_jump_std': 0.0,
        'ai_vocab_density': 0.0,
        'fingerprint_score': 0.0,
        'ai_vocab_count': 0.0,
    },
    'punctuation_humanize': {
        # 新维度
        'comma_period_ratio': 0.90,
        'punctuation_variance': 0.80,
        # 现有维度
        'comma_density_low': 0.70,
        'uniform_sentence_rhythm': 0.0,
        'sent_len_cv': 0.0,
        'short_frac': 0.0,
        'perplexity': 0.0,
        'transition_density': 0.0,
        'emotional_flatness': 0.0,
        'mechanical_connectors': 0.0,
        'empty_grand_words': 0.0,
        'ai_high_freq_words': 0.0,
        'filler_phrases': 0.0,
        'three_part_structure': 0.0,
        'semicolon_overuse': 0.0,
        'dash_overuse': 0.0,
        'paragraph_uniform_len': 0.0,
        # 其余新维度
        'syntax_similarity': 0.0,
        'pattern_repetition': 0.0,
        'mdd_mean': 0.0,
        'coherence_variance': 0.0,
        'coherence_mean': 0.0,
        'ttr_global': 0.0,
        'ttr_variance': 0.0,
        'lexical_entropy': 0.0,
        'density_variance': 0.0,
        'density_mean': 0.0,
        'semantic_jump_std': 0.0,
        'ai_vocab_density': 0.0,
        'fingerprint_score': 0.0,
        'ai_vocab_count': 0.0,
    },
    'ai_vocab_scrub': {
        # 新维度
        'fingerprint_score': 0.85,
        'ai_vocab_density': 0.80,
        'ai_vocab_count': 0.80,
        # 现有维度
        'mechanical_connectors': 0.80,
        'empty_grand_words': 0.80,
        'ai_high_freq_words': 0.80,
        'filler_phrases': 0.0,
        'three_part_structure': 0.0,
        'semicolon_overuse': 0.0,
        'dash_overuse': 0.0,
        'paragraph_uniform_len': 0.0,
        'uniform_sentence_rhythm': 0.0,
        'sent_len_cv': 0.0,
        'short_frac': 0.0,
        'comma_density_low': 0.0,
        'perplexity': 0.0,
        'transition_density': 0.0,
        'emotional_flatness': 0.0,
        # 其余新维度
        'syntax_similarity': 0.0,
        'pattern_repetition': 0.0,
        'mdd_mean': 0.0,
        'coherence_variance': 0.0,
        'coherence_mean': 0.0,
        'ttr_global': 0.0,
        'ttr_variance': 0.0,
        'lexical_entropy': 0.0,
        'comma_period_ratio': 0.0,
        'punctuation_variance': 0.0,
        'density_variance': 0.0,
        'density_mean': 0.0,
        'semantic_jump_std': 0.0,
    },
}

# ──────────────────────────────────────────────
# 5. 映射函数
# ──────────────────────────────────────────────

NORMALIZE = 10.0


def clamp(value, lo, hi):
    """将 value 限制在 [lo, hi] 区间内。"""
    return max(lo, min(hi, value))


def map_to_range(match_score, min_val, max_val, cap=1.0):
    """
    将 match_score 映射到 [min_val, max_val] 区间，并受 cap 约束。

    match_score=0 时返回 min_val。
    match_score 越大越接近 max_val，但不超过 cap 对应的上限。

    cap 映射: cap * max_val 为实际允许的最大输出值。
    例如: min_val=0.0, max_val=0.5, cap=0.3 → 输出最大值 0.15

    实现: min_val + (max_val - min_val) * clamp(match_score / NORMALIZE, 0, cap)
    """
    t = clamp(match_score / NORMALIZE, 0.0, cap)
    return min_val + (max_val - min_val) * t


# ──────────────────────────────────────────────
# 6. 权重加载函数
# ──────────────────────────────────────────────

def load_weights(weights_path=None):
    """
    加载维度权重 JSON 文件，覆盖默认 REWRITE_IMPACT_MAP。

    若 weights_path 未提供，默认查找本文件同目录下的 dimension_weights.json。
    找不到文件或解析失败则返回默认的 REWRITE_IMPACT_MAP。
    """
    if weights_path is None:
        weights_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'weights', 'dimension_weights.json',
        )

    try:
        with open(weights_path, 'r', encoding='utf-8') as f:
            loaded = json.load(f)
        # 确保外部 JSON 的键与 REWRITE_OPS 一致
        validated = {}
        for op in REWRITE_OPS:
            if op in loaded:
                validated[op] = loaded[op]
            else:
                validated[op] = REWRITE_IMPACT_MAP.get(op, {})
        return validated
    except (FileNotFoundError, json.JSONDecodeError, IOError):
        return REWRITE_IMPACT_MAP


# ──────────────────────────────────────────────
# 7. 维度诊断函数
# ──────────────────────────────────────────────

# detect_cn issue 类别名 → 本模块维度名的映射
_ISSUE_TO_DIM = {
    'mechanical_connectors': 'mechanical_connectors',
    'empty_grand_words': 'empty_grand_words',
    'ai_high_freq_words': 'ai_high_freq_words',
    'filler_phrases': 'filler_phrases',
    'three_part_structure': 'three_part_structure',
    'balanced_arguments': 'filler_phrases',       # 平衡论述 → 归入填充
    'template_sentences': 'three_part_structure', # 模板句式 → 归入三段式
    'hedging_language': 'filler_phrases',         # 过度谨慎 → 归入填充
    'list_addiction': 'uniform_sentence_rhythm',  # 列举上瘾 → 归入节奏
    'excessive_rhetoric': 'uniform_sentence_rhythm',
    'uniform_paragraphs': 'paragraph_uniform_len',
    'low_burstiness': 'uniform_sentence_rhythm',
    'emotional_flatness': 'emotional_flatness',
    'repetitive_starters': 'uniform_sentence_rhythm',
    'low_entropy': 'perplexity',
}

# detect_cn 统计 issue 类别名 → 本模块维度名
_STAT_ISSUE_TO_DIM = {
    'stat_low_perplexity': 'perplexity',
    'stat_low_burstiness': 'uniform_sentence_rhythm',
    'stat_uniform_entropy': 'perplexity',
    'stat_low_surprisal_skew': 'perplexity',
    'stat_low_surprisal_kurt': 'perplexity',
    'stat_high_top10_bucket': 'perplexity',
    'stat_low_sentence_length_cv': 'sent_len_cv',
    'stat_low_short_sentence_fraction': 'short_frac',
    'stat_low_comma_density': 'comma_density_low',
    'stat_high_transition_density': 'transition_density',
    'stat_high_curvature': 'perplexity',
    'stat_low_binoculars_diff': 'perplexity',
    'stat_low_char_mattr': 'perplexity',
    'stat_low_para_sent_len_cv': 'sent_len_cv',
}

# detect_cn severity 权重
_SEVERITY_WEIGHTS = {
    'critical': 8,
    'high': 4,
    'medium': 2,
    'style': 1.5,
    'statistical': 0,
}

# detect_cn 统计层各 issue 的权重（需要延迟从 detect_cn 加载）
_STAT_WEIGHTS_CACHE = None


def _get_stat_weights():
    """延迟加载 detect_cn 的 STATISTICAL_WEIGHTS。"""
    global _STAT_WEIGHTS_CACHE
    if _STAT_WEIGHTS_CACHE is not None:
        return _STAT_WEIGHTS_CACHE
    try:
        from detect_cn import STATISTICAL_WEIGHTS
        _STAT_WEIGHTS_CACHE = STATISTICAL_WEIGHTS
    except ImportError:
        try:
            from scripts.detect_cn import STATISTICAL_WEIGHTS
            _STAT_WEIGHTS_CACHE = STATISTICAL_WEIGHTS
        except ImportError:
            _STAT_WEIGHTS_CACHE = {}
    return _STAT_WEIGHTS_CACHE


def diagnose_scores(text):
    """
    对输入文本执行维度诊断，返回各维度的得分字典。

    返回结构:
    {
        'dims': {dim_name: score},          # 各维度的规则+统计合并分
        'rule_score': float,                # 规则层总分 (0-60)
        'stat_score': float,                # 统计层总分 (0-40)
        'rule_stat_total': float,           # rule+stat+bonus (0-100)
        'lr_score': float,                  # LR 模型分 (0-100)
        'total_score': float,               # 最终融合分 0.2*rule_stat + 0.8*lr
        'char_count': int,                  # 中文字符数
    }
    """
    dims = {dim: 0.0 for dim in DIMENSION_MAX_SCORES}

    # ── 规则层 ──
    try:
        from detect_cn import detect_patterns
        from ngram_model import compute_lr_score
    except ImportError:
        try:
            from scripts.detect_cn import detect_patterns
            from scripts.ngram_model import compute_lr_score
        except ImportError:
            return {
                'dims': dims,
                'rule_score': 0.0,
                'stat_score': 0.0,
                'rule_stat_total': 0.0,
                'lr_score': 0.0,
                'total_score': 0.0,
                'char_count': 0,
            }

    issues, metrics = detect_patterns(text)
    char_count = metrics.get('char_count', 0)

    stat_weights = _get_stat_weights()

    # 计算 rule_score + stat_score
    rule_raw = 0
    stat_raw = 0

    for category, items in issues.items():
        if category.startswith('stat_'):
            # 统计层
            if items:
                weight = stat_weights.get(category, 5)
                stat_raw += weight
                dim_name = _STAT_ISSUE_TO_DIM.get(category)
                if dim_name and dim_name in dims:
                    dims[dim_name] += weight
        else:
            # 规则层
            for item in items:
                severity = item.get('severity', 'medium')
                weight = _SEVERITY_WEIGHTS.get(severity, 2)
                count = item.get('count', 1)
                score = weight * min(count, 5)
                rule_raw += score

                dim_name = _ISSUE_TO_DIM.get(category)
                if dim_name and dim_name in dims:
                    dims[dim_name] += score

    # 额外加成
    bonus = 0.0
    emo_density = metrics.get('emotional_density', 0.5)
    if emo_density < 0.1 and char_count > 500:
        bonus += 5
        if 'emotional_flatness' in dims:
            dims['emotional_flatness'] += 5
    entropy_raw = metrics.get('entropy')
    if entropy_raw is not None and entropy_raw < 5.5:
        bonus += 5
        if 'perplexity' in dims:
            dims['perplexity'] += 5

    rule_score = min(60.0, float(rule_raw))
    stat_score = min(40.0, float(stat_raw))
    rule_stat_total = min(100.0, rule_score + stat_score + bonus)

    # ── LR 层 ──
    lr_score = 0.0
    try:
        lr_result = compute_lr_score(text)
        if lr_result and 'score' in lr_result:
            lr_score = float(lr_result['score'])
    except Exception:
        pass

    total_score = round(0.2 * rule_stat_total + 0.8 * lr_score)

    # ── 维普对齐 8 维语言学特征 (Phase 1, try/except 降级) ──
    # 通过 linguistic_features.diagnose_linguistic_features() 追加 8 维检测结果。
    # 若 linguistic_features 或其依赖 (jieba / numpy) 不可用，静默降级，不影响原功能。
    try:
        from linguistic_features import diagnose_linguistic_features as _dlf
        _lf_result = _dlf(text)
        _lf_keys = [
            'syntax_similarity', 'pattern_repetition', 'mdd_mean',
            'coherence_variance', 'coherence_mean',
            'ttr_global', 'ttr_variance', 'lexical_entropy',
            'comma_period_ratio', 'punctuation_variance',
            'density_variance', 'density_mean',
            'semantic_jump_std',
            'ai_vocab_density', 'fingerprint_score', 'ai_vocab_count',
        ]
        for _k in _lf_keys:
            if _k in _lf_result and _k not in dims:
                dims[_k] = _lf_result[_k]
        _vipu_score = _lf_result.get('_vipu_aligned_score', 0.0)
    except Exception:
        _vipu_score = 0.0

    return {
        'dims': dims,
        'rule_score': rule_score,
        'stat_score': stat_score,
        'rule_stat_total': rule_stat_total,
        'lr_score': lr_score,
        'total_score': total_score,
        'char_count': char_count,
        '_vipu_aligned_score': _vipu_score,
    }


def measure_impact(original, rewritten):
    """
    测量改写前后的各维度冲击量。

    返回: {dim_name: impact} 字典，impact = score_before - score_after
    正数表示改善（分数降低），负数表示变差（分数升高）。
    """
    before = diagnose_scores(original)
    after = diagnose_scores(rewritten)

    impact = {}
    before_dims = before.get('dims', {})
    after_dims = after.get('dims', {})

    all_dims = set(before_dims.keys()) | set(after_dims.keys())
    for dim in all_dims:
        impact[dim] = before_dims.get(dim, 0.0) - after_dims.get(dim, 0.0)

    # 附加总体变化
    impact['_total'] = before.get('total_score', 0) - after.get('total_score', 0)
    impact['_rule_stat'] = before.get('rule_stat_total', 0) - after.get('rule_stat_total', 0)
    impact['_lr'] = before.get('lr_score', 0) - after.get('lr_score', 0)

    return impact


# ──────────────────────────────────────────────
# 8. 策略路由函数
# ──────────────────────────────────────────────

# 三档总强度的 cap 值
TIER_CAPS = {
    'conservative': 0.3,
    'moderate': 0.7,
    'full': 1.0,
}

# 问题维度筛选阈值：得分超过该维度满分的此比例才算问题
PROBLEM_DIM_THRESHOLD = 0.3

# match_score 归一化常数
ROUTE_NORMALIZE = 10.0


def route_strategy(scores, tier='moderate'):
    """
    根据维度诊断结果，为每个改写操作计算独立的操作强度。

    参数:
        scores: 维度得分字典，例如 {'mechanical_connectors': 16, 'sent_len_cv': 14, ...}
        tier: 总强度档位，'conservative' / 'moderate' / 'full'

    返回:
        {
            'ops': {op_name: {param: value}},
            'match_scores': {op_name: float},
            'problem_dims': [dim_name, ...],
            'tier_cap': float,
        }
    """
    cap = TIER_CAPS.get(tier, 0.7)

    # Step 2: 筛选问题维度
    problem_dims = []
    for dim, score in scores.items():
        max_s = DIMENSION_MAX_SCORES.get(dim, 10)
        if score > max_s * PROBLEM_DIM_THRESHOLD:
            problem_dims.append(dim)

    # Step 3: 计算每个操作的 match_score
    impact_map = load_weights()  # 从 JSON 加载校准后权重，或使用默认值
    match_scores = {}
    for op in REWRITE_OPS:
        match = 0.0
        op_weights = impact_map.get(op, {})
        for dim in problem_dims:
            weight = op_weights.get(dim, 0.0)
            match += weight * scores.get(dim, 0.0)
        match_scores[op] = match

    # Step 4: 将 match_score 映射为具体参数值
    ops_params = {}
    for op in REWRITE_OPS:
        op_params = {}
        param_ranges = OP_PARAM_RANGES.get(op, {})
        for param, (min_val, max_val) in param_ranges.items():
            intensity = map_to_range(match_scores[op], min_val, max_val, cap)
            op_params[param] = round(intensity, 4)
        ops_params[op] = op_params

    return {
        'ops': ops_params,
        'match_scores': match_scores,
        'problem_dims': problem_dims,
        'tier_cap': cap,
    }


# ──────────────────────────────────────────────
# 自测
# ──────────────────────────────────────────────

if __name__ == '__main__':
    print("=" * 60)
    print("维度感知策略路由 - 自测")
    print("=" * 60)

    # 打印操作列表
    print("\n[改写操作]")
    for op in REWRITE_OPS:
        print(f"  - {op}: params={list(OP_PARAM_RANGES[op].keys())}")

    # 打印维度列表
    print("\n[检测维度]")
    for dim, max_score in DIMENSION_MAX_SCORES.items():
        print(f"  - {dim}: max_score={max_score}")

    # 打印权重映射表
    print("\n[效应权重映射表]")
    for op in REWRITE_OPS:
        weights = REWRITE_IMPACT_MAP[op]
        active_dims = [(d, w) for d, w in weights.items() if w > 0.0]
        if active_dims:
            print(f"  {op}:")
            for d, w in active_dims:
                print(f"    -> {d}: {w}")
        else:
            print(f"  {op}: (无关联维度)")

    # 测试 map_to_range
    print("\n[map_to_range 测试]")
    test_cases = [
        # (match_score, min_val, max_val, cap)
        (0.0, 0.0, 0.5, 1.0),
        (5.0, 0.0, 0.5, 1.0),
        (10.0, 0.0, 0.5, 1.0),
        (10.0, 0.0, 0.5, 0.3),
        (20.0, 0.0, 0.5, 0.3),
        (3.0, 0.2, 0.6, 1.0),
        (0.0, 0.0, 0.25, 1.0),
    ]
    for ms, mn, mx, cp in test_cases:
        result = map_to_range(ms, mn, mx, cp)
        print(f"  map_to_range(ms={ms}, min={mn}, max={mx}, cap={cp}) = {result:.4f}")

    # 测试 load_weights（默认路径）
    print("\n[load_weights 测试]")
    weights = load_weights()
    print(f"  加载成功，共 {len(weights)} 个操作的权重映射")
    assert set(weights.keys()) == set(REWRITE_OPS), "操作数量不匹配"

    # 测试 diagnose_scores（含 linguistic_features 集成）
    print("\n[diagnose_scores 集成测试]")
    test_text = (
        "首先，人工智能技术在现代社会中发挥着越来越重要的作用。"
        "其次，随着大数据技术的不断发展，人工智能在各个领域的应用日益广泛。"
        "最后，综上所述，人工智能的发展前景十分广阔。"
        "值得注意的是，我们还需要关注人工智能发展过程中的伦理问题。"
        "总而言之，人工智能技术将在未来社会中扮演更加重要的角色。"
    )
    try:
        dr = diagnose_scores(test_text)
        print(f"  规则层分数: {dr['rule_score']:.1f}")
        print(f"  统计层分数: {dr['stat_score']:.1f}")
        print(f"  LR 模型分: {dr['lr_score']:.1f}")
        print(f"  总分: {dr['total_score']}")
        print(f"  中文字符数: {dr['char_count']}")
        print(f"  维普对齐 AIGC 风险分: {dr.get('_vipu_aligned_score', 'N/A')}")
        lf_dims_present = [k for k in ['syntax_similarity', 'coherence_variance', 'ttr_global',
                                        'comma_period_ratio', 'density_variance', 'fingerprint_score']
                           if k in dr.get('dims', {})]
        print(f"  语言学特征维度已集成: {len(lf_dims_present)}/{len(lf_dims_present)}")
        for d in lf_dims_present:
            print(f"    {d}: {dr['dims'][d]}")
    except Exception as e:
        print(f"  diagnose_scores 集成异常 (可忽略): {e}")

    # 测试 route_strategy（含新操作）
    print("\n[route_strategy 集成测试]")
    if lf_dims_present:
        try:
            route = route_strategy(dr['dims'], tier='moderate')
            all_ops = route.get('ops', {})
            new_ops_present = [op for op in REWRITE_OPS if op in all_ops]
            print(f"  路由成功，共 {len(new_ops_present)}/{len(REWRITE_OPS)} 个操作已路由:")
            for op in ['burstiness_engineering', 'syntax_pattern_break', 'ai_vocab_scrub']:
                if op in all_ops:
                    print(f"    {op}: {all_ops[op]}")
            print(f"  问题维度数: {len(route.get('problem_dims', []))}")
        except Exception as e:
            print(f"  route_strategy 集成异常 (可忽略): {e}")

    print("\n✓ 自测通过")

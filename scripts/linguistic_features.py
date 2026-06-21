"""
linguistic_features.py - 维普对齐的 8 维语言学特征检测

本模块完全独立于 humanize-chinese-dimension 项目，零外部依赖。
可单独使用: python linguistic_features.py --text "输入文本"

设计原则:
  - 纯统计/规则，无 LLM
  - 单篇文本 < 0.5s (CPU)
  - 可解释，返回每个维度的子指标
  - 与原项目解耦，可通过 try/except 降级集成

依赖:
  - jieba (中文分词) — 检测端核心, 6/8 维度需要
  - jieba.posseg (词性标注) — 句法/MDD/密度需要
  - numpy (可选, 数值计算) — 无 numpy 时走 Python statistics fallback

使用示例:
  >>> from linguistic_features import diagnose_linguistic_features
  >>> result = diagnose_linguistic_features("这是测试文本。")
  >>> print(result['syntax_similarity'])
"""

import re
import json
import os
import math
from collections import Counter

try:
    import jieba
    import jieba.posseg as pseg
    _HAS_JIEBA = True
except ImportError:
    _HAS_JIEBA = False

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False

# 注: scipy 曾用于 lexical_entropy 计算, 但该指标未参与 _vipu_aligned_score 评分。
# v2 移除 scipy 依赖, lexical_entropy 改用 Python 原生 math.log 计算。


# ============================================================================
# 工具函数
# ============================================================================

def _count_cn(s):
    """统计中文字符数"""
    return sum(1 for c in s if '\u4e00' <= c <= '\u9fff')


def split_sentences(text):
    """分句: 按句号/感叹号/问号/分号/换行分割"""
    sentences = re.split(r'[。！？；\n]+', text)
    return [s.strip() for s in sentences if s.strip()]


def split_paragraphs(text):
    """分段: 按空行分割"""
    return [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]


def _cosine_sim(c1, c2):
    """两个 Counter 的余弦相似度"""
    all_words = set(c1.keys()) | set(c2.keys())
    if not all_words:
        return 0.0
    if not _HAS_NUMPY:
        return 0.0
    v1 = np.array([c1.get(w, 0) for w in all_words])
    v2 = np.array([c2.get(w, 0) for w in all_words])
    dot = np.dot(v1, v2)
    norm = np.linalg.norm(v1) * np.linalg.norm(v2)
    return float(dot / norm) if norm > 0 else 0.0


def _to_bow(text):
    """文本的词袋表示"""
    if not _HAS_JIEBA:
        return Counter()
    return Counter(jieba.lcut(text))


def _get_pos_sequence(text):
    """获取词性序列 (去标点)"""
    if not _HAS_JIEBA:
        return []
    words = list(pseg.cut(text))
    return [w.flag for w in words if w.flag != 'x']


def _get_ngrams(seq, n=3):
    """获取 n-gram 集合"""
    return set(tuple(seq[i:i+n]) for i in range(len(seq)-n+1))


def _load_vocab_dict():
    """加载 AI 词汇指纹词典"""
    vocab_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'weights', 'ai_vocab_dict.json')
    try:
        with open(vocab_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


# ============================================================================
# 维度 1: 句法结构相似度 (对应维普 30% 权重)
# ============================================================================

def compute_syntax_similarity(text):
    """
    计算句法结构相似度。

    算法:
      1. jieba.posseg 对每句话进行词性标注
      2. 提取词性序列 (如 ['n', 'v', 'n', 'u'])
      3. 计算所有句对的词性 3-gram Jaccard 相似度
      4. 返回均值

    AI 特征: 相似度 > 0.65
    人类特征: 相似度 0.30-0.50

    返回:
      syntax_similarity: 句法结构相似度 (0-1, 越高越像 AI)
      pattern_repetition: 句式重复率 (0-1)
      sentence_count: 句子数
    """
    sentences = split_sentences(text)
    if len(sentences) < 2:
        return {'syntax_similarity': 0.0, 'pattern_repetition': 0.0, 'sentence_count': len(sentences)}

    # 提取每句的词性序列
    pos_sequences = []
    for sent in sentences:
        try:
            seq = _get_pos_sequence(sent)
            if seq:
                pos_sequences.append(seq)
        except Exception:
            pass

    if len(pos_sequences) < 2:
        return {'syntax_similarity': 0.0, 'pattern_repetition': 0.0, 'sentence_count': len(sentences)}

    # 计算 3-gram Jaccard 相似度
    ngram_sets = [_get_ngrams(seq) for seq in pos_sequences]

    similarities = []
    for i in range(len(ngram_sets)):
        for j in range(i+1, len(ngram_sets)):
            s1, s2 = ngram_sets[i], ngram_sets[j]
            if s1 and s2:
                jac = len(s1 & s2) / len(s1 | s2)
                similarities.append(jac)

    mean_sim = float(np.mean(similarities)) if _HAS_NUMPY and similarities else (sum(similarities)/len(similarities) if similarities else 0.0)

    # 句式重复率: 相同词性序列模式的出现频率
    pattern_counter = Counter(tuple(seq) for seq in pos_sequences)
    repetition = sum(c for c in pattern_counter.values() if c > 1) / len(pos_sequences)

    return {
        'syntax_similarity': round(float(mean_sim), 4),
        'pattern_repetition': round(float(repetition), 4),
        'sentence_count': len(sentences),
    }


# ============================================================================
# 维度 2: 平均依存距离 MDD (轻量近似)
# ============================================================================

def compute_mdd(text):
    """
    计算平均依存距离 (Mean Dependency Distance) 的轻量近似。

    理论:
      MDD = (1/(n-1)) * Σ|DD_i|
      完整 MDD 需依存句法分析 (HanLP/pyltp)

    轻量近似:
      基于词性序列的主谓/动宾距离:
      - 主语(n)到谓语(v)的距离
      - 谓语(v)到宾语(n)的距离
      - 修饰词到中心词的距离

    AI 特征: MDD < 2.0 (句法结构简单)
    人类特征: MDD > 3.0 (句法结构复杂)

    返回:
      mdd_mean: 平均依存距离
      mdd_std: 依存距离标准差
    """
    sentences = split_sentences(text)
    all_distances = []

    for sent in sentences:
        try:
            words = list(pseg.cut(sent))
        except Exception:
            words = []
        words = [w for w in words if w.flag != 'x']
        n = len(words)
        if n < 2:
            continue

        # 近似: 计算主谓、动宾、修饰关系的距离
        # used 标记已配对的词, 避免一个词被多次匹配 (如宾语名词被误当下一动词的主语)
        used = set()
        for i, w in enumerate(words):
            if i in used:
                continue
            # 主谓: n -> v
            if w.flag.startswith('n'):
                for j in range(i+1, min(i+10, n)):
                    if j in used:
                        continue
                    if words[j].flag.startswith('v'):
                        all_distances.append(j - i)
                        used.add(i)
                        used.add(j)
                        break
            # 动宾: v -> n
            elif w.flag.startswith('v'):
                for j in range(i+1, min(i+10, n)):
                    if j in used:
                        continue
                    if words[j].flag.startswith('n'):
                        all_distances.append(j - i)
                        used.add(i)
                        used.add(j)
                        break
            # 修饰: a/ad/an/d -> n
            elif w.flag in ('a', 'ad', 'an', 'd'):
                for j in range(i+1, min(i+5, n)):
                    if j in used:
                        continue
                    if words[j].flag.startswith('n'):
                        all_distances.append(j - i)
                        used.add(i)
                        used.add(j)
                        break

    if not all_distances:
        return {'mdd_mean': 0.0, 'mdd_std': 0.0}

    if _HAS_NUMPY:
        mean_mdd = float(np.mean(all_distances))
        std_mdd = float(np.std(all_distances))
    else:
        import statistics as _stats
        mean_mdd = sum(all_distances) / len(all_distances)
        std_mdd = float(_stats.pstdev(all_distances)) if len(all_distances) > 1 else 0.0

    return {
        'mdd_mean': round(mean_mdd, 4),
        'mdd_std': round(std_mdd, 4),
    }


# ============================================================================
# 维度 3: 段落连贯性方差 (对应维普 25% 权重)
# ============================================================================

def compute_paragraph_coherence(text):
    """
    计算段落连贯性。

    算法:
      1. 按空行分割段落
      2. 每段构建词袋向量
      3. 计算相邻段落的余弦相似度
      4. 返回均值和方差

    AI 特征: 关联度稳定 0.6-0.8, 方差小 (< 0.02)
    人类特征: 关联度波动 0.3-0.9, 方差大 (> 0.05)

    返回:
      coherence_mean: 相似度均值
      coherence_variance: 相似度方差 (越高越像人类)
      semantic_jump_count: 语义跳跃次数 (相似度 < 0.4)
    """
    paragraphs = split_paragraphs(text)
    if len(paragraphs) < 2:
        return {'coherence_mean': 0.0, 'coherence_variance': 0.0, 'semantic_jump_count': 0}

    bows = [_to_bow(p) for p in paragraphs]

    sims = []
    for i in range(len(bows)-1):
        sim = _cosine_sim(bows[i], bows[i+1])
        sims.append(sim)

    if not sims:
        return {'coherence_mean': 0.0, 'coherence_variance': 0.0, 'semantic_jump_count': 0}

    if _HAS_NUMPY:
        mean_sim = float(np.mean(sims))
        var_sim = float(np.var(sims))
    else:
        import statistics as _stats
        mean_sim = sum(sims) / len(sims)
        var_sim = float(_stats.pvariance(sims))
    jump_count = int(sum(1 for s in sims if s < 0.4))

    return {
        'coherence_mean': round(mean_sim, 4),
        'coherence_variance': round(var_sim, 6),
        'semantic_jump_count': jump_count,
    }


# ============================================================================
# 维度 4: 词汇多样性 TTR (对应维普 15% 权重)
# ============================================================================

def compute_ttr(text):
    """
    计算词汇多样性 TTR (Type-Token Ratio)。

    算法:
      1. 全文 TTR = 不重复词数 / 总词数
      2. 段落间 TTR 方差
      3. 词汇 Shannon 熵

    AI 特征: TTR 稳定 0.45-0.55, 方差小
    人类特征: TTR 波动 0.35-0.7, 方差大

    返回:
      ttr_global: 全文 TTR
      ttr_variance: 段落 TTR 方差
      lexical_entropy: 词汇熵
    """
    if not _HAS_JIEBA:
        return {'ttr_global': 0.5, 'ttr_variance': 0.0, 'lexical_entropy': 0.0}

    words = jieba.lcut(text)
    total = len(words)
    unique = len(set(words))
    ttr_global = unique / max(total, 1)

    paragraphs = split_paragraphs(text)
    ttrs = []
    for para in paragraphs:
        pwords = jieba.lcut(para)
        if len(pwords) >= 5:
            ttrs.append(len(set(pwords)) / len(pwords))

    # 段落 TTR 方差: 优先 numpy, fallback 用 Python 原生 statistics
    if ttrs:
        if _HAS_NUMPY:
            ttr_var = float(np.var(ttrs))
        else:
            import statistics as _stats
            ttr_var = float(_stats.pvariance(ttrs))
    else:
        ttr_var = 0.0

    # 词汇熵 (香农熵): 纯 Python 标准库 math.log
    word_counts = Counter(words)
    lex_entropy = 0.0
    if total > 0:
        for count in word_counts.values():
            p = count / total
            if p > 0:
                lex_entropy -= p * math.log2(p)

    return {
        'ttr_global': round(float(ttr_global), 4),
        'ttr_variance': round(ttr_var, 6),
        'lexical_entropy': round(lex_entropy, 4),
    }


# ============================================================================
# 维度 5: 标点模式 (对应维普 10% 权重)
# ============================================================================

def compute_punctuation_pattern(text):
    """
    计算标点使用模式。

    AI 特征:
      - 逗号:句号 = 2:1 到 3:1
      - 分号频率低
      - 感叹号问号几乎不出现

    人类特征:
      - 标点使用不规律
      - 偶有感叹号、问号、省略号

    返回:
      comma_period_ratio: 逗号句号比
      punctuation_variance: 标点使用多样性 (0-1)
      semicolon_density: 分号密度 (每千字)
      exclamation_question_density: 感叹号问号密度 (每千字)
    """
    comma = text.count('，') + text.count(',')
    period = text.count('。')
    semicolon = text.count('；') + text.count(';')
    exclamation = text.count('！') + text.count('!')
    question = text.count('？') + text.count('?')
    ellipsis = text.count('……') + text.count('…')
    dash = text.count('——') + text.count('—')
    colon = text.count('：') + text.count(':')

    cn_chars = _count_cn(text)

    ratio = comma / max(period, 1)
    semi_density = semicolon / max(cn_chars / 1000, 0.01)
    eq_density = (exclamation + question) / max(cn_chars / 1000, 0.01)

    # 标点多样性: 使用了多少种标点 (归一化到 0-1)
    punct_types = sum(1 for x in [comma, period, semicolon, exclamation,
                                   question, ellipsis, dash, colon] if x > 0)
    punct_variance = punct_types / 8.0

    return {
        'comma_period_ratio': round(float(ratio), 4),
        'punctuation_variance': round(float(punct_variance), 4),
        'semicolon_density': round(float(semi_density), 4),
        'exclamation_question_density': round(float(eq_density), 4),
    }


# ============================================================================
# 维度 6: 信息密度方差 (对应维普 20% 权重)
# ============================================================================

def compute_info_density_variance(text):
    """
    计算信息密度分布方差。

    算法:
      1. 分段
      2. 每段计算动名词密度 = (动词数 + 名词数) / 字数
      3. 计算段落间密度的方差

    AI 特征: 密度均匀, 方差小
    人类特征: 密度起伏大, 方差大

    返回:
      density_variance: 密度方差 (越高越像人类)
      density_mean: 密度均值
    """
    if not _HAS_JIEBA:
        return {'density_variance': 0.0, 'density_mean': 0.0}

    paragraphs = split_paragraphs(text)
    if len(paragraphs) < 2:
        return {'density_variance': 0.0, 'density_mean': 0.0}

    densities = []
    for para in paragraphs:
        words = list(pseg.cut(para))
        # 只统计非标点词
        content_words = [w for w in words if w.flag != 'x']
        verbs = sum(1 for w in content_words if w.flag.startswith('v'))
        nouns = sum(1 for w in content_words if w.flag.startswith('n'))
        total_words = len(content_words)
        # 信息密度 = 实义词(动名词) / 总词数 (0-1)
        density = (verbs + nouns) / max(total_words, 1)
        densities.append(density)

    # 统计: 优先 numpy, fallback 用 Python 原生 statistics (修复 v1 无 numpy 时 var_d=0.0 的 bug)
    if _HAS_NUMPY:
        densities_arr = np.array(densities)
        mean_d = float(np.mean(densities_arr))
        var_d = float(np.var(densities_arr))
    else:
        import statistics as _stats
        mean_d = sum(densities) / len(densities)
        var_d = float(_stats.pvariance(densities))

    return {
        'density_variance': round(var_d, 8),
        'density_mean': round(mean_d, 6),
    }


# ============================================================================
# 维度 7: 语义跳跃指数
# ============================================================================

def compute_semantic_jump(text):
    """
    计算语义跳跃指数。

    算法:
      1. 分句
      2. 计算相邻句子的词袋余弦相似度
      3. 返回标准差

    AI 特征: 标准差小 (< 0.1, 语义平滑)
    人类特征: 标准差大 (> 0.15, 有跳跃)

    返回:
      semantic_jump_std: 句间相似度标准差
      low_overlap_count: 低重叠句对数 (相似度 < 0.3)
    """
    if not _HAS_JIEBA:
        return {'semantic_jump_std': 0.0, 'low_overlap_count': 0}

    sentences = split_sentences(text)
    if len(sentences) < 2:
        return {'semantic_jump_std': 0.0, 'low_overlap_count': 0}

    bows = [_to_bow(s) for s in sentences]

    sims = []
    for i in range(len(bows)-1):
        sim = _cosine_sim(bows[i], bows[i+1])
        sims.append(sim)

    if not sims:
        return {'semantic_jump_std': 0.0, 'low_overlap_count': 0}

    if _HAS_NUMPY:
        std_sim = float(np.std(sims))
    else:
        import statistics as _stats
        std_sim = float(_stats.pstdev(sims)) if len(sims) > 1 else 0.0
    low_count = int(sum(1 for s in sims if s < 0.3))

    return {
        'semantic_jump_std': round(std_sim, 6),
        'low_overlap_count': low_count,
    }


# ============================================================================
# 维度 8: AI 词汇指纹
# ============================================================================

def compute_ai_vocab_fingerprint(text, vocab_dict=None):
    """
    计算中文 AI 词汇指纹匹配率。

    算法:
      1. 加载 AI 词汇指纹词典
      2. 统计文本中 AI 指纹词的出现频率
      3. 与人类基线频率对比

    AI 特征: 指纹词频率高
    人类特征: 指纹词频率低

    参数:
      text: 输入文本
      vocab_dict: AI 词汇指纹词典 (可选, 默认自动加载)

    返回:
      ai_vocab_count: AI 指纹词出现总次数
      ai_vocab_density: AI 指纹词密度 (每千中文字)
      fingerprint_score: 0-1, 越高越像 AI
    """
    if vocab_dict is None:
        vocab_dict = _load_vocab_dict()

    cn_chars = _count_cn(text)

    ai_count = 0
    matched_categories = set()

    for category, word_list in vocab_dict.items():
        if isinstance(word_list, list):
            for word in word_list:
                count = text.count(word)
                if count > 0:
                    ai_count += count
                    matched_categories.add(category)

    # 密度 = 每千中文字的 AI 指纹词数
    if cn_chars > 0:
        density = ai_count * 1000.0 / cn_chars
    else:
        density = 0.0
    total_categories = max(len(vocab_dict), 1)

    # 指纹分数: 密度归一化 + 类别覆盖
    density_component = min(density / 15, 1.0)
    coverage_component = len(matched_categories) / total_categories
    fingerprint_score = density_component * 0.7 + coverage_component * 0.3

    return {
        'ai_vocab_count': int(ai_count),
        'ai_vocab_density': round(float(density), 4),
        'fingerprint_score': round(float(fingerprint_score), 4),
    }


# ============================================================================
# 统一诊断接口
# ============================================================================

def diagnose_linguistic_features(text, vocab_dict=None):
    """
    统一诊断接口: 计算全部 8 维语言学特征。

    参数:
      text: 输入文本
      vocab_dict: AI 词汇指纹词典 (可选)

    返回:
      dict: 8 维特征的扁平化字典

    使用示例:
      >>> from linguistic_features import diagnose_linguistic_features
      >>> result = diagnose_linguistic_features("这是一段测试文本。今天天气不错。")
      >>> print(result['syntax_similarity'])
    """
    if not _HAS_JIEBA:
        # 降级: 返回默认值 + 可计算的维度 (标点、AI 词汇)
        result = {
            'syntax_similarity': 0.0, 'pattern_repetition': 0.0,
            'mdd_mean': 0.0,
            'coherence_variance': 0.0, 'coherence_mean': 0.0,
            'ttr_global': 0.5, 'ttr_variance': 0.0, 'lexical_entropy': 0.0,
            'comma_period_ratio': 2.5, 'punctuation_variance': 0.5,
            'semicolon_density': 0.0, 'exclamation_question_density': 0.0,
            'density_variance': 0.0, 'density_mean': 0.0,
            'semantic_jump_std': 0.0, 'low_overlap_count': 0,
        }
        # 仍计算 AI 词汇指纹 (基于字符串匹配, 不依赖 jieba)
        r = compute_ai_vocab_fingerprint(text, vocab_dict)
        result.update(r)
        # 计算标点模式 (不依赖 jieba)
        p = compute_punctuation_pattern(text)
        result['comma_period_ratio'] = p['comma_period_ratio']
        result['punctuation_variance'] = p['punctuation_variance']
        # 维普对齐总分
        vipu_score = 0.0
        vipu_score += result.get('syntax_similarity', 0.0) * 30
        ai_coherence = max(0, (result.get('coherence_mean', 0.0) - 0.4) / 0.4)
        ai_coherence += max(0, (0.02 - result.get('coherence_variance', 0.0)) / 0.02)
        vipu_score += min(ai_coherence, 1.0) * 25
        ttr = result.get('ttr_global', 0.5)
        vipu_score += (0.8 * 15) if 0.40 <= ttr <= 0.60 else (0.2 * 15)
        ai_density = max(0, (0.005 - result.get('density_variance', 0.0)) / 0.005)
        vipu_score += min(ai_density, 1.0) * 20
        cpr = result.get('comma_period_ratio', 2.5)
        vipu_score += (0.9 * 10) if 2.0 <= cpr <= 3.5 else (0.1 * 10)
        result['_vipu_aligned_score'] = round(vipu_score, 2)
        return result

    result = {}

    # 维度 1: 句法结构相似度
    try:
        r = compute_syntax_similarity(text)
        result['syntax_similarity'] = r['syntax_similarity']
        result['pattern_repetition'] = r['pattern_repetition']
    except Exception as e:
        result['syntax_similarity'] = 0.0
        result['pattern_repetition'] = 0.0

    # 维度 2: 平均依存距离
    try:
        r = compute_mdd(text)
        result['mdd_mean'] = r['mdd_mean']
    except Exception as e:
        result['mdd_mean'] = 0.0

    # 维度 3: 段落连贯性
    try:
        r = compute_paragraph_coherence(text)
        result['coherence_variance'] = r['coherence_variance']
        result['coherence_mean'] = r['coherence_mean']
    except Exception as e:
        result['coherence_variance'] = 0.0
        result['coherence_mean'] = 0.0

    # 维度 4: 词汇多样性 TTR
    try:
        r = compute_ttr(text)
        result['ttr_global'] = r['ttr_global']
        result['ttr_variance'] = r['ttr_variance']
        result['lexical_entropy'] = r['lexical_entropy']
    except Exception as e:
        result['ttr_global'] = 0.5
        result['ttr_variance'] = 0.0
        result['lexical_entropy'] = 0.0

    # 维度 5: 标点模式
    try:
        r = compute_punctuation_pattern(text)
        result['comma_period_ratio'] = r['comma_period_ratio']
        result['punctuation_variance'] = r['punctuation_variance']
    except Exception as e:
        result['comma_period_ratio'] = 2.5
        result['punctuation_variance'] = 0.5

    # 维度 6: 信息密度方差
    try:
        r = compute_info_density_variance(text)
        result['density_variance'] = r['density_variance']
    except Exception as e:
        result['density_variance'] = 0.0

    # 维度 7: 语义跳跃
    try:
        r = compute_semantic_jump(text)
        result['semantic_jump_std'] = r['semantic_jump_std']
    except Exception as e:
        result['semantic_jump_std'] = 0.0

    # 维度 8: AI 词汇指纹
    try:
        r = compute_ai_vocab_fingerprint(text, vocab_dict)
        result['ai_vocab_density'] = r['ai_vocab_density']
        result['fingerprint_score'] = r['fingerprint_score']
        result['ai_vocab_count'] = r['ai_vocab_count']
    except Exception as e:
        result['ai_vocab_density'] = 0.0
        result['fingerprint_score'] = 0.0
        result['ai_vocab_count'] = 0

    # 维普对齐的五大维度总分 (越高越像 AI)
    # 句法结构 30% | 段落连贯性 25% | 词汇多样性 15% | 信息密度 20% | 标点特征 10%
    vipu_score = 0.0
    if 'syntax_similarity' in result:
        vipu_score += result['syntax_similarity'] * 30
    if 'coherence_mean' in result:
        # 高连贯性 = AI 特征, 低方差 = AI 特征
        ai_coherence = max(0, (result['coherence_mean'] - 0.4) / 0.4)
        ai_coherence += max(0, (0.02 - result['coherence_variance']) / 0.02)
        result['_ai_coherence_score'] = round(min(ai_coherence, 1.0), 4)
        vipu_score += min(ai_coherence, 1.0) * 25
    if 'ttr_global' in result:
        # TTR 在 0.45-0.55 = AI 特征
        if 0.40 <= result['ttr_global'] <= 0.60:
            vipu_score += 0.8 * 15
        else:
            vipu_score += 0.2 * 15
    if 'density_variance' in result:
        # density_variance 修改后范围约 0.001-0.05, 阈值用 0.005
        ai_density = max(0, (0.005 - result['density_variance']) / 0.005)
        result['_ai_density_score'] = round(min(ai_density, 1.0), 4)
        vipu_score += min(ai_density, 1.0) * 20
    if 'comma_period_ratio' in result:
        if 2.0 <= result['comma_period_ratio'] <= 3.5:
            vipu_score += 0.9 * 10
        else:
            vipu_score += 0.1 * 10

    result['_vipu_aligned_score'] = round(vipu_score, 2)

    return result


# ============================================================================
# 测试数据 (HC3 风格的 AI/人类 对照文本)
# ============================================================================

SAMPLE_AI_TEXT = (
    "人工智能技术在现代社会中发挥着越来越重要的作用。"
    "随着大数据和计算能力的不断提升，人工智能技术在各个领域都得到了广泛应用。"
    "首先，在医疗领域，人工智能可以辅助医生进行疾病诊断。"
    "其次，在教育领域，人工智能可以为学生提供个性化的学习方案。"
    "最后，在交通领域，人工智能技术正在推动自动驾驶技术的发展。"
    "综上所述，人工智能技术的发展前景十分广阔。"
    "值得注意的是，我们还需要关注人工智能发展过程中的伦理问题。"
    "总而言之，人工智能技术将在未来社会中扮演更加重要的角色。"
)

SAMPLE_HUMAN_TEXT = (
    "今天去超市买菜，碰到邻居张阿姨也在挑水果。"
    "她问我最近怎么瘦了，我说在控制饮食。"
    "她说她女儿也在减肥，天天吃沙拉，看着都心疼。"
    "回家路上想起小时候妈妈也是这么念叨我的。"
    "那时候嫌烦，现在却觉得挺温暖的。"
    "时间过得真快啊。"
)

SAMPLE_LONGFORM_TEXT = (
    "本研究以某制造企业为案例，通过分析其 2020-2025 年的生产数据，发现数字化转型对生产效率有显著影响。"
    "研究采用定量分析方法，收集了包括产能利用率、设备故障率、产品质量合格率等在内的多项指标。"
    "数据来源包括企业 ERP 系统、生产管理台账以及员工访谈记录。"
    "首先对原始数据进行了清洗和标准化处理，然后使用回归模型分析了数字化转型水平与生产效率之间的关系。"
    "研究发现，企业的数字化水平每提升 10%，生产效率平均提高 3.2%。"
    "这一结果在控制了企业规模、行业特征和区域差异后依然稳健。"
    "本研究的结果对于制造业企业推进数字化转型具有一定的参考价值。"
)


# ============================================================================
# 命令行入口
# ============================================================================

def _print_dim(name, value, max_score=10):
    """格式化打印维度分数"""
    bar_len = 20
    ratio = min(value / max_score, 1.0)
    filled = int(bar_len * ratio)
    bar = '█' * filled + '░' * (bar_len - filled)
    print(f"  {name:30s} {bar} {value:.4f}  (max={max_score})")


def _print_result(result, title=""):
    """格式化打印诊断结果"""
    if title:
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}")

    # 8 维特征
    print(f"\n  8 维语言学特征:")
    dims_to_show = [
        ('syntax_similarity', '句法结构相似度', 1.0),
        ('pattern_repetition', '句式重复率', 1.0),
        ('mdd_mean', '平均依存距离', 5.0),
        ('coherence_mean', '段落连贯性均值', 1.0),
        ('coherence_variance', '段落连贯性方差', 0.1),
        ('ttr_global', '词汇多样性 TTR', 1.0),
        ('ttr_variance', 'TTR 方差', 0.1),
        ('lexical_entropy', '词汇香农熵', 8.0),
        ('comma_period_ratio', '逗号句号比', 5.0),
        ('punctuation_variance', '标点多样性', 1.0),
        ('density_variance', '信息密度方差', 0.01),
        ('semantic_jump_std', '语义跳跃标准差', 0.3),
        ('ai_vocab_density', 'AI 词汇密度', 20),
        ('fingerprint_score', '指纹分数', 1.0),
        ('ai_vocab_count', 'AI 词汇计数', 20),
    ]

    for key, label, max_val in dims_to_show:
        if key in result:
            val = result[key]
            _print_dim(label, val, max_val)

    # 维普对齐总分
    if '_vipu_aligned_score' in result:
        print(f"\n  维普对齐 AIGC 风险分: {result['_vipu_aligned_score']:.2f} / 100")


def main():
    """命令行接口"""
    import argparse
    parser = argparse.ArgumentParser(description='语言学特征检测 (8 维维普对齐)')
    parser.add_argument('--text', '-t', type=str, help='输入文本')
    parser.add_argument('--file', '-f', type=str, help='从文件读取文本')
    parser.add_argument('--demo', '-d', action='store_true', help='运行演示 (AI vs 人类)')
    parser.add_argument('--longform', '-l', action='store_true', help='长文本演示')
    parser.add_argument('--full-test', '-a', action='store_true', help='全量测试 (所有内置样本)')

    args = parser.parse_args()

    texts = []
    labels = []

    if args.full_test:
        texts = [SAMPLE_AI_TEXT, SAMPLE_HUMAN_TEXT, SAMPLE_LONGFORM_TEXT]
        labels = ['HC3 AI 风格文本', 'HC3 人类风格文本', '长文本 (学术论文)']
    elif args.demo:
        texts = [SAMPLE_AI_TEXT, SAMPLE_HUMAN_TEXT]
        labels = ['AI 风格文本', '人类风格文本']
    elif args.longform:
        texts = [SAMPLE_LONGFORM_TEXT]
        labels = ['长文本 (学术论文)']
    elif args.file:
        with open(args.file, 'r', encoding='utf-8') as f:
            content = f.read()
        texts = [content]
        labels = [args.file]
    elif args.text:
        texts = [args.text]
        labels = ['输入文本']
    else:
        parser.print_help()
        return

    vocab_dict = _load_vocab_dict()

    for text, label in zip(texts, labels):
        result = diagnose_linguistic_features(text, vocab_dict)
        _print_result(result, label)

        if len(texts) > 1:
            print(f"\n  文本长度: {_count_cn(text)} 中文字符")

    if len(texts) >= 2:
        print(f"\n{'='*60}")
        print("  AI vs 人类 对比分析")
        print(f"{'='*60}")
        results = [diagnose_linguistic_features(t, vocab_dict) for t in texts]
        ai_result = results[0]
        human_result = results[1]

        ai_total = ai_result.get('_vipu_aligned_score', 0)
        human_total = human_result.get('_vipu_aligned_score', 0)
        diff = ai_total - human_total
        print(f"\n  维普总分差 (AI - 人类): {diff:+.2f}")
        print(f"  AI 文本: {ai_total:.2f}")
        print(f"  人类文本: {human_total:.2f}")

        # 各维度差异
        print(f"\n  各维度差异 (AI - 人类):")
        for key in ['syntax_similarity', 'ttr_global', 'coherence_mean',
                     'comma_period_ratio', 'fingerprint_score', 'semantic_jump_std']:
            if key in ai_result and key in human_result:
                d = ai_result[key] - human_result[key]
                arrow = "↑" if d > 0 else ("↓" if d < 0 else "→")
                print(f"    {key:25s}: {d:+.4f} {arrow}")


if __name__ == '__main__':
    main()

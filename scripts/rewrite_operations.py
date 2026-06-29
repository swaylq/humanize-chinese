"""
rewrite_operations.py — 维普对齐的 6 个新改写操作

本模块完全独立于 humanize-chinese-dimension 项目，零项目内依赖。
可单独使用: python rewrite_operations.py --text "输入文本" --op burstiness

设计原则:
  - 纯规则/统计，无 LLM, 无 jieba/numpy/scipy
  - 每个操作独立可测
  - 与原项目解耦，可通过 try/except 降级集成到 humanize_cn.py

历史:
  早期版本在 syntax_pattern_break 和 info_density_rebalance 中使用
  jieba.posseg。消融实验显示 jieba 路径质量不稳定 (改写端 detect_cn
  改善 +15.8) 反而不如纯零依赖路径 (+17.2), 因此 v2 移除了 jieba 依赖。

依赖:
  - random, re (标准库)

使用示例:
  >>> from rewrite_operations import burstiness_engineering
  >>> result = burstiness_engineering("这是测试文本。今天天气不错。", intensity=0.7)
  >>> print(result)
"""

import re
import random
import math
import os
import json


# ============================================================================
# 术语保护层: 语境感知碎片插入的分类词表 (Phase 1)
# ============================================================================
# 从 scripts/weights/fragments_by_relation.json 加载分类碎片词表.
# 学术支撑: PDTB-style Chinese (Zhou & Xue, ACL 2012) + RST Chinese (Peng et al. 2022)
#           + Chinese DM sentiment polarity (Huang et al. 2014) + Lakoff hedge
# 7 类: hedge / comment_neutral / comment_surprise / comment_positive /
#       comment_negative / comment_termination / contrast
# 加载失败时 fallback 到内置默认词表 (与旧 _FRAGMENTS 等价但已分类).

_FRAGMENTS_FALLBACK = {
    'hedge': [
        '未必如此。', '也难讲。', '不一定。', '看情况。', '难说。',
        '未必。', '不好说。', '说不准。',
    ],
    'comment_neutral': [
        '看起来是这样。', '有这个说法。', '也是。', '也正常。',
    ],
    'comment_surprise': [
        '也是奇怪。', '说来也怪。', '怪了。',
    ],
    'comment_positive': [
        '颇有看点。', '势头不错。', '成效不小。', '影响不小。',
        '前景看好。', '空间不小。',
    ],
    'comment_negative': [
        '没什么大不了的。', '算了。', '无所谓了。', '就这样吧。',
    ],
    'comment_termination': [
        '就这样。', '到此为止。', '说完了。',
    ],
    'contrast': [
        '其实不然。', '话又说回来。', '换个角度看。',
    ],
}

_FRAGMENTS_CACHE = None


def _load_fragments_by_relation():
    """加载分类碎片词表, 带缓存. 失败时返回 fallback."""
    global _FRAGMENTS_CACHE
    if _FRAGMENTS_CACHE is not None:
        return _FRAGMENTS_CACHE
    path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'weights', 'fragments_by_relation.json'
    )
    if os.path.isfile(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # 过滤 _meta 等非词表字段
            _FRAGMENTS_CACHE = {
                k: v for k, v in data.items()
                if k != '_meta' and isinstance(v, list)
            }
            return _FRAGMENTS_CACHE
        except Exception:
            pass
    _FRAGMENTS_CACHE = dict(_FRAGMENTS_FALLBACK)
    return _FRAGMENTS_CACHE


# ============================================================================
# 通用工具函数
# ============================================================================

def split_sentences(text):
    """分句: 按句号/感叹号/问号/分号/换行分割"""
    raw = re.split(r'([。！？；\n]+)', text)
    sentences = []
    i = 0
    while i < len(raw):
        s = raw[i].strip()
        if s:
            # 保留标点
            if i + 1 < len(raw) and raw[i+1].strip():
                sentences.append(s + raw[i+1].strip())
                i += 2
            else:
                sentences.append(s)
                i += 1
        else:
            i += 1
    return [s for s in sentences if len(s) >= 2]


def split_paragraphs(text):
    """分段: 按空行分割"""
    return [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]


def _count_cn(s):
    """统计中文字符数"""
    return sum(1 for c in s if '\u4e00' <= c <= '\u9fff')


# ============================================================================
# 操作 1: burstiness_engineering (突发性工程)
# ============================================================================

# ── 旧 _FRAGMENTS 单列表已废弃, 改为分类词表 _load_fragments_by_relation() ──
# 保留 _FRAGMENTS 名字做向后兼容 (扁平化为单列表), 但新代码应用 _load_fragments_by_relation
_FRAGMENTS = [
    '真的。', '但没用。', '就这样。', '未必。', '看情况。',
    '难说。', '不一定。', '谁知道呢。', '不好说。', '其实不然。',
    '未必如此。', '未必有效。', '未必能成。', '没什么大不了的。',
    '也是奇怪。', '也正常。', '无所谓了。', '算了。',
]


# ── 语境感知: 情感/语体/discourse relation 识别 (轻量零依赖) ──

# 情感词典 (简化版, 内嵌; Phase 2 可扩为 sentiment_lexicon.json)
_SENTIMENT_POSITIVE = {
    '爱', '喜欢', '美好', '幸福', '快乐', '开心', '高兴', '欣慰',
    '感动', '温暖', '珍惜', '怀念', '想念', '骄傲', '自豪', '成功',
    '突破', '进展', '成效', '收获', '希望', '期待', '赞美', '优秀',
    '显著', '卓越', '杰出', '辉煌', '美满', '甜蜜', '温馨', '慈祥',
    '鼓励', '支持', '帮助', '进步', '提升', '改善', '优化', '完善',
}
_SENTIMENT_NEGATIVE = {
    '失去', '失败', '挫折', '痛苦', '悲伤', '难过', '伤心', '失望',
    '绝望', '无奈', '遗憾', '后悔', '错误', '缺陷', '不足', '问题',
    '困难', '困境', '危机', '威胁', '风险', '挑战', '障碍', '阻力',
    '下降', '退化', '衰退', '恶化', '削弱', '损害', '破坏', '严重',
}
# 否定词 (前一词极性翻转)
_NEGATORS = {'不', '没', '未', '别', '无', '非', '莫'}

# 语体 marker (学术/法律/医学, 命中 >=2 个判定为 formal)
# 强学术 marker: 命中 1 个即判定 academic (专属性高)
_ACADEMIC_MARKERS_STRONG = {
    'BERT', 'Transformer', 'GPT', '预训练', '微调', '神经网络',
    '深度学习', '机器学习', '自注意力', '数据集', '准确率', '召回率',
    'F1', '显著性', '泛化', '梯度', '表征', '嵌入',
}
# 弱学术 marker: 需 >=2 个才判定 academic (通用技术词)
_ACADEMIC_MARKERS_WEAK = {
    '研究', '本研究', '实验', '论文', '文献', '理论', '假设', '验证',
    '模型', '算法', '相关性',
    '架构', '机制', '建模', '序列', '依赖', '长距离',
    '迭代', '优化', '参数', '特征', '编码', '解码', '注意力',
}
# 强法律 marker: 命中 1 个即判定 legal
_LEGAL_MARKERS_STRONG = {
    '构成要件', '数据隐私', '算法偏见', '个人信息', '知情同意',
    '司法实践', '行为人', '主观故意',
}
# 弱法律 marker: 需 >=2
_LEGAL_MARKERS_WEAK = {
    '法律', '法规', '条款', '合规', '监管', '权利', '义务',
    '认定', '证据', '判决', '裁判', '追诉', '刑事责任',
}
_MEDICAL_MARKERS = {
    'PKM2', '丙酮酸激酶', '凋亡', '糖酵解', '信号通路', '细胞代谢',
    '增殖', '肿瘤', '蛋白', '基因', '分子', '临床', '诊断', '治疗',
    '病理', '生理', '酶', '受体', '抑制', '激活',
}

# 转折词 (用于 discourse relation = contrast 判定)
_CONTRAST_MARKERS = {'但是', '然而', '不过', '可是', '尽管如此', '反而', '反之', '相比之下'}

# 收尾词 (用于 discourse relation = termination 判定)
_TERMINATION_MARKERS = {'总结', '综上', '总的来说', '总而言之', '到此结束', '到此为止',
                        '就此结束', '先到这里', '说完了', '讲完了'}


def _sentiment_of_sentence(sent):
    """判定单句情感极性. 返回 'positive' / 'negative' / 'neutral'.

    算法: 统计 positive/negative 词数, 否定词翻转前一词极性.
    """
    if not sent:
        return 'neutral'
    pos = 0
    neg = 0
    prev_negated = False
    for ch in sent:
        # 简单按字符扫描 (中文单字情感词 + 2字词前缀匹配)
        if ch in _NEGATORS:
            prev_negated = True
            continue
        if ch in _SENTIMENT_POSITIVE:
            if prev_negated:
                neg += 1
            else:
                pos += 1
            prev_negated = False
        elif ch in _SENTIMENT_NEGATIVE:
            if prev_negated:
                pos += 1
            else:
                neg += 1
            prev_negated = False
        else:
            prev_negated = False
    # 2-4 字情感词扫描
    for w in _SENTIMENT_POSITIVE:
        if len(w) >= 2 and w in sent:
            pos += 1
    for w in _SENTIMENT_NEGATIVE:
        if len(w) >= 2 and w in sent:
            neg += 1
    if pos > neg + 1:
        return 'positive'
    if neg > pos + 1:
        return 'negative'
    return 'neutral'


def _register_of_text(text):
    """判定文本语体. 返回 'academic' / 'legal' / 'medical' / 'general'.

    算法:
      - 强学术 marker 命中 >=1 → academic
      - 弱学术 marker 命中 >=2 → academic
      - legal/medical marker 命中 >=2 → 对应语体
      - 否则 → general
    """
    if not text:
        return 'general'
    # 强学术词 1 个就够
    if any(w in text for w in _ACADEMIC_MARKERS_STRONG):
        return 'academic'
    # 强法律词 1 个就够
    if any(w in text for w in _LEGAL_MARKERS_STRONG):
        return 'legal'
    # 弱学术词需 >=2
    acad_weak = sum(1 for w in _ACADEMIC_MARKERS_WEAK if w in text)
    legal_weak = sum(1 for w in _LEGAL_MARKERS_WEAK if w in text)
    med = sum(1 for w in _MEDICAL_MARKERS if w in text)
    if med >= 2:
        return 'medical'
    if legal_weak >= 2:
        return 'legal'
    if acad_weak >= 2:
        return 'academic'
    return 'general'


def _discourse_relation_of(prev_sent, curr_sent):
    """推断相邻句 discourse relation.

    返回 'contrast' / 'elaboration' / 'termination' / 'unknown'.

    算法:
      1. curr 句首含转折词 → contrast
      2. prev 句含转折词 (如"但是他并不认同") → contrast
      3. curr 句含收尾词 (总结/综上/到此结束) → termination
      4. 共享字符多 → elaboration
      5. 否则 → unknown
    """
    if not curr_sent:
        return 'unknown'
    curr_head = curr_sent.strip()[:6]
    for marker in _CONTRAST_MARKERS:
        if marker in curr_head:
            return 'contrast'
    # prev 句含转折词 → contrast (如"大家都认为稳妥, 但是他并不认同" → 下句是转折延续)
    if prev_sent:
        for marker in _CONTRAST_MARKERS:
            if marker in prev_sent:
                return 'contrast'
    # curr 句含收尾词 → termination
    for marker in _TERMINATION_MARKERS:
        if marker in curr_sent:
            return 'termination'
    # 实体共现 (简化版 Centering)
    if prev_sent:
        prev_chars = set(c for c in prev_sent if '\u4e00' <= c <= '\u9fff')
        curr_chars = set(c for c in curr_sent if '\u4e00' <= c <= '\u9fff')
        overlap = prev_chars & curr_chars
        if len(overlap) >= 2:
            return 'elaboration'
    return 'unknown'


def _pick_fragment(relation, sentiment, register, rng, allow_comment=True):
    """根据 discourse relation + sentiment + register 选碎片.

    返回带句号的碎片字符串.

    选择逻辑:
      1. formal register (academic/legal/medical) + relation != contrast
         → 只允许 hedge (学术场景最安全)
      2. relation == contrast → contrast 类
      3. sentiment == positive → comment_positive
      4. sentiment == negative → comment_negative
      5. sentiment == neutral → comment_neutral + hedge 混合
      6. fallback → hedge
    """
    fragments = _load_fragments_by_relation()

    # formal register 只允许 hedge (除非 contrast 关系)
    if register in ('academic', 'legal', 'medical') and relation != 'contrast':
        pool = fragments.get('hedge', _FRAGMENTS_FALLBACK['hedge'])
        return rng.choice(pool) if pool else ''

    if relation == 'contrast':
        pool = fragments.get('contrast', _FRAGMENTS_FALLBACK['contrast'])
        return rng.choice(pool) if pool else ''

    if relation == 'termination':
        pool = fragments.get('comment_termination', _FRAGMENTS_FALLBACK['comment_termination'])
        return rng.choice(pool) if pool else ''

    if not allow_comment:
        pool = fragments.get('hedge', _FRAGMENTS_FALLBACK['hedge'])
        return rng.choice(pool) if pool else ''

    if sentiment == 'positive':
        pool = fragments.get('comment_positive', _FRAGMENTS_FALLBACK['comment_positive'])
    elif sentiment == 'negative':
        pool = fragments.get('comment_negative', _FRAGMENTS_FALLBACK['comment_negative'])
    else:
        # neutral: comment_neutral + hedge 混合
        pool = (fragments.get('comment_neutral', _FRAGMENTS_FALLBACK['comment_neutral'])
                + fragments.get('hedge', _FRAGMENTS_FALLBACK['hedge']))
    return rng.choice(pool) if pool else ''


def _find_natural_split(sentence):
    """寻找自然拆分点 (逗号、顿号)"""
    for i, c in enumerate(sentence):
        if c in '，、':
            if 5 <= i <= 18:
                return i + 1
    return None


def _merge_sentences(s1, s2, rng=None):
    """合并两个句子"""
    if rng is None:
        rng = random
    s1 = s1.rstrip('。！？；')
    s2 = s2.rstrip('。！？；')
    connectors = ['，而且', '，同时', '，另外', '，不过', '，然而']
    return s1 + rng.choice(connectors) + s2


def burstiness_engineering(text, intensity=0.7, seed=None):
    """
    突发性工程: 强制短长句交替，打破 AI 文本句长均匀的特征。

    理论:
        Carnegie Mellon 2025 研究: 仅强制句长变化就能降低 GPTZero 检测 31%
        AI 文本句长多在 15-25 字，人类句长 4-40 字波动

    参数:
        text: 输入文本
        intensity: 0-1, 控制变化幅度
        seed: 随机种子

    算法:
        1. 分句
        2. 对连续中等长度句 (15-25 字) 进行:
           a. 以 intensity 概率拆分为短句+碎片
           b. 以 intensity/2 概率合并相邻短句
        3. 确保相邻句长差异

    返回:
        str: 改写后的文本
    """
    rng = random.Random(seed)
    sentences = split_sentences(text)

    if len(sentences) < 2:
        return text

    result = []
    i = 0
    while i < len(sentences):
        sent = sentences[i]
        sent_len = len(sent)

        if 15 <= sent_len <= 25 and rng.random() < intensity:
            # 中等长度句: 拆分
            if rng.random() < 0.5:
                split_pos = _find_natural_split(sent)
                if split_pos:
                    short_part = sent[:split_pos].strip()
                    rest_part = sent[split_pos:].strip()
                    # Phase 1: 拆点后不再插碎片 (碎片由 fragment_injection 语境感知统一处理)
                    # short_part 末尾标点规范化
                    if short_part and short_part[-1] in '，、':
                        short_part = short_part[:-1] + '。'
                    elif short_part and short_part[-1] not in '。！？；':
                        short_part = short_part + '。'
                    result.append(short_part)
                    # rest_part 若已有标点则保留，否则补句号
                    if rest_part and rest_part[-1] in '。！？；':
                        result.append(rest_part)
                    else:
                        result.append(rest_part + '。')
                else:
                    # 原句已有标点则直接用，否则补句号
                    if sent and sent[-1] in '。！？；':
                        result.append(sent)
                    else:
                        result.append(sent + '。')
            else:
                # 与下一句合并
                if i + 1 < len(sentences):
                    merged = _merge_sentences(sent, sentences[i + 1], rng=rng)
                    result.append(merged + '。')
                    i += 1
                else:
                    if sent and sent[-1] in '。！？；':
                        result.append(sent)
                    else:
                        result.append(sent + '。')
        else:
            if sent and sent[-1] in '。！？；':
                result.append(sent)
            else:
                result.append(sent + '。')

        i += 1

    return ''.join(result)


# ============================================================================
# 操作 2: fragment_injection (碎片注入)
# ============================================================================

def fragment_injection(text, intensity=0.3, seed=None):
    """
    语境感知碎片注入: 在长句后注入 2-6 字的碎片句.

    理论:
        人类写作特征: 长句后跟碎片句 ("但没用。" "真的。")
        AI 文本几乎没有碎片句
        Centering Theory (Grosz 1995): 相邻句中心转移影响连贯性
        PDTB-style Chinese (Zhou & Xue 2012): discourse relation 4 大类
        Huang 2014: DM 含 sentiment polarity

    Phase 1 改动 (vs 旧版):
      1. 句末标点约束: 只在 。！？ 后插, 不在 ，、 后插 (修复"细胞代谢、。真的。增殖")
      2. 全局上限: 单篇最多 3 个碎片 (旧版无上限)
      3. 间距控制: 距上一个碎片 >= 3 句
      4. 语境感知: 根据 discourse relation + sentiment + register 选碎片类
         - academic/legal/medical 语体 → 只允许 hedge
         - contrast 关系 → contrast 类
         - positive 情感 → comment_positive
         - negative 情感 → comment_negative
         - neutral → comment_neutral + hedge 混合
      5. 不在末句后插 (避免孤立碎片)

    参数:
        text: 输入文本
        intensity: 0-1, 注入概率
        seed: 随机种子

    返回:
        str: 改写后的文本
    """
    rng = random.Random(seed)
    sentences = split_sentences(text)

    if len(sentences) < 1:
        return text

    # 语体判定 (全文一次)
    text_register = _register_of_text(text)
    formal_registers = ('academic', 'legal', 'medical')
    allow_comment = text_register not in formal_registers

    MAX_FRAGMENTS = 3
    MIN_GAP = 3  # 距上一个碎片至少 3 句

    result = []
    frag_count = 0
    last_frag_idx = -MIN_GAP - 1  # 允许第一次插入

    for i, sent in enumerate(sentences):
        # 保留句末标点
        if sent and sent[-1] in '。！？；':
            result.append(sent)
        else:
            result.append(sent + '。')

        # 插入判定
        should_try = (
            len(sent) > 25
            and sent[-1] in '。！？'  # 必须句末标点 (修复 C3)
            and frag_count < MAX_FRAGMENTS
            and i - last_frag_idx >= MIN_GAP
            and i < len(sentences) - 1  # 不在末句后插
        )

        if should_try and rng.random() < intensity:
            prev_sent = sentences[i - 1] if i > 0 else ''
            relation = _discourse_relation_of(prev_sent, sent)
            sentiment = _sentiment_of_sentence(sent)
            fragment = _pick_fragment(
                relation, sentiment, text_register, rng,
                allow_comment=allow_comment
            )
            if fragment:
                result.append(fragment)
                frag_count += 1
                last_frag_idx = i

    return ''.join(result)


# ============================================================================
# 操作 3: syntax_pattern_break (句式模式打破)
# ============================================================================

def _detect_pattern(sent):
    """检测句式 (纯字符串规则, 无 jieba):
        - 'passive': 含"被"
        - 'ba_construction': 含"把"
        - 'other': 其他
    """
    if '被' in sent:
        return 'passive'
    if '把' in sent:
        return 'ba_construction'
    return 'other'


def _passive_to_active(sent):
    """被动转主动 (字符串规则): "X被YV" -> "YVX"
    若无法识别, 返回原句。
    """
    if '被' not in sent:
        return sent
    parts = sent.split('被', 1)
    if len(parts) != 2:
        return sent
    patient = parts[0].strip()
    rest = parts[1].strip()
    # rest 形如 "YV" 或 "YV了/着..."
    # 简单地把 "Y V" 当作 agent + verb, 把 patient 移到句末
    # 去掉句末标点
    end_punct = ''
    if rest and rest[-1] in '。！？；':
        end_punct = rest[-1]
        rest = rest[:-1]
    if patient and rest:
        return f"{rest}{patient}{end_punct}"
    return sent


def _ba_to_normal(sent):
    """把字句转普通句: "S把OV" -> "SVO"
    若无法识别, 返回原句。
    """
    if '把' not in sent:
        return sent
    parts = sent.split('把', 1)
    if len(parts) != 2:
        return sent
    subject = parts[0].strip()
    rest = parts[1].strip()
    end_punct = ''
    if rest and rest[-1] in '。！？；':
        end_punct = rest[-1]
        rest = rest[:-1]
    # rest 形如 "OV", 简单重组为 "S V O" (rest 整体作为 V+O)
    if subject and rest:
        return f"{subject}{rest}{end_punct}"
    return sent


def syntax_pattern_break(text, intensity=0.5, seed=None):
    """
    句式模式打破: 变换被动/把字句 (纯字符串规则, 无 jieba)。

    理论:
        AI 偏爱 "主语+谓语+宾语+补充说明" 结构
        人类会主动被动交替、倒装、省略主语

    参数:
        text: 输入文本
        intensity: 0-1, 变换概率
        seed: 随机种子

    算法:
        1. 分句
        2. 识别含"被""把"的句子
        3. 以 intensity 概率做反向变换

    返回:
        str: 改写后的文本
    """
    rng = random.Random(seed)
    sentences = split_sentences(text)

    if len(sentences) < 2:
        return text

    result = []
    last_pattern = None

    for sent in sentences:
        pattern = _detect_pattern(sent)

        # 连续相同句式且命中概率: 做反向变换
        if pattern == last_pattern and rng.random() < intensity:
            if pattern == 'passive':
                transformed = _passive_to_active(sent)
                result.append(transformed if transformed != sent else sent)
            elif pattern == 'ba_construction':
                transformed = _ba_to_normal(sent)
                result.append(transformed if transformed != sent else sent)
            else:
                result.append(sent)
        else:
            result.append(sent)

        last_pattern = pattern

    return ''.join(result)


# ============================================================================
# 操作 4: info_density_rebalance (信息密度再平衡)
# ============================================================================

def info_density_rebalance(text, intensity=0.5, seed=None):
    """
    信息密度再平衡: 打破 AI 文本每段密度均匀的特征。

    理论:
        AI: 每段信息密度均匀
        人类: 有的段落堆论点，有的段落只展开细节

    参数:
        text: 输入文本
        intensity: 0-1, 操作强度
        seed: 随机种子

    算法:
        1. 分段
        2. 对密度相近的连续段落合并
        3. 随机拆分长段落

    返回:
        str: 改写后的文本
    """
    rng = random.Random(seed)
    paragraphs = [p.strip() for p in text.split('\n') if p.strip()]

    if len(paragraphs) < 3:
        return text

    # 计算每段信息密度 (中文字符占比, 纯零依赖)
    # 注: 检测端 compute_info_density_variance 用 jieba 的动名词密度,
    # 这里用字符密度作为简化代理 (消融实验显示两者效果接近)
    densities = []
    for p in paragraphs:
        cn = _count_cn(p)
        density = cn / max(len(p), 1)
        densities.append(density)

    result = []
    i = 0
    while i < len(paragraphs):
        if i + 1 < len(paragraphs):
            diff = abs(densities[i] - densities[i + 1])
            # 密度相近 (差值 < 0.1) 时合并
            if diff < 0.1 and rng.random() < intensity:
                # 密度相近: 合并
                result.append(paragraphs[i] + '。' + paragraphs[i + 1])
                i += 2
                continue

        # 随机拆分长段落
        if _count_cn(paragraphs[i]) > 120 and rng.random() < intensity * 0.5:
            split_pos = paragraphs[i].find('。', 50)
            if 50 < split_pos < len(paragraphs[i]) - 20:
                result.append(paragraphs[i][:split_pos + 1])
                result.append(paragraphs[i][split_pos + 1:])
                i += 1
                continue

        result.append(paragraphs[i])
        i += 1

    return '\n'.join(result)


# ============================================================================
# 操作 5: punctuation_humanize (标点人性化)
# ============================================================================

_QUESTION_PATTERNS = ['是不是', '对不对', '能不能', '为什么', '怎么', '难道', '是否']


def punctuation_humanize(text, intensity=0.3, seed=None):
    """
    标点人性化: 打破 AI 标点使用模式。

    理论:
        AI: 逗号:句号 = 2:1 到 3:1, 分号少, 无感叹问号
        人类: 标点不规律, 有感叹问号省略号

    参数:
        text: 输入文本
        intensity: 0-1, 操作强度
        seed: 随机种子

    算法:
        1. 降低逗号句号比: 部分逗号改句号
        2. 问句末尾加问号
        3. 适当位置加省略号

    返回:
        str: 改写后的文本
    """
    rng = random.Random(seed)
    result = text

    # 1. 降低逗号句号比
    comma_count = result.count('，')
    period_count = result.count('。')
    if period_count > 0 and comma_count / period_count > 2.0:
        commas = [i for i, c in enumerate(result) if c == '，']
        n_change = int(len(commas) * intensity * 0.3)
        if n_change > 0:
            for idx in rng.sample(commas, min(n_change, len(commas))):
                # 只改长句中的逗号
                next_period = result.find('。', idx)
                if next_period > 0 and next_period - idx > 15:
                    result = result[:idx] + '。' + result[idx + 1:]

    # 2. 在问句末尾加问号
    for pattern in _QUESTION_PATTERNS:
        pos = 0
        while True:
            pos = result.find(pattern, pos)
            if pos == -1:
                break
            end = result.find('。', pos)
            if end > 0 and rng.random() < intensity:
                result = result[:end] + '？' + result[end + 1:]
            pos = end + 1 if end > 0 else len(result)

    # Phase 1: 砍掉省略号添加逻辑 (原第 3 步)
    # 旧版在末段长度 > 50 时随机加省略号, 但触发条件只看长度+随机,
    # 不看末句语义是否属于"未尽/沉思/留白". 实测产生"势头不错……"
    # "确保了实验的可靠性……" 等语义错位 (省略号语用功能是未尽/沉思,
    # 不是降低句号密度的工具). 直接砍掉, 原文有省略号则保留.

    return result


# ============================================================================
# 操作 6: ai_vocab_scrub (AI 词汇指纹清除)
# ============================================================================

_VOCAB_REPLACEMENTS = {
    '首先': ['先说', '一开始', '头一个'],
    '其次': ['再说', '接着', '然后'],
    '再次': ['还有', '另外'],
    '最后': ['最后呢', '到头来', '归根结底'],
    '综上所述': ['所以', '总的看下来', '说到底'],
    '由此可见': ['看得出来', '这说明', '显然'],
    '值得注意': ['要注意', '得留心', '有个点要注意'],
    '总而言之': ['总之', '一句话', '说白了'],
    '众所周知': ['大家都知道', '谁都清楚', '明摆着'],
    '不可或缺': ['少不得', '缺不了', '不能没有'],
    '至关重要': ['要紧', '关键', '最要紧'],
    '深入探讨': ['细聊', '好好说说', '掰开揉碎'],
    '许多': ['不少', '一大堆', '好多'],
    '大量': ['一大堆', '好多', '不少'],
    '显著': ['明显', '挺', '相当'],
    '进行': ['做', '搞', '弄', '来'],
    '实施': ['干', '做', '搞'],
    '开展': ['搞', '做', '弄'],
    '推进': ['往前推', '搞下去', '做下去'],
    '构建': ['搭', '建', '搞'],
    '打造': ['做', '搞', '弄'],
    '提升': ['提高', '往上拉', '改善'],
    '优化': ['改进', '调好', '弄好'],
    '强化': ['加强', '加大'],
    '完善': ['补全', '弄好', '改好'],
    '推动': ['带动', '推一把'],
    '促进': ['帮着', '带起来'],
    '赋能': ['帮助', '支持'],
    '助力': ['帮忙', '支持'],
    '不容忽视': ['不能忽视', '得注意', '要留心'],
    '不可否认': ['说实话', '得承认'],
    '毫无疑问': ['不用说', '肯定'],
    '显而易见': ['很明显', '明摆着'],
    '从某种意义上说': ['某种程度上', '可以说'],
    '在一定程度上': ['多少有点', '算是'],
    '发挥着': ['起到', '有'],
    '扮演着': ['是', '成为'],
}


def ai_vocab_scrub(text, intensity=0.7, seed=None, replacements=None,
                   protected_set=None):
    """
    AI 词汇指纹清除: 替换 AI 高频词为口语化表达。

    理论:
        AI 过量使用特定词汇 (频率比人类高 3-6 倍)
        替换为口语化表达可降低检测

    参数:
        text: 输入文本
        intensity: 0-1, 替换概率
        seed: 随机种子
        replacements: 替换映射表 (可选, 默认使用内置表)
        protected_set: 受保护术语集合 (可选, 来自 _humanize_protect).
            位于这些术语内部的 ai_word 不会被替换, 避免 数据隐私→数额隐私
            类误替换. None 时表示不启用保护.

    返回:
        str: 改写后的文本
    """
    import re as _re
    rng = random.Random(seed)
    if replacements is None:
        replacements = _VOCAB_REPLACEMENTS

    # 预计算受保护位置集 (一次性, 避免每次替换重算)
    blocked_positions = set()
    if protected_set:
        for t in protected_set:
            if not t or len(t) < 2:
                continue
            for m in _re.finditer(_re.escape(t), text):
                for p in range(m.start(), m.end()):
                    blocked_positions.add(p)

    result = text
    for ai_word, alternatives in replacements.items():
        # 从后向前替换, 避免位置偏移
        positions = [m.start() for m in _re.finditer(_re.escape(ai_word), result)]
        if not positions:
            continue
        for pos in reversed(positions):
            # 术语保护: 跳过位于受保护术语内部的 occurrence
            if pos in blocked_positions:
                continue
            if rng.random() < intensity:
                replacement = rng.choice(alternatives)
                result = result[:pos] + replacement + result[pos + len(ai_word):]
                # 更新 blocked_positions (替换后位置偏移)
                delta = len(replacement) - len(ai_word)
                if delta != 0:
                    blocked_positions = {p if p < pos else p + delta
                                         for p in blocked_positions}

    return result


# ============================================================================
# 统一改写接口
# ============================================================================

# 操作注册表
AVAILABLE_OPS = {
    'burstiness': {
        'func': burstiness_engineering,
        'params': {'intensity': (0.0, 1.0)},
        'description': '突发性工程 — 强制短长句交替',
    },
    'fragment': {
        'func': fragment_injection,
        'params': {'intensity': (0.0, 0.6)},
        'description': '碎片注入 — 长句后追加碎片句',
    },
    'syntax': {
        'func': syntax_pattern_break,
        'params': {'intensity': (0.0, 0.8)},
        'description': '句式模式打破 — 变换主被动/倒装',
    },
    'density': {
        'func': info_density_rebalance,
        'params': {'intensity': (0.0, 0.8)},
        'description': '信息密度再平衡 — 段落合并/拆分',
    },
    'punct': {
        'func': punctuation_humanize,
        'params': {'intensity': (0.0, 0.5)},
        'description': '标点人性化 — 问号/省略号/改逗号',
    },
    'vocab': {
        'func': ai_vocab_scrub,
        'params': {'intensity': (0.0, 1.0)},
        'description': 'AI 词汇指纹清除 — 替换高频 AI 词汇',
    },
}


def apply_pipeline(text, ops_spec, seed=None):
    """
    按顺序执行多个改写操作。

    参数:
        text: 输入文本
        ops_spec: 操作规范列表 [(op_name, intensity), ...]
        seed: 随机种子

    示例:
        >>> apply_pipeline("测试文本。", [('burstiness', 0.7), ('vocab', 0.5)])
    """
    rng = random.Random(seed)
    for op_name, intensity in ops_spec:
        if op_name in AVAILABLE_OPS:
            op_func = AVAILABLE_OPS[op_name]['func']
            text = op_func(text, intensity=intensity, seed=rng.randint(0, 2 ** 32))
    return text


# ============================================================================
# CLI 命令行入口
# ============================================================================

def main():
    """命令行入口"""
    import argparse
    parser = argparse.ArgumentParser(description='rewrite_operations — 6 个维普对齐改写操作')
    parser.add_argument('--text', '-t', type=str, help='输入文本')
    parser.add_argument('--file', '-f', type=str, help='从文件读取文本')
    parser.add_argument('--op', '-o', type=str, default='burstiness',
                        choices=list(AVAILABLE_OPS.keys()) + ['pipeline'],
                        help='改写操作')
    parser.add_argument('--intensity', '-i', type=float, default=0.5,
                        help='操作强度 0-1')
    parser.add_argument('--seed', type=int, default=None, help='随机种子')
    parser.add_argument('--list-ops', '-l', action='store_true', help='列出可用操作')
    parser.add_argument('--full-demo', '-d', action='store_true', help='运行完整演示')

    args = parser.parse_args()

    if args.list_ops:
        print("可用改写操作:")
        for name, info in AVAILABLE_OPS.items():
            print(f"  {name:10s} {info['description']}")
            param_str = ', '.join(f"{k}={v}" for k, v in info['params'].items())
            print(f"            params: {param_str}")
        return

    if args.full_demo:
        texts = [
            ("AI 样本文本",
             "首先，人工智能技术在现代社会中发挥着越来越重要的作用。其次，随着大数据技术的发展，"
             "人工智能在医疗、教育、交通等领域都得到了广泛应用。最后，综上所述，人工智能的发展前景十分广阔。"
             "值得注意的是，我们还需要关注人工智能发展过程中的伦理问题。"),
            ("人类样本文本",
             "今天去超市买菜，碰到邻居张阿姨也在挑水果。她问我最近怎么瘦了，我说在控制饮食。"
             "她说她女儿也在减肥，天天吃沙拉，看着都心疼。回家路上想起了小时候。"),
        ]
        print(f"\n{'='*70}")
        print("  rewrite_operations 完整演示")
        print(f"{'='*70}")
        for label, text in texts:
            print(f"\n--- {label} (原始, {_count_cn(text)} 字) ---")
            print(f"  {text[:120]}...")
            for op_name, info in AVAILABLE_OPS.items():
                try:
                    op_func = info['func']
                    result = op_func(text, intensity=0.6, seed=42)
                    changed = result != text
                    print(f"    [{op_name:10s}] {'✓ 有变化' if changed else '— 无变化'}")
                except Exception as e:
                    print(f"    [{op_name:10s}] ✗ 错误: {e}")
        print(f"\n{'='*70}")
        print("  演示完成")
        print(f"{'='*70}")
        return

    # 获取输入文本
    if args.file:
        with open(args.file, 'r', encoding='utf-8') as f:
            text = f.read()
    elif args.text:
        text = args.text
    else:
        # 默认演示文本
        text = ("首先，人工智能技术在现代社会中发挥着越来越重要的作用。"
                "其次，随着大数据和计算能力的不断提升，人工智能技术在各个领域都得到了广泛应用。"
                "最后，综上所述，人工智能技术的发展前景十分广阔。")
        print(f"输入文本: {text}\n")

    # 执行操作
    if args.op == 'pipeline':
        ops_to_run = [(name, args.intensity) for name in AVAILABLE_OPS]
        result = apply_pipeline(text, ops_to_run, seed=args.seed)
        print(f"=== 全管线改写结果 ===")
    else:
        op_func = AVAILABLE_OPS[args.op]['func']
        result = op_func(text, intensity=args.intensity, seed=args.seed)
        print(f"=== {args.op} 改写结果 ===")

    print(f"原始 ({_count_cn(text)} 字): {text[:200]}")
    print(f"改写 ({_count_cn(result)} 字): {result[:200]}")
    print(f"{'='*50}")
    print(f"变化: {'✓ 有变化' if result != text else '— 无变化'}")
    print(f"{'='*50}")


if __name__ == '__main__':
    main()

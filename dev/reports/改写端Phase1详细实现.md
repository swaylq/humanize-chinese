# 改写端 Phase 1 详细实现计划

> **基于**: [dev/reports/改写端优化建议.md](file:///d:/working/0001/humanize-chinese-dimension/dev/reports/改写端优化建议.md) + [dev/reports/改写端未来计划.md](file:///d:/working/0001/humanize-chinese-dimension/dev/reports/改写端未来计划.md)
> **日期**: 2026-06-26
> **范围**: Phase 1 四个任务（P1-1 ~ P1-4）+ 语境检查框架 + 语料扩充总体方案
> **约束**: 零外部依赖（仅 jieba）；新增依赖必须是可内嵌的轻量词典 JSON

---

## 一、当前不足的细致分析

### 1.1 `_FRAGMENTS` 盲插的完整失败链

**当前代码** ([rewrite_operations.py:69-74](file:///d:/working/0001/humanize-chinese-dimension/scripts/rewrite_operations.py))：

```python
_FRAGMENTS = [
    "真的。", "但没用。", "就这样。", "未必。", "看情况。",
    "难说。", "不一定。", "谁知道呢。", "不好说。", "其实不然。",
    "未必如此。", "未必有效。", "未必能成。", "没什么大不了的。",
    "也是奇怪。", "也正常。", "无所谓了。", "算了。",
]
```

**失败链分析**：

| 层次 | 问题 | 代码位置 | 后果 |
|------|------|---------|------|
| 词表设计 | 18 条碎片混合 4 类语用功能：hedging（未必）/ 评论（也是奇怪）/ 终结（就这样）/ 消极（算了） | 第 69-74 行 | `rng.choice` 等概率选，10% 概率选出语义冲突的碎片 |
| 插入位置 | `burstiness_engineering` 在 `_find_natural_split` 拆点插碎片，拆点常在 `，`/`、` 后 | 第 134-141 行 | "细胞代谢、。真的。增殖" — 碎片插入并列项中间，断词 |
| 触发条件 | `fragment_injection` 只看 `len(sent) > 25`，不看句末标点 | 第 208 行 | 碎片可能插在逗号后的子句后，破坏句法 |
| 频率控制 | 仅"避免连续注入"（`len(result[-2]) > 5`），无全局上限 | 第 210 行 | 长文本可能堆积 5+ 个碎片，读起来像机器人 |
| 语境感知 | 完全无：不看前句情感、不看语体、不看 discourse relation | 全函数 | 怀念爷爷段落后跟"没什么大不了的"，温情被轻化 |

**真实失败 case 复盘**（[semantic_check_articles.md](file:///d:/working/0001/humanize-chinese-dimension/dev/reports/semantic_check_articles.md) 案例 3）：

```
原文: "在这个世界上，每个人都有自己的邻居"
改写: "在这个世界上。谁知道呢。每个人都有自己的邻居"
                    ^^^^^^^^^^^^
失败链:
1. split_sentences 把"在这个世界上，每个人都有自己的邻居"按逗号拆成 2 句
2. burstiness_engineering 见第 1 句"在这个世界上"长度 < 15，跳过拆分
3. fragment_injection 见第 1 句 len=6 < 25，不插 — 但第 2 句 > 25，插碎片
4. rng.choice(_FRAGMENTS) 选到"谁知道呢"
5. 没有情感检查，"谁知道呢"的"无所谓/不可知"语义与温情开头冲突
```

**根因总结**：当前实现是**纯统计句长分布**的改写，把"短句注入"等同于"碎片注入"，忽略了碎片的**语用功能**必须与上下文一致。

### 1.2 省略号滥用的完整失败链

**当前代码** ([rewrite_operations.py:451-458](file:///d:/working/0001/humanize-chinese-dimension/scripts/rewrite_operations.py))：

```python
# 3. 在适当位置加省略号
if result.count('……') == 0 and rng.random() < intensity * 0.3:
    paras = result.split('\n')
    if paras:
        last_para = paras[-1].rstrip('。')
        if len(last_para) > 50:
            paras[-1] = last_para + '……'
            result = '\n'.join(paras)
```

**失败链分析**：

| 层次 | 问题 | 后果 |
|------|------|------|
| 触发条件 | 仅 `count('……') == 0 + rng < intensity*0.3 + len > 50` | 末段长度 > 50 就可能加，不论末句语义 |
| 位置选择 | 永远加在 `paras[-1]`（末段） | 末段常常是结论，结论加省略号 = 语义延宕错位 |
| 语义检查 | 无 | "确保了实验的可靠性……" — "确保"是闭环动词，加省略号变成"未确保" |
| 标点剥离 | `rstrip('。')` 只剥句号，不剥 `！？` | 末句若是"太好了！"会变成"太好了！……"双重标点 |
| 总量控制 | `== 0` 只防重复，不限总量 | 实际上只允许 1 个，但没明确表达，后续若多次调用会叠加 |

**真实失败 case**（PR dimension_upgrade.md AI 三段式）：

```
原文末句: "只有这样，我们才能确保人工智能技术真正造福人类社会。"
改写末句: "只有这样，我们才能确保人工智能技术真正造福人类社会。势头不错……"
                                                                              ^^^
失败链:
1. punctuation_humanize 在 burstiness/fragment 之后运行
2. 末段已经被前面操作加了"势头不错。"，长度 > 50
3. rng.random() < 0.4*0.3 = 0.12 命中
4. rstrip('。') 剥掉"势头不错。"的句号
5. 加"……" → "势头不错……"
6. "势头不错"是评论性收尾，加省略号变成"势头未完"，语义错位
```

**根因总结**：省略号的语用功能是**未尽/沉思/留白**，当前实现把它当作"降低句号密度的工具"，完全错配。

### 1.3 同义词替换误伤的完整失败链

**当前代码** ([rewrite_operations.py:508-543](file:///d:/working/0001/humanize-chinese-dimension/scripts/rewrite_operations.py))：

```python
def ai_vocab_scrub(text, intensity=0.7, seed=None, replacements=None):
    rng = random.Random(seed)
    if replacements is None:
        replacements = _VOCAB_REPLACEMENTS
    result = text
    for ai_word, alternatives in replacements.items():
        count = result.count(ai_word)
        if count == 0:
            continue
        for _ in range(count):
            if ai_word not in result:
                break
            if rng.random() < intensity:
                replacement = rng.choice(alternatives)  # 盲选
                result = result.replace(ai_word, replacement, 1)
            else:
                break
    return result
```

**失败链分析**：

| 层次 | 问题 | 后果 |
|------|------|------|
| 候选词表 | `_VOCAB_REPLACEMENTS["数据"] = ["数额", "多寡", ..."]` 混合多义项 | "数据隐私"里"数据"是 data，"数额"是 quantity，义项错位 |
| 选择策略 | `rng.choice(alternatives)` 等概率盲选 | 1/3 概率选到"数额"，破坏"数据隐私"术语 |
| 上下文检查 | 完全无 | 替换"数据"时不看后接词是"隐私"还是"量" |
| 保护机制 | 无术语白名单 | "PKM2""数据隐私""算法偏见"都可能被替换 |
| 二次替换保护 | 无 | "数据"→"数额"后，下一轮若"数额"在词表里会再被替换 |

**真实失败 case**（PR dimension_upgrade.md baseline 改写）：

```
原文: "数据隐私和安全问题日益凸显"
baseline 改写: "数额隐私和安全问题逐渐突出"
                       ^^^^
失败链:
1. ai_vocab_scrub 遍历 _VOCAB_REPLACEMENTS
2. 命中"数据" → alternatives = ["数额", "多寡", ...]
3. rng.choice 等概率选到"数额"
4. result.replace("数据", "数额", 1) → "数额隐私"
5. 没有白名单保护"数据隐私"术语
6. 没有上下文检查"数据"后接"隐私"应保持 data 义项
```

**根因总结**：当前实现是**纯词表替换**，把"AI 词汇指纹清除"等同于"高频词盲替换"，忽略了多义词的义项必须与上下文一致。

### 1.4 Adaptive 模式全开的完整失败链

**当前代码** ([humanize_cn.py:3830-3892](file:///d:/working/0001/humanize-chinese-dimension/scripts/humanize_cn.py))：

```python
if _HAS_REWRITE_OPS and adaptive:
    _ro_defaults = {
        'burstiness_engineering': 0.5,
        'fragment_injection': 0.3,
        'syntax_pattern_break': 0.4,
        'info_density_rebalance': 0.3,
        'punctuation_humanize': 0.4,
        'ai_vocab_scrub': 0.6,
    }
    _ro_params = {}
    if route and 'ops' in route:
        for _op_name in _ro_defaults:
            _op_cfg = route['ops'].get(_op_name, {})
            _route_val = _op_cfg.get('intensity', 0.0)
            # 取 route 值和默认值的较大者，确保至少有默认强度
            _ro_params[_op_name] = max(_route_val, _ro_defaults[_op_name])
    else:
        _ro_params = dict(_ro_defaults)
```

**失败链分析**：

| 层次 | 问题 | 后果 |
|------|------|------|
| 强制下限 | `max(_route_val, _ro_defaults)` 强制 ≥0.3 | clean text 也被全操作处理，过度改写 |
| 无并发上限 | 6 个操作全开，无最大并发数 | 操作间叠加效应不可控（碎片+省略号+拆句同时发生） |
| 无长度分流 | 短文本（< 200 字）走与长文本相同的管线 | 短文本被拆得更碎，段落丢失 |
| 无语义预算 | 不估计每操作的语义代价 | 6 操作叠加可能破坏 30%+ 语义，无熔断 |
| 顺序固定 | 按 syntax→density→burstiness→fragment→punct→vocab 固定顺序 | 前序操作的输出影响后序，但无回滚 |

**根因总结**：当前 Adaptive 是"无脑全开 + 强制下限"，与 `route_strategy` 的"按问题维度算强度"初衷矛盾 — route 算出某操作强度 0.0（无问题），却被强制拉到 0.3。

---

## 二、改写端语境检查框架（统一架构）

在写 P1-1 ~ P1-4 具体算法前，先定义**所有操作共用的语境检查框架**。这是 Phase 1 的核心基础设施，后续所有操作的安全边界都基于它。

### 2.1 框架设计

新增 `scripts/rewrite_context.py`（~200 行，零依赖），提供 4 类语境检查函数：

```python
"""
rewrite_context.py — 改写端语境检查框架

所有改写操作共用的安全边界检查。零依赖（仅 jieba 可选）。
设计参考:
  - Biran et al. ACL 2011 "Putting it Simply" 的 context-aware simplification
  - Vladika et al. 2025 "Lexical Substitution is not Synonym Substitution"
  - Centering Theory (Grosz 1995) 的局部连贯性
"""

import re
import os
import json

# ── 词典加载（懒加载，模块级缓存） ──
_WEIGHTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'weights')
_LEXICON_CACHE = {}

def _load_lexicon(name):
    """加载 weights/{name}.json，带缓存。"""
    if name in _LEXICON_CACHE:
        return _LEXICON_CACHE[name]
    path = os.path.join(_WEIGHTS_DIR, name + '.json')
    if not os.path.exists(path):
        _LEXICON_CACHE[name] = {}
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    _LEXICON_CACHE[name] = data
    return data


# ── 检查 1: 情感一致性 ──

def sentiment_of_sentence(sent):
    """
    判定单句情感极性。

    返回: 'positive' / 'negative' / 'neutral'

    算法:
      1. 加载 sentiment_lexicon.json: {word: polarity}
      2. 统计句中 positive/negative 词数
      3. 若 pos > neg+1 → positive; 若 neg > pos+1 → negative; 否则 neutral
      4. 检测否定词（"不""没""未""别"）翻转前一词极性
    """
    lex = _load_lexicon('sentiment_lexicon')
    if not lex:
        return 'neutral'
    
    # 否定词前缀翻转
    negators = {'不', '没', '未', '别', '无', '非', '莫'}
    
    # 简单分词（中文按字符 + 词典最长匹配）
    tokens = _simple_tokenize(sent)
    
    pos_count = 0
    neg_count = 0
    prev_negated = False
    for tok in tokens:
        if tok in negators:
            prev_negated = True
            continue
        pol = lex.get(tok)
        if pol == 'positive':
            if prev_negated:
                neg_count += 1
            else:
                pos_count += 1
        elif pol == 'negative':
            if prev_negated:
                pos_count += 1
            else:
                neg_count += 1
        prev_negated = False
    
    if pos_count > neg_count + 1:
        return 'positive'
    if neg_count > pos_count + 1:
        return 'negative'
    return 'neutral'


# ── 检查 2: 语体识别 ──

def register_of_text(text):
    """
    判定文本语体。

    返回: 'academic' / 'legal' / 'medical' / 'narrative' / 'general'

    算法:
      1. 加载 register_markers.json: {register: [marker_words]}
      2. 统计各语体 marker 命中数
      3. 命中数最高的语体为判定结果；均 < 2 则 general
    """
    markers = _load_lexicon('register_markers')
    if not markers:
        return 'general'
    
    scores = {}
    for reg, words in markers.items():
        hit = sum(1 for w in words if w in text)
        scores[reg] = hit
    
    top_reg = max(scores, key=scores.get)
    if scores[top_reg] < 2:
        return 'general'
    return top_reg


# ── 检查 3: 术语保护 ──

def is_protected_term(phrase, register=None):
    """
    判定短语是否为受保护术语。

    参数:
      phrase: 待判定短语（如"数据隐私"）
      register: 可选语体提示，限定查某领域白名单

    返回: True 若受保护

    算法:
      1. 加载 protected_terms.json: {domain: [terms]}
      2. 若指定 register，只查该域；否则查全部域
      3. 精确匹配 + 子串包含双重判定
    """
    terms_by_domain = _load_lexicon('protected_terms')
    if not terms_by_domain:
        return False
    
    domains = [register] if register else terms_by_domain.keys()
    for d in domains:
        terms = terms_by_domain.get(d, [])
        for t in terms:
            if phrase == t or (len(phrase) >= 3 and t in phrase):
                return True
    return False


# ── 检查 4: discourse relation 提示 ──

def discourse_relation_of(prev_sent, curr_sent):
    """
    推断相邻句的 discourse relation。

    返回: 'contrast' / 'elaboration' / 'cause' / 'temporal' / 'unknown'

    算法:
      1. 加载 discourse_markers.json: {relation: [markers]}
      2. 检查 curr_sent 句首是否含 marker
      3. 若无 marker，用共现实体推断（Centering Theory 简化版）
         - 共享实体多 → elaboration
         - 无共享实体 → unknown（不应插碎片）
    """
    markers = _load_lexicon('discourse_markers')
    if not markers:
        return 'unknown'
    
    for relation, words in markers.items():
        for w in words:
            # 句首 5 字内匹配
            if curr_sent.strip().startswith(w) or curr_sent.strip()[:5].find(w) >= 0:
                return relation
    
    # 无 marker，用实体共现
    prev_entities = _extract_entities(prev_sent)
    curr_entities = _extract_entities(curr_sent)
    overlap = prev_entities & curr_entities
    if len(overlap) >= 1:
        return 'elaboration'
    return 'unknown'


# ── 检查 5: 句法位置安全 ──

def is_safe_split_point(sent, pos):
    """
    判定 sent[pos] 是否为安全的拆分点（用于 burstiness_engineering）。

    返回: True 若安全（拆点后两侧都是完整句法单元）

    算法:
      1. 拆点字符必须是 ，或 、
      2. 拆点后 10 字内不能有并列连词（"和""与""及""以及""或者"）
         — 否则拆点在并列结构内部
      3. 拆点前 5 字内不能有"等""之类"（列举未尽）
      4. 拆点后不能紧跟标点（避免空句）
    """
    if pos >= len(sent):
        return False
    if sent[pos] not in '，、':
        return False
    
    # 拆点后 10 字内含并列连词 → 并列结构内部
    after = sent[pos+1:pos+11]
    for conj in ['和', '与', '及', '以及', '或者', '还有', '并且']:
        if conj in after:
            return False
    
    # 拆点前 5 字内含列举词 → 未尽列举
    before = sent[max(0, pos-5):pos]
    for enum in ['等', '之类', '比如', '例如', '诸如此类']:
        if enum in before:
            return False
    
    # 拆点后紧跟标点 → 空句
    if pos + 1 < len(sent) and sent[pos+1] in '。！？；，、':
        return False
    
    return True


# ── 辅助函数 ──

def _simple_tokenize(sent):
    """简单分词：优先词典最长匹配，否则按字符切。"""
    # 用 cilin_synonyms 的词表做最长匹配（已有 38873 词）
    lex = _load_lexicon('cilin_synonyms')
    # 简化实现：按 2-4 字滑窗找词典词，否则单字
    tokens = []
    i = 0
    while i < len(sent):
        matched = False
        for L in (4, 3, 2):
            w = sent[i:i+L]
            if w in lex:
                tokens.append(w)
                i += L
                matched = True
                break
        if not matched:
            if sent[i].strip():
                tokens.append(sent[i])
            i += 1
    return tokens


def _extract_entities(sent):
    """抽取句子实体（简化版：取名词性 2-4 字词）。"""
    tokens = _simple_tokenize(sent)
    # 简化：长度 >= 2 的非停用词视为实体
    stop = {'的', '了', '是', '在', '和', '与', '及', '或', '也', '都', '这', '那', '一', '不', '没'}
    return set(t for t in tokens if len(t) >= 2 and t not in stop)
```

### 2.2 框架依赖的 4 个词典

| 词典 | 体积 | 内容 | Phase 1 是否必需 |
|------|------|------|----------------|
| `sentiment_lexicon.json` | ~5KB | 词 → positive/negative 极性 | P1-1 需要（情感约束） |
| `register_markers.json` | ~3KB | 语体 → marker 词列表 | P1-3 需要（术语保护） |
| `protected_terms.json` | ~10KB | 领域 → 术语清单 | P1-3 必需 |
| `discourse_markers.json` | ~2KB | 关系 → marker 词列表 | P1-1 需要（DM 分类） |

### 2.3 理论依据

- **Biran et al. ACL 2011** *Putting it Simply*: context-aware simplification 的两个核心 — Word-Sentence Similarity + context rules。我们用 `is_safe_split_point` 和 `discourse_relation_of` 实现 context rules。
- **Vladika et al. 2025** *Lexical Substitution is not Synonym Substitution*: 强调候选必须语境相关。我们用 `sentiment_of_sentence` + `register_of_text` 做语境约束。
- **Centering Theory (Grosz 1995)**: `discourse_relation_of` 的实体共现推断即简化版 Centering。

---

## 三、P1-1 碎片位置约束 + 情感一致性 — 详细算法

### 3.1 改动点

**文件**: [rewrite_operations.py](file:///d:/working/0001/humanize-chinese-dimension/scripts/rewrite_operations.py)
**新增依赖**: `rewrite_context.py`（Phase 1 框架）+ `discourse_markers.json` + `sentiment_lexicon.json`

### 3.2 算法：语境感知碎片插入

替换 `burstiness_engineering` 第 131-172 行的拆分逻辑 + `fragment_injection` 第 202-213 行的插入逻辑。

#### 3.2.1 新 `_FRAGMENTS` 结构（按 discourse relation 分类）

```python
# 替换原 _FRAGMENTS 单一列表，改为分类词表
_FRAGMENTS_BY_RELATION = {
    'hedge': [
        '未必如此。', '也难讲。', '不一定。', '看情况。', '难说。',
        '未必。', '不好说。',
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
        '没什么大不了的。', '算了。', '无所谓了。', '就这样。',
    ],
    'comment_termination': [
        '就这样。', '到此为止。', '说完了。',
    ],
    'contrast': [
        '其实不然。', '未必如此。', '话又说回来。', '换个角度看。',
    ],
}
```

#### 3.2.2 新 `fragment_injection` 算法

```python
def fragment_injection(text, intensity=0.3, seed=None):
    """
    语境感知碎片注入。

    算法:
      1. 分句
      2. 对每句判断是否插入:
         a. 句长 > 25 字
         b. 句末标点 ∈ {。！？}
         c. 全局碎片数 < 上限（默认 3，可配）
         d. 距上一个碎片 >= 3 句
      3. 若插入，根据前句情感 + discourse relation 选碎片类:
         a. 前句 positive → comment_positive 或 hedge
         b. 前句 negative → comment_negative 或 hedge
         c. 前句 neutral + academic/legal 语体 → 跳过（学术文本不插评论）
         d. 前句 neutral + general/narrative → comment_neutral 或 hedge
         e. discourse relation = contrast → contrast 类
         f. discourse relation = unknown → 只允许 hedge（最安全）
    """
    from rewrite_context import sentiment_of_sentence, discourse_relation_of, register_of_text
    
    rng = random.Random(seed)
    sentences = split_sentences(text)
    if len(sentences) < 1:
        return text
    
    # 语体判定（全文一次）
    text_register = register_of_text(text)
    
    # 学术/法律/医学语体：禁插 comment 类，只允许 hedge
    formal_registers = {'academic', 'legal', 'medical'}
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
            and sent[-1] in '。！？'  # 必须句末标点（修复 C3）
            and frag_count < MAX_FRAGMENTS
            and i - last_frag_idx >= MIN_GAP
            and i < len(sentences) - 1  # 不在末句后插（避免孤立碎片）
        )
        
        if should_try and rng.random() < intensity:
            prev_sent = sentences[i-1] if i > 0 else ''
            relation = discourse_relation_of(prev_sent, sent)
            sentiment = sentiment_of_sentence(sent)
            
            fragment = _pick_fragment(
                relation, sentiment, allow_comment, rng
            )
            if fragment:
                result.append(fragment)
                frag_count += 1
                last_frag_idx = i
    
    return ''.join(result)


def _pick_fragment(relation, sentiment, allow_comment, rng):
    """根据 relation + sentiment 选碎片，返回带句号的碎片或 None。"""
    from rewrite_context import _FRAGMENTS_BY_RELATION  # 或本地导入
    
    # 学术语体且 relation=unknown → 只允许 hedge
    if not allow_comment and relation == 'unknown':
        candidates = _FRAGMENTS_BY_RELATION['hedge']
        return rng.choice(candidates)
    
    # contrast 关系优先
    if relation == 'contrast':
        candidates = _FRAGMENTS_BY_RELATION['contrast']
        return rng.choice(candidates)
    
    # 按情感选 comment 类
    if allow_comment:
        if sentiment == 'positive':
            pool = _FRAGMENTS_BY_RELATION['comment_positive']
        elif sentiment == 'negative':
            pool = _FRAGMENTS_BY_RELATION['comment_negative']
        else:
            pool = (_FRAGMENTS_BY_RELATION['comment_neutral']
                    + _FRAGMENTS_BY_RELATION['hedge'])
        return rng.choice(pool)
    
    # fallback: hedge
    return rng.choice(_FRAGMENTS_BY_RELATION['hedge'])
```

#### 3.2.3 新 `burstiness_engineering` 拆分约束

修改第 131-172 行，关键改动：拆点必须通过 `is_safe_split_point` 检查；拆点后**不插碎片**（碎片交给 `fragment_injection` 统一处理）。

```python
def burstiness_engineering(text, intensity=0.7, seed=None):
    """
    突发性工程: 强制短长句交替。

    改动:
      1. 拆点必须通过 is_safe_split_point 检查（修复 C2）
      2. 拆点后不再插碎片（碎片由 fragment_injection 统一处理）
      3. 拆分后 short_part 末尾若是 ，或 、则改为 。
    """
    from rewrite_context import is_safe_split_point
    
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
            if rng.random() < 0.5:
                # 拆分模式
                split_pos = _find_natural_split(sent)
                # 新增：拆点安全性检查
                if split_pos and is_safe_split_point(sent, split_pos - 1):
                    short_part = sent[:split_pos].strip()
                    rest_part = sent[split_pos:].strip()
                    # short_part 末尾标点规范化
                    if short_part and short_part[-1] in '，、':
                        short_part = short_part[:-1] + '。'
                    elif short_part and short_part[-1] not in '。！？；':
                        short_part = short_part + '。'
                    result.append(short_part)
                    # rest_part 标点规范化
                    if rest_part and rest_part[-1] in '。！？；':
                        result.append(rest_part)
                    else:
                        result.append(rest_part + '。')
                else:
                    # 拆点不安全，保留原句
                    result.append(_ensure_terminator(sent))
            else:
                # 合并模式（保持原逻辑）
                if i + 1 < len(sentences):
                    merged = _merge_sentences(sent, sentences[i + 1], rng=rng)
                    result.append(merged + '。')
                    i += 1
                else:
                    result.append(_ensure_terminator(sent))
        else:
            result.append(_ensure_terminator(sent))
        i += 1
    
    return ''.join(result)


def _ensure_terminator(sent):
    """确保句末有标点。"""
    if sent and sent[-1] in '。！？；':
        return sent
    return sent + '。'
```

### 3.3 验收用例

| 输入 | 期望输出 | 旧版输出 |
|------|---------|---------|
| "重点分析其在细胞代谢、增殖及凋亡中的角色" | "重点分析其在细胞代谢、增殖及凋亡中的角色。"（不拆） | "重点分析其在细胞代谢、。真的。增殖及凋亡中的角色" |
| "在这个世界上，每个人都有自己的邻居" | 不插碎片（前句 neutral + general + relation=elaboration 可插 hedge） | "在这个世界上。谁知道呢。" |
| "爷爷主动承担起了照顾我的责任" | 不插"没什么大不了的"（positive 情感禁插 negative） | "没什么大不了的。" |
| "本研究揭示了 PKM2 在肿瘤细胞中的复杂功能" | 不插 comment（academic 语体） | "也是奇怪。" |

---

## 四、P1-2 省略号语境触发 — 详细算法

### 4.1 改动点

**文件**: [rewrite_operations.py](file:///d:/working/0001/humanize-chinese-dimension/scripts/rewrite_operations.py) `punctuation_humanize` 第 451-458 行
**新增依赖**: 无（触发词表内嵌函数）

### 4.2 算法：语境触发省略号

```python
# 省略号允许语境（语义属于"未尽/沉思/留白"）
_ELLIPSIS_OK_CONTEXTS = {
    'enum_incomplete': ['等', '之类', '比如', '例如', '诸如此类', '等等', '之类'],
    'uncertainty': ['或许', '可能', '也许', '大概', '似乎', '说不定', '难说', '未尝'],
    'hesitation': ['不知道', '不确定', '没想好', '说不上', '讲不清'],
    'quotation_open': ['"', '"', '「', '『'],  # 引文未闭合
}

# 省略号禁止语境（语义属于"闭环/确定"）
_ELLIPSIS_FORBIDDEN_CONTEXTS = {
    'conclusion': ['确保', '证明', '表明', '综上', '因此', '所以', '可见', '显然', '无疑'],
    'definitive': ['一定', '必然', '肯定', '绝对', '毫无疑问', '毫无疑问地'],
    'imperative': ['必须', '应当', '应该', '务必', '需要'],
}


def _should_add_ellipsis(last_sentence):
    """
    判定末句是否适合加省略号。

    返回: (should_add: bool, reason: str)

    算法:
      1. 末句含 forbidden 词 → 直接拒绝
      2. 末句含 OK 词 → 准许
      3. 末句是引文且未闭合 → 准许
      4. 否则 → 拒绝（默认不加）
    """
    for word in _ELLIPSIS_FORBIDDEN_CONTEXTS['conclusion']:
        if word in last_sentence:
            return False, 'conclusion_word'
    for word in _ELLIPSIS_FORBIDDEN_CONTEXTS['definitive']:
        if word in last_sentence:
            return False, 'definitive_word'
    for word in _ELLIPSIS_FORBIDDEN_CONTEXTS['imperative']:
        if word in last_sentence:
            return False, 'imperative_word'
    
    # 检查 OK 语境
    for word in _ELLIPSIS_OK_CONTEXTS['enum_incomplete']:
        if word in last_sentence:
            return True, 'enum_incomplete'
    for word in _ELLIPSIS_OK_CONTEXTS['uncertainty']:
        if word in last_sentence:
            return True, 'uncertainty'
    for word in _ELLIPSIS_OK_CONTEXTS['hesitation']:
        if word in last_sentence:
            return True, 'hesitation'
    
    # 引文未闭合
    quote_count = last_sentence.count('"') + last_sentence.count('"')
    if quote_count % 2 == 1:
        return True, 'quotation_open'
    
    return False, 'no_trigger'


def _extract_last_sentence(text):
    """提取文本末句（最后一个完整句）。"""
    sents = split_sentences(text)
    if not sents:
        return ''
    # 去掉末尾标点，返回纯文本
    last = sents[-1]
    return last.rstrip('。！？；…')
```

### 4.3 新 `punctuation_humanize` 省略号部分

```python
def punctuation_humanize(text, intensity=0.3, seed=None):
    """标点人性化（省略号部分重写）。"""
    rng = random.Random(seed)
    result = text
    
    # ... (逗号句号比、问号部分保持不变) ...
    
    # 3. 在适当位置加省略号（重写）
    MAX_ELLIPSIS = 1  # 单篇硬上限
    if result.count('……') < MAX_ELLIPSIS and rng.random() < intensity * 0.3:
        # 找末段末句
        paras = result.split('\n')
        if paras:
            last_para = paras[-1]
            last_sent = _extract_last_sentence(last_para)
            
            if len(last_sent) > 10:  # 末句够长才考虑
                should, reason = _should_add_ellipsis(last_sent)
                if should:
                    # 剥掉末句标点再加省略号
                    last_para_clean = last_para.rstrip('。！？…')
                    paras[-1] = last_para_clean + '……'
                    result = '\n'.join(paras)
    
    return result
```

### 4.4 验收用例

| 末句 | 旧版 | 新版 | 原因 |
|------|------|------|------|
| "确保了实验的可靠性" | "确保了实验的可靠性……" | "确保了实验的可靠性" | conclusion 词"确保"触发禁止 |
| "综上所述，技术前景广阔" | "综上所述，技术前景广阔……" | "综上所述，技术前景广阔" | conclusion 词"综上"触发禁止 |
| "比如苹果、香蕉、橘子等" | "比如苹果、香蕉、橘子等……" | "比如苹果、香蕉、橘子等……" | enum_incomplete 触发允许 |
| "或许这就是答案" | "或许这就是答案……" | "或许这就是答案……" | uncertainty 触发允许 |
| "势头不错" | "势头不错……" | "势头不错" | 无触发词，默认拒绝 |

---

## 五、P1-3 术语保护词典 — 详细算法 + 词典构建方案

### 5.1 词典构建：自动化 + 人工校验

**目标**: 构建 `protected_terms.json`（~10KB），按领域分组的不可替换术语。

#### 5.1.1 数据来源（零成本）

| 来源 | 用途 | 获取方式 |
|------|------|---------|
| [scripts/weights/cilin_synonyms.json](file:///d:/working/0001/humanize-chinese-dimension/scripts/weights/cilin_synonyms.json) | 已有词林，过滤出领域术语候选 | 已有 |
| 现有改写案例 [semantic_check_articles.md](file:///d:/working/0001/humanize-chinese-dimension/dev/reports/semantic_check_articles.md) | 人工标注被误替换的术语 | 已有 |
| HC3-Chinese 数据集 | 抽取 AI 文本高频术语 | 已有 |
| 学术/法律/医学公开术语表 | 领域术语标准 | 公开 |

#### 5.1.2 自动化构建算法（参考 Wang 2021 K-means++ + SO-PMI）

新增 `dev/build_protected_terms.py`（一次性脚本，不入运行时依赖）：

```python
"""
build_protected_terms.py — 自动构建 protected_terms.json

算法（参考 Wang et al. 2021 Connection Science）:
  1. 种子词：从现有改写案例中人工标注 20 个误替换术语
  2. 语料：HC3-Chinese + 长文本 benchmark 语料
  3. SO-PMI 扩展: 对每个种子词 w，计算候选词 c 的 SO-PMI:
     SO-PMI(w, c) = PMI(w, c) - PMI(w, neg_seed)
     其中 neg_seed 是领域外词（如"苹果"对医学域）
  4. 阈值过滤: SO-PMI > 3.0 且共现频次 > 5 的候选词加入
  5. K-means++ 聚类：把扩展词按语义聚类，去除噪声
  6. 人工校验：输出候选词表，人工 review 后入库

输出: scripts/weights/protected_terms.json
"""
import json
import math
from collections import Counter, defaultdict
import os

SEED_TERMS = {
    'medical': ['PKM2', '丙酮酸激酶', '凋亡', '糖酵解', '信号通路', '细胞代谢', '增殖'],
    'legal': ['数据隐私', '算法偏见', '构成要件', '个人信息', '知情同意'],
    'academic': ['BERT', 'Transformer', '微调', '预训练', '语言模型', '深度学习'],
    'tech': ['数据库', 'API', '架构', '框架', '系统', '协议'],
}

# 领域外否定词（用于 SO-PMI）
NEG_SEEDS = {
    'medical': ['苹果', '旅游', '电影', '美食'],
    'legal': ['细胞', '分子', '酶', '蛋白'],
    'academic': ['厨房', '跑步', '睡眠', '约会'],
    'tech': ['诗歌', '绘画', '音乐', '舞蹈'],
}


def build_pmi_from_corpus(corpus_files, window=5):
    """从语料构建 PMI 表。"""
    word_count = Counter()
    pair_count = defaultdict(int)
    total = 0
    
    for f in corpus_files:
        with open(f, 'r', encoding='utf-8') as fp:
            text = fp.read()
        # 简单分字（中文）
        chars = [c for c in text if '\u4e00' <= c <= '\u9fff' or c.isalpha()]
        # 用 jieba 分词（若可用）
        try:
            import jieba
            words = list(jieba.cut(text))
        except ImportError:
            words = chars
        
        for i, w in enumerate(words):
            if len(w) < 2:
                continue
            word_count[w] += 1
            total += 1
            for j in range(i+1, min(i+window, len(words))):
                if len(words[j]) >= 2:
                    pair_count[(w, words[j])] += 1
    
    return word_count, pair_count, total


def compute_so_pmi(seed, candidate, word_count, pair_count, total, neg_seeds):
    """计算 SO-PMI。"""
    def pmi(w1, w2):
        c1 = word_count.get(w1, 0)
        c2 = word_count.get(w2, 0)
        c12 = pair_count.get((w1, w2), 0) + pair_count.get((w2, w1), 0)
        if c1 == 0 or c2 == 0 or c12 == 0:
            return -float('inf')
        return math.log2((c12 * total) / (c1 * c2))
    
    pos_pmi = max(pmi(seed, candidate), -10)
    neg_pmi = max(pmi(neg_seeds[0], candidate), -10)
    return pos_pmi - neg_pmi


def expand_domain(domain, seeds, neg_seeds, word_count, pair_count, total,
                  threshold=3.0, min_cooccur=5):
    """扩展单领域术语。"""
    expanded = list(seeds)
    # 候选词：与种子词共现频次 >= min_cooccur 的词
    candidates = set()
    for seed in seeds:
        for (w1, w2), c in pair_count.items():
            if w1 == seed and c >= min_cooccur and w2 not in seeds:
                candidates.add(w2)
            if w2 == seed and c >= min_cooccur and w1 not in seeds:
                candidates.add(w1)
    
    # SO-PMI 打分
    scored = []
    for cand in candidates:
        so_pmi = compute_so_pmi(seeds[0], cand, word_count, pair_count, total, neg_seeds)
        if so_pmi > threshold:
            scored.append((cand, so_pmi))
    
    scored.sort(key=lambda x: -x[1])
    expanded.extend([w for w, _ in scored[:50]])  # 取 Top-50
    return expanded


def main():
    # 1. 收集语料
    corpus_files = []  # HC3 + 长文本语料路径
    # ... (扫描 dev/data/ 下语料)
    
    # 2. 构建 PMI
    word_count, pair_count, total = build_pmi_from_corpus(corpus_files)
    
    # 3. 逐领域扩展
    result = {}
    for domain, seeds in SEED_TERMS.items():
        expanded = expand_domain(
            domain, seeds, NEG_SEEDS[domain],
            word_count, pair_count, total
        )
        result[domain] = expanded
        print(f"[{domain}] 种子 {len(seeds)} → 扩展 {len(expanded)}")
    
    # 4. 输出（待人工 review）
    out = os.path.join('scripts', 'weights', 'protected_terms.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"输出: {out} (待人工 review)")


if __name__ == '__main__':
    main()
```

#### 5.1.3 词典结构

```json
{
  "medical": ["PKM2", "丙酮酸激酶", "凋亡", "糖酵解", "信号通路", ...],
  "legal": ["数据隐私", "算法偏见", "构成要件", "个人信息", ...],
  "academic": ["BERT", "Transformer", "微调", "预训练", ...],
  "tech": ["数据库", "API", "架构", "框架", ...]
}
```

### 5.2 改动点：`ai_vocab_scrub` 集成术语保护

**文件**: [rewrite_operations.py](file:///d:/working/0001/humanize-chinese-dimension/scripts/rewrite_operations.py) `ai_vocab_scrub` 第 508-543 行

```python
def ai_vocab_scrub(text, intensity=0.7, seed=None, replacements=None):
    """AI 词汇指纹清除（带术语保护）。"""
    from rewrite_context import is_protected_term, register_of_text
    
    rng = random.Random(seed)
    if replacements is None:
        replacements = _VOCAB_REPLACEMENTS
    
    # 语体判定（全文一次）
    text_register = register_of_text(text)
    
    result = text
    for ai_word, alternatives in replacements.items():
        count = result.count(ai_word)
        if count == 0:
            continue
        for _ in range(count):
            if ai_word not in result:
                break
            # 找到 ai_word 在 result 中的位置
            pos = result.find(ai_word)
            # 取上下文 ±10 字用于术语保护检查
            ctx_start = max(0, pos - 5)
            ctx_end = min(len(result), pos + len(ai_word) + 5)
            context_phrase = result[ctx_start:ctx_end]
            
            # 新增：术语保护检查
            if is_protected_term(ai_word, text_register) or is_protected_term(context_phrase, text_register):
                # 受保护，跳过此替换
                # 用 sentinel 标记已处理，避免死循环
                result = result[:pos] + '\x00' + result[pos+len(ai_word):]
                continue
            
            if rng.random() < intensity:
                replacement = rng.choice(alternatives)
                result = result[:pos] + replacement + result[pos+len(ai_word):]
            else:
                # 标记已处理
                result = result[:pos] + '\x00' + result[pos+len(ai_word):]
    
    # 清理 sentinel
    result = result.replace('\x00', ai_word) if '\x00' in result else result
    # 注意：上面的清理逻辑有 bug，应改为最后统一恢复
    # 正确实现见下方完整版
    
    return result
```

**修正实现**（用占位符避免死循环 + 最后恢复）：

```python
def ai_vocab_scrub(text, intensity=0.7, seed=None, replacements=None):
    """AI 词汇指纹清除（带术语保护）。"""
    from rewrite_context import is_protected_term, register_of_text
    
    rng = random.Random(seed)
    if replacements is None:
        replacements = _VOCAB_REPLACEMENTS
    
    text_register = register_of_text(text)
    
    # 用占位符标记已处理位置，避免二次替换
    SENTINEL = '\x01\x02\x03'  # 不可见占位符
    
    result = text
    for ai_word, alternatives in replacements.items():
        count = result.count(ai_word)
        if count == 0:
            continue
        for _ in range(count):
            pos = result.find(ai_word)
            if pos == -1:
                break
            
            # 术语保护检查
            ctx_start = max(0, pos - 5)
            ctx_end = min(len(result), pos + len(ai_word) + 5)
            context_phrase = result[ctx_start:ctx_end]
            
            if is_protected_term(ai_word, text_register) or is_protected_term(context_phrase, text_register):
                # 受保护，用占位符替换此位置后跳过
                result = result[:pos] + SENTINEL + result[pos+len(ai_word):]
                continue
            
            if rng.random() < intensity:
                replacement = rng.choice(alternatives)
                result = result[:pos] + replacement + result[pos+len(ai_word):]
            else:
                result = result[:pos] + SENTINEL + result[pos+len(ai_word):]
    
    # 恢复占位符为原词
    # 注意：占位符位置应保持原词，但由于已经替换过，这里需要更复杂的处理
    # 简化：用唯一占位符 + 词表记录
    # 更简洁的实现见最终版
    
    return result
```

**最终简洁实现**（用更清晰的逐位置处理）：

```python
def ai_vocab_scrub(text, intensity=0.7, seed=None, replacements=None):
    """AI 词汇指纹清除（带术语保护 + WSD 预留接口）。"""
    from rewrite_context import is_protected_term, register_of_text
    
    rng = random.Random(seed)
    if replacements is None:
        replacements = _VOCAB_REPLACEMENTS
    
    text_register = register_of_text(text)
    
    result = text
    for ai_word, alternatives in replacements.items():
        # 用正则 finditer 收集所有位置，避免修改后位置偏移
        positions = [m.start() for m in __import__('re').finditer(
            __import__('re').escape(ai_word), result
        )]
        if not positions:
            continue
        
        # 从后向前替换，避免位置偏移
        for pos in reversed(positions):
            ctx_start = max(0, pos - 5)
            ctx_end = min(len(result), pos + len(ai_word) + 5)
            context_phrase = result[ctx_start:ctx_end]
            
            # 检查 1: 术语保护
            if is_protected_term(ai_word, text_register) or is_protected_term(context_phrase, text_register):
                continue  # 跳过此位置
            
            # 检查 2: WSD（Phase 2 实现，Phase 1 预留接口）
            # if not _wsd_check(ai_word, alternatives, result, pos):
            #     continue
            
            if rng.random() < intensity:
                replacement = rng.choice(alternatives)
                result = result[:pos] + replacement + result[pos+len(ai_word):]
    
    return result
```

### 5.3 验收用例

| 输入片段 | 旧版 | 新版 | 原因 |
|---------|------|------|------|
| "数据隐私和安全" | "数额隐私和安全" | "数据隐私和安全" | "数据隐私"在 legal 保护清单 |
| "PKM2 在肿瘤细胞" | "PKM2 在肿瘤细胞"（不命中替换表） | "PKM2 在肿瘤细胞" | "PKM2"在 medical 保护清单 |
| "数据量很大" | "数据量很大" | "数额量很大"（允许） | "数据量"非保护术语，"数据"可替换 |
| "构建深度学习模型" | "搭深度学习模型" | "构建深度学习模型" | "深度学习"在 academic 保护清单 |

---

## 六、P1-4 语义预算 + 长度分流 — 详细算法

### 6.1 改动点

**文件**: [humanize_cn.py](file:///d:/working/0001/humanize-chinese-dimension/scripts/humanize_cn.py) Pass 5 第 3830-3892 行

### 6.2 算法：自适应强度路由 + 语义预算

```python
# 替换原 _ro_defaults 强制下限逻辑

# 语义代价预估表（基于 ablation 历史，Phase 1 用经验值，Phase 2 用实测）
_SEMANTIC_COST_ESTIMATE = {
    'syntax_pattern_break': 0.05,      # 句式变换代价低
    'info_density_rebalance': 0.08,    # 段落合并/拆分代价中
    'burstiness_engineering': 0.12,    # 拆句代价高
    'fragment_injection': 0.20,        # 碎片插入代价最高
    'punctuation_humanize': 0.05,      # 标点变换代价低
    'ai_vocab_scrub': 0.10,            # 词汇替换代价中
}

# 长度分流的字数阈值
SHORT_TEXT_THRESHOLD = 200  # < 200 字为短文本

# 语义预算上限（累计代价不超过此值）
SEMANTIC_BUDGET_DEFAULT = 0.40  # 40% 累计代价上限

# 最大并发操作数
MAX_CONCURRENT_OPS = 4


def _compute_adaptive_params(route, char_count, tier='moderate'):
    """
    计算自适应操作参数，带语义预算 + 长度分流。

    返回: {op_name: intensity}

    算法:
      1. 长度分流:
         - 短文本 (< 200 字): 只启用 vocab + punct，跳过 structure 类
         - 长文本: 全操作候选
      2. 从 route 取 route_val，不强制下限（移除原 max 逻辑）
      3. 按 route_val 降序排操作
      4. 贪心选操作: 累计 semantic_cost <= budget 且 ops 数 <= max_concurrent
      5. route_val < 0.1 的操作不启用（无问题维度）
    """
    # 长度分流
    is_short = char_count < SHORT_TEXT_THRESHOLD
    short_text_ops = {'ai_vocab_scrub', 'punctuation_humanize'}  # 短文本只允许这两个
    
    # 从 route 取值
    route_ops = {}
    if route and 'ops' in route:
        for op_name in _SEMANTIC_COST_ESTIMATE:
            op_cfg = route['ops'].get(op_name, {})
            route_val = op_cfg.get('intensity', 0.0)
            if route_val >= 0.1:  # 有问题维度才启用
                route_ops[op_name] = route_val
    
    # 短文本过滤
    if is_short:
        route_ops = {k: v for k, v in route_ops.items() if k in short_text_ops}
    
    # 按 route_val 降序排
    sorted_ops = sorted(route_ops.items(), key=lambda x: -x[1])
    
    # 贪心选择，受语义预算 + 并发上限约束
    selected = {}
    cumulative_cost = 0.0
    for op_name, intensity in sorted_ops:
        if len(selected) >= MAX_CONCURRENT_OPS:
            break
        cost = _SEMANTIC_COST_ESTIMATE.get(op_name, 0.1)
        if cumulative_cost + cost > SEMANTIC_BUDGET_DEFAULT:
            continue  # 跳过此操作，不中断（可能后面有更便宜的操作）
        selected[op_name] = intensity
        cumulative_cost += cost
    
    # 兜底：若 selected 为空且非 short text，至少启用 vocab scrub（最低代价）
    if not selected and not is_short:
        selected['ai_vocab_scrub'] = 0.3
    
    return selected
```

### 6.3 新 Pass 5 集成

替换 [humanize_cn.py:3830-3892](file:///d:/working/0001/humanize-chinese-dimension/scripts/humanize_cn.py)：

```python
# ── Pass 5: 维普对齐新改写操作 (Phase 2, 语义预算 + 长度分流) ──
if _HAS_REWRITE_OPS and adaptive:
    char_count = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    
    # 计算自适应参数（带语义预算 + 长度分流）
    _ro_params = _compute_adaptive_params(route, char_count, tier='moderate')
    
    # 应用改写操作（顺序: 句式 → 密度 → 突发性 → 碎片 → 标点 → 词汇）
    # 但只应用 _ro_params 中启用的操作
    op_order = [
        ('syntax_pattern_break', syntax_pattern_break),
        ('info_density_rebalance', info_density_rebalance),
        ('burstiness_engineering', burstiness_engineering),
        ('fragment_injection', fragment_injection),
        ('punctuation_humanize', punctuation_humanize),
        ('ai_vocab_scrub', ai_vocab_scrub),
    ]
    
    for op_name, op_func in op_order:
        if op_name not in _ro_params:
            continue
        intensity = _ro_params[op_name]
        if intensity <= 0:
            continue
        try:
            text = op_func(text, intensity=intensity, seed=seed)
        except Exception:
            pass
```

### 6.4 验收用例

| 输入 | 字数 | 旧版启用 | 新版启用 | 原因 |
|------|------|---------|---------|------|
| 日常随笔 107 字 | 107 | 6 操作全开 | vocab + punct | 短文本分流 |
| AI 三段式 341 字 | 341 | 6 操作全开 | syntax + burstiness + vocab（route 值高的 3 个） | 语义预算 0.40 限制 |
| 学术论文 235 字 | 235 | 6 操作全开 | vocab + punct + syntax（route 值高的 3 个） | 累计代价 < 0.40 |
| 新闻报道 172 字 | 172 | 6 操作全开 | vocab + punct | < 200 字短文本分流 |

---

## 七、语料扩充总体计划

### 7.1 现有语料资产盘点

| 资产 | 位置 | 体量 | 用途 |
|------|------|------|------|
| `ngram_freq_cn.json` | [scripts/weights/](file:///d:/working/0001/humanize-chinese-dimension/scripts/weights/) | 字符 3-gram 频率 | 已用于困惑度，可扩展做 PMI |
| `ngram_freq_cn_human.json` | 本地训练 | 人类文本 n-gram | best-of-n 排序 |
| `cilin_synonyms.json` | [scripts/weights/](file:///d:/working/0001/humanize-chinese-dimension/scripts/weights/) | 38873 词 | 同义词替换 |
| `ai_vocab_dict.json` | [scripts/weights/](file:///d:/working/0001/humanize-chinese-dimension/scripts/weights/) | 460+ AI 高频词 | AI 词汇检测 |
| HC3-Chinese | 本地 | 12853 对问答 | 校准 + 测试 |
| 长文本语料 | [dev/data/](file:///d:/working/0001/humanize-chinese-dimension/dev/data/) | 170 AI + 170 人类长文本 | 长文本 benchmark |

### 7.2 Phase 1 新增语料需求

| 词典 | 体量 | 构建方法 | 理论依据 |
|------|------|---------|---------|
| `protected_terms.json` | ~10KB | 种子词 + SO-PMI 扩展 + 人工 review | Wang 2021 K-means++ + SO-PMI |
| `sentiment_lexicon.json` | ~5KB | 从 HowNet/NRC 公开词典摘取 + 简化 | Li 2025 HowNet + SentiWordNet |
| `register_markers.json` | ~3KB | 人工整理（每领域 20-30 marker） | 领域术语工程实践 |
| `discourse_markers.json` | ~2KB | 人工整理（按 RST 关系分类） | Grosz 1995 + Wu 2025 polysemous DM |

### 7.3 Phase 2 语料扩充计划（前瞻）

| 词典 | 体量 | 构建方法 | 理论依据 |
|------|------|---------|---------|
| `sense_definitions.json` | ~50KB | HowNet 义项定义摘取 + 词典释义递归抽取 | Liang & Tian 2020 词典释义关系抽取 |
| `collocations.json` | ~20KB | 从 ngram_freq_cn.json 用 MI3 算法抽取 | Gu & Pan 2021 MI3 中文搭配抽取 |
| 候选替换语料扩充 | 词表翻倍 | 用 PMI 从 ngram_freq_cn 抽取近义词 + AddCos 排序 | Melamud 2015 AddCos + Hawker 2007 PMI |

### 7.4 替换语料扩充的统一算法

**目标**: 把 `_VOCAB_REPLACEMENTS`（当前 40 词）扩充到 200+ 词，每个词带 3-5 个语境相关候选。

**算法**（参考 Hawker 2007 PMI + Bolshakov 2004 n-gram + Melamud 2015 AddCos）：

```python
"""
build_replacement_corpus.py — 扩充替换语料

算法:
  1. 种子: 现有 _VOCAB_REPLACEMENTS 的 40 个 AI 高频词
  2. 候选生成: 对每个种子词 w
     a. 从 cilin_synonyms.json 取同义词集 S
     b. 从 ngram_freq_cn.json 找与 w 共现频次高的词（PMI > 2）
     c. 合并候选集 C = S ∪ {高 PMI 词}
  3. 候选排序: 对每个候选 c ∈ C
     a. 计算 AddCos(c, w, Ctx) = (cos(c, w) + Σ cos(c, ctx_word)) / (|Ctx|+1)
        - cos 用字符 2-gram Jaccard 近似（零依赖）
        - Ctx 取 w 在 HC3 AI 文本中的上下文（±5 词）
     b. 按 AddCos 降序排
  4. 过滤:
     a. 去掉 AddCos < 0.3 的候选（语义不相关）
     b. 去掉 WSD 冲突候选（Phase 2，用 sense_definitions）
     c. 去掉 protected_terms 命中候选
  5. 取 Top-5 候选入库
  6. 人工 review 抽样 10%

输出: scripts/weights/ai_vocab_replacements_expanded.json
"""

def compute_pmi(w1, w2, ngram_freq, total):
    """从 ngram_freq_cn 计算 PMI。"""
    # 假设 ngram_freq 是 {(w1, w2): freq} 的 2-gram 表
    c12 = ngram_freq.get((w1, w2), 0) + ngram_freq.get((w2, w1), 0)
    c1 = sum(v for k, v in ngram_freq.items() if w1 in k)
    c2 = sum(v for k, v in ngram_freq.items() if w2 in k)
    if c12 == 0 or c1 == 0 or c2 == 0:
        return -float('inf')
    return math.log2((c12 * total) / (c1 * c2))


def compute_addcos(candidate, target, context_words):
    """
    AddCos (Melamud 2015) 的零依赖近似:
      AddCos(c, t, C) = (sim(c, t) + Σ sim(c, w)) / (|C|+1)
    sim 用字符 2-gram Jaccard 近似。
    """
    def char_2gram_jaccard(w1, w2):
        s1 = set(w1[i:i+2] for i in range(len(w1)-1))
        s2 = set(w2[i:i+2] for i in range(len(w2)-1))
        if not s1 or not s2:
            return 0.0
        return len(s1 & s2) / len(s1 | s2)
    
    sim_target = char_2gram_jaccard(candidate, target)
    sim_context = sum(char_2gram_jaccard(candidate, w) for w in context_words)
    return (sim_target + sim_context) / (len(context_words) + 1)


def expand_replacements(seed_replacements, cilin, ngram_freq, hc3_contexts):
    """扩充替换词表。"""
    expanded = {}
    for ai_word, old_alts in seed_replacements.items():
        # 1. 候选生成
        synonyms = cilin.get(ai_word, [])
        # PMI 高的共现词
        pmi_candidates = []
        for (w1, w2), _ in ngram_freq.items():
            if w1 == ai_word and w2 != ai_word:
                pmi = compute_pmi(ai_word, w2, ngram_freq, total=sum(ngram_freq.values()))
                if pmi > 2.0:
                    pmi_candidates.append((w2, pmi))
            elif w2 == ai_word and w1 != ai_word:
                pmi = compute_pmi(ai_word, w1, ngram_freq, total=sum(ngram_freq.values()))
                if pmi > 2.0:
                    pmi_candidates.append((w1, pmi))
        pmi_candidates.sort(key=lambda x: -x[1])
        
        all_candidates = list(set(synonyms + [w for w, _ in pmi_candidates[:20]] + old_alts))
        
        # 2. AddCos 排序
        contexts = hc3_contexts.get(ai_word, [])[:5]  # 取 5 个上下文
        ctx_words = []
        for ctx in contexts:
            ctx_words.extend(ctx.split())
        
        scored = []
        for cand in all_candidates:
            score = compute_addcos(cand, ai_word, ctx_words)
            scored.append((cand, score))
        scored.sort(key=lambda x: -x[1])
        
        # 3. 过滤 + 取 Top-5
        top = [w for w, s in scored[:5] if s > 0.3]
        if len(top) >= 2:
            expanded[ai_word] = top
    
    return expanded
```

### 7.5 语境触发词扩充计划

**目标**: 为每个语境检查（情感/语体/discourse relation）建立**可扩充的触发词库**。

**统一架构**（已在 §2.1 `rewrite_context.py` 实现）：
- 所有触发词存 `scripts/weights/*.json`
- `_load_lexicon(name)` 懒加载 + 模块级缓存
- 词典格式统一：`{category: [words]}`

**扩充流程**：
1. **种子词**：人工整理 20-30 词/类
2. **自动化扩展**（参考 Wang 2021）：
   - 从 HC3 + 长文本语料计算 SO-PMI
   - 阈值过滤 + K-means++ 聚类
3. **人工 review**：抽样 10% 验证
4. **版本化**：`weights/v2026Q3/` 备份，支持回退

---

## 八、Phase 1 实施时间表

| 任务 | 工作量 | 依赖 | 输出 |
|------|--------|------|------|
| 8.1 编写 `rewrite_context.py` 框架 | 1 天 | 无 | 200 行 Python + 4 词典骨架 |
| 8.2 构建 `sentiment_lexicon.json` | 0.5 天 | 8.1 | ~5KB 词典 |
| 8.3 构建 `discourse_markers.json` | 0.5 天 | 8.1 | ~2KB 词典 |
| 8.4 构建 `register_markers.json` | 0.5 天 | 8.1 | ~3KB 词典 |
| 8.5 构建 `protected_terms.json`（种子+SO-PMI） | 2 天 | 8.1 | ~10KB 词典 + `build_protected_terms.py` |
| 8.6 P1-1 实现 + 单元测试 | 1 天 | 8.1-8.3 | `fragment_injection` / `burstiness_engineering` 重写 |
| 8.7 P1-2 实现 + 单元测试 | 0.5 天 | 无 | `punctuation_humanize` 省略号部分重写 |
| 8.8 P1-3 实现 + 单元测试 | 0.5 天 | 8.4-8.5 | `ai_vocab_scrub` 术语保护集成 |
| 8.9 P1-4 实现 + 单元测试 | 0.5 天 | 无 | `humanize_cn.py` Pass 5 语义预算 |
| 8.10 集成测试 | 1 天 | 8.6-8.9 | 跑 [semantic_check.py](file:///d:/working/0001/humanize-chinese-dimension/dev/semantic_check.py) 105 篇 |
| 8.11 HC3 benchmark 回归 | 0.5 天 | 8.10 | 跑 `run_hc3_benchmark.py --n 200` |
| 8.12 跨版本对比 + 文档更新 | 0.5 天 | 8.11 | 更新 [改写端未来计划.md](file:///d:/working/0001/humanize-chinese-dimension/dev/reports/改写端未来计划.md) |

**总计**: ~9 个工作日

---

## 九、验证与测试方案

### 9.1 单元测试

新增 `tests/test_rewrite_context.py` + `tests/test_phase1_ops.py`：

```python
# tests/test_rewrite_context.py
class TestSentimentOfSentence(unittest.TestCase):
    def test_positive(self):
        assert sentiment_of_sentence("爷爷主动承担起了照顾我的责任") == 'positive'
    
    def test_negative(self):
        assert sentiment_of_sentence("失去了那份纯粹快乐") == 'negative'
    
    def test_neutral(self):
        assert sentiment_of_sentence("本研究生成了实验数据") == 'neutral'
    
    def test_negation(self):
        assert sentiment_of_sentence("不太开心") == 'negative'  # 否定翻转


class TestIsProtectedTerm(unittest.TestCase):
    def test_medical(self):
        assert is_protected_term("PKM2", 'medical') == True
        assert is_protected_term("丙酮酸激酶", 'medical') == True
    
    def test_legal(self):
        assert is_protected_term("数据隐私", 'legal') == True
    
    def test_not_protected(self):
        assert is_protected_term("苹果", None) == False


class TestIsSafeSplitPoint(unittest.TestCase):
    def test_conjunction_internal(self):
        # "细胞代谢、增殖及凋亡" 中 、后是"增殖及凋亡"，含"及"→ 不安全
        sent = "细胞代谢、增殖及凋亡中的角色"
        assert is_safe_split_point(sent, 4) == False  # 、在 index 4
    
    def test_normal_comma(self):
        sent = "人工智能技术，正在改变着社会"
        assert is_safe_split_point(sent, 7) == True


# tests/test_phase1_ops.py
class TestFragmentInjection(unittest.TestCase):
    def test_no_fragment_in_medical(self):
        text = "本研究揭示了 PKM2 在肿瘤细胞中的复杂功能。"
        result = fragment_injection(text, intensity=1.0, seed=42)
        assert "也是奇怪" not in result
        assert "真的" not in result
    
    def test_fragment_after_positive(self):
        text = "成效显著。这一进展令人振奋。"
        result = fragment_injection(text, intensity=1.0, seed=42)
        # positive 情感后应插 comment_positive 或 hedge
        assert any(frag in result for frag in ['颇有看点', '势头不错', '未必', '难说'])


class TestPunctuationHumanize(unittest.TestCase):
    def test_no_ellipsis_after_conclusion(self):
        text = "综上，我们确保了实验的可靠性。"
        result = punctuation_humanize(text, intensity=1.0, seed=42)
        assert "……" not in result
    
    def test_ellipsis_after_enum(self):
        text = "比如苹果、香蕉、橘子等。"
        result = punctuation_humanize(text, intensity=1.0, seed=42)
        assert "……" in result
```

### 9.2 集成测试

```bash
# 1. 跑现有语义完整性检查
python dev/semantic_check.py
# 期望: Adaptive 正常率从 96% → ≥ 99%

# 2. HC3-Chinese 200 样本回归
python evals/run_hc3_benchmark.py --n 200 --seed 42
# 期望: 平均降幅不降反升（从 40.6 分 → ≥ 40 分，不回退即可）

# 3. 长文本 benchmark
python evals/run_longform_benchmark.py --n-human 60 --seed 42 --best-of-n 20
# 期望: 段落保留率 100%

# 4. 跨版本对比
python dev/cross_version_test.py
# 期望: 短文本（107 字日常随笔）降幅 ≥ 旧版

# 5. 人工抽检
# 重跑 [semantic_check_articles.md](file:///d:/working/0001/humanize-chinese-dimension/dev/reports/semantic_check_articles.md) 5 篇
# 期望: 无"碎片断词/情感错位/省略号滥用"
```

### 9.3 回归门槛

Phase 1 合并前必须满足：

| 指标 | 旧版 | Phase 1 目标 |
|------|------|-------------|
| Adaptive 正常率 | 96% | ≥ 99% |
| HC3 平均降幅 | 40.6 分 | ≥ 40 分（不回退） |
| 长文本段落保留率 | 100% | 100% |
| "碎片断词"出现率 | ~15% | < 1% |
| "省略号滥用"出现率 | ~20% | < 5% |
| 术语误替换率 | ~5% | 0% |

---

## 十、关键约束再强调

1. **零外部依赖**: 仅 jieba；所有新词典 JSON 内嵌 `scripts/weights/`
2. **语义优先**: P1-4 语义预算是硬约束，操作累计代价不超过 40%
3. **反对攻击式改写**: 不把检测器当 oracle；P1-1/P1-2/P1-3 都是语义保护，不是降分手段
4. **每个操作带安全边界**: 语境触发 + 频率上限 + 情感/语体一致性
5. **可复现**: 所有阈值在 HC3 上校准；`--seed` 保证复现
6. **向后兼容**: `--adaptive` / `--best-of-n` 等参数行为只增强不削弱
7. **词典可扩充**: 所有触发词库用统一 JSON 格式，支持后续 SO-PMI 自动扩展

---

## 十一、参考文献

### 学术论文（Phase 1 直接引用）

1. Biran, O., Brody, S., & Elhadad, N. (2011). *Putting it Simply: a Context-Aware Approach to Lexical Simplification*. ACL 2011. [Columbia](http://www.cs.columbia.edu/~orb/papers/simplification_acl_2011.pdf) — context-aware 替换的 Word-Sentence Similarity + context rules
2. Vladika, J., Meisenbacher, S., & Matthes, F. (2025). *Lexical Substitution is not Synonym Substitution: On the Importance of Producing Contextually Relevant Word Substitutes*. arXiv 2502.04173. [arxiv](https://arxiv.org/html/2502.04173v1) — 候选必须语境相关
3. Hawker, T. (2007). *USYD: WSD and Lexical Substitution using the Web1T Corpus*. SemEval 2007. [ACL](https://aclanthology.org/S07-1100.pdf) — PMI-based substitutability
4. Bolshakov, I. A. (2004). *Synonymous paraphrasing using electronic dictionaries*. [ACL](https://preview.aclanthology.org/manual-author-scripts/C10-1141.pdf) — n-gram 归一化频率排序
5. Melamud, O., et al. (2015). *A Simple Word Embedding Model for Lexical Substitution*. EMNLP. — AddCos 公式
6. Gu, L., & Pan, Y. (2021). *A Comparative Study of Collocation Extraction Methods*. PACLIC 2021. [ACL](https://aclanthology.org/2021.paclic-1.21.pdf) — MI3 中文搭配抽取
7. Wang, Q., et al. (2021). *Extending emotional lexicon for improving the classification accuracy of Chinese film reviews*. Connection Science, 33(2). [Taylor & Francis](https://www.tandfonline.com/doi/full/10.1080/09540091.2020.1782839) — K-means++ + SO-PMI 词典扩展
8. Liang, L., & Tian, F. (2020). *Using normal dictionaries to extract multiple semantic relationships*. IET The Journal of Engineering. [IET](https://ietresearch.onlinelibrary.wiley.com/doi/full/10.1049/joe.2019.1212) — 词典释义递归抽取语义关系
9. Lacerra, C., et al. (2021). *ALaSca: an Automated Approach for Large-Scale Lexical Substitution*. IJCAI 2021. [IJCAI](https://www.ijcai.org/proceedings/2021/0528.pdf) — 大规模替换语料自动构建
10. Seneviratne, S., et al. (2022). *CILex: An Investigation of Context Information for Lexical Substitution Methods*. COLING 2022. [ACL](https://aclanthology.org/2022.coling-1.362.pdf) — 词典 + 上下文混合
11. Abualhaija, S., et al. (2017). *Metaheuristic Approaches to Lexical Substitution and Simplification*. EACL 2017. [ACL](https://aclanthology.org/E17-1082.pdf) — D-Bees / 模拟退火 WSD
12. Grosz, B. J., Joshi, A. K., & Weinstein, S. (1995). *Centering: A Framework for Modeling the Local Coherence of Discourse*. ACL Journal. [J95-4004](https://aclanthology.org/J95-4004.pdf) — Centering Theory

### 项目内已有资源

13. [scripts/rewrite_operations.py](file:///d:/working/0001/humanize-chinese-dimension/scripts/rewrite_operations.py) — 6 个改写操作
14. [scripts/humanize_cn.py](file:///d:/working/0001/humanize-chinese-dimension/scripts/humanize_cn.py) — Pass 5 集成
15. [scripts/weights/cilin_synonyms.json](file:///d:/working/0001/humanize-chinese-dimension/scripts/weights/cilin_synonyms.json) — 38873 词同义词林
16. [scripts/weights/ngram_freq_cn.json](file:///d:/working/0001/humanize-chinese-dimension/scripts/weights/ngram_freq_cn.json) — 字符 3-gram 频率
17. [dev/semantic_check.py](file:///d:/working/0001/humanize-chinese-dimension/dev/semantic_check.py) — 语义完整性检查
18. [dev/reports/semantic_check_articles.md](file:///d:/working/0001/humanize-chinese-dimension/dev/reports/semantic_check_articles.md) — 105 篇真实改写案例

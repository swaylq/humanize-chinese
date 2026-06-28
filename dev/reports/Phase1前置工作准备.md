# Phase 1 前置工作准备

> **基于**: [dev/reports/改写端Phase1详细实现.md](file:///d:/working/0001/humanize-chinese-dimension/dev/reports/改写端Phase1详细实现.md)
> **日期**: 2026-06-26
> **状态**: 前置准备中，未正式开始改动生产代码
> **范围**: 整合用户想法 + 术语保护分支集成评估 + 实施步骤安排

---

## 一、用户想法汇总与对齐

### 1.1 用户明确的需求

| # | 用户想法 | 对应 Phase 1 文档 | 调整 |
|---|---------|------------------|------|
| U1 | `_FRAGMENTS` 进行分类和扩充 | §3.2.1 `_FRAGMENTS_BY_RELATION` 7 类 | 保持，需扩充词表 |
| U2 | 省略号滥用**直接砍掉**乱添加省略号的代码 | §4 P1-2 语境触发 | **调整**：从"语境触发"改为"直接砍掉省略号添加逻辑" |
| U3 | 术语保护用之前的分支 `protect-terms-simple` | §5 P1-3 自建 `protected_terms.json` | **调整**：改用分支现成的 `_humanize_protect.py` + `mini_dict.json`（68K 术语） |
| U4 | 不影响 academic 部分功能 | — | 约束确认：所有改动只影响 general 流程 |
| U5 | 语义完整度检查方案，独立简单测试脚本 | §9 验证方案 | **已交付**：[dev/semantic_integrity_check.py](file:///d:/working/0001/humanize-chinese-dimension/dev/semantic_integrity_check.py) |
| U6 | 先安排计划，前置工作准备后再正式改动 | — | 本文档即前置准备 |

### 1.2 与原 Phase 1 计划的差异

| 项 | 原 Phase 1 计划 | 用户调整后 |
|----|---------------|-----------|
| P1-2 省略号 | 语境触发（OK 词 + FORBIDDEN 词） | **直接砍掉** `punctuation_humanize` 第 451-458 行省略号添加代码 |
| P1-3 术语保护 | 自建 `protected_terms.json`（~10KB）+ SO-PMI 扩展 | **集成分支** `_humanize_protect.py` + `mini_dict.json`（4.7MB，68K 术语） |
| P1-1 碎片分类 | 7 类 DM 词表 + 情感一致性 | 保持，需扩充每类候选词 |
| 语义检查脚本 | 在 §9 描述 | **已独立交付**脚本 |

---

## 二、术语保护分支集成评估

### 2.1 分支已 clone 到本地

- **路径**: `d:\working\humanize-chinese-protect-terms-simple`（注意：`..` 解析到 `d:\working\`，不在 `0001\` 下）
- **分支**: `protect-terms-simple`
- **来源**: https://github.com/Asami-Lilith/humanize-chinese/tree/protect-terms-simple

### 2.2 分支关键资产

| 文件 | 体积 | 作用 |
|------|------|------|
| `scripts/_humanize_protect.py` | 9.4KB | 术语保护层模块（ProtectLayer 类） |
| `scripts/data/mini_dict.json` | 4.7MB | ~68K 术语扁平列表（9 个技术领域） |
| `scripts/download_full_dict.py` | 7.4KB | 下载完整 DomainWordsDict（升级到 full mode） |
| `scripts/_domain_dict_convert.py` | 6.1KB | 词典格式转换工具 |
| `scripts/_gen_all_dicts.py` | 8.3KB | 生成所有领域词典 |

### 2.3 分支的术语保护设计

**`_humanize_protect.py` 核心结构**：

```python
class ProtectLayer:
    # 两种模式:
    #   mini (默认): 加载 data/mini_dict.json, bisect 二分查找, 无领域评分
    #   full (需外部缓存): 加载 data/DomainWordsDict/*.json, 按领域+权重
    
    def extract_protected_terms(self, text, ...):
        # mini 模式: 返回所有在 text 中匹配的 mini_dict 术语
        # full 模式: 先 detect_domains, 再按领域+权重过滤
```

**集成到 `humanize_cn.py` 的方式**（分支已实现）：

| 位置 | 代码 | 作用 |
|------|------|------|
| 第 26-29 行 | `_USE_PROTECT_FLAG = False` + `_PROTECTION_SET = set()` | 模块级全局变量 |
| 第 3310 行 | `def humanize(..., protect=False):` | 入口函数新增参数 |
| 第 3405-3420 行 | `if protect: from _humanize_protect import get_layer; _PROTECTION_SET = _layer.extract_protected_terms(text)` | 加载保护集 |
| 第 1420-1428 行 | Pass 2 大词替换：计算 `_blocked` 位置集，从 `to_replace` 排除 | 替换时跳过保护术语位置 |
| 第 1544-1547 行 | Pass 4 另一个保护点 | 同上 |
| 第 3636 行 | `parser.add_argument('--protect', ...)` | CLI flag |
| 第 3688 行 | `protect=args.protect` | 透传 |

### 2.4 集成冲突分析

#### 冲突 1：词典路径

| 项 | 分支 | 我们项目 |
|----|------|---------|
| `mini_dict.json` 位置 | `scripts/data/mini_dict.json` | 无 `scripts/data/` 目录 |
| 词典集中管理 | `scripts/` 根目录 + `scripts/data/` | `scripts/weights/`（11 个 JSON） |
| `cilin_synonyms.json` 位置 | `scripts/cilin_synonyms.json` | `scripts/weights/cilin_synonyms.json` |

**方案**：保持分支原路径 `scripts/data/mini_dict.json`。
- 理由 1：`_humanize_protect.py` 硬编码此路径，不改代码
- 理由 2：4.7MB 大文件不混入 `weights/` 的轻量词典
- 理由 3：`data/` 目录语义清晰（大数据文件）

#### 冲突 2：模块导入路径

`_humanize_protect.py` 在 `scripts/`，我们的 `rewrite_operations.py` 也在 `scripts/`，路径一致，**无冲突**。

#### 冲突 3：全局变量传递

分支用 `humanize_cn.py` 模块级全局变量 `_USE_PROTECT_FLAG` + `_PROTECTION_SET` 传递保护集。但我们的 Pass 5 操作（`ai_vocab_scrub` 等）在 `rewrite_operations.py` 里，**无法直接访问 humanize_cn.py 的全局变量**。

**方案 A（推荐）**：把保护集作为参数传给 `ai_vocab_scrub`
- 改动：`ai_vocab_scrub(text, intensity, seed, replacements, protected_set=None)`
- 在 `humanize_cn.py` Pass 5 调用时传 `_PROTECTION_SET`
- 优点：无侵入，函数签名清晰
- 缺点：需改 `rewrite_operations.py` 的 `ai_vocab_scrub` 签名

**方案 B**：在 `rewrite_operations.py` 也导入 `_humanize_protect` 自己维护一份
- 缺点：4.7MB 词典加载两次，浪费内存
- 否决

**方案 C**：通过 `humanize_cn.py` Pass 5 的 `_ro_params` 字典附带保护集
- 改动：`_ro_params['_protected_set'] = _PROTECTION_SET`
- 在 `ai_vocab_scrub` 调用前取出
- 缺点：`_ro_params` 语义被污染
- 备选

**采用方案 A**。

#### 冲突 4：CLI flag 透传

我们项目用 `humanize.py` 分发到 `humanize_cn.py`。

| 项 | 分支 | 我们项目 |
|----|------|---------|
| CLI 入口 | `humanize_cn.py` 直接 argparse | `humanize.py` 分发 + `humanize_cn.py` argparse |
| `--protect` flag | 在 `humanize_cn.py` 第 3636 行 | 需在 `humanize.py` 加透传 + `humanize_cn.py` 加 flag |

**方案**：
1. `humanize_cn.py` 保持分支的 `--protect` flag（第 3636 行 + 第 3688 行）
2. `humanize.py` 的 `rewrite` 子命令加 `--protect` 透传（分发器模式）
3. `academic_cn.py` **不加** `--protect`（用户要求不影响 academic）

#### 冲突 5：academic 流程

用户明确"暂时先不管 academic 部分的改动，仅保证当前改动不会让其功能出现问题"。

**方案**：
- `academic_cn.py` **不导入** `_humanize_protect`
- `academic_cn.py` 不加 `--protect` flag
- `humanize_cn.py` Pass 5 的 `_PROTECTION_SET` 是模块级全局，`academic_cn.py` 不走 Pass 5（它有自己的管线），**不会受影响**
- 验证：academic 流程调用 `humanize_cn` 的共享函数（`reduce_high_freq_bigrams` / `inject_noise_expressions` / `randomize_sentence_lengths`）时，这些函数**不读** `_USE_PROTECT_FLAG`（只有 Pass 2/4 读），所以 academic 不受影响

#### 冲突 6：mini_dict.json 体积

4.7MB 入库会增大仓库。

**方案**：
- **方案 A**：入 gitignore，提供 `download_full_dict.py` 下载（分支已有此脚本）
- **方案 B**：入库（4.7MB 可接受，一次性）
- **方案 C**：Git LFS

**推荐方案 A**：入 gitignore + 下载脚本。理由：
- 与项目"轻量"理念一致
- 分支已有 `download_full_dict.py` 可复用
- 用户可按需下载
- `humanize doctor` 可检查词典状态

### 2.5 集成步骤清单

| 步骤 | 操作 | 冲突点 |
|------|------|--------|
| S1 | 复制 `_humanize_protect.py` 到 `scripts/` | 无 |
| S2 | 复制 `mini_dict.json` 到 `scripts/data/`（需建目录） | 冲突 1 |
| S3 | `.gitignore` 加 `scripts/data/mini_dict.json` | 冲突 6 |
| S4 | 复制 `download_full_dict.py` 到 `scripts/`（可选） | 无 |
| S5 | `humanize_cn.py` 加 `_USE_PROTECT_FLAG` / `_PROTECTION_SET` 全局变量 + `humanize(protect=False)` 参数 + 第 3405-3420 行加载逻辑 + Pass 2/4 保护点 | 冲突 3 |
| S6 | `rewrite_operations.py` 的 `ai_vocab_scrub` 加 `protected_set=None` 参数 | 冲突 3 方案 A |
| S7 | `humanize_cn.py` Pass 5 调用 `ai_vocab_scrub` 时传 `protected_set=_PROTECTION_SET` | 冲突 3 方案 A |
| S8 | `humanize.py` 的 `rewrite` 子命令加 `--protect` 透传 | 冲突 4 |
| S9 | `humanize doctor` 加 mini_dict.json 状态检查 | 冲突 6 |
| S10 | 不动 `academic_cn.py` | 冲突 5 |

---

## 三、P1-2 调整：省略号直接砍掉

### 3.1 用户决定

用户明确："省略号滥用的问题可能需要直接砍掉乱添加省略号的代码"。

### 3.2 砍掉范围

[rewrite_operations.py](file:///d:/working/0001/humanize-chinese-dimension/scripts/rewrite_operations.py) `punctuation_humanize` 第 451-458 行：

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

**直接删除这 8 行**。

### 3.3 理由

- 省略号的语用功能是"未尽/沉思/留白"，学术/公文/新闻几乎不用
- 当前实现是"降低句号密度的工具"，完全错配
- 语境触发（原 P1-2 方案）实现成本高，且仍然可能误加
- 直接砍掉最安全：**不主动加省略号**，原文有省略号则保留

### 3.4 影响评估

| 流程 | 影响 |
|------|------|
| general adaptive | 不再出现"势头不错……""确保了实验的可靠性……" |
| general 非 adaptive | `punctuation_humanize` 不在非 adaptive 路径调用，无影响 |
| academic | `academic_cn.py` 不调 `punctuation_humanize`，无影响 |
| style 转换 | 取决于是否走 Pass 5；若走则同样不再加省略号 |

### 3.5 保留部分

`punctuation_humanize` 的另外两部分**保留**：
- 第 426-437 行：降低逗号句号比（部分逗号改句号）
- 第 439-449 行：问句末尾加问号

这两部分是合理的标点人性化，不删。

---

## 四、P1-1 调整：_FRAGMENTS 分类与扩充

### 4.1 分类结构（保持 Phase 1 文档设计）

```python
_FRAGMENTS_BY_RELATION = {
    'hedge':              ['未必如此。', '也难讲。', ...],
    'comment_neutral':    ['看起来是这样。', '有这个说法。', ...],
    'comment_surprise':   ['也是奇怪。', '说来也怪。', ...],
    'comment_positive':   ['颇有看点。', '势头不错。', ...],
    'comment_negative':   ['没什么大不了的。', '算了。', ...],
    'comment_termination': ['就这样。', '到此为止。', ...],
    'contrast':           ['其实不然。', '话又说回来。', ...],
}
```

### 4.2 扩充计划

每类从当前 ~3 条扩充到 **8-12 条**，保证多样性。扩充原则：

1. **语用功能纯一**：每类只含该类语用功能的碎片
2. **情感极性一致**：`comment_positive` 全部 positive，`comment_negative` 全部 negative
3. **语体中性**：避免过于口语化（如"绝了"）或过于书面（如"诚然"）
4. **长度 2-6 字**：保持碎片特性
5. **不含术语**：避免与 protected_terms 冲突

### 4.3 扩充后的词表（草案）

```python
_FRAGMENTS_BY_RELATION = {
    'hedge': [
        '未必如此。', '也难讲。', '不一定。', '看情况。', '难说。',
        '未必。', '不好说。', '说不准。', '也未必。', '未必尽然。',
    ],
    'comment_neutral': [
        '看起来是这样。', '有这个说法。', '也是。', '也正常。',
        '说来也是。', '算是吧。', '可以这么看。', '有道理。',
    ],
    'comment_surprise': [
        '也是奇怪。', '说来也怪。', '怪了。', '有意思。',
        '说来奇怪。', '也颇有意思。',
    ],
    'comment_positive': [
        '颇有看点。', '势头不错。', '成效不小。', '影响不小。',
        '前景看好。', '空间不小。', '颇有意思。', '算是个亮点。',
    ],
    'comment_negative': [
        '没什么大不了的。', '算了。', '无所谓了。', '就这样吧。',
        '也无所谓。', '不必在意。', '倒也未必。',
    ],
    'comment_termination': [
        '就这样。', '到此为止。', '说完了。', '先这样。',
        '暂且如此。', '先说到这。',
    ],
    'contrast': [
        '其实不然。', '话又说回来。', '换个角度看。', '话说回来。',
        '未必如此。', '也未必。', '反过来想。',
    ],
}
```

### 4.4 选择算法（保持 Phase 1 文档 §3.2.2）

`_pick_fragment(relation, sentiment, allow_comment, rng)`：
- academic/legal/medical 语体 + relation=unknown → 只允许 hedge
- contrast 关系 → contrast 类
- positive 情感 → comment_positive
- negative 情感 → comment_negative
- neutral → comment_neutral + hedge 混合
- fallback → hedge

---

## 五、语义完整度检查脚本（已交付）

### 5.1 脚本位置

[dev/semantic_integrity_check.py](file:///d:/working/0001/humanize-chinese-dimension/dev/semantic_integrity_check.py)（~340 行，零依赖）

### 5.2 理论依据

| 维度 | 来源 |
|------|------|
| 多维评估框架 | ICLR 2026 *Towards Human-Preferences Chinese Rewriting Evaluation*（semantic consistency + syntactic structure + lexical variation + stylistic fidelity） |
| 语义保持评估 | MeaningBERT (Frontiers in AI 2023) — 指出 BLEU/SARI 与人类判断相关性差 |
| BERTScore 零依赖近似 | Zhang 2020 BERTScore → 用字符 n-gram Jaccard 替代上下文嵌入 |
| 语义保持硬过滤 | REPRO (arXiv 2510.10681 2025) — BERTScore ≥ τ 做硬过滤 |

### 5.3 10 个维度

| # | 维度 | 含义 | 阈值 |
|---|------|------|------|
| 1 | length_ratio | 改写/原文字符数比 | 0.5-1.5 |
| 2 | char_overlap | 字符保留率 | ≥0.6 |
| 3 | word_overlap | 词保留率 | ≥0.5 |
| 4 | keyword_retention | TF Top-K 关键词保留率 | ≥0.7 |
| 5 | bigram_jaccard | 字符 2-gram Jaccard | — |
| 6 | trigram_jaccard | 字符 3-gram Jaccard | ≥0.2 |
| 7 | paragraph_ratio | 段落数比 | 0.5-2.0 |
| 8 | sentence_ratio | 句子数比 | — |
| 9 | synonym_coverage | 词林同义覆盖（可选） | — |
| 10 | protected_term_retention | 术语保留（可选） | =1.0 |

外加标点异常检测：省略号滥用 / 碎片断词 / 双标点 / 空句 / 感叹号滥用。

### 5.4 用法

```bash
# 单文件检查
python dev/semantic_integrity_check.py --orig orig.txt --rewrite rewritten.txt

# JSON 输出（便于管道）
python dev/semantic_integrity_check.py -o orig.txt -r rewritten.txt --json

# 详细模式（含改进建议）
python dev/semantic_integrity_check.py -o orig.txt -r rewritten.txt -v
```

### 5.5 退出码

- 0 = ok / suspicious
- 1 = failed（语义严重破坏）
- 2 = 参数错误

### 5.6 与现有 `dev/semantic_check.py` 的关系

| 项 | `dev/semantic_check.py`（现有） | `dev/semantic_integrity_check.py`（新） |
|----|-------------------------------|--------------------------------------|
| 设计目标 | 跑 fdgpt_scored_results.json 批量检查 | 独立单文件/双文件检查 |
| 依赖 | 依赖 fdgpt 结果 JSON | 零依赖 |
| 维度 | 5 维（len/char/word/para/sent） | 10 维 + 标点异常 |
| 标点异常 | 无 | 有（省略号/碎片断词/双标点） |
| 关键词 | 无 | TF Top-K |
| 术语保留 | 无 | 有（需 protected_terms.json） |
| 同义覆盖 | 无 | 有（需 cilin_synonyms.json） |
| 输出 | 改写 JSON + articles.md | stdout / JSON |

**两者共存**：`semantic_check.py` 用于批量回归（fdgpt 路径），`semantic_integrity_check.py` 用于开发时快速验证单 case。

---

## 六、实施步骤安排

### 6.1 前置工作（已完成）

| # | 任务 | 状态 | 产出 |
|---|------|------|------|
| F1 | clone 术语保护分支 | ✅ 完成 | `d:\working\humanize-chinese-protect-terms-simple` |
| F2 | 评估术语保护集成冲突 | ✅ 完成 | 本文 §2 |
| F3 | 语义完整度检查脚本 | ✅ 完成 | [dev/semantic_integrity_check.py](file:///d:/working/0001/humanize-chinese-dimension/dev/semantic_integrity_check.py) |
| F4 | 实施步骤安排 | ✅ 完成 | 本文 §6 |

### 6.2 正式改动（待用户确认后启动）

#### 阶段 A：术语保护集成（独立可测）

| # | 任务 | 文件 | 依赖 |
|---|------|------|------|
| A1 | 复制 `_humanize_protect.py` 到 `scripts/` | 新文件 | F1 |
| A2 | 创建 `scripts/data/` 目录 + 复制 `mini_dict.json` | 新文件 | A1 |
| A3 | `.gitignore` 加 `scripts/data/mini_dict.json` | `.gitignore` | A2 |
| A4 | `humanize_cn.py` 加全局变量 + `protect` 参数 + 加载逻辑 | `humanize_cn.py` | A1 |
| A5 | `humanize_cn.py` Pass 2/4 加保护点（从分支移植） | `humanize_cn.py` | A4 |
| A6 | `rewrite_operations.py` `ai_vocab_scrub` 加 `protected_set` 参数 | `rewrite_operations.py` | A4 |
| A7 | `humanize_cn.py` Pass 5 调用 `ai_vocab_scrub` 传 `protected_set` | `humanize_cn.py` | A6 |
| A8 | `humanize.py` `rewrite` 子命令加 `--protect` 透传 | `humanize.py` | A4 |
| A9 | `humanize doctor` 加 mini_dict 状态检查 | `humanize.py` 或 `check_assets.py` | A2 |
| A10 | 单元测试：`--protect` 启用后术语不被替换 | `tests/` | A8 |

**验证**：跑 `semantic_integrity_check.py` 对比 `--protect` on/off 的 `protected_term_retention` 维度。

#### 阶段 B：_FRAGMENTS 分类 + 省略号砍掉（独立可测）

| # | 任务 | 文件 | 依赖 |
|---|------|------|------|
| B1 | 替换 `_FRAGMENTS` 单列表为 `_FRAGMENTS_BY_RELATION` 7 类 | `rewrite_operations.py` | 无 |
| B2 | 扩充每类到 8-12 条（§4.3 草案） | `rewrite_operations.py` | B1 |
| B3 | 新增 `_pick_fragment(relation, sentiment, allow_comment, rng)` | `rewrite_operations.py` | B2 |
| B4 | 重写 `fragment_injection`：语境感知选碎片（§3.2.2 算法） | `rewrite_operations.py` | B3 |
| B5 | 重写 `burstiness_engineering`：`is_safe_split_point` 约束 + 拆点不插碎片 | `rewrite_operations.py` | B4 |
| B6 | **直接砍掉** `punctuation_humanize` 第 451-458 行省略号添加代码 | `rewrite_operations.py` | 无 |
| B7 | 单元测试：碎片不再断词、省略号不再被主动添加 | `tests/` | B5, B6 |

**验证**：跑 `semantic_integrity_check.py` 对比改前改后的 `punctuation_issues` 维度。

#### 阶段 C：语境检查框架（可延后）

| # | 任务 | 文件 | 依赖 |
|---|------|------|------|
| C1 | 新增 `rewrite_context.py`（情感/语体/discourse relation/拆点安全） | 新文件 | 无 |
| C2 | 构建 `sentiment_lexicon.json` | 新词典 | C1 |
| C3 | 构建 `discourse_markers.json` | 新词典 | C1 |
| C4 | 构建 `register_markers.json` | 新词典 | C1 |
| C5 | `fragment_injection` 集成 `rewrite_context` 检查 | `rewrite_operations.py` | C1-C4, B4 |
| C6 | 单元测试：情感错位 case（如"爷爷"段落禁插"没什么大不了"） | `tests/` | C5 |

**注**：阶段 C 可延后到 Phase 2。阶段 A+B 已能解决用户最关心的问题（术语保护 + 省略号滥用 + 碎片断词）。

#### 阶段 D：Adaptive 语义预算（可延后）

| # | 任务 | 文件 | 依赖 |
|---|------|------|------|
| D1 | `_compute_adaptive_params` 语义预算算法 | `humanize_cn.py` | 无 |
| D2 | Pass 5 替换强制下限逻辑 | `humanize_cn.py` | D1 |
| D3 | 短文本长度分流 | `humanize_cn.py` | D1 |
| D4 | 单元测试：短文本不走结构操作 | `tests/` | D3 |

**注**：阶段 D 可延后到 Phase 2。

### 6.3 验证流程（每阶段完成后）

```bash
# 1. 单元测试
PYTHONHASHSEED=0 python -m unittest discover tests/

# 2. 语义完整度（开发时快速验证）
python dev/semantic_integrity_check.py --orig examples/sample_academic.txt --rewrite out.txt -v

# 3. 现有语义检查（批量回归，需 fdgpt 结果）
python dev/semantic_check.py

# 4. HC3 benchmark
python evals/run_hc3_benchmark.py --n 200 --seed 42

# 5. 跨版本对比
python dev/cross_version_test.py
```

---

## 七、待用户确认的决策点

在正式开始改动前，请确认以下决策：

### 决策 1：术语保护词典入库方式

| 选项 | 说明 |
|------|------|
| A. 入 gitignore + 下载脚本（推荐） | 4.7MB 不入库，`download_full_dict.py` 按需下载，`humanize doctor` 检查 |
| B. 直接入库 | 4.7MB 入仓库，clone 即用，但仓库变大 |
| C. Git LFS | 需配 LFS，复杂 |

### 决策 2：阶段 C/D 是否本轮做

| 选项 | 说明 |
|------|------|
| A. 本轮只做阶段 A+B（推荐） | 术语保护 + 碎片分类 + 省略号砍掉，立即见效 |
| B. 本轮做 A+B+C | 加语境检查框架，需构建 3 个词典 |
| C. 本轮做 A+B+C+D | 加语义预算，最完整但工作量大 |

### 决策 3：_FRAGMENTS 扩充词表是否需要人工 review

| 选项 | 说明 |
|------|------|
| A. 直接用 §4.3 草案 | 我已整理 7 类 ~50 条 |
| B. 草案 + 人工 review | 你过一遍草案，删改后再入库 |
| C. 自动化扩充 | 用 SO-PMI 从语料扩展（Phase 2 方案，工作量大） |

### 决策 4：术语保护默认开关

| 选项 | 说明 |
|------|------|
| A. 默认关闭，需 `--protect` 显式启用（分支原设计） | 与分支一致，向后兼容 |
| B. 默认开启，`--no-protect` 关闭 | 保护更彻底，但可能影响降幅 |
| C. adaptive 模式默认开，非 adaptive 默认关 | 折中 |

---

## 八、风险与缓解

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| mini_dict.json 4.7MB 加载慢 | 中 | 首次 humanize 慢 ~1s | 模块级单例 + import 时预加载（分支已实现） |
| 术语保护过度，降幅缩小 | 中 | HC3 benchmark 分数下降 | `--protect` 默认关闭，用户按需启用 |
| `_FRAGMENTS` 分类后某些类候选太少 | 低 | 碎片多样性下降 | 每类扩充到 8-12 条（§4.3） |
| 砍省略号后某些场景反而不像人 | 低 | 小红书风格可能需要省略号 | `style_cn.py` 可独立处理，不受影响 |
| 全局变量 `_PROTECTION_SET` 非线程安全 | 低 | CLI 单进程无影响 | 文档注明不支持并发 |
| academic 流程意外受影响 | 低 | academic 不走 Pass 5，不读全局变量 | 验证：`academic_cn.py` 不导入 `_humanize_protect` |

---

## 九、关键约束再强调

1. **零外部依赖**：仅 jieba；`_humanize_protect.py` 纯 Python + json + bisect，无新依赖
2. **不影响 academic**：所有改动只影响 general 流程的 adaptive 模式
3. **语义优先**：术语保护是硬约束，降分是软目标
4. **向后兼容**：`--protect` 默认关闭，不启用时行为与现在一致
5. **可复现**：`--seed` 保证复现
6. **可验证**：`semantic_integrity_check.py` 提供独立验证手段

---

## 十、下一步

等待用户确认 §7 的 4 个决策点后，按 §6.2 阶段 A → B → （可选 C/D）顺序启动改动。

**建议先做阶段 A+B**（术语保护 + 碎片分类 + 省略号砍掉），这是用户最关心的三个问题，且独立可测，不依赖语境检查框架。

完成阶段 A+B 后，跑 `semantic_integrity_check.py` + HC3 benchmark 验证效果，再决定是否继续阶段 C+D。

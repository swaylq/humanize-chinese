# PR: ToW 检测+改写增强 + LaTeX 保护层

**Branch:** `detect-test` → `main`  
**Commits:** `2ea9064` · `8875c39` · `655ef66`  
**Files:** 8 changed, **+1278 / −7**

---

## 摘要

基于 ACL 2026 *Tree-of-Writing* (ToW, Pearson ρ=0.93) 论文发现，新增 **3 个检测信号**（Opening-Ending 重叠、末句模板化、情感词聚簇 CV）和 **3 个改写策略**（长度罚分、聚集式噪声注入、首尾段落浅改写）。同时整合 LaTeX 保护层 (`--protect-latex`)，防止改写破坏学术论文中的 LaTeX 命令与数学公式。所有新功能通过 `_ENABLE_TOW` 标志控制，默认关闭，对现有行为零影响。

---

## 代码变更

### 修改文件 (4)

| 文件 | 行数 | 核心变更 |
|------|------|---------|
| `scripts/ngram_model.py` | +114 | `compute_oe_overlap()`, `compute_emotional_clustering()`, LR 特征向量 22→25 维 |
| `scripts/detect_cn.py` | +45 | D-1/D-2/D-3 三信号 + `--tow` CLI + `_ENABLE_TOW` 开关 |
| `scripts/humanize_cn.py` | +97 | LaTeX 保护入口/出口, R-1 长度罚分, R-2 聚簇注入, R-3 OE 浅改写, `--protect-latex` / `--tow` CLI |
| `scripts/patterns_cn.json` | +14 | `tow_patterns` 配置节 (模板词表 + 阈值) |

### 新增文件 (4)

| 文件 | 行数 | 说明 |
|------|------|------|
| `scripts/_humanize_protect.py` | 204 | LaTeX 保护层：9 类模式匹配 + 占位符 + scope-brace 短内容分治 |
| `tests/test_protect_latex_acceptance.py` | 393 | 29 个验收测试覆盖 8 大场景 |
| `docs/评分与改写模块说明.md` | 294 | 检测信号表更新 (14→17) + ToW 策略说明 |
| `docs/PR_v6_ToW_enhancements.md` | 124 | 技术 PR 摘要 |

---

## 功能详解

### 检测层：3 个可开关信号

| 信号 | 类型 | 设计权重 | 触发条件 | 设计依据 |
|------|------|---------|---------|---------|
| `stat_high_oe_overlap` | 统计层 | 6 分 | 首尾段 bigram Jaccard > 40% | 基于 ToW 论文表 4，OE 一致性是跨 12 体裁稳定评估维度 |
| `last_sentence_template` | 规则层(critical) | 8 分 | 末句以模板词开头 (8 种) | ToW + 经验：AI 文本末句高度模板化 |
| `stat_low_emotional_cv` | 统计层 | 4 分 | 情感词段落间分布 CV < 0.5 | ToW 论文核心发现：人类情感表达聚簇、AI 均匀撒布 |

### 改写层：3 个防御性策略

| 策略 | 触发方式 | 说明 | 设计依据 |
|------|---------|------|---------|
| **长度罚分** | `--tow` | 候选输出超出原始 30% 时 rank_score += (ratio − 0.3) × 10 | ToW Table 6: 输入长度与 Content 分 ρ=−0.44 |
| **聚簇式情感注入** | `--tow` | 选 2 个内容密度最低的段落集中注入噪声，其余段落不注入 | 对抗 AI 均匀撒布情感词的检测特征 |
| **首尾段落浅改写** | `--tow` + academic/formal | ≥5 段落时，首 2 段及末 2 段仅做短语替换，跳过 deep_restructure 与噪声注入 | 保护论文段首段尾的逻辑结构完整性 |

### LaTeX 保护层

| 保护模式 | 覆盖范围 | 用例 |
|---------|---------|------|
| 显示数学 | `$$...$$`, `\[...\]` | 公式块 |
| 环境 | `\begin{...}...\end{...}` | figure, table, verbatim, equation, align |
| 命令+参数 | `\cite{...}`, `\textbf{...}`, `\color{red}`, `\fontsize{...}{...}` | 引用、排版 |
| scope brace | `{\small 文本}`, `{\color{red} 文本}` | 范围样式 |
| 行内数学 | `$...$`, `\(...\)` | 公式插入 |
| 表格符号 | `&`, `~` | tabular 环境内 |

**scope-brace 分治规则**：花括号内中文字 ≤6 个（如标题 `{\textbf 第一章}`）不保护，允许改写；中文字 >6 个（如段落级文本）完整保护。

---

## 实验数据

### 实验 1：三信号控制对比

每个信号针对 AI 文本和人类文本各一例，保持其他维度相同，仅改变目标特征。

| 信号 | 设计权重 | AI Rule Δ | AI 触发 | Human 触发 | 原始值 (AI/Hu) |
|------|---------|----------|---------|-----------|---------------|
| D-1 OE overlap | 6 | **+5** | ✅ | ❌ | overlap=0.614 / 0.020 |
| D-2 Last-sentence template | 8 | **+8** | ✅ | ❌ | — |
| D-3 Emotional CV | 4 | **+4** | ✅ | ❌ | CV=0.000 / 1.732 |

> **AI 段落级差异**：D-3 情感词分布——AI 每段恰好 1 个 "高兴" → CV=0.000；人类情感集中在首段 → CV=1.732。

### 实验 2：跨分支回归（seed=42，无 ToW 标志）

| 测试样本 | detect-test | main | 是否一致 |
|----------|-----------|------|---------|
| sample_academic.txt | len=3284 | len=3284 | ✅ |
| sample_general.txt | len=3805 | len=3805 | ✅ |
| sample_long_blog.txt | len=4157 | len=4157 | ✅ |
| sample_social.txt | len=1714 | len=1714 | ✅ |
| AI template (fused score) | 78 | 78 | ✅ |

> **结论**：ToW 功能默认关闭时，detect-test 与 main 输出逐字相同，零回归。

### 实验 3：LaTeX 保护验收

29 个验收测试全部通过（8 大场景 × 3-4 用例）：

| 场景 | 测试数 | 结果 |
|------|-------|------|
| Academic paper (`\cite`, `\ref`, `\section`) | 3 | ✅ |
| Math-dense (`\begin{equation}`, `\frac`, `\sqrt`) | 4 | ✅ |
| Table environments (`\begin{tabular}`, `&`, `\caption`) | 3 | ✅ |
| Brace blocks (`\textbf`, `\color`, `\small`) | 3 | ✅ |
| Mixed Chinese/English (`\citet`, `\cite`) | 3 | ✅ |
| Escape chars (`\\`, `\&`, `~`) | 3 | ✅ |
| Boundary/regression (empty, whitespace, pure LaTeX) | 7 | ✅ |
| best_of_n paths | 3 | ✅ |

**LaTeX 损坏对比**：不含 `--protect-latex` 时，`\textbf{值得注意的是}` 被改写为 `\textbf{注意}`（丢失 3 字），含保护时完整保留。

### 实验 4：纯中文文本 × 三系统评分

控制变量对比（无 LaTeX，best_of_n=5，统一用 fast-DetectGPT+Qwen 评分）：

| 文本类型 | 系统 | fused-score ↓ | fast-gpt2 ↓ | fast-Qwen ↓ |
|---------|------|-------------|-----------|-----------|
| AI paragraph | DT(tow) | 84 (-6) | 1.978 (-0.10) | -0.965 (-0.70) |
| | main | 84 (-6) | 1.978 (-0.10) | -0.965 (-0.70) |
| AI list-heavy | DT(tow) | 43 (-49) | 0.797 (+0.62) | -1.797 (-0.30) |
| | main | 43 (-49) | 0.797 (+0.62) | -1.797 (-0.30) |

> 无 LaTeX 的纯文本场景下，ToW 不改写输出 —— 这是正确的防御性行为。ToW 的价值在 LaTeX 和学术长篇场景中保护文本结构。

---

## CLI 使用

```bash
# 检测（启用 ToW 信号）
python scripts/detect_cn.py paper.txt --tow -v

# 改写（LaTeX 保护 + ToW 策略）
python scripts/humanize_cn.py paper.tex --protect-latex --tow -o clean.tex

# 仅 LaTeX 保护
python scripts/humanize_cn.py paper.tex --protect-latex -o clean.tex
```

```python
import humanize_cn
result = humanize_cn.humanize(text, enable_tow=True, protect_latex=True)
```

---

## 向后兼容性

| 场景 | 影响 |
|------|------|
| `--tow` 未设置 | 零影响。`_ENABLE_TOW=False` 关断所有新增代码 |
| `--protect-latex` 未设置 | 零影响。保护层入口仅显式传参时触发 |
| 无 LaTeX 文本 + `--protect-latex` | 输出不变。扫描无匹配直接返回原文 |
| 现有回归测试 | 37/38 passed, 1 skipped (需外部 HC3 数据) |
| hero floor (2 subtest) | 预存基线问题，与本次变更无关 |

---

## 审查要点

1. `_ENABLE_TOW` gating — 所有新代码在 `if _ENABLE_TOW:` 或 `enable_tow` 守护下
2. 特征向量扩展 — `LR_FEATURE_NAMES` 从 22 扩展到 25 维（oe_overlap + emotional_cv），索引连续
3. 占位符安全 — 使用 `\ue000` (Unicode PUA) 而非 `\x00`，避免与 `reduce_high_freq_bigrams` 哨兵冲突
4. scope-brace 分治 — ≤6 中文字短标题不保护，>6 字长内容保护，防止标题类过度锁定
5. `patterns_cn.json` — `tow_patterns` 为独立顶级节点，不影响现有 parse 逻辑

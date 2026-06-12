# PR: v6 ToW 增强 + LaTeX 保护层

**Branch:** `detect-test` → `main`  
**Commit:** `2ea9064`  
**Files:** 7 changed, +1131 / -7

---

## 摘要

本 PR 基于 ACL 2026 论文 *Tree-of-Writing* (ToW, Pearson ρ=0.93) 的研究发现，新增 3 个检测信号和 3 个改写优化策略。同时集成了 LaTeX 标记保护层 (`--protect-latex`)，防止改写过程破坏学术论文中的 LaTeX 命令、数学公式和花括号块。

所有新功能通过 `--enable-v6` 标志控制，默认关闭，对现有行为零影响。

---

## 变更清单

### 修改文件 (4)

| 文件 | 行数变化 | 变更说明 |
|------|---------|---------|
| `scripts/ngram_model.py` | +114 | 新增 `compute_oe_overlap()`、`compute_emotional_clustering()`、`LR_FEATURE_NAMES` 扩展(22→27维) |
| `scripts/detect_cn.py` | +45 | 新增 `last_sentence_template` 规则层检测、`stat_high_oe_overlap` / `stat_low_emotional_cv` 统计层信号、`--enable-v6` CLI |
| `scripts/humanize_cn.py` | +97 | 集成保护层入口/出口、R-1 长度罚分、R-2 聚集情感注入、R-3 OE浅改写、`--protect-latex` / `--enable-v6` CLI |
| `scripts/patterns_cn.json` | +14 | 新增 `v6_patterns` 配置节(模板词表 + 阈值) |

### 新增文件 (3)

| 文件 | 行数 | 说明 |
|------|------|------|
| `scripts/_humanize_protect.py` | 181 | LaTeX 保护层：9 类模式匹配 + Unicode PUA 占位符 + 多轮还原 |
| `tests/test_protect_latex_acceptance.py` | 393 | 29 验收测试(8 场景 × 3-4 用例)，全面覆盖保护层功能 |
| `docs/评分与改写模块说明.md` | 294 | 人类可读的评分/改写模块说明(信号表 14→17 + v6 策略) |

---

## 功能详解

### 🔍 检测层 (D-1 ~ D-3)

| 信号 | 类型 | 权重 | 触发条件 | 设计依据 |
|------|------|------|---------|---------|
| `stat_high_oe_overlap` | 统计层 | 6 分 | 首尾段 bigram Jaccard >40% | ToW: Opening-Ending 是跨12体裁稳定评估维度(权重~10%) |
| `last_sentence_template` | 规则层(critical) | 8 分 | 末句以模板词开头(综上所述/总而言之/由此可见...) | ToW + 经验：AI 末句高度模板化 |
| `stat_low_emotional_cv` | 统计层 | 4 分 | 情感词段落间分布 CV <0.5 | ToW: 人类情感聚集、AI均匀撒 |

### ✏️ 改写层 (R-1 ~ R-3)

| 策略 | 控制 | 说明 | 设计依据 |
|------|------|------|---------|
| **长度罚分** | `--enable-v6` | 候选输出超出原始30%时，rank_score += (ratio-0.3)×10 | ToW Table 6: 输入长度与 Content 分负相关(ρ=-0.44) |
| **聚集情感注入** | `--enable-v6` | 选2个内容密度最低的段落集中注入噪声，其余段落不注入 | ToW: 人类情感聚集 |
| **OE浅改写** | `--enable-v6` + academic/formal | 首2段和末2段仅做短语替换，跳过 deep_restructure/noise | ToW: OE一致性权重~10%，过度改写破坏结构 |

### 🛡️ LaTeX 保护层

| 模式 | 覆盖 |
|------|------|
| Display math | `$$...$$`, `\[...\]` |
| Environments | `\begin{...}...\end{...}` |
| Commands w/ args | `\cite{...}`, `\textbf{...}`, `\includegraphics[...]{...}` |
| Bare commands | `\clearpage`, `\\`, `\&` |
| Inline math | `$...$`, `\(...\)` |
| LaTeX braces | `{...}` (含 `\` 或 `$` 的) |
| Tabular | `&`, `~` |

**实测效果**：`\textbf{值得注意的是}` 无保护时被改为 `\textbf{特别说一下}`(损坏)，有保护时完整保留。

---

## 向后兼容性

| 场景 | 影响 |
|------|------|
| `--enable-v6` 未设置(默认) | **零影响** — 所有新增代码由 `_ENABLE_V6=False` 关断 |
| `--protect-latex` 未设置(默认) | **零影响** — 保护层入口仅当显式传参时触发 |
| 无 LaTeX 文本 + `--protect-latex` | **输出不变** — 扫描无匹配，直接返回原文 |
| 现有回归测试 | 37 passed, 1 skipped (test_secondary_signal 需外部 HC3 数据) |
| hero floor | 2 subtest 为预存问题(academic 55>50, general 51>45)，与本次改动无关 |

---

## 测试覆盖

```
test_regression.py:            8/9 passed, 1 skipped
test_protect_latex_acceptance: 29/29 passed
  - Scene 1: Academic paper (3 tests)
  - Scene 2: Math-dense text (4 tests)
  - Scene 3: Table environments (3 tests)
  - Scene 4: Brace blocks (3 tests)
  - Scene 5: Mixed Chinese/English (3 tests)
  - Scene 6: Escape chars (3 tests)
  - Scene 7: Boundary/regression (7 tests)
  - Scene 8: best_of_n paths (3 tests)
```

---

## 使用方式

```bash
# 启用 v6 检测信号
./humanize detect paper.txt --enable-v6 -v

# 启用 v6 改写 + LaTeX 保护
./humanize rewrite paper.tex --enable-v6 --protect-latex -o clean.tex
```

```python
# 编程接口
from humanize_cn import humanize
result = humanize(text, enable_v6=True, protect_latex=True)
```

---

## 审查要点

1. **`_ENABLE_V6` gating** — 确认所有新代码都在 `if _ENABLE_V6:` 或 `if enable_v6:` 守护下（ngram_model / detect_cn / humanize_cn）
2. **特征向量扩展** — `LR_FEATURE_NAMES` 和 `extract_feature_vector` 新增 2 维(oe_overlap, emotional_cv)，索引连续无空洞
3. **占位符安全** — 使用 `\ue000` (Unicode PUA) 而非 `\x00`，避免与现有 `reduce_high_freq_bigrams` 哨兵冲突
4. **`patterns_cn.json` 格式** — `v6_patterns` 为独立顶级节点，不影响现有 parse 逻辑

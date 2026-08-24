# P1 长文本 perplexity boost 设计 (2026-05-18, heartbeat 43)

## 触发

heartbeat 20/32 多次 LR diagnostic 指出 perplexity 是 long_blog/general 主要
+AI driver：
- long_blog general LR: perplexity contrib +1.04 (raw 386, std -1.56, w -0.67)
- sample_general LR: perplexity contrib +1.46 (raw 282, std -2.19, w -0.67)
- raw 距 human mean (~600) 差距明显

humanize 现有 perplexity-boosting 间接策略 (cilin/WORD_SYNONYMS/bigram 替换)
对 long-form text 不够。Direct boost 是结构性 lever。本文档设计 prototype 路径。

## 现状

humanize 现有间接 perplexity 提升路径：
1. WORD_SYNONYMS 替换 (~30+ keys × 2-5 alts each) — 平均 perplexity +5%
2. reduce_high_freq_bigrams — 把高频 bigram 替换为低频 → perplexity 直接提升
3. cilin synonym expansion (~10k keys, ~3-6 alts each) — 大概 +10% perplexity
4. paraphrase templates (PHRASE_REPLACEMENTS via patterns_cn.json regex) — ~+5%

累积效果：长文本 perplexity 从 AI ~280 提升到 ~386，但距 human ~600 仍差 ~55%。

## 候选策略

### A. Rare-character injection (推荐 ★★★)

- 在句尾或低风险位置（句中逗号后、并列连词前）插入 1-2 低频字符的近义词替换
- 候选字符池：从 zhwiki / human corpus 提取 char freq rank > 5000 但
  semantically-valid 的字
- e.g.: 常用 "认为" → "以为" (low freq); "看到" → "瞥见" (rare)
- 适合 long-form，对 short-form 风险大（一段 100 字插 2 个低频字过分明显）

### B. Aggressive paraphrase template (推荐 ★★)

- 现有 PHRASE_REPLACEMENTS 模板 ~50 条，每个长 5-15 字
- 加 50-100 条新模板，每个含 1-2 低频字符
- e.g.: "需要注意的是" → "尤需留心的一点是" (留心 freq lower than 注意)
- 增量低，可独立验证每条 ROI

### C. Sentence-level perplexity targeting (推荐 ★)

- 跑 each sentence through perplexity model
- 找最高 perplexity 句子 (最 AI-like)
- 针对性 rewrite 那几句的 high-frequency words
- 复杂、慢，但 surgical

### D. Char-level n-gram entropy injection (☆)

- 计算每个 char 的窗口熵
- 在低熵区段插 rare char
- 风险：可能破坏文本可读性 (e.g. "他是一个" → "他乃一介")
- 高 risk reward 不确定

## 评估方法

每个候选实施前后：
- hero 4 sample 跑 + 全 floor 验证 (academic 50/general 45/social 30/long_blog 46)
- HC3 N=30 mini benchmark (correct/gap/grammar)
- n=60 longform spot check (avg delta delta)
- perplexity raw 测：sample_long_blog/sample_general/sample_academic

成功标准：
- perplexity raw 进 [450, 650] 区间 (避免过度引入古风/晦涩)
- hero floor 全过
- HC3 correct ≥ 90%（默认 95% baseline -5pp 容忍度）
- 无新增 grammar defects

## 推荐第一步 prototype

**Strategy B: 加 30 条 long-form 友好 paraphrase 模板，覆盖 academic/blog/review 高频
AI 起手 phrase。**

理由：
- 增量小 (json edit + 测试)
- 风险低 (现有模板路径)
- ROI 可测 (每条模板独立)
- 不破现有结构

候选模板初稿（待筛选）：
- "首先 → 第一点要说的是" (5字→9字, perplexity +)
- "然而 → 但话说回来" (2字→6字, perplexity +)
- "因此 → 这样一来" (2字→4字, perplexity ≈)
- "我们可以 → 不妨这样想" (4字→6字, perplexity +)
- "目前 → 眼下来看" (2字→4字, perplexity +)
- "需要注意 → 尤需留心" (4字→4字, perplexity +)
- "对于 → 谈到" (2字→2字, perplexity +)
- "由于 → 缘于" (2字→2字, perplexity ≈)
- "可以发现 → 不难看出" (4字→4字, perplexity ≈)
- "重要的是 → 关键还在于" (4字→5字, perplexity +)
- "广泛 → 颇为普遍" (2字→4字, perplexity +)
- "持续 → 一脉相承" (2字→4字, perplexity ++) (idiom)
- "显著 → 颇为可观" (2字→4字, perplexity +)
- "充分 → 不无道理地" (2字→5字, perplexity +)
- "有效 → 行之有效地" (2字→5字, perplexity +) (cliché but rare)
- ... (其余 15 条待挖)

每条要验证：
- 替换后语义保持
- 长度比合理 (1.0-1.5x)
- 不和现有 patterns 冲突
- 不在 detect_cn 的 AI marker list

## 风险

1. **paraphrase 替换 cascade**：原 phrase + 替换 phrase 都在 patterns_cn.json 里可能死循环（cycle 14 死循环 bug 类型）。需 safe_alts filter (已有)。
2. **register mismatch**: "一脉相承" 在科技文本里看上去很文。需 scene-gated。
3. **paragraph density 过载**: 30 条模板都加，可能一段里命中多次。需 per-paragraph cap。

## 不在本次范围

- Strategy A (rare-char injection): 复杂度高，留 next cycle。需要 corpus freq 表。
- Strategy C/D: 复杂度大，长 ROI 待商榷。

## 完成标记

DONE: audit/p1_perplexity_boost_design_2026-05-18.md
NO_CODE_CHANGE: true
NEXT: heartbeat 44 起 prototype Strategy B 5-10 条最稳的模板，先验单条 ROI。

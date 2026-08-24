# long_blog GENERAL LR diagnostic (2026-05-17, heartbeat 20)

## 触发

heartbeat 18 全力诊断了 novel LR top 25 features，但 heartbeat 19 发现 long_blog
1446 cn chars < 1500 → auto-route 实际去 **general LR** 而非 novel。需要重做
诊断锁定真正驱动 long_blog 44 production fused score 的特征。

## 数据

humanized long_blog (PYTHONHASHSEED=0, seed=42), GENERAL LR:
- score=42, p_ai=0.42, logit=-0.34（不强烈 AI，处于边缘）
- intercept=-0.36

Top 8 drivers：

| rank | feature | contrib | std | weight | raw | 方向 |
|---:|---|---:|---:|---:|---:|---|
| 1 | sent_len_cv | **-1.38** | +0.79 | -1.75 | 0.608 | human↑ (已强 push) |
| 2 | perplexity | **+1.04** | -1.56 | -0.67 | 385.94 | AI↑ |
| 3 | gltr_top10_frac | -0.83 | +1.67 | -0.50 | 0.302 | human↑ |
| 4 | news_vs_human | +0.67 | +0.45 | +1.49 | -0.191 | AI↑ |
| 5 | entropy_cv | +0.56 | +1.22 | +0.46 | 0.092 | AI↑ |
| 6 | sent_len_short_frac | +0.51 | +1.37 | +0.37 | 0.192 | AI↑ |
| 7 | wiki_vs_human | +0.43 | +0.53 | +0.82 | -1.275 | AI↑ |
| 8 | uni_tri_ratio | -0.38 | -0.54 | +0.70 | 1.885 | human↑ |

## 关键发现（vs novel LR 对比）

1. **cross_para_3gram_repeat 不在 general LR top 15！** novel LR 里它是 #1 driver
   (+2.30)；general LR 里它的 weight 太小没排进 top。
   - 这就是为什么 heartbeat 19 max_replacements 4→8 对 long_blog fused 0 影响
     （novel LR -55，但 long_blog 不走 novel）
   - 但 social hero（也 general LR）24→25 改善 1 分，说明 social 有 cross_para
     repeat（社交文本短，segments 间复用词易）
2. **perplexity 是 long_blog 真正主驱动（+1.04）**。raw 385.94 远低 general LR
   training human mean → "太流畅 / 太可预测"。perplexity-boosting 是 humanize
   现有策略（cilin 替换、bigram 低频替换等），但显然没把 long_blog perplexity
   推到 human band。
3. **sent_len_short_frac 0.192（+1.37 std）**。19.2% 短句。merge_short_sentences
   已在 pipeline 但 long_blog 长文本 threshold 可能不合理（min_len=8 全局；长文
   本里 8 字的短句仍是 short_frac contributor）。
4. **news_vs_human +0.67 / wiki_vs_human +0.43**。文本"看起来像新闻 / 百科"。
   这两个 secondary ngram 特征很难 humanize 侧动（要换 register／语体）。
5. **sent_len_cv 已经 -1.38**。已是最强 human-side push，再 push 边际递减
   （previous cycle audit 也提到过 saturation）。

## 下 cycle 候选 actionable

按 ROI 排：

1. ★★★ **加 perplexity boost on long-form**：sample long_blog 跑后看哪些 segment
   perplexity 最低，针对性替换。或 inject low-freq char clusters。如能把 raw
   385.94 推到 ~600（human mean）→ std 从 -1.56 → ~0 → 贡献 +1.04 减到 ~0 → fused
   -8 范围。需要新代码路径。
2. ★★ **reduce sent_len_short_frac for long-form**：long_blog 短句门槛抬高（>15 字
   保留作"正常短"，<8 字 merge）。或单独 long-form merge strategy。
3. ★ **news_vs_human 长期路径**：需要 secondary corpus retrain 或 humanize 加
   register-shift 策略（"news 风格 → blog 风格" rewrite）。属下下下游。
4. ☆ **cross_para_3gram_repeat 已 ship max_replacements=8**，对 general LR 长文本
   贡献小，对 novel LR / short text 还有提升空间，但优先级低。

## 修正盲点

- heartbeat 18 强制 scene='novel' 给出 cross_para_3gram_repeat #1 driver 结论
  仅适用 ≥1500 cn 文本（hero 里没有这样的样本，longform corpus n=170 才有）。
- 对 hero floor 优化，应该用 GENERAL LR 诊断；对 longform corpus 优化，用 novel LR。

## 完成标记

DONE: audit/n2e_lr_diagnostic_general_2026-05-17.md
NO_CODE_CHANGE: true
NEXT: 试 perplexity boost on long-form（设计阶段，需 prototype）

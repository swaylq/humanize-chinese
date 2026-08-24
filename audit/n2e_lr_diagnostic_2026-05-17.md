# N-2e long_blog LR feature contribution diagnostic (2026-05-17, heartbeat 18)

## 触发

heartbeat 16/17 两次 N-2e 尝试（rename 一、 / merge 段落）双双失败：
- rename 三、 → 第三、: long_blog 44 → 46 (at floor)
- merge 二、X → 二、X：<content>: long_blog 44 → 48 (exceed floor)

直觉是「numbered headers 是 AI 信号」错了。需要先看 long_blog LR 实际什么特征驱动 97 分。

## 方法

跑 humanize(sample_long_blog.txt, seed=42) → compute_lr_score(scene='novel') →
全 25 feature contribution 排序。

## 结果

humanized long_blog: 1428 cn chars (走 longform LR), score=97, p_ai=0.966, logit=+3.34

intercept +0.69, top 5 drivers：

| rank | feature | contrib | std | weight | raw | 方向 |
|---:|---|---:|---:|---:|---:|---|
| 1 | cross_para_3gram_repeat | **+2.30** | +0.69 | +3.33 | 0.067 | AI↑ (dominant) |
| 2 | gltr_top10_frac | +1.01 | +1.99 | +0.51 | 0.306 | AI↑ |
| 3 | bino_lp_diff | +0.94 | -1.55 | -0.61 | -1.870 | AI↑ |
| 4 | perplexity | +0.86 | -1.82 | -0.47 | 384.06 | AI↑ |
| 5 | sent_len_cv | -0.76 | +0.47 | -1.62 | 0.604 | human↑ |

## 关键发现

1. **cross_para_3gram_repeat 是 long_blog 单一主驱动**。raw 0.067（67/1000 trigrams 跨段重复）→ std +0.69 → 乘 weight +3.33 → 贡献 +2.30 logit。
   - reduce_cross_para_3gram_repeat 已在 pipeline（max_replacements=4），但仍残留 0.067。max_replacements 不够。

2. **gltr_top10_frac std=+1.99** 二号驱动。humanized 文本 30.6% 字符落 corpus top-10 frequency words。这是「高频字密集」signal，AI 改写后仍偏高。

3. **bino_lp_diff 与 perplexity 都是反向 weight 但贡献 +AI**。原因 raw 低于 human 均值 → std 负 → 乘负 weight 得正。意味长 blog perplexity 384（明显低于 longform human 均值 → 行文太流畅 → AI 信号）。

4. **numbered headers 完全不在 top 25 driver**。原因：LR 没有 header-presence feature。等距 / 段落数 / 段落长度 CV 等 structural 信号 weight 都微小。
   - `paragraph_length_cv` rank 22, contrib +0.04
   - `para_sent_len_cv_avg` rank 16, contrib -0.17
   - 解释了为什么 N-2e rename/merge 都无效：header structure 不在 LR 雷达上。

5. **sent_len_cv -0.76 是唯一显著 human-side contribution**。current humanize 已经把句长 CV 推高到 0.60，远超 human longform 均值 0.55，再 push 收益递减。

## 下一 cycle 候选 actionable

按 ROI 排：

1. ★★★ **加 reduce_cross_para_3gram_repeat 频次**：max_replacements 4 → 8 / 10，或加二级循环到 cross_para_3gram_repeat<0.04 收手。预期 long_blog -3 to -5。
2. ★★ **gltr_top10_frac 直接打压**：检测 top-10 freq 字符密集段落，针对性低频替换。需要新增 humanize 函数 `reduce_top10_density`。
3. ★ **perplexity 不直接调整** — humanize 已尽量增 perplexity，384 已是 baseline 后产物。
4. ☆ **N-2e structural intervention 暂停**：本 diagnostic 证伪「header 等距是主信号」假设。

## 建议下 cycle

P1: 试 max_replacements 4 → 8（单参数 tweak，30 min cycle 完成）。验证 long_blog ≤44。如成功，进一步 sweep 找 sweet spot。

## 完成标记

DONE: audit/n2e_lr_diagnostic_2026-05-17.md
NO_CODE_CHANGE: true
NEXT: heartbeat 19 试 reduce_cross_para_3gram_repeat max_replacements bump

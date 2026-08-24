# N-3d 短样本影响分析 (2026-05-17, heartbeat 15)

任务来源：BACKLOG.md N-path 方向 3 — "misc 真人语料偏长，对 hero 短样本 calibration 影响"。
本 cycle 跑全量 source 长度分布对比，不动 coef，只产 audit。

## 数据 source 长度分布（中文字符）

| Source | n | p10 | p50 | mean | p90 | max |
|---|---:|---:|---:|---:|---:|---:|
| m4_zh_ood | 400 | 113 | 170 | 189 | 294 | 946 |
| cudrt_zh_ood | 400 | 488 | 1065 | 996 | 1313 | 3834 |
| human_misc_corpus | 234 | 316 | 1157 | 1040 | 1350 | 1663 |
| human_news_corpus | 500 | 3575 | 3866 | 3882 | 4222 | 4480 |
| human_novel_corpus | 221 | 806 | 838 | 868 | 935 | 1640 |

HC3 chatgpt/human 混合（n=5001）：p10=31，p25=73，p50=153，p75=190，p90=272，max=350。
- <300 字：94%
- 300-800：5%
- 800+：0%

Hero 样本长度：
- sample_academic.txt：263 字
- sample_general.txt：394 字
- sample_social.txt：479 字
- sample_long_blog.txt：1364 字
- sample_workplace.txt：166 字

## 结论

**Misc 人类语料 vs HC3 之间存在量级的 length 错配**：

- HC3 p50=153 字，是 sub-300 的短问答语境。
- cudrt + human_misc + human_news + human_novel 四源 p50 全部 ≥838，p10 全部 ≥316。
- 只有 m4_zh_ood（p50=170）覆盖 HC3 主流长度区间。
- 在 train_lr_longform / train_lr_multisource 时，长 source 数量占绝对多数（cudrt 400 + misc 234 + news 500 + novel 221 = 1355 长，对 m4 400 短）→ LR human 侧 75% 是 >300 字样本。

**LR calibration 风险**：
- 长样本主导 → LR 学到"段落多 / 句子多 / 句长 CV 大 = human"等长文本特征。
- 短样本（hero academic 263 / general 394 / workplace 166）缺少这些长结构信号，可能被 LR 误判为 AI。
- Hero baseline academic 9（极低）与 long_blog 38（最高）的差距，可能部分由此 length-bias 推动：长样本评分更"严"，短样本评分更"松"。

**反方向证据**：
- 如果短样本被 LR 误判为 AI，academic 9（极人类）会变高，不是变低。
- 实际短样本 fused 都很低（9/37/27），long_blog 38 最高 → 当前可能是另一种 calibration：长样本里 LR 学到 cudrt/human_misc 风格指纹，long_blog 偏离这些指纹被推高。
- 总之 length 是 LR 隐式特征，需 stratify 验证才能定论。

## 建议（下一 cycle）

1. **不动 runtime coef**。本 cycle 是 diagnostic，无 ship 改动。
2. **N-3c 衔接**：训练时按 length bucket stratify human 侧 sampling，避免 cudrt/misc 长样本主导：
   - 100-300 字：60%（m4 + HC3 human 摘）
   - 300-800：25%（misc 短端 + 部分 cudrt）
   - 800+：15%（cudrt/misc/news/novel 长端）
3. **m4_zh_ood 重要性提升**：唯一覆盖 HC3 主流长度的 OOD 源，train_lr_multisource 应保证 m4 占 human 侧 ≥30%。
4. **新增短端 pre-LLM source** 是 N-3a 续核心 ask：人民日报短评 / 早期博客标题段 / 知乎短答 都是候选，长度 100-400 字最有价值，填补 HC3 量级真人 baseline。

## 完成标记

DONE: audit/n3d_misc_length_2026-05-17.md
NO_CODE_CHANGE: true
NEXT: N-3a 续推动 → 补 100-400 字 pre-LLM 短端真人源

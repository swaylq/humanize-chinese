# Longform n=170 full benchmark post heartbeats 14/19/22/24/25 (2026-05-17, heartbeat 26)

## 触发

heartbeat 23 spot check 跑 n=60 显示表面回退（avg Δ +10.9 vs cycle 252 +25.1），
但 n=60 不严格。本 cycle 跑全量 n=170 apples-to-apples 与 cycle 252 baseline 对比。

## 全量数据

```bash
python3 evals/run_longform_benchmark.py --n 170 -o /tmp/longform_n170_post_heartbeat25.json
```

| 指标 | n=170 当前 | cycle 252 baseline (n=170, 2026-05-04) | 差 |
|---|---:|---:|---:|
| detector gap | 70.0 | ~51 | +19 (detector 加强了) |
| AI orig avg | 85.4 | ~76 | +9 |
| AI post avg | 74.7 | ~51 | +23 |
| Δ avg | **+10.7** | **+25.1** | **-14.4 (回退)** |
| Δ median | 8 | — | — |
| 改善样本 | 157/170 (92.4%) | — | — |
| 回退样本 (Δ<0) | **8** | — | 新增问题 |
| 段留率 | 97.6% | 98.8% | -1.2 |
| **grammar defects** | **3** | **0** | **+3 (硬回退)** |

按 genre：

| genre | n | orig | post | Δ now | Δ baseline | 差 |
|---|---:|---:|---:|---:|---:|---:|
| academic | 20 | 95.2 | 87.5 | +7.7 | +13.8 | -6.1 |
| blog | 50 | 86.6 | 73.2 | +13.5 | +36.3 | **-22.8 (最大回退)** |
| news | 20 | 92.7 | 83.2 | +9.4 | +18.8 | -9.4 |
| novel | 60 | 76.8 | 67.7 | +9.1 | +19.5 | -10.4 |
| review | 20 | 90.6 | 78.0 | +12.7 | +31.8 | -19.1 |

按 model：

| model | n | orig | post | Δ |
|---|---:|---:|---:|---:|
| qwen-max | 34 | 84.8 | 66.4 | +18.4 |
| gpt-4o | 34 | 86.4 | 74.3 | +12.1 |
| gemini-2.5-flash | 34 | 87.9 | 79.7 | +8.2 |
| claude-sonnet-4 | 34 | 85.7 | 78.1 | +7.6 |
| deepseek-chat | 34 | 81.9 | 74.9 | +6.9 |

## 8 个 -delta 样本

| Δ | genre | model | cn | orig | 备注 |
|---:|---|---|---:|---:|---|
| **-40** | blog | deepseek | 1607 | 18 | **最严重** |
| -14 | novel | deepseek | 2807 | 55 | heartbeat 24 修过 围绕，但 seed 变化导致 sample 再跑出 -14 (random state 在 n=60 vs n=170 不同) |
| -9 | review | deepseek | 1092 | 28 | heartbeat 25 修过 控制，但 n=170 seed 变化导致 -6→-9 |
| -8 | blog | claude-sonnet-4 | 1692 | 68 | 新 |
| -7 | novel | deepseek | 3396 | 58 | 新 |
| -3 | novel | claude-sonnet-4 | 2683 | 65 | 新 |
| -1 | novel | gemini-2.5-flash | 3944 | 67 | 新 |
| -1 | review | deepseek | 1847 | 86 | 新 |

deepseek 模型占 -delta 5/8（high orig score + 短 cn 范围更容易被 humanize 弄坏）。

## 3 grammar defect 样本

| genre | model | cn | defects | delta |
|---|---|---:|---:|---:|
| novel | gemini-2.5-flash | 2692 | 1 | +23 |
| blog | claude-sonnet-4 | 1993 | 1 | +18 |
| news | deepseek-chat | 1623 | 1 | +8 |

grammar 0 → 3 是硬回退。每个样本 delta 仍正，所以是 "改善的同时引入了 1 处病句"，
不是 "改坏了" 的样本（与 -delta 样本无重叠）。

## 关键解读

1. **detector gap 70.0 vs cycle 252 ~51**：detector 侧强化了（heartbeats 1-15 之前
   的工作 + 后续 LR retrains），AI orig 评分变高 ~9pt。这部分 humanize Δ "回退"
   其实是 AI orig 进了门，分数 ceiling 抬高。
2. **修正后 vs 修正前差距估算**：
   - cycle 252 baseline post avg ~51（orig ~76, Δ +25）
   - 现在 post avg 74.7（orig 85.4, Δ +10.7）
   - 净 post score 上升 ~24pt。考虑 orig 上升 ~9pt，剩 ~15pt 是 humanize 退化
3. **疑似回退源**：cycle 252 → 现在之间有 15 commits（5-14/15/16 cycles 230-247
   work，主要 fluency cleanup）+ 5 heartbeats 14-25。fluency cleanup 加强了 cilin
   blacklist 会减少 humanize 替换多样性 → 可能损 LR delta。是已知 tradeoff。
4. **grammar 0 → 3**：fluency 加强同时引入 3 处新 病句。值得 N-1 cycle 单挑诊断。
5. **blog 回退 -22.8 最严重**：cycle 252 时 blog +36.3 是大杀器，现在 +13.5 接近
   academic 水平。可能 vary_paragraph_rhythm / paragraph 操作的 regression。

## 建议下 cycle

按 ROI 排：

1. ★★★ **bisect 回退源**：cycle 252 commit 259be50 vs 当前 b7b001f 之间的 15+5 commits，
   每个 commit checkout 跑 n=60 acid test 锁定哪一个引起 blog/review Δ 跌的最猛。
2. ★★ **挖最差 -delta 样本（blog/deepseek -40, cn=1607）**：和 heartbeat 24/25
   同 pattern，找 humanize 引入的 bug 加 cilin blacklist。
3. ★★ **3 grammar defect 样本单挑**：novel/gemini/2692, blog/claude/1993,
   news/deepseek/1623 — humanize 引入了什么病句？
4. ★ **接受当前状态**：detector 升级 + fluency cleanup 是有意识的 trade，cycle 252
   baseline 不强求复原；hero floor 全持平、HC3 95% 仍稳。

## 完成标记

DONE: audit/longform_n170_full_2026-05-17.md
NO_CODE_CHANGE: true
NEXT: heartbeat 27 候选 ★★★ bisect 或 ★★ -40 sample 单挑

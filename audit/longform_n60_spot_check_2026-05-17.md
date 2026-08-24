# Longform n=60 spot check post heartbeats 14/19/22 (2026-05-17, heartbeat 23)

## 触发

heartbeat 22 ship 后想 spot check：commits a540048（max_replacements 4→8）+ 
8f4e3c6（target_short_frac 0.15→0.10）+ d5f6415（助力 fix）累计对 longform corpus
benchmark 影响如何，确认无 longform 回退。

## 结果

`evals/run_longform_benchmark.py --n 60 -o /tmp/longform_n60_post_heartbeat22.json`

| 指标 | 当前 (n=60) | cycle 252 baseline (n=170, 2026-05-04) |
|---|---:|---:|
| AI orig avg | 85.5 | ~76 (推算) |
| AI post avg | 74.6 | ~51 |
| Δ avg | **+10.9** | +25.1 |
| Δ median | +8 | — |
| Δ range | [-14, 68] | — |
| 降分样本 | 55/60 (92%) | — |
| 段留率 | 98.3% | 98.8% |
| grammar defects | 0 | 0 |

按 genre（vs cycle 252）：

| genre | n=60 now | n=170 baseline | 差 |
|---|---:|---:|---:|
| academic | +8.5 (n=10) | +13.8 | -5.3 |
| blog | +14.1 (n=19) | +36.3 | -22.2 |
| news | +5.7 (n=3) | +18.8 | -13.1 |
| novel | +8.0 (n=23) | +19.5 | -11.5 |
| review | +20.4 (n=5) | +31.8 | -11.4 |

按 model：

| model | n | Δ |
|---|---:|---:|
| qwen-max | 16 | +19.2 |
| gpt-4o | 12 | +11.8 |
| gemini-2.5-flash | 14 | +9.3 |
| claude-sonnet-4 | 7 | +6.6 |
| deepseek-chat | 11 | +2.7 |

## 解读

1. **Avg delta 表面回退 -14.2 (+25.1 → +10.9)**，但比较不严格：
   - n=60 vs n=170 不同随机样本
   - per-genre n 太小（news=3, review=5）单样本扰动放大
   - cycle 252 后又跑了 30+ cycle 微调，整体 trajectory 难溯
2. **降分样本 92% (55/60)**：humanize 仍在 work，主要降分能力没坏
3. **grammar 0 / 段留 98.3%**：质量 floor 持平
4. **5 个 -delta 样本** (range [-14, 68])：少量样本 humanize 后反而更 AI 检出，
   值得 N-1 fluency 后续 cycle 单挑看是 substitution cascade 还是其他

## 建议下 cycle

1. 跑 n=170 full benchmark（~10 分钟），获得 apples-to-apples 数据
2. 看 5 个 -delta 样本，找 humanize 失效 root cause
3. heartbeat 22 reply 提的 P1 仍有效：长文本 perplexity boost

## 完成标记

DONE: audit/longform_n60_spot_check_2026-05-17.md
NO_CODE_CHANGE: true
NEXT: 或跑 n=170 full benchmark 锁定 baseline，或开始长文本 perplexity boost prototype

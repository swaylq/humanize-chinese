# Benchmark vs production scene routing 不一致诊断 (2026-05-19, heartbeat 53)

## 触发

heartbeat 52 reply 说 deepseek samples 仍 -delta，原因疑似 cross-LR scoring。
深挖发现 longform benchmark 和 production 用不同 LR coef。

## 现象

heartbeat 27 修 blog/deepseek 1607 sample 时报告：fused delta -40 → +3。
但 heartbeat 52 跑 n=170 同一个 sample 仍是 Δ -30。两次测量看似矛盾。

## 根因

`evals/run_longform_benchmark.py:79` 的 `score_longform()` 函数：

```python
def score_longform(text, scene='novel'):
    ...
    lr_r = compute_lr_score(text, scene=scene)
```

显式传 `scene='novel'`，强制用 `lr_coef_longform.json`。

但 production `compute_lr_score` 默认 / `scene='auto'` 自动路由 (`ngram_model.py:1450`)：
- text ≥ 1500 cn chars → novel LR (`lr_coef_longform.json`)
- text < 1500 → general LR (`lr_coef_cn.json`)

我之前修 heartbeat 27 用的 fused 函数（hero check / debugging）默认 scene='general'。
所以 measured：
- heartbeat 27 自测: general LR fused = +3 (sample 1607 cn < 1500 → general 是 production 路径) 
- heartbeat 52 benchmark: novel LR fused = -30 (强制 scene='novel')

两个数都对，但反映不同 LR 视角。

## 含义

1. **大量 fluency 修复（heartbeats 14/24/25/27/28/31/35/36/37/39/41/42）都是冲 general
   LR 优化的**。1000-1500 cn chars 这个段在 production auto-route 走 general，但
   benchmark 走 novel —— 两个 LR 关心的 feature 完全不同（heartbeat 18 vs 20 已记录）。
2. **Strategy B 30 templates 在 n=170 (novel LR) 只 +0.4 avg delta**，但若 benchmark
   走 'auto' 可能 +0.7+。
3. **deepseek 6 -delta samples**：4 个 cn=1092~3396 中，至少 1092 < 1500 走 general 应改善。
   现 benchmark 全用 novel 看不出这块。

## 选项

### A. 改 benchmark 默认到 scene='auto'（推荐）

- 优点：vs production 一致；fluency 改进 reflect 正确
- 缺点：scores 全 reshuffle，trend 历史断
- 实现：1 行 `score_longform(text, scene='auto')`

### B. 加 'auto' variant 输出，保留 'novel'

- 优点：保 historic baseline；可双视角对比
- 缺点：report 加倍长

### C. 不改 benchmark，文档化差异

- 优点：零代码风险
- 缺点：未来 cycle 继续被这个 mismatch 误导

## 建议

选 **A**。production 一致是 ultimate ground truth；historic baseline 反正已经被
heartbeat 51 改变了多次（trans cap 1500→1000）。同时 hero floor / test_regression
仍用 default scene='general'，hero 始终一致。

但这是 sway 决定：production 真该是 auto？还是 longform corpus 真该 force novel
（since corpus 主要是 long-form 创作型）？需要 sway 输入。

## 完成标记

DONE: audit/benchmark_scene_routing_diag_2026-05-19.md
NO_CODE_CHANGE: true
DECISION_NEEDED: sway 选 A/B/C

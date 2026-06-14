# PR — 维度感知改写策略路由 (Dimension-Aware Rewrite Routing)

## 概述

当前改写器采用固定流水线 + 全局三档强度策略，对所有改写操作统一施加相同强度，不根据具体 AI 检测维度（如"标点符号 AI 痕迹过重"、"句长 CV 太低"）做针对性差异化。

本 PR 引入**维度诊断 + 策略路由**两层架构，使每个改写操作获得独立的连续强度值，定向解决问题维度。

## 架构

```
diagnose_scores(text) → {dim: score}                    # 15 维度分解
    ↓
route_strategy(scores, tier) → {op: {param: value}}     # 独立操作强度
    ↓    match_score[op] = Σ(weight[op][dim] × score[dim])
    ↓    intensity[op] = map_to_range(match_score, min, max, tier_cap)
    ↓
humanize(text, adaptive=True) → 各 Stage 按路由参数执行
```

关键设计：
- 每个改写操作**独立计算强度**，彼此不互相约束
- 三档总强度 (conservative=0.3 / moderate=0.7 / full=1.0) 作为安全上限
- `--adaptive` 默认关闭，不传则行为完全不变

## 文件变更

| 文件 | 状态 | 行数 | 说明 |
|------|------|------|------|
| `.gitignore` | 修改 | +22 | 新增测试/数据文件忽略规则 |
| `scripts/dimension_router.py` | **新增** | 551 | 核心路由引擎 |
| `scripts/dimension_weights.json` | **新增** | 87 | 效应权重矩阵 |
| `scripts/humanize_cn.py` | 修改 | +72 | 集成路由 + `--adaptive` 参数 |
| `scripts/restructure_cn.py` | 修改 | +11 | 新增可选强度参数 |

**总变更: +743 行 / -5 行**，零破坏性变更。

## 改写操作 → 可调参数

| 操作 | 参数 | 范围 | 说明 |
|------|------|------|------|
| phrase_replace | bigram_strength | [0.0, 0.5] | 唯一词替换比例 |
| synonym_replace | strength | [0.0, 0.6] | 同义词替换比例 |
| deep_restructure | strength | [0.3, 0.6] | 句式模板应用概率 |
| deep_restructure | delete_prob | [0.2, 0.6] | AI 废话删除概率 |
| noise_injection | density | [0.0, 0.25] | 噪声注入概率 |
| sentence_len_randomize | merge_rate | [0.0, 0.25] | 句子合并概率 |
| sentence_len_randomize | truncate_rate | [0.0, 0.25] | 句子截断概率 |

## 对比测试

### C-ReD 长文本 (均值 1644 字, 20 篇 × 3 seed)

| 指标 | Baseline | Adaptive | 变化 |
|------|----------|----------|------|
| 改写后 AI 分均值 | 44.6 | **40.6** | **+4.0 (↓8.9%)** |
| 稳定性 (std) | 11.0 | **9.1** | +1.9 |
| 改进 : 退化 : 持平 | — | — | **16 : 2 : 2** |
| 输出长度 (字) | 1636 | 1636 | 无膨胀 |

### 维度级改进

| 维度 | 平均 Δ | 改善样本 | 说明 |
|------|--------|---------|------|
| sent_len_cv | **+3.04** | 5/20 | 句式复杂度优化 |
| three_part_structure | **+1.74** | 6/20 | 三段式结构改善 |
| empty_grand_words | +1.60 | 3/20 | 空洞词减少 |
| mechanical_connectors | +1.60 | 4/20 | 机械连接词改善 |
| ai_high_freq_words | +1.40 | 5/20 | AI 高频词改善 |

### HC3 短文本 (均值 196 字, 30 篇 × 3 seed)

| 指标 | Baseline | Adaptive |
|------|----------|----------|
| AI 分均值 | 66.0 | 66.4 |
| 改进 : 退化 : 持平 | — | 10 : 12 : 8 |

> 短文本检测信号稀疏，总分近乎持平。长文本信号丰富后维度感知路由明显领先。

## 使用方式

```bash
# 标准模式 (行为不变)
python humanize_cn.py input.txt -o output.txt

# 维度感知模式
python humanize_cn.py input.txt -o output.txt --adaptive
```

## 待 PR 后补充

- [ ] 用更多长文本校准 `dimension_weights.json`
- [ ] 完善 `docs/评分与改写模块说明.md` 中新增路由章节
- [ ] 补充 dimension_router 独立单元测试

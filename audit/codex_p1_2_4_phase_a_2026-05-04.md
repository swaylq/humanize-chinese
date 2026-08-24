# Codex P1#2 + P1#4 Phase A 设计提案

日期：2026-05-04

范围：只调研和设计，不改业务代码。

## P1#2 fresh clone 数据资产缺失

### 现状

`.gitignore` 明确排除了 3 份本地大 ngram：

- `scripts/ngram_freq_cn_human.json`，当前本机约 19MB，`python scripts/train_ngram_human.py` 生成。
- `scripts/ngram_freq_cn_wiki.json`，当前本机约 9.8MB，`python scripts/train_ngram_wiki.py` 生成。
- `scripts/ngram_freq_cn_news.json`，当前本机约 28MB，`python scripts/train_ngram_news.py` 生成。

`scripts/ngram_freq_cn_human_holdout.json` 已入库，约 21KB，只描述 HC3 human holdout split，不是可替代的频率表。

### 实际依赖点

grep 和代码路径显示依赖集中在 `scripts/ngram_model.py`：

- `_load_human_freq()` 读取 `ngram_freq_cn_human.json`，缺失时返回 `None`。
- `_load_wiki_freq()` 读取 `ngram_freq_cn_wiki.json`，缺失时返回 `None`。
- `_load_news_freq()` 读取 `ngram_freq_cn_news.json`，缺失时返回 `None`。
- `compute_binoculars_ratio(text)` 依赖 human ngram；缺失时返回 `available=False`，没有 `mean_lp_diff`。
- `compute_wiki_lp_diff(text)` 依赖 wiki + human ngram；缺失任一返回 `available=False`，`wiki_vs_human/wiki_vs_primary=0.0`。
- `compute_news_lp_diff(text)` 依赖 news + human + wiki ngram；缺失任一返回 `available=False`，`news_vs_human/news_vs_wiki=0.0`。
- `analyze_text()` 总是调用上述三类函数，并把结果挂到 `analysis['bino']`、`analysis['wiki']`、`analysis['news']`。
- `extract_feature_vector()` 把 `bino.mean_lp_diff`、`wiki_vs_human`、`wiki_vs_primary`、`news_vs_human` 写入 LR 特征向量；缺失时这些连续特征归零。
- 三个 LR 系数文件 `scripts/lr_coef_cn.json`、`scripts/lr_coef_academic.json`、`scripts/lr_coef_longform.json` 都包含 `wiki_vs_human`、`wiki_vs_primary`、`news_vs_human` 等特征名，因此 fresh clone 的 LR detector 分数会和有本地资产的开发机不同。
- `scripts/humanize_cn.py` 的 `_secondary_signal_details()` 读取 `analysis['bino'].mean_lp_diff` 作为 best-of-n secondary signal 的 35% 权重；缺失 human ngram 时 `bino` 退化为 0，candidate ranking 会变。

规则层 detector 里 `low_binoculars_diff` 目前是 disabled；`detect_cn.py` 仍有显示/权重 wiring，但实际不会因为缺失三份大 ngram 直接打这个规则分。

### README 标注建议

不建议把 57MB 左右 JSON 入库，也不建议自动下载。README 应该清晰区分：

- fresh clone 可离线运行 detect/rewrite/academic/style/compare，不会崩。
- 但以下高阶统计信号在 fresh clone 中不可用或退化：Binoculars-like `bino_lp_diff`、`wiki_vs_human`、`wiki_vs_primary`、`news_vs_human`，以及 best-of-n secondary signal 中的 binoculars 分量。
- README 中“30 秒看效果”和 hero 分数如果来自开发机完整资产，应标注“完整本地 ngram 资产下复现”；fresh clone 的分数可能不同。
- 给出本地重训命令，并说明需要调用方自行准备本地语料：
  - `python scripts/train_ngram_human.py`
  - `python scripts/train_ngram_wiki.py`
  - `python scripts/train_ngram_news.py`
- 明确不会联网、不会自动下载、不会把大文件提交到 git。

### doctor/check_assets 建议

建议新增 `scripts/check_assets.py`，并把统一 CLI 扩展为 `./humanize doctor`，实现：

- 扫描核心入库资产：`ngram_freq_cn.json`、`patterns_cn.json`、`lr_coef_cn.json`、`lr_coef_academic.json`、`lr_coef_longform.json`、`ngram_freq_cn_human_holdout.json`。
- 扫描本地可选资产：三份 ignored ngram。
- 对每个资产打印状态：`OK` / `MISSING` / `SMALL`，文件大小，是否 git ignored。
- 打印影响说明：
  - human 缺失：`bino_lp_diff` 和 best-of-n secondary 的 binoculars 分量退化。
  - wiki 缺失：`wiki_vs_human/wiki_vs_primary` 退化；news divergence 也不可用。
  - news 缺失：`news_vs_human` 退化。
  - 任一 optional 缺失：LR 特征向量仍可计算，但相关特征置 0，fresh clone 分数可能不同。
- 打印重训命令，只提示，不下载。
- 默认 exit 0，方便用户查看状态；可考虑后续加 `--strict` 给 CI 使用，但本次不必扩大范围。

### fresh-clone smoke test 建议

建议在 `tests/test_regression.py` 增加一个“optional ngram 缺失路径”smoke test，而不是真的修改 `.gitignore` 或删除本机文件：

- 用 monkeypatch 方式临时把 `ngram_model._HUMAN_FREQ_FILE/_WIKI_FREQ_FILE/_NEWS_FREQ_FILE` 指到不存在路径，并清空对应 cache。
- 对一段短中文跑：
  - `ngram_model.analyze_text(text)` 不抛异常，且 `bino/wiki/news.available == False`。
  - `ngram_model.compute_lr_score(text)` 返回非 None 分数。
  - `humanize_cn.humanize(text, seed=42, best_of_n=1 或 None)` 不抛异常并保留中文输出。
- 这个测试应放在现有 `tests/test_regression.py`，随常规 `pytest` 触发；它不依赖大文件、不依赖网络、不依赖外部数据，适合 fresh clone CI。

## P1#4 `_pick_lr_scene` scene routing

### 现状

`scripts/humanize_cn.py` 当前逻辑：

```python
academic_hits = sum(1 for marker in _ACADEMIC_LR_MARKERS if marker in text)
if academic_hits >= 2:
    return 'academic'
if len(text) >= 1500:
    return 'longform'
return 'general'
```

问题：

- `len(text)` 是 raw Python string 长度，会把 ASCII、emoji、空白、Markdown、参考文献等都算进长度；中英混排会误进 longform。
- `scripts/ngram_model.py` 的 `_auto_scene()` 已经用 CJK 字符计数，阈值 1500。
- academic marker 优先于 longform，没有显式测试；长中文 + 两个学术 marker 会进 academic。

### helper 方案

推荐在 `scripts/humanize_cn.py` 内新增一个很小的本地 helper：

```python
def _count_chinese_chars(text):
    return sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
```

理由：

- 直接 import `ngram_model._auto_scene` 会让 humanize 的 routing 依赖 ngram detector 模块的私有函数；`humanize_cn.py` 已经允许 `ngram_analyze` 缺失 fallback，scene routing 不应因此变重。
- 抽出公开共享 helper 到 `_text_utils.py` 也可行，但本次只需要修一个 P1，局部 helper 风险更小。
- 算法必须和 `_auto_scene()` 保持一致，即 `'\u4e00' <= c <= '\u9fff'`，避免中文长度定义分叉。

阈值建议保持 1500 一致。可在 `humanize_cn.py` 定义 `_LONGFORM_LR_CN_CHAR_THRESHOLD = 1500`，避免 magic number；`ngram_model._auto_scene(short_thresh=1500)` 暂不改，减少交叉影响。

### academic vs longform 优先级

候选：

- 现状：academic markers >= 2 -> academic；raw len >= 1500 -> longform；else general。
- 候选 A：CJK char_count >= 1500 -> longform；academic markers >= 2 -> academic；else general。
- 候选 B：CJK char_count >= 1500 且 academic markers >= 2 -> academic；CJK char_count >= 1500 -> longform；academic markers >= 2 -> academic；else general。

推荐候选 A：长文优先。

理由：

- `_pick_lr_scene()` 只用于 best-of-n candidate 排序，不是用户显式 `--scene academic` 的检测选择。长文 LR 的训练目标更贴近“长文本段落节奏、跨段重复、段落长度 CV”等特征；这些特征在 1500+ 中文字时比两个 marker 更稳定。
- academic marker 是 keyword hit，容易被参考文献、教程、博客中的局部表述触发；长文长度是结构性信号，误判成本更高。
- README/教程/博客混合文档最常见的事故是被 marker 拉到 academic 或被 raw len 拉到 longform；改为 CJK char_count + 长文优先能同时解决两个问题。
- 用户显式走 academic 子命令或 `--scene academic` 时，humanize 主 pipeline 仍按 academic 场景执行；这里只影响 best-of-n LR scorer 的自动排序。

### 测试建议

在 `tests/test_regression.py::test_pick_lr_scene` 加显式 case：

- 短中文 + 2 学术 marker -> `academic`。
- >1500 CJK、无学术 marker -> `longform`。
- >1500 CJK + 2 学术 marker -> `longform`（候选 A）。
- 500 CJK + 1500 ASCII/Markdown -> `general`，不得误进 longform。

## Phase B 实施顺序

1. 新增 `scripts/check_assets.py`。
2. 扩展 `scripts/humanize.py` / `./humanize --list` / README CLI 表，加入 `doctor`。
3. README 增加“数据资产状态”说明和重训命令。
4. 修改 `_pick_lr_scene()` 使用 CJK 字符数，并采用“长文优先”。
5. 增加 regression tests：scene routing 四个 case + optional ngram missing smoke。
6. 跑 `pytest`、hero floors、HC3 sanity/100 benchmark；如任一 trip wire 触发立即停止并报告。

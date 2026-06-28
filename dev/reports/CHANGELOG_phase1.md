# 更新日志

## Phase 1: 改写端语义保护 — 术语保护 + 碎片语境感知 + 省略号砍掉 (2026-06-26)

### 关键改动

#### 1. 术语保护层集成（`--protect` flag）

集成自 `protect-terms-simple` 分支的 `_humanize_protect.py` + 68K 术语词典。

- `humanize_cn.py` 新增 `_USE_PROTECT_FLAG` / `_PROTECTION_SET` 全局变量 + `humanize(protect=False)` 参数
- 加载时推断 Top-3 领域术语（减小内存/算力，非全 68K 词扫描）
- `reduce_high_freq_bigrams` / `_simple_synonym_pass` / `ai_vocab_scrub` 三处加保护点，跳过位于受保护术语内部的同义词替换
- `rewrite_operations.py` `ai_vocab_scrub` 新增 `protected_set` 参数，从后向前替换 + blocked 位置集动态更新
- `humanize doctor` 加 `mini_dict.json` 状态检查
- 4.7MB 词典入 gitignore，按需用 `download_full_dict.py` 下载

解决 `数据隐私 → 数额隐私` 类误替换。

#### 2. `_FRAGMENTS` 分类 + 语境感知碎片注入

- `_FRAGMENTS` 单一混杂列表（18 条）→ 按 discourse relation + 情感极性 分 7 类（72 条）
- 新增 `scripts/weights/fragments_by_relation.json`（带学术支撑标注：PDTB-style Chinese / RST Chinese / Huang 2014 DM sentiment polarity / Lakoff hedge）
- 新增 `_pick_fragment` 选择算法：根据 discourse relation + sentiment + register 选碎片类
  - academic/legal/medical 语体 → 只允许 hedge
  - contrast 关系 → contrast 类
  - termination 关系 → comment_termination 类
  - positive 情感 → comment_positive
  - negative 情感 → comment_negative
  - neutral → comment_neutral + hedge 混合
- `fragment_injection` 重写：句末标点约束（修复"细胞代谢、。真的。增殖"）+ 全局上限 3 + 间距 ≥3 句 + 不在末句后插
- `burstiness_engineering` 拆点后不再插碎片 + 标点规范化
- 新增语境检查辅助函数：`_sentiment_of_sentence` / `_register_of_text`（强/弱 marker 分级）/ `_discourse_relation_of`（含 prev 句转折词检测 + termination 检测）

#### 3. 省略号滥用砍掉

- `punctuation_humanize` 第 451-458 行省略号添加逻辑直接砍掉
- 原触发条件只看长度+随机，不看末句语义，产生"势头不错……""确保了实验的可靠性……"等语义错位
- 省略号语用功能是未尽/沉思/留白，不是降低句号密度的工具；原文有省略号则保留

### 新增资产

- `scripts/_humanize_protect.py` — 术语保护层模块（ProtectLayer 类，mini/full 双模式）
- `scripts/data/mini_dict.json` — 68K 术语扁平列表（4.7MB，gitignore，按需下载）
- `scripts/download_full_dict.py` — 全领域词典下载脚本
- `scripts/weights/fragments_by_relation.json` — 7 类 72 条分类碎片词表（带学术支撑 _meta）
- `dev/semantic_integrity_check.py` — 独立语义完整度检查脚本（10 维 + 标点异常，零依赖，基于 MeaningBERT + ICLR 2026 多维框架）
- `dev/test_fragment_selection.py` — _FRAGMENTS 选择算法验收脚本
- `dev/test_fragment_selection_data.json` — 30 case 测试数据集（8 场景覆盖）

### 验收结果

`dev/test_fragment_selection.py` 30 case 验收：

| 指标 | 结果 | 门槛 |
|------|------|------|
| accuracy（选对类） | 96.7% | ≥70% ✓ |
| no_negative_in_positive | 100% | ≥95% ✓ |
| no_comment_in_academic | 100% | ≥95% ✓ |

真实改写 smoke test（`sample_academic.txt --adaptive`）：
- 省略号数：0（砍掉成功）
- 碎片断词：0（语境感知约束成功）
- 术语保护：`--protect` flag 生效，改写正常完成

### 不影响 academic 流程

所有改动只影响 general 流程的 adaptive 模式：
- `academic_cn.py` 不导入 `_humanize_protect`，不加 `--protect` flag
- `academic_cn.py` 不走 Pass 5（它有独立管线），不读 `_USE_PROTECT_FLAG` 全局变量
- 共享函数（`reduce_high_freq_bigrams` / `inject_noise_expressions` / `randomize_sentence_lengths`）不读保护全局变量，academic 调用不受影响

### 向后兼容

- `--protect` 默认关闭，不启用时行为与现在一致
- `--adaptive` 默认关闭，非 adaptive 模式跳过 Pass 5（碎片/省略号/术语保护均不触发）
- `_FRAGMENTS` 旧名单列表保留做向后兼容

### 学术支撑

- PDTB-style Chinese discourse annotation (Zhou & Xue, ACL 2012)
- Chinese RST annotation manual (Peng, Liu & Zeldes, Georgetown 2022)
- Chinese DM sentiment polarity (Huang et al., IEEE/WIC/ACM 2014)
- Formal Hedging in Chinese (sublearn 2026)
- MeaningBERT (Beauchemin & Saggion, Frontiers in AI 2023)
- Towards Human-Preferences Chinese Rewriting Evaluation (ICLR 2026)
- Centering Theory (Grosz, Joshi & Weinstein, ACL 1995)

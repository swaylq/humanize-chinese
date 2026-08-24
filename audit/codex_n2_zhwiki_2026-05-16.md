# N2 2010-11-09 zhwiki dump 解析报告

## 产物

- 脚本：`/Users/mac/claudeclaw/humanize/data/prepare_zhwiki_20101109.py`
- 原始 dump：`/Users/mac/claudeclaw/humanize/data/raw/zhwiki-20101109-pages-articles.xml.bz2`
- 全量 JSONL：`/Users/mac/claudeclaw/humanize/data/processed/zhwiki_20101109_schema_v1.jsonl`
- 样本 JSONL：`/Users/mac/claudeclaw/humanize/data/processed/zhwiki_20101109_schema_v1.sample.jsonl`
- 统计 JSON：`/Users/mac/claudeclaw/humanize/data/processed/zhwiki_20101109_schema_v1.stats.json`

## 实际指标

数据只从 Wikimedia 2010-11-09 zhwiki archive 下载 `zhwiki-20101109-pages-articles.xml.bz2`。首次 `curl -L -C -` 下载耗时约 1 分 43 秒；正式全量重跑时 dump 已在本地，因此脚本记录的 `download_seconds=0.0`。Wikimedia 该 dump 页面只提供 MD5，脚本校验官方 MD5 并计算本地 SHA256；MD5 为 `701e8613d84a170ee0025c168e25723a`，SHA256 为 `6073eb9a43c3c05334c1ad40bc53555a01deb9f4a584d238aa0ada6f38bd865b`。若本地存在同名 `.sha256` sidecar，脚本会额外校验 SHA256。

正式解析耗时 732.295 秒，总耗时 733.069 秒。共读取 798,675 个 page，保留 246,768 行 schema v1.0 JSONL。过滤项：redirect 306,475，namespace/meta 153,252，消歧义 17,881，stub 或清洗后正文低于 200 字 74,021，empty 1。去重项：全文 SHA256 精确重复 176，SimHash64 近重复 101。PII：strong-pattern redact 346 行，pending_review 5 行。`mwparserfromhell` 解析错误为 0。

全量输出大小 932,956,782 bytes，约 932.96 MB；样本 100 行，1,128,021 bytes。schema/license 抽查：246,768 行均有固定 27 个字段，`license=CC-BY-SA-3.0+GFDL` 且 `license_url=https://creativecommons.org/licenses/by-sa/3.0/`。

长度分桶：`100_300` 39,955；`300_800` 105,158；`800_1500` 50,429；`1500_plus` 51,226。粗 genre 分布：`geography` 115,137；`biography` 63,328；`other` 36,666；`history` 10,704；`science` 9,890；`culture` 5,809；`tech` 5,234。清洗 notes 统计：原始文本含 URL 141,666 行，含 ref 73,068 行，含表格 46,582 行。

## 样本摘录

1. `zhwiki_20101109_12`，genre=`biography`，char_len=11032：
> 数学是研究數量、结构、变化以及空间模型等概念的一門学科。透過抽象化和邏輯推理的使用,由計數、計算、量度和對物體形狀及運動的觀察中產生。數學家們拓展這些概念,為了公式化新的猜想以及從合適選定的公理及定義中建立起嚴謹推導出的定理。

2. `zhwiki_20101109_19`，genre=`history`，char_len=5400：
> 哲學是從希腊语 philo-sophia 轉變而來,意思為「热愛智慧」,或是比較少用的「智慧的朋友」。从西方學術史看,哲学衍生出科学。后来,哲学成为与科学并行的学科。

3. `zhwiki_20101109_21`，genre=`biography`，char_len=3819：
> 文学是指以语言文字为工具形象化地反映客观现实的艺术,包括戏剧、诗歌、小说、散文等,是文化的重要表现形式,以不同的形式表现内心情感和再现一定时期和一定地域的社会生活。

4. `zhwiki_20101109_24`，genre=`geography`，char_len=3723：
> 计算机科学用于解决信息与计算的理论基础,以及实现和应用它们的实用技术。计算机科学是对于信息与计算的理论基础以及它们在计算机系统中如何实现与应用的实用技术的学习。

5. `zhwiki_20101109_30`，genre=`history`，char_len=4542：
> 维基百科的目标是提供每一个人都可以自由使用的百科全书格式的信息。维基百科的内容依照知识共享 署名-相同方式共享 3.0协议和 GNU 自由文档许可证公开发行。

## 数据质量观察

整体可作为 pre-LLM 人类百科/说明文语料。正文段落保留为 `\n\n`，NFKC 后简繁不转换，简繁混排明显存在，符合 zhwiki 历史 dump 的自然状态。平均 `zh_ratio=0.5507`，中位长度 647 字，平均长度 1319.8 字；`zh_ratio<0.5` 有 97,270 行，主要来自数学、计算机、地名、人名、外文参考和多语 interwiki 残留，不建议直接按该阈值全删。

模板与 ref 清理总体有效；含表格页面多数转为线性文本，保留了一些枚举内容，但表格结构丢失。抽查发现约 2,266 行仍命中 `{{`、`[[`、`|}`、`<ref`、`table` 等残留模式，占保留行约 0.92%。样本早期曾出现 `Wikipedia:` 上传/删除日志，脚本已额外过滤 upload/deletion log；仍保留少量 `Wikipedia:` 项目说明页，因为任务要求保留 Main 与 Wikipedia 命名空间，但这部分不应在后续训练中高权重使用。

## 已知问题

- `genre` 是轻量关键词粗分类，存在误判：例如数学因开头人名命中 biography，计算机科学因“位于”等词可能误进 geography。建议 N7 前只把它当分层采样标签，不当强监督主题标签。
- SimHash64 使用字 3-gram 的确定性均匀采样，长文最多 256 个 3-gram。这样能把全量处理压到 12 分钟级，但近重召回低于全量 3-gram SimHash。若后续需要更强去重，可对输出 JSONL 再跑离线 MinHash/LSH。
- `Wikipedia:` 项目页仍有少量 meta/register 混入；建议训练采样优先 Main namespace，或按 `notes.title` 过滤 `Wikipedia:`。
- 表格转纯文本没有结构恢复，适合 LR 的 n-gram/风格特征，不适合需要事实表结构的任务。
- PII 只做 strong-pattern：手机、邮箱、身份证 redact；银行卡/医疗号 pending_review。真实姓名、用户名、IP 地址没有通用删除。

## 下游建议

N6 可直接从全量 JSONL 派生 `data/features/ngram_freq_cn_prellm_human.json`：读取 `label=human`、`pii_status in {clean,redacted}`，优先过滤 `zh_ratio>=0.5` 与 `char_len>=300`，再按字符 3-gram 统计全量频次。建议输出全量 top 50k 频次，同时给 LR 侧使用顶 3000 词项白名单，避免低频地名、人名、外文串放大 source shortcut。

N7 ablation 建议先加在 academic LR、general LR、longform LR 的 human 侧。参考 dataset plan 中 academic LR 35% 人类百科/说明文占比，不建议让 zhwiki 单源吃满 35%；第一轮可设 academic LR human 侧 zhwiki 15%-20%，general LR 10%-15%，longform LR 5%-10%，并做按长度桶均衡采样。若检测器出现“百科腔=human”的捷径，再降低 `1500_plus` 和 `Wikipedia:` 页权重。

## 完成标记

DONE: `/Users/mac/claudeclaw/humanize/code/humanize-chinese/audit/codex_n2_zhwiki_2026-05-16.md`
SAMPLE: `/Users/mac/claudeclaw/humanize/data/processed/zhwiki_20101109_schema_v1.sample.jsonl`
SCRIPT: `/Users/mac/claudeclaw/humanize/data/prepare_zhwiki_20101109.py`
FULL_OUTPUT: `/Users/mac/claudeclaw/humanize/data/processed/zhwiki_20101109_schema_v1.jsonl`（仅供审，不入 git）
ROW_COUNT: 246768
SIZE_MB: 932.96

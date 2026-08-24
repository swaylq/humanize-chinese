# N1 URL/license 审计与训练集 schema 定稿（2026-05-05）

本轮在 2026-05-05（Asia/Shanghai）用 `curl -L`、GitHub API、arXiv API、Hugging Face API 实访了 `codex_dataset_plan_2026-05-04.md` §2/§3 的候选。结论：无 404；但“页面可达”不等于“数据可训练”。直接可进入后续实验的优先级是 NLPCC-2025、2010 zhwiki、C-Eval/CMMLU 作为 prompt seed；M4/COLING 更适合 OOD/eval 或低权重训练；C-ReD 数据未开放，只能 watch；人民日报、ctext、Wayback、OCR 路线都有明确 license/PII/合同边界。

## Phase A：URL/license 审计

| 候选 | 状态/活跃度 | license 证据 | 数据规模/中文比例/入口 | 风险结论 |
| --- | --- | --- | --- | --- |
| NLPCC-2025 Task 1 <https://github.com/NLP2CT/NLPCC-2025-Task1> | HTTP 200；GitHub `pushed_at=2026-04-06`，README 更新到 2025-04-30；repo 未归档。 | GitHub API 无 SPDX license，仓库未见 LICENSE。README 有 “Data Restriction”：dev 只调参；禁止外部数据与 LLM 改写。 | 仓库直接含 `data/train.json` 47.1MB、`dev.json` 5.1MB、`test_with_label.json` 18.4MB；实测 `jq length` 为 train 32,400、dev 2,800、test 11,000。中文检测任务，训练源 ASAP/CNewSum/CSL，生成器 GPT-4o/GLM-4-flash/Qwen-turbo；测试 STORAL + DeepSeek-V3，Normal/Attack/Varying Lengths。GitHub/Google Drive 均可下载，无登录但比赛条款要留档。 | ROI 高；license 不完整，先做私有训练/评估资产，不随包分发原文。 |
| C-ReD arXiv <https://arxiv.org/abs/2604.11796> / repo <https://github.com/HeraldofLight/C-ReD> | 两者 HTTP 200；repo `pushed_at=2026-04-15`，README 仅 120B。 | GitHub API 无 license；README 只有 “Coming soon.”。 | arXiv v1 2026-04-13，标题为中文 real-prompt AIGC detection benchmark，声称资源发布在 GitHub；但仓库尚无数据文件。 | 极高潜力但当前不可准入；N4 watch，不要把论文描述当数据可用。 |
| CUDRT arXiv <https://arxiv.org/abs/2406.09056>；发现 repo <https://github.com/TaoZhen1110/CUDRT> | arXiv HTTP 200；repo HTTP 200，`pushed_at=2025-07-16`，默认分支 `LLMs`。 | repo 无 LICENSE，API 无 SPDX。README 说明 bilingual benchmark、C/U/D/R/T 五操作。 | 仓库主要是生成/检测代码；`DatasetAll/`、`DatasetFinal/` 只有 README，占位未放真实数据。树中可见中文 Baichuan/ChatGLM/GPT3.5/GPT4/Qwen 与英文 Llama2/3 等预处理脚本。 | 本地已有派生可做去重；公开 repo 不足以新增原始数据。license 阻塞。 |
| SemEval-2024 Task 8/M4 <https://github.com/mbzuai-nlp/SemEval2024-task8> / <https://arxiv.org/abs/2404.14183> | HTTP 200；repo `pushed_at=2024-04-22`，未归档。 | LICENSE 头部为 Apache License Version 2.0；README badge 指代码 license。数据来自 M4，比赛规则禁止额外训练数据。 | README 表示 multilingual，但测试集新闻只列 English/Arabic/German/Italian；训练/测试入口在 Google Drive/CodaBench，GitHub 只含代码、PDF、图片统计。中文比例未在可检索 README 文本中给出，需下载后按 `lang` 字段核算。 | 本地已有部分；不宜高比例进 LR，适合 OOD/attack/mixed eval。 |
| COLING 2025 GenAI Detection <https://arxiv.org/abs/2501.11012> / repo <https://github.com/mbzuai-nlp/COLING-2025-Workshop-on-MGT-Detection-Task1> | HTTP 200；repo `pushed_at=2025-01-19`，未归档。 | LICENSE 为 Apache-2.0；README 仍称 code license。 | README 给 Google Drive + HF。HF `Jinyan1/COLING_2025_MGT_multingual`：train 674,083、dev 288,894，字段有 `lang/model/label/text`，download 913MB；英文集 train 610,767、dev 261,758。中文比例 README 图片不可文本检索，需下载 parquet 统计。 | 可作多语 OOD；中文比例未知，不能预设收益。 |
| SuperCLUE <https://github.com/CLUEbenchmark/SuperCLUE> | HTTP 200；`pushed_at=2026-02-06`，活跃。 | API 无 license；README 未见明确数据许可。 | 中文评测基准/排行榜，README 提到 2023-12 OPEN 多轮题量 4,265；主要是 prompt/eval seed，不是 AI/human 检测语料。官网入口，无需 GitHub 登录。 | 仅作 synthetic prompt seed；license 不明，不纳入原文训练。 |
| C-Eval <https://github.com/hkust-nlp/ceval> | HTTP 200；`pushed_at=2025-07-27`，活跃。 | 代码 MIT；`LICENSE-DATA` 与 README 明确 C-Eval dataset 为 CC BY-NC-SA 4.0。 | README：13,948 道中文多选题，52 学科；HF `ceval/ceval-exam` lastModified 2025-07-27，language zh，size 10K<n<100K。GitHub 主仓本身不含完整 data 目录，需 HF/官方下载。 | prompt seed 好；NC/SA 不友好，若商业训练需隔离或只用题型元信息。 |
| CMMLU <https://github.com/haonan-li/CMMLU> | HTTP 200；`pushed_at=2024-12-06`，未归档。 | GitHub API 无 SPDX；README 许可证写 CC BY-NC-SA 4.0，HF card 写 `cc-by-nc-4.0`，存在 SA 不一致。 | README：67 个中文主题；GitHub `data/` 134 个 CSV，总 2.46MB；HF `haonan-li/cmmlu` 指到 `lmlmcat/cmmlu`，size 10K<n<100K。 | 可作 prompt seed；license 元数据冲突，按更严格 BY-NC-SA 4.0 处理。 |
| 2010 zhwiki dump <https://dumps.wikimedia.org/archive/2010/2010-11/zhwiki/20101109/> | HTTP 200；archive 页 timestamp 为 2010-11-09，多项 done。 | 页面链接 Wikimedia copyrights；文本应按当时 Wikipedia 内容许可处理（需在 N2 固化 attribution）。 | `pages-articles.xml.bz2` 462.5MB，798,675 pages；`pages-meta-current.xml.bz2` 579.6MB，1,152,243 pages；abstract zh-cn/zh-tw 各 341.8MB。免登录直接下载。 | pre-LLM human 首选；要剔除模板、讨论页、列表页，保留 attribution 和 dump 日期。 |
| 人民日报历史档案 <https://www.eastview.com/resources/newspapers/renmin-ribao/> | HTTP 200；商业产品页。 | 页面无开放许可；需 Request Trial/机构授权。 | 页面明示 archive 1946-May 31, 2012，Chinese，北京，full-text/full-image，100% searchable text，内容繁体，入口 Request Trial。 | 高价值但商业授权阻塞；不下载、不分发，只有合同明确才训练私有资产。 |
| ctext <https://ctext.org/> / license <https://ctext.org/tools/linked-open-data> | HTTP 200。 | license 页明示 RDF data 为 CC BY-NC-SA 3.0；需 attribution、non-commercial、share alike。 | 古籍/文言、LOD/RDF 入口；不是现代 register。 | 只做 old-human 旁路或排除测试；NC/SA 阻止商业默认训练。 |
| Wayback CDX <https://github.com/internetarchive/wayback/blob/master/wayback-cdx-server/README.md> | HTTP 200；repo `pushed_at=2024-03-01`。 | API 无 SPDX license；README 是 CDX server 文档，不是网页内容授权。 | 提供 Wayback CDX 查询接口文档；数据入口不等于目标页面版权许可。 | PII、robots、版权、模板噪声高；只能白名单小样本、只存派生特征或确认授权文本。 |
| PaddleOCR <https://github.com/PaddlePaddle/PaddleOCR> | HTTP 200；`pushed_at=2026-04-28`，活跃。 | LICENSE 头部 Apache License Version 2.0。 | 工具支持 100+ languages，PP-OCRv5、文档解析 JSON/Markdown；不是文本数据源。 | 工具许可友好；OCR 输入文本版权才是主要风险。 |
| Tesseract tessdata <https://github.com/tesseract-ocr/tessdata> | HTTP 200；`pushed_at=2024-03-09`。 | LICENSE Apache-2.0；README 写 all data in repository are Apache-2.0。 | 中文模型可用于 OCR；不是语料。 | 工具/模型可用；OCR 语料仍需公版或授权。 |

失效候选：本轮没有 HTTP 404/失效 URL。准入失败项是“可达但数据/许可不可用”：C-ReD（数据未发布）、CUDRT（数据目录占位且无 license）、人民日报（商业授权）、Wayback（CDX 不是内容授权）。替代搜索建议：C-ReD 关注 GitHub releases/issues 和 arXiv v2；CUDRT 关注 ACM DOI 补充材料、作者主页、Zenodo/HF；人民日报只走机构采购；Wayback 先找 CC/BY 或作者授权的老博客集合。

## Phase B：schema v1.0 定稿

正式字段：`schema_version/id/source/source_url/source_record_id/license/license_url/time_start/time_end/language/zh_ratio/register/genre/model/model_family/prompt_id/prompt_text/text/label/split/hash_sha256/simhash64/char_len/length_bucket/pii_status/normalize_version/notes`。

| 字段 | 类型/必填 | 约束与示例 |
| --- | --- | --- |
| `schema_version` | str/必填 | 固定 `"1.0"`，后续破坏性变更递增。 |
| `id` | str/必填 | 全局唯一，如 `zhwiki20101109_000001`。 |
| `source` | str/必填 | 规范源名，如 `nlpcc2025_task1`、`zhwiki_20101109`。 |
| `source_url` | str/必填 | 候选或下载 URL。 |
| `source_record_id` | str/可空 | 原始行号/题号/page id；无则 `null`。 |
| `license` | str/必填 | SPDX 或保守文本，如 `Apache-2.0`、`CC-BY-SA-3.0-or-GFDL`、`unknown-research-only`。 |
| `license_url` | str/可空 | license 文件或页面 URL。 |
| `time_start/time_end` | str/可空 | ISO date；AI 输出用生成日，历史 corpus 用覆盖时间。 |
| `language` | str/必填 | BCP-47，中文默认 `zh`，简繁不改写。 |
| `zh_ratio` | float/必填 | `[0,1]`，按 CJK 字符/总字数估算；中文训练建议 `>=0.6`。 |
| `register` | str/必填 | 枚举见下。 |
| `genre` | str/必填 | 枚举见下。 |
| `model` | str/可空 | `label="ai"` 必填，如 `deepseek-v3`；human 必须 `null`，不要写 `"human"`。 |
| `model_family` | str/可空 | `openai/qwen/deepseek/glm/baichuan/unknown/null`。 |
| `prompt_id` | str/可空 | 有 prompt 时必填；wiki/news/OCR 等无 prompt 用 `null`。 |
| `prompt_text` | str/可空 | synthetic 或公开 prompt 可存；版权/隐私敏感时只存 hash/摘要。 |
| `text` | str/必填 | normalize 后正文，100 字以上；原文另行冷存不进训练 jsonl。 |
| `label` | str/必填 | 枚举：`human`、`ai`、`mixed`。`mixed` 仅用于人机混写/攻击样本，不并入二分类训练主集，需切片评估。 |
| `split` | str/必填 | `train/dev/test/holdout`；同源相似文本不能跨 split。 |
| `hash_sha256` | str/必填 | `sha256(normalized_text)`，用于完整性和精确去重。 |
| `simhash64` | str/必填 | 64-bit hex，基于 char 5-gram，用于近重复聚类。 |
| `char_len` | int/必填 | normalize 后字符数。 |
| `length_bucket` | str/必填 | `100_300/300_800/800_1500/1500_plus`。 |
| `pii_status` | str/必填 | `clean/redacted/dropped/pending_review`。 |
| `normalize_version` | str/必填 | 当前固定 `cn_norm_v1`。 |
| `notes` | str/可空 | 准入限制、抽样说明、原始字段映射。 |

`register` v1：`qa_exam`、`news`、`encyclopedic`、`academic`、`creative_longform`、`blog_essay`、`social_comment`、`business_copy`、`official_policy`、`ocr_book`。  
`genre` v1：`qa`、`multiple_choice`、`abstract`、`article`、`news_report`、`editorial`、`wiki_page`、`paper_summary`、`story`、`novel`、`blog_post`、`forum_post`、`comment`、`ad_copy`、`proposal`、`ocr_page`、`rewrite`、`translation`、`mixed_attack`。

Normalize 规则 `cn_norm_v1`：对全文做 Unicode NFKC；统一全半角 ASCII、数字、常见标点；折叠连续空白为单空格；去 HTML/Markdown 模板、页眉页脚、免责声明和模型自述；保留简繁原貌，不做简繁转换；保留段落边界为 `\n`；删除控制字符。PII：手机号、邮箱、18 位身份证、QQ/微信号强模式直接 redact 为 `<PHONE>/<EMAIL>/<IDCN>/<ACCOUNT>`；含完整住址、银行卡、医疗号等进入 `pending_review`；真实姓名不做通用自动删除，只在“姓名+电话/身份证/住址”等组合命中时 redact 或 drop；私域社媒默认 drop。

reference jsonl 示例：

```jsonl
{"schema_version":"1.0","id":"zhwiki20101109_000001","source":"zhwiki_20101109","source_url":"https://dumps.wikimedia.org/archive/2010/2010-11/zhwiki/20101109/","source_record_id":"page:12345","license":"CC-BY-SA-3.0-or-GFDL","license_url":"https://dumps.wikimedia.org/legal.html","time_start":"2010-11-09","time_end":"2010-11-09","language":"zh","zh_ratio":0.96,"register":"encyclopedic","genre":"wiki_page","model":null,"model_family":null,"prompt_id":null,"prompt_text":null,"text":"南京长江大桥位于江苏省南京市，是连接市区南北交通的重要桥梁。","label":"human","split":"train","hash_sha256":"sha256:example01","simhash64":"0x0123456789abcdef","char_len":32,"length_bucket":"100_300","pii_status":"clean","normalize_version":"cn_norm_v1","notes":"示例短文本，真实训练需>=100字"}
{"schema_version":"1.0","id":"nlpcc2025_000001","source":"nlpcc2025_task1","source_url":"https://github.com/NLP2CT/NLPCC-2025-Task1","source_record_id":"train:0","license":"unknown-research-only","license_url":null,"time_start":"2025-02-27","time_end":"2025-04-30","language":"zh","zh_ratio":0.98,"register":"qa_exam","genre":"qa","model":"gpt-4o","model_family":"openai","prompt_id":"asap_000001","prompt_text":null,"text":"本文从两个方面说明城市绿化的意义：一是改善空气质量，二是提升居民生活体验。","label":"ai","split":"dev","hash_sha256":"sha256:example02","simhash64":"0x1111111111111111","char_len":38,"length_bucket":"100_300","pii_status":"clean","normalize_version":"cn_norm_v1","notes":"NLPCC license 待补"}
{"schema_version":"1.0","id":"syn_frontier_000001","source":"synthetic_frontier_2026q2","source_url":"internal://prompts/frontier/register_blog","source_record_id":"run:20260505:001","license":"internal-generated","license_url":null,"time_start":"2026-05-05","time_end":"2026-05-05","language":"zh","zh_ratio":0.99,"register":"blog_essay","genre":"blog_post","model":"deepseek-v3","model_family":"deepseek","prompt_id":"blog_essay_001","prompt_text":"写一篇关于通勤变化的中文博客。","text":"过去一年，我把通勤路线从地铁换成了骑行，最明显的变化不是节省时间，而是每天开始得更慢一些。","label":"ai","split":"train","hash_sha256":"sha256:example03","simhash64":"0x2222222222222222","char_len":48,"length_bucket":"100_300","pii_status":"clean","normalize_version":"cn_norm_v1","notes":"API ToS 单独归档"}
{"schema_version":"1.0","id":"ceval_prompt_000001","source":"ceval","source_url":"https://github.com/hkust-nlp/ceval","source_record_id":"advanced_mathematics:dev:1","license":"CC-BY-NC-SA-4.0","license_url":"https://github.com/hkust-nlp/ceval/blob/main/LICENSE-DATA","time_start":null,"time_end":null,"language":"zh","zh_ratio":0.94,"register":"academic","genre":"multiple_choice","model":null,"model_family":null,"prompt_id":null,"prompt_text":null,"text":"设函数在区间内连续，以下关于极值点的说法正确的是哪一项？","label":"human","split":"holdout","hash_sha256":"sha256:example04","simhash64":"0x3333333333333333","char_len":31,"length_bucket":"100_300","pii_status":"clean","normalize_version":"cn_norm_v1","notes":"仅示例；真实用途偏 prompt seed"}
{"schema_version":"1.0","id":"old_blog_2008_000001","source":"wayback_whitelist_blog","source_url":"https://web.archive.org/cdx","source_record_id":"example.com/post/2008","license":"permission-required","license_url":null,"time_start":"2008-01-01","time_end":"2008-12-31","language":"zh","zh_ratio":0.92,"register":"social_comment","genre":"forum_post","model":null,"model_family":null,"prompt_id":null,"prompt_text":null,"text":"今天论坛里讨论得很热闹，大家对新线路开通后的换乘时间有不少不同意见。","label":"human","split":"test","hash_sha256":"sha256:example05","simhash64":"0x4444444444444444","char_len":36,"length_bucket":"100_300","pii_status":"redacted","normalize_version":"cn_norm_v1","notes":"白名单授权后才可用"}
```

## Phase C：N2-N8 更新与顺序

推荐顺序：N2 与 N3 先跑，可并行；N4 持续 watch；N5 在 N3/N2 的 schema 映射稳定后跑；N6 依赖 N2 产物；N7 必须等 N2/N3/N5 至少各有小样本；N8 最后汇总。

| 任务 | 输入依赖 | 工作量 | 风险 | deliverable |
| --- | --- | --- | --- | --- |
| N2 2010 zhwiki 本地解析设计 | N1 schema；dump URL/license | M | trip wire 中；license 低；模板噪声中 | `data/prepare_zhwiki_20101109.py` 设计稿、`data/processed/zhwiki_20101109.schema_v1.sample.jsonl`、`audit/codex_n2_zhwiki_2026-05-xx.md` |
| N3 NLPCC-2025 准入实验 | N1 schema；NLPCC data | M | trip wire 中；license 中高 | `data/processed/nlpcc2025_schema_v1.jsonl`、三 LR one-corpus 报告 |
| N4 C-ReD watch | C-ReD repo/arXiv | S | 数据不开放概率高；license 高 | `audit/codex_n4_cred_watch_2026-05-xx.md`，含 release/license diff |
| N5 synthetic frontier 1000 小样本 | N1 schema；prompt seed；API ToS | M | trip wire 中；ToS/模型漂移中 | `data/private/synthetic_frontier_2026q2.schema_v1.jsonl`、prompt card、cost log |
| N6 pre-LLM ngram | N2 clean human | M | trip wire 低；license 低 | gitignored `data/features/ngram_freq_cn_prellm_human.json`、对比报告 |
| N7 三 LR one-corpus ablation | N2/N3/N5 小样本；既有 eval | L | trip wire 高；source shortcut 高 | `audit/codex_n7_lr_ablation_2026-05-xx.md`、更新后的模型系数候选 |
| N8 训练卡 | N7 结果；所有 license 记录 | S | license 漏标中 | `audit/training_card_dataset_expansion_2026-05-xx.md` |

Ship 标准：所有进入 `train` 的记录必须有 `schema_version=1.0`、`license`、`split`、`hash_sha256`、`simhash64`、`length_bucket`、`pii_status`；任何 `unknown-*` 或 `*-NC-*` license 数据默认只能进私有实验或 holdout，不能随开源包分发原文。

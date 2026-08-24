# humanize-chinese 训练集扩充方案（2026-05-04）

## 1. 现状盘点

本地 `/Users/mac/claudeclaw/humanize/data/` 约 79MB。按中文字符粗估，人类侧：HC3 human 约 288 万字，THUCNews 约 370 万字，新闻 jsonl 约 194 万字，多段新闻约 316 万字，Wiki academic/general 合计约 127 万字，小说约 19 万字，misc 约 24 万字，`pdaily_modern_corpus.txt` 为空。AI 侧：HC3 ChatGPT 包在 `hc3_chinese_all.jsonl` 内，整文件约 600 万中文字符；`ai_longform_corpus.jsonl` 170 条约 34 万字；M4/CUDRT OOD 合计约 47 万字。

已覆盖问答、新闻、百科/学术、现代长文和少量 2024/2025 多模型长文。缺口是：2025/2026 frontier 中文输出不足；pre-LLM 人类文本不足；社媒、学生作文、商业文案、早期博客、民国白话、纸书 OCR 等 register 缺失。三个 LR 链路为：general=`train_lr_multisource.py`，HC3+CUDRT+少量 longform；academic=`train_lr_academic.py`，AI 仍主要 HC3，human 为 Wiki+HC3 human；longform=`train_lr_longform.py`，AI longform vs human novel/news/multipara news，可选 M4/CUDRT。cycle 217 已证明 OOD 不能盲加。

## 2. 新 AI 模型输出候选

| 候选 | 新鲜度/中文/量级/许可/ROI/定位 |
| --- | --- |
| NLPCC-2025 Task 1 <https://github.com/NLP2CT/NLPCC-2025-Task1> | 中文检测任务，训练集含 ASAP/CNewSum/CSL，测试含 STORAL + DeepSeek-V3，Normal/Attack/Varying Lengths，量级万级。license/比赛条款需复核。ROI 高。训练时可行，runtime 纯净。 |
| C-ReD <https://arxiv.org/abs/2604.11796>，仓库 <https://github.com/HeraldofLight/C-ReD> | 2026 real-prompt 中文 AIGC 检测基准，最贴近目标。需等待/确认数据开放、license、字段。ROI 极高。训练时可行。 |
| CUDRT <https://arxiv.org/abs/2406.09056> | 中英双语，Create/Update/Delete/Rewrite/Translate 覆盖好。本地已有 Baichuan-Rewrite 派生，新增需去重。ROI 中高。训练时可行。 |
| SemEval-2024 Task 8/M4 <https://github.com/mbzuai-nlp/SemEval2024-task8>，论文 <https://arxiv.org/abs/2404.14183> | 多语言多域多模型，含中文但模型偏旧，本地已有部分。更适合作 OOD eval，不宜高比例进 LR。 |
| COLING 2025 GenAI Detection <https://arxiv.org/abs/2501.11012>，仓库 <https://github.com/mbzuai-nlp/COLING-2025-Workshop-on-MGT-Detection-Task1> | 多语 AI vs human，中文比例需进一步搜索。ROI 中。 |
| SuperCLUE/C-Eval/CMMLU prompts：<https://github.com/CLUEbenchmark/SuperCLUE>，<https://github.com/hkust-nlp/ceval>，<https://github.com/haonan-li/CMMLU> | 不是检测数据，但可作中文 prompt seed，生成考试解析、知识问答、说明文。训练时可行。 |

激进选项 1：自跑 API 生成 synthetic AI。模型池按官方可用模型滚动：OpenAI <https://openai.com/api/pricing/>、Anthropic <https://docs.anthropic.com/en/docs/about-claude/pricing>、Gemini <https://ai.google.dev/gemini-api/docs/pricing>、DeepSeek <https://www.deepseek.com/en/price>、Qwen/Alibaba <https://www.alibabacloud.com/help/en/model-studio/model-pricing>。建议 8-10 个 register，每 register 200-500 个 prompt，每 prompt 采 temperature 0.2/0.7/1.0，记录 model/date/prompt/response。成本几百到数千美元，ROI 最高；runtime 不受影响；风险是 ToS、模型漂移、prompt 太干净。

激进选项 2：购买或合作收集“真实用户 prompt + 模型原答 + 人类最终稿”。1-5 万条中文 pair 若 license 清楚，价值高于无来源 AI dump。训练时可行；若原文随开源包分发，会动摇产品定位和法律边界。

## 3. pre-LLM 人类文本候选

| 候选 | 时间/风格/量级/风险/定位 |
| --- | --- |
| 2010 zhwiki dump <https://dumps.wikimedia.org/archive/2010/2010-11/zhwiki/20101109/> | 2010-11-09，百科/说明文，OCR 零错误，许可相对清晰，百 MB 级。ROI 高。训练时可行，runtime 只带派生统计。 |
| 人民日报历史档案 <https://www.eastview.com/resources/newspapers/renmin-ribao/> | 1946-May 31 2012 full text/full image。新闻/评论/政论文价值高，商业授权。只在授权明确时使用，不分发原文。 |
| ctext <https://ctext.org/>，license <https://ctext.org/tools/linked-open-data> | 古籍/文言，CC BY-NC-SA 3.0。可作 old-human 旁路或排除测试，不宜大比例进现代 LR。 |
| Wayback CDX <https://github.com/internetarchive/wayback/blob/master/wayback-cdx-server/README.md> | 1998-2010 老博客/个人站/论坛公开页。风格稀缺；风险是 PII、robots、版权、模板噪声。只做白名单小样本。 |
| 民国报刊/图书馆资源 | 民国白话、杂志、小说、新闻。需逐库确认授权；OCR 错误率约 1-8%。训练时可行，公开分发风险高。 |
| 当代纸书 OCR | 工具可用 PaddleOCR <https://github.com/PaddlePaddle/PaddleOCR> 或 Tesseract 中文模型 <https://github.com/tesseract-ocr/tessdata>。只走公版或签约授权；否则跳过。 |

OCR 路线应先做版面检测、OCR、页眉页脚/页码/目录/版权页清理、繁简字段保留、抽样人工估错，并用乱码率、非汉字率、重复行率、异常单字率硬过滤。

## 4. 架构方案

general LR：AI 侧建议 HC3 25%、CUDRT/M4 15%、NLPCC/C-ReD 30%、自采 frontier 20%、longform 10%；人类侧 HC3 20%、THUCNews/现代新闻 25%、2010 zhwiki 20%、pre-2020 博客/评论 15%、小说/杂文 20%。单来源不超 30%，单 register 不超 35%。

academic LR：修正 AI 侧过旧问题。AI 用 HC3 academic-like 20%、NLPCC CSL/CNewSum 25%、C-ReD/自采学术说明文 35%、CUDRT rewrite/translate 20%。人类用 2010 zhwiki 35%、现有 wiki_academic 25%、pre-2020 学术百科/教材 20%、HC3 human 20%，避免 Wiki token 成为 label shortcut。

longform LR：AI 加 NLPCC STORAL DeepSeek-V3、C-ReD 长文、自采 frontier 长博客/小说/方案；人类补 pre-LLM 小说、民国白话杂志、长新闻、老博客。建议人类小说:新闻:杂文:博客=3:3:2:2；AI creative:expository:rewrite:business=3:3:2:2。cycle 217 的 OOD 只作 ablation，不默认合入。

暂不新增 runtime 第四 LR。先加 eval slice：`human_pre1950`、`human_1950_2010`、`human_2010_2020`、`ai_2023`、`ai_2025_2026`、`ai_attack`。ngram 建议新增 gitignored `ngram_freq_cn_prellm_human.json`；`ngram_freq_cn_frontier_ai_eval.json` 只做分析。小 encoder/BERT finetune 可作训练期 teacher，不建议进 runtime，否则会动摇“零 LLM、纯 Python、离线轻量”定位。新 feature 入 LR 前仍要求 Cohen d > 0.6，并同步重训三个 LR。

## 5. Pipeline 设计

采集脚本放 workspace `data/collect_<source>_<yyyy>.py`，解析放 `data/prepare_<source>.py`，训练仍在 repo `scripts/`。统一 jsonl schema：`id/source/source_url/license/time_start/time_end/register/genre/model/prompt_id/text/label/split/hash/notes`。清洗做 NFKC、全半角统一、HTML 正文抽取、繁简保留、100-300/300-800/800-1500/1500+ 分桶、SimHash + char 5-gram 去重、去 prompt 泄漏/模型自述/免责声明/Markdown 模板、PII 粗过滤。

Backlog：N1 URL/license 审计与 schema 定稿；N2 2010 zhwiki 本地解析设计；N3 NLPCC-2025 准入实验；N4 C-ReD watch；N5 synthetic frontier 1000 条小样本；N6 pre-LLM ngram；N7 三 LR one-corpus ablation；N8 训练卡。评估闭环：每加一个 corpus，跑 HC3 holdout、hero、academic、longform、social smoke、pre-LLM human、新 AI frontier、attack。Trip wire：核心准确率下降 >1pp、人类 FP 上升 >2pp、longform holdout 下降 >1.5pp 即回退。

## 6. Roadmap

保守版，1-3 个月：只用公开/许可清晰数据，不新增 runtime 依赖。Sprint 1 审计 NLPCC/M4/CUDRT/C-ReD；Sprint 2 加 2010 zhwiki 和 pre-LLM eval slice；Sprint 3 对三个 LR 做小比例 ablation；Sprint 4 只合入不触发 trip wire 的组合。目标：新增 50-100 万字 pre-LLM human、20-50 万字新 AI eval/training，核心集不降，frontier slice F1 提升 3-5pp。回退：只保留 eval slice 和 gitignored ngram。

激进版，6-12 个月：训练期允许 API、OCR、采购和合作。前 2 个月自采 2-5 万条 frontier 中文 synthetic AI；3-6 个月谈新闻/报刊/作者授权，建立 500-1000 万字 pre-LLM human；6-9 个月做 OCR pipeline；9-12 个月尝试 teacher encoder 做 feature discovery。目标：覆盖 8+ 最新模型、10+ register、5 个时间段，attack slice 提升，old-human FP 降低。回退：激进数据留私有训练资产，runtime 只发布系数和派生统计。

## 7. 风险 + 不做建议

cycle 217 教训要制度化：不按“量大”合入，只按 register-balanced、time-balanced、one-corpus-at-a-time 合入。跳过或后置：无 license AI dump、CNKI/维普/读秀批量全文、未授权当代纸书 OCR、古籍全量进 LR、私域社媒抓取、Wayback 模板页、只含英文的新检测数据。法律重点是版权、数据库合同、robots/ToS、PII、作者同意、可再分发范围。runtime 的“零 LLM、零 API、零联网”可以保持，但训练资产必须标清哪些是训练期破例，哪些不能随开源包分发。

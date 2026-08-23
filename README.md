# 🔧 中文 AI 文本去痕迹工具 &nbsp;[![Tweet](https://img.shields.io/badge/share%20on-Twitter%2FX-000000?style=flat-square&logo=x)](https://twitter.com/intent/tweet?text=humanize-chinese%20%E2%80%94%20%E5%85%8D%E8%B4%B9%E6%9C%AC%E5%9C%B0%E8%BF%90%E8%A1%8C%E7%9A%84%E4%B8%AD%E6%96%87%20AI%20%E6%96%87%E6%9C%AC%E5%8E%BB%E7%97%95%E8%BF%B9%E5%B7%A5%E5%85%B7%EF%BC%8C%E6%A3%80%E6%B5%8B%20%2B%20%E6%94%B9%E5%86%99%E4%B8%80%E6%AD%A5%E5%88%B0%E4%BD%8D%EF%BC%8C%E9%9B%B6%20LLM%20%E9%9B%B6%20API%20Key&url=https%3A%2F%2Fgithub.com%2Fswaylq%2Fhumanize-chinese&hashtags=AIGC%2C%E4%B8%AD%E6%96%87NLP%2C%E5%BC%80%E6%BA%90%E5%B7%A5%E5%85%B7)

**中文文章去 AI 腔。离线免费可用，也可以接大模型做得更彻底。**

[![GitHub stars](https://img.shields.io/github/stars/swaylq/humanize-chinese?style=flat-square)](https://github.com/swaylq/humanize-chinese)
[![ClawHub](https://img.shields.io/badge/clawhub-humanize--chinese-blue?style=flat-square)](https://clawhub.com/skills/humanize-chinese)
[![License: MIT Non-Commercial](https://img.shields.io/badge/License-MIT_Non--Commercial-yellow?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.6+-blue?style=flat-square)](https://python.org)
[![Claude Code](https://img.shields.io/badge/Claude_Code-compatible-orange?style=flat-square)](#claude-code)

---

## 30 秒看效果

一份典型的工作汇报，满篇套话：

**改写前**
> 随着业务的不断发展，本季度团队在多个层面取得了显著进展。值得注意的是，通过深度优化业务流程，我们不仅全方位提升了工作效率，更进一步赋能了公司核心战略，充分体现了多维度协同的价值。
>
> 首先，技术团队聚焦核心系统的稳定性建设，持续推动业务长效发展。其次，产品团队基于用户洞察，打造了更具竞争力的解决方案。综上所述，团队凝聚力得到进一步增强，为下一季度的发展奠定了坚实基础。

**改写后**
> 本季度团队在多个层面取得了显著进展。通过优化业务流程，我们提升了工作效率，也支持了公司核心战略，多方协同在其中起了作用。
>
> 技术团队推进核心系统的稳定性建设，支撑业务持续运行。产品团队基于用户洞察，提出了更有竞争力的解决方案。团队凝聚力也得到进一步增强。

「随着业务的不断发展」「值得注意的是」「赋能」「多维度」「综上所述」都没了，
事实一个没少，句子读着顺。

```bash
./humanize rewrite 汇报.txt --llm -o 改后.txt
```

---

## 三种用法，按你手上有什么选

| 命令 | 做什么 | 要不要 API key |
|---|---|---|
| `./humanize rewrite 文件.txt` | 只调整断句节奏，不动一个字 | 不要，离线免费 |
| `./humanize rewrite 文件.txt --llm` | 拆掉套话和模板句式，再调节奏 | 要 |
| `./humanize write "写一篇讲复利的科普"` | 从零写一篇本来就没有 AI 腔的 | 要 |

离线那档很保守：它只移动标点，去掉标点后前后文字必须一模一样，程序会校验。
碰上没法安全改的地方，它会直接告诉你「没有可以安全修改的地方」，
而不是硬改出病句。

---

## 改完还能读，这是重点

改写工具最常见的失败不是改得不够，是**改出了不是中文的句子**。
比如把「打造了更具竞争力的解决方案」换成「做出了更具竞争力的解决方案」——
「做出」不搭配「方案」。或者为了让句子变短，从不该断的地方断开：
「通过优化业务流程。我们提升了工作效率」，前半句不是一句话。

所以每次改写都要过两道关：

1. **事实关**：原文的数字、人名、专有名词、段落数，少一个就打回重做。
2. **通顺关**：三个大模型各自读一遍打分，并把觉得不通的句子原样抄出来。
   两个以上都指出同一句，就打回重做。三次还不过，**原样返回，不改**。

拿仓库里五份样本实测（1-5 分，3 个模型评审）：

| | 通顺度 | 病句 |
|---|---|---|
| 本工具 | 4.0 - 5.0 | **0 处** |
| 上一版的纯规则改写 | 2.0 | 5 - 17 处 |

宁可不改，也不写病句。

## 关于「AIGC 率」这个分数，先说清楚

这个工具带一个 0-100 的检测分。**但我们自己实测下来，这个分数不能当目标去优化，
只能当参考。** 三个数字说明为什么：

**一、真人写的论文也会被判成 AI。**
拿 60 篇真实的知网论文摘要（发表时间早于大模型）去跑，平均分 60，
其中 35% 落在「几乎确定是 AI」那一档。中文学术论文本来就爱写「综上所述」
「与此同时」，检测器分不出这是文体还是机器。

**二、对 2026 年的模型，它基本失效了。**
同题目同长度做对照：面对 2024 年的模型，它能把 AI 和真人分开（准确率约 96%）；
换成今年的模型，准确率掉到 64%，而瞎猜是 50%。

**三、长文场景它的方向是反的。**
50 篇模型写的博客对 50 篇真人写的博客，**真人那批的分数反而更高**。
也就是说，你拿它筛长文，它会让你去改真人写的文章，放过模型写的。

外面商用检测器的情况也类似：同一批文字，有的工具给 0 分，有的给 99.9 分；
朱自清的《荷塘月色》在某个工具上被判 62.88%。

**所以本工具的目标是「改完读起来像人写的」，不是「把分数压低」。**
上一版为了压分数去乱换同义词、插入过渡句、打乱句子顺序，分数确实降得多，
但改出来的是病句。那条路我们不走了。想看旧版行为：加 `--legacy`。

---

## 📚 技术基础（参考论文）

本项目的检测算法不是拍脑袋设的，每一条特征都对应一篇 paper 或研究发现：

| 技术 | 来源论文 / 数据集 | 作用 |
|---|---|---|
| **HC3-Chinese** 校准 | [Hello-SimpleAI/chatgpt-comparison-detection](https://github.com/Hello-SimpleAI/chatgpt-comparison-detection) | 12,853 对人类/ChatGPT 真实问答，所有阈值在此数据集 300+300 样本上校准 |
| **DivEye 惊奇度** | [Basani & Chen, TMLR 2026](https://arxiv.org/abs/2502.00258) | 字符级 surprisal 时间序列的 skew/kurtosis/spectral flatness |
| **GLTR rank 分桶** | [Gehrmann et al., ACL 2019](https://arxiv.org/abs/1906.04043) | AI 倾向选 top-10 概率字，人类更分散 |
| **Fast-DetectGPT** | [Bao et al., ICLR 2024](https://arxiv.org/abs/2310.05130) | 局部曲率：AI 文本在模型预测下曲率低 |
| **Binoculars** | [Hans et al., ICML 2024](https://arxiv.org/abs/2401.12070) | 两个模型 perplexity 比值区分 AI / 人类 |
| **MPU (AIGC_detector_zhv2)** | [Tian et al., ICLR 2024](https://arxiv.org/abs/2305.18149) | 中文 AIGC detector 的 PU learning 范式 |
| **Ghostbuster 多尺度 ngram** | [Verma et al., NAACL 2024](https://arxiv.org/abs/2305.15047) | 多个 weak LM 的 log-prob 特征组合 |
| **Chinese AIGC 深度学习检测** | [AIMS 2025](https://www.aimspress.com/article/doi/10.3934/bdia.2025016) | 中文 AI 文本的句长方差、标点密度等特征 |
| **psycholinguistic 差异** | [arxiv 2505.01800](https://arxiv.org/abs/2505.01800) | 人类写作的具体名词/命名实体密度更高 |
| **Stumbling Blocks taxonomy** | [Wang et al., ACL 2024](https://arxiv.org/abs/2402.11638) | AI 检测攻击面地图 |
| **CNKI 三链路情报** | [linggantext 技术博客](https://www.linggantext.com/public/blog/cnki-aigc-detection-guide-2026/) | 知网 AIGC 3.0 官方「语言模式/语义逻辑/知识增强」三链路 |
| **CiLin 同义词词林** | 哈工大 LTP 同义词词林扩展版 | 38,873 词的同义词映射，`--cilin` 可选启用 |

**非商业使用免费，任何用户都可以复现所有数值。**

---

## 安装

```bash
# 方式一：ClawHub
clawhub install humanize-chinese

# 方式二：Git Clone
git clone https://github.com/swaylq/humanize-chinese.git

# 方式三：Claude Code Skill
npx skills add https://github.com/swaylq/humanize-chinese.git
```

不需要 `pip install` 任何东西。下载就能用。

---

## Claude Code

4 个 slash command，复制到 `.claude/commands/` 即可：

```bash
git clone https://github.com/swaylq/humanize-chinese.git
cp humanize-chinese/claude-code/*.md YOUR_PROJECT/.claude/commands/
```

然后在 Claude Code 里：

```
/detect 综上所述，人工智能技术在教育领域具有重要的应用价值...
/humanize 本文旨在探讨人工智能对高等教育教学模式的影响...
/academic 论文.txt
/style xiaohongshu 在当今快节奏的生活中...
```

| 命令 | 功能 |
|------|------|
| `/detect` | AI 痕迹检测，0-100 评分 |
| `/humanize` | 去 AI 味改写 |
| `/academic` | 学术论文 AIGC 降重 |
| `/style [风格]` | 风格转换（7 种） |

---

## 快速上手

### 统一 CLI（推荐）

```bash
./humanize --list
./humanize detect 论文.txt                       # 检测
./humanize academic 论文.txt -o 改后.txt --compare # 学术降重
./humanize rewrite text.txt --quick -o clean.txt  # 通用改写（极速）
./humanize style text.txt --style xiaohongshu     # 风格转换
./humanize compare text.txt -a                    # 前后对比
./humanize <sub> --help                           # 子命令帮助
```

底层依然是各 `scripts/*_cn.py` 独立脚本，`./humanize` 只是分发器，直接调用旧脚本也完全 OK。

### 🎓 学术论文降 AIGC 率

```bash
./humanize academic 论文.txt                      # 只检测
./humanize academic 论文.txt -o 改后.txt --compare  # 改写 + 对比
./humanize academic 论文.txt -o 改后.txt --quick    # 快速模式（跳过统计，~18× 速度）
./humanize academic 论文.txt -o 改后.txt -a --compare  # 激进模式
```

### 🔍 通用文本去 AI 味

```bash
./humanize detect text.txt -v           # 检测（详细）
./humanize rewrite text.txt -o clean.txt # 改写
./humanize rewrite text.txt --quick      # 纯替换，极快
./humanize compare text.txt -a           # 对比
```

### 📚 长篇小说 / 博客（--scene novel / --scene auto）

默认 detector 用 HC3 短问答校准，对 GPT-4o/Claude/Gemini 写的长篇小说、长博客会系统性欠估。两种修正方式：

```bash
python scripts/detect_cn.py 章节.txt --scene novel     # 显式：小说/长博客/散文/长新闻
python scripts/detect_cn.py 稿件.txt --scene auto      # 按长度自动选（≥1500 中文字符走长篇 LR）
python scripts/detect_cn.py 短问答.txt                 # 默认 scene（短问答/通用）
python scripts/detect_cn.py 论文.txt --scene academic  # 学术论文（显式 opt-in）
```

长篇 LR 专训在 170 条 AI 长文本（5 家 LLM × 5 类：小说/学术/新闻/博客/评论）+ 170 条人类长文本（v3ucn 小说 + CNewSum 新闻 + 博客）上，holdout 89.7%。

实测对照（3 篇 Gemini-2.5-flash 新写小说章节，约 2800-3200 字）：

| 模式 | 样本1 | 样本2 | 样本3 | 均值 |
|------|-------|-------|-------|------|
| 默认 scene（HC3 校准） | 52 | 38 | 70 | 53 |
| **--scene novel / auto** | **63** | **57** | **82** | **67** |

默认模式对现代 LLM 的长篇创作欠估 ~15 分，切 `--scene novel` 或 `--scene auto` 可修正。混合长度输入推荐 `--scene auto` —— 短文本仍走 general，长文本走长篇 LR。

### 🎨 风格转换

```bash
./humanize style text.txt --style xiaohongshu   # 小红书
./humanize style text.txt --style zhihu         # 知乎
./humanize style text.txt --style weibo         # 微博
./humanize style chapter.txt --style novel      # 小说/长篇叙事
```

8 种风格：口语化 / 知乎 / 小红书 / 公众号 / 学术 / 文艺 / 微博 / **小说**

`--style novel` 专为长篇叙事设计：humanize 后剔除 AI 写小说时常混入的元说明（"我将按照您的要求创作..."、"故事梗概"、"本次写作"）+ markdown 章节头 (## ###) + 大纲 bullet (- **关键点**：) + 分隔线，保段落不加 emoji/hashtag。处理长篇章节、博客时观感更干净。

风格转换会先自动跑一遍 humanize，去掉 AI 高频词，再套风格。`--no-humanize` 关闭。

---

## 功能一览

| 功能 | 说明 |
|------|------|
| 🔍 AI 检测 | 20+ 规则维度 + **三路 LR 分场景校准**（general / academic / novel），0-100 评分 |
| 📈 统计层 | 字符级 trigram 困惑度 + DivEye 惊奇度 + GLTR rank 分桶 + 句长 burstiness + 标点密度 |
| ✏️ 智能改写 | 困惑度引导选词 + 低频 bigram 注入 + 短句插入 + 句长随机化 + **40 paraphrase 模板** + **144 条短语替换** + 三档自适应强度 + **多段 \n\n 段落保留**（长篇章节不丢结构）|
| 🎓 学术降重 | 10 维度检测（含扩散度）+ **126 条学术替换** + 独立 picker 策略，针对知网/维普/万方 |
| 🎨 风格转换 | 8 种中文写作风格（知乎/小红书/微博/公众号/学术/文艺/口语化/**小说**） |
| 📊 前后对比 | 学术分 + 通用分双评分，改写效果一目了然 |
| 🔄 可复现 | `--seed` 保证相同输入相同输出 |
| ⚡ 速度 | 10k 字符 `--quick` 模式 0.3 秒，完整模式 5 秒 |
| 📦 零依赖 | 纯 Python 标准库，下载即用。可选 CiLin 词林（`--cilin`，38873 词 + 语义过滤） |
| 📐 基准测试 | HC3-Chinese 12853 对人类/AI 真实问答回归测试（200 样本 fused 模式 95.5% 正确率）|

---

## 🎓 学生党必看

用 ChatGPT / DeepSeek 写了论文初稿？三步搞定：

```bash
# 1. 看看 AIGC 率多高
python scripts/academic_cn.py 论文.txt

# 2. 一键改写
python scripts/academic_cn.py 论文.txt -o 改后.txt --compare

# 3. 不够就开激进模式
python scripts/academic_cn.py 论文.txt -o 改后.txt -a --compare
```

**工具做了什么：**
- "本文旨在" → "本研究聚焦于"
- "被广泛应用" → "得到较多运用"
- 打破每段一样长的结构
- 加入"可能""在一定程度上"等学术犹豫语
- "研究表明" → "笔者认为""前人研究发现"
- 基于 HC3-Chinese Cohen's d 校准的统计特征，学术词表禁用口语候选（不会把"应用"改成"施用"）

⚠️ 改完通读一遍，确认专业术语没被误改、引用格式正确。建议用知网 AMLC 或维普验证。

---

## 评分标准

| 分数 | 等级 | 含义 |
|------|------|------|
| 0-24 | 🟢 LOW | 基本像人写的 |
| 25-49 | 🟡 MEDIUM | 有些 AI 痕迹 |
| 50-74 | 🟠 HIGH | 大概率 AI 生成 |
| 75-100 | 🔴 VERY HIGH | 几乎确定是 AI |

⚠️ **这张表的档位名称在学术和长文场景下不准。** 实测 60 篇真实知网论文摘要，
平均落在 60 分、35% 进了「几乎确定是 AI」那一档 —— 它们都是真人写的。
把这个分数当参考可以，当验收标准不行。见上文「关于「AIGC 率」这个分数」。

---

## 技术原理

### 规则层（看词）

三段式套路、机械连接词、空洞宏大词、AI 高频词、模板句式、段落结构均匀度。规则都在 `scripts/patterns_cn.json`，可以自己改。

### 统计层（看分布）

所有阈值都基于 HC3-Chinese 300+300 人类-AI 对照样本的 Cohen's d 校准，不是拍脑袋设的。

**1. 句长 burstiness (最强信号)** — AI 中文爱写 15-25 字等长句，人类长短交错。灵感来自 AIMS 2025 中文深度学习 AIGC 检测 paper + 知网语言模式链情报。
   - 句长变异系数 CV (HC3 **Cohen's d = 1.22** — 人类 0.52 vs AI 0.32)
   - 短句占比 (< 10 字的句子比例，HC3 **Cohen's d = 1.21** — 人类 25% vs AI 2.6%)

**2. 困惑度 (Perplexity)** — 字符序列的平均负对数概率（d = 0.47）。基于 `scripts/ngram_freq_cn.json` 训练语料的字符级 3-gram。

**3. GLTR rank 分桶** ([Gehrmann et al. ACL 2019](https://arxiv.org/abs/1906.04043))
   - top-10 bucket 占比（AI 更集中在高概率字，d = 0.44）

**4. DivEye surprisal 时间序列** ([Basani & Chen TMLR 2026](https://arxiv.org/abs/2502.00258))
   - skew（d = 0.41）、excess_kurt（d = 0.29）、spectral_flatness（d = 0.20）

**5. 逗号密度** — 有趣发现：AIMS 2025 paper 说「AI 标点密」但 HC3 实测相反。Q&A corpus 里人类写 casual 文本用更多 commas（4.82/百字 vs AI 3.82/百字，d = -0.47）。加了 `low_comma_density` 指标。

所有 statistical indicators 总分上限 25，和规则层（上限 75）加成最终 0-100。

### 智能改写

**Picker 策略**：每次替换从多候选中选「困惑度次高」的（最高的常是古语/错字，次高才是自然人类选择）。学术场景额外禁用 30 个口语候选 + 37 个 AI 触发词候选。

**三档自适应强度**：
- score < 5：**conservative** — 仅短语替换 + 标点清理
- 5 ≤ score < 25：**moderate** — +restructure + bigram
- score ≥ 25：**full** — 全量（含噪声注入 + 句长随机化）

避免对已经够干净的文本乱加噪音反而更像 AI。

**其他技术**：
- 低频 bigram 注入（把 "系统" × 6 的重复 60% 换成 "架构""体系""框架"）
- 句长随机化（避免每句差不多长，但保留"X指出，Y"等 attribution 结构）
- 段落感知（每一步按 `\n\n` 分段处理，不丢段落结构）
- 可选 CiLin 同义词词林扩展（`--cilin`，38,873 词 JSON）

---

## CLI 参数速查

统一 CLI 形式（推荐）：

```bash
./humanize detect   [file] [-v] [-s] [-j]
./humanize rewrite  [file] [-o out] [--scene S] [--style S] [-a] [--seed N] [--quick] [--cilin] [--best-of-n N] [--score-mode lr|fused|lr+rule]
./humanize academic [file] [-o out] [--detect-only] [-a] [--compare] [--quick]
./humanize style    [file] --style S [-o out] [--no-humanize]
./humanize compare  [file] [-o out] [--scene S] [-a]
./humanize doctor
```

等价的独立脚本形式：

```bash
python scripts/detect_cn.py [file] ...
python scripts/humanize_cn.py [file] ...
python scripts/academic_cn.py [file] ...
python scripts/style_cn.py [file] --style S ...
python scripts/compare_cn.py [file] ...
python scripts/check_assets.py
```

| 参数 | 说明 |
|------|------|
| `-v` | 详细模式，显示最可疑的句子 |
| `-s` | 只输出评分 |
| `-j` | JSON 输出 |
| `-o` | 输出文件 |
| `-a` | 激进模式 |
| `--seed N` | 固定随机种子 |
| `--quick` | 纯替换 + 结构还原，跳过统计优化（**~18× 速度**） |
| `--no-stats` | 关闭统计优化 |
| `--no-noise` | 关闭噪声注入和句长随机化 |
| `--cilin` | 开启 CiLin 同义词扩展（humanize） |
| `--best-of-n N` | 跑 N 个候选取 LR 最低（默认 20，0 关闭，N 倍延迟） |
| `--debug-best-of-n` | 打印每候选的 scene LR / 主要贡献到 stderr |
| `--score-mode` | best-of-n 排序：`lr`（默认 scene-aware）/ `fused` / `lr+rule` |
| `--secondary-weight` | secondary signal 权重（默认 0.2，0 关闭） |
| `--compare` | 改写前后双评分对比（academic） |
| `--no-humanize` | style 转换前不先去 AI 词 |

### 数据资产状态

fresh clone 可以离线运行，不会自动联网下载数据。但 3 份本地高阶 ngram 频率表不入库：

- `scripts/ngram_freq_cn_human.json`：启用 Binoculars-like `bino_lp_diff`，也影响 best-of-n secondary signal。
- `scripts/ngram_freq_cn_wiki.json`：启用 `wiki_vs_human` / `wiki_vs_primary` LR 特征。
- `scripts/ngram_freq_cn_news.json`：启用 `news_vs_human` LR 特征。

缺少这些文件时程序会 graceful fallback，相关特征按 0.0 处理；detect/rewrite 不会崩，但 LR 分数、best-of-n 排序和 README hero 分数可能与完整本地资产环境不同。查看当前状态：

```bash
./humanize doctor
```

如需完整资产，请先准备本地语料，再离线重训：

```bash
python scripts/train_ngram_human.py
python scripts/train_ngram_wiki.py
python scripts/train_ngram_news.py
```

---

## 批量处理

```bash
for f in *.txt; do echo "=== $f ===" && ./humanize detect "$f" -s; done
for f in *.md; do ./humanize rewrite "$f" -a -o "${f%.md}_clean.md"; done
```

---

## 对比 Humanizer-zh

和 [Humanizer-zh](https://github.com/op7418/Humanizer-zh)（5k⭐）的区别：

| | 本项目 | Humanizer-zh |
|---|---|---|
| 运行方式 | ✅ 独立 CLI，终端直接跑 | 纯 prompt，必须在 Claude Code 内用 |
| 依赖 | 离线档零依赖零 token；接大模型的两档需要 API key | 需要 Claude Code + API 额度 |
| 量化评分 | ✅ 0-100 分（学术 + 通用双尺度） | ❌ 无评分 |
| 统计检测 | ✅ 困惑度 + DivEye + GLTR，HC3 校准 | ❌ 无 |
| 学术模式 | ✅ 10 维度 + 126 条替换 | ❌ 无 |
| 风格转换 | ✅ 7 种 | ❌ 无 |
| 可复现 | ✅ `--seed` | ❌ 每次不同 |
| 批量处理 | ✅ CLI 管道 | ❌ 只能单篇交互 |
| 免费 | ✅ 完全免费 | ⚠️ 需要 API 额度 |
| 基准测试 | ✅ HC3-Chinese 200 样本回归 | ❌ 无 |

简单说：Humanizer-zh 是个好 prompt，但只能在 Claude Code 里用。我们是独立工具，任何环境都能跑，而且每次改动都有 HC3 回归验证。

---

## 局限

- **融合检测让分数差距拉大**：v4.0.0 默认用 rule+stat + LR ensemble 融合评分，真实 ChatGPT 回答也能清晰区分。刻板化 AI 文本（论文模板/小红书腔）降幅 80-90 分；自然 ChatGPT 文本降幅 30-40 分。
- **统计层不用神经网络**：我们用字符级 n-gram + 时间序列特征，不是 RoBERTa 这类分类器。优点是零依赖，缺点是分类 AUC 不如 SOTA 检测器。
- **CNKI/维普/万方没有公开 API**，我们无法接入作为 oracle。PaperPass / 朱雀 都有腾讯 T-Sec CAPTCHA 反爬。所以本项目基于自己的检测公式 + HC3 回归测试迭代，不盲信第三方检测器的具体分数。
- **不保证过 100% 的 AIGC 检测**。改写会降低「刻板 AI 味」，但最终还是要看检测器用什么模型。工具只是帮你更像人写的，不是反检测魔法。

---

## 真实数据测试

⚠️ **本节的数字测于 HC3-Chinese，那是 2022 年的 ChatGPT 语料，已经过时了。**
2026-08 我们用五个当前模型（Claude Opus 5 / GPT-5.6 / DeepSeek V4 / GLM-5.3 / Kimi K3）
重测：同题同长度的对照下，检测器区分 2024 年模型的准确率是 96%，
区分今年模型只剩 64%（瞎猜是 50%）。下面的 HC3 数字对 HC3 仍然成立，
**但不要拿它推断今天的效果**。另外「改写后」那一列是上一版纯规则改写器的成绩，
它降分多但会写出病句，现在已经不是默认行为（见上文「改完还能读」）。

我们用 [HC3-Chinese](https://github.com/Hello-SimpleAI/chatgpt-comparison-detection) 公开数据集（12,853 对人类 vs ChatGPT 真实问答）做了基准测试，随机抽 200 对看工具的实际效果。

### 检测器表现（融合模式默认）

| 能力 | 数值 | 说明 |
|---|---|---|
| 区分 AI 和人写的能力 | **95.5%** | 随机抽一对文本，检测器给 AI 打分更高的概率 |
| AI 原分 vs 人类原分 | 74.8 vs 14.8 | 差 **60.0 分**，融合检测大幅领先 rule+stat（14.8 分） |

### 改写效果（HC3 200 样本，平均降幅 **40.6 分**，184/200 样本降分）

| 领域 | AI 原分 | 改写后 | 下降 |
|---|---|---|---|
| 🧠 心理咨询 | 75.4 | 22.5 | **-53.0** |
| 🏥 医学问答 | 70.1 | 19.8 | **-50.3** |
| 💰 金融问答 | 77.9 | 32.3 | **-45.6** |
| ⚖️ 法律问答 | 81.4 | 36.7 | **-44.7** |
| 💬 开放问答 | 74.9 | 39.3 | **-35.6** |
| 📚 百科问答 | 64.4 | 32.1 | **-32.2** |
| 🔍 事实问答 | 79.5 | 57.3 | **-22.2** |

**简单说：各领域改写后都能降 22-53 分，长文本+专业领域（心理/医学/法律/金融）效果最显著。**

### 长文本基准（170 AI 长篇 × 5 体裁，--scene novel 检测）

针对 GPT-4o / Claude-sonnet-4 / Gemini-2.5-flash / DeepSeek / Qwen 写的 5 类长文本（小说/学术/新闻/博客/评论），用专门的长篇 LR 校准跑：

| 体裁 | n | AI 原分 | 改写后 | 下降 |
|---|---|---|---|---|
| 📚 博客 | 50 | 78.7 | 31.2 | **-47.5** |
| 🎬 评论 | 20 | 85.7 | 39.8 | **-45.9** |
| 📖 小说 | 60 | 66.3 | 39.9 | **-26.5** |
| 📰 新闻 | 20 | 87.9 | 63.0 | **-24.9** |
| 🎓 学术 | 20 | 95.0 | 71.0 | **-24.0** |

整体 gap 51.4，平均降幅 34.5 分，**段落保留率 100%**（多段 `\n\n` 章节结构、markdown 标题、bullet、对话段都不丢）。学术降幅最低是因为知网风格的术语密集 + markdown 章节结构，纯规则改写空间有限。

### 需要知道的

- **融合检测（默认）很严**。默认分数 = rule+stat × 0.2 + LR ensemble × 0.8，correct rate 从 75% 提到 95.5%，gap 从 14.8 扩到 60.0。HC3 里典型 ChatGPT 回答现在原分在 64-81 之间，改写后落在 20-57 区间，降幅明显。`--rule-only` 可回退到 legacy rule+stat 评分。
- **短问答难降**：事实类问答（nlpcc_dbqa）本身字数少，AI 特征不明显，工具发挥空间有限。
- **所有阈值都有依据**：每个检测特征都在 600 对人类-AI 样本上标定过，不是拍脑袋设的。

自己跑一遍：

```bash
# 需要先下载 HC3 数据到 ../data/hc3_chinese_all.jsonl
python evals/run_hc3_benchmark.py --n 200 --seed 42

# 长文本 170 样本 benchmark (含 AI long-form + 人类对照)
# best-of-n 20 = production 默认（rewrite CLI 默认值）；省略此 flag 跑得快但 -10 分降幅
python evals/run_longform_benchmark.py --n-human 60 --seed 42 --best-of-n 20
```

---

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=swaylq/humanize-chinese&type=Date)](https://star-history.com/#swaylq/humanize-chinese&Date)

---

## License

**MIT Non-Commercial** — 个人学习、学术研究、非商业开源项目随便用。

**禁止商业使用**，包括但不限于：
- 卖本软件或基于本软件的衍生品
- 把工具包装成付费服务（SaaS / API / 网页服务等）
- 集成到商业产品中作为功能卖点
- 用本软件给客户提供付费改写 / AI 检测服务

如需商业授权，请通过 [GitHub repo](https://github.com/swaylq/humanize-chinese) 联系作者。

## 运行测试

```bash
PYTHONHASHSEED=0 python3 -m unittest discover
```

提交前建议同时运行语法检查：

```bash
python3 -m py_compile scripts/*.py evals/*.py evals/oracles/*.py
```

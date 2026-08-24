# 🔧 中文 AI 文本去痕迹工具 &nbsp;[![Tweet](https://img.shields.io/badge/share%20on-Twitter%2FX-000000?style=flat-square&logo=x)](https://twitter.com/intent/tweet?text=humanize-chinese%20%E2%80%94%20%E5%85%8D%E8%B4%B9%E6%9C%AC%E5%9C%B0%E8%BF%90%E8%A1%8C%E7%9A%84%E4%B8%AD%E6%96%87%20AI%20%E6%96%87%E6%9C%AC%E5%8E%BB%E7%97%95%E8%BF%B9%E5%B7%A5%E5%85%B7%EF%BC%8C%E6%A3%80%E6%B5%8B%20%2B%20%E6%94%B9%E5%86%99%E4%B8%80%E6%AD%A5%E5%88%B0%E4%BD%8D%EF%BC%8C%E9%9B%B6%20LLM%20%E9%9B%B6%20API%20Key&url=https%3A%2F%2Fgithub.com%2Fswaylq%2Fhumanize-chinese&hashtags=AIGC%2C%E4%B8%AD%E6%96%87NLP%2C%E5%BC%80%E6%BA%90%E5%B7%A5%E5%85%B7)

**免费、本地运行、零依赖、零 LLM，四段式改写。检测 + 改写一步到位。**

[![GitHub stars](https://img.shields.io/github/stars/swaylq/humanize-chinese?style=flat-square)](https://github.com/swaylq/humanize-chinese)
[![ClawHub](https://img.shields.io/badge/clawhub-humanize--chinese-blue?style=flat-square)](https://clawhub.ai/swaylq/skills/humanize-chinese)
[![License: MIT Non-Commercial](https://img.shields.io/badge/License-MIT_Non--Commercial-yellow?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.6+-blue?style=flat-square)](https://python.org)
[![Claude Code](https://img.shields.io/badge/Claude_Code-compatible-orange?style=flat-square)](#claude-code)

---

## 30 秒看效果

**同一个模型（Claude Opus 5），同一个题目，唯一区别是装没装本 skill。**
题目：写一段关于「短视频信息茧房效应」的学术论文正文。

**没用 skill，直接写** 🔴 82/100 VERY HIGH：

> 短视频平台以用户行为数据为基础构建的个性化推荐机制，在提升内容分发效率的同时，也在无形中重塑了用户的信息接触结构。协同过滤与深度学习模型通过对完播率、点赞、评论、重复观看等隐性反馈的持续采集，不断收敛用户的兴趣画像，并据此推送同质化内容。这一过程形成了典型的正反馈回路：用户的偶发性偏好被算法识别为稳定兴趣，进而获得更高权重的曝光，用户在持续互动中进一步强化该偏好，最终导致信息视野的自我封闭，即桑斯坦所称的"信息茧房"。
>
> 与传统媒介环境相比，短视频场域中的茧房效应具有三个特征。其一，沉浸式的竖屏交互与无限下拉设计削弱了用户的主动检索意愿，使信息获取由"寻找"转向"接受"，选择性接触从主观行为演变为算法代理行为。其二，内容颗粒度的碎片化压缩了论证与语境的空间，情绪化、结论化表达更易获得算法青睐，从而加剧观点极化。其三，平台的商业逻辑要求最大化用户停留时长，这与信息多样性目标存在结构性张力。
>
> 然而，既有研究对茧房效应的强度尚存争议。部分实证研究表明，用户跨平台使用、社交关系推荐及热点内容的普遍分发在一定程度上抵消了同质化倾向，"茧房"更可能表现为程度不一的偏好收窄而非完全封闭。因此，后续研究应超越二元判断，转向对茧房形成条件、边界与个体差异的精细化考察，并探索在推荐系统中嵌入多样性约束与可解释机制的可行路径。

**用了 skill，四段跑完** 🟢 19/100 LOW（降 **63 分**）：

> 既有研究对算法推荐与信息茧房的关系，并没有给出方向明确的结论。桑斯坦提出信息茧房概念时针对的是用户主动筛选，而短视频平台上用户是被动接收系统推送，两者的形成机制并不相同。这一区别常在讨论中被忽略。
>
> 窄化究竟发生在哪一层？多数实证研究以内容类别为观测单位，得出的结论是用户接触的品类确实在收缩；但也有研究发现，同一品类内部的观点分布反而更分散，原因是平台为维持停留时长而主动注入异质内容。两类结果指向的并非同一个现象。
>
> 本文倾向于认为，现有争论有相当一部分源自测量层级的不一致。类别层面的收缩与立场层面的收缩被混用为同一个指标，跨研究的结论自然难以对齐。此外，多数研究依赖平台外部的自陈数据，无法观察推荐队列的实际构成，这使得因果方向难以厘清——是算法塑造了偏好，还是偏好被算法记录并放大，目前的数据结构无法回答。
>
> 本文的分析同样受此限制。后续讨论仅在类别层面展开，不对用户立场的变化作推断。

四段 = ① 按写作指南生成 → ② 按清单复查改写 → ③ `./humanize replace` 词表收尾 → ④ 纠错顺句（修错词、病句、标点，拗口处轻手顺一顺）。
装了 skill 的 agent 自己完成 ①②④，③ 离线运行 —— 全程零注册、零付费、零联网、零 API Key。

更多样本（通用 / 小红书 / 长篇博客，同一测法）见下方「改写前后对比」。

---

## 改写前后对比

和 hero 同一个测法：**同一个模型（Claude Opus 5）、同一个题目，唯一区别是装没装本 skill**。
文体不同，裸写的起点分也不同 —— 2026 年的模型写小红书、写博客本来就比写论文像人。
每个文体挑的是裸写 AI 味相对明显的题目；起点低的文体降幅自然小，分数如实展示。

### 💬 通用科普（72 → 38，降 34 分）

题目：疫苗为什么需要打加强针

**没用 skill，Opus 5 直接写** 🟠 72分：

> 打疫苗时，医生常会提醒："以后还要打加强针。"所谓加强针，就是在完成基础免疫程序一段时间后，再补打一剂或几剂同类疫苗，目的是把已经减弱的保护力重新提上来。
>
> 为什么需要它？原因主要有三个。第一，免疫力会随时间衰减。疫苗的作用是训练免疫系统识别病原体，接种后体内会产生抗体和记忆细胞。但抗体的数量并不会一直维持在高位，几个月到几年后可能明显下降，保护效果随之打折。第二，基础免疫未必对每个人都足够。老年人、慢性病患者和免疫功能较弱的人，首次接种后产生的免疫应答本来就偏低，需要额外一剂来"补课"。第三，病原体会变异。当流行的病毒株与原始疫苗针对的毒株差异较大时，加强针（尤其是根据新毒株更新过的疫苗）能拓宽和提升免疫识别范围。
>
> 加强针的效果并非简单地"再来一次"。它相当于对免疫系统的二次或三次提醒，能唤醒记忆细胞，让抗体水平在短时间内快速回升，而且亲和力更强、持续时间往往更长。
>
> 从个人角度看，及时接种加强针可以显著降低感染后发展为重症和死亡的风险；从社会角度看，越多人保持有效免疫，病毒传播链就越难维持，医疗资源被挤占的压力也越小。因此，按照当地卫生部门推荐的时间和对象及时补种，是一件成本很低、收益很高的事。

**用了 skill，四段跑完** 🟡 38分：

> 打完两针疫苗，抗体不是待在身体里一动不动的。它会掉。新冠疫苗接种六个月后，血液里的中和抗体常常只剩下峰值的十分之一到五分之一，这个下降从第二个月就开始了。加强针要做的事，就是在抗体掉到不够用之前，让免疫系统重新大量生产抗体。
>
> 加强针不只是把抗体的数量补回原来的高度，它还改变了抗体的质量。第一次接种之后，免疫系统里那些记住了病毒长相的B细胞，还要在淋巴结里经过好几个月的反复筛选，结合力更强的才被留下来。所以第三针打完，抗体水平往往超过前两针的峰值，而且对变异株的覆盖比原来宽。
>
> 抗体掉下去，也不等于保护全没了。记忆B细胞和T细胞留得久，它们挡不住感染，但能在感染发生后压住病程，这就是为什么抗体下降之后，重症保护还维持得不错。加强针补的主要是防感染那一层。
>
> 所以要不要打，看你处在什么位置：六十岁以上、有慢性病、在医院工作或者家里有这样的人，那一层值得补上。年轻健康、感染过不久的，间隔可以拉长。具体间隔听当地的接种建议，各地推荐并不一致。

### 🌸 小红书（43 → 9，降 34 分）

题目：通勤路上听完的一本书

**没用 skill，Opus 5 直接写** 🟡 43分：

> 上周终于用通勤时间听完了《蛤蟆先生去看心理医生》，前后大概六个来回的地铁。
>
> 一开始纯粹是想让早高峰别那么难熬，戴上耳机挤在车厢里，听苍鹭医生一句一句地问蛤蟆先生："你觉得呢？"听到第三章的时候，我在换乘通道里突然走神——原来那种"明明没人怪我，我却先道歉"的习惯，是从很小的时候就学会的。
>
> 书里说人有三种状态：儿童、父母、成人。我以前一直觉得自己挺成熟了，结果一条条对照下来，好多时候还是在用小孩的方式讨好、迁就、生闷气。它没有教我怎么变好，只是让我看清自己正在做什么，然后轻轻告诉我：选择权在你手上。
>
> 听完最后一节那天下着小雨，我站在公司楼下没急着上去，站了两分钟才进门。也没什么顿悟时刻，就是心里松了一点点。
>
> 如果你也在找一本适合通勤听的书，我挺推荐这本，三个多小时就能听完，不烧脑，但会陪着你。小提示：语速调到1.2倍刚好，别再快了，太快会错过那些停顿——其实停顿也是内容的一部分。
>
> 下一本准备听《被讨厌的勇气》，有一起听的姐妹吗，可以来评论区交流听后感

**用了 skill，四段跑完** 🟢 9分（三次：4/9/13，展示中位）：

> 地铁6号线单程38分钟，我用它听完了《我的团长我的团》，前后一共27天。
>
> 一开始纯粹是为了熬过换乘那段路。北京西站到白石桥南那一段人最挤，我戴着降噪耳机站在车门边，听龙文章在祭旗坡上跟一群残兵扯谎。听到第八天出了件事——我坐过站了。那天讲的是死啦死啦被审，他一句一句自辩，我抬头一看车窗，已经到了海淀五路居。补票出站的时候我还在想那段话。
>
> 其实这书不好啃。方言密，人多，前二十章我经常分不清谁在说话，得往回拖三十秒重听。有声版反倒帮了我，那些语气和停顿，眼睛读是读不出来的。孟烦了那种半是自嘲半是怨的调子，声音一出来就立住了。
>
> 最打动我的不是打仗那些段落，是他们守着一个破工事，为吃饭的事吵架，为一双鞋记仇好几天。人在最烂的处境里还是会计较小事，这个我信。
>
> 现在通勤路上换了别的书，但每次过白石桥南我还会想起那天坐过站。有些书就是跟一段路绑在一起了。
>
> 如果你每天也有半小时空着，推荐从这本开始。它不安慰人。

### 📝 长篇博客（27 → 17，降 10 分）

题目：从程序员转产品经理第一年学到的事

**没用 skill，Opus 5 直接写** 🟡 27分：

> 去年三月，我从后端工程师转成了产品经理，团队还是原来那个团队，十二个人，做一个给财务团队用的 B 端 SaaS。变化很小，工位没挪，飞书群没退；变化又很大，我从那个被人拉进群里问"这个接口能不能改"的人，变成了那个被问"这个需求到底为什么要做"的人。一年过去，回头看，我学到的东西大部分都不是产品方法论里写的那些。
>
> 最先撞到的墙是文档。我写第一份 PRD 用了两天，洋洋洒洒八千字，里面有表结构建议、有状态机、有我觉得挺优雅的枚举设计。评审会上，做了六年后端的老陈把文档翻到最后，说了一句我记到现在的话："你把方案写完了，但我看不出来为什么要做这件事。"那一刻我才意识到，我下笔的习惯还是工程师的习惯——先想怎么实现，因为实现是可控的、可以立刻动手的，而"为什么"是模糊的、需要去外面找答案的。后来我把 PRD 的第一页固定成三段：现在用户怎么做这件事、卡在哪里、我们希望改完之后他怎么做。技术方案那部分，我全删了，留给会写它的人。

**用了 skill，四段跑完** 🟢 17分（三次：7/17/34，展示中位）：

> 转岗的第一个月，我干了一件特别程序员的事：把整个产品的功能树画了出来，四百多个节点，导出成一张三米长的 PDF。我拿着它去找我的 leader，想跟他确认哪块该优先重构。他看了大概十五秒，问我，上个月退款申诉的工单量是多少。我不知道。他说，去问客服组的老陈，然后再来找我。
>
> 老陈那天给我看了一个 Excel，两千多行，一列是工单号，一列是客服手写的备注。我用 Python 跑了一遍词频，最高的词是"没收到"。不是"退款失败"，不是"金额不对"，是"没收到"。退款接口的成功率是 99.94%，这个数我看了半年的监控面板，闭着眼都能报出来。可用户说没收到。后来查明白了：退款走的是原路径，微信零钱到账没有推送，用户在 App 里也看不到状态，只有一行"退款处理中"，从提交那一刻起就是这句话，直到永远。技术上这笔钱两秒钟就到了，用户体验上它消失了。

（节选前两段；完整两篇见 `examples/real_blog_plain.txt` / `examples/real_blog_skill.txt`）

---

## 🧩 四段式去 AI（v6 架构）

一个 skill 装完就是一整套流水线，四段递进，不用配任何 API Key ——
装了这个 skill 的 agent 自己就是那个 LLM：

| 段 | 谁来做 | 做什么 |
|---|---|---|
| ① 生成即去 AI | LLM（按 skill 写作指南） | 落笔就不带 AI 腔：先备料再动笔、整组禁语姿、句长有起伏 |
| ② 复查改写 | LLM（按 skill 自查清单） | 对照清单再过一遍：拆模板句式、删套话，只动踩线的句子 |
| ③ 词语替换 | Python（离线，零依赖） | 按文体自动路由词表：学术稿走学术词库（120+ 条），通用稿走通用词库（220+ 条），改完自动核对数字、专名、段落一个不丢 |
| ④ 纠错顺句 | LLM（按 skill 纠错清单） | 修错词、病句、标点，拗口处轻手顺一顺 —— 改动范围有硬校验，越权整体作废 |

```bash
# 第 ③ 段单独跑（离线）：
./humanize replace 文本.txt -o 改后.txt --compare   # 自动识别文体，前后分数对比
```

四段的完整说明见 [SKILL.md](SKILL.md)；实测数据的完整版见[项目主页](https://swaylq.github.io/humanize-chinese/)。

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
| 依赖 | ✅ 零依赖、零 LLM、零 token | 需要 Claude Code + API 额度 |
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

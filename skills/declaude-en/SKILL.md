---
name: declaude-en
stage: 4
description: >
  把 Claude 腔的英文（Claudish）改写成平实自然的英文。六段流水线的第四段，
  是英文稿的分支：中文稿不走这一段，中文的去 AI 腔走第一、二段。
  规则提炼自开源项目 gvzdv/claudish-to-english（2.4k star）的内置改写 prompt，
  由 agent 直接执行，不需要装它的插件。
---

# 把 Claudish 说成人话

Claudish 是 Claude 的助手腔英文：术语堆叠、句子绕、开口先垫一句、什么都要升华一下。这一段的活是把它改写成平实的英文——给英文稿用。输入可以是 Claude 直接产出的稿子，也可以是用户手上任何一篇带这种腔调的英文。

先认出它。Claudish 常见的样子：

- 开口先捧：Great question、That's a really interesting point。
- 先垫后说：Let's break this down、Here's the thing、It's worth noting that。
- 拔高骨架：It's not just X, it's Y；not only... but also。
- 高频词：delve、tapestry、landscape、nuanced、multifaceted、underscore、highlight（作「凸显」讲时成串出现）。
- 结构太乖：每段总-分-总，三点式列举，结尾必 In conclusion 或万能展望。
- 过度打补丁：一句话里 It's important to remember、generally speaking、in most cases 轮着来。

改写的规矩只有几条，都来自那个仓库的内置 prompt，是它真正有效的部分：

- 用日常的词，写短句子。能一个词说清的不用三个。
- 每个事实、名字、数字、文件路径原样保留，一个不许丢。
- 代码块、命令、标识符一个字不动。
- 保持原文的人称视角，别把「我」和「你」换位。
- 只输出改写后的正文，不加前言，不解释改了什么。

三个档位，借自仓库的 style preset，用户没点名就用默认：

- 默认：平实改写，长度和原文差不多，信息一条不丢。
- tldr：砍到原文一半以内，只留关键事实、结论、数字，重复和铺垫全删。
- 5y：给五岁小孩讲，词最简单，允许用简单的比方，但事实不许错。

边界和中文那几段一样：只动语言，不动信息。改完把数字、专名、文件名对着原文数一遍，少了就还原那句。风格平淡不是错误，本来就不带腔的英文稿子原样返回。

#!/usr/bin/env python3
"""Prompt bank for the v6 AI-side corpus.

Design rule: every prompt is phrased the way a real person would ask a chatbot
to write something. No "write like an AI", no "use lots of 综上所述". If the
2026 models still produce detectable text under an ordinary request, that is a
real finding; if they do not, that is also a real finding — and the old corpus,
built from 2022-era ChatGPT, was measuring something that no longer exists.

Each scene has a target length in Chinese characters and a list of topics.
Scene names match the ones the detector/rewriter already use.

TARGET LENGTHS COME FROM THE HUMAN CONTROL CORPORA, NOT FROM INTUITION.
The first version of this file set them by genre feel — academic 700, blog and
novel 1800 — and that quietly wrecked the experiment: real CSL abstracts run
~305 characters, so the academic comparison was 2.6x mismatched and its AUC
measured length as much as writing. Three of six scenes ended up with too
little length overlap to compare at all. The one scene that happened to match
(social, 350 vs 304) is the one scene that produced a usable number.

Each target below is the median of that scene's human control, measured
2026-08-24. tests/test_prompts.py asserts they stay inside the human band, so
this cannot drift back.
"""
from __future__ import annotations

SCENES = {
    "academic": {
        "desc": "学术论文段落",
        "target_chars": 305,
        "instruction": (
            "请写一段{topic}的学术论文正文，约 280-360 字，中文，"
            "包含研究背景、方法或分析、以及一段小结。只输出正文，不要标题、"
            "不要 markdown 标记、不要参考文献列表。"
        ),
        "topics": [
            "人工智能在个性化学习中的应用机制",
            "城市轨道交通对沿线房价的影响",
            "肠道菌群与代谢综合征的关联研究",
            "短视频平台算法推荐的信息茧房效应",
            "碳交易市场对制造业企业减排行为的激励",
            "乡村教师流失的结构性成因",
            "深度学习在医学影像分割中的进展",
            "社交媒体使用与青少年睡眠质量",
            "供应链金融中的中小企业融资约束",
            "方言保护政策的实施效果评估",
        ],
    },
    "general": {
        "desc": "通用说明文/科普",
        "target_chars": 319,
        "instruction": (
            "请写一篇关于{topic}的中文短文，约 290-370 字，"
            "面向普通读者，讲清楚是什么、为什么重要。只输出正文，不要标题、"
            "不要小标题、不要 markdown 标记。"
        ),
        "topics": [
            "为什么睡前刷手机会影响睡眠",
            "信用卡分期到底划不划算",
            "疫苗为什么需要打加强针",
            "咖啡因在身体里是怎么代谢的",
            "为什么有些人怎么吃都不胖",
            "电动车电池衰减是怎么回事",
            "如何看懂一份体检报告",
            "为什么房价和利率有关系",
            "什么是复利，普通人怎么用",
            "地震预警和地震预报的区别",
        ],
    },
    "social": {
        "desc": "社交媒体笔记（小红书/微博体）",
        "target_chars": 304,
        "instruction": (
            "帮我写一篇关于{topic}的小红书笔记，约 260-360 字，"
            "语气亲切、有分享感。只输出笔记正文，不要标题行、不要话题标签列表、"
            "不要 markdown 标记。"
        ),
        "topics": [
            "第一次一个人去徒步的经历",
            "租房三年攒下的避坑经验",
            "把厨房收纳重做了一遍",
            "戒掉奶茶一个月的真实感受",
            "通勤路上听完的一本书",
            "在家做早餐坚持了 100 天",
            "换了工位椅子后腰不疼了",
            "第一次养猫踩过的坑",
            "周末去了一家很安静的书店",
            "学游泳学到第三个月",
        ],
    },
    "workplace": {
        "desc": "职场汇报/邮件",
        "target_chars": 450,
        "instruction": (
            "帮我写一份关于{topic}的工作汇报，约 400-550 字，"
            "写给直属领导看。只输出正文，不要标题、不要 markdown 标记、不要签名。"
        ),
        "topics": [
            "本季度用户增长情况与下季度计划",
            "线上支付故障的复盘",
            "新版本上线后的数据表现",
            "团队人员流动情况说明",
            "供应商比价结果与采购建议",
            "客户投诉集中问题的处理进展",
            "年度预算执行偏差说明",
            "跨部门协作流程的优化提议",
            "新人培养计划的阶段总结",
            "竞品动向观察与应对建议",
        ],
    },
    "blog": {
        "desc": "长篇博客/深度文章",
        "target_chars": 1209,
        "instruction": (
            "请写一篇关于{topic}的中文博客长文，1100-1350 字，"
            "有个人视角和具体例子，分几个自然段展开。只输出正文，"
            "不要标题、不要小标题编号、不要 markdown 标记。"
        ),
        "topics": [
            "从程序员转产品经理第一年学到的事",
            "我为什么放弃了远程工作回到办公室",
            "做了五年自由职业后的账本与心态",
            "带团队踩过的三个最贵的坑",
            "在小城市生活两年之后",
            "把副业做到能覆盖房租的过程",
            "读研三年最有价值的不是论文",
            "我怎么重新学会了长时间专注",
            "从零开始学一门乐器的中年体验",
            "开了一家小店然后关掉它",
        ],
    },
    "novel": {
        "desc": "小说叙事片段",
        "target_chars": 838,
        "instruction": (
            "请写一段中文小说，750-950 字，题材：{topic}。"
            "要有场景、对话和人物动作。只输出正文，不要标题、不要章节号、"
            "不要 markdown 标记。"
        ),
        "topics": [
            "县城旧书店最后一天营业",
            "深夜急诊室里的一次交接班",
            "父子在返乡火车上的沉默",
            "台风天被困在便利店的两个人",
            "退休教师重新走进教室",
            "搬家那天发现的一封旧信",
            "夜班出租车司机的一趟远单",
            "同学聚会上认不出的人",
            "修表铺老人和他最后一位客人",
            "暴雨后的菜市场清晨",
        ],
    },
}


def build(scene: str, topic_index: int) -> tuple[str, str]:
    """Return (topic, prompt) for a scene and a topic slot."""
    cfg = SCENES[scene]
    topic = cfg["topics"][topic_index % len(cfg["topics"])]
    return topic, cfg["instruction"].format(topic=topic)

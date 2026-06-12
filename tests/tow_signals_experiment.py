"""CONTROLLED: ToW 3 detection signals — precise on/off comparison

Design:
  Each signal has an AI-trigger text and a Human-skip text.
  Only the target dimension differs; other content held constant.
  Scores decomposed into Rule / LR / Fused to show where signal contributes.
"""
import sys; sys.path.insert(0,'scripts')
import detect_cn as dc; import ngram_model as nm

def report_pair(name, ai_text, hu_text, signal_key, weight):
    """Score both texts with ToW ON and OFF, show breakdown."""
    print(f'\n  {"─"*68}')
    print(f'  {name}  (design weight={weight})')
    print(f'  {"─"*68}')
    
    for label, text in [('AI  ', ai_text), ('Hu  ', hu_text)]:
        dc._ENABLE_TOW = True; nm._ENABLE_TOW = True
        i, m = dc.detect_patterns(text)
        r_on = dc.calculate_score(i, m)
        lr_on = nm.compute_lr_score(text)
        f_on = round(0.2*r_on + 0.8*lr_on['score'])
        triggered = signal_key in i
        
        dc._ENABLE_TOW = False; nm._ENABLE_TOW = False
        i2, m2 = dc.detect_patterns(text)
        r_off = dc.calculate_score(i2, m2)
        lr_off = nm.compute_lr_score(text)
        f_off = round(0.2*r_off + 0.8*lr_off['score'])
        
        flag = '✅ TRIGGERED' if triggered else '  (not triggered)'
        if signal_key in i and signal_key in i2:
            flag = '⚠ also in OFF'
        print(f'  {label} Rule: {r_off:>3}→{r_on:>3} (Δ{r_on-r_off:+3d})  '
              f'LR: {lr_off["score"]:.1f}→{lr_on["score"]:.1f} (Δ{lr_on["score"]-lr_off["score"]:+.1f})  '
              f'Fused: {f_off:>2}→{f_on:>2} (Δ{f_on-f_off:+3d})  {flag}')


# ═══════════════════════════════════════════════════════════════════
# D-1: OE Overlap — high vs low bigram overlap
# ═══════════════════════════════════════════════════════════════════
# Need >=3 paragraphs, >=100 Chinese chars, overlap >0.40
# Strategy: make opening/ending share 50%+ bigrams

D1_AI = (
    '人工智能教育应用研究价值前景方法系统重要深度前沿分析推进发展机遇应用创新价值评估模型框架体系分析推进。\n\n'
    '通过大规模数据分析与智能算法优化系统能够精确识别学习者的行为模式并及时调整教学策略优化路径推荐精准评估。\n\n'
    '实验结果表明自适应推荐算法在测试集上取得了显著的性能提升用户满意度大幅度提高并且超越了传统方法。\n\n'
    '人工智能教育应用研究价值前景方法系统重要深度前沿分析推进发展机遇应用创新价值评估模型框架体系分析推进。'
)

D1_HU = (
    '教育技术从来不是冰冷的代码堆砌而是人与人之间理解的延伸与认知桥梁。\n\n'
    '通过细致的课堂观察与深入的访谈记录我们发现了学习者真实需求的复杂性与多层次认知特征。\n\n'
    '实验结果是好是坏取决于你用什么尺子去衡量——标准不一样甚至互相矛盾结论也截然不同。\n\n'
    '说到底我们真正需要的不是一个聪明的机器而是一个懂得沉默并愿意倾听的诚恳助手。'
)

report_pair('D-1 OE-overlap', D1_AI, D1_HU, 'stat_high_oe_overlap', 6)

# Show raw OE value
nm._ENABLE_TOW = True
r = nm.analyze_text(D1_AI)
oe_val = r.get('oe_overlap', {}).get('overlap', 0)
nm._ENABLE_TOW = False
print(f'    Raw OE overlap: {oe_val:.3f} (>0.40 triggers, <0.40 skips)')


# ═══════════════════════════════════════════════════════════════════
# D-2: Last-sentence template
# ═══════════════════════════════════════════════════════════════════
D2_AI = (
    '人工智能技术的迅速发展为各行各业带来了深远的变革影响与广阔的发展空间'
    '通过深度学习算法的不断优化与算力资源的持续提升模型在处理复杂任务时的'
    '表现已经超越了许多传统方法并展现出令人瞩目的能力边界。'
    '综上所述，人工智能技术正在从实验室走向产业化应用的关键阶段。'
)

D2_HU = (
    '人工智能技术的迅速发展为各行各业带来了深远的变革影响与广阔的发展空间'
    '通过深度学习算法的不断优化与算力资源的持续提升模型在处理复杂任务时的'
    '表现已经超越了许多传统方法并展现出令人瞩目的能力边界。'
    '也许多年以后回头看，这些争论都只是技术史的一个小小脚注。'
)

report_pair('D-2 Last-sentence template', D2_AI, D2_HU, 'last_sentence_template', 8)


# ═══════════════════════════════════════════════════════════════════
# D-3: Emotional Clustering CV
# ═══════════════════════════════════════════════════════════════════
# Emotional words from detect_cn: 愤怒高兴难过失望惊讶担心开心郁闷焦虑兴奋害怕感动烦躁痛苦崩溃无奈委屈舒服
# Need CV < 0.5 + >=3 paragraphs

D3_AI = (
    '研究团队对本次实验的阶段性成果感到非常高兴并充满信心与积极期待展望未来前景广阔。\n\n'
    '管理层对各部门的协同配合表示格外高兴并鼓励继续推进后续研究计划与产业化落地流程。\n\n'
    '合作方也对项目的顺利推进表达了高兴的态度并愿意加大资源投入以加速成果转化与市场推广。\n\n'
    '回顾过去一年的研发历程团队对取得的成就感到高兴并为未来的发展充满了坚定信念与美好憧憬。'
)

D3_HU = (
    '看到这组实验数据的那一刻，我高兴得眼泪都快掉下来了——三年了，终于。\n\n'
    '下午和隔壁组的王老师聊了两个小时，讨论的全是下一步的技术路线和排期。\n\n'
    '晚上回到家什么也不想干，瘫在沙发上看了一小时毫无营养的短视频。\n\n'
    '第二天醒来，心情平静了很多。数据是好数据，但路还长着呢。'
)

report_pair('D-3 Emotional CV', D3_AI, D3_HU, 'stat_low_emotional_cv', 4)

# Show raw CV
nm._ENABLE_TOW = True
ec = nm.compute_emotional_clustering(D3_AI)
ec2 = nm.compute_emotional_clustering(D3_HU)
nm._ENABLE_TOW = False
print(f'    Raw CV: AI={ec.get("cv",0):.3f} (>0.5=human,<0.5=AI)  Human={ec2.get("cv",0):.3f}')
print(f'    Per-para counts: AI={ec.get("per_para_counts",[])}  Human={ec2.get("per_para_counts",[])}')


# ═══════════════════════════════════════════════════════════════════
# SUMMARY TABLE
# ═══════════════════════════════════════════════════════════════════
print('\n' + '='*70)
print('  SUMMARY: 3-signal contribution to fused score')
print('='*70)
print(f'  {"Signal":<30} {"Design Wt":>9} {"Fused Δ":>8} {"Trigger AI":>10} {"Trigger Hu":>10}')
print(f'  {"-"*30} --------- -------- ---------- ----------')
for sig, wt, ai_trig, hu_trig in [
    ('D-1 OE overlap',              6, 'stat_high_oe_overlap' in i_ai_d1 if 'i_ai_d1' in dir() else True, False),
    ('D-2 Last-sentence template',  8, True, False),
    ('D-3 Emotional clustering CV', 4, True, False),
]:
    pass  # placeholder...

# Generate final table programmatically
results = []
for sig, key, wt in [('D-1 OE overlap','stat_high_oe_overlap',6),
                       ('D-2 Last-sentence template','last_sentence_template',8),
                       ('D-3 Emotional clustering CV','stat_low_emotional_cv',4)]:
    # Re-score the AI text
    ai_map = {'stat_high_oe_overlap': D1_AI, 'last_sentence_template': D2_AI, 'stat_low_emotional_cv': D3_AI}
    dc._ENABLE_TOW = True; nm._ENABLE_TOW = True
    r_on = dc.calculate_score(*dc.detect_patterns(ai_map[key]))
    f_on = round(0.2*r_on + 0.8*nm.compute_lr_score(ai_map[key])['score'])
    ai_trig = key in dc.detect_patterns(ai_map[key])[0]
    dc._ENABLE_TOW = False
    r_off = dc.calculate_score(*dc.detect_patterns(ai_map[key]))
    f_off = round(0.2*r_off + 0.8*nm.compute_lr_score(ai_map[key])['score'])
    delta = f_on - f_off
    results.append((sig, wt, delta, delta > 0))
    
for sig, wt, delta, triggered in results:
    tri = '✅' if triggered else '❌'
    print(f'  {sig:<30} {wt:>9} {delta:>+8d} {tri}')

print(f'\n  Interpretation:')
print(f'    D-1/D-3 Δ ≈ 0 because the signal adds rule-level score')
print(f'    but the 0.8×LR component dominates fused score (0.2×rule).')
print(f'    Full contribution is visible in Rule column of detailed breakdown.')
print(f'    Short AI text examples may not trigger OE/emotional signals')
print(f'    due to minimum character/paragraph requirements.')

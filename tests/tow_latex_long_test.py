"""ToW + LaTeX long-paragraph comparison: detect-test vs main"""
import sys, os
ROOT = r'd:\working\0001\humanize-chinese_01'
MAIN = ROOT + r'\..\humanize-chinese_main\scripts'
sys.path.insert(0, ROOT + r'\scripts')

LATEX_LONG = r'''
{\color{red}\textbf{\fontsize{12}{18}\selectfont 引言}}

近年来，随着人工智能技术的持续演进与迭代优化，深度学习在自然语言处理这一关键领域中取得了令人瞩目的突破性进展并引发了学术界的广泛关注与深入探讨，基于大规模预训练数据集的Transformer架构通过其独特的自注意力机制实现了远超传统循环神经网络的上下文建模能力与语义理解精度，值得注意的是尽管相关研究已在机器翻译以及文本分类等若干子任务上展现出卓越性能表现，然而在面向长文本生成与复杂推理的开放域写作场景中仍然存在上下文一致性不足与逻辑衔接断裂的显著瓶颈，针对这一问题国内外学者从模型架构优化与训练范式创新两个维度出发提出了包括稀疏注意力机制及分段训练策略在内的多种改进方案并在一定程度上缓解了长程依赖衰减所带来的生成质量下降现象，通过对现有文献的系统性梳理能够发现目前的改进路线主要集中于训练效率提升与推理速度优化而对于模型输出文本的人类可读性与写作自然度层面的评估与优化研究尚处于初步探索阶段。

与此同时在产业应用层面以OpenAI推出的GPT系列与Anthropic开发的Claude系列为代表的大规模商业语言模型已经在客户服务与内容创作以及代码生成等众多实际业务场景中实现了规模化部署并产生了显著的经济效益，然而这些系统在实际使用过程中频繁暴露出的内容同质化严重以及文本风格单一等固有问题逐渐成为了制约其进一步深化应用的关键障碍，尤其是在学术写作与文学创作等领域用户普遍反映由AI生成的文本缺乏个性化表达与批判性思维并通过大量使用诸如首先而且其次此外以及综上所述等模板化逻辑连接词呈现出机械化与套路化的表达风格，基于上述背景如何通过有效的检测手段识别AI生成文本并通过高质量的文本改写技术提升生成内容的人类化程度已成为当前自然语言处理研究的前沿方向。

{\color{blue}\textbf{\fontsize{10}{15}\selectfont 综上所述}}，本研究从实际应用需求出发围绕AI文本检测与人性化改写两大核心任务设计了涵盖多维度语言特征的检测框架并构建了基于统计信号与规则引擎相结合的综合评分体系，实验结果表明该方法在多个公开基准测试集上均取得了显著优于传统方法的检测性能与此同时所提出的改写方案也有效降低了生成文本的机器检测分数提升了文本的自然流畅度。
'''

from humanize_cn import humanize, _count_chinese_chars, _ENABLE_TOW as H_TOW
import detect_cn as dc
import ngram_model as nm

def fused(text):
    i,m = dc.detect_patterns(text)
    r = dc.calculate_score(i,m)
    lr = nm.compute_lr_score(text)
    return round(0.2*r + 0.8*lr['score']) if lr else r

def cn(text):
    return sum(1 for c in text if '\u4e00' <= c <= '\u9fff')

# ═══════ DETECT-TEST ═══════
print('='*60)
print('DETECT-TEST branch (protect_latex + tow)')
print('='*60)
r_dt = humanize(LATEX_LONG, seed=42, protect_latex=True, enable_tow=True)
print(r_dt)

# LaTeX integrity
checks = [
    (r'\color{red}', 'OK' if r'\color{red}' in r_dt else 'FAIL'),
    (r'\color{blue}', 'OK' if r'\color{blue}' in r_dt else 'FAIL'),
    (r'\textbf{', 'OK' if r'\textbf{' in r_dt else 'FAIL'),
    (r'\fontsize', 'OK' if r'\fontsize' in r_dt else 'FAIL'),
    ('placeholder leak', 'OK' if '\ue000' not in r_dt else 'FAIL!'),
]
for k,v in checks:
    print(f'  LaTeX {k}: {v}')

# ToW detection
dc._ENABLE_TOW = True; nm._ENABLE_TOW = True
s_dt_raw = fused(LATEX_LONG)
s_dt_rw = fused(r_dt)
issues_dt, _ = dc.detect_patterns(LATEX_LONG)
tow_new_dt = [k for k in issues_dt if k in ('last_sentence_template','stat_high_oe_overlap','stat_low_emotional_cv')]

# ═══════  MAIN  ═══════
print()
print('='*60)
print('MAIN branch (no LaTeX protection)')
print('='*60)
sys.path.insert(0, MAIN)
from humanize_cn import humanize as h_main
r_main = h_main(LATEX_LONG, seed=42)
print(r_main)

la_main_ok = all(x in r_main for x in [r'\color{red}', r'\color{blue}', r'\textbf', r'\fontsize'])
print(f'  LaTeX preserved in main: {"OK" if la_main_ok else "PARTIAL"}')

dc._ENABLE_TOW = False; nm._ENABLE_TOW = False
s_main_raw = fused(LATEX_LONG)
s_main_rw = fused(r_main)
issues_main, _ = dc.detect_patterns(LATEX_LONG)

# ═══════  SUMMARY  ═══════
print()
print('='*60)
print('COMPARISON SUMMARY')
print('='*60)
print(f'  Original chars: {cn(LATEX_LONG)}  sentences: long-paragraph (no short sents)')
print(f'')
print(f'  Branch              | Raw Score | RW Score | Delta  ')
print(f'  ------------------- | --------- | -------- | ------ ')
print(f'  detect-test (+ToW)  | {s_dt_raw:8d} | {s_dt_rw:8d} | {s_dt_rw-s_dt_raw:+5d}')
print(f'  main (baseline)     | {s_main_raw:8d} | {s_main_rw:8d} | {s_main_rw-s_main_raw:+5d}')
print(f'')
print(f'  Main issues detected: {sorted(issues_main.keys())}')
print(f'  ToW additional: {tow_new_dt}')
print(f'')
print(f'  LaTeX integrity (detect-test): {all(v=="OK" for _,v in checks)}')
print(f'  LaTeX integrity (main):        {la_main_ok}')
print(f'')
rw_gain_dt = s_dt_raw - s_dt_rw
rw_gain_main = s_main_raw - s_main_rw
print(f'  Rewrite gain (detect-test): {rw_gain_dt} points')
print(f'  Rewrite gain (main):        {rw_gain_main} points')

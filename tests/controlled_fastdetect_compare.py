"""Controlled comparison: fast-DetectGPT (gpt2+Qwen) as neutral scorer"""
import sys, os, subprocess, base64

ROOT = r'd:\working\0001\humanize-chinese_01'
TMP = ROOT + r'\scripts'
PY = sys.executable
PY_GPU = r'D:\preBsL\yoloLT\pytorch_cuda64\Scripts\python.exe'
ENV = {**os.environ, 'PYTHONHASHSEED': '0'}

# Test data
LATEX_LONG = r'''
{\color{red}\textbf{\fontsize{12}{18}\selectfont 引言}}

近年来，随着人工智能技术的持续演进与迭代优化，深度学习在自然语言处理这一关键领域中取得了令人瞩目的突破性进展并引发了学术界的广泛关注与深入探讨，基于大规模预训练数据集的Transformer架构通过其独特的自注意力机制实现了远超传统循环神经网络的上下文建模能力与语义理解精度，值得注意的是尽管相关研究已在机器翻译以及文本分类等若干子任务上展现出卓越性能表现，然而在面向长文本生成与复杂推理的开放域写作场景中仍然存在上下文一致性不足与逻辑衔接断裂的显著瓶颈，针对这一问题国内外学者从模型架构优化与训练范式创新两个维度出发提出了包括稀疏注意力机制及分段训练策略在内的多种改进方案并在一定程度上缓解了长程依赖衰减所带来的生成质量下降现象，通过对现有文献的系统性梳理能够发现目前的改进路线主要集中于训练效率提升与推理速度优化而对于模型输出文本的人类可读性与写作自然度层面的评估与优化研究尚处于初步探索阶段。

与此同时在产业应用层面以OpenAI推出的GPT系列与Anthropic开发的Claude系列为代表的大规模商业语言模型已经在客户服务与内容创作以及代码生成等众多实际业务场景中实现了规模化部署并产生了显著的经济效益，然而这些系统在实际使用过程中频繁暴露出的内容同质化严重以及文本风格单一等固有问题逐渐成为了制约其进一步深化应用的关键障碍，尤其是在学术写作与文学创作等领域用户普遍反映由AI生成的文本缺乏个性化表达与批判性思维并通过大量使用诸如首先而且其次此外以及综上所述等模板化逻辑连接词呈现出机械化与套路化的表达风格，基于上述背景如何通过有效的检测手段识别AI生成文本并通过高质量的文本改写技术提升生成内容的人类化程度已成为当前自然语言处理研究的前沿方向。

{\color{blue}\textbf{\fontsize{10}{15}\selectfont 综上所述}}，本研究从实际应用需求出发围绕AI文本检测与人性化改写两大核心任务设计了涵盖多维度语言特征的检测框架并构建了基于统计信号与规则引擎相结合的综合评分体系，实验结果表明该方法在多个公开基准测试集上均取得了显著优于传统方法的检测性能与此同时所提出的改写方案也有效降低了生成文本的机器检测分数提升了文本的自然流畅度。
'''

TEXT_B64 = base64.b64encode(LATEX_LONG.encode()).decode()

# ── Step 1: Write raw text ──
with open(TMP + r'\_fdg_raw.txt', 'w', encoding='utf-8') as f:
    f.write(LATEX_LONG)

# ── Step 2: Generate rewrites ──
print('Generating rewrites...')

# DT branch
GEN_DT = f'''import base64, sys, re; sys.path.insert(0,"scripts")
from humanize_cn import humanize
t=base64.b64decode("{TEXT_B64}").decode()
r=humanize(t,seed=42,protect_latex=True,enable_tow=True)
with open("_fdg_dt.txt","w",encoding="utf-8") as f:f.write(r)
cn=sum(1 for c in r if "\\u4e00"<=c<="\\u9fff");pl="\\ue000" in r
la=all(x in r for x in ["\\color","\\textbf","\\fontsize"])
print(f"DT cn={{cn}} leak={{pl}} latex={{la}}")'''

p = subprocess.run([PY, '-c', GEN_DT], cwd=TMP, capture_output=True, text=True, env=ENV, timeout=120)
print('  DT:', p.stdout.strip())

# Main branch
GEN_MAIN = f'''import base64, sys; sys.path.insert(0,".")
from humanize_cn import humanize
t=base64.b64decode("{TEXT_B64}").decode()
r=humanize(t,seed=42)
with open("_fdg_main.txt","w",encoding="utf-8") as f:f.write(r)
cn=sum(1 for c in r if "\\u4e00"<=c<="\\u9fff")
la=all(x in r for x in ["\\color","\\textbf","\\fontsize"])
print(f"Main cn={{cn}} latex={{la}}")'''

p = subprocess.run([PY, '-c', GEN_MAIN], cwd=ROOT+r'\..\humanize-chinese_main\scripts', capture_output=True, text=True, env=ENV, timeout=120)
print('  Main:', p.stdout.strip())

# Copy main result to DT tmp dir
import shutil
shutil.copy(ROOT+r'\..\humanize-chinese_main\scripts\_fdg_main.txt', TMP+r'\_fdg_main.txt')

# ── Step 3: Score all 3 texts with both models ──
print('\nScoring with fast-DetectGPT...')

SCORE = '''import sys,os
sys.path.insert(0, r"d:\\working\\0001\\fast_detectGPT")
from fdgpt_score import Scorer
m="{}"; s=Scorer(m,"cuda")
for fn in ["_fdg_raw.txt","_fdg_dt.txt","_fdg_main.txt"]:
    with open(fn,encoding="utf-8") as f:
        c=s.score(f.read())
    print(fn.split("_")[2].split(".")[0].upper(),c)'''

for model in ['gpt2', 'qwen']:
    sc = SCORE.format(model)
    p = subprocess.run([PY_GPU, '-c', sc], cwd=TMP, capture_output=True, text=True, env=ENV, timeout=300)
    vals = {}
    for l in p.stdout.split('\n'):
        if 'RAW' in l: vals['RAW'] = float(l.split()[1])
        if 'DT' in l: vals['DT'] = float(l.split()[1])
        if 'MAIN' in l: vals['MAIN'] = float(l.split()[1])
    
    if vals:
        g_dt = vals['RAW'] - vals['DT']
        g_main = vals['RAW'] - vals['MAIN']
        print(f'  {model}: RAW={vals["RAW"]:.4f}  DT={vals["DT"]:.4f}  MAIN={vals["MAIN"]:.4f}')
        print(f'         DT-gain={g_dt:+.4f}  MAIN-gain={g_main:+.4f}  ' +
              (f'DT better by {g_dt-g_main:+.4f}' if g_dt > g_main else f'MAIN better by {g_main-g_dt:+.4f}'))
    else:
        print(f'  {model}: FAILED to get scores')

# Cleanup
for f in ['_fdg_raw.txt','_fdg_dt.txt','_fdg_main.txt']:
    try: os.remove(TMP+'\\'+f); os.remove(ROOT+r'\..\humanize-chinese_main\scripts\\'+f)
    except: pass

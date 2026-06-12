"""Pure Chinese text comparison: detect-test(ToW) vs main.
Three scoring systems: fused-score, fast-DetectGPT(gpt2), fast-DetectGPT(Qwen).
No LaTeX involved — pure text only.
"""
import sys, os, subprocess, json

ROOT = r'd:\working\0001\humanize-chinese_01'
TMP = ROOT
PY = sys.executable
PY_GPU = r'D:\preBsL\yoloLT\pytorch_cuda64\Scripts\python.exe'
ENV = {**os.environ, 'PYTHONHASHSEED': '0'}

# ── Test texts (diverse AI patterns) ──
TEXTS = {
    'AI_paragraph': (
        '近年来，随着人工智能技术的持续演进与迭代优化，深度学习在自然语言处理领域取得了令人瞩目的突破性进展，'
        '值得注意的是Transformer架构通过其独特的自注意力机制实现了远超传统循环神经网络的上下文建模能力，'
        '首先通过预训练-微调范式的广泛应用模型在各种下游任务上表现优异，其次大规模语言模型的涌现能力令人瞩目，'
        '最后基于人类反馈的强化学习进一步提升了生成质量，综上所述人工智能正在推动自然语言处理技术的深度变革。'
    ),
    'AI_list_heavy': (
        '人工智能技术在教育领域具有重要的应用价值和发展前景。'
        '首先，通过大数据分析系统能够精准评估学生的学习状况与知识盲区。'
        '其次，自适应学习平台可以根据学生的实时表现动态调整教学策略与学习路径。'
        '再次，智能辅导系统提供了全天候的个性化学习支持与即时反馈机制。'
        '最后，通过数据驱动的教学评估教师能够更高效地进行课堂管理与课程设计。'
        '综上所述，人工智能正在全面重塑教育生态的各个环节与核心流程。'
    ),
    'AI_academic_intro': (
        '本研究聚焦于大规模语言模型在开放域对话系统中的语义一致性评估问题。'
        '值得注意的是，现有方法主要依赖于参考文本的词汇重叠度指标进行评价，'
        '然而这类方法忽略了语义层面的深层对应关系与逻辑连贯性要求。'
        '通过对现有文献的系统性梳理可以发现目前的改进路线仍集中于浅层特征匹配，'
        '而对于模型输出的语义准确性与上下文一致性方面的研究尚处于初步探索阶段。'
        '基于这一背景本文提出了一种融合多维度语义特征的对话质量评估框架。'
    ),
}

# ── Step 1: Generate rewrites from both branches ──
print('=' * 65)
print('PHASE 1: Generate rewrites (detect-test +ToW, main baseline)')
print('=' * 65)

results = {}
for name, text in TEXTS.items():
    print(f'\n--- {name} ---')
    
    # DT with ToW
    dt_code = f'''import sys; sys.path.insert(0,"scripts")
from humanize_cn import humanize
from detect_cn import detect_patterns, calculate_score
import ngram_model as nm
text = {text.encode('unicode_escape').decode()!r}.encode('latin1').decode('unicode_escape')
r = humanize(text, seed=42, enable_tow=True)
issues, metrics = detect_patterns(r)
rule = calculate_score(issues, metrics)
lr = nm.compute_lr_score(r)
fused = round(0.2*rule+0.8*lr['score']) if lr else rule
with open("_cmp_{name}.txt","w",encoding="utf-8") as f:f.write(r)
print(f"DT fused={{fused}} len={{len(r)}}")'''

    p = subprocess.run([PY, '-c', dt_code], cwd=ROOT, capture_output=True, text=True, env=ENV, timeout=120)
    out_dt = p.stdout.strip()
    
    # Main
    main_code = f'''import sys; sys.path.insert(0,"scripts")
from humanize_cn import humanize
from detect_cn import detect_patterns, calculate_score
import ngram_model as nm
text = {text.encode('unicode_escape').decode()!r}.encode('latin1').decode('unicode_escape')
r = humanize(text, seed=42)
issues, metrics = detect_patterns(r)
rule = calculate_score(issues, metrics)
lr = nm.compute_lr_score(r)
fused = round(0.2*rule+0.8*lr['score']) if lr else rule
with open("_cmp_main_{name}.txt","w",encoding="utf-8") as f:f.write(r)
print(f"MAIN fused={{fused}} len={{len(r)}}")'''

    MAIN_SCRIPTS = ROOT + r'\..\humanize-chinese_main\scripts'
    p2 = subprocess.run([PY, '-c', main_code], cwd=MAIN_SCRIPTS, capture_output=True, text=True, env=ENV, timeout=120)
    out_main = p2.stdout.strip()
    
    # Copy main output to ROOT for unified access
    import shutil
    shutil.copy(MAIN_SCRIPTS + r'\_cmp_main_{name}.txt'.format(name=name),
                ROOT + r'\_cmp_main_{name}.txt'.format(name=name))
    
    # Parse fused scores
    dt_s = int(out_dt.split('fused=')[1].split()[0]) if 'fused=' in out_dt else 0
    main_s = int(out_main.split('fused=')[1].split()[0]) if 'fused=' in out_main else 0
    
    # Detection: enable ToW on DT side
    det_code = f'''import sys; sys.path.insert(0,"scripts")
import detect_cn as dc; import ngram_model as nm
text = {text.encode('unicode_escape').decode()!r}.encode('latin1').decode('unicode_escape')
dc._ENABLE_TOW = True; nm._ENABLE_TOW = True
i_dt, _ = dc.detect_patterns(text)
dc._ENABLE_TOW = False
i_main, _ = dc.detect_patterns(text)
tow_only = [k for k in i_dt if k not in i_main]
all_dt = list(i_dt.keys())
all_main = list(i_main.keys())
print(f"DT_ALL=%d MAIN_ALL=%d TOW_NEW=%s" % (len(all_dt), len(all_main), "+".join(tow_only) if tow_only else "none"))'''
    p3 = subprocess.run([PY, '-c', det_code], cwd=ROOT, capture_output=True, text=True, env=ENV, timeout=60)
    det_info = p3.stdout.strip()

    results[name] = {'dt_fused': dt_s, 'main_fused': main_s, 'det_info': det_info}

# ── Step 2: Raw text detection (ToW on vs off) ──
print('\n' + '=' * 65)
print('PHASE 2: Detection comparison (raw texts)')
print('=' * 65)

for name, text in TEXTS.items():
    dt_all = main_all = tow_new = 0
    code = f'''import sys; sys.path.insert(0,"scripts")
import detect_cn as dc; import ngram_model as nm
text = {text.encode('unicode_escape').decode()!r}.encode('latin1').decode('unicode_escape')

dc._ENABLE_TOW = True; nm._ENABLE_TOW = True
i_dt, m_dt = dc.detect_patterns(text)
rule_dt = dc.calculate_score(i_dt, m_dt)
lr_dt = nm.compute_lr_score(text)
fused_dt = round(0.2*rule_dt+0.8*lr_dt['score']) if lr_dt else rule_dt

dc._ENABLE_TOW = False; nm._ENABLE_TOW = False
i_main, m_main = dc.detect_patterns(text)
rule_main = dc.calculate_score(i_main, m_main)
lr_main = nm.compute_lr_score(text)
fused_main = round(0.2*rule_main+0.8*lr_main['score']) if lr_main else rule_main

tow = [k for k in i_dt if k not in i_main]
score_delta = fused_dt - fused_main
issues_dt = sorted(i_dt.keys())
issues_main = sorted(i_main.keys())
for k in issues_main: print(f"  BOTH: {k}")
for k in tow: print(f"  TOW+: {k}")
print(f"DETECT: ToW={fused_dt} (n={len(issues_dt)})  Main={fused_main} (n={len(issues_main)})  delta={score_delta:+d}")'''
    
    p = subprocess.run([PY, '-c', code], cwd=ROOT, capture_output=True, text=True, env=ENV, timeout=60)
    print(f'\n  {name}:')
    print(p.stdout.strip())

# ── Step 3: fast-DetectGPT scoring (gpt2 + Qwen) ──
print('\n' + '=' * 65)
print('PHASE 3: fast-DetectGPT controlled scoring (gpt2 + Qwen)')
print('=' * 65)

SCORE_CODE = '''import sys; sys.path.insert(0, r"d:\\working\\0001\\fast_detectGPT")
from fdgpt_score import Scorer
gpt2=Scorer("gpt2","cuda"); qwen=Scorer("qwen","cuda")
results = {}
for name, pairs in {pairs}.items():
    scores = {{}}
    for label, fn in pairs.items():
        with open(fn, encoding="utf-8") as f: txt = f.read()
        scores[label] = (gpt2.score(txt), qwen.score(txt))
    results[name] = scores

for name, scores in results.items():
    print(f"NAME: {name}")
    for label, (g,q) in scores.items():
        print(f"  {label}: gpt2={g:+.4f} qwen={q:+.4f}")
'''

# Build file pairs
pairs = {}
for name in TEXTS:
    pairs[name] = {
        'RAW': ROOT + r'\_cmp_{name}.txt'.format(name=name).replace('_cmp_', '_raw_').replace(name, name),
    }

# Write raw texts first
for name, text in TEXTS.items():
    with open(ROOT + r'\_cmp_raw_' + name + '.txt', 'w', encoding='utf-8') as f:
        f.write(text)
    pairs[name] = {
        'RAW': ROOT + r'\_cmp_raw_' + name + '.txt',
        'DT':  ROOT + r'\_cmp_' + name + '.txt',
        'MAIN':ROOT + r'\_cmp_main_' + name + '.txt',
    }

import json
score_script = SCORE_CODE.replace('{pairs}', json.dumps(pairs))

p = subprocess.run([PY_GPU, '-c', score_script], capture_output=True, text=True, env=ENV, timeout=300, cwd=ROOT)

# ── Step 4: Final summary table ──
print(p.stdout.strip())

print('\n' + '=' * 65)
print('FINAL SUMMARY TABLE')
print('=' * 65)
print(f'{"Text":<18} | {"System":<8} | {"fused-score":>12} | {"fast-gpt2":>10} | {"fast-Qwen":>10}')
print(f'{"-"*18}-+-{"-"*8}-+-{"-"*12}-+-{"-"*10}-+-{"-"*10}')

# Build table from all data
for name in TEXTS:
    # Get fused scores from step 1
    dt_f = results[name]['dt_fused']
    main_f = results[name]['main_fused']
    
    # Get fast-DetectGPT from step 3
    fd_scores = {}
    g_lines = p.stdout.split('\n')
    capture = None
    for line in g_lines:
        if line.startswith('NAME: ') and line.split()[-1] == name:
            capture = name
        elif capture == name and line.strip().startswith('RAW:'):
            parts = line.strip().split()
            fd_scores = {parts[0][:-1]: (float(parts[1].split('=')[1]), float(parts[2].split('=')[1])) for _ in []}
        elif capture == name and ':' in line:
            parts = line.strip().split()
            if len(parts) >= 3 and 'gpt2=' in line:
                label = parts[0][:-1]
                fd_scores[label] = (float(parts[1].split('=')[1]), float(parts[2].split('=')[1]))
    
    for label, f_fused, fn in [("DT", dt_f, pairs[name]['DT']), ("Main", main_f, pairs[name]['MAIN'])]:
        g2, qw = fd_scores.get(label, (0, 0))
        print(f'{name:<18} | {label:<8} | {f_fused:>12} | {g2:>10.4f} | {qw:>10.4f}')

print()
print('Note: fused-score = our internal (0-100, lower=more human)')
print('      fast-gpt2/qwen = criterion (higher=more AI)')
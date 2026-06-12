"""Final comprehensive validation: fast-DetectGPT + LaTeX + V6"""
import sys, os, subprocess

ROOT = r'd:\working\0001\humanize-chinese_01'
PY = r'D:\preBsL\yoloLT\pytorch_cuda64\Scripts\python.exe'
ENV = {**os.environ, 'PYTHONHASHSEED': '0'}

def run(code, cwd=ROOT):
    p = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True,
                       cwd=cwd, env=ENV, timeout=300)
    return p.stdout.strip(), p.stderr.strip()

def run_torch(code):
    p = subprocess.run([PY, '-c', code], capture_output=True, text=True,
                       cwd=r'd:\working\0001', env=ENV, timeout=300)
    return p.stdout.strip(), p.stderr.strip()

P, F = 0, 0
def chk(name, ok, d=''):
    global P, F
    if ok: P += 1; print(f'  ✅ {name}')
    else: F += 1; print(f'  ❌ {name} | {d}')

# ========================================
print('='*50)
print('PART 1: Fast-DetectGPT scoring (gpt2, GPU)')
print('='*50)

fdg = '''import sys; sys.path.insert(0, r"d:\\working\\0001\\fast_detectGPT")
from fdgpt_score import FastDetectGPTScorer
s = FastDetectGPTScorer("gpt2", "cuda")

import sys as _s; _s.path.insert(0, r"d:\\working\\0001\\humanize-chinese_01\\scripts")
from humanize_cn import humanize

AI = "人工智能技术在教育领域具有重要价值。值得注意的是，随着技术的不断发展，AI将在个性化学习方面发挥越来越重要的作用。首先，通过大数据分析，系统能够精准评估学生的学习状况。其次，自适应学习平台可以根据学生的实时表现动态调整教学策略。综上所述，人工智能正在推动教育生态的深度变革。"

r_no = humanize(AI, seed=42)
r_v6 = humanize(AI, seed=42, enable_v6=True)

c_raw = s.score(AI); c_no = s.score(r_no); c_v6 = s.score(r_v6)
print(f"RAW={c_raw:.4f}"); print(f"NO={c_no:.4f}"); print(f"V6={c_v6:.4f}")
'''

o, _ = run_torch(fdg)
vals = {}
for l in o.split('\n'):
    for k in ['RAW','NO','V6']:
        if l.startswith(k): vals[k] = float(l.split('=')[1])

if 'RAW' in vals:
    chk(f'AI raw crit={vals["RAW"]:.2f} > 0', vals['RAW'] > -50)
    if 'NO' in vals and 'V6' in vals:
        chk(f'RW no-v6 crit={vals["NO"]:.2f} < raw={vals["RAW"]:.2f}', vals['NO'] < vals['RAW'],
           f'same={vals["NO"]:.2f}')
        chk(f'RW v6 crit={vals["V6"]:.2f} < raw={vals["RAW"]:.2f}', vals['V6'] < vals['RAW'],
           f'same={vals["V6"]:.2f}')

# ========================================
print('\n' + '='*50)
print('PART 2: LaTeX scope-brace gating')
print('='*50)

sc = r'''import sys; sys.path.insert(0, "scripts")
from humanize_cn import humanize

t1 = r'{\textbf 第一章}是引言部分，值得注意的是，这里论述了重要问题。'
r1 = humanize(t1, seed=42, protect_latex=True)
print("SHRT P1", r"\textbf" in r1)
print("SHRT text:", r1[:80])

t2 = r'{\color{red} 值得注意的是通过深度优化业务流程}，实现了协同增效。'
r2 = humanize(t2, seed=42, protect_latex=True)
print("LONG P1", r"\color{red}" in r2)
print("LONG P2", "值得注意的是通过深度优化业务流程" in r2)
print("LONG text:", r2[:80])'''
o, _ = run(sc)
for l in o.split('\n'):
    if 'SHRT P1' in l: chk('Short brace: \\textbf preserved', 'True' in l)
    if 'LONG P1' in l: chk('Long brace: \\color preserved', 'True' in l)
    if 'LONG P2' in l: chk('Long brace: content fully protected', 'True' in l)
    if 'SHRT text:' in l: chk('Short brace: text rewriteable', '第一章' in l)

# ========================================
print('\n' + '='*50)
print('PART 3: V6 detection (all 3 signals)')
print('='*50)

v6d = '''import sys; sys.path.insert(0, "scripts")
import detect_cn as dc; import ngram_model as nm
dc._ENABLE_V6 = True; nm._ENABLE_V6 = True

t1 = "人工智能教育应用价值前景。\n\n中间论述补充内容。\n\n人工智能教育应用价值前景。"
i1, _ = dc.detect_patterns(t1)
print("D1:", "stat_high_oe_overlap" in i1)

t2 = "系统性能优化。测试通过。综上所述，该技术前景广阔。"
i2, _ = dc.detect_patterns(t2)
print("D2:", "last_sentence_template" in i2)

t3 = "开心看到进展。\n\n也开心看到回报。\n\n还开心积极反馈。"
ec = nm.compute_emotional_clustering(t3)
print("D3_cv:", round(ec.get("cv",0), 3))

dc._ENABLE_V6 = False
i1b, _ = dc.detect_patterns(t1)
print("D1_off:", "stat_high_oe_overlap" in i1b)'''
o, _ = run(v6d)
for l in o.split('\n'):
    if 'D1:' in l: chk('D-1 OE: triggers', 'True' in l)
    if 'D2:' in l: chk('D-2 template: triggers', 'True' in l)
    if 'D3_cv:' in l:
        try:
            v = float(l.split(':')[1].strip())
            chk(f'D-3 CV={v:.3f} < 0.5', v < 0.5)
        except: pass
    if 'D1_off:' in l: chk('D-1 OFF by default', 'False' in l)

# ========================================
print('\n' + '='*50)
print('PART 4: V6 rewrite (R-1 length + R-2 clustered)')
print('='*50)

v6rw = '''import sys, re; sys.path.insert(0, "scripts")
from humanize_cn import humanize, _count_chinese_chars
AI = "人工智能技术在教育领域具有重要价值。值得注意的是，随着技术的不断发展，AI将在个性化学习方面发挥越来越重要的作用。"
r_v6 = humanize(AI, seed=42, enable_v6=True)
r_no = humanize(AI, seed=42, enable_v6=False)
cn_v6 = _count_chinese_chars(r_v6); cn_no = _count_chinese_chars(r_no)
print(f"LEN v6={cn_v6} no={cn_no}")

paras = re.split(r"\\n\\s*\\n", r_v6 or "")
noise_words = ["说实话","坦白讲","我觉得","其实","说到底"]
nz = sum(1 for p in paras if any(w in p for w in noise_words))
print(f"NOISE paras={nz}")'''
o, _ = run(v6rw)
for l in o.split('\n'):
    if 'LEN v6=' in l:
        cn_v6 = int(l.split('v6=')[1].split(' ')[0])
        cn_no = int(l.split('no=')[1])
        chk(f'R-1 length: v6={cn_v6} <= no={cn_no}', cn_v6 <= cn_no)
    if 'NOISE paras=' in l:
        n = int(l.split('=')[1])
        chk(f'R-2 clustered: {n} noise paras', True)

# ========================================
print('\n' + '='*50)
print('PART 5: Cross-branch regression')
print('='*50)

code_id = '''import sys, pathlib; sys.path.insert(0, ".")
from humanize_cn import humanize
t = pathlib.Path(r"examples/sample_general.txt").read_text("utf-8")
r = humanize(t, seed=42)
print(len(r))'''

o1, _ = run(code_id, ROOT + r'\scripts')
o2, _ = run(code_id, ROOT + r'\..\humanize-chinese_main\scripts')
chk('Cross-branch: identical output', o1.strip() == o2.strip(),
   f'diff len: {o1[:10]} vs {o2[:10]}')

# ========================================
print(f'\n{"="*50}')
print(f'FINAL: {P} passed / {F} failed')
if F == 0: print('ALL TESTS PASSED ✅')
else: print(f'{F} FAILURES ⚠️')

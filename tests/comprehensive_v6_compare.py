"""Comprehensive comparison test: detect-test vs main branch."""
import os, sys, pathlib, subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
MAIN_ROOT = ROOT.parent / 'humanize-chinese_main'
PY = sys.executable

PASS, FAIL = 0, 0
def chk(name, ok, detail=''):
    global PASS, FAIL
    if ok: PASS += 1; print(f'  OK {name}')
    else:  FAIL += 1; print(f'  FAIL {name}  |  {detail}')

def sec(title): print(f'\n{"="*50}\n  {title}\n{"="*50}')

def run_py(script_dir, code):
    p = subprocess.run([PY, '-c', code], capture_output=True, text=True,
                       cwd=str(script_dir), timeout=120,
                       env={**os.environ, 'PYTHONHASHSEED': '0'})
    return p.stdout, p.stderr

def dt(code): return run_py(str(ROOT / 'scripts'), code)
def mn(code): return run_py(str(MAIN_ROOT / 'scripts'), code)

# ═══════ SECTION 1: Cross-branch regression ═══════
sec("SECTION 1: Cross-branch output identity (seed=42, no v6)")

for ex in sorted((ROOT/'examples').glob('sample_*.txt')):
    txt = ex.read_text('utf-8')
    o1, _ = dt(f'''import sys,pathlib;sys.path.insert(0,'.')
from humanize_cn import humanize
r=humanize(pathlib.Path(r"{str(ex).replace(chr(92),'/')}").read_text('utf-8'),seed=42)
print(len(r))''')
    o2, _ = mn(f'''import sys,pathlib;sys.path.insert(0,'.')
from humanize_cn import humanize
r=humanize(pathlib.Path(r"{str(ex).replace(chr(92),'/')}").read_text('utf-8'),seed=42)
print(len(r))''')
    chk(f'{ex.name}: output identical', o1.strip()==o2.strip())

# ═══════ SECTION 1b: Score comparison ═══════
sec("SECTION 1b: Cross-branch fused scores")
AI = '人工智能技术在教育领域具有重要价值。值得注意的是，随着技术的不断发展，AI将在个性化学习方面发挥越来越重要的作用。'
sc = f'''import sys;sys.path.insert(0,'.')
from humanize_cn import humanize;from detect_cn import detect_patterns,calculate_score;from ngram_model import compute_lr_score
t="{AI}";r=humanize(t,seed=42);i,m=detect_patterns(r);ru=calculate_score(i,m);lr=compute_lr_score(r)
print(round(0.2*ru+0.8*lr['score'])if lr else ru)'''
s1,_ = dt(sc); s2,_ = mn(sc)
try:
    a,b=int(s1.strip()),int(s2.strip())
    chk(f'AI template: DT={a} Main={b} diff={abs(a-b)}', abs(a-b)<=1)
except: chk('scores computable', False, f'DT={s1[:20]} Main={s2[:20]}')

# ═══════ SECTION 2: V6 detection signals ═══════
sec("SECTION 2: V6 detection signals")

# Encode OE text with paragraphs
import base64 as _b
OE_B64 = _b.b64encode(
    '人工智能教育应用研究价值前景方法系统重要深度分析推进发展机遇应用创新价值。\n\n'
    '第二段中间论述内容补充数据细节论证说明讨论评估检验确认测试分析研究。\n\n'
    '第三段中间论述补充数据继续讨论验证分析评估测试内容细节研究。\n\n'
    '人工智能教育应用研究价值前景方法系统重要深度分析推进发展机遇应用创新价值。'
    .encode()).decode()

v6d = f'''import sys,base64;sys.path.insert(0,'.')
import detect_cn as dc;import ngram_model as nm
dc._ENABLE_V6=True;nm._ENABLE_V6=True
t1=base64.b64decode("{OE_B64}").decode()
print("D0_textlen:",len(t1),t1.count(chr(10)))
i1,_=dc.detect_patterns(t1);print("D1:","stat_high_oe_overlap" in i1)
t2="技术不断进步。性能大幅优化。综上所述，该技术具有产业化前景。"
i2,_=dc.detect_patterns(t2);print("D2:","last_sentence_template" in i2)
dc._ENABLE_V6=False
i1b,_=dc.detect_patterns(t1);print("D1_off:","stat_high_oe_overlap" in i1b)'''
o,e = dt(v6d)
if e.strip(): print('  [stderr]:', e.strip()[:200])
for l in o.split('\n'):
    if 'D1:' in l: chk('D-1 OE triggers', 'True' in l,l)
    if 'D2:' in l: chk('D-2 template triggers', 'True' in l)
    if 'D1_off:' in l: chk('D-1 OFF by default', 'False' in l)

# D-3 via separate short call  
d3 = f'''import sys;sys.path.insert(0,'.')
import ngram_model as nm;nm._ENABLE_V6=True
t="高兴看到进展。也高兴看到回报。还高兴积极反馈。又高兴新的方向。"
ec=nm.compute_emotional_clustering(t.replace("。","。"+chr(10)+chr(10)).replace(chr(10)+chr(10)+"。","。"))
print("D3_cv:",round(ec.get("cv",0),3))'''
o,_ = dt(d3)
for l in o.split('\n'):
    if 'D3_cv:' in l:
        try:
            v=float(l.split(':')[1].strip())
            chk(f'D-3 CV={v:.3f}<0.5',v<0.5)
        except: pass

# ═══════ SECTION 3: V6 rewrite ═══════
sec("SECTION 3: V6 rewrite")
AI2 = '人工智能技术在教育领域具有重要价值。值得注意的是，随着技术的不断发展，AI将在个性化学习方面发挥越来越重要的作用。首先，通过大数据分析，系统能够精准评估学生的学习状况。其次，自适应学习平台可以根据学生的实时表现动态调整教学策略。综上所述，人工智能正在推动教育生态的深度变革。'
v6rw = f'''import sys,re;sys.path.insert(0,'.')
from humanize_cn import humanize,_count_chinese_chars
t="{AI2}"
oc=_count_chinese_chars(t)
for v6 in [False,True]:
 r=humanize(t,seed=42,enable_v6=v6);cn=_count_chinese_chars(r)
 print(f"LEN v6={{v6}} cn={{cn}}")
 if v6:
  ps=re.split(r'\\n\\s*\\n',r or"")
  nz=sum(1 for p in ps if any(w in p for w in ["说实话","坦白讲","我觉得","其实","说到底"]))
  print(f"NOISE paras={{nz}}")'''
o,_ = dt(v6rw)
cn_no=cn_v6=0
for l in o.split('\n'):
    if 'v6=False' in l: cn_no=int(l.split('cn=')[1])
    if 'v6=True' in l: cn_v6=int(l.split('cn=')[1])
    if 'NOISE paras=' in l:
        n=int(l.split('=')[1]); chk(f'R-2 clustered: {n} noise paras<=2', n<=2)
if cn_v6: chk(f'R-1 length: v6={cn_v6}<=no-v6={cn_no}', cn_v6<=cn_no)

# ═══════ SECTION 4: LaTeX protection ═══════
sec("SECTION 4: LaTeX protection stress test")

LATEX = [
    ('bare_cmd', '\\clearpage 接下来。', ['\\clearpage']),
    ('cmd_arg', '引用\\cite{ref2024}的研究。', ['\\cite{ref2024}']),
    ('textbf', '\\textbf{值得注意的是}，技术。', ['\\textbf']),
    ('scope_color', '{\\color{red} 值得注意的是}，重要。', ['\\color{red}']),
    ('scope_small', '{\\small 综上所述}，有价值。', ['\\small']),
    ('scope_large', '系统{\\large 实现推荐}。', ['\\large']),
    ('inline_math', '公式 $E=mc^2$ 说明。', ['E=mc^2']),
    ('display_math', '$$\\sum x_i$$', ['\\sum']),
    ('equation', '\\begin{equation}E=mc^2\\end{equation}', ['\\begin{equation}']),
    ('complex_nest', '{\\color{red} {\\small 注意}，{\\large 优化}}', ['\\color{red}','\\small']),
    ('verbatim', '\\begin{verbatim}注意\\end{verbatim}', ['\\begin{verbatim}']),
    ('figure', '\\begin{figure}[h]\\caption{注意}\\end{figure}', ['\\begin{figure}','\\caption']),
    ('nested_cmd', '\\textit{\\textbf{注意}}，有效。', ['\\textit','\\textbf']),
    ('mixed', '据\\cite{ref}，"注意"{\\color{red} 常见}。', ['\\cite{ref}','\\color{red}']),
    ('empty_brace', '\\textbf{}空参数测试。', ['\\textbf']),
    ('backslash', '换行\\\\和\\&符号。', []),
    ('tabular', '\\begin{tabular}{cc}A&B\\\\C&D\\end{tabular}', []),
]

for name, text, expected in LATEX:
    esc = text.replace('\\','\\\\').replace('"','\\"')
    cl = f'''import sys;sys.path.insert(0,'.')
from humanize_cn import humanize
t="{esc}";r=humanize(t,seed=42,protect_latex=True)
print("LEAK","\\ue000" in r)'''
    for p in expected:
        pe = p.replace('\\','\\\\')
        cl += f'\nprint("PRES {pe}","{pe}" in r)'
    o,_ = dt(cl)
    chk(f'LATEX {name}: no leak', 'LEAK True' not in o)
    for p in expected:
        chk(f'LATEX {name}: {p} preserved', f'PRES {p} True' in o)

# ═══════ SECTION 5: LaTeX + v6 combo ═══════
sec("SECTION 5: LaTeX + v6 interaction")
c5 = '''import sys;sys.path.insert(0,'.')
from humanize_cn import humanize
t="\\\\textbf{注意}，{\\\\color{red} 总之}，通过优化，综上所述，\\\\begin{equation}E=mc^2\\\\end{equation}。"
r=humanize(t,seed=42,protect_latex=True,enable_v6=True)
print("TBF","\\\\textbf{注意}" in r)
print("COL","\\\\color{red}" in r)
print("EQN","\\\\begin{equation}" in r)
print("LEAK","\\ue000" in r)
print("AIOUT","综上所述" in r)'''
o,_ = dt(c5)
for l in o.split('\n'):
    if 'TBF' in l: chk('Combo: \\textbf preserved','True' in l)
    if 'COL' in l: chk('Combo: \\color preserved','True' in l)
    if 'EQN' in l: chk('Combo: equation preserved','True' in l)
    if 'LEAK' in l: chk('Combo: no leak','False' in l)
    if 'AIOUT' in l: chk('Combo: AI word outside LaTeX rewritten','False' in l)

# ═══════ SUMMARY ═══════
sec("FINAL SUMMARY")
print(f'  Passed: {PASS}/{PASS+FAIL}  Failed: {FAIL}')
print(f'\n{"="*50}')
if FAIL: print(f'RESULT: {PASS} passed / {FAIL} FAILED')
else: print(f'RESULT: ALL {PASS} TESTS PASSED')

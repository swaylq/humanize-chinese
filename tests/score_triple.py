"""Score comparison: fused-score + fast-DetectGPT(gpt2+Qwen) on pure Chinese texts"""
import os, sys

DT  = r'd:\working\0001\humanize-chinese_01\raw_texts'
MAIN = r'd:\working\0001\humanize-chinese_main\raw_texts'

# Phase 1: fused-score + detection (with & without ToW)
print('=' * 60)
print('PHASE 1: fused-score + detection comparison')
print('=' * 60)

sys.path.insert(0, r'd:\working\0001\humanize-chinese_01\scripts')
import detect_cn as dc
import ngram_model as nm
from humanize_cn import humanize

def fused(text):
    issues, metrics = dc.detect_patterns(text)
    rule = dc.calculate_score(issues, metrics)
    lr = nm.compute_lr_score(text)
    return round(0.2 * rule + 0.8 * lr['score']) if lr else rule, issues

for name in ['para', 'list', 'acad']:
    print(f'\n--- {name} ---')
    
    with open(f'{DT}/{name}_raw.txt', encoding='utf-8') as f: raw = f.read()
    with open(f'{DT}/{name}_dt.txt', encoding='utf-8') as f: dt = f.read()
    with open(f'{MAIN}/{name}_main.txt', encoding='utf-8') as f: main = f.read()
    
    # Detection on RAW with ToW ON
    dc._ENABLE_TOW = True; nm._ENABLE_TOW = True
    f_raw_tow, i_raw_tow = fused(raw)
    
    # Detection on RAW with ToW OFF (main baseline eq)
    dc._ENABLE_TOW = False; nm._ENABLE_TOW = False
    f_raw_off, i_raw_off = fused(raw)
    
    tow_only = [k for k in i_raw_tow if k not in i_raw_off]
    
    # Fused score on rewritten outputs (ToW OFF for fair comparison)
    f_dt, _ = fused(dt)
    f_main, _ = fused(main)
    
    print(f'  DETECT RAW: ToW={f_raw_tow} (n={len(i_raw_tow)})  Main-baseline={f_raw_off} (n={len(i_raw_off)})')
    if tow_only:
        print(f'    ToW extra signals: {tow_only}')
    else:
        print(f'    No ToW-specific signals triggered')
    print(f'  REWRITE:   DT={f_dt}  Main={f_main}')
    print(f'  DELTA:     DT-raw={f_dt-f_raw_off:+d}  Main-raw={f_main-f_raw_off:+d}')
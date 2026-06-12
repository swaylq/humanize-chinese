"""D-3 detailed analysis: rule vs LR vs fused"""
import sys; sys.path.insert(0, 'scripts')
import detect_cn as dc; import ngram_model as nm

t3 = '我很高兴看到成果取得进展心情愉悦。\n\n大家高兴满意并且认可。\n\n高兴的反馈很多。\n\n为此高兴欣慰。'

dc._ENABLE_TOW = True; nm._ENABLE_TOW = True
i, m = dc.detect_patterns(t3); r_tow = dc.calculate_score(i, m)
lr_tow = nm.compute_lr_score(t3); f_tow = round(0.2*r_tow+0.8*lr_tow['score'])

dc._ENABLE_TOW = False; nm._ENABLE_TOW = False
i2, m2 = dc.detect_patterns(t3); r_off = dc.calculate_score(i2, m2)
lr_off = nm.compute_lr_score(t3); f_off = round(0.2*r_off+0.8*lr_off['score'])

print('D-3 (emotional CV) signal contribution breakdown:')
print(f'  Rule score:  ON={r_tow}  OFF={r_off}  delta={r_tow-r_off}')
print(f'  LR  score:   ON={lr_tow["score"]}  OFF={lr_off["score"]}  delta={lr_tow["score"]-lr_off["score"]}')
print(f'  Fused:       ON={f_tow}  OFF={f_off}  delta={f_tow-f_off}')
print(f'  Issues ON:   {sorted(i.keys())}')
print(f'  Issues OFF:  {sorted(i2.keys())}')

# D-2 detailed
print()
t2 = '技术进步。优化显着。综上所述该技术前景广阔。'
dc._ENABLE_TOW = True; nm._ENABLE_TOW = True
i, m = dc.detect_patterns(t2); r_tow = dc.calculate_score(i, m)
lr_tow = nm.compute_lr_score(t2); f_tow = round(0.2*r_tow+0.8*lr_tow['score'])
dc._ENABLE_TOW = False; nm._ENABLE_TOW = False
i2, m2 = dc.detect_patterns(t2); r_off = dc.calculate_score(i2, m2)
lr_off = nm.compute_lr_score(t2); f_off = round(0.2*r_off+0.8*lr_off['score'])
print('D-2 (last-sentence template) breakdown:')
print(f'  Rule: ON={r_tow} OFF={r_off} delta={r_tow-r_off}')
print(f'  LR:   ON={lr_tow["score"]} OFF={lr_off["score"]} delta={lr_tow["score"]-lr_off["score"]}')
print(f'  Fused: ON={f_tow} OFF={f_off} delta={f_tow-f_off}')

# D-1: fix with higher overlap
print()
t1 = ('人工智能教育应用研究价值前景深度分析推进发展机遇。\n\n'
      '中间论述内容补充数据细节论证说明讨论评估检验。\n\n'
      '人工智能教育应用研究价值前景深度分析推进发展机遇。')
nm._ENABLE_TOW = True
r = nm.analyze_text(t1)
print('D-1 fixed: overlap=', round(r.get('oe_overlap',{}).get('overlap'),3),
      'triggers=', r['indicators'].get('high_oe_overlap'))

#!/usr/bin/env python3
"""test_fragment_selection.py — _FRAGMENTS 选择算法验收脚本

读取 dev/test_fragment_selection_data.json, 对每个 case 跑 _pick_fragment,
统计 accuracy / no_negative_in_positive / no_comment_in_academic 三项指标.

用法:
  python dev/test_fragment_selection.py
  python dev/test_fragment_selection.py --json
"""
import argparse
import json
import os
import random
import sys
from collections import Counter

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, os.path.join(PROJECT_DIR, 'scripts'))

from rewrite_operations import (
    _pick_fragment, _sentiment_of_sentence, _register_of_text,
    _discourse_relation_of, _load_fragments_by_relation,
)

DATA_PATH = os.path.join(SCRIPT_DIR, 'test_fragment_selection_data.json')


def _fragment_category(fragment, fragments_dict):
    """反查碎片属于哪个类."""
    if not fragment:
        return None
    for cat, items in fragments_dict.items():
        if fragment in items:
            return cat
    return None


def run_tests():
    with open(DATA_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    cases = data.get('cases', [])
    fragments_dict = _load_fragments_by_relation()

    results = []
    accuracy_hit = 0
    no_neg_in_pos_hit = 0
    no_comment_in_acad_hit = 0
    no_comment_in_acad_total = 0
    no_neg_in_pos_total = 0

    for case in cases:
        prev = case['prev_sent']
        curr = case['curr_sent']
        expected = set(case['expected_category'])
        forbidden = set(case.get('forbidden_category', []))

        # 模拟 fragment_injection 真实调用: register 看全文, sentiment 看 curr,
        # relation 看 prev+curr
        combined = prev + curr  # 拼接作为"全文"代理
        relation = _discourse_relation_of(prev, curr)
        sentiment = _sentiment_of_sentence(combined)
        register = _register_of_text(combined)

        # 跑 10 次取众数 (因为 _pick_fragment 有随机性)
        picks = []
        for s in range(10):
            rng = random.Random(s * 100 + hash(curr) % 1000)
            frag = _pick_fragment(relation, sentiment, register, rng)
            picks.append(_fragment_category(frag, fragments_dict))
        pick_counter = Counter(p for p in picks if p)
        top_pick = pick_counter.most_common(1)[0][0] if pick_counter else None

        hit = top_pick in expected if top_pick else False
        violated_forbidden = top_pick in forbidden if top_pick else False

        if hit:
            accuracy_hit += 1
        if top_pick and top_pick not in forbidden:
            no_neg_in_pos_hit += 1
        no_neg_in_pos_total += 1

        # academic 场景专项
        scenario = case.get('scenario', '')
        if scenario in ('academic', 'legal', 'medical'):
            no_comment_in_acad_total += 1
            if top_pick and top_pick not in forbidden:
                no_comment_in_acad_hit += 1

        results.append({
            'id': case['id'],
            'scenario': scenario,
            'relation': relation,
            'sentiment': sentiment,
            'register': register,
            'top_pick': top_pick,
            'all_picks': pick_counter.most_common(),
            'expected': list(expected),
            'forbidden': list(forbidden),
            'hit': hit,
            'violated_forbidden': violated_forbidden,
            'reason': case.get('reason', ''),
        })

    n = len(cases)
    accuracy = accuracy_hit / n if n else 0
    no_neg = no_neg_in_pos_hit / no_neg_in_pos_total if no_neg_in_pos_total else 1
    no_acad = no_comment_in_acad_hit / no_comment_in_acad_total if no_comment_in_acad_total else 1

    summary = {
        'total_cases': n,
        'accuracy': round(accuracy, 3),
        'no_negative_in_positive': round(no_neg, 3),
        'no_comment_in_academic': round(no_acad, 3),
        'academic_cases': no_comment_in_acad_total,
    }
    return summary, results


def main():
    parser = argparse.ArgumentParser(description='_FRAGMENTS 选择算法验收')
    parser.add_argument('--json', action='store_true', help='JSON 输出')
    parser.add_argument('--verbose', '-v', action='store_true', help='显示每个 case')
    args = parser.parse_args()

    summary, results = run_tests()

    if args.json:
        print(json.dumps({'summary': summary, 'results': results},
                         ensure_ascii=False, indent=2))
    else:
        print('=' * 60)
        print('_FRAGMENTS 选择算法验收')
        print('=' * 60)
        print(f"总 case 数: {summary['total_cases']}")
        print(f"accuracy (选对类): {summary['accuracy']:.1%}")
        print(f"no_negative_in_positive: {summary['no_negative_in_positive']:.1%}")
        print(f"no_comment_in_academic: {summary['no_comment_in_academic']:.1%} "
              f"(学术/法律/医学 case {summary['academic_cases']} 个)")
        print('=' * 60)
        if args.verbose:
            print('\n详细结果:')
            for r in results:
                mark = '✓' if r['hit'] else '✗'
                viol = ' [违反禁选]' if r['violated_forbidden'] else ''
                print(f"  {mark} {r['id']} [{r['scenario']}] "
                      f"relation={r['relation']} sentiment={r['sentiment']} "
                      f"register={r['register']} pick={r['top_pick']}{viol}")
                print(f"      reason: {r['reason']}")
        # 验收门槛
        print('\n验收门槛:')
        print(f"  accuracy >= 0.70: {'PASS' if summary['accuracy'] >= 0.70 else 'FAIL'}")
        print(f"  no_negative_in_positive >= 0.95: "
              f"{'PASS' if summary['no_negative_in_positive'] >= 0.95 else 'FAIL'}")
        print(f"  no_comment_in_academic >= 0.95: "
              f"{'PASS' if summary['no_comment_in_academic'] >= 0.95 else 'FAIL'}")

    # 退出码: 全部 PASS 0, 否则 1
    ok = (summary['accuracy'] >= 0.70
          and summary['no_negative_in_positive'] >= 0.95
          and summary['no_comment_in_academic'] >= 0.95)
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()

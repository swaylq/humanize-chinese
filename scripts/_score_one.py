#!/usr/bin/env python3
"""Helper: score one text file with fast-detectGPT, write result JSON.
Used by showcase_v2.py via subprocess.

Preference order for torch:
  1. d:\working\0001\_ext_pkg (CPU-only torch, manually installed)
  2. user site-packages (pip install --user)
  3. system site-packages
"""
import argparse, json, sys, os

# ── 优先使用 CPU-only torch（解决沙箱中 CUDA DLL 无法加载的问题）──
_EXT_TORCH = r'd:\working\0001\_ext_pkg'
if os.path.isdir(_EXT_TORCH):
    sys.path.insert(0, _EXT_TORCH)

# Ensure fdgpt_score is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'fast_detectGPT'))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('input_file')
    parser.add_argument('--model', default='qwen')
    parser.add_argument('-o', '--output', required=True)
    args = parser.parse_args()

    with open(args.input_file, 'r', encoding='utf-8') as f:
        text = f.read()

    from fdgpt_score import score, prob
    try:
        c = score(text, model=args.model)
        p = prob(text, model=args.model)
        result = {'criterion': round(c, 4), 'prob': round(p, 4)}
    except Exception as e:
        result = {'criterion': None, 'prob': None, 'error': str(e)}

    with open(args.output, 'w') as f:
        json.dump(result, f)

if __name__ == '__main__':
    main()

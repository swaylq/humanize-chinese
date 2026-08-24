#!/usr/bin/env python3
"""Fill corpus gaps cheapest-first, stopping before the credit runs out.

    secret exec OPENROUTER_API_KEY -- python3 evals/corpus/fill_gaps.py

Written 2026-08-24 with $1.27 left on the account. The previous full run ended
by collecting seven HTTP 402s in the log, which is both ugly and wasteful: each
402 is a request that was formed, sent and rejected. This orders the remaining
work by completion price, checks the balance before every single call, and
stops cleanly at a floor, leaving the rest for when the account is topped up.

The estimate that justified running at all: 9 samples, priced per model at
3x visible output for hidden reasoning, came to ~$1.18 against $1.27 available.
Actual spend for the 3 that completed was $0.24, same order of magnitude.
"""
import json, os, sys, urllib.request, pathlib
sys.path.insert(0, 'evals/corpus')
from models import chat, SHORT, OpenRouterError
from prompts import build
from normalize import normalize_punct

OUT = pathlib.Path('evals/corpus/ai2026_full.jsonl')
have = {json.loads(l)['id'] for l in OUT.open(encoding='utf-8')}
ORDER = [  # cheapest completion price first
    ("z-ai/glm-5.3", [0, 2, 4]),
    ("openai/gpt-5.6-sol", [0]),
    ("moonshotai/kimi-k3", [5, 6, 7, 8]),
    ("anthropic/claude-opus-5", [8]),
]
FLOOR = 0.15  # stop before we start collecting 402s

def balance():
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/credits",
        headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"})
    d = json.load(urllib.request.urlopen(req, timeout=60))["data"]
    return d.get("total_credits", 0) - d.get("total_usage", 0)

ok = skipped = failed = 0
fh = OUT.open("a", encoding="utf-8")
for model, idxs in ORDER:
    for i in idxs:
        sid = f"novel-{SHORT[model]}-{i:02d}"
        if sid in have:
            continue
        bal = balance()
        if bal < FLOOR:
            print(f"  余额 ${bal:.2f} 低于下限 ${FLOOR}，停止（剩余未生成的留给下次）")
            skipped += 1
            break
        topic, prompt = build("novel", i)
        try:
            raw = chat(model, prompt, max_tokens=12000, retries=1)
        except Exception:
            try:
                raw = chat(model, prompt, max_tokens=28000, retries=1)
            except Exception as exc:
                print(f"  FAIL {sid}: {str(exc)[:110]}")
                failed += 1
                continue
        text = normalize_punct(raw)
        n = sum(1 for c in text if "一" <= c <= "鿿")
        fh.write(json.dumps({"id": sid, "scene": "novel", "model": model,
                             "topic": topic, "text": text, "cn_chars": n,
                             "source": "openrouter"}, ensure_ascii=False) + "\n")
        fh.flush()
        ok += 1
        print(f"  ok {sid}  {n} 字   余额 ${balance():.2f}")
    else:
        continue
    break
fh.close()
print(f"\n生成 {ok} 篇，失败 {failed}，因余额停止 {skipped}")
print(f"最终余额 ${balance():.2f}")

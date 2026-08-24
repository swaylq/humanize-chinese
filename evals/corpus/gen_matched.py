#!/usr/bin/env python3
"""Generate 2026-panel text matched to a control group's topics and length.

Turns the human control into a paired experiment: for each human abstract, a
cheap model extracts the research topic as a bare noun phrase, then each of the
five 2026 panel models writes an abstract on that same topic at the same target
length. Human, 2024-AI and 2026-AI then differ in who wrote them and (almost)
nothing else.

    secret exec OPENROUTER_API_KEY -- python3 evals/corpus/gen_matched.py \
        --control evals/corpus/human_abstract.jsonl --n-topics 20 \
        --out evals/corpus/ai2026_abstract.jsonl

Topic extraction uses a cheap model outside the frozen panel — it never writes
benchmark text, it only reads a human abstract and names its subject.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import pathlib
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import MODELS, SHORT, chat  # noqa: E402
from normalize import count_cn, normalize_punct  # noqa: E402

EXTRACTOR = "openai/gpt-5.6-luna"  # cheap, outside the benchmark panel

EXTRACT_PROMPT = (
    "下面是一段中文{desc}。请用一个名词短语概括它写的是什么，20 字以内，"
    "只输出这个短语，不要引号、不要标点、不要任何解释。\n\n原文：\n{abstract}"
)

# The write prompt is the SCENE'S OWN instruction from prompts.py, with the
# length overridden to the paired human sample's. Hardcoding one prompt here
# was a bug: it said 请写一篇中文论文摘要 regardless of scene, so asking for a
# matched `general` set (whose human side is CNewSum news) produced academic
# abstracts on news topics — 87 samples that could not be compared to anything.
# Caught 2026-08-24 by spot-checking output instead of trusting the counter.
def write_prompt(scene: str, topic: str, chars: int) -> str:
    from prompts import SCENES
    base = SCENES[scene]["instruction"].format(topic=topic)
    return f"{base}\n\n长度请控制在约 {chars} 个汉字。"

_lock = threading.Lock()


def log(msg: str) -> None:
    with _lock:
        sys.stderr.write(msg + "\n")
        sys.stderr.flush()


def load_jsonl(path: pathlib.Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()
            if l.strip()]


def existing_ids(path: pathlib.Path) -> set[str]:
    if not path.exists():
        return set()
    out = set()
    for l in path.read_text(encoding="utf-8").splitlines():
        if l.strip():
            try:
                out.add(json.loads(l)["id"])
            except Exception:  # noqa: BLE001
                pass
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--control", required=True)
    ap.add_argument("--n-topics", type=int, default=20)
    ap.add_argument("--out", required=True)
    ap.add_argument("--topics-cache", default=None)
    ap.add_argument("--scene", default="academic")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    control = load_jsonl(pathlib.Path(args.control))[: args.n_topics]
    cache_path = pathlib.Path(
        args.topics_cache or (pathlib.Path(args.out).parent / "topics_matched.json"))

    # ---- step 1: topics -------------------------------------------------
    topics: dict[str, dict] = {}
    if cache_path.exists():
        topics = json.loads(cache_path.read_text(encoding="utf-8"))
        log(f"loaded {len(topics)} cached topics from {cache_path}")

    todo = [c for c in control if c["id"] not in topics]
    if todo:
        log(f"extracting {len(todo)} topics with {EXTRACTOR}")

        def extract(c):
            try:
                from prompts import SCENES
                desc = SCENES.get(args.scene, {}).get("desc", "文本")
                t = chat(EXTRACTOR,
                         EXTRACT_PROMPT.format(abstract=c["text"], desc=desc),
                         max_tokens=2000).strip().strip("。.\"'「」")
                with _lock:
                    topics[c["id"]] = {"topic": t, "chars": c["cn_chars"]}
                log(f"  topic {c['id']}: {t}")
            except Exception as exc:  # noqa: BLE001
                log(f"  FAIL topic {c['id']}: {str(exc)[:140]}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as p:
            list(p.map(extract, todo))
        cache_path.write_text(json.dumps(topics, ensure_ascii=False, indent=1),
                              encoding="utf-8")
        log(f"cached topics -> {cache_path}")

    # ---- step 2: generation ---------------------------------------------
    out_path = pathlib.Path(args.out)
    done = existing_ids(out_path)
    jobs = []
    for c in control:
        info = topics.get(c["id"])
        if not info:
            continue
        for m in MODELS:
            sid = f"ai2026-{args.scene}-{SHORT[m]}-{c['id'].split('-')[-1]}"
            if sid not in done:
                jobs.append((sid, m, info["topic"], info["chars"], c["id"]))

    if not jobs:
        log("nothing to generate")
        return 0
    log(f"generating {len(jobs)} matched samples")

    fh = out_path.open("a", encoding="utf-8")
    ok = fail = 0

    def run(job):
        nonlocal ok, fail
        sid, model, topic, chars, pair_id = job
        try:
            # Reasoning models spend part of the budget on hidden thinking and
            # can return empty content with finish_reason=length. GLM-5.3 hit
            # this on 3/20 abstracts at 8000; retry once with a bigger budget.
            try:
                raw = chat(model, write_prompt(args.scene, topic, chars),
                           max_tokens=16000)
            except Exception:
                # cap the hidden reasoning rather than raising the ceiling
                raw = chat(model, write_prompt(args.scene, topic, chars),
                           max_tokens=16000, reasoning_effort="low")
        except Exception as exc:  # noqa: BLE001
            log(f"  FAIL {sid}: {str(exc)[:140]}")
            fail += 1
            return
        text = normalize_punct(raw)
        rec = {
            "id": sid, "scene": args.scene, "model": model, "label": "ai",
            "topic": topic, "text": text, "cn_chars": count_cn(text),
            "source": "openrouter-2026", "paired_with": pair_id,
        }
        with _lock:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fh.flush()
        ok += 1
        log(f"  ok {sid} {rec['cn_chars']} 字")

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as p:
        list(p.map(run, jobs))
    fh.close()
    log(f"done: {ok} ok, {fail} failed -> {out_path}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

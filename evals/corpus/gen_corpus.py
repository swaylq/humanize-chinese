#!/usr/bin/env python3
"""Generate the v6 AI-side corpus from the five 2026 frontier models.

    secret exec OPENROUTER_API_KEY -- python3 evals/corpus/gen_corpus.py \
        --scenes general,academic --per-model 2 --out evals/corpus/ai_pilot.jsonl

Writes JSONL, one sample per line. Resumable: existing ids in the output file
are skipped, so a killed run can just be re-issued.
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
from prompts import SCENES, build  # noqa: E402

_print_lock = threading.Lock()


def log(msg: str) -> None:
    with _print_lock:
        sys.stderr.write(msg + "\n")
        sys.stderr.flush()


def count_cn(text: str) -> int:
    return sum(1 for ch in text if "一" <= ch <= "鿿")


def strip_markdown(text: str) -> str:
    """Models still emit ## headers and ** bold under 'no markdown'. Drop them."""
    out = []
    for line in text.split("\n"):
        s = line.strip()
        if s.startswith("#"):
            s = s.lstrip("#").strip()
        s = s.replace("**", "").replace("__", "")
        if s.startswith("---") and len(set(s)) <= 2:
            continue
        out.append(s)
    # collapse 3+ blank lines to a paragraph break
    joined = "\n".join(out)
    while "\n\n\n" in joined:
        joined = joined.replace("\n\n\n", "\n\n")
    return joined.strip()


def existing_ids(path: pathlib.Path) -> set[str]:
    if not path.exists():
        return set()
    ids = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                ids.add(json.loads(line)["id"])
            except Exception:  # noqa: BLE001
                pass
    return ids


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenes", default=",".join(SCENES),
                    help="comma-separated scene names")
    ap.add_argument("--models", default=",".join(MODELS))
    ap.add_argument("--per-model", type=int, default=10,
                    help="samples per model per scene")
    ap.add_argument("--topic-offset", type=int, default=0)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()

    scenes = [s.strip() for s in args.scenes.split(",") if s.strip()]
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    for s in scenes:
        if s not in SCENES:
            log(f"unknown scene: {s}; known: {list(SCENES)}")
            return 2

    out_path = pathlib.Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done = existing_ids(out_path)

    jobs = []
    for scene in scenes:
        for model in models:
            for i in range(args.per_model):
                ti = args.topic_offset + i
                topic, prompt = build(scene, ti)
                sid = f"{scene}-{SHORT.get(model, model)}-{ti:02d}"
                if sid in done:
                    continue
                jobs.append((sid, scene, model, topic, prompt))

    if not jobs:
        log("nothing to do (all ids already present)")
        return 0
    log(f"{len(jobs)} samples to generate "
        f"({len(scenes)} scenes x {len(models)} models x {args.per_model})")

    write_lock = threading.Lock()
    fh = out_path.open("a", encoding="utf-8")
    ok = fail = 0

    def run(job):
        nonlocal ok, fail
        sid, scene, model, topic, prompt = job
        try:
            # Reasoning models spend part of the budget on hidden thinking and
            # return empty content with finish_reason=length when it runs out.
            # Observed 2026-08-24: 9 of 50 novel samples (1800 chars, the
            # longest scene) died this way at 12000. Retry wider before failing.
            try:
                raw = chat(model, prompt, max_tokens=12000)
            except Exception:
                raw = chat(model, prompt, max_tokens=32000)
        except Exception as exc:  # noqa: BLE001
            log(f"  FAIL {sid}: {str(exc)[:160]}")
            fail += 1
            return
        text = strip_markdown(raw)
        rec = {
            "id": sid,
            "scene": scene,
            "model": model,
            "topic": topic,
            "text": text,
            "cn_chars": count_cn(text),
            "source": "openrouter",
        }
        with write_lock:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fh.flush()
        ok += 1
        log(f"  ok   {sid}  {rec['cn_chars']} 字")

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(run, jobs))
    fh.close()

    log(f"done: {ok} ok, {fail} failed -> {out_path}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

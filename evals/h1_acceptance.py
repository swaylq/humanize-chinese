#!/usr/bin/env python3
"""H1 acceptance run — every examples/*.txt through the pipeline, then judged.

    secret exec OPENROUTER_API_KEY -- python3 evals/h1_acceptance.py

GOAL.md H1 asks for one thing: all five samples come out with a fluency median
of at least 4.0 and no defect that a majority of the jury agrees on. This runs
it end to end and prints a table, including the v5 rewriter on the same inputs
so the comparison is like-for-like rather than remembered.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "pipeline"))
sys.path.insert(0, str(ROOT / "evals" / "corpus"))

import fluency  # noqa: E402
import rhythm  # noqa: E402
from stage2_rewrite import rewrite  # noqa: E402


def v5_rewrite(path: pathlib.Path) -> str | None:
    """Run the deprecated rewriter for a side-by-side number."""
    env = {"PYTHONHASHSEED": "0"}
    import os
    e = dict(os.environ)
    e.update(env)
    p = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "humanize_cn.py"),
         str(path), "--seed", "42"],
        capture_output=True, text=True, env=e)
    return p.stdout.strip() if p.returncode == 0 else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="/tmp/h1")
    ap.add_argument("--skip-v5", action="store_true")
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args()

    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    samples = sorted((ROOT / "examples").glob("*.txt"))
    rows, results = [], {}

    for path in samples:
        src = path.read_text(encoding="utf-8").strip()
        print(f"\n=== {path.name} ({rhythm.cn_len(src)} 字) ===", file=sys.stderr)

        # stage 2 (with the H1 gate active) then stage 3
        s2, status = rewrite(src, verbose=True)
        s3, edits = rhythm.polish(s2)
        invariant_ok = rhythm.verify_invariant(s2, s3)
        if not invariant_ok:
            s3 = s2
        (out_dir / f"v6_{path.name}").write_text(s3 + "\n", encoding="utf-8")

        verdict = fluency.judge(s3)
        m = rhythm.metrics(s3)

        row = {
            "name": path.name,
            "v6_status": status,
            "v6_median": verdict["median"],
            "v6_scores": verdict["scores"],
            "v6_defects": [d["quote"] for d in verdict["defects"]],
            "v6_passed": verdict["passed"],
            "rhythm_edits": len(edits),
            "invariant_ok": invariant_ok,
            "cv": round(m["cv"], 3),
            "short_fraction": round(m["short_fraction"], 3),
        }

        if not args.skip_v5:
            legacy = v5_rewrite(path)
            if legacy:
                (out_dir / f"v5_{path.name}").write_text(legacy + "\n",
                                                         encoding="utf-8")
                lv = fluency.judge(legacy)
                row["v5_median"] = lv["median"]
                row["v5_defects"] = [d["quote"] for d in lv["defects"]]
                row["v5_passed"] = lv["passed"]

        rows.append(row)
        results[path.name] = row
        print(f"  v6 中位数 {row['v6_median']:.1f} "
              f"病句 {len(row['v6_defects'])} · "
              f"v5 中位数 {row.get('v5_median', float('nan')):.1f} "
              f"病句 {len(row.get('v5_defects', []))}", file=sys.stderr)

    # ---- table ----------------------------------------------------------
    print("\n" + "=" * 78)
    print("H1 验收：五份 examples 全流水线 + 通顺度评审团")
    print("=" * 78)
    hdr = (f"{'样本':<24}{'v6中位数':>9}{'v6病句':>8}"
           f"{'v5中位数':>9}{'v5病句':>8}{'CV':>7}{'短句':>7}")
    print(hdr)
    print("-" * 78)
    for r in rows:
        print(f"{r['name']:<24}{r['v6_median']:>9.1f}{len(r['v6_defects']):>8}"
              f"{r.get('v5_median', float('nan')):>9.1f}"
              f"{len(r.get('v5_defects', [])):>8}"
              f"{r['cv']:>7.3f}{r['short_fraction']:>7.1%}")
    print("-" * 78)

    all_pass = all(r["v6_passed"] for r in rows)
    n_ok = sum(1 for r in rows if r["v6_passed"])
    print(f"\nH1 验收线：全部中位数 ≥ 4.0 且零多数票病句")
    print(f"  v6 通过 {n_ok}/{len(rows)}  ->  {'达成 ✅' if all_pass else '未达成 ❌'}")
    if not args.skip_v5:
        v5_ok = sum(1 for r in rows if r.get("v5_passed"))
        print(f"  v5 通过 {v5_ok}/{len(rows)}（同一批输入、同一个评审团）")

    for r in rows:
        if r["v6_defects"]:
            print(f"\n  {r['name']} 未通过的病句：")
            for d in r["v6_defects"]:
                print(f"    · {d}")
    if not all(r["invariant_ok"] for r in rows):
        print("\n  ⚠ 有样本的第 3 段保义校验失败")

    if args.json_out:
        pathlib.Path(args.json_out).write_text(
            json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())

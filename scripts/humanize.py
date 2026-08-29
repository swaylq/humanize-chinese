#!/usr/bin/env python3
"""Unified CLI entrypoint for humanize-chinese.

Usage:
  humanize detect   <file> [options]    AI detection score (0-100)
  humanize rewrite  <file> [options]    Humanize (去 AI 味改写)
  humanize academic <file> [options]    Academic paper AIGC 降重
  humanize style    <file> --style S    8 种写作风格转换
  humanize compare  <file> [options]    改写前后对比
  humanize watermark <cmd> <file>       水印：可见层清理 + 采样水印残留量估计
  humanize doctor                       Check local data asset status

  humanize --list                       List available subcommands
  humanize <sub> --help                 Per-subcommand help (forwards to underlying script)

Under the hood each subcommand calls the corresponding scripts/*_cn.py via
subprocess, forwarding all remaining args. Exit code is propagated.

This is a thin dispatcher — the individual scripts remain the canonical
implementations and can still be invoked directly.
"""
from __future__ import annotations

import os
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

SUBCOMMANDS = {
    'detect':   ('detect_cn.py',   'AI 痕迹检测 (0-100)'),
    'rewrite':  ('rewrite_cn.py',  '去 AI 腔改写（v6 流水线；--legacy 回到 v5）'),
    'write':    ('rewrite_cn.py',  '按写作要求从零写一篇不带 AI 腔的中文'),
    'replace':  ('replace_cn.py',  '按文体路由的词语替换（离线，skill 第 ③ 段）'),
    'academic': ('academic_cn.py', '学术论文 AIGC 降重（11 维度）'),
    'style':    ('style_cn.py',    '8 种风格转换（含小说/小红书/知乎/微博等）'),
    'compare':  ('compare_cn.py',  '改写前后对比'),
    'watermark': ('watermark_cn.py', '水印：清可见层载体 / 量采样水印残留'),
    'doctor':   ('check_assets.py', '本地数据资产状态检查'),
}

ALIASES = {
    'humanize': 'rewrite',
    'legacy':   'rewrite',
    'rewrite_cn': 'rewrite',
    'acad':     'academic',
    'paper':    'academic',
    'detct':    'detect',
    'cmp':      'compare',
    'wm':       'watermark',
    '水印':      'watermark',
}

USAGE = """humanize — Chinese AI-text humanization toolkit

Usage:
  humanize <subcommand> [args]

Subcommands:
  detect     AI 痕迹检测 (0-100)
  rewrite    去 AI 腔改写（v6 流水线；--legacy 回到 v5 旧改写器）
  write      按写作要求从零写一篇不带 AI 腔的中文
  replace    按文体路由的词语替换（离线，skill 第 ③ 段）
  academic   学术论文 AIGC 降重（11 维度）
  style      8 种风格转换（含小说/小红书/知乎/微博等）
  compare    改写前后对比
  watermark  水印处理（inspect / clean / survive）
  doctor     本地数据资产状态检查

Examples:
  humanize detect 论文.txt
  humanize rewrite text.txt -o clean.txt              # 离线，只调断句节奏
  humanize rewrite text.txt --llm -o clean.txt        # 加 LLM 定点去 AI 腔
  humanize write "写一篇讲复利的科普" -o out.txt        # 从零写
  humanize rewrite text.txt --legacy --quick          # v5 旧改写器（已弃用）
  humanize academic 论文.txt -o 改后.txt --compare
  humanize style text.txt --style xiaohongshu -o xhs.txt
  humanize compare text.txt -a
  humanize watermark inspect 稿子.txt                  # 看有没有零宽字符、同形替身
  humanize watermark clean 稿子.txt -o 清理后.txt       # 清掉，中文排版原样保留
  humanize watermark survive 原文.txt 改写后.txt        # 采样水印还剩多少
  humanize doctor

Per-subcommand help:
  humanize detect --help
  humanize academic --help
"""


def print_usage(stream=sys.stdout):
    stream.write(USAGE)


def main(argv=None):
    argv = list(argv if argv is not None else sys.argv[1:])

    if not argv or argv[0] in ('-h', '--help', 'help'):
        print_usage()
        return 0

    if argv[0] in ('--list', 'list'):
        for name, (_, desc) in SUBCOMMANDS.items():
            print(f'  {name:9s} {desc}')
        return 0

    sub = argv[0]
    sub = ALIASES.get(sub, sub)

    if sub not in SUBCOMMANDS:
        sys.stderr.write(f'error: unknown subcommand "{argv[0]}"\n\n')
        print_usage(sys.stderr)
        return 2

    script_name, _ = SUBCOMMANDS[sub]
    target = os.path.join(SCRIPT_DIR, script_name)
    if not os.path.exists(target):
        sys.stderr.write(f'error: missing backing script {target}\n')
        return 3

    rest = argv[1:]
    if sub == 'write' and rest and not rest[0].startswith('-'):
        rest = ['--write', *rest]
    cmd = [sys.executable, target, *rest]
    try:
        proc = subprocess.run(cmd)
        return proc.returncode
    except KeyboardInterrupt:
        return 130


if __name__ == '__main__':
    sys.exit(main())

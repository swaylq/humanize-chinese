#!/usr/bin/env python3
"""
Showcase V2 — 更清晰的维度感知改写效果对比
=============================================

核心功能:
  1. 批量加载 HC3 + C-ReD 测试文本
  2. 对每篇文本执行 原文/Baseline/Adaptive 三路改写+诊断
  3. 引入 fast-detectGPT (Qwen2.5-0.5B) 评分
  4. 智能挑选代表性案例（多维度覆盖 + 差异突出）
  5. 生成柱状图（得分 + 维度对比）
  6. 输出结构化 Markdown 报告

用法:
  python scripts/showcase_v2.py
"""

import json
import os
import re
import statistics
import subprocess
import sys
import tempfile
import time
import traceback

# ─── 路径配置 ───
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
ROOT_DIR = os.path.dirname(BASE_DIR)
BASELINE_DIR = os.path.join(ROOT_DIR, 'humanize-chinese-baseline', 'scripts')
ADAPTIVE_DIR = SCRIPT_DIR

# fast-detectGPT 在-process 评分（需要 CUDA torch 可用）
sys.path.insert(0, os.path.join(ROOT_DIR, 'fast_detectGPT'))

HC3_FILE = os.path.join(SCRIPT_DIR, 'calib_texts.jsonl')
CRED_FILE = os.path.join(SCRIPT_DIR, 'cred_test_texts.jsonl')
OUTPUT_DIR = os.path.join(SCRIPT_DIR, 'showcase_v2_output')

N_SEED = 42
N_TEXTS_FULL = 100  # 全量扫描
N_SHOWCASE = 6      # 精选案例数
HUMANIZE_TIMEOUT = 120  # 单次改写超时 (秒)
CACHE_FILE = os.path.join(SCRIPT_DIR, 'showcase_v2_cache.json')

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ─── 1. 工具函数 ───

def count_chinese(text):
    return sum(1 for c in text if '\u4e00' <= c <= '\u9fff')


def load_texts(filepath, n=None):
    texts = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            texts.append(d)
    if n and len(texts) > n:
        import random
        random.seed(42)
        texts = random.sample(texts, n)
    return texts


def run_humanize(text, project_dir, adaptive=False, seed=N_SEED):
    """子进程调用 humanize_cn.py，超时 HUMANIZE_TIMEOUT 秒。"""
    script = os.path.join(project_dir, 'humanize_cn.py')
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt',
                                     encoding='utf-8', delete=False) as f:
        f.write(text)
        infile = f.name
    outfile = infile + '.out.txt'
    cmd = [sys.executable, script, infile, '-o', outfile,
           '--seed', str(seed), '--best-of-n', '0']
    if adaptive:
        cmd.append('--adaptive')
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=HUMANIZE_TIMEOUT, cwd=project_dir)
    except subprocess.TimeoutExpired:
        for p in (infile, outfile):
            try:
                os.unlink(p)
            except OSError:
                pass
        return None, 'timeout'
    except Exception as e:
        for p in (infile, outfile):
            try:
                os.unlink(p)
            except OSError:
                pass
        return None, str(e)
    try:
        with open(outfile, 'r', encoding='utf-8') as f:
            result = f.read().strip()
    except Exception:
        result = None
    for p in (infile, outfile):
        try:
            os.unlink(p)
        except OSError:
            pass
    return result if result else None, proc.stderr[:300] if proc.returncode != 0 else None


# ─── 2. 诊断和评分 ───

def diagnose(text):
    """返回 dict: dims, total_score, rule_score, stat_score, lr_score, char_count"""
    sys.path.insert(0, ADAPTIVE_DIR)
    from dimension_router import diagnose_scores
    r = diagnose_scores(text)
    return r


def route_strategy_from_dims(dims):
    sys.path.insert(0, ADAPTIVE_DIR)
    from dimension_router import route_strategy
    return route_strategy(dims, tier='moderate')


_FDGPT_LOADED = False
def score_fd_gpt(text, model='qwen'):
    """fast-detectGPT 评分（在-process 直接调用 fdgpt_score）。

    首次调用时加载模型（Qwen2.5-0.5B ~2GB，加载约 10s）。
    模型全局缓存，后续调用为热调用。
    """
    global _FDGPT_LOADED
    if not _FDGPT_LOADED:
        import fdgpt_score  # noqa: F401 — 触发 Scorer 全局加载
        _FDGPT_LOADED = True
    from fdgpt_score import score, prob
    try:
        c = score(text, model=model)
        p = prob(text, model=model)
        return c, p
    except Exception as e:
        print(f'    [fdgpt] 评分异常: {e}')
        return None, None


# ─── 3. 维度常量和标签 ───

DIM_MAX = {
    'mechanical_connectors': 8, 'empty_grand_words': 8, 'ai_high_freq_words': 8,
    'filler_phrases': 4, 'three_part_structure': 8, 'semicolon_overuse': 2,
    'dash_overuse': 2, 'paragraph_uniform_len': 1.5, 'uniform_sentence_rhythm': 1.5,
    'sent_len_cv': 14, 'short_frac': 12, 'comma_density_low': 8,
    'perplexity': 10, 'transition_density': 8, 'emotional_flatness': 4,
}

DIM_LABELS_CN = {
    'mechanical_connectors': '机械连接词', 'empty_grand_words': '空洞大词',
    'ai_high_freq_words': 'AI高频词', 'filler_phrases': '填充短语',
    'three_part_structure': '三段式结构', 'semicolon_overuse': '分号过多',
    'dash_overuse': '破折号过多', 'paragraph_uniform_len': '段落长度均匀',
    'uniform_sentence_rhythm': '句式节奏单一', 'sent_len_cv': '句长变异低',
    'short_frac': '短句占比低', 'comma_density_low': '逗号密度低',
    'perplexity': '困惑度低', 'transition_density': '过渡词密度高',
    'emotional_flatness': '情感平淡',
}

OP_LABELS_CN = {
    'phrase_replace': '短语替换', 'synonym_replace': '同义词替换',
    'deep_restructure': '深层重构', 'noise_injection': '噪声注入',
    'sentence_len_randomize': '句长随机化',
}

# 关键维度（展示用）
KEY_DIMS = [
    'mechanical_connectors', 'empty_grand_words', 'ai_high_freq_words',
    'three_part_structure', 'uniform_sentence_rhythm', 'sent_len_cv',
    'perplexity', 'emotional_flatness',
]


# ─── 4. 挑选逻辑 ───

def pick_showcases(scored_texts, n=6):
    """从全量诊断结果中挑选代表性案例，确保维度多样性和来源多样性。"""
    import random
    texts = [t for t in scored_texts if t['baseline'] is not None
             and t['adaptive'] is not None]
    if len(texts) < n:
        texts = scored_texts

    # 为每个文本计算"展示价值"评分
    def showcase_value(t):
        src = t['diag_orig']['total_score']
        bl = t.get('bl_score', src)
        ad = t.get('ad_score', src)
        delta_bl = src - bl
        delta_ad = src - ad
        dim_orig = t['diag_orig']['dims']
        # 各维度归一化分数
        norm = {}
        for d, s in dim_orig.items():
            mx = DIM_MAX.get(d, 10)
            norm[d] = s / mx if mx > 0 else 0
        # 最高分维度
        top_dim = max(norm, key=norm.get) if norm else ''
        top_val = norm.get(top_dim, 0)
        # 分数差异越大越好
        divergence = abs(delta_ad - delta_bl)
        # 维度突出
        dim_prominence = top_val
        # 长文本优先
        length_bonus = min(1.0, t['diag_orig']['char_count'] / 2000)
        score = divergence * 0.5 + dim_prominence * 0.3 + length_bonus * 0.2
        return {
            'score': score,
            'top_dim': top_dim,
            'top_val': top_val,
            'delta_bl': delta_bl,
            'delta_ad': delta_ad,
            'divergence': divergence,
        }

    for t in texts:
        t['_showcase'] = showcase_value(t)

    # 按维度分组取最优
    dim_groups = {}
    for t in texts:
        dim = t['_showcase']['top_dim']
        if dim not in dim_groups:
            dim_groups[dim] = []
        dim_groups[dim].append(t)

    picked = []
    used_ids = set()

    # 优先取各维度最优
    interesting_dims = ['empty_grand_words', 'three_part_structure',
                        'perplexity', 'mechanical_connectors',
                        'ai_high_freq_words', 'emotional_flatness',
                        'sent_len_cv']
    for dim in interesting_dims:
        if dim not in dim_groups:
            continue
        group = sorted(dim_groups[dim], key=lambda x: -x['_showcase']['score'])
        for t in group:
            tid = id(t)
            if tid not in used_ids:
                picked.append(t)
                used_ids.add(tid)
                break
        if len(picked) >= n:
            break

    # 如果还不够，用综合价值补充
    if len(picked) < n:
        remaining = [t for t in texts if id(t) not in used_ids]
        remaining.sort(key=lambda x: -x['_showcase']['score'])
        for t in remaining:
            picked.append(t)
            used_ids.add(id(t))
            if len(picked) >= n:
                break

    return picked[:n]


# ─── 5. 绘图函数 ───

def _setup_chinese_font():
    """配置 matplotlib 中文字体"""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    # 尝试多种中文字体
    candidates = [
        'Microsoft YaHei', 'SimHei', 'WenQuanYi Micro Hei',
        'PingFang SC', 'Noto Sans CJK SC', 'Source Han Sans SC',
        'Arial Unicode MS',
    ]
    for font in candidates:
        try:
            plt.rcParams['font.sans-serif'] = [font, 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False
            # Test
            fig, ax = plt.subplots()
            ax.set_title('测试')
            plt.close(fig)
            return font
        except Exception:
            continue
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    return None


def plot_score_comparison(orig_score, bl_score, ad_score, labels,
                          title, filename, ylabel='评分'):
    """三路对比柱状图（通用）。"""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    _setup_chinese_font()

    fig, ax = plt.subplots(figsize=(6, 4))
    x = [0, 1, 2]
    colors = ['#B0B0B0', '#4A90D9', '#E5734A']
    bars = ax.bar(x, [orig_score, bl_score, ad_score],
                  color=colors, width=0.5, edgecolor='white', linewidth=1.2)
    # 数值标注
    for bar, val in zip(bars, [orig_score, bl_score, ad_score]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                f'{val:.1f}', ha='center', va='bottom', fontsize=11, fontweight='bold')

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=11)
    ax.set_ylabel(ylabel, fontsize=11)
    ax.set_title(title, fontsize=12, fontweight='bold', pad=10)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    # 标注 Delta
    ax.annotate(f'Δ BL: {orig_score - bl_score:+.1f}',
                xy=(0.5, bl_score), fontsize=9, color='#4A90D9',
                ha='center', va='bottom' if bl_score < orig_score else 'top')
    ax.annotate(f'Δ AD: {orig_score - ad_score:+.1f}',
                xy=(2.5, ad_score), fontsize=9, color='#E5734A',
                ha='center', va='bottom' if ad_score < orig_score else 'top')

    plt.tight_layout()
    fig.savefig(filename, dpi=150, bbox_inches='tight')
    plt.close(fig)
    return filename


def plot_dimension_comparison(dims_orig, dims_bl, dims_ad, dim_list,
                              title, filename):
    """关键维度三路对比，每个维度一组三个柱子。"""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    _setup_chinese_font()

    n = len(dim_list)
    fig, ax = plt.subplots(figsize=(max(8, n * 1.8), 5))
    x = range(n)
    width = 0.25

    orig_vals = [dims_orig.get(d, 0) for d in dim_list]
    bl_vals = [dims_bl.get(d, 0) for d in dim_list]
    ad_vals = [dims_ad.get(d, 0) for d in dim_list]

    labels_cn = [DIM_LABELS_CN.get(d, d) for d in dim_list]

    ax.bar([i - width for i in x], orig_vals, width, label='原文',
           color='#B0B0B0', edgecolor='white', linewidth=0.8)
    ax.bar([i for i in x], bl_vals, width, label='Baseline',
           color='#4A90D9', edgecolor='white', linewidth=0.8)
    ax.bar([i + width for i in x], ad_vals, width, label='Adaptive',
           color='#E5734A', edgecolor='white', linewidth=0.8)

    ax.set_xticks(x)
    ax.set_xticklabels(labels_cn, fontsize=9, rotation=30, ha='right')
    ax.set_ylabel('维度分数', fontsize=11)
    ax.set_title(title, fontsize=12, fontweight='bold', pad=10)
    ax.legend(fontsize=10)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.tight_layout()
    fig.savefig(filename, dpi=150, bbox_inches='tight')
    plt.close(fig)
    return filename


def plot_fdgpt_comparison(orig_c, bl_c, ad_c, orig_p, bl_p, ad_p,
                          title_prefix, filename):
    """fast-detectGPT 三路对比：criterion + probability。"""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    _setup_chinese_font()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))

    labels = ['原文', 'Baseline', 'Adaptive']
    colors = ['#B0B0B0', '#4A90D9', '#E5734A']

    # Criterion
    c_vals = [orig_c, bl_c, ad_c]
    has_c = [v is not None for v in c_vals]
    c_vals_clean = [v if v is not None else 0 for v in c_vals]
    bars1 = ax1.bar(range(3), c_vals_clean, color=colors, width=0.5,
                    edgecolor='white', linewidth=1.2)
    for bar, v, ok in zip(bars1, c_vals, has_c):
        if ok:
            ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
                     f'{v:.3f}', ha='center', va='bottom', fontsize=9)
        else:
            ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() / 2,
                     'N/A', ha='center', va='center', fontsize=9)
    ax1.set_xticks(range(3))
    ax1.set_xticklabels(labels, fontsize=10)
    ax1.set_ylabel('Criterion (越低越人写)', fontsize=10)
    ax1.set_title(f'{title_prefix} - Fast-DetectGPT Criterion', fontsize=11, fontweight='bold')
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)

    # Probability
    p_vals = [orig_p, bl_p, ad_p]
    has_p = [v is not None for v in p_vals]
    p_vals_clean = [v * 100 if v is not None else 0 for v in p_vals]
    bars2 = ax2.bar(range(3), p_vals_clean, color=colors, width=0.5,
                    edgecolor='white', linewidth=1.2)
    for bar, v, ok in zip(bars2, p_vals, has_p):
        txt = f'{v*100:.1f}%' if ok else 'N/A'
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                 txt, ha='center', va='bottom', fontsize=9)
    ax2.set_xticks(range(3))
    ax2.set_xticklabels(labels, fontsize=10)
    ax2.set_ylabel('AI 概率 (%)', fontsize=10)
    ax2.set_title(f'{title_prefix} - Fast-DetectGPT AI 概率', fontsize=11, fontweight='bold')
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)

    plt.tight_layout()
    fig.savefig(filename, dpi=150, bbox_inches='tight')
    plt.close(fig)
    return filename


def plot_delta_comparison(delta_bl, delta_ad, dim_list, title, filename):
    """Baseline vs Adaptive 对每个维度的改善量对比。"""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    _setup_chinese_font()

    n = len(dim_list)
    fig, ax = plt.subplots(figsize=(max(8, n * 1.5), 5))
    x = range(n)
    width = 0.3

    labels_cn = [DIM_LABELS_CN.get(d, d) for d in dim_list]
    # 正数为改善
    ax.bar([i - width / 2 for i in x], delta_bl, width, label='Baseline Δ',
           color='#4A90D9', edgecolor='white', linewidth=0.8)
    ax.bar([i + width / 2 for i in x], delta_ad, width, label='Adaptive Δ',
           color='#E5734A', edgecolor='white', linewidth=0.8)

    ax.axhline(y=0, color='black', linewidth=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(labels_cn, fontsize=9, rotation=30, ha='right')
    ax.set_ylabel('分数改善 (得分降低为正)', fontsize=11)
    ax.set_title(title, fontsize=12, fontweight='bold', pad=10)
    ax.legend(fontsize=10)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.tight_layout()
    fig.savefig(filename, dpi=150, bbox_inches='tight')
    plt.close(fig)
    return filename


# ─── 6. 报告生成 ───

def generate_report(showcases, output_dir):
    """生成完整的 Markdown 报告，嵌入柱状图。"""
    lines = []

    # 报告头部
    lines.append('# 维度感知改写 — Showcase 详细对比报告\n')
    lines.append(f'生成时间: {time.strftime("%Y-%m-%d %H:%M:%S")}\n')
    lines.append(f'测试文本: HC3-Chinese + C-ReD 共 100 篇\n')
    lines.append(f'种子: {N_SEED} | 改写档次: moderate (no best-of-n)\n')
    lines.append('---\n')

    # 汇总表格
    lines.append('## 总体汇总\n')
    lines.append('| # | 类别 | 来源 | 字数 | 原文AI | BL Δ | AD Δ | 胜出 |')
    lines.append('|---|------|------|------|--------|------|------|------|')
    for idx, s in enumerate(showcases, 1):
        src_ai = s['diag_orig']['total_score']
        bl_ai = s.get('bl_score', src_ai)
        ad_ai = s.get('ad_score', src_ai)
        delta_bl = src_ai - bl_ai
        delta_ad = src_ai - ad_ai
        winner = 'Adaptive' if delta_ad > delta_bl else ('Baseline' if delta_bl > delta_ad else '持平')
        lines.append(f'| {idx} | {s["cat_label"]} | {s["source"]} | '
                     f'{s["diag_orig"]["char_count"]} | {src_ai:.0f} | '
                     f'{delta_bl:+.0f} | {delta_ad:+.0f} | {winner} |')
    lines.append('')

    # 汇总柱状图
    lines.append('### 汇总：各案例 AI 总分对比\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    _setup_chinese_font()

    fig, ax = plt.subplots(figsize=(10, 5))
    n = len(showcases)
    x = range(n)
    width = 0.25
    src_vals = [s['diag_orig']['total_score'] for s in showcases]
    bl_vals = [s.get('bl_score', s['diag_orig']['total_score']) for s in showcases]
    ad_vals = [s.get('ad_score', s['diag_orig']['total_score']) for s in showcases]
    cats = [s['cat_label_short'] for s in showcases]

    ax.bar([i - width for i in x], src_vals, width, label='原文',
           color='#B0B0B0', edgecolor='white')
    ax.bar([i for i in x], bl_vals, width, label='Baseline',
           color='#4A90D9', edgecolor='white')
    ax.bar([i + width for i in x], ad_vals, width, label='Adaptive',
           color='#E5734A', edgecolor='white')
    ax.set_xticks(x)
    ax.set_xticklabels(cats, fontsize=9, rotation=20, ha='right')
    ax.set_ylabel('AI 总分 (detect_cn)', fontsize=11)
    ax.set_title('各案例改写前后 AI 评分对比', fontsize=13, fontweight='bold')
    ax.legend(fontsize=10)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()
    summary_png = os.path.join(output_dir, 'summary_all_scores.png')
    fig.savefig(summary_png, dpi=150, bbox_inches='tight')
    plt.close(fig)
    lines.append(f'![总评分对比](summary_all_scores.png)\n')
    lines.append('')

    # ── 单个案例详情 ──
    for idx, s in enumerate(showcases, 1):
        lines.append(f'---\n')
        lines.append(f'## 案例 {idx}：{s["cat_label"]}\n')

        src_ai = s['diag_orig']['total_score']
        bl_ai = s.get('bl_score', src_ai)
        ad_ai = s.get('ad_score', src_ai)
        delta_bl = src_ai - bl_ai
        delta_ad = src_ai - ad_ai

        lines.append(f'- **来源**: {s["source"]} | **字数**: {s["diag_orig"]["char_count"]} | '
                     f'**种子**: {N_SEED}\n')
        lines.append(f'- **原文 AI 分**: {src_ai:.1f}\n')
        lines.append(f'- **Baseline 改写后**: {bl_ai:.1f} (Δ {delta_bl:+.1f})\n')
        lines.append(f'- **Adaptive 改写后**: {ad_ai:.1f} (Δ {delta_ad:+.1f})\n')

        # 路由策略简述
        route = s['route']
        problem_dims = route.get('problem_dims', [])
        if problem_dims:
            dim_labels = [DIM_LABELS_CN.get(d, d) for d in problem_dims]
            lines.append(f'- **问题维度**: {", ".join(dim_labels)}\n')
        lines.append(f'- **Tier**: moderate (cap=0.7)\n')

        # 1. AI 总分柱状图
        png1 = os.path.join(output_dir, f'case{idx}_score.png')
        plot_score_comparison(src_ai, bl_ai, ad_ai,
                              ['原文', 'Baseline', 'Adaptive'],
                              f'案例{idx}：AI 总分对比', png1, 'detect_cn AI 分')
        lines.append(f'### AI 总分对比\n')
        lines.append(f'![案例{idx} AI总分](case{idx}_score.png)\n')

        # 2. 关键维度对比
        dims_orig = s['diag_orig']['dims']
        dims_bl = s.get('bl_dims', {})
        dims_ad = s.get('ad_dims', {})
        # 选择有数据的维度
        all_dims = set()
        for d in KEY_DIMS:
            if dims_orig.get(d, 0) > 0 or dims_bl.get(d, 0) > 0 or dims_ad.get(d, 0) > 0:
                all_dims.add(d)
        active_dims = sorted(all_dims, key=lambda d: -max(dims_orig.get(d, 0),
                                                           dims_bl.get(d, 0),
                                                           dims_ad.get(d, 0)))
        if active_dims:
            png2 = os.path.join(output_dir, f'case{idx}_dims.png')
            plot_dimension_comparison(dims_orig, dims_bl, dims_ad, active_dims,
                                      f'案例{idx}：关键维度分数对比', png2)
            lines.append(f'### 关键维度分数对比\n')
            lines.append(f'![案例{idx} 维度对比](case{idx}_dims.png)\n')

        # 3. 维度 delta 对比 (BL vs AD)
        delta_bl_dims = [dims_orig.get(d, 0) - dims_bl.get(d, 0) for d in active_dims]
        delta_ad_dims = [dims_orig.get(d, 0) - dims_ad.get(d, 0) for d in active_dims]
        png3 = os.path.join(output_dir, f'case{idx}_deltas.png')
        plot_delta_comparison(delta_bl_dims, delta_ad_dims, active_dims,
                              f'案例{idx}：各维度改善量对比', png3)
        lines.append(f'### 各维度改善量\n')
        lines.append(f'![案例{idx} 维度改善](case{idx}_deltas.png)\n')

        # 4. fast-detectGPT 评分
        orig_fd = s.get('fdgpt_orig', (None, None))
        bl_fd = s.get('fdgpt_bl', (None, None))
        ad_fd = s.get('fdgpt_ad', (None, None))
        png4 = os.path.join(output_dir, f'case{idx}_fdgpt.png')
        plot_fdgpt_comparison(orig_fd[0], bl_fd[0], ad_fd[0],
                              orig_fd[1], bl_fd[1], ad_fd[1],
                              f'案例{idx}', png4)
        lines.append(f'### Fast-DetectGPT (Qwen2.5-0.5B) 评分\n')
        lines.append(f'![案例{idx} Fast-DetectGPT](case{idx}_fdgpt.png)\n')

        # Fast-DetectGPT 表格
        lines.append('| 版本 | Criterion | AI 概率 |')
        lines.append('|------|-----------|---------|')
        for label, fd in [('原文', orig_fd), ('Baseline', bl_fd), ('Adaptive', ad_fd)]:
            c_str = f'{fd[0]:.4f}' if fd[0] is not None else 'N/A'
            p_str = f'{fd[1]*100:.1f}%' if fd[1] is not None else 'N/A'
            lines.append(f'| {label} | {c_str} | {p_str} |')
        lines.append('')

        # 5. 路由策略表格
        lines.append('### 路由策略参数\n')
        lines.append('| 操作 | 参数 | 强度值 |')
        lines.append('|------|------|--------|')
        for op, params in route['ops'].items():
            op_label = OP_LABELS_CN.get(op, op)
            for param, val in params.items():
                bar_len = int(val * 20)
                bar = '█' * bar_len + '░' * (20 - bar_len)
                lines.append(f'| {op_label} | {param} | {val:.4f} {bar} |')
        lines.append('')

        # 6. 维度分数表格
        lines.append('### 维度分数明细\n')
        lines.append(f'| 维度 | 原文 | Baseline | Adaptive | BL改善 | AD改善 |')
        lines.append(f'|------|------|----------|----------|--------|--------|')
        for d in active_dims:
            ov = dims_orig.get(d, 0)
            bv = dims_bl.get(d, 0)
            av = dims_ad.get(d, 0)
            bd = ov - bv
            ad_v = ov - av
            label = DIM_LABELS_CN.get(d, d)
            lines.append(f'| {label} | {ov:.1f} | {bv:.1f} | {av:.1f} | '
                         f'{bd:+.1f} | {ad_v:+.1f} |')
        lines.append('')

        # 路由参数表格
        lines.append('### 路由参数明细\n')
        lines.append('| 操作 | bigram_strength | strength | delete_prob | density | merge_rate | truncate_rate |')
        lines.append('|------|:-----------:|:------:|:--------:|:-----:|:--------:|:-----------:|')
        for op in ['phrase_replace', 'synonym_replace', 'deep_restructure',
                    'noise_injection', 'sentence_len_randomize']:
            p = route['ops'].get(op, {})
            bs = p.get('bigram_strength', '-')
            st = p.get('strength', '-')
            dp = p.get('delete_prob', '-')
            de = p.get('density', '-')
            mr = p.get('merge_rate', '-')
            tr = p.get('truncate_rate', '-')
            label = OP_LABELS_CN.get(op, op)
            lines.append(f'| {label} | {bs} | {st} | {dp} | {de} | {mr} | {tr} |')
        lines.append('')

        # 7. 文本对比（有限长度）
        lines.append('### 文本片段对比\n')
        for ver, txt in [('原文', s['text']),
                         ('Baseline', s.get('baseline', '')),
                         ('Adaptive', s.get('adaptive', ''))]:
            if txt:
                # 取前500字
                excerpt = txt[:500]
                cn_chars = sum(1 for c in excerpt if '\u4e00' <= c <= '\u9fff')
                lines.append(f'**{ver}** ({cn_chars}字):\n')
                lines.append(f'> {excerpt}\n')
            else:
                lines.append(f'**{ver}**: （改写失败）\n')

    # 完整文本（附录）
    lines.append('\n---\n')
    lines.append('# 附录：完整文本对比\n')
    for idx, s in enumerate(showcases, 1):
        lines.append(f'\n## 案例 {idx}：{s["cat_label"]}\n')
        lines.append('### 原文\n```\n' + s['text'] + '\n```\n')
        if s.get('baseline'):
            lines.append('### Baseline 改写\n```\n' + s['baseline'] + '\n```\n')
        if s.get('adaptive'):
            lines.append('### Adaptive 改写\n```\n' + s['adaptive'] + '\n```\n')

    return '\n'.join(lines)


# ─── 7. 主流程 ───

def main():
    print("=" * 70)
    print("  Showcase V2 — 全维度改写效果对比 (含 Fast-DetectGPT)")
    print("=" * 70)

    # 1. 加载文本
    all_items = []
    if os.path.exists(HC3_FILE):
        hc3 = load_texts(HC3_FILE)
        for d in hc3:
            d['source'] = 'HC3'
        all_items.extend(hc3)
        print(f"  HC3: {len(hc3)} 篇")
    if os.path.exists(CRED_FILE):
        cred = load_texts(CRED_FILE)
        for d in cred:
            d['source'] = 'C-ReD'
        all_items.extend(cred)
        print(f"  C-ReD: {len(cred)} 篇")

    # 过滤短文本
    all_items = [d for d in all_items if count_chinese(d.get('text', '')) >= 100]
    print(f"  有效 (≥100字): {len(all_items)} 篇\n")

    # 2. Phase 1: 扫描
    print(f"{'─' * 70}")
    print("  Phase 1: 全量诊断 (原文)")
    print(f"{'─' * 70}")

    scored = []
    for i, item in enumerate(all_items):
        text = item['text']
        chars = count_chinese(text)
        try:
            diag = diagnose(text)
            route = route_strategy_from_dims(diag['dims'])
        except Exception as e:
            print(f"  [{i+1}] 诊断失败: {e}")
            continue
        scored.append({
            'id': i,
            'text': text,
            'source': item.get('source', '?'),
            'chars': chars,
            'diag_orig': diag,
            'route': route,
        })
        top3 = sorted(diag['dims'].items(), key=lambda x: -x[1])[:3]
        top3_s = ', '.join(f'{DIM_LABELS_CN.get(d,d)}={s:.0f}' for d, s in top3)
        print(f"  [{i+1}/{len(all_items)}] {chars:5d}字 | AI={diag['total_score']:.0f} | {top3_s}")
    print(f"\n  诊断完成: {len(scored)} 篇\n")

    # 3. Phase 2: 执行改写（带缓存支持）
    print(f"{'─' * 70}")
    print("  Phase 2: Baseline & Adaptive 改写 (带缓存)")
    print(f"{'─' * 70}")

    # 尝试加载缓存
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            cached_ids = {item['id'] for item in cache_data}
            print(f"  发现缓存: {len(cached_ids)} 篇已完成")
        except Exception:
            cached_ids = set()
            cache_data = []
    else:
        cached_ids = set()
        cache_data = []

    for idx, s in enumerate(scored):
        if s['id'] in cached_ids:
            # 从缓存恢复
            cached = [c for c in cache_data if c['id'] == s['id']][0]
            for k in ['baseline', 'bl_score', 'bl_dims', 'bl_diag',
                      'adaptive', 'ad_score', 'ad_dims', 'ad_diag']:
                s[k] = cached.get(k)
            print(f"  [{idx+1}/{len(scored)}] ID={s['id']} ({s['chars']}字) — 从缓存恢复")
            continue

        text = s['text']
        print(f"  [{idx+1}/{len(scored)}] ID={s['id']} ({s['chars']}字)")

        # Baseline
        t0 = time.time()
        try:
            bl_r, bl_err = run_humanize(text, BASELINE_DIR, adaptive=False, seed=N_SEED)
        except Exception as e:
            bl_r, bl_err = None, str(e)
        t_bl = time.time() - t0
        if bl_r:
            try:
                diag_bl = diagnose(bl_r)
            except Exception:
                diag_bl = {'total_score': None, 'dims': {}}
            s['baseline'] = bl_r
            s['bl_score'] = diag_bl['total_score']
            s['bl_dims'] = diag_bl['dims']
            s['bl_diag'] = diag_bl
            bl_ai_str = f"AI={diag_bl['total_score']:.0f}" if diag_bl['total_score'] is not None else 'diag_err'
            print(f"    Baseline: ✓ ({t_bl:.1f}s, {count_chinese(bl_r)}字, {bl_ai_str})")
        else:
            s['baseline'] = None
            s['bl_score'] = None
            s['bl_dims'] = {}
            s['bl_diag'] = None
            print(f"    Baseline: ✗ ({t_bl:.1f}s) {bl_err}")

        # Adaptive
        t0 = time.time()
        try:
            ad_r, ad_err = run_humanize(text, ADAPTIVE_DIR, adaptive=True, seed=N_SEED)
        except Exception as e:
            ad_r, ad_err = None, str(e)
        t_ad = time.time() - t0
        if ad_r:
            try:
                diag_ad = diagnose(ad_r)
            except Exception:
                diag_ad = {'total_score': None, 'dims': {}}
            s['adaptive'] = ad_r
            s['ad_score'] = diag_ad['total_score']
            s['ad_dims'] = diag_ad['dims']
            s['ad_diag'] = diag_ad
            ad_ai_str = f"AI={diag_ad['total_score']:.0f}" if diag_ad['total_score'] is not None else 'diag_err'
            print(f"    Adaptive: ✓ ({t_ad:.1f}s, {count_chinese(ad_r)}字, {ad_ai_str})")
        else:
            s['adaptive'] = None
            s['ad_score'] = None
            s['ad_dims'] = {}
            s['ad_diag'] = None
            print(f"    Adaptive: ✗ ({t_ad:.1f}s) {ad_err}")

        # 保存缓存
        try:
            cache_entry = {k: s.get(k) for k in ['id', 'baseline', 'bl_score', 'bl_dims', 'bl_diag',
                                                   'adaptive', 'ad_score', 'ad_dims', 'ad_diag']}
            # 确保 JSON 可序列化
            cache_data = [c for c in cache_data if c['id'] != s['id']]
            cache_data.append(cache_entry)
            with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, default=str)
        except Exception as e:
            print(f"    [缓存写入失败: {e}]")

    # 4. Phase 3: 挑选 showcase
    print(f"\n{'─' * 70}")
    print("  Phase 3: 智能挑选")
    print(f"{'─' * 70}")
    showcases = pick_showcases(scored, n=N_SHOWCASE)
    for s in showcases:
        src_ai = s['diag_orig']['total_score']
        bl_ai = s.get('bl_score', src_ai)
        ad_ai = s.get('ad_score', src_ai)
        print(f"  ID={s['id']} | {s['source']} | {s['chars']}字 | 原文={src_ai:.0f} BL={bl_ai:.0f} AD={ad_ai:.0f}")

    # 5. Phase 4: Fast-DetectGPT 评分
    print(f"\n{'─' * 70}")
    print("  Phase 4: Fast-DetectGPT (Qwen2.5-0.5B) 评分")
    print(f"{'─' * 70}")

    for idx, s in enumerate(showcases):
        print(f"  [{idx+1}/{len(showcases)}] ID={s['id']} ...", end=' ', flush=True)
        # 原文
        oc, op = score_fd_gpt(s['text'], model='qwen')
        s['fdgpt_orig'] = (oc, op)
        print(f'原文={oc}', end=' ', flush=True)
        # Baseline
        if s.get('baseline'):
            bc, bp = score_fd_gpt(s['baseline'], model='qwen')
            s['fdgpt_bl'] = (bc, bp)
            print(f'BL={bc}', end=' ', flush=True)
        else:
            s['fdgpt_bl'] = (None, None)
        # Adaptive
        if s.get('adaptive'):
            ac_, ap_ = score_fd_gpt(s['adaptive'], model='qwen')
            s['fdgpt_ad'] = (ac_, ap_)
            print(f'AD={ac_}', end=' ')
        else:
            s['fdgpt_ad'] = (None, None)
        print()

    # 6. Phase 5: 标签
    print(f"\n{'─' * 70}")
    print("  Phase 5: 生成报告 + 柱状图")
    print(f"{'─' * 70}")

    # 为 showcase 生成标签
    showcase_labels = {
        0: ('短语替换高效型：机械连接词主导', '机械连接词'),
        1: ('同义词替换高效型：AI高频词突出', 'AI高频词'),
        2: ('噪声注入高效型：情感平淡文本', '情感平淡'),
        3: ('深层重构高效型：三段式结构', '三段式结构'),
        4: ('综合型：高分长文本', '综合高分'),
        5: ('保守型：低分文本', '低分保守'),
    }
    for i, s in enumerate(showcases):
        src_ai = s['diag_orig']['total_score']
        delta_bl = src_ai - s.get('bl_score', src_ai)
        delta_ad = src_ai - s.get('ad_score', src_ai)

        norm = {}
        for d, v in s['diag_orig']['dims'].items():
            mx = DIM_MAX.get(d, 10)
            norm[d] = v / mx if mx > 0 else 0
        top_dim = max(norm, key=norm.get) if norm else ''
        top_val = norm.get(top_dim, 0)

        # 自动生成标签
        if top_val > 0.8:
            dim_cn = DIM_LABELS_CN.get(top_dim, top_dim)
            if delta_ad > delta_bl + 5:
                cat = f'{dim_cn}主导 (AD胜出+{delta_ad-delta_bl:.0f})'
            elif delta_bl > delta_ad + 5:
                cat = f'{dim_cn}主导 (BL胜出)'
            else:
                cat = f'{dim_cn}主导 (持平)'
            short = dim_cn[:6]
        elif src_ai >= 80:
            cat = '综合高分文本 (AD充分)'
            short = '综合高分'
        elif src_ai <= 30:
            cat = '低分保守文本 (已近人写)'
            short = '低分保守'
        else:
            cat = f'中等文本 (AD Δ={delta_ad:+.0f})'
            short = f'中等'
        s['cat_label'] = cat
        s['cat_label_short'] = short

    # 生成报告
    report_md = generate_report(showcases, OUTPUT_DIR)
    report_path = os.path.join(OUTPUT_DIR, 'showcase_v2_report.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_md)
    print(f"\n  报告已写入: {report_path}")

    # 7. 终端摘要
    print(f"\n{'═' * 70}")
    print(f"  摘要")
    print(f"{'═' * 70}")
    print(f"{'#':<5} {'类别':<30} {'字数':<6} {'原文':<6} {'BL':<6} {'AD':<6} {'FD-原文':<8} {'FD-BL':<8} {'FD-AD':<8}")
    print('-' * 85)
    for idx, s in enumerate(showcases, 1):
        src_ai = s['diag_orig']['total_score']
        bl_ai = s.get('bl_score', src_ai)
        ad_ai = s.get('ad_score', src_ai)
        fd_o = s.get('fdgpt_orig', (None, None))[0] or 0
        fd_b = s.get('fdgpt_bl', (None, None))[0] or 0
        fd_a = s.get('fdgpt_ad', (None, None))[0] or 0
        print(f'{idx:<5} {s["cat_label"][:28]:<30} {s["chars"]:<6} '
              f'{src_ai:<6.0f} {bl_ai:<6.0f} {ad_ai:<6.0f} '
              f'{fd_o:<8.4f} {fd_b:<8.4f} {fd_a:<8.4f}')

    print(f"\n  所有输出: {OUTPUT_DIR}/")
    print(f"  ├── showcase_v2_report.md")
    print(f"  ├── summary_all_scores.png")
    for i in range(1, len(showcases) + 1):
        print(f"  ├── case{i}_score.png")
        print(f"  ├── case{i}_dims.png")
        print(f"  ├── case{i}_deltas.png")
        print(f"  └── case{i}_fdgpt.png")


if __name__ == '__main__':
    main()

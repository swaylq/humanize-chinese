# Humanize Chinese for Claude Code (v5.0)

## Installation

```bash
# Clone the repo
git clone https://github.com/swaylq/humanize-chinese.git

# Copy slash commands to your project
cp -r humanize-chinese/claude-code/*.md YOUR_PROJECT/.claude/commands/
```

Or install individual commands:

```bash
mkdir -p .claude/commands
cp humanize-chinese/claude-code/detect.md .claude/commands/
cp humanize-chinese/claude-code/humanize.md .claude/commands/
cp humanize-chinese/claude-code/academic.md .claude/commands/
cp humanize-chinese/claude-code/style.md .claude/commands/
```

## Commands

| Command | Description |
|---------|-------------|
| `/detect [text]` | Detect AI patterns, 0-100 fused score (rule × 0.2 + LR × 0.8). Scene-aware: general / academic / novel / auto |
| `/humanize [text]` | Rewrite (default best-of-10 取最低 LR, scene-aware 三路 LR) |
| `/academic [text]` | Academic paper AIGC reduction. Scene-aware academic LR + 双评分 (CNKI/VIP/Wanfang) |
| `/style [style] [text]` | Transform to style (8 styles incl. novel). Auto-humanizes first. |

## What's new in v5.0

- **Scene-aware LR fusion** (`general` / `academic` / `longform` 三路 LR，`--scene auto` 按 ≥1500 字切换)
- **HC3 fused 准确率 95%** (vs v3.0 的 73%) on HC3-Chinese 100-sample regression
- **Long-form support**: paragraph length CV / 段内句长 CV / 跨段 trigram 重复 三新信号 + 反制改写
- **`--style novel`** 长篇叙事专属 (剔除 AI prompt artifact + markdown headers + dialogue 保护)
- **`--best-of-n N`** humanize N 次取最低 LR (默认 10)
- **165 replacement patterns** (vs v3 122) + CiLin 同义词词林 38873 with collision blacklist (49 entries)
- **Hero 降幅**: 学术 100→35 (-65) / 通用 100→35 (-65) / 小红书 100→41 (-59) / 长篇博客 96→41 (-55) / 工作汇报 96→13 (-83)
- **Unified CLI**: `./humanize {detect,rewrite,academic,style,compare}`

## Note

Make sure the `scripts/` directory from humanize-chinese is accessible. The commands reference `$SKILL_DIR/scripts/` or `$SKILL_DIR/humanize` (the unified CLI shim) — if using as a standalone Claude Code project, update paths to point to your local copy.

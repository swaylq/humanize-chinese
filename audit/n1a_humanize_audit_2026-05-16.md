# N-1a humanize 输出 audit (2026-05-16, HEAD 1c9d810 之后)

跑 4 hero（PYTHONHASHSEED=0 seed=42 bn=20）找 broken substitution / awkward 搭配。

## 本 cycle 修复

- `_CILIN_BLACKLIST` += `'家常'`：通常 cilin alt，输出 "数据家常用于调试和优化代码性能"（sample_long_blog.txt）像 1 字 typo。修后变 "数据一般用于"，读起自然。

## 已识别但未修（留后续 cycle）

按严重度排序：

1. **`本身就，是一类核心竞争力`** (sample_social.txt, "实话说，这种取舍能力本身就，是一类核心竞争力")
   - "本身就，" 多余逗号 + "一类" 不合中文（应 "是一种" / "是一项"）
   - 来源：可能是 inject_noise 误插逗号 + WORD_SYNONYMS 把 "一种" → "一类"
   - 修法：搜 humanize_cn 哪里产 "本身就，" 或 "一类核心"

2. **`数据相关解读揭示`** (sample_long_blog.txt, "数据相关解读揭示，改进后的版本显著提升了...")
   - 原文 "数据分析揭示"
   - WORD_SYNONYMS['分析'] = ['剖析', '解读']，所以是 "数据分析" → "数据 + ? + 解读" 多了 "相关"
   - 修法：找谁注入 "相关" 前缀 + 看 phrase pattern

3. **`辨析数据的能力`** (sample_long_blog.txt, "产品经理一定要具备辨析数据的能力")
   - 原文 "分析数据"
   - WORD_SYNONYMS['分析'] cilin alts 含 '辨析'（"分析"→cilin 给的 alts），但 "辨析数据" 在中文搭配上 awkward（"辨析" 适合论点/概念，"分析" 才适合数据）
   - 修法：'辨析' 入 _CILIN_BLACKLIST 或 contextual guard（"辨析" + "数据/数字" 视为 broken）

4. ~~**`保有广阔的发展前景`** (sample_academic.txt, "深入研究该领域，保有广阔的发展前景")~~ **fixed 2026-05-16 cycle (heartbeat) — 加 '保有' to _CILIN_BLACKLIST，输出变 "具备广阔的发展前景"**

5. ~~**`融入大数据剖析`** (sample_academic.txt / general.txt)~~ **fixed 2026-05-16 cycle (heartbeat 2) — patterns_cn.json "深度融合" alts ["结合", "融入"] → ["结合", "整合"]，4 hero 全部从 "融入X" → "整合X"。剖析问题（#6）单独处理。**

6. **`给出 X 体验/解决方案`** (sample_general.txt, social.txt)
   - "提供" → "给出"，但 "给出体验" / "给出方案" 不像中文自然搭配
   - 修法：'给出' 限定 collocation（适合 "给出答案/建议"，不适合 "给出体验"）

7. **`竞争剖析`** (sample_long_blog.txt, "市场定位、竞争剖析等")
   - "竞争分析" → "竞争剖析"
   - 中文 "剖析" 偏深入展开，"竞争" 抽象主题，搭配略硬
   - 修法：'剖析' contextual guard（与 "市场/竞争/数据" 抽象主语搭配视为 broken），或单独看 WORD_SYNONYMS['分析'] 中 '剖析' 的使用频率

## 验证

- test_regression.py 9/9 OK
- HC3 N=30: correct 86.7%, gap 50.9, 0 grammar defects（已在前一 commit 验证）
- 4 hero floor 全过

## 下一 cycle 建议

按上面 #1 → #7 顺序排，每 cycle 修 1-2 个。修法多为 _CILIN_BLACKLIST 增条或 contextual guard，单 commit 风险低。

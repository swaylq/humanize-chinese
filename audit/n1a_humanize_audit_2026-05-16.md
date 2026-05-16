# N-1a humanize 输出 audit (2026-05-16, HEAD 1c9d810 之后)

跑 4 hero（PYTHONHASHSEED=0 seed=42 bn=20）找 broken substitution / awkward 搭配。

## 本 cycle 修复

- `_CILIN_BLACKLIST` += `'家常'`：通常 cilin alt，输出 "数据家常用于调试和优化代码性能"（sample_long_blog.txt）像 1 字 typo。修后变 "数据一般用于"，读起自然。

## 已识别但未修（留后续 cycle）

按严重度排序：

1. ~~**`本身就，是一类核心竞争力`** (sample_social.txt, "实话说，这种取舍能力本身就，是一类核心竞争力")~~ **fixed 2026-05-16 cycle (heartbeat 5) — restructure_cn.py:946 boost_comma_density 加 '就' 到 prefix-tail2 skip set。"X 就是 Y" 是中文 compound copula，"就" 后插逗号读破句。post-fix: "本身就是一类核心竞争力"。"一类" 替换 "一种" 略宽但留作可接受语义偏移。**

2. ~~**`数据相关解读揭示`** (sample_long_blog.txt, "数据相关解读揭示，改进后的版本显著提升了...")~~ **fixed 2026-05-16 cycle (heartbeat 4) — 改 patterns_cn.json 的 "分析显示" alts: 删 "相关分析揭示" 改为 "分析揭示"。原 source 是 "数据分析显示" → "数据相关分析揭示" (因 prefix "数据" 留作 leftover)。post-fix long_blog "数据解读反映，..." 读起自然。**

3. ~~**`辨析数据的能力`** (sample_long_blog.txt, "产品经理一定要具备辨析数据的能力")~~ **fixed 2026-05-16 cycle (heartbeat 3) — 加 '辨析' to _CILIN_BLACKLIST。fallback '浅析' 在 heartbeat 6 通过 WORD_SYNONYMS['分析'] 改 ['解读', '解析'] 一并解决。post-fix 输出 "具备解读数据的能力" 自然。**

4. ~~**`保有广阔的发展前景`** (sample_academic.txt, "深入研究该领域，保有广阔的发展前景")~~ **fixed 2026-05-16 cycle (heartbeat) — 加 '保有' to _CILIN_BLACKLIST，输出变 "具备广阔的发展前景"**

5. ~~**`融入大数据剖析`** (sample_academic.txt / general.txt)~~ **fixed 2026-05-16 cycle (heartbeat 2) — patterns_cn.json "深度融合" alts ["结合", "融入"] → ["结合", "整合"]，4 hero 全部从 "融入X" → "整合X"。剖析问题（#6）单独处理。**

6. ~~**`给出 X 体验/解决方案`** (sample_general.txt, social.txt)~~ **fixed 2026-05-16 cycle (heartbeat 7) — WORD_SYNONYMS['提供'] 从 ['给出', '给予'] 改 ['给予']。'给出' 适合具象答案/建议，不适合 体验/方案/支撑 这类抽象/复合对象。'给予' 更 versatile：4 hero 全部 "给出X" → "给予X" 读自然。**

7. ~~**`竞争剖析`** (sample_long_blog.txt, "市场定位、竞争剖析等")~~ **fixed 2026-05-16 cycle (heartbeat 6) — WORD_SYNONYMS['分析'] 从 ['剖析', '解读'] 改为 ['解读', '解析']。'剖析' 偏深入展开不适合 "竞争/大数据/市场分析" 这类抽象 collocations。同 swap 一并清掉 entry #3 fallback '浅析' 问题：post-fix 大数据剖析→大数据解读 / 竞争剖析→竞争解读 / 浅析数据→解读数据 / 数据解读反映→数据解析反映。**

## 验证

- test_regression.py 9/9 OK
- HC3 N=30: correct 86.7%, gap 50.9, 0 grammar defects（已在前一 commit 验证）
- 4 hero floor 全过

## 下一 cycle 建议

按上面 #1 → #7 顺序排，每 cycle 修 1-2 个。修法多为 _CILIN_BLACKLIST 增条或 contextual guard，单 commit 风险低。

## Round 2 audit (heartbeat 8, post 9 commits)

跑全 hero 第二轮，找新候选：

1. ~~**`反应了使用体验`** (sample_long_blog.txt, "这直接反应了他们的使用体验")~~ **fixed 2026-05-16 cycle (heartbeat 8) — 加 '反应' to _CILIN_BLACKLIST。CiLin 双向 group 把 影响↔反应 列为同义，但 影响=effect/cause 与 反应=response/reaction 语义反向，且易混淆于 反映(reflect)。post-fix 输出 "这直接影响了他们的使用体验" 恢复原意。**
2. ~~**`在过去的一年里。估摸着，`** (sample_long_blog.txt)~~ **fixed 2026-05-16 cycle (heartbeat 9) — bisect 定位 randomize_sentence_lengths Strategy B truncation at first comma。原 "在过去的一年里，我经历了..." 在 comma 切，产 "在过去的一年里。" + 后续 inject_noise 塞 "估摸着，" filler。新增 _ZAI_LOCATIVE_RE guard：在 + {1,20}字 + 里/中/里面/期间/前后/之前/之后/之间/之上/之下/之外 不允许 truncate。**
3. ~~**`案例：在一个项目中。我们需要开发...`** (sample_long_blog.txt)~~ **fixed 同一 commit — _ZAI_LOCATIVE_RE 同时 cover "案例：在一个项目中" (在 不在 first_part 开头时 regex 也 catch)。原 "案例：在一个项目中，我们需要..." 保留 comma。**
4. ~~**`一类核心竞争力`** (sample_social.txt) — heartbeat 5 修 comma 后 "本身就是一类" 仍然，"一类" 替换 "一种" 语义偏移~~ **fixed 2026-05-16 cycle (heartbeat 10) — patterns_cn.json 删 "是一种" → ["是一类"] 单 alt 替换（top-level + academic_patterns 各一处）。"一种" (kind of) 与 "一类" (category of) 语义不同；"是一种" 留作 source 不替换比硬变 "是一类" 通顺。post-fix social "本身就是一种核心竞争力"。**
5. **`使用价值 / 应用价值`** (sample_general.txt) — "应用价值" 替成 "使用价值"，意思偏 utilitarian，原 academic register 偏 conceptual。低优先级。

Round 2 主修 #1（最严重 typo-class），#2-#3 留下次（结构性 split 问题，需要 bisect 找 transform）。

## Round 3 audit (heartbeat 11, 2026-05-17)

post 12 commits 跑 long_blog seed=42 跳现 2 新严重 bug：

1. ~~**`并发现暧昧的问题`** (sample_long_blog.txt)~~ **fixed 2026-05-17 cycle (heartbeat 11) — _CILIN_SOURCE_BLACKLIST 加 '潜在'。cilin 把 潜在 (latent/potential) 误归 hidden/secret 族 (地下/心腹/暗昧/暧昧/机密/机要)，所有 alts 都改义。Block source。post-fix 恢复 "发现潜在的问题"。**
2. ~~**`这一年不停是职业角色的转变`** (sample_long_blog.txt)~~ **fixed 2026-05-17 cycle (heartbeat 11+12) — 初步 _CILIN_SOURCE_BLACKLIST 加 '不止' (commit f8a38da)，cycle 12 refine：改为 _CILIN_BLACKLIST 加 '不停' alt（保留 '不止' 作 source，cilin 仍可 vary 不止→不仅/不仅仅）。long_blog 45→44 (margin to floor 46 改善 +1)。**

Hero 验证：long_blog 38→45（窄过 floor 46，margin 1）；其他 hero 持平/微改善。HC3 N=30 持平 86.7%/50.9/0 grammar。

Round 3 剩 candidates（低优先）：
3. `处理这一难题` (sample_long_blog) — "处理" 替 "应对/面对/面临"，semantic-OK but register-shift；保留

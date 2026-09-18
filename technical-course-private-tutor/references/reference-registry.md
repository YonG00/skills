# Reference Registry

Skill 的外部知识地图。**Skill 保存"如何思考"，Registry 保存"去哪里重新找到证据和原始知识"。**

原则：不把外部资料全文复制进 Skill，只保留**找到原始信息的路径**。需要准确细节时优先重新访问原文——摘要用于快速定位，原文用于最终确认。

## 字段定义

| 字段 | 含义 |
|---|---|
| `title` | 来源名称 |
| `url` | 原始链接 |
| `type` | blog / paper / docs / github / pdf / data |
| `topic` | 涉及主题 |
| `purpose` | 为什么保存 |
| `supports` | 支持哪些规则或判断 |
| `retrieved_at` | 最近访问时间 |
| `notes` | 简短说明 |

## 规范来源（本 skill 的上游）

**v3 是 2.0.0 的主线**（`SKILL.md` 的章节骨架与它的九节大纲对齐）；其余四篇的注意点降为其下的子节。

| title | url | type | topic | purpose | supports | retrieved_at |
|---|---|---|---|---|---|---|
| 技术课程私人导师 v2 | https://www.cnblogs.com/yong2333/articles/22986095 | blog | teaching | 基础教师能力、课程主线、认知依赖、逐节教学、数学/代码/例子讲解、节奏控制、理解检查 | SKILL.md §0、§1.3–§1.5、§四、§5.1、§六、§7.2 | 2026-09-18 |
| **技术课程私人导师 v3（主线）** | https://www.cnblogs.com/yong2333/articles/22998999 | blog | teaching | 单节信息边界、跨节抢跑禁令、下一节钩子、来源与时间规则、Reference Registry、执行前快速检查 | **`SKILL.md` 章节骨架**；§1.1、§二、§三、§四、§5.1、§八、§九、§7.1 | 2026-09-18 |
| 技术课程私人导师 v3.1 | https://www.cnblogs.com/yong2333/articles/23002078 | blog | teaching | 单节聚焦收紧为"一个认知问题"、先看见区别再给概念、对照教学、反板书腔、问题推动、教学压缩检查、反馈触发的即时校正 | SKILL.md §1.3、§1.5、§5.2–§5.3、§7.4 | 2026-09-18 |
| 技术课程私人导师 v3.2 | https://www.cnblogs.com/yong2333/articles/23016300 | blog | teaching | 新技术第一次出现时的历史锚点规则：什么时候、谁、为什么出现 | SKILL.md §三、references/history-anchor-examples.md | 2026-09-18 |
| Skill 更新、博客化与外部知识资产原则 | https://www.cnblogs.com/yong2333/articles/22998468 | blog | skill-maintenance | Skill 更新方法、从反馈抽象通用规则、旧规则保留、冲突处理、Reference Registry、外部知识优先保留 URL | SKILL.md §八、§九、references/skill-maintenance.md | 2026-09-18 |

## 测试材料（fixture）

用于 `references/section-splitting.md` 的 worked example 与回归验证。**按 commit 钉住，不 vendor 进仓库**——这既是可复现性要求，也是本仓库"知识资产只存路径"原则的应用。

| title | url | type | topic | purpose | supports | retrieved_at |
|---|---|---|---|---|---|---|
| Stanford CS336 Lecture 15（After Pretraining / Mid-Post Training） | https://github.com/flyfei-cmd/video-to-chapter-book/blob/14a67918e3a4e6e98d2b346b29518fe12e8d9cd7/chapter-books/stanford-cs336/lecture-15.md | blog | teaching-fixture | 拆节方法的 worked example 与回归材料。原始规模 45,363 字符 / 68 个 `##` 节点（65 个内容节点）；公认产出为 22 节 | `references/section-splitting.md` §5 | 2026-09-18 |

**钉住的版本**：commit `14a67918e3a4e6e98d2b346b29518fe12e8d9cd7`（经 `raw.githubusercontent.com` 实测可复现：HTTP 200，45,363 字符，68 个 `##` 节点）。**不要用 `main` 分支**，否则材料漂移会使回归结果不可比。

## 待补充：高价值一手来源

以下类别可在后续任务中逐步加入（不要预填未经核实的内容）：

- `type: paper` — 课程中首次出现的关键论文原始页面（用于 §3.5 的事实核实）；
- `type: docs` — 官方项目文档、框架文档；
- `type: data` — 数据集官方页面与版本说明；
- `type: github` — 官方仓库；
- `type: blog` — 与教学方法论相关的其他参考。

加入时请同时填写 `supports`，说明它支持哪条规则或判断；否则它只是书签，不是知识资产。

## 维护约定

1. 新增条目前先确认它支持**具体的规则或判断**。
2. 涉及年份、作者、机构、版本、API、政策等易变事实时，使用前必须重新访问原始链接。
3. 若原始链接失效，优先寻找迁移后的官方地址，而不是删除条目；无法找回时标注 `notes: link-dead`。
4. Registry 的检索入口是 SKILL.md §3.5（历史锚点事实核实）、§八（知识资产与外部来源）和 `references/section-splitting.md` §5（测试材料）。

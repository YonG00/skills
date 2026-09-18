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

| title | url | type | topic | purpose | supports | retrieved_at |
|---|---|---|---|---|---|---|
| 技术课程私人导师 v2 | https://www.cnblogs.com/yong2333/articles/22986095 | blog | teaching | 基础教师能力、课程主线、认知依赖、逐节教学、数学/代码/例子讲解、节奏控制、理解检查 | SKILL.md §0–§9、§11 | 2026-09-18 |
| 技术课程私人导师 v3 | https://www.cnblogs.com/yong2333/articles/22998999 | blog | teaching | 单节信息边界、跨节抢跑禁令、下一节钩子、来源与时间规则、Reference Registry、执行前快速检查 | SKILL.md §4、§7、§11、§12 | 2026-09-18 |
| 技术课程私人导师 v3.1 | https://www.cnblogs.com/yong2333/articles/23002078 | blog | teaching | 单节聚焦收紧为"一个认知问题"、先看见区别再给概念、对照教学、反板书腔、问题推动、教学压缩检查、反馈触发的即时校正 | SKILL.md §2、§5、§10、§11.1 | 2026-09-18 |
| 技术课程私人导师 v3.2 | https://www.cnblogs.com/yong2333/articles/23016300 | blog | teaching | 新技术第一次出现时的历史锚点规则：什么时候、谁、为什么出现 | SKILL.md §7 | 2026-09-18 |
| Skill 更新、博客化与外部知识资产原则 | https://www.cnblogs.com/yong2333/articles/22998468 | blog | skill-maintenance | Skill 更新方法、从反馈抽象通用规则、旧规则保留、冲突处理、Reference Registry、外部知识优先保留 URL | SKILL.md §13、references/skill-maintenance.md | 2026-09-18 |

## 待补充：高价值一手来源

以下类别可在后续任务中逐步加入（不要预填未经核实的内容）：

- `type: paper` — 课程中首次出现的关键论文原始页面（用于 §7.5 的事实核实）；
- `type: docs` — 官方项目文档、框架文档；
- `type: data` — 数据集官方页面与版本说明；
- `type: github` — 官方仓库；
- `type: blog` — 与教学方法论相关的其他参考。

加入时请同时填写 `supports`，说明它支持哪条规则或判断；否则它只是书签，不是知识资产。

## 维护约定

1. 新增条目前先确认它支持**具体的规则或判断**。
2. 涉及年份、作者、机构、版本、API、政策等易变事实时，使用前必须重新访问原始链接。
3. 若原始链接失效，优先寻找迁移后的官方地址，而不是删除条目；无法找回时标注 `notes: link-dead`。
4. Registry 的检索入口是 SKILL.md §7.5（历史锚点事实核实）和 §12（知识资产与外部来源）。

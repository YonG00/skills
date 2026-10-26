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
| **Conversation Synthesis Skill v3（主线）** | https://www.cnblogs.com/yong2333/articles/22980128 | blog | writing | 19 个部分、59 条规则：问题链、用户真实性、信息资产、证据与来源、推进思考、结构、风格、结尾、修订、质量审计、自更新 | **`SKILL.md` 章节骨架**；§一～§十三；`references/evidence.md`、`argumentation.md`、`structure-and-style.md`、`quality-audit.md`、`skill-maintenance.md` | 2026-09-18 |
| Conversation Synthesis Skill（基础版） | https://www.cnblogs.com/yong2333/articles/22933656 | blog | writing | 前身版本：17 条编号规则 + 默认流程 + 最终标准 | `references/base-version.md`（存档，用于核对规则无丢失） | 2026-09-18 |
| Skill 更新、博客化与外部知识资产原则 | https://www.cnblogs.com/yong2333/articles/22998468 | blog | skill-maintenance | 同源的方法论通用版：规则资产 vs 知识资产、外部来源只存链接、Reference Registry、知识循环 | 本文件的字段设计与 `SKILL.md` §十二 | 2026-09-18 |

> **同源文档提示**：本 skill 的 `references/skill-maintenance.md` 与 `technical-course-private-tutor/references/skill-maintenance.md` 出自同一套方法论的两个版本。前者是**规则治理**视角（一条规则该不该进、怎么合并、谁来决定），后者额外包含**知识资产**视角（知识放在哪里、博客化输出、知识循环）。差异表见本 skill 的 `references/skill-maintenance.md` 末尾。

## 待补充：高价值一手来源

对话合成类任务会频繁引用外部事实（法律、政策、统计、论文）。这些**属于具体文章的知识资产，不属于本 skill**——它们应该写进那篇文章的资产表，而不是仓库。

若某个来源被反复用于**规则层面**（例如一份权威的写作规范、一份官方的事实核查指南），才值得加入下表：

| 类型 | 说明 |
|---|---|
| `type: docs` | 官方写作/编审规范、事实核查指南 |
| `type: paper` | 关于论证、证据强度、因果推断的方法论论文 |
| `type: blog` | 与本文档方法论相关的其他参考 |

加入时请同时填写 `supports`，说明它支持哪条规则或判断；否则它只是书签，不是知识资产。

## 维护约定

1. 新增条目前先确认它支持**具体的规则或判断**。
2. 涉及年份、作者、机构、版本、政策等易变事实时，使用前必须重新访问原始链接。
3. 若原始链接失效，优先寻找迁移后的官方地址，而不是删除条目；无法找回时标注 `notes: link-dead`。
4. 文章级别的资料（案例、数据、论文）**不进本文件**，它们属于那篇文章的信息资产清单（见 `references/conversation-to-outline.md` Stage E）。

## 相关文件

| 文件 | 作用 |
|---|---|
| `../SKILL.md` | 可执行规范（主文件） |
| `conversation-to-outline.md` | ★ 本地原创：从对话记录到文章骨架的七阶段方法 |
| `evidence.md` | 第 23–28 条：证据覆盖、来源优先级、因果强度 |
| `argumentation.md` | 第 29–35 条：推进思考的分析清单 |
| `structure-and-style.md` | 第 36–50 条：结构、风格、排版、结尾 |
| `quality-audit.md` | 第 54–59 条 + 默认工作流 |
| `skill-maintenance.md` | 第 1–12 条 + 第十三～十七、十九部分 |
| `base-version.md` | 基础版存档（核对规则无丢失） |

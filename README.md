# Skills

Agent Skills 集合。

## 工作区存放约定

当前 Git 只管理技能及相关文档、提示词和维护脚本。

- `资料/YYYY-MM-DD_HHMMSS_内容主题/`：动画、视频、素材、制作源码和运行环境。使用北京时间命名，整个目录不纳入 Git。
- `仓库/`：后续新增的独立仓库和非技能代码项目。名称、来源和本地路径记入 `仓库/仓库索引.md`，不纳入当前 Git；各仓库可独立管理版本。
- `技能库/`：个人维护的技能源码，纳入当前 Git。用户技能目录中的安装副本与这里的源码分别管理；作品留在 `资料/`。

具体执行约定见 [AGENTS.md](AGENTS.md)。

| Skill | 说明 |
|---|---|
| [`qwen3-tts-mlx/`](技能库/qwen3-tts-mlx/) | 获准后整理口播稿，使用保存音色生成本地纯人声；支持长稿续跑、内容核对及 motion-video 交接。 |
| [`technical-course-private-tutor/`](技能库/technical-course-private-tutor/) | 技术课程私人导师：把 lecture notes / PDF / 视频转录稿 / GitHub chapter 重建为可逐节学习的连续知识路径。**先把材料拆成主干路线图**（每节一个疑问句核心问题、声明"本节不做什么"），再一节一节讲；每个新概念首次出现时给 1–3 句历史锚点。 |
| [`conversation-synthesis/`](技能库/conversation-synthesis/) | 对话合成：把长期对话整理成**真正被思考过**的文章 / 研究笔记 / 分析稿。先还原**问题链与判断变化**再决定章节（不按聊天时间顺序）；保护用户真实表达；信息资产先回收再筛选并做**守恒核对**；可核验事实必须有来源；交付前跑六项审计。 |
| [`cnblogs-publisher/`](技能库/cnblogs-publisher/) | 博客园文章检查、预览、明确确认后发布及合集归属核验，含防重复提交的配套脚本。 |
| [`self-reflection-journal/`](技能库/self-reflection-journal/) | 个人思考成文：将录音转写、随笔或对话按方向归并成少量完整文章，保留本人语言、经历与判断变化；默认直接给正文。 |
| [`lingbot-auto-learning-logic/`](技能库/lingbot-auto-learning-logic/) | LingBot-VLA-v2 自动学习（AL）**逻辑地图**：任务/回合/帧模型、四个评测 split、三把尺子与判定口径、状态机与门控、unit 与 hook、两套缓存、启动器、观测手段，以及**已确认的逻辑冲突与踩坑台账**。含"存档策略四象限"（哪格必崩）、"attempt/reopen 的真实语义"（为什么复习机会只有一次）与"任务周期成本模型"（覆盖 50 个任务要多久）。规则全部来自真机事故与实测数字。 |
| [`lingbot-code-changes/`](技能库/lingbot-code-changes/) | 分四阶段的**受控代码改动流程**（讨论 → 清单 → 逐条执行 → 提交）：未经点头不动手、不扩权、报错先取证。核心遗留物是**改动台账**（§1 待验证 / §2 已验证 / §3 遗留）与「**改动本意」四问**（不变量 / 出错症状 / 快速回滚 / 验证入口）；并含**组合类改动的验证矩阵**（凡"开关 × 开关"必须四象限逐格给证据 —— 这条来自一次真实事故）。 |

其他：

| 文件 | 说明 |
|---|---|
| [`scripts/check.py`](scripts/check.py) | **仓库自检**。`python3 scripts/check.py` 一次跑三类检查：① CJK 加粗渲染缺陷；② 内部链接；③ **提示词与 skill 的同步**（关键词 + 目录完整性）。改完任何东西推之前跑一下。 |
| [`prompts/technical-course-private-tutor.md`](prompts/technical-course-private-tutor.md) | **聊天模式提示词**（对应 `technical-course-private-tutor`）。给没有文件系统（可能也没有联网）的纯聊天模型用。含方案 A（URL 版）/ 方案 B（自包含版）/ 三消息协议 / 与 `SKILL.md` 的同步清单。**用法**：开课时贴出，然后按「继续」逐节推进。 |
| [`prompts/conversation-synthesis.md`](prompts/conversation-synthesis.md) | **聊天模式提示词**（对应 `conversation-synthesis`）。**用法**：在一段**已经聊完的对话末尾**贴出，让模型把这段对话整理成文章。含 **6 阶段流水线**（脉络 → 标题子标题 → 初稿 → 润色 → 加链接 → 成稿）、停止契约、与 `SKILL.md` 的同步清单。 |
| [`prompts/self-reflection-journal.md`](prompts/self-reflection-journal.md) | 个人思考成文的聊天模式提示词：按方向归并文章，保留第一人称与未完成判断，不凑篇数、不默认生成文件。 |
| [`prompts/lingbot-code-changes.md`](prompts/lingbot-code-changes.md) | **聊天模式提示词**（对应 `lingbot-code-changes`）。**用法**：在要改代码的那次对话里贴出。含方案 A（有文件系统）/ 方案 B（纯聊天）两版，**4 阶段契约**（讨论 → 清单 → 逐条执行 → 收尾），以及"组合类改动的验证矩阵"与血泪提醒清单。 |
| [`prompts/lingbot-auto-learning-logic.md`](prompts/lingbot-auto-learning-logic.md) | **知识型提示词**（对应 `lingbot-auto-learning-logic`）。**注意**：它不是流程提示词，而是把"AL 系统逻辑要点"压缩成一段可贴进聊天的正文（状态机与机会数量 / 四个 split / 任务周期成本 / 存档四象限 / 三套步号 / 配置硬校验），让没有文件系统的模型也能准确回答 AL 问题。**能读文件时优先直接读 `SKILL.md`**。 |

每个 skill 目录自带 `SKILL.md`（执行形态）与 `README.md`（可阅读形态），可单独复制安装。

> ⚠️ `prompts/` 下的提示词是各自 `SKILL.md` 的**派生副本**。改完 skill 记得按它的「同步清单」检查提示词是否过期——**提示词过期不会报错，只会让模型悄悄按旧规则走**。

## 视频技能

- [motion-video-workflow](技能库/motion-video-workflow/)：音频转动效视频，已建立个人维护副本，后续改动在这里迭代。
- [dashi-animationstyle](技能库/dashi-animationstyle/)：多风格讲解动画，保留上游模板与许可。

技能清单及维护方式见 [技能库/README.md](技能库/README.md)。

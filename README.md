# Skills

Agent Skills 集合。

| Skill | 说明 |
|---|---|
| [`technical-course-private-tutor/`](technical-course-private-tutor/) | 技术课程私人导师：把 lecture notes / PDF / 视频转录稿 / GitHub chapter 重建为可逐节学习的连续知识路径。**先把材料拆成主干路线图**（每节一个疑问句核心问题、声明"本节不做什么"），再一节一节讲；每个新概念首次出现时给 1–3 句历史锚点。 |
| [`conversation-synthesis/`](conversation-synthesis/) | 对话合成：把长期对话整理成**真正被思考过**的文章 / 研究笔记 / 分析稿。先还原**问题链与判断变化**再决定章节（不按聊天时间顺序）；保护用户真实表达；信息资产先回收再筛选并做**守恒核对**；可核验事实必须有来源；交付前跑六项审计。 |
| [`zhihu-question-mining/`](zhihu-question-mining/) | 知乎提问挖掘：把**口述稿 / 录音转写 / 随笔笔记**整理成**可发布的知乎提问**。先切话题单元（**一个提问 = 一个核心矛盾**），再写一句话标题 + 问题描述；标题从**具体对象**切进去，描述**保留本人的第一人称口语风格**。规则全部提炼自一次真实的六轮退回记录。 |
| [`lingbot-auto-learning-logic/`](lingbot-auto-learning-logic/) | LingBot-VLA-v2 自动学习（AL）**逻辑地图**：任务/回合/帧模型、四个评测 split、三把尺子与判定口径、状态机与门控、unit 与 hook、两套缓存、启动器、观测手段，以及**已确认的逻辑冲突与踩坑台账**。含"存档策略四象限"（哪格必崩）、"attempt/reopen 的真实语义"（为什么复习机会只有一次）与"任务周期成本模型"（覆盖 50 个任务要多久）。规则全部来自真机事故与实测数字。 |
| [`lingbot-code-changes/`](lingbot-code-changes/) | 分四阶段的**受控代码改动流程**（讨论 → 清单 → 逐条执行 → 提交）：未经点头不动手、不扩权、报错先取证。核心遗留物是**改动台账**（§1 待验证 / §2 已验证 / §3 遗留）与「**改动本意」四问**（不变量 / 出错症状 / 快速回滚 / 验证入口）；并含**组合类改动的验证矩阵**（凡"开关 × 开关"必须四象限逐格给证据 —— 这条来自一次真实事故）。 |

其他：

| 文件 | 说明 |
|---|---|
| [`scripts/check.py`](scripts/check.py) | **仓库自检**。`python3 scripts/check.py` 一次跑三类检查：① CJK 加粗渲染缺陷；② 内部链接；③ **提示词与 skill 的同步**（关键词 + 目录完整性）。改完任何东西推之前跑一下。 |
| [`prompts/technical-course-private-tutor.md`](prompts/technical-course-private-tutor.md) | **聊天模式提示词**（对应 `technical-course-private-tutor`）。给没有文件系统（可能也没有联网）的纯聊天模型用。含方案 A（URL 版）/ 方案 B（自包含版）/ 三消息协议 / 与 `SKILL.md` 的同步清单。**用法**：开课时贴出，然后按「继续」逐节推进。 |
| [`prompts/conversation-synthesis.md`](prompts/conversation-synthesis.md) | **聊天模式提示词**（对应 `conversation-synthesis`）。**用法**：在一段**已经聊完的对话末尾**贴出，让模型把这段对话整理成文章。含 **6 阶段流水线**（脉络 → 标题子标题 → 初稿 → 润色 → 加链接 → 成稿）、停止契约、与 `SKILL.md` 的同步清单。 |
| [`prompts/zhihu-question-mining.md`](prompts/zhihu-question-mining.md) | **聊天模式提示词**（对应 `zhihu-question-mining`）。**用法**：贴出口述稿后贴出。含 **4 阶段流水线**（转写核对+话题划分 → 标题 → 描述 → 交付自检）、停止契约、标题反例、与 `SKILL.md` 的同步清单。 |
| [`prompts/lingbot-code-changes.md`](prompts/lingbot-code-changes.md) | **聊天模式提示词**（对应 `lingbot-code-changes`）。**用法**：在要改代码的那次对话里贴出。含方案 A（有文件系统）/ 方案 B（纯聊天）两版，**4 阶段契约**（讨论 → 清单 → 逐条执行 → 收尾），以及"组合类改动的验证矩阵"与血泪提醒清单。 |
| [`prompts/lingbot-auto-learning-logic.md`](prompts/lingbot-auto-learning-logic.md) | **知识型提示词**（对应 `lingbot-auto-learning-logic`）。**注意**：它不是流程提示词，而是把"AL 系统逻辑要点"压缩成一段可贴进聊天的正文（状态机与机会数量 / 四个 split / 任务周期成本 / 存档四象限 / 三套步号 / 配置硬校验），让没有文件系统的模型也能准确回答 AL 问题。**能读文件时优先直接读 `SKILL.md`**。 |

每个 skill 目录自带 `SKILL.md`（执行形态）与 `README.md`（可阅读形态），可单独复制安装。

> ⚠️ `prompts/` 下的提示词是各自 `SKILL.md` 的**派生副本**。改完 skill 记得按它的「同步清单」检查提示词是否过期——**提示词过期不会报错，只会让模型悄悄按旧规则走**。

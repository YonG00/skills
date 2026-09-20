# Skills

Agent Skills 集合。

| Skill | 说明 |
|---|---|
| [`technical-course-private-tutor/`](technical-course-private-tutor/) | 技术课程私人导师：把 lecture notes / PDF / 视频转录稿 / GitHub chapter 重建为可逐节学习的连续知识路径。**先把材料拆成主干路线图**（每节一个疑问句核心问题、声明"本节不做什么"），再一节一节讲；每个新概念首次出现时给 1–3 句历史锚点。 |
| [`conversation-synthesis/`](conversation-synthesis/) | 对话合成：把长期对话整理成**真正被思考过**的文章 / 研究笔记 / 分析稿。先还原**问题链与判断变化**再决定章节（不按聊天时间顺序）；保护用户真实表达；信息资产先回收再筛选并做**守恒核对**；可核验事实必须有来源；交付前跑六项审计。 |
| [`zhihu-question-mining/`](zhihu-question-mining/) | 知乎提问挖掘：把**口述稿 / 录音转写 / 随笔笔记**整理成**可发布的知乎提问**。先切话题单元（**一个提问 = 一个核心矛盾**），再写一句话标题 + 问题描述；标题从**具体对象**切进去，描述**保留本人的第一人称口语风格**。规则全部提炼自一次真实的六轮退回记录。 |

其他：

| 文件 | 说明 |
|---|---|
| [`prompts/technical-course-private-tutor.md`](prompts/technical-course-private-tutor.md) | **聊天模式提示词**（对应 `technical-course-private-tutor`）。给没有文件系统（可能也没有联网）的纯聊天模型用。含方案 A（URL 版）/ 方案 B（自包含版）/ 三消息协议 / 与 `SKILL.md` 的同步清单。**用法**：开课时贴出，然后按「继续」逐节推进。 |
| [`prompts/conversation-synthesis.md`](prompts/conversation-synthesis.md) | **聊天模式提示词**（对应 `conversation-synthesis`）。**用法**：在一段**已经聊完的对话末尾**贴出，让模型把这段对话整理成文章。含 **7 阶段流水线**（骨架 → 初稿 → 论证加固 → 语言风格 → 证据链接 → 结尾 → 标题与成稿）、两阶段停止契约、与 `SKILL.md` 的同步清单。 |
| [`prompts/zhihu-question-mining.md`](prompts/zhihu-question-mining.md) | **聊天模式提示词**（对应 `zhihu-question-mining`）。**用法**：贴出口述稿后贴出。含 **4 阶段流水线**（话题划分 → 标题 → 描述 → 交付自检）、停止契约、标题反例、与 `SKILL.md` 的同步清单。 |

每个 skill 目录自带 `SKILL.md`（执行形态）与 `README.md`（可阅读形态），可单独复制安装。

> ⚠️ `prompts/` 下的提示词是各自 `SKILL.md` 的**派生副本**。改完 skill 记得按它的「同步清单」检查提示词是否过期——**提示词过期不会报错，只会让模型悄悄按旧规则走**。

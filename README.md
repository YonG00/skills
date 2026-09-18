# Skills

Agent Skills 集合。

| Skill | 说明 |
|---|---|
| [`technical-course-private-tutor/`](technical-course-private-tutor/) | 技术课程私人导师：把 lecture notes / PDF / 视频转录稿 / GitHub chapter 重建为可逐节学习的连续知识路径。**先把材料拆成主干路线图**（每节一个疑问句核心问题、声明"本节不做什么"），再一节一节讲；每个新概念首次出现时给 1–3 句历史锚点。 |

其他：

| 文件 | 说明 |
|---|---|
| [`prompts/chat-mode.md`](prompts/chat-mode.md) | **聊天模式提示词**。给没有文件系统（可能也没有联网）的纯聊天模型用，把 skill 能力以提示词形式注入。含方案 A（URL 版）/ 方案 B（自包含版）/ 三消息协议 / 与 `SKILL.md` 的同步清单。 |

每个 skill 目录自带 `SKILL.md`（执行形态）与 `README.md`（可阅读形态），可单独复制安装。

> ⚠️ `prompts/chat-mode.md` 是 `SKILL.md` 的**派生副本**。改完 skill 记得按它的「同步清单」检查提示词是否过期——**提示词过期不会报错，只会让模型悄悄按旧规则走**。

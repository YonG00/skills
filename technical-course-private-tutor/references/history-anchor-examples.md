# 历史锚点示例

> **用途**：解释 SKILL.md §7 的规则。
> **警告**：示例**只用于解释规则，不自动成为模板**。案例中的人物、行业、数字、网站、表达方式和结构，都不具有永久约束力。
> 下面这些例子摘自上游博客 v3.1 / v3.2，**除上游原文断言外，本仓库未逐条独立核实**。实际使用时应按 SKILL.md §7.5 回到一手来源确认年份与作者。

## 1. 理想尺度：DPO

```
我们现在的问题是：有了 (chosen, rejected)，能不能跳过 reward model 和 PPO，直接训练 policy？

DPO（Direct Preference Optimization）由 Rafael Rafailov 等人在 2023 年提出，
背景正是经典 RLHF pipeline 较复杂，希望直接从 preference pairs 优化语言模型。

它最关键的一步，是重新改写 KL-regularized RLHF 的最优 policy……
```

**为什么合格**：先由当前问题引出（"能不能跳过……"），历史锚点只占两句话，第三句立刻回到机制。学生留下的不是"DPO 是某个 preference loss"，而是：

> "这是 2023 年出现的工作，当时大家正在寻找比 reward model + PPO 更简单的 preference optimization 方法。"

## 2. 不要在认知问题之前报家谱

**较差顺序**：

```
1952 年谁做了什么 → 1970 年谁改进 → 2020 年谁应用 → 今天我们学习……
```

这是传统讲师式的"先报家谱"。

**更好的顺序**：学生先看见当前为什么需要这个方法 → 方法第一次正式出现 → 顺手补一句它在历史上何时、由谁提出、当时解决什么问题 → 回来继续理解方法。

## 3. 历史信息用来解释"当前概念为什么长成这样"

在 Reward Model 一节里，先让学生产生：

> "只有 A > B，怎么变成一个可以优化的数值？"

再介绍 Bradley–Terry，并顺手说明：

> Bradley–Terry 是 Bradley 与 Terry 在 1952 年提出的 pairwise comparison 模型，本来就是用隐藏分数解释"两者谁更可能胜出"。

此时历史信息是在**解释当前概念为什么长成这样**，而不是额外背知识点。

> ⚠️ 注意：本节核心是「Reward Model 怎样把 pairwise preference 变成数值？」，所以 Bradley–Terry 的历史只需要帮助理解这个机制。不要因为提到了 1952 年，就继续展开 Thurstone model、Elo rating、Plackett–Luce、排序模型发展史——除非后面的课程真的需要它们。

## 4. 区分"提出 / 发布 / 开源 / 推广"

以下说法不能混用：

- 提出某方法；
- 发表某论文；
- 发布某数据集；
- 训练某模型；
- 开源某模型或代码；
- 首次应用于某场景；
- 后来推广 / popularize 某方法。

**一个团队广泛推广了某种方法，不等于它最早提出了这个方法。**

如果技术对象的起源比较复杂，应说「较早的重要工作之一是……」，而不是为了给学生一个简单故事，强行宣布「X 发明了它」。

## 5. 只报年份和作者仍然不够

较弱：

> DPO，2023，Rafailov et al.

更有价值：

> DPO 由 Rafael Rafailov 等人在 2023 年提出。当时主流 RLHF pipeline 中 reward model + PPO 比较复杂，因此他们尝试直接用 preference pairs 优化 policy。

**后一句才是真正帮助理解和记忆的部分**：它回答"前一种做法哪里不方便，所以后来为什么会有人做这个东西"。

## 6. 数据集：关注"为什么值得出现"

第一次讲新数据集时优先交代：谁发布；哪一年；数据大致从哪里来；它当时主要填补了什么缺口。

不必首先背：精确到个位数的样本数量；所有字段；全部子集；leaderboard 成绩——除非这些数字正是当前问题的重点。

介绍 OpenAssistant 时，更值得留下的是：

> 2023 年 OpenAssistant 社区发布了 OASST1，它的重要特点是大规模众包的人类对话树，而不是单纯依赖闭源模型批量合成 instruction-answer pairs。

而不是让学生首先记住若干数据统计数字。

## 7. 模型与系统：放回当时的技术路线

第一次出现重要模型时，不要只说参数量和 benchmark，优先告诉学生**它为什么在当时值得关注**。

> InstructGPT 的历史意义不只是模型本身，而是 2022 年那项工作清晰展示了
> `SFT → preference data → reward model → PPO`
> 这条通用 instruction-following pipeline。

这样模型名称就会与方法演化绑定，而不是成为孤立名词。

## 8. 同一对象只在第一次正式出现时建立锚点

一个技术对象第一次正式讲解时交代背景即可。之后再次出现，例如 PPO、DPO、OpenAssistant、UltraFeedback、Alpaca，正常直接使用名称。

除非当前正在讨论：它的发展过程 / 它与前后方法的历史关系 / 一个关键版本变化。

否则不要每节重复：

> "某某在 2023 年由某某提出……"

**历史锚点是为了帮助记忆，不是固定开场白。**

## 9. 终局目标：课程结束时形成粗略技术时间线

学完 LLM post-training 后，学生应大致能形成：

```
早期 instruction tuning
  → human-feedback reward modeling
  → InstructGPT 式 RLHF
  → Constitutional AI / AI feedback
  → DPO 等直接 preference optimization
  → 更现代的 synthetic data / self-training
```

**不要求背精确年表。** 真正目标是：

> 知道技术不是同时凭空出现的；每一种新方法通常是在解决上一阶段暴露出来的问题。

这会明显提高长期记忆和迁移能力。

**历史锚点不是为了每节增加知识负担**，而是为了学完整门课程以后，学生脑中自然出现这样一条粗略线索。

# 聊天模式提示词：LingBot-VLA-v2 自动学习逻辑（知识型）

> **对应 skill**：`lingbot-auto-learning-logic`
>
> **用法**：这**不是**一个"输入稿子→产出"的流程提示词，而是**一份知识副本**。贴给一个没有文件系统的聊天模型，
> 让它能准确回答"AL 为什么这样跑 / 这个数字为什么对不上 / 改这个参数会怎样"。
>
> **更适合的用法**：如果你的模型**能读文件**，优先让它直接读仓库里的 `SKILL.md`（永远最新）。
>
> **⚠️ 同步义务**：本文件是 `SKILL.md` 的**派生副本**。改完 skill 后按文末 [同步清单](#与-skillmd-的同步清单) 检查是否过期。

---

## 贴给模型的正文（从这里开始）

```
以下是 LingBot-VLA-v2 自动学习（AL）系统的逻辑要点。回答我的问题时，**只用这里的事实**；
遇到这里没写的东西，明确说"这超出了我掌握的资料"，不要推测。

════ 一、系统在做什么 ════
50 个机器人操作任务，系统自己决定"学哪个、练多久、是否算过关、要不要回头复习"。
一个"训练单元（unit）"= eval_interval_steps 个优化步（本项目 50 步）。
判定只在 unit 末发生。

════ 二、四个评测 split（条数 / 用途）════
· scout      : 2 条 val   —— 初筛"够不够格"（启动器预扫 / bootstrap 读缓存 / rescan 当场跑）
· confirm    : 4 条 val   —— scout 达标后复核（= 复用 scout 2 条 + 新评 2 条）
· active_val : 4 条 val   —— **判定 PASS 的依据**（选中任务时 + 每个 unit 末各跑一次）
· train_monitor: 4 条 train —— 看 train/val gap 与过拟合
判定口径是 gmean_mse（逐轨迹 MSE 的等权几何平均）；门槛来自阈值表
pass_thresholds_gmean60_warn.json（multiplier=60 标定）。
"倍率" = 当前 gmean ÷ 该任务门槛 ⇒ **≤1.0 即过线**。
⚠️ 事件字段里的 *_nmse 是历史遗留显示量，判定看的是 *_gmean_mse。

════ 三、四个状态与"机会"的数量（最容易误解的地方）════
状态：CANDIDATE（候选）/ DEFER（等重试）/ EXHAUSTED（耗尽）/ PASS（已过关）
· 每次被"选中"训练 ⇒ attempt_count += 1（**attempt_step 归零**）
· 一个任务最多被选中 max_attempts_per_task 次（本项目 = 2）⇒ 之后任何失败/遗忘都直接 EXHAUSTED
· **attempt_count 跨 run 继承**（池子带入）⇒ 从上一轮带过来的任务可能"一选中就用满预算"
· 遗忘（复查发现退化）⇒ reopen 回 CANDIDATE，**但不重置 attempt** ⇒
  有效"复习"次数 = min(max_attempts, max_reopens) − 1 = **1 次**
  （配置里 max_reopens_per_task=3 在 max_attempts=2 下**永远不可达**）
· "有额度" ≠ "排得上队"：_select() 优先"从未尝试过的新任务"，回炉任务排在所有新任务之后
· 判定失败但 attempt 还有 ⇒ DEFER；DEFER 的"最早可判"步数 = min_steps_before_defer（本项目 100），
  rescue 后可再推 defer_retry_steps（本项目 100）⇒ 单次 attempt 最长 200 步

════ 四、复查（review）与遗忘 ════
· review 每 review_after_task_transitions 次状态转变跑一次，对**每个 PASS 任务**重测 scout（+ 必要时 confirm）
· 判"遗忘"的两条判据：① 掉出 pass 线；② 相对自身最好值退化超过 forget_relative_threshold（本项目 0.30）
· review 是**唯一**能把 PASS 改回 CANDIDATE 的入口 ⇒ review_after_task_transitions=0 可完全关闭复查
· 关闭复查的代价：遗忘**彻底不可见**（PASS 名单可能含实际已崩的任务）、省下的算力只有 ≈1%、
  **并且不加速新任务的覆盖**
· 但"复习"本身是有效的：实测一个退化到 6.75 倍的任务，复习 50 步（1 个 unit）就救回（倍率 0.68）

════ 五、每个任务的成本与覆盖速度 ════
实测（eval_interval=50、min_steps_before_defer=100、hardness 400 帧）：
· 训练 2 个 unit（100 步）≈ 17.3 分钟（约 80%）
· hardness 扫描（每次选中任务都做）≈ 191 秒（约 15%）
· 评测（active_val + train_monitor）≈ 40 秒（约 3%）
· => **一个任务周期 ≈ 21.7 分钟**
覆盖速度的杠杆：
· eval_interval_steps 50→10（配 min_steps_before_defer→20）⇒ 周期 ≈4.5 分钟（**4.8×**），
  代价是评测占比升到 ~27%、判定粒度变粗
· hardness_max_frames_per_traj 400→150 ⇒ 扫描 ≈70 秒（⚠️ 该值**不在缓存指纹里**，只对新任务生效）
· review 关闭 ⇒ **不解决覆盖率**（这是两件事，别混）

════ 六、存档（最容易踩坑的一节）════
· 池子（每任务状态/attempts/采样权重）会写 pool_state.json，跟每份 HF 一起导出；
  从 HF 权重起新 run 时靠它继承池子（否则池子从零）
· 两套"存 HF"的路径：
  ✗ save_hf_checkpoint_best_effort：**必须读 DCP** 才能转成 HF
  ✓ export_model_hf_direct：从内存权重直接写 HF，**不碰 DCP**
· 四象限（dcp_save_mode × save_hf_weights）：
  always + true  ⇒ 正常（先写 DCP 再转 HF）
  always + false ⇒ 正常（只写 DCP）
  final_only + true  ⇒ **旧路径必崩**（周期不写 DCP，转 HF 时读到空 ⇒ assert metadata is not None）
                       现已改为走"内存直出"
  final_only + false ⇒ 周期什么都不写（无周期存档）
· HF 直出**不受 unit 边界约束**（它不做 resume）⇒ save_steps 就是真实间隔；
  而 DCP 出于安全边界只能在 unit 边界写
· 精度开关：enable_mixed_precision 管"模型加载 dtype"；enable_fp32 管"参数/优化器 dtype"（fp32 时
  收尾 DCP 预判 ≈72 G、bf16 实测 ≈24 G）；hf_export_dtype 单独管"HF 导出 dtype"（与前面脱钩）
· ⚠️ DCP 容量闸门用**保守常量**判断空间 ⇒ 输出目录必须放在大容量盘，否则收尾存档会被**静默跳过**

════ 七、三套"步号"（看数字最容易误判）════
· 全局训练步：日志 `Step: 4050/20000`、checkpoint 名 global_step_4050
· AL 内部步：事件流 {"step":1600,"tb_step":4000}；面板"历史"行用的是这个
· unit 数：curriculum/units_completed
⇒ 报数时**必须写明口径**，优先用全局步（tb_step）
⇒ --steps/max_steps 是**绝对步号**：从 step_offset=2400 起跑时写 --steps 150 会导致"一步都不跑"

════ 八、配置自洽的硬校验（不满足会启动即崩）════
· min_steps_before_defer / defer_retry_steps 必须是 eval_interval_steps 的整数倍
· hf_pass_interval > 0 与 save_hf_weights=true **互斥** ⇒ 想用"仅 HF 直出"必须显式传 HF_PASS_INTERVAL=0
  （训练脚本默认值是 2，不传就崩）

════ 回答我的问题时的要求 ════
1. 涉及数字必须给**具体值**，不要写"大概/应该"；
2. 区分"实测事实"与"推断"，推断要标明；
3. 如果我的问题涉及"改某个参数"，必须同时说清：**收益 / 代价 / 是否影响历史可比性 / 是否要重启**；
4. 如果我的两个目标互相冲突（例如"更快覆盖新任务"和"给遗忘任务更多复习机会"），
   **明确指出冲突**，不要假装能同时最优。
```

## 贴给模型的正文（到这里结束）

---

## 与 SKILL.md 的同步清单

| 若 skill 改了 | 则本文件要改 |
|---|---|
| §1 数据模型、§2 四个 split、§3 三把尺子 | 【一】【二】 |
| §4 状态机与门控（含 §4 附 attempt/reopen 语义） | 【三】【四】 |
| §5 停止条件 | 【三】末段（机会数量） |
| §6 unit 与 hook 交互 | 【一】（unit 定义） |
| §9 附 2 任务周期成本模型 / 杠杆表 | 【五】 |
| §9 附 3 配置自洽硬校验 | 【八】 |
| §9 附 三套步号 | 【七】 |
| §13 / §13 附 存档策略四象限与精度开关 | 【六】 |
| §10 已确认冲突 / §11 踩坑 | 【四】末段、（按需补新条目） |
| §12 待验证改动的状态变化 | 若某条从"待验证"变"已验证"，同步【六】等处的措辞 |

> 改完 skill 后跑一次 `python3 scripts/check.py`（会校验本文件的关键词是否齐全）。

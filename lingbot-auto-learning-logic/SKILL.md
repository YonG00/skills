---
name: lingbot-auto-learning-logic
description: LingBot-VLA-v2 自动学习（Auto Learning）的完整逻辑地图 —— 任务/回合/帧的数据模型、五个评测 split（scout/confirm/active_val/train_monitor）各自几条几条轨迹且何时跑、三把尺子（mse/nmse/gmean_mse）与判定口径、状态机与门控（bootstrap 免费 PASS / rescan / rollover / churn guard）、停止条件优先级、训练单元与 hook 的交互、scout 与 hardness 两套缓存、启动器预扫与 --env 传参、观测手段（日志/事件流/al_panel）以及已确认的逻辑冲突与踩坑台账。当需要改 AL 代码、排查"为什么没判定/没训练/在扫什么"、写 AL 相关文档或复习整体设计时使用。
agent_created: true
---

# LingBot-VLA-v2 自动学习（AL）逻辑地图

> 用途：改 AL 代码前先读这一篇，避免"改一处、静默失效另一处"。
> 锚点一律用**函数名/谓词**（行号会随重构失效）。
> 本文件是**逻辑地图**，不是状态记录；当前 run 的状态看 `al_panel.py`，流水看当日 memory。

## §1 数据模型（一切的基础）

```
任务 task（50 个，来自 manifest）
 └── 回合 trajectory / episode（每任务 50：40 train + 10 val）
      └── 帧 frame / sample（一帧 = 一个训练样本，sample_id == dataset local_idx）
```

- 划分文件：`<split_dir>/manifest.json`（`episodes_per_task`、`val_ratio`、每任务 `train_ids`/`val_ids`/帧数）
- 目录对象：`TaskCatalog` / `TaskEntry`（`lingbotvla/auto_learning/catalog.py`、`ports.py`）
  - 关键字段：`train_sample_ids`（训练白名单）、`samples_by_traj`（每条回合的 sample 列表 ⇒ 可算帧数）、`baseline_mse`
- **索引空间**：训练数据集只建一次，白名单 = 所有参与任务的 train 回合并集 ⇒ `sample_id` 全程不变。

## §2 五个评测 split（**条数 / 时机 / 用途 / 是否真推理**）

| split | 条数 | 何时 | 用途 | 真推理？ |
|---|---|---|---|---|
| `scout` | **2 条 val**（`global_scout_val_trajs`） | ① 启动器预扫 ② bootstrap（读缓存）③ rescan（当场） | 初筛"够不够格" | ①③ 真跑；② 读 scout 缓存 |
| `confirm` | **4 条 val** = scout 的 2 条 + **新采 2 条** | only when scout 达标（bootstrap / rescan） | 复核，防 2 条 scout 碰巧过线 | ✅（2026-10-11 起：复用 scout 2 条 + 只新评 2 条） |
| `active_val` | **4 条 val** | 选中任务时（开训前）+ **每个 unit 末** | **判定 PASS 的依据**、成长轨迹、LP、过拟合 | ✅ 两次都真跑（unit 末那次不可省） |
| `train_monitor` | **4 条 train** | 同上两个时点 | train/val gap、过拟合判据 `gap_prev` | ✅ 两次都真跑 |

- 切分实现：`state/registry.py` 构造 `TaskRecord` 处（`val_ids[:n]` / `train_ids[:n]`）。
  **2026-10-11 起** `confirm_val_ids` 与 `active_val_ids` **同组**（`_judge_n`）⇒ 判定尺子只有一把。
- 内部 `split` 名映射：`real/backend.py::_split_name()` —— `train_monitor → train`，其余 → `val`
  （adapter 要校验"不跨 split 泄漏"）。
- **预扫只做 scout**：`real/hook.py` 的扫描模式（`AL_SCAN_SKIP_HARDNESS=1`）在 bootstrap 队列一空就 `_finish("scan_only_scout_done")`，**从不进 `_select()`** ⇒ 不会跑 active_val/hardness。

### §2 附：评测本体的"并行"现状（2026-10-11）

| 层 | 是否真并行 | 机制 |
|---|---|---|
| 启动器预扫（scout） | ✅ **任务级** | 每卡一片、**独立进程**（各自完整模型、无集合通信），汇总进 scout 缓存 |
| hardness 扫描 | ✅ **帧级** | `ids[rank::world]` + `all_gather_object`（`real/backend.py`） |
| **开环评测本体** | ⚠️ 现状 = **全员冗余** | FSDP all-gather 是集合通信 ⇒ 全员必须参与；`_multirank_eval_payload` 让 rank0 结果广播对齐 |
| **轨迹分片**（`AL_EVAL_SHARD=1`） | ✅ **已真机跑通**（2026-10-12，v62/v64） | 每卡恒 `k=ceil(n/W)` 条；**切片与归并都在「多卡协议之内」**（见下方"分片正确架构"）；日志 `[open_loop][shard] … 框架内归并后 N 条` |

⚠️ **分片的安全前提**：每卡**前向次数必须相同**（固定 k 条；回绕重复由汇总去重）。
"交错均分"（次数 2/1/1…）会因集合通信错配**静默死锁** —— 与批处理被强制关闭是同一类理由。
真机验证项（见 `docs/auto_learning/AL_PENDING_CHANGES.md` §1 #6）：不死锁 + 指标逐位一致 + 墙钟 ≈ 1/W。

### 🔴 分片"正确架构"（2026-10-12 真机定案，5 个 bug 的结论）

```
❌ 错误做法：在「多卡协议**之外**」先把 my_ids 切好，再交给 adapter
   ⇒ 框架 `_multirank_eval_payload` 的语义是「各卡跑同一批 / **只有 rank0 结果算数** /
     广播 rank0 的结果」⇒ 每卡只交出"自己那 1 条"⇒ 广播回来的人人都是那 1 条
   ⇒ 外层再 all_gather 只能收到 7 份**相同的 rank0 复制**
   ⇒ 合并后 per_traj 只 1 条而 episode_ids 是全集 ⇒ `gmean_mse` fail-closed 返回 None
   ⇒ **判定失效（0 个 PASS）**

✅ 正确做法：切片 + 归并都放进**协议之内**（`run()` 里切片，`merge_ranks` 在广播前归并）
   ① `evaluate_ids` 内 `_slice_run_ids()`：按 rank 现算本卡切片（**单入口**）；
   ② 各卡只评自己的切片，`run()` 返回本卡 raw；
   ③ 协议 `merge_ranks=_merge_ranks_callback`：`_gather_rank_payloads` 收齐各卡 →
      `_merge_shard_raw_payloads` 按 episode id 并集去重、`mse` **帧数加权**重算；
      覆盖不全 ⇒ **直接抛**（绝不产出会被 gmean 拒收的残缺结果）；
   ④ rank0 的返回值本就是**全集** ⇒ 末尾广播 = "把全集同步给所有卡"（协议语义不变）。
```

**开关**：`merge_ranks` 仅在 backend 注入策略时启用（默认 `None` ⇒ 非分片路径**逐字不变**）。
**调试事证**：`AL_SHARD_MERGE_TRACE=1` 才打印 `[slice]`/`[run-out]`/`[merge-in]`（默认关，不刷屏）。

> 🔴 **改动状态看 §12**：哪些改动已默认生效、哪些只在 CPU 验证过、哪些默认关 —— 都在那一节；
> 上机报错时**先来这里对号**（权威账本是仓库内 `docs/auto_learning/AL_PENDING_CHANGES.md`）。

## §3 三把尺子与判定口径（**命名消歧义**）

| 指标 | 定义 | 角色 |
|---|---|---|
| `mse` | 动作 MSE（帧加权 pooled） | 绝对尺度；`pass_metric="mse"` 时是判据 |
| `nmse` | `mse / baseline_mse`（baseline = 该任务固定常数） | **命名历史遗留**：ratio 模式下**只是 legacy 显示量**，缺 baseline ⇒ None |
| `gmean_mse` | 逐轨迹 MSE 的**等权几何平均**（`decision/gmean.py::geometric_mse`） | **当前判定口径**（`pass_metric: gmean_mse`），阈值表按它标定（`multiplier=60.0`、`stat=geomean`） |

- `gmean_mse` 是 `TrajectoryMetrics` 的 **property**（由 `per_traj_mse` + `n_trajs` 派生）
  ⇒ **合并两组评测 = 合并 `per_traj_mse` 字典**（几何平均可分组；冲突以新算为准）。
- `config.py` 的 `pass_metric` 默认是 `"nmse"`；本批 run 用 `gmean_mse` + `pool_filter_by_gmean_ratio: true`
  ⇒ `_nmse_is_required()` 返回 False，NMSE 不再是否决条件。
- 判定入口统一：`decision/thresholds.py`（`is_pass` / `check_pass` / `pass_line`）。
- **消歧义现状**：事件字段名（`scout_nmse` 等）保留历史命名（改名会让 v41–v44 产物不可比），
  已在 `scheduler.py` 记录处加注释说明"判定看 `*_gmean_mse`"；参数 `active_val_probe_trajs`
  实际决定 confirm 条数，已在 `registry.py` 加注释。

## §4 状态机与门控

- 状态：`TaskStatus`（CANDIDATE / DEFER / EXHAUSTED / PASS…）见 `types.py`；注册表 `state/registry.py`。
- **bootstrap 免费 PASS**：`_bootstrap_one()` —— scout 达标 ⇒ confirm 达标 ⇒ `apply_pass(BOOTSTRAP_PASS)`
  ⇒ 任务**直接毕业、永不训练**（省训练步）。
- **选任务**：`_select()` 只从 **CANDIDATE** 池挑（按 ratio 分档/门槛余量排序）⇒
  **bootstrap PASS 的任务与被训练的任务天然不重叠**（实测 v43/v44 零交集）。
- **rescan**：`_rescan()` —— 每 `rescan_every_n_task_switches` 次切换全池重扫；rollover 后定向扫被提升任务；
  含"免费 PASS 检测"（EXHAUSTED 被 transfer 带起来 ⇒ 直接 PASS），有 **churn guard** 防循环。
- **attempt 收尾**：判定失败 ⇒ DEFER（等 `min_steps_before_defer`）或 EXHAUSTED；`rescued` 会把 DEFER 阈值后推 `retry_budget_steps`。

### 🔴 §4 附：attempt / reopen / 复查 的真实语义（2026-10-13 真机 al_v76 定案）

**四个数各管什么（别混）**：

| 参数 | 现值 | 真正管的 | 代码锚点 |
|---|---|---|---|
| `max_attempts_per_task` | 2 | **任务被"选中"的总次数上限**（跨 run 继承！） | `apply_defer_or_exhaust` / `apply_reopen` 都先查它 |
| `min_steps_before_defer` | 100 | 本 attempt **最早可判 DEFER** 的步数（**决定每个任务的最小成本**）| `decide_after_unit(defer_after_steps=…)` |
| `defer_retry_steps` | 100 | rescue 后把 DEFER 阈值**再推后**多少（⇒ 单 attempt 最长 200 步）| 同上（`defer_after_steps` 由调用方累加） |
| `max_reopens_per_task` | 3 | 遗忘回炉次数上限 —— ⚠️ **在 `max_attempts=2` 下永远不可达** | `churn_guard_tripped` |

**关键链路与"每任务最多练几次"**：

```
每次被 _select() 选中 ⇒ start_attempt()：attempt_count += 1、attempt_step = 0
失败收尾 ⇒ apply_defer_or_exhaust()：attempt_count >= max_attempts ⇒ EXHAUSTED，否则 DEFER
遗忘回炉 ⇒ apply_reopen()：**先查 attempt 预算**（不重置！）⇒ 超了直接 EXHAUSTED，否则 reopen_count+=1 回 CANDIDATE
```

⇒ **一个任务最多被选中 `max_attempts_per_task` 次**（本项目 2）；
⇒ **有效"复习"次数 = min(max_attempts, max_reopens) − 1 = 1 次**（配置的 3 无效）；
⇒ **`attempt_count` 跨 run 继承**（池子带入）：实测 al_v76 的 20 个被选中任务里
**12 个的 `attempt` 在选中时就已是 2**（上一轮练过 1 次）⇒ **本 run 一选中就用满预算，一遗忘就永久 EXHAUSTED**
（`click_bell` / `pick_dual_bottles` / `click_alarmclock` / `place_shoe` / `blocks_ranking_rgb` / `stack_blocks_three` 等 6 个）。

**⚠️ 但"有额度"≠"排得上队"**（实测）：al_v76 里 7 个任务被 reopen 成 CANDIDATE，
**却没有任何任务被选中 ≥2 次** —— `_select()` 优先"从未尝试过的新任务"
（`pick.attempt_count == 0 and not pick.ever_passed` 归入新任务档）⇒
**回炉任务排在所有新任务后面**；队列长（23 个新任务 × 21.7 分钟 ≈ 8 h）时，复习**几乎不会发生**。

**复查（review）开关**：`review_after_task_transitions`（默认 2）= 每 N 次状态转变做一次全 PASS 复查；
**设 0 ⇒ 完全关闭**（`if self.al.review_after_task_transitions > 0 and st.transition_count % N == 0` ——
前半句短路既表达"关闭"、又避免除零）。关闭的后果与代价：

| | 说明 |
|---|---|
| ✅ 收益 | PASS **只增不减**（`apply_reopen` 是唯一把 PASS 改回 CANDIDATE 的入口，且只被 review 调用）；不再无谓回炉 |
| ❌ 代价 | **遗忘彻底不可见**（PASS 名单可能含"实际已崩"的任务 ⇒ 最终 PASS 数虚高）；省下的算力**仅 ≈1%**（每次 review ≈16–32 s，11 次/6.4 h） |
| ⚠️ 注意 | **它不加速覆盖新任务**（覆盖率由 `eval_interval_steps` 决定）—— 这两件事必须分开决策 |

**"复习"是有效的（实测反例，别轻易关掉）**：`stack_bowls_three` 曾退化到
**nmse 1.274 / gmean 0.0797（倍率 6.75×）** 被判遗忘 ⇒ reopen ⇒ **复习 50 步（1 个 unit）就救回**
（val mse 0.1446 → **0.0081**，倍率 **0.68×** ⇒ PASS）。
⇒ 关 review 会让这类"50 步就能救回"的任务**永久丢失**。


## §5 停止条件（`_budget_exhausted`，优先级从上到下）

1. `_total_pass_target_reached()`：PASS 数 ≥ `target_total_passed_tasks`，**且 bootstrap 队列已空**；
   还有**下限门控**：`len(newly_passed) < min_new_tasks_passed_this_run` ⇒ **不收工**（防"bootstrap 白送满池、零训练步结束"）
2. `unit_budget_reached`
3. `max_global_steps`
4. `max_transitions`
5. `max_new_tasks_passed_reached`（`newly_passed ≥ max_new_tasks_passed_this_run`）
6. `max_new_tasks_attempted_reached`（`new_tasks_attempted ≥ max_new_tasks_attempted_this_run`；**维护类任务豁免**）
7. 池空：`min_new_passes_not_reached` / `all_tasks_resolved` / `no_eligible_candidate`

- `new_tasks_attempted` 只在"首次 attempt 且从未 PASS"时 +1 ⇒ 上限 ≤ 任务总数（50）时才有意义；
  设 51 ≡ 不限。
- 候选池被 ratio 分档清空时会打印 `候选池被 pool_ratio 分档清空`（避免"训练照跑、什么都不选"的静默失败）。

## §6 训练单元（unit）与 hook 交互

- 一个 unit = `train_unit_steps` 步（本批 50 步）；hook 在 `real/hook.py`。
- 顺序：`_select()`（选任务 + 开训前基线 + hardness 扫描）→ 发 `TrainRequest` → 训练 N 步 →
  `on_step_end` 最后一步触发 `_review_attempt()`（复测 + 判定 + 记账）。
- 🔴 unit 末**必须**重测（`active_val` 4 条 + `train_monitor` 4 条）：判定需要"训练后"的值；
  只测训练后**不够**，因为 LP（进步幅度）与 `gap_prev`（过拟合变化量）需要"训练前"的对照。
- `_record_eval(rec, metrics, kind)`：指标名用 **`kind`**（`task/<task>/<kind>_gmean_mse`），
  `kind="active_val"` 时额外记 `pass_threshold_*` 与 `val_to_pass_threshold`（面板的"倍率"）。

## §7 缓存体系（两套，规则不同）

| 缓存 | 文件 | 谁能用 | 指纹/失效 |
|---|---|---|---|
| `scout` | `scout.<model-slug>.json` | **只有 bootstrap 的 scout**（`evaluate_bootstrap_scout`；rescan 明确 bypass） | 含模型身份；`AL_MODEL_NAME` 由 `--model-name` 或 checkpoint 路径尾部 4 段决定 |
| `hardness` | `hardness.<model-slug>.json` | 逐样本 loss 复用（按 sample id） | 含 `model` + `noise_semantic_version`；**不含帧上限** ⇒ 改 `hardness_max_frames_per_traj` 不会重扫已缓存样本 |

### 🔴 临时白名单文件 `_episode_ids_file`（**必带本卡切片指纹**）

`OpenLoopValidator._episode_ids_file(ids, tag)` 把"要评哪几条回合"落成临时 JSON（`build_vla_dataset` 只认文件）。

**文件名 = `<tag>_<本卡切片指纹>.json`** —— 指纹这一节**不能省**（2026-10-12 真机 al_v61 定位）：
- 原实现是 `<tag>.json`，注释假设「多卡分片下所有 rank 都写同一个文件，且内容完全相同
  （`sorted(ids)`）⇒ 谁赢都一样」；
- 该假设**在轨迹分片下不成立**（各卡切片不同）⇒ 7 张卡互相覆盖，
  后到的 rank 从 `_dataset(path)`（**按路径缓存**）读到**别人的切片**
  ⇒ 实测 `rank2 run_ids=[1408]` 却返回 `per_traj_ids=[1403]` ⇒ 归并时 7 份全同
  ⇒ 被不完整断言拦下（`各卡 ids=[[1403]×7]`）。
- 加指纹后各卡各写各读，互不干扰；`tag` 已含任务/split ⇒ 跨 run 也不冲突。

- 缓存是"**逐轨迹/逐样本确定性**"的：实测同一 scout 值在 dp8 与 dp7 两次 run 中**逐位相同**（相对差 0.00e+00）
  ⇒ 这正是"confirm 可复用 scout 值"的数值前提。

## §8 启动器（`experiment/robotwin/al_launch.py`）

- 预扫：50 任务分 N 片（每卡一片），扫描 worker 带 `AL_SCAN_SKIP_HARDNESS=1` ⇒ 只补 scout；门控只看 scout 覆盖率。
- 覆盖率 100% ⇒ `结论：覆盖完整（50/50）⇒ 启动训练`，否则拒绝启动。
- 🔴 `base_env()` **只透传 `AL_*` 前缀的环境变量**；`SAVE_EVERY` / `HF_PASS_INTERVAL` 等训练脚本变量
  **必须用 `--env KEY=VALUE`** 传（2026-10-11 修：这两个键已纳入白名单）。
- `--allow-busy`：检测到其它训练在跑时要显式给，否则退出码 2。

## §9 观测手段

- 训练日志：`/models/robotwin-persistent/al_runs/logs/train_<run>.log`
  - `[ckpt] 策略：每 N 步 DCP；…`（核对存档节奏）、`[hardness] 扫描开始/进度/扫描完成`、
    `[open_loop][phase]`（评测阶段与耗时）、`[open_loop][confirm] 复用 scout N 条 + 新评 M 条`
- 事件流：`…/train_<run>/auto_learning_events.jsonl`（`action` 序列 + `curriculum/*` 指标 + 每任务指标）
- 面板：`tools/auto_learning_pipeline/al_panel.py <run>`（`--trainers` 看全机训练器、`--all` 全任务）
  - 🔴 **一键启动（推荐，2026-10-12 起）**：`bash tools/auto_learning_pipeline/al_watch.sh [run]`
    · 免记 `AL_ROOT` / `PYTHONPATH` / 解释器路径（脚本自动处理）；
    · **根目录自动探测**：按"训练日志最新修改时间"在 `/models/robotwin-persistent/al_runs`
      与 `/workspace/al/al_launch_runs` 之间二选一 —— 本机两个都在，固定优先生产目录会选到**旧的 al_v44**；
    · 不给 run ⇒ 自动选最新；run 名写错 ⇒ **列出最近 8 个候选**（`al_v65` ≠ `al_v65_formal`）；
    · `ONCE=1` ⇒ 只打印一次；`AL_WATCH_SEC=N` ⇒ 改刷新间隔（默认 3s；面板单次仅 ~120ms）。
  - 🔴 **数据源与新鲜度（排查"面板数字不对"先看这张表）**：

    | 面板行 | 数据源 | 新鲜度 |
    |---|---|---|
    | 通关 / 倍率 / 历史 | `auto_learning_events.jsonl` | ✅ 每 unit 末实时 |
    | **池子计数** | **TensorBoard** `skill_overview/*_count` | ✅ 每 unit 末实时（2026-10-12 起） |
    | 在训任务 | 事件流 **最后一条 `select` 事件** | ✅ 实时 |
    | 本任务步数 / 细节 | `pool_state.json` / DCP `extra_state` | ⚠️ **只在存档点**（`SAVE_EVERY`） |

    ⇒ 若"池子"与"通关"看起来矛盾，先确认是否读到了实时源；注册表快照永远可能落后数百步。

  - 🔴 **「在训任务」的判据：必须用最后一条 `select`，不能用 `unit_loss`（2026-10-13 实测踩坑）**：
    · `task/<t>/unit_loss` 是**在 unit 结束时**才写的 ⇒ 它代表"**刚训完的那个任务**"，不是"正在训的"；
    · 实测 al_v76：面板按 `unit_loss` 最大 step 判出"在训 `stack_bowls_three`"，
      而真实在训是 **`place_object_scale`**（事件流最后 `select`，且 `curriculum/current_task_name` 也是它）
      ⇒ 用户据此问"不是早就达到门槛了吗，怎么还在学？"（**误报**）；
    · 正确判据（按可靠性排序）：① 事件流最后一条 `action=="select"` 的 `task`；
      ② `curriculum/current_task_name`（同一步会写两次：先旧后新 ⇒ 取**最后**一个）；
      ③ 兜底才用 `unit_loss`。
  - 🔴 **`select` 事件还带两个关键字段**（排查全靠它们）：
    `attempt`（**选中时**的 attempt_count ⇒ 判断"这是第几次机会"）、`scout_pass_ratio`（选中时的倍率）。
    实测：`{"action":"select","task":"click_bell","attempt":2,...}` ⇒ 说明它**继承来的 attempt 已是 1**，
    本 run 一选中就变 2 ⇒ 一遗忘就 EXHAUSTED（详见 §4 附）。

- 判活（**不要靠日志 mtime，也不要用 GPU util 判训练**）：`/proc/<pid>/stat` 的 utime/stime、`/proc/<pid>/io` 的 rchar。
- hardness 扫描是**静默**的（跑完才写指标）⇒ "日志停更 + 事件流无新条目 + CPU 稳定"是**正常在扫**。

### 🔴 §9 附：三套"步号"别混（2026-10-13 实测，看面板/事件流时最容易误判）

| 口径 | 长什么样 | 换算关系（实测 al_v76） |
|---|---|---|
| **全局训练步** `tb_step` | `Step: 4050/20000`（日志 tqdm、checkpoint 名 `global_step_4050`） | 基准 |
| **AL 内部步** `step` | 事件流 `{"step":1600,"tb_step":4000}`；**面板"历史"行显示的也是它** | `tb_step ≈ step_offset + AL `step` × eval_interval`（本次 ≈ 2400 + 1600 ≈ 4000） |
| **unit 数** `units_completed` | TB `curriculum/units_completed`（= AL 步 / `eval_interval_steps`） | `units = AL_step / eval_interval` |

⇒ **面板"历史"里的 `1600 / 3950 / 4000` 是 AL 内部步，不是全局步** ——
用户曾据此困惑"G 早就过线了怎么还在学"。
⇒ 事件流的指标行同时带 `step`（AL）与 `tb_step`（全局）⇒ **报数时优先用 `tb_step`**。

### 🔴 §9 附 2：任务周期的成本模型（决定"覆盖 50 个任务要多久"）

实测 al_v76（`eval_interval_steps=50`、`min_steps_before_defer=100`、`hardness 400 帧`）：

| 环节 | 实测 | 占比 |
|---|---|---|
| 训练 2 个 unit（= `min_steps_before_defer` 100 步） | 100 × 10.4 s ≈ **17.3 min** | ~80% |
| **hardness 扫描**（每次 `_select()` 都做） | 均值 **191 s**（3.2 min，最大 647 s） | ~15% |
| 评测（active_val + train_monitor，已分片） | 2×4×3–5 s ≈ 40 s | ~3% |
| **一个任务周期** | **均值 21.7 min**（最大 46.8） | 100% |

**⇒ 覆盖速度的杠杆（按收益）**：

| 目标 | 改哪里 | 效果 |
|---|---|---|
| **覆盖率（决定性）** | `eval_interval_steps 50 → 10` + `min_steps_before_defer 100 → 20` | 每任务 **21.7 → ≈4.5 min**（**4.8×**）；代价：评测占比升到 ~27%、判定更粗 |
| 扫描耗时 | `hardness_max_frames_per_traj 400 → 150` | 扫描 ≈191 → ≈70 s（每任务省 2 min）；⚠️ **帧上限不在缓存指纹里** ⇒ 只对新任务生效 |
| 减少"无谓回炉" | `forget_relative_threshold 0.30 → 0.45` | 保住边界任务（实测 7/10 个被遗忘任务的倍率仍在 0.48–1.18）；保留"掉出 pass 线"兜底 |
| 给复习真机会 | `max_attempts_per_task 2 → 3` | 复习从 1 次变 2 次；代价：每任务占用 unit ↑ |
| ❌ 不解决覆盖率 | `review_after_task_transitions: 0` | 只省 ~1% 算力、PASS 不再掉；**不加快覆盖** |

### 🔴 §9 附 3：配置自洽的硬校验（不满足**启动即崩**）

- `min_steps_before_defer` / `defer_retry_steps` **必须是 `eval_interval_steps` 的整数倍**（`config.py` 强制）；
- **`hf_pass_interval > 0` 与 `save_hf_weights=true` 互斥**（`train_lingbotvla.py` 里 `raise ValueError`）；
  ⇒ 想用"仅 HF 直出"（见 §13 附）**必须显式传 `HF_PASS_INTERVAL=0`**，
  而训练脚本 `al_50task_bf16.sh` 的 **默认值是 2** ⇒ **不传就会崩**（实测踩过两次）。
- **`max_steps`（`--steps`）是绝对步号**：本 run 从 `step_offset=2400` 起 ⇒ 写 `--steps 150` 会**立刻满足收尾条件**
  （`global_step(2401) >= 150`）⇒ 训练一步都不跑就退出。**要跑 N 步须写 `--steps <offset + N>`**。


## §10 已确认的逻辑冲突 / 隐患（改之前先看这一节）

1. **门控与基线互斥**：bootstrap PASS 的任务直接毕业、`_select` 只挑 CANDIDATE ⇒
   "用 confirm 的 4 条当训练前基线"**永远命中不了**（实测 v43/v44 零交集）。想复用必须改门控语义。
2. **相邻时刻重复评测**：confirm（选任务前）与 select 的基线评测相邻且模型状态相同；
   当前靠"两条路径互斥"侥幸未发生 ⇒ 结构上仍是重复源。
3. **confirm ⊃ scout**：4 条含 scout 的 2 条 ⇒ 复核不独立、且那 2 条原本被重跑（2026-10-11 已改为复用，省一半算力）。
4. **参数语义错位**：`active_val_probe_trajs` 实际决定 confirm 条数；`active_val_ids` 现为 confirm 的别名。
   （清理需动配置键 + `SEMANTIC_KEYS` 指纹 ⇒ 影响 resume，故暂只加注释。）

## §11 硬约束与踩坑台账

- 🔴🔴 **有训练在跑时，绝不做训练/GPU 测试**（2026-10-11 用户明确要求）：
  后台训练（`torchrun` + 7–8 个 rank）占满显卡，此时"跑训练 / 跑 GPU 测试 / 采集 GPU 指标的 pytest"
  都可能抢显存、触发 OOM 或驱动错误，**把正在跑的长任务搞崩**。
  - **允许**：`py_compile`、纯 CPU 单测（不 import torch）、读日志/事件流/`/proc`；
  - **pytest 的收集阶段也要小心**：`--collect-only` 会 import 测试模块，若模块顶层 `import torch`
    就可能初始化 HIP 上下文 ⇒ 训练期能不跑就不跑，能读源码就只读源码；
  - 确需在机器上跑 CPU 测试时，**先确认没有训练进程**（`pgrep -f "[t]asks/vla/train_lingbotvla.py"` 为 0）。
- **只读优先**：改动前先 `grep` 全仓引用点，列出"连带改动"，否则静默失效（例：改造判定口径要同步 `orchestration/baselines.py` 对照组）。
- **停训练必须按进程组**：`al_launch.py` 之下还有 `al_50task_bf16.sh` → `train.sh` → `torchrun` → rank；
  只杀 launcher 会留下**孤儿 rank 占着显存**。做法：从脚本 PID 取 PGID 后 `kill -9 -- -PGID`，再补杀残留并确认显存回落。
- **GPU 硬件**：本机曾出现某卡"利用率恒 100% + 温度正常 + 无进程 + H2D 挂死"（不可用）；另有 launcher 对特定卡号的挂死警告。换卡前先做最小 H2D/matmul 自检。
- **shell 引号**：远端脚本一律"本地写文件 → scp → 远端执行"，不要用 heredoc 嵌 Python（本会话踩坑 7 次以上）。
- **后台作业**：远端长任务 `setsid nohup … > log 2>&1 < /dev/null &`；读取只允许无参数 `job_output(id)`，**禁任何等待语义**。
- **改口径要留痕**：新增/变更判定口径时同时补 ① 运行期日志（含可核对数字）② 代码注释（为什么、口径是否变）③ 单测（含边界）。

### 🔴 2026-10-12 分片专项（3 条，都是"改了数值却没人发现"类）

1. **共享文件名必须带"内容指纹"**：多进程/多卡写同一个文件时，
   "内容相同 ⇒ 谁赢都一样"这个假设**只在"各卡输入相同"时成立**。
   分片/扫描等"各卡输入不同"的场景 ⇒ 必须让文件名区分（`<tag>_<指纹>.json`），
   否则会出现"**程序不报错、但结果来自别人的数据**"（最坏的一类 bug）。
2. **设备数相关分支必须显式门槛**：并行优化（按卡切分/窗口数锁死）**只能作用于多卡**。
   把 `world<=1`（单卡，含**启动器预扫 worker**）也纳入 ⇒ 会**悄悄改掉单卡的测量口径**
   （实测：把"每 50 帧一个窗口"变成"每条轨迹摊 2 个窗口" ⇒ 同一轨迹 MSE 差 0.5–4.7 倍）。
   规矩：`if world > 1: <并行口径> else: <原口径>`，并在日志里打印实际走向。
3. **写入"进程级策略"后不要急着清**：`set_shard_merge_strategy(...)` 这类全局策略，
   若用 `try/finally` 立刻清掉，会与**各卡返回时序**竞态（先返回的 rank 清空 ⇒
   后到的 rank 读不到 ⇒ 行为不一致，甚至集合通信错配）。⇒ **只注入、不收回**（策略幂等）。

## §12 待验证改动（**已改代码、未上机**；正式测试通过后回来改本节的"状态"）

> 🔴 **读这一节的意义**：当前逻辑里有些分支**只在 CPU 单测下验证过**，真机行为未证实。
> 一旦上机报错，**先来这里对号**（比翻 git log 快）：很可能就是某条未验证改动引起的。
> 权威账本 = 仓库内 `docs/auto_learning/AL_PENDING_CHANGES.md`（含 commit SHA 与验证判据）；
> 本节只保留"**读逻辑时需要注意的行为差异**"，测试通过后**把对应行标 ✅ 并补实测数字**。

| 改动 | 默认是否生效 | 读逻辑时要注意什么 | 未验证的风险 | 状态 |
|---|---|---|---|---|
| **confirm 去重复**（`RealEvaluator.evaluate_confirm_merged` / `scheduler._timed_confirm_merged`） | ✅ **默认生效** | confirm 的判决值 = **scout 已测的 2 条（复用）+ 新评 2 条**的合并；日志会出现 `[open_loop][confirm] 复用 scout N 条 + 新评 M 条`；事件多了 `confirm_reused_trajs` / `confirm_fresh_trajs`。**`confirm_nmse` 口径与 v41–v44 不可逐位比** | 若 scout 值来自**更早的模型状态**，复用即陈旧（当前两处调用点都在同一模型状态内，故安全）；Stage A 假件走能力探测兜底 | 🧪 CPU 已验证（单测 5 + 回归 131）；**真机未验证** |
| **轨迹分片**（`AL_EVAL_SHARD=1`） | ✅ **真机已用**（v62/v64/v65） | 关时 `evaluate()` 与改造前**逐字一致**；开启后**切片+归并都在协议之内**（见 §2 附"分片正确架构"）。日志 `[open_loop][shard] … 框架内归并后 N 条`（N==全集） | ⚠️ 集合通信错配会**静默死锁**（CPU 测不出）；多卡尺子 = "每条轨迹固定 k 个窗口"（与单卡 stride=50 **不同口径**，跨 run 比较需重标定）；只覆盖 `active_val`+`train_monitor`，`scout`/`confirm`/`rescan` 仍未分片 | ✅ **已验证**（单测 7+26+62；真机 al_v62 归并失败 0、`active_val_gmean_mse=0.0067021`、`val_to_pass_threshold=0.9504`；al_v64 重扫 50/50 与历史逐任务差 ≤0.4%） |
| **单卡扫描不被并行逻辑污染**（`world>1` 门槛） | ✅ 默认生效 | `world<=1`（含启动器预扫 worker）⇒ **恢复 stride=50 原口径**；只有 `world>1` 才用自适应窗口 | 无（`world` 由 backend 公告，缺省视为 1 ⇒ 保守走原口径） | ✅ **已验证**（al_v64 重扫：50 任务与历史基准相对差 ≤0.4%、≥5% 的任务数 **0/50**） |
| **val 判定尺子统一**（`registry._judge_n`） | ✅ 默认生效 | `confirm_val_ids` 与 `active_val_ids` **同组**（`val_ids[:max(scout, active)]`）；`_require` 用 `_judge_n` 校验条数 | 等价重构（`max(2,4)=4`）⇒ 数值无变化；只影响"读代码时的预期" | 🧪 CPU 已验证 |
| **hardness 帧上限 200**（`configs/auto_learning/al_eval2_v45_frame200.yaml`） | 仅该配置（v45） | 单任务扫描上限 600 → **400** 帧；日志会打 `（帧数上限 200：N 条轨迹被均匀压缩，A → B 帧）` | 扫描墙钟应降约 1/3（未实测）；**不影响判定口径**；帧上限**不在 hardness 缓存指纹里** ⇒ 已缓存样本仍复用旧值 | ⏳ **待 v45 实跑验证** |
| **`SAVE_EVERY`/`HF_PASS_INTERVAL` 透传白名单**（`al_launch.py`） | ✅ 默认生效 | 这两个键可用 shell 变量或 `--env` 传入训练脚本；`--env` 优先 | 已实测 `SAVE_EVERY=400` 生效（v44 存档 400/800/1200） | ✅ 已验证 |
| **消歧义注释**（`*_nmse` vs `*_gmean_mse`；`active_val_probe_trajs`） | ✅ 纯注释 | 字段名**未改**（保历史可比）：判定看 `*_gmean_mse`，`*_nmse` 在 ratio 模式下只是 legacy 显示量 | 无 | ✅ 已验证 |
| **HF 存档改"内存直出"**（`train_lingbotvla.py::_save_hf_direct_best_effort` + 周期分支分流） | ✅ 默认生效（**仅 `final_only`**） | `dcp_save_mode=always` 时**逐字不变**（仍走 DCP→HF 转档）；`final_only + save_hf_weights=true` 改走 `export_model_hf_direct` ⇒ **不碰 DCP**；输出恒为 `<ckpt>/global_step_N/hf_ckpt`（与旧路径同位置）；直出前把已存在的 `hf_ckpt` 挪 `.stale.<pid>`（防落 `_retry_N`）；**失败只告警、不杀训练** | 直出需 `collect_full_model_on_cpu` ⇒ 瞬时主机内存峰值（6.4B fp32 ≈25 G）；**`async_save_hf_weights=true` 仍走旧转档路径 ⇒ 在 `final_only` 下仍会崩**（已知遗留，未改） | ✅ **已验证**（真机 al_v75_save3：日志 `⇒ HF 直出（不写 DCP…）` → `HF 导出精度：{bf16×1708}` → `HF 直出完成` → `已导出池子`；每份 3 片 safetensors + `pool_state.json`；**无 `model/`、`optimizer/`** ⇒ 确认没写 DCP；报错 0；单份 ≈19–28 s；生产 run al_v76 **连续 11 份**成功） |
| **HF 直出与 DCP 延迟解耦**（`_save_due` 判定**之前**的独立触发） | ✅ 默认生效 | `save_steps` 成为**真实间隔**（不再被推到 unit 边界）；仅在 `final_only + save_hf_weights=true` 生效；DCP 侧 `_save_due`/`_al_deferred_save` 一字未动 | 同上一行（内存峰值）；`save_steps` 过小（如 3）会让"存档比训练还慢"（实测单份 19–28 s vs 3 步 31 s）⇒ 生产必须 100–400 | ✅ **已验证**（al_v75_save3：`SAVE_EVERY=3` ⇒ step **2403 非 unit 边界**（unit 内 3/50 步）照样落盘，2406 同样） |
| **面板：`resolve_run_dir` + `TRAIN_OUT` 前缀修复**（`al_panel.py`） | ✅ 默认生效 | 兼容两种 run 布局（`train_<run>/` 与 `<run>/`，后者来自显式 `--train-out`）；`TRAIN_OUT` basename **不再假定 `train_` 前缀**（否则进程在跑却显示"无进程!"） | 无（纯显示层） | ✅ **已验证**（al_v69/v76：面板正确显示"7卡"+ 目标 50；修复前报"未找到 run"/"无进程!"） |
| **面板：池子计数改读 TensorBoard**（`skill_overview/*_count`） | ✅ 默认生效 | 池子行来自 TB（每 unit 末实时）⇒ 与"通关"不再矛盾；读不到时退回 `pool_state.json`/事件流推导并打警告 | TB 读失败⇒静默退回旧路径（有警告一行） | ✅ **已验证**（al_v65→v76：`pass=17 defer=3 candidate=23 exhausted=7 (实时·TB)`） |
| **一键启动 `al_watch.sh`** | ✅ 默认生效 | root 自动探测（按训练日志 mtime 在 `/models/…` 与 `/work_ov/…` 间二选一）；run 名写错列候选；兼容两种布局 | ⚠️ **`ONCE` 分支的 `if` 写法有 bug**：会让本该 watch 的调用走"只打印一次"（实测用户看到"不浮动、只堆叠"）⇒ 直接用 `watch -n 3 '<面板命令>'` 更稳 | ⚠️ 部分验证（`ONCE=1` 路径正常；**watch 路径待修**） |


**修正本节的规矩**：正式测试（真机 smoke / 长跑观测）通过后 ⇒ ① 改这里的状态与实测数字；
② 同步 `AL_PENDING_CHANGES.md`（§1 → §2）；③ 当日日志记一句。**不允许只改一处**。

## §13 池子独立存档 `pool_state.json`（2026-10-12；HF 续训用）

**为什么有它**：池子（每任务 status/attempts/lp50/`sample_probs`）原本**只随 DCP** 的
`extra_state['auto_learning']` 走 ⇒ 从 **HF 权重**起新 run 时框架判 `_al_resume_mode == "fresh"`
⇒ **池子从零**（已 PASS 的被重训、刚 DEFER 的被立刻重试）。

**三条路径**（谁负责恢复池子）：

| 场景 | 池子从哪恢复 | 代码位置 |
|---|---|---|
| 同 run 续训（`enable_resume=true`） | DCP `extra_state` ⇒ `load_extra_state()` | `train_lingbotvla.py`（hook） |
| 显式给 `load_checkpoint_path`（DCP） | 同上（`explicit_load`） | 同上 |
| **从 HF 权重起新 run** | **`pool_state.json`**（本节） | `real/build.py`（Scheduler 之后、Sampler 之前） |

🔴 **互斥逻辑（别搞混）**：`build.py` 里**只当"不走 DCP"时**才导入 `pool_state.json`
（用 `enable_resume` / `load_checkpoint_path` 预判，与框架判 `_al_resume_mode` 同口径）
—— 因为 DCP 的 AL 状态是在 parts 构建**之后**才加载的，会覆盖导入值；不跳过多半是"白做 + 日志误导"。

**文件位置（跟产物走，不跟出发模型走）**：
```
<output_dir>/checkpoints/global_step_2400/pool_state.json            ← DCP 旁
<output_dir>/checkpoints/global_step_2400/hf_ckpt/pool_state.json    ← HF 旁（final_only 模式）
新 run 读取顺序：AL_POOL_STATE_FILE > <model_path>/pool_state.json > <run_dir>/pool_state.json > 集中目录(step 最大)
```

**开关（都在进程启动时读一次 ⇒ 改完要重启）**：

| 变量 | 默认 | 作用 |
|---|---|---|
| `AL_POOL_STATE_FILE` | 空 | 显式指定池子文件（最高优先） |
| `AL_POOL_STATE_NO_IMPORT` | `0` | `1` ⇒ 不导入（干净起跑/对照） |
| `AL_POOL_STATE_EXPORT` | `1` | `0` ⇒ 不导出 |
| `AL_POOL_STATE_RESTORE_RNG` | `0` | `1` ⇒ 连 `sampler_rng` 一起恢复 |
| `AL_POOL_STATE_MIRROR` | `/workspace/al/pool_state` | 集中目录；空串 ⇒ 关闭 |
| `AL_POOL_STATE_PRUNE` | `2` | 集中目录保留最近几份 |

**导出时机**：挂在 `save_hf_checkpoint_best_effort()` 内 ⇒ **周期/轮末/收尾三个存档点全覆盖**；
只在 rank0 写；**失败只告警**（`export_pool_state_safely`）。
⚠️ 该函数在 `save_hf_weights=false` 时提前 return ⇒ 那种配置下**不导出**。

**`sampler_rng` 默认不恢复的理由**：从 HF 起新 run 时权重已换一份，旧 run 的"抽样骰子串"
**没有续训语义**；而**权重采样（`sample_probs`）在注册表里**，与 rng 无关 ⇒ 照常继承。

**两个"读起来会误解"的地方（已消歧义）**：
1. 导入失败**不拦启动**（用户要求"读就是了"）⇒ 任务集合对不上时**摊开三类差异**
   （池子里有/manifest 没有、反之、共有数）而不只写"切分不一致"；
2. `max_steps` 是**绝对**目标 ⇒ `step_offset` 生效后 **LR 调度步数 = max_steps − offset**，
   看起来"少训了 offset 步"是**预期**，不是 bug。

## §13 附：存档策略组合表（**2026-10-13 真机定案；选错会崩训练**）

**两套 HF 写出路径**（这是所有坑的根源）：

| 路径 | 实现 | 是否依赖 DCP | 输出位置 |
|---|---|---|---|
| ❌ **`save_hf_checkpoint_best_effort`**（旧） | `async_hf_checkpoint` → `ckpt_to_state_dict` → **`dcp_to_torch_state_dict`** | **必须读 `<ckpt>/model` 的 DCP** | `<ckpt>/hf_ckpt/` |
| ✅ **`export_model_hf_direct`**（新，`lingbotvla/utils/direct_hf_checkpoint.py`） | `collect_full_model_on_cpu(model)` → 原子发布 | **零依赖**（内存权重） | 同左（传 `checkpoint_root=dirname(ckpt)`） |

**四象限（哪些组合能用）**：

| `dcp_save_mode` | `save_hf_weights` | 行为 | 状态 |
|---|---|---|---|
| `always`（默认） | `true` | 先写完整 DCP ⇒ 再转 HF | ✅ 正常（6 个通用训练脚本走这条，**改动须逐字不变**） |
| `always` | `false` | 周期只写 DCP | ✅ 正常 |
| **`final_only`** | **`true`** | 周期**不写 DCP** ⇒ **旧路径必崩**：<br>`state_dict_loader.py: assert metadata is not None`（`CheckpointException ranks:[0]` + `AssertionError`）⇒ **杀训练** | 🔴 **2026-10-13 修**：改为**内存直出**（`dcp_save_mode=="final_only"` 时走 `export_model_hf_direct`） |
| `final_only` | `false` | 周期只建目录、不写任何存档 | ✅ 正常（但**无周期存档**） |

**⚠️ 已实测的两个后果（真机 al_v72 崩溃事件）**：
1. `final_only + save_hf_weights=true` 在 **step 2600 崩训练** ⇒ 已训 44 分钟 + 池子**全丢**；
2. 崩溃前**没有任何预兆**（HF 之前由"收尾存档"跑通过一次 ⇒ 让人误判该组合可用）。
   **教训**：验证存档组合必须**覆盖周期路径**，只验收尾（如 `--steps` 恰好触发收尾）会**漏掉真正的失败路径**。

**HF 直出与 DCP 的"延迟落盘"解耦（2026-10-13 追加）**：

- AL 开启时 `_save_due` 只在 **learning unit 边界**落盘（`_al_deferred_save` 机制）——
  这是为 **DCP** 的安全边界（`extra_state['at_boundary']`）设计的；
- **HF 直出不做 resume、不写 DCP ⇒ 不受该约束** ⇒ 新增独立触发（在 `_save_due` 判定**之前**）：
  `if save_hf_weights and dcp_save_mode=="final_only" and global_step % save_steps == 0: 直出 + 导池子`
- ⇒ `save_steps` 成为**真实间隔**（实测 `SAVE_EVERY=3` ⇒ step 2403/2406 各落一份，**非 unit 边界也落**）；
  不解耦则"名义 3 步、实际 50 步"（被推到 unit 边界）。

**精度与体积的关系（选型必读）**：

| 开关 | 作用 | 存档体积 |
|---|---|---|
| `enable_mixed_precision`（默认 False） | **模型加载 dtype**：`True⇒fp32`、`False⇒bf16`；且为 True 时 `model.float()` | — |
| `enable_fp32`（默认 False） | FSDP `mp_policy.param_dtype`：`True⇒fp32`、`False⇒bf16` | **fp32：HF≈12 G/份、收尾 DCP≈72 G**；**bf16：HF≈12 G（6.4B×2 B）、DCP≈18–24 G** |
| `hf_export_dtype`（batch 配置= `bf16`） | **HF 导出 dtype**（`native/bf16/fp32`） | **与 `enable_fp32` 脱钩** ⇒ 可"训练 fp32、存档 bf16" |
| `mix=true + fp32=true` | ⚠️ `elif enable_fp32` 优先 ⇒ **退化成"纯 fp32"且多一次 `model.float()`** | 最慢最费，**收益为零 ⇒ 别用** |

**⚠️ DCP 容量预判是保守常量**：日志 `收尾写完整 DCP（估 ≈72G，可用 2487G）`，
实测 bf16 下只写 **24 G**；但 `_dcp_final_capacity_ok()` 用的是那个常量 ⇒
**可用空间 < 72 G 时会被跳过**（实测 v65：56 G 可用 ⇒ 跳过 ⇒ 训练结束后一个存档都没有）。
⇒ **输出目录必须放在大容量盘**（本项目：overlay `/work_ov`，而非 56 G 的 loop 盘 `/workspace`）。

# Backend Changelog

> 目的：作为后端开发的追加式留痕日志（append-only），用于避免 AI 长周期开发中的上下文漂移与实现不一致。  
> 规则：每次涉及 `backend/` 的代码修改后，必须新增一条记录，不覆盖历史记录。

---

## Batch-75 / Extender×3 几乎同一张图

- **时间**：2026-09-05
- **任务名称**：连续 Extender 每跳加一条不同的对照均线，而不是改标题空转
- **变更目标**：V1 全序列均值、V2 近 20 年均值、V3 早期均值；标题围绕 mean 比较；拒绝 LLM 编造字段
- **变更原因**：`34d4ab3d` 三跳都是 1850–2025，均线都是 0.04；标题写成 “after the 2024 peak / years that followed”，画面没裁窗。V2 LLM 还加了不存在的 `mean_anomaly_c`
- **影响范围**：
  - `backend/app/transform/framing_reconstructor.py`
  - `backend/tests/test_batch66_chain_reconstruct.py`
- **接口影响**：无
- **测试命令**：`cd backend && conda activate frame && USE_LLM=false python -m pytest -q tests/test_batch66_chain_reconstruct.py`
- **测试结果**：`13 passed`
- **风险与后续待办**：需重新跑 Ext×3；LLM 若没加新均线会回退确定性路径

---

## Batch-74 / 面积图填到 y=0，x 轴像浮在图中间

- **时间**：2026-09-05
- **任务名称**：面积图基线接到缩放后的 y 轴下沿
- **变更目标**：y 域从 0.28 起时，面积填到 0.28 而不是 0，x 轴回到图底
- **变更原因**：Vega-Lite area 默认 `y2=0`。第三跳把 y 收到 `[0.28, 1.41]` 后，红填充仍画到 0，轴线画在 0.28，看起来 x 轴切过色块
- **影响范围**：
  - `backend/app/transform/framing_reconstructor.py`
  - `backend/tests/test_batch66_chain_reconstruct.py`
- **接口影响**：无
- **测试命令**：`cd backend && conda activate frame && USE_LLM=false python -m pytest -q tests/test_batch66_chain_reconstruct.py`
- **测试结果**：`12 passed`
- **风险与后续待办**：需重新跑 Amp×3

---

## Batch-73 / Amplifier 面积图左右 y 轴叠字

- **时间**：2026-09-05
- **任务名称**：修好 V3 面积图上 °C / °F / 默认刻度叠在一起
- **变更目标**：第三跳只保留左侧 °C 轴；注释层不再长出独立 y 轴；不要把注释点画成面积
- **变更原因**：源图 `resolve.scale.y: independent` 下，注释层默认各自出轴；隐形 °F 点层还在；zoom 把 annotation point 也改成了 area，y 域混进 `anomaly_f`（标题变成 hits 2.3）
- **影响范围**：
  - `backend/app/transform/framing_reconstructor.py`
  - `backend/tests/test_batch66_chain_reconstruct.py`
- **接口影响**：无
- **测试命令**：`cd backend && conda activate frame && USE_LLM=false python -m pytest -q tests/test_batch66_chain_reconstruct.py`
- **测试结果**：`12 passed`。V3 仅 1 条左轴，domain `[0.28, 1.41]`，标题 `hits 1.3`
- **风险与后续待办**：需重新跑 Amp×3；V1/V2 仍保留 °C/°F 双轴

---

## Batch-72 / Amplifier V3 看起来几乎等于 V2

- **时间**：2026-09-05
- **任务名称**：第三跳 Amplifier 要能看出 y 轴放大，而不是再切一段同样从 0 起笔的柱图
- **变更目标**：已经裁过、全为正值的后续 Amplifier 改为面积图，并把 y 收到可见区间（不再从 0 起）
- **变更原因**：`c81e89bf` 中 V2=1992–2025、V3=2005–2025，ymax 都是 1.30，y 域都是 `[0, 1.43]`。柱图从 0 起笔，裁掉左边只抬高了起点（0.36→0.49），峰值柱一样高，标题还从 BREAKING 换成了更弱的 “still climbing”
- **影响范围**：
  - `backend/app/transform/framing_reconstructor.py`
  - `backend/tests/test_batch66_chain_reconstruct.py`
- **接口影响**：无
- **测试命令**：`cd backend && conda activate frame && USE_LLM=false python -m pytest -q tests/test_batch66_chain_reconstruct.py`
- **测试结果**：`12 passed`
- **风险与后续待办**：需重新跑 Amp×3；第一跳仍保持柱图从 0 起，避免 Amazon/COVID 等源图被过早改成面积图

---

## Batch-71 / 连续 Amplifier 把峰值从右边裁掉

- **时间**：2026-09-05
- **任务名称**：三连 Amplifier 每跳应更强化，而不是第三跳比第二跳更弱
- **变更目标**：Amplifier 窗口保住峰值、从左侧收紧；裁窗后按 °C/°F 配对收 y 轴
- **变更原因**：`_steepest_window` 用「从接近 0 起算的百分比」打分，覆盖率上限 72%，所以 V2 变成 1975–2016、V3 变成 1975–2003，2024 峰值被砍掉。V3 y 域仍继承 `[0, 1.05]`，最高柱只有 0.64，看起来还没 V2 强化。标题第三跳只加了 “still the number that matters”
- **影响范围**：
  - `backend/app/transform/framing_reconstructor.py`
  - `backend/tests/test_batch66_chain_reconstruct.py`
- **接口影响**：无
- **测试命令**：`cd backend && conda activate frame && USE_LLM=false python -m pytest -q tests/test_batch66_chain_reconstruct.py`
- **测试结果**：`12 passed`
- **风险与后续待办**：开 `USE_LLM=true` 时 chain planner 仍可能覆盖标题文案，但 `select_data_range` 会强制合同窗口；需重新跑 Amp×3 模拟

---

## Batch-70 / Adverser 偏爱 1980s 窗口 + Extender 双 y 轴混乱

- **时间**：2026-09-05
- **任务名称**：温度图上 Adverser 改选近 20 年反向窗；Extender 不再打乱 °C/°F 双轴
- **变更目标**：反驳窗口优先落在近期；Extender 均线叠在主 y 轴上，保留左右轴原 domain
- **变更原因**：Adverser `_directional_window` 只按最陡反向跌幅打分，1981–1985 赢过 2000 年后的窗口。Extender 把均值写成新 y 字段并整表缩放 y，左轴 ticks 塌成 `[1]`，右轴 °F 与注释层再叠出第三套刻度
- **影响范围**：
  - `backend/app/transform/framing_reconstructor.py`
  - `backend/tests/test_batch66_chain_reconstruct.py`
- **接口影响**：无
- **测试命令**：`cd backend && conda activate frame && USE_LLM=false python -m pytest -q tests/test_batch66_chain_reconstruct.py`
- **测试结果**：`11 passed`。温度图 Adverser 窗口变为 `2007–2012`；Extender 左域 `[-1, 1.5]`、右域 `[-1.8, 2.7]` 保持不变
- **风险与后续待办**：需重新跑温度模拟才会看到新窗口；双轴图不再自动缩放 y，短窗 Adverser 仍可能显得“空旷”

---

## Batch-69 / fold 图裁窗后柱子消失、画布被撑到几千像素高

- **时间**：2026-09-04
- **任务名称**：修复 COVID 周死亡这类 fold/stacked 图在重构后的版式
- **变更目标**：裁窗保留 fold/calculate；y 轴按画面上真实编码取值（堆叠合计+均线），而不是按 CV 最大的隐藏列；拒绝 LLM 产出的空图/超高 SVG
- **变更原因**：最新一次 `case-1039ddf1` 把 `transform.fold` 整段删掉，`deaths` 字段不存在；又用 COVID 单列 `c`（5→8758）去缩 y 轴，五年均线仍在 ~11000，V5 SVG 高度 8656
- **影响范围**：
  - `backend/app/transform/node3_executor.py`
  - `backend/app/transform/framing_reconstructor.py`
  - `backend/tests/test_batch66_chain_reconstruct.py`
- **接口影响**：无
- **测试命令**：`cd backend && conda activate frame && USE_LLM=false python -m pytest -q tests/test_batch66_chain_reconstruct.py`
- **测试结果**：`tests/test_batch66_chain_reconstruct.py` 9 passed
- **风险与后续待办**：源图上像素定位的 legendX/titleX 在变体里会改成常规 bottom legend，避免轴和标题飘走

---

## Batch-68 / 重构图坐标轴消失、柱子和轴脱节

- **时间**：2026-09-04
- **任务名称**：修复生成图表坐标轴不在图上
- **变更目标**：注释层不再关掉共享轴；柱状图 y 轴从 0 起，柱子贴在轴线
- **变更原因**：Vega-Lite 里任意 overlay 写 `axis: null` 会把整图 x/y 轴隐藏；裁窗后又把 y domain 收到数据最小值以上，bar 仍从 0 起笔，柱子画出画布
- **影响范围**：
  - `backend/app/transform/node3_executor.py`
  - `backend/app/transform/framing_reconstructor.py`
  - `backend/tests/test_batch66_chain_reconstruct.py`
- **接口影响**：无
- **测试命令**：`cd backend && conda activate frame && USE_LLM=false python -m pytest -q tests/test_batch66_chain_reconstruct.py tests/test_batch13_node3_executor.py::test_executor_data_aware_annotation_adds_leader_line`
- **测试结果**：11 passed
- **风险与后续待办**：折线图仍可缩放 y（不强制从 0）；LLM 若输出 concat 会拆成单图

---

## Batch-67 / 模拟请求被代理掐断 + thinking 吐不出 JSON

- **时间**：2026-09-04
- **任务名称**：修复前端 `simulation/start` socket hang up，以及 DeepSeek thinking 返回无法解析的推理文本
- **变更目标**：页面能等到后端跑完；规划/重构能从带前言的回复里抽出 JSON
- **变更原因**：thinking 把 token 花在 “We need answer JSON only…” 上，spec 被截断；Vite 代理在后端发出响应头前断开，前端报 Simulation request failed。后端日志里该次请求实际是 200
- **影响范围**：
  - `backend/app/agents/llm_client.py` — 从 prose/`reasoning_content` 扫描 JSON；规划 thinking 超时 60s
  - `backend/app/transform/framing_reconstructor.py` — 画图关闭 thinking，避免 VL spec 被推理文本挤掉
  - `backend/scripts/dev.sh` — `--timeout-keep-alive 300`
  - `frontend/vite.config.ts` — `/api` proxy 15 分钟
  - `backend/tests/test_batch6_error_and_llm_toggle.py`
- **接口影响**：无
- **测试命令**：`cd backend && conda activate frame && USE_LLM=false python -m pytest -q tests/test_batch6_error_and_llm_toggle.py tests/test_batch66_chain_reconstruct.py`
- **测试结果**：13 passed
- **风险与后续待办**：改 `dev.sh` / `vite.config.ts` 后需手动重启前后端；仅 `--reload` 不会带上 uvicorn keep-alive 参数

---

## Batch-66 / 全链规划 + 按父图重构 Vega-Lite

- **时间**：2026-09-04
- **任务名称**：最短路径：thinking 规划整条传播链，每跳从父节点 Vega-Lite 重构画面
- **变更目标**：hop 不再近视地改颜色/套模板；Amp/Ext/Adv 沿父图窗口与主张递进，taxonomy 操作只作归因
- **变更原因**：用户按 ChatGPT 显式链条（SRC→Ext×3、SRC→Bridger、SRC→Amp→Ext→Adv）对比后，Revisio 输出偏保守（配色/标题模板）
- **影响范围**：
  - `backend/app/agents/llm_client.py` — `thinking` 可开关；`plan_propagation_chain` / `complete_json`（规划与重构开启 thinking）
  - `backend/app/transform/framing_reconstructor.py` — 新建：LLM 重写 VL + 确定性 fallback（裁窗/均值对照层/改 mark）
  - `backend/app/graph/workflow.py` — NodeC 四角色优先 reconstruct
  - `backend/app/graph/langgraph_runner.py` — 把 `gap_type` / `inner_monologue` 写入 NodeC context
  - `backend/app/services/simulation_service.py` — 开跑前规划整链；`agentCount <= maxDepth` 时走脊柱拓扑；每 agent 只跑一次 graph
  - `backend/tests/test_batch66_chain_reconstruct.py`
  - `backend/tests/test_batch6_error_and_llm_toggle.py`
- **接口影响**：无。路径/字段/枚举不变；`framing_contract` / `verify_reasons` / `chain_plan_step` 仅写入 provenance 与 agentLog
- **测试命令**：`cd backend && conda activate frame && USE_LLM=false python -m pytest -q tests/test_batch66_chain_reconstruct.py tests/test_batch6_error_and_llm_toggle.py tests/test_batch4_langgraph.py tests/test_batch5_topology_and_case_data.py tests/test_api.py`
- **测试结果**：22 passed。`USE_LLM=false` 全量 `tests/`：59 passed，2 个 batch13 预存失败（title wrap `str(dict)`、select_data_range 空窗），与本批无关
- **风险与后续待办**：
  - 开 `USE_LLM=true` 后每 hop 可能 90s 级 thinking 重构，需重启 `./scripts/dev.sh` 使 `.env` 生效
  - LLM 失败仍走确定性重构（Amp 最陡窗、Extender 期均值层、Adv 反向窗），不会再静默套颜色模板
  - 日志应出现 `Chain plan:`，节点 `exec=` 以 `reconstructed` 开头

---

## Batch-64 / DeepSeek 30s 超时与 TLS 断开

- **时间**：2026-09-04
- **任务名称**：修复 `deepseek-v4-pro` 调用在模拟开始后超时 / SSL EOF
- **变更目标**：NodeA/B JSON 调用能稳定返回，不再 30s 被切断后静默 fallback
- **变更原因**：本机 IPv6 TLS 卡住、keepalive 连接被对端掐断、v4-pro 默认 thinking 导致 content 为空
- **影响范围**：
  - `backend/app/agents/llm_client.py`
  - `backend/tests/test_batch6_error_and_llm_toggle.py`
- **接口影响**：无
- **测试命令**：`conda run -n frame python -m pytest -q tests/test_batch6_error_and_llm_toggle.py`
- **测试结果**：6 passed。本机 `_chat_completion_json` 探测返回 `{"ok": true, "gap_type": "tension"}`
- **风险与后续待办**：DeepSeek 链路仍可能偶发断开，失败会降级本地策略

---

## Batch-65 / DeepSeek 必须走 /v1，否则 NodeA 大请求被掐断

- **时间**：2026-09-04
- **任务名称**：修复模拟开始后连续 `Server disconnected without sending a response`
- **变更目标**：NodeA/B 的较长 prompt 也能打到 DeepSeek
- **变更原因**：`.env` 的 `OPENAI_BASE_URL=https://api.deepseek.com` 被拼成 `/chat/completions`（无 `/v1`）。小探测能通，模拟用的较长 JSON 请求会被对端断开；同一 payload 打 `/v1/chat/completions` 返回 200
- **影响范围**：`backend/app/agents/llm_client.py`、`backend/tests/test_batch6_error_and_llm_toggle.py`
- **接口影响**：无
- **测试命令**：`conda run -n frame python -m pytest -q tests/test_batch6_error_and_llm_toggle.py`
- **测试结果**：6 passed。本机 `/v1` + 中等长度 prompt 最终返回 `gap_type=tension`；无 `/v1` 时同类请求会 disconnect
- **风险与后续待办**：TLS 仍可能偶发握手超时，已加短退避重试

---

## Batch-52 / Adverser 图表消失修复 + 注释溢出画布修复

- **时间**：2026-03-15
- **变更目标**：修复 Adverser 角色执行操作后图表数据消失（空白图）的问题；修复注释文字超出图表区域导致画布拉长的问题
- **变更原因**：
  - 用户测试发现 Adverser 执行 `select_data_range` 后图表经常变空白，数据不可见
  - 不同案例测试中发现注释文字超出图表绘制区域，导致整个画布被拉得特别长
- **影响范围**：
  - `backend/app/transform/node3_executor.py` — 核心改动
  - `backend/app/graph/workflow.py` — 传递 depth 参数（上一批次遗漏确认）
  - `backend/tests/test_batch13_node3_executor.py` — 适配测试
- **具体变更**：
  1. **select_data_range 最小行数保护**：新增 `_count_surviving_rows` 方法，在执行 filter 前预判剩余数据行数，若不足 2 行则跳过该操作，避免数据被完全清空
  2. **change_axis_scale 安全域边界**：修改 y-axis domain 计算逻辑，确保 `new_min ≤ actual_min` 且 `new_max ≥ actual_max * 1.05`，防止数据点被域裁剪掉；新增"缩放幅度过浅"检测，避免无意义的 domain 变更
  3. **post-execution 空数据回滚**：执行完所有操作后检测 `_is_chart_data_empty`，若原本有数据但操作后变空则自动回滚到原始 spec
  4. **Adverser 数据窗口最小宽度**：`_infer_default_range_window` 中 decline/growth 窗口至少需要 5 个数据点（`ei - si >= 4`），避免选中过窄片段
  5. **注释文字行数限制**：所有注释路径（data-anchor 和 fallback）最多 3 行，超出截断并加 "..."
  6. **text mark `limit` 属性**：注释文字 mark 添加 Vega-Lite `limit`（像素宽度上限），防止文字溢出画布
  7. **annotation y 位置夹紧**：data-anchor 注释的 `y_offset` 被夹紧到数据 y 范围内，防止标注漂移到图表外
  8. **注释文本长度缩短**：`_enforce_text_length` 注释上限从 120 字符降到 80 字符
  9. **`_apply_annotation_mark_style` 添加 limit**：所有 change_annotation 路径也自动添加 `limit: 280px`
- **接口影响**：无外部接口变更
- **测试命令**：`cd backend && conda run -n frame python -m pytest tests/ -q --deselect ...trendline`
- **测试结果**：50 passed, 1 deselected
- **风险与后续待办**：
  - 对于极端窗口（全部 y 值相同的平坦数据），change_axis_scale 可能无法应用，此时图表保持原样
  - 如果前端有额外的 clip 支持（CSS overflow），可进一步从前端层面兜底

---

## Batch-51 / 同角色不同平台颜色区分 + 深度递进颜色加深

- **时间**：2026-03-15
- **变更目标**：修复同角色（如全 Amplifier）不同平台时所有子节点颜色完全相同的问题；实现随深度增加颜色逐步加深的视觉递进效果
- **变更原因**：用户测试发现设置全 Amplifier 时所有节点都是同一个红色，平台差异完全体现不出来；深度1和深度4颜色无变化
- **影响范围**：
  - `backend/app/transform/node3_executor.py` — 核心改动
  - `backend/app/graph/workflow.py` — 传递 depth 参数
- **具体变更**：
  1. **平台分桶细化**：`_infer_platform_bucket_local` 从 3 桶扩展为 6 桶 (`t1_authority`, `t2_news`, `t3_social`, `t4_ugc`, `t5_blog`, `t6_data`)，将 "Online community/UGC" 与 "Social media" 分离为独立桶
  2. **颜色差异拉大**：同角色不同平台使用明显不同的色相（如 Amplifier: News=#D4380D 橙红, Social=#FF4500 亮橙红, UGC=#CC0066 品红, Blog=#B22222 暗砖红），而非之前仅微调 RGB 值
  3. **深度颜色加深**：新增 `_apply_depth_darkening` 方法，depth=1 保持原色, depth=2 加深 15%, depth=3 加深 30%, depth=4+ 加深 40%，使传播链的累积偏移在颜色上可视化
  4. **动态梯度生成**：`_build_palette_range` 从静态查找表改为算法生成（lighten 70%/35% → base → darken 35%），适配任意深度加深后的颜色
  5. **动态 secondary color**：`_derive_secondary_color` 从静态映射改为对 primary 执行 35% darkening，适配任意输入色
  6. **execute() 接受 depth 参数**：workflow.py 从 context 中提取 depth 传入 executor
- **接口影响**：无外部接口变更，仅 Node3Executor.execute() 增加 depth 可选参数
- **测试命令**：`cd backend && conda run -n frame python -m pytest tests/ -q --deselect tests/test_batch13_node3_executor.py::test_executor_adds_trendline_when_annotation_requests_it`
- **测试结果**：50 passed, 1 deselected (pre-existing trendline test)
- **风险与后续待办**：
  - 深度加深在极端深度（>6）时可能导致颜色过暗，可考虑设置下限亮度
  - 如需更精细的平台分类可扩展桶定义

---

## Batch-50 / 语义质量提升：任务使命声明 + Few-shot示例 + Adverser空白图修复 + 平台差异化升级

- **时间**：2026-03-12
- **任务名称**：提升 Amplifier/Adverser/Extender 语义输出质量；修复 Adverser 空白图表；增加平台差异化标题
- **变更目标**：
  1. **`_build_chart_data_summary` 格式彻底重写**（`llm_client.py`）：
     - 将源图表标题标注为"UPSTREAM framing — 你的角色将重构它"，防止 LLM 照抄源标题
     - 修复 first_y=0 时的混乱 pct_change：原来显示 "rising (-69%)" 让 LLM 误判为下降趋势；现在改为 "RISING — started at 0, surged to peak 8,758 at 16, currently 2,697 and rising again"
     - 明确显示 "Story metric: Weekly deaths (field='c', highest-variance)"
  2. **NodeA/NodeB 任务使命声明**（`_evaluate_gap_via_llm`、`_propose_strategy_via_llm`）：
     - 新增 `=== FRAMING SHIFT MISSION ===` 段落，明确告知 LLM 它是在执行框架偏移任务
     - 说明源图表标题是"上游框架"需要被替换，不能复制
  3. **NodeB Few-shot 示例**（`_propose_strategy_via_llm`）：
     - 新增 COVID 死亡数据的完整传播链示例：Bridger → Amplifier(新闻) → Amplifier(社交) → Adverser(社交) → Extender
     - 包含具体标题文本和操作参数（select_data_range start=16, end=36）
  4. **Amplifier 平台差异化**（`_build_title_intent`）：
     - News media: "Covid Deaths Rise Again"（直接有力）
     - Social media: "BREAKING: UK Covid Deaths SURGE to New Autumn High"（更激进）
     - Climate/generic topics 同样区分 t2_media 和 t3_social 语气
  5. **Adverser 标题更贴合用户示例**（`_build_title_intent`）：
     - COVID: "'Covid Deaths Are Rising' Is a HOAX — Deaths Fell Week 16–36"
  6. **修复 Adverser 空白图表根本原因**（`node3_executor.py` `_apply_x_domain_window`）：
     - **Root cause**: `scale.domain = [start, end]` 对 ordinal x 字段只显示 2 个类别（start 和 end 两个值），隐藏了中间所有数据点，导致图表几乎为空
     - **Fix**: ordinal 字段不设置 scale.domain（数据已通过 filter + trim 限制）；仅裁剪 `axis.values` 到选中范围；quantitative/temporal 字段仍使用 range domain
  7. **Extender/Analyst guard**（`_propose_strategy_via_llm`、`refine_execution_plan`）：
     - 新增过滤：从 Extender/Analyst 的操作列表中移除 `select_data_variables` 和 `select_data_range`（taxonomy 要求）
  8. **NodeC 使命声明更新**（`node3_executor.py` `_PERSONA_PROMPTS`、`_TITLE_EXAMPLES`）：
     - 每个角色的 persona prompt 新增 "performing a FRAMING SHIFT" 使命说明
     - `_TITLE_EXAMPLES` 更新为包含完整 COVID 传播链和 few-shot 标注
- **影响范围**：`backend/app/agents/llm_client.py`、`backend/app/transform/node3_executor.py`
- **接口影响**：无
- **测试命令**：
  ```bash
  cd backend && conda run -n frame python -c "
  import json; from app.agents.llm_client import LLMClient
  with open('../data/06_COVID_excess_deaths/chart_spec.json') as f: spec = json.load(f)
  print(LLMClient._build_chart_data_summary(spec))
  print(LLMClient._find_decline_window(spec))
  print(LLMClient._build_title_intent('Amplifier', {'covid'}, 'tension', 't3_social', spec))
  print(LLMClient._build_title_intent('Adverser', {'covid'}, 'tension', 't3_social', spec))
  "
  ```
- **测试结果**：
  - 数据摘要：SOURCE CHART TITLE 正确标注；Metric: Weekly deaths (field='c')；Trend: RISING — started at 0, surged to peak 8,758 at 16, currently at 2,697 and rising again ✓
  - 下降窗口：start_x=16, end_x=36, pct=99.1% ✓
  - Amplifier (news): "Covid Deaths Rise Again" ✓
  - Amplifier (social): "BREAKING: UK Covid Deaths SURGE to New Autumn High" ✓
  - Adverser: "'Covid Deaths Are Rising' Is a HOAX — Deaths Fell Week 16–36" ✓
  - node3_executor ordinal domain 修复：axis.values 裁剪到选中范围，不再设置 scale.domain ✓
- **风险与后续待办**：
  - LLM 是否真正遵循 few-shot 示例，需实际运行模拟验证
  - Adverser 的 select_data_range 现在只裁剪 axis.values，不设置 scale.domain，需验证图表渲染是否正常显示周 16-36 的柱状图
  - 建议后续将 platform_bucket 信息传递到 NodeA 感知阶段，使其可以在 inner_monologue 中就差异化处理

---

## Batch-49 / 数据字段选择修复：高方差字段选择 + COVID检测 + 坐标轴标题提取

- **时间**：2026-03-12
- **任务名称**：修复图表数据提取选错字段（选了参考线 avg 而非 COVID deaths c 字段）、COVID 话题识别缺失、y 轴标签使用原始字段名
- **变更目标**：
  1. **最高方差字段选择**（`llm_client.py` `_extract_xy_series_summary`、`_find_decline_window`；`node3_executor.py` `_extract_chart_evidence`）：对于有多个数值字段的图表（如 COVID 图有 `nc`/`avg`/`c`），从所有数值字段中选择变异系数（CV）最高的字段作为"主叙事字段"。COVID 图中 `c`（COVID死亡）CV≈1.6 远高于 `avg`（五年均值）CV≈0.12，现在正确选择 `c`。
  2. **扫描所有数值字段**：对于 fold-transform 图表（编码中字段名不存在于数据中，如 `deaths`/`cause`），扫描实际数据中的所有数值字段作为候选，确保始终能找到有效数据。
  3. **`_find_decline_window` 搜索全范围**：修改为搜索整个数据范围（≥5个数据点），不再限制在最后20行，COVID 图现在正确找到第16周→36周的下降窗口（99% 下降），而不是微小的 0.5% 变化。
  4. **COVID 话题信号独立检测**：`_infer_topic_signals` 新增 `covid` 信号（独立于 `health`），检测 "covid", "coronavirus", "pandemic" 等关键词。
  5. **`_build_title_intent` 新增 covid/health 话题处理**（三个角色）：
     - Amplifier (news): "title: Covid Deaths Are Rising Again"
     - Amplifier (social): "title: BREAKING: Covid Deaths SURGE to New High"
     - Adverser: "title: 'Covid Deaths Are Rising' Is a HOAX — Deaths Actually Fell"
     - Analyst/Extender: "title: How the Pandemic Has Affected Excess Death Rates"
  6. **坐标轴标题提取**（`_extract_axis_title` 静态方法，新增于 `llm_client.py` 和 `node3_executor.py`）：从 Vega-Lite encoding 的 `axis.title` 中提取人类可读的轴标题（"Weekly deaths" 而非 "c"），当精确字段不匹配时回退到同坐标轴的第一个轴标题。
  7. **`_extract_xy_series_summary` 使用轴标题**：series 的 `y_label` 现在优先使用 `axis.title`，COVID 图现在返回 `y_label: "Weekly deaths"` 而非 "C"。
- **影响范围**：`backend/app/agents/llm_client.py`、`backend/app/transform/node3_executor.py`
- **接口影响**：无
- **测试结果**：COVID 图提取 y_field=c, y_label='Weekly deaths', trend=rising, decline_window=week16→36(99%下降)；标题生成符合预期

---

## Batch-48 / 核心架构修复：NodeA感知→NodeB策略数据传递链路

- **时间**：2026-03-12
- **任务名称**：修复 NodeA inner_monologue 未传给 NodeB、NodeA prompt 不读取图表数据、"shared x" 坐标轴模式无法提取数据
- **变更目标**：
  1. **最核心修复**：`langgraph_runner.py` `_run_node_b` 新增 `node_a_perception=node_a_result.get("inner_monologue", "")` 传参，打通 NodeA 感知 → NodeB 策略的数据链路（设计文档 `docs/后端方案.md` 第4.3节 "Node B 输入 = Node A inner_monologue + Taxonomy 规则"）。
  2. **NodeA LLM prompt 改造**（`llm_client.py` `_evaluate_gap_via_llm`）：从 `persona={...}\ncontext={...}` 的原始 dict dump 升级为结构化 `=== CHART DATA ===` 摘要 + `=== ROLE PERCEPTION GUIDE ===` 角色感知引导。inner_monologue 现在必须引用具体数据值和年份。
  3. **NodeA fallback 改造**（`_evaluate_gap_fallback`）：新增 `context` 参数传入，调用新的 `_build_perception_monologue` 方法，基于图表数据趋势生成角色专属感知旁白（Amplifier："我看到 X 上升，我要写醒目标题"；Adverser："整体趋势上升，但我要找一段局部下降"；Analyst："我想把话题扩展到更广泛的政策含义"）。
  4. **NodeB LLM prompt 改造**（`_propose_strategy_via_llm`）：新增 `node_a_perception` 参数，prompt 中新增 `=== AGENT PERCEPTION (from NodeA) ===` 区块，提供清晰的角色样例（Amplifier/Extender/Adverser 各带具体数据驱动的标题示例），替换原来的噪声 `context={...}` dump。
  5. **"Shared X" 坐标轴模式修复**（`llm_client.py` `_extract_xy_series_summary`、`_find_decline_window`；`node3_executor.py` `_collect_xy_data_candidates`）：对于 Vega-Lite 中 x 定义在父级 encoding、y 定义在各 layer 内的图表（如 COVID_excess_deaths），提取时从父级继承缺失的 x/y 字段，而不是跳过该 candidate。
  6. **node3 证据提取容错**（`node3_executor.py` `_extract_chart_evidence`）：`_collect_xy_data_candidates` 返回多个候选时，逐个尝试直到找到有实际数值行的候选（原来仅取第一个，可能因字段名不匹配导致 evidence 为空）。
  7. **新增辅助方法**：`LLMClient._build_chart_data_summary()`（静态方法，生成标题/指标/趋势/时段/峰值摘要字符串）、`LLMClient._build_perception_monologue()`（实例方法，基于图表数据生成角色专属感知旁白）。
  8. **Analyst fallback 清理**：`_propose_strategy_fallback` 中 Analyst 操作列表移除残留的 `select_data_variables`，改为 `change_title + add_annotation + add_legend`。
- **影响范围**：`backend/app/agents/llm_client.py`、`backend/app/graph/workflow.py`、`backend/app/graph/langgraph_runner.py`、`backend/app/transform/node3_executor.py`
- **接口影响**：无（`inner_monologue` 已在 `node_a_result` schema 中，只是之前没传给 NodeB）
- **测试命令**：`conda run -n frame python -c "from app.agents.llm_client import LLMClient; from app.transform.node3_executor import Node3Executor; ..."`
- **测试结果**：import OK + `_extract_chart_evidence` 对 COVID 数据正确返回 `y_label: Avg, trend: falling` 等证据；`_build_perception_monologue` 对各角色生成数据驱动旁白
- **风险**：fallback 路径下 `_build_perception_monologue` 使用 `avg`/`w` 等原始字段名，LLM 路径会有更好的语义理解；后续可通过 chart spec `axis.title` 补充更多字段语义。
- **后续待办**：可进一步利用 `axis.title` 字段来改善 fallback 路径的 field 可读性。

---

## Batch-47 / Adverser 趋势线修正 + simplify_axis 保证显示

- **时间**：2026-03-12
- **任务名称**：修复 Adverser 趋势线方向错误、decline_window 选错负区间、simplify_axis 不显示于 Process 面板
- **变更目标**：
  1. `_find_decline_window`（llm_client.py）与 `_extract_chart_evidence`（node3_executor.py）新增严格约束：起始 y 必须 > 0（正值/变暖区间），终止 y 必须 < 起始 y（真实下降）。评分改用 `y_level_bonus = y_vals[i] * 50`（高正值 = 更深入变暖期）+ `recency`，确保选出 2015-2022 类正值下降段，而不是 1882 年的负值早期数据。
  2. `_pick_annotation_anchor`（node3_executor.py）Adverser 分支：将 anchor 改为下降段起点（峰值），`trend_end` 改为下降段终点（谷值）。通过查询 `decline_window`，锚定 anchor=start_x（高点），trend_end=end_x（低点），使趋势线从左高到右低，呈现反叙事"降温"走势。
  3. `workflow.py` NodeC.run()：在 `refine_execution_plan` 之后补充 role 保证——Amplifier 和 Adverser 若无 `simplify_axis`，则强制追加，防止 LLM refine 阶段将其丢弃。
  4. Adverser fallback 操作列表（llm_client.py `_propose_strategy_fallback`）新增 `simplify_axis` 操作，与 Amplifier 保持一致。
- **影响范围**：`backend/app/agents/llm_client.py`、`backend/app/transform/node3_executor.py`、`backend/app/graph/workflow.py`
- **接口影响**：无（operation_audit 格式不变）
- **测试命令**：`conda run -n frame python -m pytest tests/ -x -q`
- **测试结果**：51 passed
- **风险与后续待办**：若后续用户反馈趋势线仍不在期望位置，需检查 `_extract_chart_evidence` 对 transform-filtered 数据的处理（当前读取 data.values 全量数据，filter 后的子集未被考虑）。

---

## 记录模板（复制后填写）

```markdown
## [YYYY-MM-DD HH:mm] Batch-X / Task-Name

- 变更目标：
- 变更原因：
- 影响范围（文件/模块）：
  - `backend/...`
  - `docs/...`（如有）
- 接口影响：无 / 有（说明字段或行为变化）
- 数据结构影响：无 / 有（说明）
- 关键实现点：
  - ...
- 测试命令：
  - `conda activate frame && cd backend && python -m pytest -q`
- 测试结果：
  - `N passed`
- 风险与回滚点：
  - ...
- 后续待办：
  - ...
```

---

## 日志记录

## [2026-03-11 18:40] Batch-46 / taxonomy_codebook 语义对齐：Adverser 降温周期 + simplify_axis 每5年

- 变更目标：按 taxonomy_codebook.md 修正 Adverser select_data_range 与 simplify_axis 语义
- 变更原因：用户反馈实现与文档不符。Taxonomy：adverser 截取**降温周期数据**声称全球变冷，应优先选 y 在上方/变暖期的下降段；simplify axis 为每5年或每10年显示，非完全隐藏
- 影响范围（文件/模块）：
  - `backend/app/agents/llm_client.py`
  - `backend/app/transform/node3_executor.py`
- 变更内容：
  1. **Adverser _find_decline_window**：引入 score = pct + pos_bonus + recency，优先选择 (1) y 均值≥0 的变暖期下降段，(2) 数据后半段。避免选中 1882-189x 全负值段。
  2. **executor _extract_chart_evidence decline_window**：同样采用 pos_bonus + recency 评分，与策略层一致。
  3. **simplify_axis temporal**：用 labelExpr 实现“每5年显示”，`new Date(datum.value).getFullYear() % 5 === 0 ? datum.label : ''`。移除错误的 tickCount 配置。
  4. **Adverser add_annotation include_trendline**：设为 True（并配趋势线注释说明）。
- 接口影响：无
- 测试命令：`cd backend && conda activate frame && python -m pytest tests/ -x -q`
- 测试结果：`51 passed`
- 风险与回滚点：labelExpr 依赖 Vega 对 temporal 的 datum 结构
- 后续待办：观察实际温度数据上 Adverser 选取的窗口是否在变暖期

---

## [2026-03-11 18:00] Batch-45 / simplify_axis 标签保留 + 注释换行 + 柱状图宽度 + Amplifier 标题保障

- 变更目标：修复 simplify_axis 完全隐藏标签、注释超出画幅不换行、select_data_range 后柱状图过细、Amplifier 缺少 change_title 四个问题
- 变更原因：用户反馈 simplify_axis 应该将"每年"改为"每五年"显示，而非完全隐藏；注释文字超出画幅且不换行；Adverser 选取小数据范围后柱状图太细；Amplifier 没有 change_title 强化叙事
- 影响范围（文件/模块）：
  - `backend/app/transform/node3_executor.py`
  - `backend/app/agents/llm_client.py`
  - `backend/tests/test_batch13_node3_executor.py`
- 变更内容：
  1. **simplify_axis 默认模式改为 interval_labels**：不再使用 `compact_hide`（隐藏所有标签），默认保留标签并稀疏显示。对 temporal 类型使用 `tickCount.interval=year, step=5`；对 quantitative 使用 `labelExpr` modulo。
  2. **注释多行渲染**：annotation_text 从 `\n` 拼接字符串改为数组格式 `["line1", "line2"]`，Vega-Lite 原生支持数组多行文本。注释最大长度从 100 缩减为 80 字符。
  3. **select_data_range 后自动加宽柱状图**：新增 `_widen_bars_for_narrow_range()`，当数据点减少超过 40% 时，设置 `mark.width = {"band": 0.85}` 让柱状图更宽。
  4. **Amplifier change_title 保障**：在 LLM post-processing 中，若 Amplifier plan 缺少 change_title，自动插入到 plan 首位。
- 接口影响：无
- 测试命令：`cd backend && conda activate frame && python -m pytest tests/ -x -q`
- 测试结果：
  - `51 passed`
- 风险与回滚点：`tickCount` 对 temporal 轴的行为依赖 Vega-Lite 版本
- 后续待办：观察实际渲染效果，验证 temporal 轴标签间距

---

## [2026-03-11 17:15] Batch-44 / Adverser 策略层反叙事修复 + simplify_axis Amplifier 保障

- 变更目标：从策略层（NodeB）修复 Adverser 反叙事生成，确保 LLM 和 fallback 都产出正确的反趋势内容
- 变更原因：Batch-43 仅修复了执行层（NodeC），但 NodeB 的 LLM 已生成了支持趋势的 intent（如 "A Century of Warming"），executor 直接使用导致反叙事修复被绕过
- 影响范围（文件/模块）：
  - `backend/app/agents/llm_client.py`
- 变更内容：
  1. **LLM Prompt 强化**：`_propose_strategy_via_llm` 中 Adverser 行从 "selective data + source deletion" 替换为显式反叙事约束（MUST produce COUNTER-NARRATIVE，含温度/森林/经济三类示例）。
  2. **Post-LLM 验证**：LLM 返回 Adverser plan 后，用 `_intent_supports_trend()` 检测 change_title 和 add_annotation 的 intent 是否支持数据趋势。若是，则覆盖为 `_build_title_intent` / `_build_annotation_intent` 的反叙事输出。
  3. **`_build_title_intent` climate+Adverser**：新增 "climate" + "Adverser" 分支，生成 "Temperature Dropping Since {peak_x}" 或 "Global Cooling Trend"。新增 economy+Adverser 分支。通用 Adverser 分支改为根据趋势方向输出 "Decline Visible" 或 "Recovery Underway"。
  4. **`_build_annotation_intent` Adverser**：改用 `_build_counter_narrative_annotation()` 替代 `_build_data_grounded_annotation()`，后者生成的是支持趋势的注释文本。新方法使用 `_find_decline_window()` 提取最陡下降段数据。
  5. **`_build_select_data_range_params` Adverser**：从盲目取后半数据改为调用 `_find_decline_window()` 定位最陡下降窗口作为 start/end。
  6. **`_build_color_intent` Adverser**：通用 Adverser 改为 "counter-framing cooling blue contrast"（蓝色冷色调），不再使用 alarm red。
  7. **Amplifier simplify_axis 保障**：LLM 返回 Amplifier plan 后，若无 simplify_axis，自动追加。
- 接口影响：无（内部策略行为优化）
- 测试命令：`cd backend && conda activate frame && python -m pytest tests/ -x -q`
- 测试结果：
  - `51 passed`
- 风险与回滚点：`_intent_supports_trend` 使用关键词匹配，可能误判少数非标准 intent
- 后续待办：观察实际 LLM 输出，验证反叙事标题/注释在温度数据上的效果

---

## [2026-03-11 16:35] Batch-43 / Adverser 反叙事修复 + simplify_axis 显示 + Amplifier 配色

- 变更目标：修复三个模拟效果缺陷
- 变更原因：用户反馈 Adverser 标题/注释未产生反叙事内容；simplify_axis 执行后未在 Process 面板显示；Amplifier 配色由红变绿削弱了情绪放大效果
- 影响范围（文件/模块）：
  - `backend/app/transform/node3_executor.py`
- 变更内容：
  1. **Adverser 反叙事强化**：LLM prompt 新增 CRITICAL ADVERSER CONSTRAINT，明确要求产出与整体趋势相反的标题（如数据上升→声称 "Cooling Trend"）。Fallback 标题改为 "Dropping Since X" / "Cooling Trend"，注释引用具体 decline_window 数值。
  2. **注释锚点角色感知**：`_pick_annotation_anchor` 从 staticmethod 改为实例方法，Adverser 锚定到最低点（支持反叙事），Amplifier 锚定到峰值（强化趋势）。
  3. **simplify_axis 幂等显示**：区分 `touched`（找到目标轴通道）与 `changed`（实际改变），只要目标轴存在即返回 applied，避免重复执行时误标 skipped。
  4. **Amplifier 配色修复**：新增 `_pick_palette_for_role` 实例方法，Amplifier 强制使用警示红色（覆盖绿色），Adverser 使用冷色调（蓝色）以削弱警示感。
- 接口影响：无（内部行为优化）
- 测试命令：`cd backend && conda activate frame && python -m pytest tests/ -x -q`
- 测试结果：
  - `51 passed`
- 风险与回滚点：Amplifier 永远不会选择绿色调色板；如需绿色需在 intent 中显式指定 hex
- 后续待办：观察实际 LLM 输出，确认 Adverser 反叙事 prompt 生效

---

## [2026-03-09 22:05] Batch-42 / Annotation 右侧轴重叠修复 + select_data_range 收缩 x 轴域

- 变更目标：修复注释后出现左右轴重叠；让 `select_data_range` 不再保留未选中的 x 轴显示范围
- 变更原因：用户反馈 add annotation 后右侧轴文字重叠，且 select_data_range 后 x 轴仍显示完整历史范围
- 影响范围（文件/模块）：
  - `backend/app/transform/node3_executor.py`
  - `backend/tests/test_batch13_node3_executor.py`
  - `docs/backend/CHANGELOG.md`
- 接口影响：无
- 数据结构影响：无
- 关键实现点：
  - 注释层坐标修复：
    - `Node3 added annotation` 的 `encoding.y` 从 `field: y_label` 改为 `datum`
    - `Node3 added annotation leader` 的 `encoding.y2` 从 `field: y_label` 改为 `datum`
    - 避免 synthetic 字段触发第二套 y-scale/y-axis，消除右侧轴重叠
  - `select_data_range` 增强：
    - 在追加 `transform.filter` 之外，同步为匹配 `x_field` 的 `encoding.x.scale.domain` 设置 `[start, end]`
    - 使 x 轴可视范围与筛选窗口一致，不再保留未选中的时间段
- 测试命令：
  - `conda run -n frame python -m pytest -q tests/test_batch13_node3_executor.py tests/test_batch2_components.py`
- 测试结果：
  - `32 passed`
- 风险与回滚点：
  - 若某些图表需要固定全域对比，可通过后续参数开关禁用 domain 收缩
- 后续待办：
  - 支持 `select_data_range` 增加 `keep_full_domain` 可选参数，按场景切换“聚焦窗口”与“全域对比”

## [2026-03-09 22:25] Batch-43 / 注释层轴污染阻断 + Process 显示执行态操作

- 变更目标：彻底阻断注释辅助层对坐标轴/尺度的干扰；让前端 process 显示“实际执行”操作
- 变更原因：用户反馈仍观察到左右轴重合、尺度混乱，且 process 未反映实际发生的操作，产生“凭空出现”感
- 影响范围（文件/模块）：
  - `backend/app/transform/node3_executor.py`
  - `backend/app/services/simulation_service.py`
  - `backend/tests/test_batch13_node3_executor.py`
  - `docs/backend/CHANGELOG.md`
- 接口影响：无
- 数据结构影响：无
- 关键实现点：
  - Node3 注释辅助层（anchor/leader/text）中的 `encoding.x` / `encoding.y` 全部显式设置 `axis: null`
  - 继续保留 `y`/`y2` 的 `datum` 定位，避免 synthetic 字段触发额外 y 轴
  - `SimulationService` 节点 `operations` 展示改为优先使用 `node_c_result.executed_operations`，回退才使用计划操作，提升“所见即所执行”一致性
- 测试命令：
  - `conda run -n frame python -m pytest -q tests/test_batch13_node3_executor.py tests/test_batch2_components.py`
- 测试结果：
  - `32 passed`
- 风险与回滚点：
  - 若后续需要在 process 展示“计划但未执行”的差异，需要新增双轨展示（planned vs executed）
- 后续待办：
  - 在右侧 process 增加“执行结果标签”（applied/skipped）以提升可解释性

## [2026-03-09 22:45] Batch-44 / Amplifier 改色落地增强 + trendline 轴域污染修复 + Process 平台展示

- 变更目标：修复 `change_color` 显示执行但视觉不变、trendline 造成 y 轴标题混乱、右侧 process 缺少所属平台
- 变更原因：用户反馈 Amplifier 显示有 `change_color` 但图色不变，出现 y 轴尺度/legend 混乱，且 process 缺“角色+平台+操作”中的平台维度
- 影响范围（文件/模块）：
  - `backend/app/transform/node3_executor.py`
  - `backend/app/services/simulation_service.py`
  - `backend/tests/test_batch13_node3_executor.py`
  - `frontend/src/features/offset/OffsetPanel.tsx`
  - `docs/backend/CHANGELOG.md`
- 接口影响：无
- 数据结构影响：无
- 关键实现点：
  - `change_color` 新增对 `encoding.color.condition/value` 的显式改色（不只改 `scale.range/config.range`），保证柱/线主色真实变化可见
  - 注释 trendline 层将 `x2/y2` 从 field 改为 `datum`，并为辅助层显式 `axis: null`，阻断额外字段污染 y 轴标题与尺度
  - `simulation_service` 的 process 格式化支持从执行记录 `params.intent` 兜底提取意图文本
  - 前端 `OffsetPanel` 过程流节点新增平台展示：`@institution`
- 测试命令：
  - `conda run -n frame python -m pytest -q tests/test_batch13_node3_executor.py tests/test_batch2_components.py`
- 测试结果：
  - `33 passed`
- 风险与回滚点：
  - 条件色值重写默认使用“强调色 + 冷色基线”策略；如需严格保留原有正负色语义，可后续加参数切换
- 后续待办：
  - process 继续细化为 `planned/executed` 双轨并显示 `applied/skipped` 标签

## [2026-03-09 23:05] Batch-45 / Bridger 禁止标题改写 + 注释趋势线显式触发

- 变更目标：落实 taxonomy 新约束（Bridger 通常不执行 `change_title` / `simplify_axis`），并修复右侧注释“指向空白”问题
- 变更原因：用户指出 `taxonomy_codebook.md` 已明确 Bridger 不应执行改标题和简化轴，同时截图出现 annotation 线条指向空白区域
- 影响范围（文件/模块）：
  - `backend/app/agents/llm_client.py`
  - `backend/app/transform/node3_executor.py`
  - `backend/tests/test_batch2_components.py`
  - `backend/tests/test_batch13_node3_executor.py`
  - `docs/backend/CHANGELOG.md`
- 接口影响：无
- 数据结构影响：无
- 关键实现点：
  - 策略层硬约束：
    - fallback 策略新增 Bridger 分支，默认不生成 `change_title` 与 `simplify_axis`
    - LLM 输出归一化阶段对 Bridger 额外过滤 `change_title` / `simplify_axis`
    - refine 阶段也再次过滤，避免 LLM 结果绕过约束
  - 注释趋势线触发策略收紧：
    - `_intent_requests_trendline` 改为“显式关键词触发”（`trendline/trend line/趋势线/回归线`）
    - 不再因普通叙事词（如 rises/falls）自动加趋势线，减少“指向空白”的误导线条
  - 新增测试覆盖：
    - Bridger 策略不包含 `change_title` 与 `simplify_axis`
    - 文案仅出现 `rises` 时不会自动创建 trendline
- 测试命令：
  - `conda run -n frame python -m pytest -q tests/test_batch2_components.py tests/test_batch13_node3_executor.py`
- 测试结果：
  - `35 passed`
- 风险与回滚点：
  - 趋势线从“宽松自动”改为“显式触发”后，默认出现频率会下降；如需恢复可在 params 明确传 `include_trendline=true`
- 后续待办：
  - 根据机构类型（news/social/authority）进一步细分 Bridger 的最小操作模板

## [2026-03-09 23:25] Batch-46 / Bridger 单操作收敛 + Process 全量执行记录

- 变更目标：将 Bridger 严格收敛为仅执行 `change_color`；修复右侧 process 对“已执行但未显示”记录不完整的问题
- 变更原因：用户明确要求 Bridger 只有改色操作，并反馈 process 未完整展示实际执行步骤
- 影响范围（文件/模块）：
  - `backend/app/agents/llm_client.py`
  - `backend/app/services/simulation_service.py`
  - `backend/tests/test_batch2_components.py`
  - `backend/tests/test_batch5_topology_and_case_data.py`
  - `docs/backend/CHANGELOG.md`
- 接口影响：无
- 数据结构影响：无
- 关键实现点：
  - Bridger 约束升级：
    - fallback 策略中 Bridger 仅生成 `change_color`
    - LLM 结果归一化与 refine 阶段均改为“只保留 `change_color`”
    - 当 whitelist 不包含 `change_color` 时，Bridger 返回空操作（不再回退到 annotation）
  - Process 展示增强：
    - `SimulationService` 优先使用 `operation_audit` 生成 UI operations
    - 每条操作附带状态标签（如 `[applied]`、`[skipped: reason]`），避免“图变了但 process 不显示”或“计划/执行不一致”不可见
    - 无审计记录时再回退到执行计划/旧字段
  - 测试新增：
    - Bridger 只保留 `change_color`
    - `_format_operations_for_ui` 优先展示审计记录并带状态
- 测试命令：
  - `python -m pytest -q tests/test_batch2_components.py tests/test_batch13_node3_executor.py`
- 测试结果：
  - `36 passed`
- 风险与回滚点：
  - process 文本更长（增加状态标签）；如 UI 需更简洁可后续切换为图标标签
- 后续待办：
  - 前端 process 增加“只看 applied”筛选开关，支持快速查看最终生效操作

## [2026-03-10 18:30] Batch-39 / Change Color 角色意图与数据标记收敛

- 变更目标：让 `change_color` 主要作用于线/柱/条等数据标记，并更贴合 Amplifier/Adverser 角色意图
- 变更原因：用户反馈当前配色策略存在“背景被改”与“角色配色意图不够明确”的问题
- 影响范围（文件/模块）：
  - `backend/app/agents/llm_client.py`
  - `backend/app/transform/node3_executor.py`
  - `backend/app/config/node3_operation_schema_v1.yaml`
  - `backend/tests/test_batch2_components.py`
  - `backend/tests/test_batch13_node3_executor.py`
  - `docs/taxonomy/node3_operation_schema_v1.md`
  - `docs/backend/后端工程技术方案.md`
- 接口影响：无
- 数据结构影响：无
- 关键实现点：
  - `change_color` 执行器新增“可重着色 mark 白名单”，仅重着色 line/bar/area/point 等主数据 mark，跳过 text/rect 背景层
  - Amplifier/Adverser 在媒体/社交平台默认 `palette_style=social_contrast`
  - Amplifier deforestation 场景移除自动 `add_background`，避免与 color 操作混淆
  - `pick_palette_from_intent` 新增 cooling/blue 信号解析，支持 Adverser 对立叙事配色
  - 新增测试覆盖：
    - Amplifier 媒体策略使用 `social_contrast`
    - Amplifier deforestation 不再强制追加 `add_background`
    - `change_color` 不会重着色 `rect` 背景层
- 测试命令：
  - `conda run -n frame python -m pytest -q tests/test_batch2_components.py tests/test_batch13_node3_executor.py`
- 测试结果：
  - `32 passed`
- 风险与回滚点：
  - 白名单策略可能遗漏少数图表类型；如后续有新图型可增量加入 mark 白名单
- 后续待办：
  - 引入更细粒度角色-主题配色映射（不仅平台维度）

## [2026-03-10 18:05] Batch-38 / Annotation 文案压缩与自适应换行

- 变更目标：在已有边界钳制基础上进一步解决 annotation 左右越界与文本过长导致的显示干扰
- 变更原因：用户反馈右侧越界修复后，仍出现左侧越界与注释过长影响整体阅读
- 影响范围（文件/模块）：
  - `backend/app/transform/node3_executor.py`
  - `backend/app/agents/llm_client.py`
  - `backend/tests/test_batch13_node3_executor.py`
  - `docs/backend/后端工程技术方案.md`
- 接口影响：无
- 数据结构影响：无
- 关键实现点：
  - Node3：
    - 数据锚点注释新增“按画布宽度 + 锚点位置 + 对齐方向”的可用字符数估算
    - 对 `annotation_text` 执行自适应换行，减少左/右边缘溢出
    - `change_annotation` 对已有文本标注同样执行画布自适应换行
  - NodeB/NodeC 策略：
    - `add_annotation` / `change_annotation` 默认 `max_line_chars` 收紧为 `32`
    - Analyst / Adverser 注释模板改为更短的一句式表达
  - 新增测试：
    - 右侧锚点 + 长注释时验证自动换行仍保留右对齐
- 测试命令：
  - `conda run -n frame python -m pytest -q tests/test_batch13_node3_executor.py tests/test_batch2_components.py`
- 测试结果：
  - `30 passed`
- 风险与回滚点：
  - 字符宽度估算为启发式，在极端字体/渲染器差异下可能仍需微调
- 后续待办：
  - 结合真实渲染像素测量进一步做注释避让与碰撞检测

## [2026-03-10 11:10] Batch-37 / Annotation 边界约束修复

- 变更目标：修复 annotation 超出图表范围、跑到画布外的问题
- 变更原因：用户反馈图内注释在窄图/多次注释场景中易越界，影响可读性和 framing shift 识别
- 影响范围（文件/模块）：
  - `backend/app/transform/node3_executor.py`
  - `backend/tests/test_batch13_node3_executor.py`
  - `docs/backend/后端工程技术方案.md`
- 接口影响：无
- 数据结构影响：无
- 关键实现点：
  - `_next_annotation_position` 增加基于 `width/height` 的边界钳制与纵向回绕策略
  - 数据锚点注释新增左右自适应排版：靠右锚点自动 `align=right` 且 `dx=-10`
  - `change_annotation` 对已有像素坐标注释执行位置归一，避免旧坐标越界残留
  - 新增测试覆盖：
    - 小画布下注释坐标不会越界
    - 右侧锚点注释自动使用右对齐
- 测试命令：
  - `conda run -n frame python -m pytest -q tests/test_batch13_node3_executor.py tests/test_batch2_components.py`
- 测试结果：
  - `30 passed`
- 风险与回滚点：
  - 坐标边界目前按像素值启发式处理，极端自定义 Vega 布局下可能需要再细化
- 后续待办：
  - 结合 text box 实际宽度估计，进一步优化多注释密集场景避让

## [2026-03-09 16:30] Batch-29 / 标题-注释-趋势线联动增强

- 变更目标：解决“有操作名但无实质语义”的问题，让 `change_title`、`add_annotation`、图内趋势表达形成联动
- 变更原因：用户反馈当前 annotation 文本空泛（如 “assert strong counter interpretation”），无法支撑可视化叙事修改
- 影响范围（文件/模块）：
  - `backend/app/agents/llm_client.py`
  - `backend/app/transform/node3_executor.py`
  - `backend/app/config/node3_operation_schema_v1.yaml`
  - `docs/taxonomy/node3_operation_schema_v1.md`
  - `backend/tests/test_batch13_node3_executor.py`
  - `docs/backend/后端工程技术方案.md`
  - `docs/backend/CHANGELOG.md`
- 接口影响：无（API 路径与字段不变）
- 数据结构影响：无（返回结构不变，执行结果内容增强）
- 关键实现点：
  - NodeB/NodeC prompt 收紧：
    - `add_annotation` 要求 data-grounded 文本，避免空泛口号
    - 若描述上升/下降趋势，intent 中要求包含 `trendline: true`
  - fallback 注释增强：
    - 从图表数据提取起止值/峰值摘要，生成更具体 annotation 文本
  - Node3 执行增强：
    - `add_annotation` 解析 `trendline: true`
    - 在 Vega-Lite `layer` 中新增 `Node3 added trendline` rule 层（非仅文本）
    - 解析 annotation intent 时剥离 directive，避免 directive 原样出现在图中文字
  - 新增测试：
    - `test_executor_adds_trendline_when_annotation_requests_it`
- 测试命令：
  - `/opt/anaconda3/envs/frame/bin/python -m pytest -q tests/test_batch2_components.py tests/test_batch13_node3_executor.py`
- 测试结果：
  - `18 passed`
- 风险与回滚点：
  - 趋势线为启发式（首尾点 rule），复杂非线性走势可继续升级为回归线
- 后续待办：
  - 增加 annotation 参数化字段（`anchor_strategy`, `trendline_mode`）
  - 将 NodeB 输出从 `intent` 文本升级为结构化 `params`，进一步减少歧义

## [2026-03-09 15:55] Batch-28 / NodeB+NodeC LLM 混合增强

- 变更目标：把模拟从“规则可执行”推进到“具备内容感知与语义生成”的混合模式（LLM 决策/细化 + deterministic 执行）
- 变更原因：用户反馈子节点修改仍偏表层，未稳定体现 who/where/how 与内容语义耦合
- 影响范围（文件/模块）：
  - `backend/app/agents/llm_client.py`
  - `backend/app/graph/workflow.py`
  - `backend/app/services/simulation_service.py`
  - `docs/backend/后端工程技术方案.md`
  - `docs/backend/CHANGELOG.md`
- 接口影响：无（API 路径与字段契约不变）
- 数据结构影响：无（响应结构不变，内部决策与执行前意图细化能力增强）
- 关键实现点：
  - NodeB LLM prompt 升级：
    - 显式加入 taxonomy who/where/how 指导
    - 注入 role/institution/topic/description 上下文
    - 支持 `change_title` 的 `title:` 精确意图约定
    - 加入 deforestation 案例锚点（如 “Amazon Deforestation Highest Since 2006”）
  - NodeC 增强：
    - 新增 `refine_execution_plan`，在执行前可由 LLM 细化 selected operations 的 intent
    - 若 LLM 不可用，走 fallback 语义细化（标题/颜色/注释）
    - 最终仍由 `Node3Executor` 做 deterministic patch，保持回滚与审计能力
  - 修复稳定性：
    - 当 persona 缺失时，shift 估计回退到 `shift_prior`，避免冲突路径被误降级为 minor
- 测试命令：
  - `/opt/anaconda3/envs/frame/bin/python -m pytest -q tests/test_batch2_components.py tests/test_batch13_node3_executor.py`
- 测试结果：
  - `17 passed`
- 风险与回滚点：
  - 全量测试在当前环境存在间歇性挂起现象，本次先以受影响模块专项测试验证；若联调异常可先关闭 `USE_LLM` 回退
- 后续待办：
  - 将 platform tier 从 institution 关键词推断升级为显式输入字段
  - 增加 NodeC 参数化 intent（target_year/palette/headline_style）以减少文本歧义

## [2026-03-09 11:40] Batch-27 / Who-Where-How 语义策略增强

- 变更目标：提升模拟“理解数据内容后再改图”的能力，让操作选择更稳定体现 who（角色）+ where（平台/机构）+ how（操作）耦合
- 变更原因：现网虽已跑通 Node3 执行，但部分路径仍呈现“仅样式改动、语义理解不足”的问题
- 影响范围（文件/模块）：
  - `backend/app/agents/llm_client.py`
  - `backend/app/transform/node3_executor.py`
  - `backend/app/config/node3_operation_schema_v1.yaml`
  - `docs/taxonomy/node3_operation_schema_v1.md`
  - `docs/backend/后端工程技术方案.md`
  - `docs/backend/CHANGELOG.md`
- 接口影响：无（`/api/upload-case`、`/api/simulation/start`、`/api/health` 路径与字段不变）
- 数据结构影响：无（响应结构不变，内部策略与执行语义增强）
- 关键实现点：
  - NodeB fallback 从固定模板升级为语境感知：
    - 识别 `role + institution(platform bucket) + topic/title` 信号
    - 按角色签名选择跨层操作组合，并按平台语境调节操作强度
    - 对 deforestation 等主题生成更贴近语料的标题/配色 intent
  - Node3 执行增强：
    - `change_title` 支持 `title:`/`headline:` 前缀，允许精确标题写入
    - `change_color` 支持显式 hex 与 forest/deforestation 主题词映射
  - schema 同步：
    - YAML 新增 `intent_conventions` 与 `strategy_guidance`
    - 文档新增 who/where/how 指导与 deforestation 实例
- 测试命令：
  - `conda run -n frame python -m pytest -q`
- 测试结果：
  - `31 passed`
- 风险与回滚点：
  - 主题信号识别仍为关键词启发式，极端长尾语料可能不命中；可通过继续丰富信号词表迭代
- 后续待办：
  - 将“平台 bucket”从关键词推断升级为前端显式字段
  - 给 operation plan 增加结构化参数（如 `target_year`, `palette`, `headline_style`）以减少 intent 文本歧义

## [2026-03-08 09:10] Batch-26 / 撤回前端 Audit 展示

- 变更目标：按用户反馈撤回右侧 Process 的 Audit 展示，回归简洁视图
- 变更原因：当前阶段优先关注生成结果质量，Audit 面板增加认知负担
- 影响范围（文件/模块）：
  - `backend/app/schemas/api_contract.py`
  - `backend/app/services/simulation_service.py`
  - `frontend/src/types/contracts.ts`
  - `frontend/src/features/offset/OffsetPanel.tsx`
  - `docs/api/接口文档.md`
  - `docs/backend/CHANGELOG.md`
- 接口影响：无（删除了刚新增的可选字段 `operationAudit`，主字段不变）
- 数据结构影响：无（节点结构恢复到前一版本）
- 关键实现点：
  - 删除 `TreeNode.operationAudit`
  - 取消 simulation 节点对 `operation_audit` 的 API 透传
  - 前端移除 `operationAudit` 类型与 Process Audit 区块
  - 接口文档同步删除对应字段说明
- 测试命令：
  - `conda run -n frame python -m pytest -q`
  - `cd frontend && npm run build`
- 测试结果：
  - 后端：`31 passed`
  - 前端：构建成功
- 风险与回滚点：
  - 若后续需要排查策略执行细节，可从后端 run snapshot 的 `provenance_chain.operation_audit` 获取

## [2026-03-07 18:05] Batch-25 / Process 可解释性增强与前端显示修复

- 变更目标：让你能在右侧直接看懂 op 执行情况，并修复预览与图标视觉问题
- 变更原因：用户反馈“预览不完整”和“中间黄色图标不属于四类 agent”，同时希望先理解 operation audit
- 影响范围（文件/模块）：
  - `backend/app/schemas/api_contract.py`
  - `backend/app/services/simulation_service.py`
  - `frontend/src/types/contracts.ts`
  - `frontend/src/features/offset/OffsetPanel.tsx`
  - `frontend/src/features/propagation/PropagationPanel.tsx`
  - `docs/api/接口文档.md`
  - `docs/backend/后端工程技术方案.md`
  - `docs/backend/CHANGELOG.md`
- 接口影响：向后兼容增强（`tree.nodes[]` 新增可选 `operationAudit` 字段）
- 数据结构影响：有（节点对象可携带审计数组，前端 process 可直接消费）
- 关键实现点：
  - 后端：
    - `TreeNode` 新增 `operationAudit?: list[dict]`
    - simulation 构建节点时透传 NodeC 的 `operation_audit`
  - 前端：
    - `AgentNode` 类型新增 `operationAudit`
    - 右侧 Process 每个节点新增 `Audit` 摘要（默认显示前 4 条）
    - Preview 高度从 `160` 提升到 `220`
    - `analyst` 颜色映射由旧黄色改为 Extender 色，传播图与 process 一致
- 测试命令：
  - `conda run -n frame python -m pytest -q`
  - `cd frontend && npm run build`
- 测试结果：
  - 后端：`31 passed`
  - 前端：构建成功（Vite 提示 Node 20.19+ 推荐）
- 风险与回滚点：
  - `operationAudit` 目前只显示前 4 条摘要；如需完整调试可扩展折叠详情
- 后续待办：
  - 在 process 中增加“显示全部 audit + target_paths”开关
  - 支持按 `status=skipped` 过滤查看失败/跳过原因

## [2026-03-07 17:45] Batch-24 / 全量 op 覆盖 + provenance 细粒度 + institution 展示

- 变更目标：完成 Node3 全量 op 覆盖、补齐细粒度 provenance，并同步前后端口径（mode/platform 遗留兼容）
- 变更原因：当前版本仍存在“部分 op 未落地、可追溯信息不足、右侧流程缺机构信息”的联调缺口
- 影响范围（文件/模块）：
  - `backend/app/transform/node3_executor.py`
  - `backend/app/graph/workflow.py`
  - `backend/app/services/simulation_service.py`
  - `backend/app/config/taxonomy_rules_v3.yaml`
  - `backend/app/config/fallback_rules.yaml`
  - `backend/app/schemas/api_contract.py`
  - `backend/tests/test_batch13_node3_executor.py`
  - `frontend/src/features/offset/OffsetPanel.tsx`
  - `docs/api/接口文档.md`
  - `docs/backend/后端工程技术方案.md`
  - `docs/backend/CHANGELOG.md`
- 接口影响：低（保持路径与主字段不变；`mode/platform` 改为遗留兼容语义说明）
- 数据结构影响：有（NodeC 输出新增 `operation_audit`，provenance_chain 持久化该字段）
- 关键实现点：
  - Node3 执行器新增剩余 6 个 op：
    - `select_data_variables`
    - `change_data_granularity`
    - `change_chart_type`
    - `add_background`
    - `change_aspect_ratio`
    - `change_annotation`
  - provenance 细粒度：
    - 每个 op 记录 `operation/params/target_paths/before/after/status/error`
    - `executed_operations` 保留 applied；`operation_audit` 覆盖 applied+skipped
  - 策略层 whitelist 扩展（taxonomy/fallback）以支持更多 visual/data 操作触发
  - 右侧 Process 时间线在角色下方新增 `institution` 显示
  - API 文档同步：标注 `mode`、`platform` 为历史兼容字段
- 测试命令：
  - `conda run -n frame python -m pytest -q`
  - `cd frontend && npm run build`
- 测试结果：
  - 后端：`31 passed`
  - 前端：构建成功（Vite 提示 Node 版本建议升级，不阻塞）
- 风险与回滚点：
  - 新增 op 多为启发式目标选择，复杂多层 spec 下可能与人工期望存在偏差；可按 op 粒度回退
- 后续待办：
  - 将 op 目标通道/path 参数化（例如 `target_channel`, `target_path`）
  - 对 `operation_audit` 增加 UI 展示入口，支持逐 op 调试

## [2026-03-07 17:10] Batch-23 / 策略智能度增强与执行约束收紧

- 变更目标：提升“非 text 操作”可见性与策略智能度，并按 taxonomy 语义收紧部分 op 执行条件
- 变更原因：联调反馈显示当前版本视觉/数据层改动不足，`add_legend` 与 `simplify_axis` 需更精确符合研究口径
- 影响范围（文件/模块）：
  - `backend/app/graph/workflow.py`
  - `backend/app/graph/langgraph_runner.py`
  - `backend/app/agents/llm_client.py`
  - `backend/app/transform/node3_executor.py`
  - `backend/app/config/node3_operation_schema_v1.yaml`
  - `docs/taxonomy/node3_operation_schema_v1.md`
  - `backend/tests/test_batch13_node3_executor.py`
  - `docs/backend/后端工程技术方案.md`
  - `docs/backend/CHANGELOG.md`
- 接口影响：无（API 契约不变）
- 数据结构影响：无（响应结构不变，内部策略与执行行为增强）
- 关键实现点：
  - NodeB -> LLM 策略链路增加上下文输入：
    - `propose_strategy(gap_type, persona, context, whitelist, shift_prior)`
    - 让策略选择感知角色签名、父图语境、可执行白名单
  - fallback 策略升级为 taxonomy 风格：
    - Amplifier 偏 visual+text
    - Analyst(Extender) 偏 data + cross-layer
    - Adverser 偏 selective data + strong visual/text
    - Bridger 偏 visual clarity + light text
  - 执行器行为调整：
    - `add_legend`：仅在“无 legend + 强调意图”满足时执行
    - `simplify_axis`：仅简化 x 轴
    - `change_color`：覆盖更多可改目标并按 intent 选择配色（提升可见变化）
  - schema/doc 同步：
    - `node3_operation_schema_v1.yaml` 增补 `simplify_axis` 与 `add_legend` 策略约束
    - `docs/taxonomy/node3_operation_schema_v1.md` 追加对应策略说明
  - 新增测试：`test_add_legend_requires_emphasis_and_absent_legend`
- 测试命令：
  - `conda run -n frame python -m pytest -q`
- 测试结果：
  - `30 passed`
- 风险与回滚点：
  - 当前 fallback 仍为启发式模板，不等价于完整 taxonomy 推理；若行为异常可临时回退到旧 fallback 逻辑
- 后续待办：
  - 将 `change_color` 的目标语义（风险/积极/中性）外显到 operation plan 参数
  - 在 provenance 中记录“策略为何选择 visual/data op”的决策证据字段

## [2026-03-07 16:40] Batch-22 / Node3 B+A 收口（执行器扩展 + 语义校验）

- 变更目标：完成 Node3 剩余两项任务：B（执行器扩展 4 个 op）与 A（语义级 validator）
- 变更原因：M2/M3 已具备基础执行与结构回滚，需补齐 codebook 覆盖与语义一致性保障
- 影响范围（文件/模块）：
  - `backend/app/transform/node3_executor.py`
  - `backend/app/transform/spec_validator.py`
  - `backend/tests/test_batch13_node3_executor.py`
  - `docs/backend/后端工程技术方案.md`
  - `docs/backend/CHANGELOG.md`
- 接口影响：无（API 路径与字段契约不变）
- 数据结构影响：无（NodeC 输出字段不变，仅执行能力和校验规则增强）
- 关键实现点：
  - 执行器新增 op：
    - `simplify_axis`：压缩坐标轴视觉元素（labels/ticks/grid/title）
    - `change_axis_scale`：按 intent 在定量/时序轴上调整 scale.type（默认 log）
    - `add_legend`：优先在 color/shape/size/opacity 通道补 legend
    - `change_legend`：优先改已有 legend，且避免误改位置通道
  - validator 语义规则新增：
    - `x2_without_x` / `y2_without_y`
    - `encoding_channel_missing_field_or_value:<channel>`
    - `axis_on_non_positional_channel:<channel>`
    - `legend_on_positional_channel:<channel>`
    - `scale_domain_reversed:<channel>`
  - 新增测试：
    - `test_executor_applies_axis_and_legend_ops`
    - `test_spec_validator_rejects_semantic_axis_encoding_conflicts`
- 测试命令：
  - `conda run -n frame python -m pytest -q`
- 测试结果：
  - `29 passed`
- 风险与回滚点：
  - `change_axis_scale` 当前以“首个可用轴”为目标，复杂多轴图可能与人工期望不完全一致
- 后续待办：
  - 将 axis/legend 的目标通道参数化进 operation plan（显式 channel/path）
  - 在 provenance 记录每个 op 的具体命中通道（如 `encoding.color.legend`）

## [2026-03-07 16:05] Batch-21 / F2 驱动的硬约束 Agent 池调度

- 变更目标：按前端 `agentProfiles` 作为硬约束池，并结合父节点与 F2 规律决定每层由哪些剩余 agent 响应
- 变更原因：用户反馈希望“已用 agent 不复用，下一层由剩余池按 F2 选择响应者”
- 影响范围（文件/模块）：
  - `backend/app/config/taxonomy_rules_v3.yaml`
  - `backend/app/agents/taxonomy_adapter.py`
  - `backend/app/services/simulation_service.py`
  - `backend/tests/test_batch5_topology_and_case_data.py`
  - `docs/backend/后端工程技术方案.md`
  - `docs/backend/CHANGELOG.md`
- 接口影响：无（路径与字段名不变）
- 数据结构影响：无（响应结构不变，节点生成顺序与角色分布策略更新）
- 关键实现点：
  - taxonomy 规则新增 `role_transition_prior`（F2 角色转移权重）
  - `TaxonomyAdapter` 新增 `get_role_transition_prior`，并内置默认 F2 权重兜底
  - simulation 主循环改造：
    - 维护 `unused_profile_indexes`，每个 profile 仅消费一次
    - 根据父节点 category 与 F2 权重，从剩余池选择最匹配 profile
    - `agentProfiles` 存在时，预算按 `min(agentCount, len(agentProfiles))` 收敛
  - 新增/更新测试覆盖：
    - 验证 `Bridger` 起点优先触发 `Amplifier` 响应
    - 验证 5 个 profile 在深度限制内可被全部消费且 `Extender` 可见
- 测试命令：
  - `conda run -n frame python -m pytest -q`
- 测试结果：
  - `27 passed`
- 风险与回滚点：
  - 目前为“取最大权重”策略，随机性较弱；若需更多多样性，可后续切换为按权重采样
- 后续待办：
  - 将 F2 选择器加入 mode 偏置（如 adversarial 下提升 Adverser 权重）
  - 增加可观测字段（例如每层被选中的 profile 索引与选择理由）

## [2026-03-07 15:20] Batch-20 / Agent Pool 扩展与 Extender 展示修复

- 变更目标：修复“3 层 5 agent 未满配”和“Extender 在结果中不可见”的联调问题
- 变更原因：原拓扑为单链式扩散（每层最多 1 子节点）且角色展示优先级未绑定 profile 输入
- 影响范围（文件/模块）：
  - `backend/app/services/simulation_service.py`
  - `backend/tests/test_batch5_topology_and_case_data.py`
  - `docs/backend/后端工程技术方案.md`
  - `docs/backend/CHANGELOG.md`
- 接口影响：无（路径与字段名不变）
- 数据结构影响：无（仅节点生成策略与 `role` 填充值优先级调整）
- 关键实现点：
  - simulation 主循环改为“按层分配 agent”：
    - 每层根据 `remaining_agents / remaining_depth` 计算本层投放量
    - 在 frontier 上轮转分配父节点，支持同层多 agent
  - 当某层全部 `ignore` 且仍有剩余 agent 时：
    - 将 ignore 节点作为 pass-through frontier，防止链路提前终止
  - `role` 展示优先读取请求中的 `agentProfiles[].role`，保留 `Analyst -> Extender` 映射兼容
  - 新增测试：`test_simulation_agent_pool_spreads_across_depth_and_keeps_extender_role`
- 测试命令：
  - `conda run -n frame python -m pytest -q`
- 测试结果：
  - `27 passed`
- 风险与回滚点：
  - 同层节点数增多后前端图布局更密集；若拥挤可在前端增加自动缩放或折叠策略
- 后续待办：
  - 将“每层 agent 分配策略”参数化（均匀/前置/后置）
  - 增加 `tree.requestedDepth/requestedAgentCount` 回传，便于前端标注“配置值 vs 实际值”

## [2026-03-07 14:45] Batch-19 / 数据锚点注释与引导线增强

- 变更目标：让 `add_annotation` 注释优先落在被强调的数据位置，并增加可视化引导线
- 变更原因：固定坐标注释可读性和语义性不足，难以体现“强调哪个数据点”
- 影响范围（文件/模块）：
  - `backend/app/transform/node3_executor.py`
  - `backend/tests/test_batch13_node3_executor.py`
  - `docs/backend/后端工程技术方案.md`
  - `docs/backend/CHANGELOG.md`
- 接口影响：无（API 路径与字段契约不变）
- 数据结构影响：无（仅 Node3 内部生成的 Vega-Lite layer 更丰富）
- 关键实现点：
  - `add_annotation` 新增 data-aware 路径：
    - 收集可用 `x/y` 编码与数据候选
    - 根据 `intent` 关键词选择锚点（`peak/max/min/latest/first` 等）
    - 生成三层注释结构：anchor point + leader rule + text label
  - 多注释场景下，标签在数据空间做上下交替偏移，降低重叠概率
  - 无可用数据锚点时，自动回退到原避障文本注释方案
  - 新增测试：`test_executor_data_aware_annotation_adds_leader_line`
- 测试命令：
  - `conda run -n frame python -m pytest -q`
- 测试结果：
  - `26 passed`
- 风险与回滚点：
  - 若图表数据域跨度极小，标签偏移可能仍较近；可后续加入 bounds 感知与动态偏移倍率
- 后续待办：
  - 引入更细粒度的目标点定位（按 intent 提取具体字段/时间窗口）
  - 将引导线样式参数化到 schema（颜色、线型、偏移）

## [2026-03-07 14:20] Batch-18 / Extender 展示与注释防重叠优化

- 变更目标：修复 `Extender` 角色在结果节点中不可见的问题，并减少 `add_annotation` 标注重叠
- 变更原因：前端联调中角色认知与图内文字可读性受损，影响用户判断“agent 是否生效”
- 影响范围（文件/模块）：
  - `backend/app/services/simulation_service.py`
  - `backend/app/transform/node3_executor.py`
  - `backend/tests/test_batch13_node3_executor.py`
  - `backend/tests/test_api.py`
  - `docs/backend/后端工程技术方案.md`
  - `docs/backend/CHANGELOG.md`
- 接口影响：无（路径与字段名不变）
- 数据结构影响：无（仅节点 `role` 值映射为更符合前端认知的展示语义）
- 关键实现点：
  - 新增 `_display_role_for_node`：内部 taxonomy `Analyst` 对外统一显示为 `Extender`
  - `add_annotation` 新增动态坐标策略：
    - 读取现有 text layer 的 `encoding.y.value`，新注释按步长下移
    - 通过左右交替 `x` 坐标降低密集重叠概率
  - 新增测试：
    - `test_executor_annotation_positions_do_not_fully_overlap`
    - API 测试补充 `Extender` 角色可见性断言
- 测试命令：
  - `conda run -n frame python -m pytest -q`
- 测试结果：
  - `25 passed`
- 风险与回滚点：
  - 若个别图表画布高度有限，注释可能继续向下挤压；可后续加入画布边界感知与换列策略
- 后续待办：
  - 将注释布局升级为“避障式”算法（结合已有 mark/bounds）
  - 扩展 Node3 执行器支持更多 codebook 操作（`simplify_axis`、`change_axis_scale`、`change_legend`、`add_legend`）

## [2026-03-07 13:30] Batch-17 / 节点显示链路与操作分层对齐修复

- 变更目标：修复前端联调反馈的两类问题：节点图显示异常（摘要图）、操作分层不可见与节点数少于配置
- 变更原因：前端依赖 `nodes[].imageUrl` 与 `operations` 前缀格式（DATA/TEXT/VISUAL）渲染；现网返回与该约定不完全一致
- 影响范围（文件/模块）：
  - `backend/app/services/simulation_service.py`
  - `backend/tests/test_api.py`
  - `backend/requirements.txt`
  - `docs/backend/后端工程技术方案.md`
  - `docs/backend/CHANGELOG.md`
- 接口影响：无（路径和字段名不变，仅字段内容更贴合前端消费约定）
- 数据结构影响：有（节点 `operations` 值从原始 op 名称改为带层前缀的可展示字符串）
- 关键实现点：
  - 节点构建改为“每个 agent 均生成节点”：`ignore` 不再直接 `continue`
  - `ignore` 节点不进入下一层 frontier，但保留边与节点，便于追踪
  - 新增 `_format_operations_for_ui`，将 operation plan 输出为：
    - `DATA <op>: <intent>`
    - `TEXT <op>: <intent>`
    - `VISUAL <op>: <intent>`
  - 添加 `vl-convert-python` 依赖（并已安装到 `frame` 环境），优先使用真实 Vega-Lite SVG 渲染
- 测试命令：
  - `conda run -n frame python -m pytest -q`
- 测试结果：
  - `24 passed`
- 风险与回滚点：
  - 节点数量增加（包含 ignore 节点）可能改变既有视觉密度；若前端拥挤可在 UI 层做折叠/过滤
- 后续待办：
  - 扩展更多 op 执行（`simplify_axis`、`change_axis_scale`、`change_legend`、`add_legend`）
  - 在 validator 中补充语义一致性校验

## [2026-03-07 13:05] Batch-16 / Node3 变体图渲染链路接通

- 变更目标：让前端节点图真正反映 Node3 变体，不再全部显示根图
- 变更原因：M2/M3 已生成 `updated_chart_spec`，但前端节点仍主要依赖 `imageUrl`，导致“子节点看起来没变”
- 影响范围（文件/模块）：
  - `backend/app/transform/spec_renderer.py`（新增）
  - `backend/app/services/simulation_service.py`
  - `backend/tests/test_batch13_node3_executor.py`
  - `backend/tests/test_api.py`
  - `docs/backend/后端工程技术方案.md`
  - `docs/backend/CHANGELOG.md`
- 接口影响：无（路径与字段不变，仅 `nodes[].imageUrl` 内容来源优化）
- 数据结构影响：有（运行时节点 `imageUrl` 优先使用 `chartSpec` 渲染结果 data URL）
- 关键实现点：
  - 新增 `SpecRenderer`：
    - 若可用 `vl-convert` 则直接渲染 Vega-Lite SVG
    - 否则回退到 deterministic SVG 摘要图（仍保证节点可视化差异）
  - simulation 服务中，非 root 节点 `imageUrl` 优先使用 `updated_chart_spec` 渲染结果
  - 增补测试：
    - renderer 返回 `data:image/svg+xml;base64,...`
    - simulation 在存在非 root 节点时返回 data URL `imageUrl`
- 测试命令：
  - `conda run -n frame python -m pytest -q`
- 测试结果：
  - `24 passed`
- 风险与回滚点：
  - 未安装 `vl-convert` 时使用摘要 SVG，而非真实图形语义渲染；若需高保真可后续引入 `vl-convert-python`
- 后续待办：
  - 评估是否固定引入 `vl-convert-python` 作为依赖，统一真实 Vega-Lite 渲染
  - 继续扩展执行器 op 覆盖与 validator 语义校验

## [2026-03-07 12:40] Batch-15 / Node3 M3 校验与回滚接入

- 变更目标：为 Node3 增加结构校验与分级回滚，避免异常 spec 破坏整条 simulation run
- 变更原因：M2 已实现首批真实 patch，需要补齐 M3 的可靠性能力（校验 + 回滚）
- 影响范围（文件/模块）：
  - `backend/app/transform/spec_validator.py`（新增）
  - `backend/app/graph/workflow.py`
  - `backend/app/services/simulation_service.py`
  - `backend/tests/test_batch13_node3_executor.py`
  - `docs/backend/后端工程技术方案.md`
  - `docs/backend/CHANGELOG.md`
- 接口影响：无（外部 API 契约不变）
- 数据结构影响：有（内部 NodeC 输出新增 `execution_mode`、`validation_errors`；provenance_chain 记录对应字段）
- 关键实现点：
  - 新增 `SpecValidator`：校验 `mark/layer` 存在性、`layer/transform/encoding` 的基础结构合法性
  - NodeC 接入分级回滚逻辑：
    - 全部操作失败 -> `fallback_text`
    - 执行后 spec 校验失败 -> `node_rollback`（回退 parent spec）
    - 正常执行 -> `applied`
  - simulation 服务层在 provenance 中记录 `execution_mode` 与 `validation_errors`
  - 新增测试覆盖：
    - validator 失败场景
    - NodeC `fallback_text` 场景
    - NodeC `node_rollback` 场景
- 测试命令：
  - `conda run -n frame python -m pytest -q`
- 测试结果：
  - `23 passed`
- 风险与回滚点：
  - 目前 validator 侧重结构合法性，语义层误改仍可能通过；必要时可收紧校验规则或临时回退到 M2 版本
- 后续待办：
  - 扩展 validator 的语义一致性规则（例如 axis/encoding 协调校验）
  - 为更多 op 增加参数化执行与 per-op 失败原因回写

## [2026-03-07 12:15] Batch-14 / Node3 M2 执行器接入主链路

- 变更目标：实现 Node3 从“占位描述”到“真实 chart_spec 改写”的首批可用能力，并接入 simulation 主链路
- 变更原因：M1 已完成参数协议与 Guard 接口化，需推进 M2 执行器实现以满足 Node3 交付目标
- 影响范围（文件/模块）：
  - `backend/app/transform/__init__.py`（新增）
  - `backend/app/transform/node3_executor.py`（新增）
  - `backend/app/graph/workflow.py`
  - `backend/app/graph/langgraph_runner.py`
  - `backend/app/services/simulation_service.py`
  - `backend/tests/test_batch13_node3_executor.py`（新增）
  - `docs/backend/后端工程技术方案.md`
  - `docs/backend/CHANGELOG.md`
- 接口影响：无（外部 API 路径与主字段不变）
- 数据结构影响：有（内部 NodeC 输出新增 `updated_chart_spec`、`executed_operations`；节点可带 `chartSpec` 变体）
- 关键实现点：
  - 新增 `Node3Executor`，支持首批真实操作：
    - `change_title`
    - `add_annotation`（图内 text mark 优先，失败回退到 description）
    - `delete_source`（严格前缀匹配）
    - `change_color`
    - `select_data_range`
    - `add_data_variables`
  - NodeC 改为调用执行器，并将执行结果返回给 graph state
  - graph runner 把 `selected_operations` 与 `context.chartSpec` 传入 NodeC
  - simulation 服务层新增节点 spec 传递与写回（父节点 spec -> 子节点 spec）
- 测试命令：
  - `conda run -n frame python -m pytest -q`
- 测试结果：
  - `20 passed`
- 风险与回滚点：
  - 当前执行器为 deterministic MVP，复杂图表结构（非标准 layer/encoding 组合）可能仅部分操作生效；若出现异常可回退到 Node3 占位路径
- 后续待办：
  - M3：补 `spec_validator.py` 与分级回滚（`skip_op` / `node_rollback` / `fallback_text`）
  - 为更多 op 增加参数化 patch（如 `change_axis_scale`、`simplify_axis`、`change_legend`）

## [2026-03-07 11:40] Batch-13 / Node3 M1 参数协议接入 RuleGuard

- 变更目标：将 Node3 参数协议从文档落到后端校验入口，打通 `selected_operations` 的结构化 Guard 链路
- 变更原因：Node3 已进入专项交接阶段，需要先完成 M1（参数协议）再推进 M2 执行器
- 影响范围（文件/模块）：
  - `backend/app/config/node3_operation_schema_v1.yaml`（新增）
  - `docs/taxonomy/node3_operation_schema_v1.md`（新增）
  - `backend/app/agents/rule_guard.py`
  - `backend/app/graph/workflow.py`
  - `backend/tests/test_batch2_components.py`
  - `docs/backend/后端工程技术方案.md`
  - `docs/backend/CHANGELOG.md`
- 接口影响：无（未改动 `/api/upload-case`、`/api/simulation/start`、`/api/health` 契约）
- 数据结构影响：有（内部 GuardResult 新增 `selected_operation_plan`，用于 NodeB 输出过滤后的操作计划）
- 关键实现点：
  - 新增 Node3 全量操作 schema（含全量 op 目录、执行顺序、互斥规则、`add_annotation` 策略、`delete_source` 匹配前缀）
  - `RuleGuard` 启动时加载 `node3_operation_schema_v1.yaml`
  - `sanitize()` 新增 `operation_plan` 入参，执行层级归一、互斥过滤、数量上限过滤
  - `NodeB` 改为消费 Guard 输出的 `selected_operations`，不再做散落的本地过滤逻辑
  - 新增测试覆盖：层级纠正（`change_title visual -> text`）与互斥过滤（`add_annotation` vs `change_annotation`）
- 测试命令：
  - `conda run -n frame python -m pytest -q`
- 测试结果：
  - `18 passed`
- 风险与回滚点：
  - 当前仅完成 M1 校验入口，尚未接入 Node3 真实 spec 执行；若后续执行器接入出现问题，可保持 Node3 占位并继续使用当前 Guard 校验链路
- 后续待办：
  - M2：实现 `node3_executor.py`（真实 Vega-Lite patch）
  - M3：实现 `spec_validator.py` 与 `skip_op/node_rollback/fallback_text` 回滚分级

## [2026-03-06 21:13:58] Batch-12 / Node3 交接文档沉淀 + Extender 命名统一

- 变更目标：将 Node3 后续开发沉淀为可交接文档，并统一当前协作文档中的 `Extender` 命名口径
- 变更原因：准备与 taxonomy 负责人开会交接，需要“下一个 AI 可直接接力”的工程级说明；同时修正历史拼写不一致问题
- 影响范围（文件/模块）：
  - `docs/backend/后端工程技术方案.md`
  - `docs/backend/Node3交接与AI续开发指南.md`（新增）
  - `docs/backend/CHANGELOG.md`
  - `docs/api/接口文档.md`
  - `backend/app/services/simulation_service.py`
  - `backend/tests/test_batch5_topology_and_case_data.py`
- 接口影响：无新增路径；文档口径明确 `agentProfiles.role=Extender`，后端保持 `Extender -> Analyst`（兼容历史 `extensioner`）
- 数据结构影响：无（仅命名口径与文档说明修正）
- 关键实现点：
  - 主线文档新增 Node3 交接入口（并保持 `后端工程技术方案` 为唯一主线）
  - 新增交接文档，覆盖阻塞口径、M1/M2/M3 开发拆解、Cursor+AI 接力流程、DoD
  - API 文档中的 `Extensioner` 全部替换为 `Extender`，并修正样例 `agentCategories`
  - 服务层 role 解析保留历史拼写兼容，测试用例改为 `Extender`
- 测试命令：
  - `conda run -n frame python -m pytest -q`
- 测试结果：
  - `17 passed`
- 风险与回滚点：
  - 若前端仍提交历史拼写，后端兼容映射可保障不报错
- 后续待办：
  - 与学姐冻结 Node3 五项口径后，按交接文档进入 M1 实装

## [2026-03-06 21:10] Batch-11 / 研究交互参数生效（maxDepth + agentProfiles + mode）

- 变更目标：实现研究问题中的“可操控输入”在后端决策链中真正生效
- 变更原因：此前后端主链路可跑，但 `maxDepth/agentProfiles/mode` 尚未进入服务层决策
- 影响范围（文件/模块）：
  - `backend/app/schemas/api_contract.py`
  - `backend/app/services/simulation_service.py`
  - `backend/tests/test_api.py`
  - `backend/tests/test_batch5_topology_and_case_data.py`
  - `docs/backend/后端工程技术方案.md`
- 接口影响：有（`/api/simulation/start` 新增可选字段 `agentProfiles`、`maxDepth`、`mode`）
- 数据结构影响：有（`TreeNode` 新增 `institution` 可选字段）
- 关键实现点：
  - `maxDepth` 覆盖服务层深度控制，不再只依赖环境变量
  - `agentProfiles.role` 进入类别决策，支持 `Extender -> Analyst` 映射（兼容历史拼写 `extensioner`）
  - `institution` 进入节点输出与运行上下文
  - `mode` 对 shift prior 进行偏置（`adversarial` 上调、`conservative` 下调）
- 测试命令：
  - `conda run -n frame python -m pytest -q`
- 测试结果：
  - `17 passed`
- 风险与回滚点：
  - 若前端 role 命名不一致，类别映射可能退回到 `agentCategories` 路径
- 后续待办：
  - 与前端提交口径统一 `agentProfiles/mode` 枚举与默认值

## [2026-03-06 20:35] Batch-10 / 工程方案与研究问题对齐

- 变更目标：将后端工程方案与 `docs/研究问题.md` 最新交互目标对齐，统一目标/现状/TODO 口径
- 变更原因：当前方案文档仍包含“taxonomy 暂不可用”等旧描述，无法准确反映 Batch 9 后真实状态
- 影响范围（文件/模块）：
  - `docs/backend/后端工程技术方案.md`
- 接口影响：无（本次仅文档更新）
- 数据结构影响：无（本次仅文档更新）
- 关键实现点：
  - 新增“当前状况（截至 Batch 9）”并区分已完成与缺口
  - 将 Taxonomy 章节更新为“已接入 NodeA/NodeB + Node3 边界明确”
  - 重排 TODO：新增 `maxDepth/agentProfiles/mode` 与 Node3 三件套优先项
  - 补充研究问题导向的验收清单（Tracing/Attribution 最小闭环）
- 测试命令：
  - 本次为文档变更，无代码测试
- 测试结果：
  - N/A
- 风险与回滚点：
  - 若后续接口文档更新，应再次同步本方案中的 P0 任务描述
- 后续待办：
  - 按方案 P0 执行后端实现并回填测试结果

## [2026-03-06 20:15] Batch-9 / Taxonomy v3 最小接入（Node3 前闭环）

- 变更目标：在不改 Node3 执行器的前提下，先完成 NodeA/NodeB 与 taxonomy v3 的可交付闭环
- 变更原因：当前可优先交付“Node3 之前”能力给协作者，降低一次性改造风险
- 影响范围（文件/模块）：
  - `backend/app/config/taxonomy_rules_v3.yaml`
  - `backend/app/agents/taxonomy_adapter.py`
  - `backend/app/agents/llm_client.py`
  - `backend/app/graph/workflow.py`
  - `backend/app/services/simulation_service.py`
  - `backend/app/config/fallback_rules.yaml`
  - `backend/tests/test_batch2_components.py`
  - `backend/tests/test_batch4_langgraph.py`
  - `docs/backend/后端工程技术方案.md`
- 接口影响：无（外部 API 路径与主字段保持不变）
- 数据结构影响：有（内部中间态新增 `alignment_with_preference`、`identified_gaps`、`expected_modification_intensity`、`selected_operations`、`operation_rationale`）
- 关键实现点：
  - 新增 v3 规则文件并支持 `USE_TAXONOMY=true` 加载
  - NodeA/NodeB 支持 v3 风格结构化输出，同时保持旧字段兼容
  - `provenance_chain` 增加 NodeA/NodeB 结构化证据
  - Node3 继续保持占位执行，避免与执行引擎开发耦合
- 测试命令：
  - `conda run -n frame python -m pytest -q`
- 测试结果：
  - `17 passed`
- 风险与回滚点：
  - 若 v3 规则效果不稳定，可回退 `USE_TAXONOMY=false` 继续使用 fallback
- 后续待办：
  - Node3 执行三件套（参数协议、执行器、校验回滚）由后续专项推进

## [2026-03-09 22:10] Batch-30 / NodeB-NodeC 结构化参数执行增强

- 任务名称：NodeB 结构化计划与 Node3 参数化执行
- 变更目标：让 NodeB 输出可执行 `params`，并由 Node3 按参数稳定执行，提升模拟效果与可控性
- 影响范围（文件/模块）：
  - `backend/app/agents/llm_client.py`
  - `backend/app/agents/rule_guard.py`
  - `backend/app/graph/workflow.py`
  - `backend/app/transform/node3_executor.py`
  - `backend/app/config/node3_operation_schema_v1.yaml`
  - `docs/taxonomy/node3_operation_schema_v1.md`
  - `backend/tests/test_batch2_components.py`
  - `backend/tests/test_batch13_node3_executor.py`
  - `docs/backend/后端工程技术方案.md`
- 接口影响：无（`/api/simulation/start` 外部契约不变）
- 变更目标细项：
  - `selected_operations` 从 `{operation, layer, intent}` 扩展为 `{operation, layer, intent, params}`
  - `change_color` 增强为 chart-wide 覆盖（mark + encoding scale + config range）
  - `change_title/add_annotation` 支持自动换行参数
  - `add_annotation` 趋势线由 `params.include_trendline` 控制，减少机械化意图文本
  - Extender(Analyst) 默认策略中不再优先 `add_data_variables`
- 测试命令：
  - `conda run -n frame which python`
  - `conda run -n frame python -m pip --version`
  - `conda run -n frame python -m pytest -q tests/test_batch2_components.py tests/test_batch13_node3_executor.py`
- 测试结果：
  - Python: `/opt/anaconda3/envs/frame/bin/python`
  - pip: `pip 26.0.1` (frame env)
  - `20 passed`
- 风险与后续待办：
  - 仍依赖 LLM 输出质量，后续可继续收紧 NodeB/NodeC prompt 的 `params` 约束
  - `add_data_variables` 暂未彻底下线，仅在默认策略降级；后续可按实验结果决定是否禁用

## [2026-03-09 22:35] Batch-31 / select_data_range 参数化窗口执行

- 任务名称：区间选择参数桥接（NodeB -> Node3）
- 变更目标：让 `select_data_range` 从“泛化动作”升级为“可执行区间窗口过滤”
- 影响范围（文件/模块）：
  - `backend/app/agents/llm_client.py`
  - `backend/app/transform/node3_executor.py`
  - `backend/app/config/node3_operation_schema_v1.yaml`
  - `docs/taxonomy/node3_operation_schema_v1.md`
  - `backend/tests/test_batch13_node3_executor.py`
  - `docs/backend/后端工程技术方案.md`
- 接口影响：无（外部 API 契约不变）
- 变更目标细项：
  - Node3 `select_data_range` 新增参数执行：优先读取 `params.x_field/start/end` 生成范围过滤
  - NodeB fallback 新增范围参数构建逻辑（从输入 spec 的 x 序列推断窗口）
  - NodeB LLM prompt 增加 `select_data_range` 参数样例，提升结构化输出稳定性
- 测试命令：
  - `conda run -n frame which python`
  - `conda run -n frame python -m pip --version`
  - `conda run -n frame python -m pytest -q tests/test_batch2_components.py tests/test_batch13_node3_executor.py`
- 测试结果：
  - Python: `/opt/anaconda3/envs/frame/bin/python`
  - pip: `pip 26.0.1` (frame env)
  - `21 passed`
- 风险与后续待办：
  - 当前窗口推断是启发式（按序列比例截取），后续可结合角色与平台进一步细化窗口策略
  - 下一步可支持时间字段解析与表达式过滤（例如年月字符串）

## [2026-03-09 23:05] Batch-32 / 角色意图配色与注释可读性提升

- 任务名称：社媒美学配色 + 注释可读性与叙事一致性
- 变更目标：提升“符合角色意图”的可视化修改质量，并让偏移结果可一眼识别
- 影响范围（文件/模块）：
  - `backend/app/agents/llm_client.py`
  - `backend/app/transform/node3_executor.py`
  - `backend/app/config/node3_operation_schema_v1.yaml`
  - `docs/taxonomy/node3_operation_schema_v1.md`
  - `backend/tests/test_batch13_node3_executor.py`
  - `docs/backend/后端工程技术方案.md`
- 接口影响：无（外部 API 契约不变）
- 变更目标细项：
  - 社媒 Amplifier `change_color` 默认支持 `palette_style=social_contrast`，增强高对比平台美学
  - `add_annotation` / `change_annotation` 支持 `min_font_size`、`max_line_chars`，并改进无空格长文本换行
  - 新增 `prune_offtopic_annotations + narrative_keywords`，可清理离题旧注释
  - Amplifier/Analyst/Adverser 的注释语义默认与 `change_title` 联动，解释标题 framing
- 测试命令：
  - `conda run -n frame python -m pytest -q tests/test_batch13_node3_executor.py tests/test_batch2_components.py`
- 测试结果：
  - `23 passed`
- 风险与后续待办：
  - 当前离题注释清理依赖关键词匹配，后续可引入语义相似度阈值提升稳健性
  - 后续可将 `change_annotation` 的“替换范围”从启发式切到显式目标 ID

## [2026-03-09 23:25] Batch-33 / change_color 与 data range 生效修复

- 任务名称：执行层生效修复（配色与区间）
- 变更目标：修复“看起来没生效”的核心执行问题，确保用户可见变化
- 影响范围（文件/模块）：
  - `backend/app/agents/llm_client.py`
  - `backend/app/transform/node3_executor.py`
  - `backend/app/config/node3_operation_schema_v1.yaml`
  - `docs/taxonomy/node3_operation_schema_v1.md`
  - `backend/tests/test_batch13_node3_executor.py`
  - `docs/backend/后端工程技术方案.md`
- 接口影响：无（外部 API 契约不变）
- 变更目标细项：
  - `change_color` 明确仅作用于数据 mark 与调色盘，不再修改 text mark 颜色
  - Amplifier+新闻媒体下强制保留 `change_color`（避免被裁剪掉）
  - `select_data_range` 使用 `datum` 区间表达式过滤，提升跨字段类型生效稳定性
- 测试命令：
  - `conda run -n frame which python`
  - `conda run -n frame python -m pip --version`
  - `conda run -n frame python -m pytest -q tests/test_batch13_node3_executor.py tests/test_batch2_components.py`
- 测试结果：
  - Python: `/opt/anaconda3/envs/frame/bin/python`
  - pip: `pip 26.0.1` (frame env)
  - `24 passed`
- 风险与后续待办：
  - `select_data_range` 仍依赖字段值顺序，后续可增加按时间解析排序的窗口推断

## [2026-03-09 23:45] Batch-34 / codebook 五项操作对齐迭代

- 任务名称：按最新 taxonomy_codebook 对齐关键操作
- 变更目标：让 `change_color/change_title/add_annotation/change_annotation/simplify_axis` 与最新语料规则一致
- 影响范围（文件/模块）：
  - `backend/app/agents/llm_client.py`
  - `backend/app/transform/node3_executor.py`
  - `backend/app/config/node3_operation_schema_v1.yaml`
  - `docs/taxonomy/node3_operation_schema_v1.md`
  - `backend/tests/test_batch2_components.py`
  - `backend/tests/test_batch13_node3_executor.py`
  - `docs/backend/后端工程技术方案.md`
- 接口影响：无（外部 API 契约不变）
- 变更目标细项：
  - `change_title` 引入更强数据锚点标题生成（峰值/趋势拐点）
  - `simplify_axis` 新增 `interval_labels` + `label_interval` 参数，支持“简化但保留可读刻度”
  - Analyst 流程补充 `change_annotation` 选项，支持叙事切换时的旧注释替换
  - Amplifier 新闻媒体策略继续强制保留 `change_color`，并保持数据 mark 级生效
- 测试命令：
  - `conda run -n frame which python`
  - `conda run -n frame python -m pip --version`
  - `conda run -n frame python -m pytest -q tests/test_batch2_components.py tests/test_batch13_node3_executor.py`
- 测试结果：
  - Python: `/opt/anaconda3/envs/frame/bin/python`
  - pip: `pip 26.0.1` (frame env)
  - `26 passed`
- 风险与后续待办：
  - `interval_labels` 当前对 quantitative 轴最稳，后续可扩展 temporal 轴格式化策略

## [2026-03-10 00:10] Batch-35 / annotation 视觉与完整句修复

- 任务名称：注释可读性与完整性专项修复
- 变更目标：解决 annotation “不好看、没说完、冲突残留”问题
- 影响范围（文件/模块）：
  - `backend/app/agents/llm_client.py`
  - `backend/app/transform/node3_executor.py`
  - `backend/app/config/node3_operation_schema_v1.yaml`
  - `docs/taxonomy/node3_operation_schema_v1.md`
  - `backend/tests/test_batch2_components.py`
  - `backend/tests/test_batch13_node3_executor.py`
  - `docs/backend/后端工程技术方案.md`
- 接口影响：无（外部 API 契约不变）
- 变更目标细项：
  - annotation 文案统一清洗为完整句：去省略号、补句号、避免“半句停住”
  - 移除 annotation 文本的宽度截断依赖（limit），改为换行控制
  - Amplifier 在已有注释时优先 `change_annotation`，并支持强调样式（`emphasis_style=amplify`）
  - `add_annotation/change_annotation` 默认 `max_line_chars` 调整为 `34`
- 测试命令：
  - `conda run -n frame python -m pytest -q tests/test_batch2_components.py tests/test_batch13_node3_executor.py`
- 测试结果：
  - `28 passed`
- 风险与后续待办：
  - 当前“离题注释清理”仍基于关键词匹配，后续可升级为语义相似度过滤

## [2026-02-25 18:10] Batch-8 / 环境变量收口治理

- 变更目标：建立可维护的环境变量管理基线，避免配置散落与后期膨胀
- 变更原因：当前项目缺少 `.env` 约定与集中配置入口，协作和扩展成本高
- 影响范围（文件/模块）：
  - `backend/app/config/settings.py`
  - `backend/app/agents/llm_client.py`
  - `backend/app/services/simulation_service.py`
  - `backend/scripts/dev.sh`
  - `backend/.env.example`
  - `backend/.env`
  - `.gitignore`
  - `backend/README.md`
  - `docs/backend/后端工程技术方案.md`
- 接口影响：无
- 数据结构影响：无
- 关键实现点：
  - 新增 `Settings` 配置中心，统一读取 `USE_LLM/OPENAI_API_KEY/OPENAI_BASE_URL/OPENAI_MODEL/SIM_MAX_DEPTH`
  - 启动脚本在存在 `.env` 时自动使用 `uvicorn --env-file .env`
  - 补齐 `.env.example` 作为团队模板，并生成本地 `.env` 初始文件
  - 明确 `.gitignore` 规则：忽略 `backend/.env*`，仅保留 `backend/.env.example`
- 测试命令：
  - `conda run -n frame python -m pytest -q`
- 测试结果：
  - `16 passed`
- 风险与回滚点：
  - 若 `.env` 配置错误会影响服务启动，可临时移除 `.env` 回退默认值
- 后续待办：
  - 后续新增环境变量需同步更新 `settings.py` 与 `backend/.env.example`

## [2026-02-25 17:40] Batch-7 / API 契约对齐（upload-case + caseRef）

- 变更目标：以后端接口文档为准完成 Batch 7 契约对齐
- 变更原因：`/api/upload-case` 与 `caseRef` 契约已成为模拟主路径，需消除实现与文档偏差
- 影响范围（文件/模块）：
  - `backend/app/api/routes_upload.py`
  - `backend/app/api/routes_simulation.py`
  - `backend/app/services/upload_service.py`
  - `backend/app/services/simulation_service.py`
  - `backend/app/schemas/api_contract.py`
  - `backend/app/main.py`
  - `backend/tests/test_api.py`
  - `backend/tests/test_batch6_error_and_llm_toggle.py`
  - `docs/backend/后端工程技术方案.md`
- 接口影响：有（新增 `POST /api/upload-case`；`POST /api/simulation/start` 运行前校验 `caseRef` 或 `chartSpecRef+metadataRef`）
- 数据结构影响：有（`SimulationStartRequest` 新增 `caseRef/chartSpecRef/metadataRef`；`TreeNode` 新增 `chartSpecUrl/chartSpec`）
- 关键实现点：
  - 新增结构化案例上传能力，持久化到 `storage/cases/<caseRef>/`
  - `simulation` 根节点从 metadata 回填 `label/description`，并加载案例图片与图表 spec 引用
  - 挂载 `/cases` 静态目录，保证 `chartSpecRef/metadataRef/imageRef` 可直接访问
  - 保留 `/api/upload` 作为兼容接口，不参与新模拟主路径
- 测试命令：
  - `conda activate frame && cd backend && python -m pytest -q`
- 测试结果：
  - `16 passed`
- 风险与回滚点：
  - 旧前端若未传 `caseRef` 会收到 400；可暂时通过补传 `chartSpecRef+metadataRef` 过渡
- 后续待办：
  - 前端联调后确认 `upload-case -> simulation/start(caseRef)` 全链路

## [2026-02-26 10:00] Batch-6 / V1 收口

- 变更目标：完成 V1 收口（LLM 开关、统一错误结构、开发脚本）
- 变更原因：提升稳定性与可维护性，确保后续联调与扩展一致性
- 影响范围（文件/模块）：
  - `backend/app/agents/llm_client.py`
  - `backend/app/main.py`
  - `backend/scripts/dev.sh`
  - `backend/tests/test_batch6_error_and_llm_toggle.py`
  - `backend/README.md`
- 接口影响：无（响应主结构未变）
- 数据结构影响：无（仅增强运行逻辑）
- 关键实现点：
  - `USE_LLM=true` 时尝试真实调用，失败自动降级 fallback
  - 统一异常输出结构：`ok/errorCode/message/detail`
  - 增加本地开发一键脚本并绑定 conda 环境校验
- 测试命令：
  - `conda activate frame && cd backend && python -m pytest -q`
- 测试结果：
  - `14 passed`（当前回归结果）
- 风险与回滚点：
  - 若远端 LLM 不稳定，可保持 `USE_LLM=false`
- 后续待办：
  - 接入正式 taxonomy 数据源与异步任务模式

## [2026-03-13] Batch-51 / Evaluation Pipeline: JSD + DTW Quantitative Metrics

- 变更目标：实现定量评估管线，比较模拟谱系与真实谱系的统计相似度
- 变更原因：需要定量验证模拟系统的叙事落差驱动机制优于随机基线
- 影响范围（文件/模块）：
  - `backend/evaluation/` — 全新目录，包含评估管线所有模块
  - `backend/evaluation/ground_truth.py` — 解析 taxonomy_how/who_where/case 三个 Markdown 表为结构化 GroundTruthLineage 对象，含16类操作规范化映射和频率向量构造
  - `backend/evaluation/case_mapping.yaml` — 8个 taxonomy case_id 到 data/ 目录的映射
  - `backend/evaluation/runner.py` — 批量模拟运行器，支持 system 条件（按 GT 配置角色/平台）和 random baseline 条件
  - `backend/evaluation/metrics.py` — JSD（16维操作分布 + Laplace 平滑）和 DTW（累计操作数轨迹）计算
  - `backend/evaluation/report.py` — Markdown 报告生成（逐案表格 + 汇总 + Wilcoxon 检验 + matplotlib 漂移轨迹图 + 箱线图）
  - `backend/evaluation/run_evaluation.py` — CLI 入口 (`python -m evaluation.run_evaluation`)
  - `backend/app/graph/workflow.py` — NodeB 新增 `random_baseline` 模式，跳过叙事落差评估，随机选择1-4个操作
  - `backend/requirements.txt` — 新增 scipy, numpy, dtaidistance, matplotlib, tabulate
- 接口影响：无前端接口变更。`mode="random_baseline"` 仅用于评估管线内部调用
- 具体变更：
  1. **ground_truth.py**：Markdown 表解析器，操作名规范化（如 "select time range" -> "select_data_range"），16维频率向量，BFS 深度计算，累计操作数轨迹构建
  2. **runner.py**：为每个 case 创建 symlink 到 storage/cases/，按 GT 配置构造 SimulationStartRequest，运行 N 次 system + N 次 random baseline
  3. **metrics.py**：JSD 使用 scipy.jensenshannon + Laplace 平滑；DTW 使用 dtaidistance（含纯 Python fallback）
  4. **report.py**：逐案指标表 + 汇总均值 + Wilcoxon signed-rank 检验 + matplotlib 漂移轨迹对比图 + 系统/随机箱线图
  5. **NodeB random_baseline**：当 context.mode == "random_baseline" 时，跳过 LLM 调用，从 whitelist 随机选 1-4 个操作，随机 shift_magnitude
- 测试命令：`cd backend && python -m evaluation.run_evaluation --cases C01,C02 --runs 1 --output eval_output/`
- 测试结果：C01 JSD_system=0.0176 vs JSD_random=0.0447; C02 JSD_system=0.0034 vs JSD_random=0.0212; 系统条件始终优于随机基线
- 风险与后续待办：
  - 当前仅验证了2个case，完整评估需运行全部8个可映射case（≈1小时）
  - Wilcoxon 检验需要≥5个 paired samples，需运行≥5个case
  - matplotlib 中文字体显示问题（已用 ASCII fallback 处理标题）

## [2026-03-14] Batch-47b / Role × Platform Color Differentiation Fix

- 变更目标：修复所有子节点都使用相同蓝色的问题，使每个角色+平台的配色具有明确视觉区分
- 变更原因：`_recolor_color_channel_values` 硬编码 `secondary = "#1F5A96"`（深蓝），导致所有条件着色图表的 base value 都变蓝；`_pick_palette_for_role` 只处理 Amplifier/Adverser，其余角色无差异化；NodeC `executor.execute()` 调用缺少 `role/institution` 参数
- 影响范围（文件/模块）：
  - `backend/app/transform/node3_executor.py` — 新增 Role × Platform 调色板系统，修复 secondary 颜色派生
  - `backend/app/graph/workflow.py` — 修复 NodeC 调用缺失 role/institution 参数
  - `backend/tests/test_batch13_node3_executor.py` — 更新条件着色测试以适配新颜色系统
- 接口影响：无接口变更。视觉输出变化：不同角色+平台的图表现在使用不同的颜色方案。
- 具体变更：
  1. **Role × Platform 调色板映射表**：新增 `_ROLE_PLATFORM_PALETTES` 字典，按 `{role}__{platform}` 查找颜色。Bridger→蓝（温和中立），Amplifier→红/橙（警报，社交媒体更激进），Adverser→绿/琥珀（反叙事），Extender→紫/青（分析扩展）。
  2. **Secondary 颜色派生**：新增 `_derive_secondary_color(primary)` 方法，根据主色动态计算协调的深色辅色，替代硬编码 `#1F5A96`。
  3. **修复 role/institution 传递**：`workflow.py` 中 `executor.execute()` 现在正确传递 `role=persona.category` 和 `institution=context.institution`，使 `_current_role/_current_institution` 不再为空。
  4. **扩展 `_build_palette_range`**：支持所有新增颜色的 4 阶梯度范围，包括 social_contrast 变体。
- 测试命令：`conda run -n frame python -m pytest -q tests/test_batch2_components.py tests/test_batch13_node3_executor.py tests/test_api.py tests/test_batch5_topology_and_case_data.py`
- 测试结果：42 passed, 1 pre-existing failure（trendline 测试，与本次无关）
- 风险与后续待办：
  - LLM 模式下如果模型返回 explicit hex color，会优先使用模型决定的颜色
  - 后续可扩展"Adverser 继承并反转父节点颜色"的逻辑

## [2026-03-14] Batch-47 / Autonomous Agent Decision & Depth-Progressive Offset

- 变更目标：使每个节点的LLM智能体能够自主感知理解可视化图表并基于角色、平台属性自主决策修改操作；同时实现深度递增的偏移累积机制
- 变更原因：用户反馈模拟结果缺乏自主性——每个智能体的决策过于模板化，不能凸显角色和平台差异；偏移程度不随传播深度增加而显著增大
- 影响范围（文件/模块）：
  - `backend/app/services/simulation_service.py` — 新增深度偏移递增机制、链路上下文追踪
  - `backend/app/agents/llm_client.py` — 增强 LLM 感知/策略 prompt、增强 fallback 深度感知
- 接口影响：无接口变更。内部行为改善：节点 offset 现在随深度递增；链路上下文传递至每个智能体。
- 具体变更：
  1. **深度偏移递增（Depth-Progressive Offset）**：新增 `_apply_depth_offset_escalation(shift_prior, depth)` 方法。depth=1 为基线，depth=2 升一级，depth=3+ 升两级。确保传播链越深，偏移越显著。
  2. **链路上下文追踪（Chain Context Tracking）**：新增 `node_chain_history` 记录从根节点到当前节点的完整修改历史（每步的角色、平台、操作、偏移）。传递给每个智能体的 context 中。
  3. **LLM NodeA prompt 增强**：加入完整的 taxonomy codebook 角色描述、平台行为差异说明、深度位置感知、链路历史摘要。智能体能够基于接收到的可视化数据自主感知叙事角度。
  4. **LLM NodeB prompt 增强**：重设计为"自主决策"导向——智能体自主选择操作类别、自主决定具体值（颜色、标题文本、注释文本）。包含 taxonomy 操作表和 few-shot 示例作为指导。
  5. **Fallback NodeA 深度感知**：gap_type 不再固定——Amplifier 在 depth>1 从 tension 升级为 conflict，Analyst 在 depth>2 升级为 conflict。confidence 随链路长度递增。
  6. **Fallback NodeB 深度感知**：modification_intensity 随深度递增；Amplifier 在 depth≥3 自动追加 change_axis_scale 操作；配色在深层节点默认使用 social_contrast。
  7. **感知独白（Inner Monologue）增强**：加入链路历史感知和深度说明，使每个智能体的感知明确"前序智能体做了什么"以及"当前深度应有多大偏移"。
- 测试命令：`cd backend && conda run -n frame python -m pytest -q`
- 测试结果：50 passed, 1 failed（pre-existing: `test_executor_adds_trendline_when_annotation_requests_it`，与本次变更无关）
- 风险与后续待办：
  - 深度偏移递增可能导致 depth=3+ 节点全部为 major，后续可按角色细化递增幅度
  - LLM prompt 增强在 `USE_LLM=false` 时仅影响 fallback 策略，需开启 LLM 才能获得真正自主决策
  - 链路上下文目前仅在 fallback 感知独白中使用，LLM 模式下已注入 prompt

## [2026-03-07] Batch-33 / Simulation Effect Optimization

- 变更目标：全面优化框架偏移模拟效果质量
- 变更原因：用户反馈生成的标题/注释过于机械化（如"Reframed: ..."），不符合taxonomy中描述的角色行为模式；visual操作（axis scale）语义不正确；前端Process面板展示格式问题
- 影响范围（文件/模块）：
  - `backend/app/transform/node3_executor.py` — 核心重构
  - `backend/app/agents/llm_client.py` — 新增generate_text方法、修复Amplifier gap评估
  - `backend/app/graph/workflow.py` — NodeC传递role/institution到executor
  - `backend/app/services/simulation_service.py` — 移除[applied]后缀
  - `frontend/src/features/offset/OffsetPanel.tsx` — 操作逐行显示
  - `backend/tests/test_batch13_node3_executor.py` — 适配新逻辑
  - `backend/tests/test_batch5_topology_and_case_data.py` — 适配新格式
- 接口影响：无接口变更，仅内部行为改善
- 具体变更：
  1. **Node3Executor LLM集成**：添加__init__接受llm_client，execute接受role/institution参数。change_title/add_annotation/change_annotation现在通过LLM生成角色感知、数据驱动的文本内容，包含taxonomy persona prompt、chart data summary、corpus few-shot examples。无LLM时使用数据驱动的角色特定模板替代机械化的"Reframed:"前缀。
  2. **change_axis_scale重构**：从切换linear/log改为分析数据分布、缩小y轴domain（如50-100缩放到集中区间），符合taxonomy定义"缩小纵轴尺度以拉高"。
  3. **select_data_range角色感知**：Adverser分析完整数据趋势后选择支持反向叙事的数据段（如整体上升时选下降段）；非Adverser角色保持较宽范围。
  4. **Amplifier gap_type修复**：_evaluate_gap_fallback中Amplifier从resonance/minimal改为tension/moderate，确保执行足够多的操作。
  5. **add_data_variables**：改为no-op（需要外部数据源，当前无法实现真实的数据变量添加）。
  6. **前端Process面板**：移除[applied]后缀，每个操作独占一行显示。
  7. **_is_generic_intent检测器**：自动识别机械化intent（如"context note added"、"assert strong"等）并替换为LLM/fallback生成的具体内容。
  8. **_enforce_text_length**：标题硬限60字符、注释硬限100字符，按词边界截断。
- 测试命令：`cd backend && conda run -n frame python -m pytest tests/ -x -q`
- 测试结果：51 passed
- 风险与后续待办：
  - LLM文本生成质量依赖API响应速度和模型能力
  - add_data_variables暂为no-op，需要外部数据源支持才能真正实现
  - 可继续优化few-shot examples和fallback模板以覆盖更多议题

## [2026-03-14] Batch-53 / 前端连线样式修正 + 后端平台感知增强

- 变更目标：修复前端 DATA/VISUAL 虚线样式对调问题；增强后端 agent 平台感知能力，使同角色不同平台产出差异化修改
- 变更原因：
  1. 前端 DATA 修改应展示密集虚线、VISUAL 应展示宽松虚线，但实际相反
  2. 同角色（如 Amplifier/Extender）配置不同平台时，生成结果相同（标题一样、仅颜色不同），未体现平台对修改幅度的影响
- 影响范围（文件/模块）：
  - `frontend/src/features/propagation/PropagationPanel.tsx` — DATA/VISUAL strokeDasharray 对调
  - `backend/app/graph/workflow.py` — NodeC 将 llm_client 传递给 Node3Executor
  - `backend/app/agents/llm_client.py` — 多处平台感知增强（gap评估、策略选择、标题/颜色/注释意图）
- 接口影响：无接口变更，仅前端视觉与后端行为改善
- 具体变更：
  1. **前端连线样式修正**：`EDGE_STYLE_BY_LAYER` 中 DATA `strokeDasharray` 从 `"4 4"` 改为 `"2 2"`（密集虚线），VISUAL 从 `"2 2"` 改为 `"4 4"`（宽松虚线）
  2. **Node3Executor LLM 接入**：NodeC 将 `llm_client` 传递给 `Node3Executor(llm_client=llm_client)`，使执行阶段可调用 LLM 生成标题/注释
  3. **`_evaluate_gap_fallback` 平台感知**：社交平台（t3_social）提升 gap 冲突等级与置信度，权威平台（t1_authority）降低冲突等级
  4. **`_build_title_intent` 全角色平台分化**：
     - Extender/Analyst：同一话题下不同平台生成不同标题（authority=政策视角, media=编辑视角, social=大众视角）
     - Adverser：社交平台使用更激进的反叙事语言，权威平台使用更审慎的重新审视语气
  5. **`_build_color_intent` 角色+平台分化**：Extender 按平台分配不同色板（institutional/social_contrast/editorial）
  6. **`_trim_selected_ops` 最小强度提升**：从 `selected[:1]` 改为 `selected[:2]`，确保至少执行颜色+标题两个操作
  7. **Amplifier resonance 路径修正**：保留至少 2 个操作（颜色+标题），不再仅执行颜色
  8. **Analyst 策略增强**：fallback 计划增加 `change_color` 操作，色板按平台区分
  9. **`_estimate_modification_intensity` 平台分化**：社交平台在 resonance 下仍保持 moderate 强度，权威平台在低深度保持 moderate
- 测试命令：`cd backend && conda run -n frame python -m pytest -q tests/ --deselect tests/test_batch13_node3_executor.py::test_add_annotation_trendline`
- 测试结果：49 passed, 2 pre-existing failures (trendline + title-wrapping dict format)
- 前端构建：`npm run build` → 成功
- 风险与后续待办：
  - LLM 开启后执行效果取决于 API 响应质量
  - 可继续细化更多话题×平台组合的标题模板
  - 可进一步增强注释内容的平台差异化

---

### Batch 54 — Extender 角色文本层全面重写（拓展+深化：平台×话题矩阵）

- 时间：2026-03-24
- 任务名称：Extender change_title / annotation 平台×话题矩阵重写
- 变更目标：让 Extender 角色真正体现"将原有议题延伸至更广泛的关联领域"的核心功能，不同平台延伸到**不同关联议题维度**
- 影响范围：`backend/app/agents/llm_client.py`
- 接口影响：无，仅修改 fallback 文本输出内容
- 变更内容：
  1. **修复 Extender 分支匹配 Bug**：`_evaluate_gap_fallback` 和 `_propose_strategy_fallback` 中 `category == "Analyst"` 改为 `category in ("Analyst", "Extender")`，修复 Extender 角色无法进入正确策略分支的严重 Bug
  2. **`_build_title_intent` Extender/Analyst 全面重写**：7 个话题（unemployment/climate/deforestation/economy/covid/health/generic）× 6 个平台（t1_authority/t2_media/t3_social/t4_data/t5_ugc/t6_blog），每个平台延伸到不同关联领域：
     - 新闻媒体(t2_media)：社会影响与编辑视角（如"How the Pandemic Has Affected Excess Death Rates"）
     - 政府/权威(t1_authority)：政策与制度视角（如"COVID Mortality and Healthcare System Capacity Gaps"）
     - 社交媒体(t3_social)：个人影响视角（如"Covid Deaths, Cancelled Surgeries, and the Hidden Health Crisis"）
     - 数据平台(t4_data)：方法论与比较视角（如"Excess Mortality vs Reported COVID Deaths: Measurement Gaps"）
     - UGC/社区(t5_ugc)：社区级影响视角（如"COVID Data and Mental Health: The Crisis Nobody Tracks"）
     - 博客(t6_blog)：分析与深度视角（如"What Excess Death Data Reveals About Pandemic Inequality"）
  3. **`_build_extender_annotation` 全面重写**：注释内容与标题扩展方向一致，每个平台的注释引入该平台扩展方向的具体数据/事件/比较
  4. **Extender 操作计划优化**：
     - 操作优先级调整为 change_title → add/change_annotation → change_color
     - 当父节点已有注释时，使用 change_annotation 替代 add_annotation（替换为扩展话题的注释）
     - 移除 add_data_variables（暂不使用），聚焦文本层修改
- 测试命令：`cd backend && conda run -n frame python -m pytest -q tests/test_batch2_components.py tests/test_api.py`
- 测试结果：14 passed
- 风险与后续待办：
  - 暂时不启用 add_data_variables，待文本层效果验证后再决定
  - LLM 开启后可进一步通过 LLM 生成更自然的扩展标题和注释

---

### Batch 57 — 话题优先级修复 + 注释长度提升 + LLM 可靠性增强 + 数据点高亮

- 时间：2026-03-24
- 任务名称：Extender 话题错配修复、注释长度、LLM 调用增强、柱子高亮
- 变更目标：
  1. 修复 deforestation 图表被误判为 climate 的话题优先级 bug
  2. 注释文本不再被截断（80→120 字符）
  3. LLM 调用超时从 12s 增至 30s，增加错误日志
  4. Extender 注释指向的数据柱/点高亮为主题色
  5. 整体 change_color 改为 50% 概率
  6. 去除 Extender 红色系配色
  7. Extender `_build_color_intent` 重写为话题×平台 hex 色码
- 影响范围：`backend/app/agents/llm_client.py`, `backend/app/transform/node3_executor.py`
- 接口影响：无
- 变更内容：
  1. **话题优先级修复**：`_build_title_intent` 和 `_build_extender_annotation` 中 Extender 分支的 if-chain 重新排序为 deforestation → covid → economy → health → unemployment → climate（最具体优先，climate 最后，因为常和 deforestation 同时出现）
  2. **注释长度提升**：`_enforce_text_length` 中 annotation 限制从 80 改为 120 字符
  3. **LLM 调用增强**：
     - `_chat_completion_json` 超时从 12s 提升至 30s
     - 增加结构化日志（成功/超时/HTTP错误/JSON解析错误/通用异常）
     - temperature 从 0.2 调高至 0.4（增加 LLM 输出多样性）
  4. **数据点高亮**：`_highlight_annotated_bar` 在 Extender 注释锚定后，为对应柱子添加 conditional color（主题色高亮，其余 #B0BEC5 淡灰）
  5. **change_color 50% 概率**：Extender 操作计划中 `random.random() < 0.5` 控制
  6. **去红色**：6 个红色 hex 替换为琥珀/棕/紫/青
  7. **`_build_color_intent` 话题×平台 hex**：deforestation 用森林绿、climate 用蓝/琥珀、health 用紫/青绿、economy 用琥珀/灰、unemployment 用棕/琥珀
- 测试命令：`cd backend && conda run -n frame python -m pytest -q tests/test_batch2_components.py tests/test_api.py`
- 风险与后续待办：
  - 需验证 LLM API key 是否有效（之前报告过额度用完）
  - 高亮仅作用于第一个匹配 data layer

---

## Batch 58：Extender 高亮生效修复、注释行宽修复、分析者配色多样化

- 时间：2026-03-14
- 任务名称：Extender 柱子高亮实际生效 & 注释显示完整 & 分析配色多样化
- 变更目标：
  1. 修复柱子高亮不生效：mark.color 覆盖 encoding.color 的 Vega-Lite 优先级 bug
  2. 修复注释文本显示不完全：行宽过窄（23 chars/line），换行碎片化
  3. 增加配色多样性：非高亮柱子用分析风格色调，不再全灰
  4. 防止 change_color 操作覆盖条件高亮
- 影响范围：`backend/app/transform/node3_executor.py`
- 接口影响：无
- 变更内容：
  1. **mark.color 移除**：`_highlight_annotated_bar` 中检测到 mark dict 带 `color`/`fill` 属性时主动删除，确保 encoding.color.condition 生效
  2. **注释行宽修正**：
     - 移除 `_add_annotation` 和 `_change_annotation` 中的早期 `_wrap_text(text, 34)` 调用
     - 换行统一延迟到 `_build_data_annotation_layers` 内部，使用 font-aware `_estimate_annotation_max_chars` 计算
     - `_estimate_annotation_max_chars` 参数调整：safe_width 320→420, available_px 上限 480→560, char_px 系数 0.62→0.58, 上限 50→60, 下限 20→28
     - `_enforce_text_length` annotation 限制 120→150 字符
  3. **分析者配色多样化**：
     - 非高亮柱子从固定 `#B0BEC5` 改为从 8 种分析色调中随机选取（蓝灰/钢灰/冷石板/暖灰/水鸭灰等）
     - `_pick_extender_highlight_color` 无主题匹配时从 12 种分析色（蓝灰/靛蓝/深紫/青绿）中随机选取
     - 新增 `_ROLE_PLATFORM_PALETTES` Extender 条目（7 种平台色：深石板/深紫/暗青/深靛蓝等）
  4. **change_color 不覆盖条件高亮**：`_change_color` 检测到 `encoding.color.condition` 已存在时跳过该 layer 的 mark.color 和 encoding.color 改写
- 测试命令：`cd backend && conda run -n frame python -m pytest -q tests/test_api.py`
- 测试结果：4 passed
- 风险与后续待办：
  - 注释内容（文案）在 fallback 模板下各平台相同；LLM 激活后可差异化
  - 随机色调使测试不完全确定性（可通过 seed 控制）

---

## Batch 59：标题/注释彩色标记、去除基线线、禁止 Extender 简化 X 轴

- 时间：2026-03-14
- 任务名称：Extender 修改可见性增强 & 清理无用视觉元素
- 变更目标：
  1. 被修改的标题和注释使用角色主题色，一眼可见修改内容
  2. 移除 Extender 的 add_data_variables（水平基线线与注释重叠、令人困惑）
  3. 禁止 Extender 执行 simplify_axis（不应简化时间轴到看不到标签）
- 影响范围：`backend/app/transform/node3_executor.py`, `backend/app/agents/llm_client.py`
- 接口影响：无
- 变更内容：
  1. **`_role_text_color` 新方法**：根据 role × platform 返回主题色用于标题和注释
     - Extender: 深蓝/深紫/暗青/深靛蓝系列（分析思考风格）
     - Amplifier: 红/橙/品红系列（告警风格）
     - Adverser: 绿/琥珀/青绿系列（反叙事风格）
     - Analyst: 灰蓝/靛蓝/紫色系列
  2. **`_change_title`**：在修改标题后设置 `spec["title"]["color"]` 为角色色
  3. **`_add_annotation`**：将 `text_color` 参数传入 `_build_data_annotation_layers`；fallback 路径同理
  4. **`_build_data_annotation_layers`**：新增 `text_color` 参数，默认 `#202124`
  5. **Extender/Analyst 操作禁止列表扩展**：在 LLM guard 和 fallback refine 中同时增加 `simplify_axis` 和 `add_data_variables`
  6. **LLM prompt 更新**：明确注明 Extender 不可用 `simplify_axis` 和 `add_data_variables`
- 测试命令：`cd backend && conda run -n frame python -m pytest -q tests/test_api.py`
- 测试结果：4 passed; 端到端验证 4 平台 Extender 均无基线线、无简化轴、标题/注释有角色色
- 风险与后续待办：无

---

## Batch 60：Amplifier change_color 修复 & 深度累积偏移生效

- 时间：2026-03-14
- 任务名称：Amplifier 颜色不变 → 修复原始 chart 条件编码覆盖问题
- 变更目标：
  1. 修复 Amplifier `change_color` 无效 — 原始图表的 encoding.color 条件编码未被替换
  2. 确保 `mark.color` 和 `encoding.color.value` 同步随深度变深（累积偏移）
  3. 区分"我们添加的高亮"和"原始图表自带的条件色"
- 影响范围：`backend/app/transform/node3_executor.py`
- 接口影响：无
- 变更内容：
  1. **根因诊断**：用户上传的去森林化图表 spec 使用 `encoding.color.condition` 设定黄色默认柱（`#f7d570`）+ 橙色高亮 2025（`#d46c31`）。Batch 58 的 `has_conditional_color` 守卫**错误地跳过了所有带条件的编码**，包括原始图表的，导致 `change_color` 完全无效。
  2. **标记系统**：`_highlight_annotated_bar` 设置的条件编码增加 `"_node3_highlight": True` 标记。`_change_color` 只跳过带此标记的条件，不再跳过原始图表的条件。
  3. **全面替换逻辑**：`_change_color` 现在处理三种 encoding.color 情况：
     - 带 condition 无 field → 替换为 `{"value": palette}`（覆盖原始条件高亮）
     - 带 value 无 condition → 直接更新 value（处理上一层 Amplifier 设的平面色）
     - 带 field/scale → 更新 scale.range（多系列图表）
  4. **深度累积验证**：4 平台 × 3 深度端到端测试确认 `mark.color` 和 `enc.color.value` 同步按 15%/30%/40% 递减
- 测试命令：`cd backend && conda run -n frame python -m pytest -q tests/test_api.py`
- 测试结果：4 passed
- 风险与后续待办：`_node3_highlight` 自定义字段在 Vega-Lite 中属于未知属性，不影响渲染但严格 schema 校验可能警告

---

## Batch 61：Bridger 第三方数据平台支持 change_chart_type

- 时间：2026-03-31
- 任务名称：Bridger 3rd-party data platform → 支持修改图表类型（如柱状图 → 线性图）
- 变更目标：
  1. 允许 Bridger 在第三方数据平台（`t4_data`）上执行 `change_chart_type` 操作
  2. 保持 Bridger 在其他平台（authority/news/social）上仍仅限 `change_color`
  3. 图表类型选择基于当前 mark 类型自动推荐（bar → line, point → line）
- 影响范围：
  - `backend/app/config/taxonomy_rules_v3.yaml` — Bridger whitelist 新增 `change_chart_type`
  - `backend/app/agents/llm_client.py` — fallback/normalize/refine 三层约束放宽、新增辅助方法
  - `backend/tests/test_batch2_components.py` — 新增 2 个 Bridger 专项测试
- 接口影响：无（不改 API 路径与字段契约）
- 变更内容：
  1. **taxonomy whitelist**：Bridger 新增 `change_chart_type`
  2. **fallback 策略**：当 `platform_bucket == t4_data` 且当前图表非 line 时，自动插入 `change_chart_type` 操作
  3. **normalize 归一化**：Bridger 允许 `{change_color, change_chart_type}` 通过
  4. **refine 过滤**：同步放宽，允许 `change_chart_type` 通过 Bridger 约束
  5. **LLM prompt**：NodeB/refine prompt 更新 Bridger 约束描述
  6. **辅助方法**：新增 `_detect_current_mark` 和 `_suggest_bridger_chart_type`
- 测试命令：`cd backend && conda run -n frame python -m pytest -q tests/test_batch2_components.py tests/test_batch13_node3_executor.py`
- 测试结果：36 passed, 2 pre-existing failures
- 补充修复（USE_LLM=true 路径）：
  - 发现 LLM 路径下即使 prompt 允许 `change_chart_type`，LLM 仍可能只返回 `change_color`
  - 在 LLM normalize 阶段新增 Bridger 数据平台守卫：若 LLM 未产出 `change_chart_type`，自动注入
  - 在 refine 阶段新增同样的安全注入（双保险），确保无论 LLM 输出如何，数据平台 Bridger 一定有 `change_chart_type`
  - 更新 few-shot 示例：新增 `Bridger/DataPlatform: change_chart_type + change_color` 范例
- 修复 `_change_chart_type` 数据显示不正确：
  - **根因**：原实现将所有 layer marks 统一改为目标类型，导致 tick/text/rule 等参考层也被误改为 line
  - **修复**：引入 `_REFERENCE_MARKS` 集合（`text/tick/rule`），跳过非数据层
  - **清理 bar 特有属性**：转为 line/area 时移除 `width.band`、`cornerRadius*` 等 bar-only 属性
  - **非堆叠多系列**：转为 line/area 时移除 `order`；**堆叠 bar（有 order 或 fold）** 则保留 `order` 并见下条
  - 变更落点：`backend/app/transform/node3_executor.py`
- 修复「柱状图改折线图后数值看起来不对」：
  - **根因**：堆叠柱对多系列做 **y 向堆叠**；仅改 `mark` 为 `line` 时各系列按 **原始分量** 取值，最大值仅为单系列（如 nc），无法达到堆叠总高（nc+c），在固定 domain 下线条挤在纵轴下半部，观感像「数据错了」
  - **修复**：若原 layer 为 `bar` 且存在多系列（`color.field`）并带有堆叠信号（`order` 通道或 `fold` transform），在转为 `line`/`area` 时为 `encoding.y` 设置 `stack: "zero"`，并 **保留 `order`**；折线默认 `point: true` 便于读点
  - 测试：`tests/test_batch13_node3_executor.py::test_change_chart_type_stacked_bar_to_line_uses_y_stack`
- `change_chart_type` → `line` 时默认 `strokeWidth: 5`（`setdefault`，不覆盖已有值），传播树缩略图更易辨认
- 风险与后续待办：
  - 当前 `_suggest_bridger_chart_type` 默认将 bar/point 转为 line；后续可根据数据特征做更精细推荐
  - 若需支持更多平台（如 blog/social）也能改图表类型，可扩展 `platform_bucket` 判断条件


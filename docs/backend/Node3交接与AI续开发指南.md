# Node3 交接与 AI 续开发指南

> 文档目标：把 Node3 后续开发交接给学姐与下一个 AI，确保不丢上下文、可直接接力开发。  
> 适用范围：后端 `Node3`（执行器）、Taxonomy 口径冻结、前后端联调前的后端主线开发。

---

## 1. 当前基线（交接时状态）

- 后端主链路已跑通：`/api/upload-case -> /api/simulation/start -> tree/agentLog/summary/pathOffsetTrend`
- Node1/Node2 已完成 taxonomy v3 最小接入：
  - NodeA：`alignment_with_preference`、`identified_gaps`、`expected_modification_intensity`
  - NodeB：`selected_operations`、`operation_rationale`
- 研究交互输入已接入：
  - `maxDepth`、`agentProfiles(role/institution)`、`mode`
- 角色命名口径：
  - 对外统一用 `Extender`
  - 后端内部仍映射到 `Analyst`（兼容现有 `agentCategories` 枚举）
  - 历史拼写 `extensioner` 仅作为兼容输入保留
- 当前测试基线：`17 passed`

---

## 2. Node3 未完成项（必须做）

Node3 目前仍是占位执行（仅输出 `variantDescription/layers`），后续要完成三件套：

1. 参数协议（Operation Schema）
2. 执行器（真实改 `chart_spec`）
3. 校验与回滚（失败可降级）

---

## 3. 需要 Taxonomy 负责人拍板的口径（阻塞项）

以下口径确认后，Node3 才能进入“稳定版本”：

1. `op -> Vega-Lite` 字段路径映射（JSONPath 级）
2. 每个 op 参数约束（类型、范围、默认值）
3. 多 op 顺序与互斥规则（冲突解决策略）
4. 执行后校验规则（结构合法 + 语义一致）
5. 回滚策略（`skip_op` / `node_rollback` / `fallback_text`）

建议交付格式（给 Taxonomy 负责人）：

- `docs/taxonomy/node3_operation_schema_v1.md`（人读版）
- `backend/app/config/node3_operation_schema_v1.yaml`（机器读版）

---

## 4. Node3 开发任务拆解（给下一个 AI）

### M1：参数协议落地（先定义）

- 新增 `operation schema` 配置文件（yaml）
- 为每个 op 固化：
  - `layer`
  - `target_paths`
  - `params`
  - `constraints`
  - `mutually_exclusive_with`
- 升级 RuleGuard：从“白名单过滤”升级到“参数级校验”

### M2：执行器落地（再执行）

- 新增执行模块：`backend/app/transform/node3_executor.py`
- 输入：`chartSpec + selected_operations`
- 输出：
  - `updated_chart_spec`
  - `executed_operations`（含 before/after）
  - `layers_affected`

### M3：校验与回滚（最后加可靠性）

- 新增校验模块：`backend/app/transform/spec_validator.py`
- 校验失败分级处理：
  - 单 op 失败 -> skip
  - 节点失败 -> 回滚 parent spec
  - 全失败 -> fallback text-only
- 所有失败写入 `provenance_chain`

---

## 5. 建议文件改动清单（执行顺序）

1. `backend/app/config/`  
   - 新增 `node3_operation_schema_v1.yaml`
2. `backend/app/agents/rule_guard.py`  
   - 加参数级校验
3. `backend/app/transform/`  
   - 新增 `node3_executor.py`、`spec_validator.py`
4. `backend/app/graph/workflow.py`  
   - Node3 从占位逻辑切换到真实执行
5. `backend/app/services/simulation_service.py`  
   - 接入执行结果、写入 `executed_operations`
6. `backend/tests/`  
   - 新增 Node3 执行与回滚测试
7. `docs/backend/后端工程技术方案.md` + `docs/backend/CHANGELOG.md`  
   - 同步留痕

---

## 6. Cursor + AI 续开发操作方法

### 6.1 开工前必读顺序（避免上下文偏差）

1. `docs/研究问题.md`
2. `docs/后端方案.md`
3. `docs/api/接口文档.md`
4. `docs/backend/后端工程技术方案.md`
5. `docs/backend/CHANGELOG.md`
6. 本文档（交接说明）

### 6.2 开发时固定流程（每批）

1. 先改代码（小步）
2. 运行测试：`conda run -n frame python -m pytest -q`
3. 更新 `docs/backend/后端工程技术方案.md` 批次记录
4. 追加 `docs/backend/CHANGELOG.md`

### 6.3 给下一个 AI 的推荐指令模板

可直接粘贴给 AI：

```text
按 docs/backend/后端工程技术方案.md 的当前 P1（Node3 三件套）继续开发。
必须遵循 docs/api/接口文档.md 契约；先实现 M1 参数协议，再实现 M2 执行器，再实现 M3 校验回滚。
每完成一批都要跑 conda run -n frame python -m pytest -q，
并更新 docs/backend/后端工程技术方案.md 与 docs/backend/CHANGELOG.md。
```

---

## 7. 交付验收标准（DoD）

Node3 交付完成的最低标准：

- [ ] 至少 5 个核心 op 能真实改写 `chart_spec`
- [ ] 失败不会中断整条 run（有回滚）
- [ ] `provenance_chain` 能回放执行证据
- [ ] 全量测试通过并新增 Node3 专项测试
- [ ] 工程方案与 changelog 有完整留痕

---

## 8. 风险提醒

- 若 Taxonomy 口径未冻结，优先做 M1，不要直接硬写 M2/M3。
- 若前后端枚举有分歧，优先保证后端向后兼容，文档先统一为 `Extender`。
- 若单批改动过大导致测试不稳，按 M1/M2/M3 分批提交，不要一次性合并。

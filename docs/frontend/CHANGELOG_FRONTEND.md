# Frontend Changelog

> 目的：作为前端开发的追加式留痕日志（append-only），便于后端工程师联调时了解前端逻辑与接口约定。  
> 规则：每次涉及前端逻辑、接口入参/出参使用方式、UI 行为变更后，可在此新增一条记录，不覆盖历史记录。

---

## 记录模板（复制后填写）

```markdown
## [YYYY-MM-DD HH:mm] Batch-X / Task-Name

- 变更目标：
- 变更原因：
- 影响范围（文件/模块）：
  - `src/...`
  - `docs/...`（如有）
- 接口影响：无 / 有（说明请求/响应字段或行为）
- 数据结构影响：无 / 有（说明）
- 关键实现点：
  - ...
- 风险与回滚点：
  - ...
- 后续待办：
  - ...
```

---

## 日志记录

## [2026-03-01] 左侧设置面板：Agent 池按数量生成、仅 role+institution、下拉选项与点亮

- 变更目标：左侧「设置模拟」支持用户选择最大深度与 Agent 数量；Agent Profile 池按数量生成灰色待编辑卡片；每个 Agent 仅配置 **角色(role)** 与 **平台(institution)**，去掉 motivation；选项来自 codebook；配置完成后卡片按角色颜色点亮。
- 变更原因：产品要求与 codebook 对齐，后端仅需 role+institution，前端展示与第四幅参考图一致（未设置：灰底、null/Platform: null、铅笔编辑；已设置：角色色、完成按钮）。
- 影响范围（文件/模块）：
  - `src/constants/codebook.ts`（新增：ROLES、INSTITUTIONS、AgentProfileEntry、FrameLayer 等）
  - `src/constants/agentProfile.ts`（ROLE_COLORS，引用 codebook 的 RoleKey）
  - `src/context/simulation.tsx`（agentProfiles、setAgentProfiles、maxDepth 等状态）
  - `src/features/setup/SetupPanel.tsx`（滑块 maxDepth/agentCount、池子数量同步、下拉选择 role/institution、点亮逻辑、提交时组装 agentProfiles）
  - `docs/codebook.md`（选项来源，未改）
- 接口影响：有。`POST /api/simulation/start` 请求体新增 **agentProfiles**（`Array<{ role: string, institution: string }>`）、**maxDepth**（number）；前端不再传 motivation。
- 数据结构影响：有。前端全局状态新增 `agentProfiles: AgentProfileEntry[]`、沿用/显式使用 `maxDepth`；Agent 类别仍通过 agentCategories 提交（由 agentProfiles 推导）。
- 关键实现点：
  - agentCount 变化时 useEffect 将 agentProfiles 长度同步为 agentCount，不足补 `{ role: null, institution: null }`，超出截断。
  - 编辑态：当前卡片显示两个 Select（role、institution）+「完成」按钮；未编辑卡片显示铅笔，点击进入编辑。
  - 提交时 `agentProfiles.slice(0, effectiveCount)` 转为 `{ role, institution }`，缺省 role 用 "Bridger"，institution 用 ""；agentCategories 由 getCategoriesForSubmit() 从 agentProfiles 推导（Bridger→Bridger, Extender→Analyst, Adverser→Adverser, Amplifier→Amplifier）。
- 风险与回滚点：若后端尚未支持 agentProfiles/maxDepth，可暂时不读该字段；前端已做缺省，旧后端仍可仅用 agentCount/agentCategories。
- 后续待办：与后端确认 agentProfiles 与 maxDepth 的最终字段名与枚举值（与 codebook 一致）。

## [2026-03-01] 中间面板：传播树边线按 DATA/TEXT/VISUAL 区分线型

- 变更目标：传播模拟图中，节点间连线的线型根据「目标节点」的 operations 所属框架层级区分：DATA→长虚线、TEXT→实线、VISUAL→短虚线。
- 变更原因：与 panel2 设计一致，便于从图中区分不同层面的传播操作。
- 影响范围（文件/模块）：
  - `src/features/propagation/PropagationPanel.tsx`（getLayersFromOperations、EDGE_STYLE_BY_LAYER、buildFlowNodesAndEdges 中 flowEdges 按层生成多条 edge）
  - `src/constants/codebook.ts`（FrameLayer 类型引用）
- 接口影响：无（仅使用 tree 中节点已有字段 `operations`）。
- 数据结构影响：无。仍使用后端返回的 `tree.nodes[].operations`（字符串数组），前端根据前缀 "DATA"/"TEXT"/"VISUAL" 推断层级。
- 关键实现点：
  - 从 target 节点的 operations 解析出 DATA/TEXT/VISUAL 列表；每条边若多层级则生成多条 React Flow edge（同 source/target，不同 id、style），线型：DATA strokeDasharray "12 6"，TEXT 无 dash，VISUAL "4 3"。
  - 修复节点样式 typo：paddingTop 由 `PANEL2.iconSize -13` 改为 `PANEL2.iconSize + 6`。
- 风险与回滚点：多层级时多条边会重叠在同一路径上，视觉上可能只看到一种线型；若需并排多线可后续改为自定义 Edge 组件绘制多条 path。
- 后续待办：可选——自定义 Edge 支持同一条逻辑边多线型并排展示。

## [2026-03-01] 右侧偏移分析：预览 / 过程（按 Agent + 三层面）/ 偏移趋势；去除 motivation

- 变更目标：右侧「偏移分析」固定为三块：预览（当前变体图）、过程（从根到当前节点的智能体修改过程，按 Agent 分组，操作按 DATA/VISUAL/TEXT 三层面展示）、偏移趋势；不再展示「变体描述」独立区块；节点信息仅展示 role、institution，不展示 motivation。
- 变更原因：与 panel3 设计一致，过程流按「Agent → 具体操作（按三层面）」展示；与左侧去掉 motivation 一致。
- 影响范围（文件/模块）：
  - `src/features/offset/OffsetPanel.tsx`（已有预览/过程/偏移趋势结构；过程按 agent 与 DATA/VISUAL/TEXT 分组展示；去掉变体描述、motivation 展示）
- 接口影响：无（仍使用 tree 中节点字段；若后端仍返回 motivation，前端不展示）。
- 数据结构影响：无。
- 关键实现点：过程流按路径上节点顺序，每个 Agent 下按 operations 归类到 DATA、TEXT、VISUAL 三块展示；预览区展示选中节点的 imageUrl。
- 风险与回滚点：无。
- 后续待办：无。

## [2026-03-01] 接口文档与前端 Changelog 更新

- 变更目标：在接口文档中明确「开始模拟」请求体包含 agentProfiles、maxDepth；明确前端不再传 motivation、右侧不展示 motivation；明确中间面板边线型与右侧过程流按 DATA/VISUAL/TEXT 的约定；新增前端 Changelog 文件供后端查阅。
- 变更原因：后端联调需要单源真相与变更历史。
- 影响范围（文件/模块）：
  - `docs/接口文档.md`（2 用户流程、2.2 请求参数、请求样例、传播树节点说明、界面描述）
  - `docs/CHANGELOG_FRONTEND.md`（新建）
- 接口影响：文档层面；约定 `agentProfiles`、`maxDepth` 的语义与示例。
- 数据结构影响：无。
- 关键实现点：请求参数表增加 agentProfiles、maxDepth；样例 body 增加上述字段；节点说明中注明前端仅用 role/institution、边线型与 operations 的对应关系、右侧三块结构。
- 风险与回滚点：无。
- 后续待办：后端若字段名或枚举与文档不一致，需同步更新接口文档与前端入参。

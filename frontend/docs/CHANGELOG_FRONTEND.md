# Frontend Changelog

> 目的：作为前端开发的追加式留痕日志（append-only），便于后端工程师联调时了解前端逻辑与接口约定。  
> 规则：每次涉及前端逻辑、接口入参/出参使用方式、变更后，可在此新增一条记录，不覆盖历史记录。

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
  - 提交时 `agentProfiles.slice(0, effectiveCount)` 转为 `{ role, institution }`，缺省 role 用 "Bridger"，institution 用 ""；agentCategories 由 getCategoriesForSubmit() 从 agentProfiles 推导（Bridger→Bridger, Extender→Amplifier, Adverser→Adverser, Amplifier→Amplifier）。
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

---

## [2026-03-01] 前端整体逻辑与接口文档对齐（左/中/右 + 后端联调摘要）

- 变更目标：统一前端整体逻辑描述，便于后端工程师联调时对照；左侧流程、中间边线型、右侧三块、提交 payload 与接口文档一致；Agent 参数编辑 UI 与参考图（第四幅）一致；补充接口文档中 role/institution 与 codebook 的对应关系。
- 变更原因：产品要求左侧「上传 → 自身理解 → 环境参数 → Agent 池」流程清晰，右侧仅保留预览/过程/偏移趋势三块，中间传播图边线按 DATA/TEXT/VISUAL 区分，且与 `docs/codebook.md`、`docs/接口文档.md` 一致。
- 影响范围（文件/模块）：
  - `src/features/setup/SetupPanel.tsx`（增加「对图表的理解」标题与占位说明）
  - `docs/接口文档.md`（agentProfiles 与 agentCategories 说明补充 codebook 取值与前端推导方式）
  - `docs/CHANGELOG_FRONTEND.md`（本条目）
- 接口影响：无（仅文档与 UI 文案）；请求体约定已符合现有实现。
- 数据结构影响：无。
- 关键实现点（前端整体逻辑摘要，供后端联调参考）：
  - **左侧（设置模拟）**：① 用户上传完整案例（chart_spec + metadata，可选 data/image）→ 获得 caseRef，预览区展示；② 用户填写「对图表的理解」（description）；③ 选择环境参数：最大深度、Agent 数量；④ Agent Profile 池按 agentCount 生成 N 个灰色待编辑卡片；⑤ 用户逐一点击编辑：**角色(role)**、**平台(institution)** 均从 `docs/codebook.md` 下拉选择（role：Bridger/Extender/Adverser/Amplifier；institution：政府/官方机构、社交媒体等），无 motivation；⑥ 配置完成后卡片按角色颜色点亮；⑦ 点击「开始模拟」提交：**caseRef**、**description**、**maxDepth**、**agentCount**、**agentProfiles**（每项 `{ role, institution }`），agentCategories 由前端从 agentProfiles 的 role 推导。
  - **中间（传播模拟）**：展示传播树；节点间连线根据**目标节点**的 operations 推断层级：**DATA** → 长虚线（strokeDasharray 大间隔）、**TEXT** → 实线、**VISUAL** → 短虚线；若一条边对应多层级则绘制多条线型（同 source/target，不同 style）。
  - **右侧（偏移分析）**：仅三块——**预览**（当前变体图）、**过程**（从根到当前节点的 Agent 修改过程，按 Agent 分组，操作按 DATA/VISUAL/TEXT 三层面展示）、**偏移趋势**（X：上一节点→当前节点，Y：偏移等级；未选节点时只显示坐标轴无红线）。不展示「变体描述」独立区块；节点信息仅展示 role、institution。
  - **Agent 参数编辑 UI**：未设置时灰底、null / Platform: null、铅笔图标；编辑时角色与机构均为下拉选择（codebook），完成后按钮「完成」，卡片点亮为对应角色颜色。
- 风险与回滚点：后端若未支持 Extender，前端已将其映射为 Amplifier 提交 agentCategories；agentProfiles 中 role 仍可传 "Extender" 供后端扩展。
- 后续待办：与后端确认 role 枚举是否统一为 codebook 四种（Bridger/Extender/Adverser/Amplifier）及 institution 取值是否与 codebook 二完全一致。

---

## [2026-03-04] 上传流程与前端独立运行（upload-case、文件夹选择、metadata 自动填充、Mock 模式）

- 变更目标：左侧上传改为「选择文件夹」方式，必含 chart_spec.json、metadata.json，可选 data.csv、预览图；上传成功后从 metadata 自动填充「对图表的理解」；支持仅跑前端不连后端（VITE_USE_MOCK 或上传/启动失败时使用 local-demo 与本地 mock 数据）。
- 变更原因：与接口文档「上传完整案例」一致；避免未起后端时代理 ECONNREFUSED；提升体验（metadata 描述自动带入）。
- 影响范围（文件/模块）：
  - `src/lib/api.ts`（uploadCase：FormData POST /upload-case，chart_spec/metadata 必填，data/image 可选；StartSimulationResult 类型）
  - `src/features/setup/SetupPanel.tsx`（文件夹选择 input、processUploadedFiles 调用 uploadCase、解析 metadata 填入 description、VITE_USE_MOCK 跳过上传、caseRef 为 null 或 local-demo 时 runSimulation 不调 startSimulation 而用 applyMockTree）
- 接口影响：有。**请求**：上传使用 `POST /api/upload-case`，FormData 字段 `chart_spec`、`metadata`（必填），`data`、`image`（可选）；**响应**：caseRef（或 chartSpecRef）供 start 使用。前端在无 caseRef 或 caseRef=local-demo 时不请求 startSimulation。
- 数据结构影响：有。全局状态 caseRef 可为 `"local-demo"` 表示仅前端演示；description 在上传成功后可能被 metadata 中的 meta.description 或 description 覆盖。
- 关键实现点：
  - 文件夹选择：`<input type="file" multiple />` 配合 `webkitdirectory`，从选中文件中按文件名取 chart_spec.json、metadata.json、data.csv 及首张图片。
  - 上传成功后 `metadata.text()` + JSON 解析，取 `meta.description ?? description` 调用 setDescription。
  - `VITE_USE_MOCK === "true"` 时直接 setCaseRef("local-demo") 并提示；uploadCase 失败时同样 setCaseRef("local-demo")；runSimulation 中若 !caseRef || caseRef === "local-demo" 则只执行本地 mock 树与 agentLog，不调用 startSimulation；超时或 start 失败时也回退到 mock。
- 风险与回滚点：后端若未提供 /upload-case 或字段名不同，上传会失败并退到 local-demo；若需强制连后端，不要设置 VITE_USE_MOCK。
- 后续待办：无。

---

## [2026-03-04] 角色命名统一：Extensioner → Extender

- 变更目标：项目中所有「Extensioner」统一改为「Extender」（含拼写修正 extensior→extender），与 codebook 及接口文档中 role 枚举一致。
- 变更原因：命名统一，避免与「Extension」混淆，便于前后端对齐。
- 影响范围（文件/模块）：
  - `src/constants/codebook.ts`（ROLES 中 value/label：Extensioner → Extender）
  - `src/constants/agentProfile.ts`（ROLE_COLORS 键 Extensioner → Extender；注释）
  - `src/features/setup/SetupPanel.tsx`（getCategoriesForSubmit 中 roleToCategory 键 Extensioner → Extender）
  - `src/features/offset/OffsetPanel.tsx`（NODE_TYPE_COLOR、NODE_TYPE_TO_ROLE_LABEL 键 extensior→extender，值 Extensioner→Extender；getProcessRoleLabel 中 role 判断）
  - `src/features/propagation/PropagationPanel.tsx`（NODE_TYPE_COLOR 键 extensior→extender）
  - `docs/接口文档.md`、`docs/codebook.md`、`docs/前端项目解析.md`、`docs/CHANGELOG_FRONTEND.md`（文案与示例）
- 接口影响：有。**请求**：agentProfiles[].role 现提交 `"Extender"`（不再提交 `"Extensioner"`）；agentCategories 推导逻辑不变（Extender→Amplifier）。**响应**：若后端返回 tree.nodes[].role 或 nodeType 含 Extender/extender，前端展示与配色已支持。
- 数据结构影响：有。codebook 的 role 选项值、全局 agentProfiles[].role、过程流与传播图 nodeType 映射键均为 Extender/extender；文档中 role 枚举统一为 Bridger/Extender/Adverser/Amplifier。
- 关键实现点：
  - ROLES 下拉选项 value 与 label 均为 "Extender"（延伸者）；ROLE_COLORS 与 NODE_TYPE_* 映射键统一为 "Extender" 或 "extender"（小写键用于 nodeType 查找）。
  - 后端若仍返回 nodeType "extensior" 等旧值，前端仅识别 "extender"；必要时可在映射表内保留 extensior→同一颜色/标签以兼容。
- 风险与回滚点：后端若仍期望 "Extensioner"，需后端同步改为 "Extender" 或前端临时做一层映射。
- 后续待办：与后端确认 role 枚举已统一为 Extender。

---

## [2026-03-07] 角色与 codebook 一致：agentCategories 为四角色，去掉 Extender→Amplifier 映射与 Analyst

- 变更目标：与 `docs/codebook.md` 一致，角色仅四种（Bridger、Extender、Adverser、Amplifier）；接口文档与前端均以这四种为准，不再将 Extender 映射为 Amplifier，不再使用 Analyst。
- 变更原因：codebook 一 明确定义四类角色，接口与后端约定应与之一致，无需「兼容后端枚举」的映射。
- 影响范围（文件/模块）：
  - `docs/接口文档.md`（agentCategories 取值改为 `"Bridger" | "Extender" | "Adverser" | "Amplifier"`，删除「Extender 可能映射为 Amplifier」及 Analyst；节点类型图例表述改为与 codebook 四角色对应）
  - `src/types/contracts.ts`（AgentCategory 类型改为上述四种，去掉 Analyst）
  - `src/features/setup/SetupPanel.tsx`（getCategoriesForSubmit 中 Extender→Extender，不再映射为 Amplifier）
  - `src/context/simulation.tsx`（初始 agentCategories 数组去掉 "Analyst"，改为合法四角色）
  - `docs/接口与交互流程对照检查.md`（agentCategories 说明更新为四角色直接对应）
- 接口影响：有。**请求**：`POST /api/simulation/start` 的 **agentCategories** 现仅含四种枚举 `"Bridger" | "Extender" | "Adverser" | "Amplifier"`，与 agentProfiles[].role 一一对应，不再出现 "Analyst"，不再将 Extender 转为 Amplifier。
- 数据结构影响：有。AgentCategory 类型与全局 agentCategories 初始值仅含四角色；提交时 getCategoriesForSubmit() 直接 role→agentCategory（Bridger→Bridger, Extender→Extender, Adverser→Adverser, Amplifier→Amplifier）。
- 关键实现点：
  - 接口文档 2.2 请求参数表：agentCategories 说明改为「与 codebook 一一致，共四种」；取值列改为 Bridger | Extender | Adverser | Amplifier。
  - 接口文档中节点类型图例、2.5 表格等处：图例与 codebook 四角色对应，不再写 Analyst。
  - 前端类型 AgentCategory 与 getCategoriesForSubmit 均按四角色直传；context 初始 state 中 "Analyst" 替换为合法枚举。
- 风险与回滚点：若后端仍只接受 Amplifier/Analyst/Bridger/Adverser 且不接受 Extender，需后端扩展枚举或前后端再约定映射；当前以 codebook 为唯一来源。
- 后续待办：与后端确认 agentCategories 枚举已与 codebook 四角色一致（接受 Extender，无需前端映射）。

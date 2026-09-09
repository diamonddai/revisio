# 传播模拟与偏移分析 — 前端架构说明

> 面向学习：必备架构 + 各文件作用 + 与 UI/流程的对应关系。

---

## 一、配置一个前端项目必须的架构（最小骨架）

| 层级 | 作用 | 本项目对应 |
|------|------|------------|
| **1. 入口与 HTML** | 浏览器加载的页面 + React 挂载点 | `index.html`、`src/main.tsx` |
| **2. 根组件与布局** | 应用唯一根组件 + 整体布局 | `src/App.tsx`、`src/app/AppLayout.tsx` |
| **3. 构建与开发** | 打包、热更新、代理、TypeScript | `vite.config.ts`、`package.json`、`tsconfig*.json` |
| **4. 类型与规范** | 接口类型、ESLint | `src/types/contracts.ts`、`eslint.config.js` |
| **5. 样式** | 全局样式、组件库 | `src/index.css`、Ant Design |
| **6. 业务模块** | 按功能划分的面板 | `src/features/setup`、`propagation`、`offset` |
| **7. 通用组件** | 可复用 UI 块 | `src/components/PanelCard.tsx` |
| **8. 全局状态** | 跨面板共享数据 | `src/context/simulation.tsx` |
| **9. 基础设施** | API、工具 | `src/lib/api.ts` |

**依赖方向**：`main.tsx` → `App.tsx` → `AppLayout` → 三个 feature 面板 → 使用 `components`、`context`、`lib`、`types`。

---

## 二、与你的 UI / 用户流程的对应关系

### 用户操作步骤 → 实现位置

| 步骤 | 说明 | 实现位置 |
|------|------|----------|
| 输入原始可视化/图片编码 | 上传或粘贴 | 左侧 `SetupPanel`：`Upload.Dragger` |
| 系统预览用户输入的图片 | 预览区 | 左侧「预览」区块，`preview.dataUrl` → `<img>` |
| 基于 LLM 解读生成描述和主题 | 描述 + 主题(international affairs, science, politics, economy, other) | 左侧「描述」「主题」；可调 `lib/api.ts` 的 `interpretImage` |
| 用户选择目标平台 | longform / shortform / video / community | 左侧「目标平台」多选 `Checkbox` |
| 最终点击开始模拟 | 开始模拟按钮 | 左侧「开始模拟」→ `runSimulation()` |

### 中间面板（传播模拟）

| 需求 | 实现位置 |
|------|----------|
| 每个节点代表一个智能体 | `PropagationPanel`：React Flow 节点，数据来自 `tree.nodes`（`AgentNode`） |
| 每个智能体有画像 | 节点类型（中立/源、权威型、情绪放大者、焦虑型、动员型）→ 图例 + 节点颜色 |
| 基于画像的倾向操作（转发、修改、增删等） | 后端/逻辑在 log 中体现；`agentLog` 展示每条操作 |
| Agent log 实时更新、模拟开始与结束 | `context` 的 `agentLog`、`appendLog`；`SetupPanel` 中 `runSimulation` 里追加 log |

### 右侧面板（偏移分析）

| 场景 | 需求 | 实现位置 |
|------|------|----------|
| **未点击节点** | 整个传播链完成后，原始 vs 最终二创图像、变体描述、明显变化（图层、语义等） | `OffsetPanel`：`selectedNode === null` 时显示 `originalImageUrl`、`variantImageUrl`、`overallVariantDescription`、整体路径偏移趋势 |
| **点击某节点** | 该节点下图像变化、智能体角色类型、具体操作、与上一节点相比的路径偏移趋势 | `OffsetPanel`：`selectedNode !== null` 时显示该节点的 `variantDescription`、`role`/`motivation`/`operations`、`pathOffsetTrend`（到该节点） |

---

## 三、项目根目录文件说明

| 文件 | 作用 |
|------|------|
| **package.json** | 项目名、依赖（react, antd, @xyflow/react, recharts, axios）、脚本（dev/build/lint/preview）。 |
| **index.html** | SPA 模板，`<div id="root">` + 入口脚本 `/src/main.tsx`。 |
| **vite.config.ts** | Vite 配置：React 插件、开发代理（`/api` → 后端），便于联调。 |
| **tsconfig.json** | TypeScript 根配置，引用 app 与 node 的 tsconfig。 |
| **tsconfig.app.json** | 应用源码（src）的 TS 配置。 |
| **tsconfig.node.json** | 仅针对 Vite 等配置文件。 |
| **eslint.config.js** | ESLint 规则。 |
| **README.md** | 项目说明、快速开始、后端接口约定。 |

---

## 四、src/ 下各文件作用

### 4.1 入口与根组件

| 文件 | 作用 |
|------|------|
| **src/main.tsx** | 引入 `antd/dist/reset.css`、`index.css`，用 `createRoot` 将 `<App />` 挂载到 `#root`。 |
| **src/App.tsx** | 根组件，只渲染 `<AppLayout />`。 |
| **src/index.css** | 全局样式：字体、背景色、#root 等。 |

### 4.2 应用骨架（app/）

| 文件 | 作用 |
|------|------|
| **src/app/AppLayout.tsx** | 三栏布局：顶部三条灰色标题（设置模拟 / 传播模拟 / 偏移分析），下方三列分别挂载 `SetupPanel`、`PropagationPanel`、`OffsetPanel`；最外层包 `SimulationProvider`。 |

### 4.3 通用组件（components/）

| 文件 | 作用 |
|------|------|
| **src/components/PanelCard.tsx** | 基于 Ant Design Card 的通用卡片，支持 title、extra、style、bodyStyle，保证三栏内样式统一。 |

### 4.4 业务模块（features/）

| 文件 | 作用 |
|------|------|
| **src/features/setup/SetupPanel.tsx** | **左侧 - 设置模拟**：上传原始可视化、预览、描述/主题（可接 LLM）、Agent 数量滑块、目标平台多选、开始模拟按钮；点击开始后写入 mock 传播树与 log、更新状态与右侧数据。 |
| **src/features/propagation/PropagationPanel.tsx** | **中间 - 传播模拟**：节点类型图例、传播树总览（节点数/边数/最大深度/最高偏移路径/拓扑类型）、React Flow 传播树图、节点可点击选中、AGENT LOG 列表。 |
| **src/features/offset/OffsetPanel.tsx** | **右侧 - 偏移分析**：未选节点时展示原始图、最终变体图、变体描述、整体路径偏移趋势图；选中节点时展示该节点角色/动机/平台、执行的操作、涉及层数、变体描述、路径偏移趋势。 |

### 4.5 全局状态（context/）

| 文件 | 作用 |
|------|------|
| **src/context/simulation.tsx** | `SimulationProvider`：统一管理预览、描述/主题、agent 数量、平台、模拟状态与摘要、传播树、agent log、选中的节点、整体/节点变体描述与路径偏移、原始/变体图片 URL；提供 `useSimulation()`。 |

### 4.6 基础设施与类型

| 文件 | 作用 |
|------|------|
| **src/lib/api.ts** | axios 实例、`uploadVisualization`、`interpretImage`、`startSimulation`、`ping`；所有请求经此发出，便于改 baseURL、加拦截器。 |
| **src/types/contracts.ts** | 类型定义：TopicType、PlatformKey、NodeTypeKey、OffsetLevel、AgentLogEntry、AgentNode、AgentEdge、PropagationTree、PathOffsetPoint、UploadPreview、SimulationStatus、SimulationResultSummary 等。 |

---

## 五、数据流简图

```
用户上传 → preview + originalImageUrl
     ↓
（可选）LLM 解读 → description, topic
     ↓
选择平台、Agent 数量 → 点击「开始模拟」
     ↓
runSimulation() → setTree, appendLog, setSummary, setPathOffsetTrend, setOverallVariantDescription, setVariantImageUrl, setStatus('done')
     ↓
中间：传播图展示 tree；点击节点 → setSelectedNode
     ↓
右侧：selectedNode === null → 整体偏移分析；selectedNode !== null → 该节点偏移分析
```

---

## 六、后续可扩展

- 将 mock 传播树与 log 改为后端接口（如 `POST /api/simulation/start` + WebSocket 或轮询）。
- 上传/解读改为真实 `uploadVisualization`、`interpretImage`。
- 按节点存储并展示每个节点的变体图像（当前可为占位或与最终变体复用）。

文档版本：1.0

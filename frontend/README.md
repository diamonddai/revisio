# 传播模拟与偏移分析 前端



## 功能概览

- **左侧 - 设置模拟**：上传原始可视化/图片 → 预览 → 用户手动填写「对图表的理解」、选择主题 → 设置 Agent 数量（0–6）、勾选 Agent 类别（Amplifier / Analyst / Bridger / Adverser）→ 开始模拟。
- **中间 - 传播模拟**：传播树图（每节点框内为该节点变体图，根节点为上传图）、左上角节点类型图例、AGENT LOG 实时更新；画布支持滚轮缩放与拖拽平移
- **右侧 - 偏移分析**：未选节点时展示整体「原始 vs 最终变体」、变体描述与路径偏移趋势图；点击中间某节点时展示该节点变体图放大、角色、动机、偏移程度、Agent 执行的操作、变体描述及到该节点的路径偏移趋势。

## 技术栈

- React 19 + TypeScript
- Vite 7
- Ant Design 5
- @xyflow/react（传播树图）
- Recharts（路径偏移趋势图）
- Axios（API 封装）

## 项目结构

```
src/
├── app/           # 应用布局
├── components/    # 通用组件
├── context/       # 全局状态（SimulationProvider）
├── features/      # 业务模块
│   ├── setup/         # 设置模拟
│   ├── propagation/   # 传播模拟
│   └── offset/       # 偏移分析
├── lib/           # API
└── types/         # 类型定义
```

## 快速开始

```bash
cd simulation
npm install
npm run dev
```

**仅跑前端、不连后端**：在项目根目录创建 `.env.local`，设置：

```
VITE_USE_MOCK=true
```

然后 `npm run dev`。上传案例时会跳过后端请求，直接进入本地演示模式，点击「开始模拟」使用演示数据，不会出现代理 ECONNREFUSED。

后端联调时，配置 `.env` 或 `.env.local`：

```
VITE_API_BASE=/api
```

并确保 Vite 代理将 `/api` 转发到后端（见 `vite.config.ts`）。不要设置 `VITE_USE_MOCK` 或设为 `false`。




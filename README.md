# 实验室项目（Frame）

一个用于模拟 `Online Discourse` 中可视化叙事偏移（Framing Shift）的前后端项目。

## 当前状态

- 后端 V1 已完成可联调版本（接口、多智能体流程、LangGraph 条件路由、快照落盘、测试）。
- 前端仍在持续对接中。

## 技术栈

- **后端**：Python + FastAPI + LangGraph（见 `backend/`）
- **前端**：见 `frontend/`（后续持续补充）

## 后端已实现接口

- `POST /api/upload`
- `POST /api/simulation/start`
- `GET /api/health`

## 文档入口

- 接口索引：`docs/api/README.md`
- 接口详细契约：`docs/api/接口文档.md`
- 研究问题：`docs/研究问题.md`
- 论文/顶层后端方案：`docs/后端方案.md`
- 后端代码运行说明：`backend/README.md`

## 本地运行（后端）

```bash
conda activate frame
cd backend
./scripts/dev.sh
```

## 仓库结构

```text
frame/
├── README.md
├── docs/             # 项目文档与接口文档
├── data/             # 研究 case 原始数据（前后端共享）
├── frontend/         # 前端工程
├── backend/          # Python 后端
└── .gitignore
```

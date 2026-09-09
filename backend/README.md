# Backend（Python / FastAPI）

用于模拟 `Framing Shift in Online Discourse` 的后端服务。  
当前为 V1 可联调版本：已支持上传、模拟启动、健康检查、多层拓扑生成、运行快照落盘与基础测试。

## 1. 环境要求

- Python `3.11+`
- conda 环境：`frame`
- 包管理：统一使用 `python -m pip`（避免装到系统环境）

## 2. 快速启动

```bash
conda activate frame
cd backend
# 首次可先生成本地环境变量文件
# cp .env.example .env
./scripts/dev.sh
```

`scripts/dev.sh` 会做两件事：

1. 检查当前 conda 环境是否为 `frame`
2. 安装依赖并启动 `uvicorn app.main:app --reload`

默认服务地址：`http://127.0.0.1:8000`

## 3. API 概览

- `POST /api/upload`
  - 上传图片（`FormData.file`）
  - 返回 `{ url?: string, dataUrl?: string }`
- `POST /api/simulation/start`
  - 启动同步模拟
  - 入参包含：`agentCount`、`agentCategories`、`description?`、`topic?`、`imageRef?`
  - 返回：`tree`、`agentLog`、`summary`、`pathOffsetTrend` 等
- `GET /api/health`
  - 返回 `{ "ok": true }`

接口详细契约请看：`docs/api/接口文档.md`

## 4. 项目结构

```text
backend/
├── app/
│   ├── api/                 # 路由层（upload/simulation/health）
│   ├── schemas/             # Pydantic 契约模型
│   ├── services/            # 主流程（simulation/upload）
│   ├── graph/               # LangGraph runner + NodeA/B/C
│   ├── agents/              # LLMClient / TaxonomyAdapter / RuleGuard
│   ├── analysis/            # 偏移分析
│   └── infra/               # 存储等基础设施
├── scripts/dev.sh           # 本地开发启动脚本
├── tests/                   # pytest 测试
├── requirements.txt
└── README.md
```

## 5. 配置项（环境变量）

推荐做法：

- 本机配置放在 `backend/.env`（已默认忽略，不上传）
- 团队模板放在 `backend/.env.example`（可上传）
- 启动脚本会在存在 `.env` 时自动使用 `uvicorn --env-file .env`

- `USE_TAXONOMY`（默认 `false`）
  - `true`：预留给正式 taxonomy 数据源（V1 仍以 fallback 规则为主）
- `USE_LLM`（默认 `false`）
  - `true`：尝试真实 LLM 调用；失败自动降级到本地 fallback
- `OPENAI_API_KEY`（可选）
  - `USE_LLM=true` 时建议提供
- `OPENAI_BASE_URL`（可选，默认 `https://api.openai.com/v1`）
- `OPENAI_MODEL`（可选，默认 `gpt-4o-mini`）
- `SIM_MAX_DEPTH`（默认 `3`）
  - 控制模拟拓扑最大深度

## 6. 测试

运行全部测试：

```bash
conda activate frame
cd backend
python -m pytest -q
```

## 7. 运行产物说明

- `backend/storage/uploads/`：上传文件的本地存储
- `backend/storage/runs/`：每次模拟的运行快照（含 request/response/provenance）

这两类都属于运行时产物，已在根 `.gitignore` 中忽略，不提交 GitHub。

## 8. 开发建议

- 先看 `app/schemas/api_contract.py`（接口边界）
- 再看 `app/services/simulation_service.py`（主流程）
- 多智能体编排看 `app/graph/langgraph_runner.py`
- 规则与降级看 `app/agents/`

## 9. 数据位置说明

- 当前项目约定：原始 case 数据统一放在仓库根目录 `data/`
- 后端不直接依赖该目录运行，主要通过前端上传/传参驱动
- `data/` 作为研究数据资产保留，便于前后端与研究侧共享

## 10. 开发留痕规则（协作约定）

- 开发修改前，除阅读代码外，先阅读：`docs/backend/后端工程技术方案.md`
- 开发修改后，必须同步更新：
  - `docs/backend/后端工程技术方案.md`（当前实现与进度）
  - `docs/backend/CHANGELOG.md`（追加式记录，append-only）
- `CHANGELOG` 每条至少包含：
  - 时间、任务名称、变更目标、影响范围、接口影响
  - 测试命令、测试结果、风险与后续待办
- 目的：保证后端实现、文档与历史记录一致，降低长周期 AI 协作中的漂移风险

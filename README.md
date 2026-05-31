# Y.Scape — Phase 9

> Transactional Agent Runtime（当前阶段：Frontend Functional UI）

## 已实现

| Phase | 内容 |
|-------|------|
| **1–7** | Runtime → Recovery 全链路 |
| **8–9** | 功能型 React 控制台（7 面板 + 冒烟验收） |

## 前端面板

| 面板 | 功能 |
|------|------|
| Mission Console | 场景选择、目标输入、创建并启动、Run ID |
| Status Bar | runState / thinking / progress / heartbeat / stale 标志 |
| Timeline | SSE 事件 + polling 回退 + Replay |
| Artifact Explorer | md/json/txt 列表与点击预览 |
| Markdown Preview | 独立 artifact API，错误明确展示 |
| Recovery Actions | cancel / retry / resume 按状态显隐 |
| Debug Panel | DEV 模式 snapshot / event / audit-wal-replay 链接 |

## 运行

```bash
# 后端
cd backend
uvicorn src.main:app --reload --port 8000
pytest tests/ -v

# 前端
cd frontend
npm install
npm run dev      # http://localhost:5173
npm run build

# API 冒烟（需后端已启动）
python scripts/smoke_api.py
```

## Recovery API

```
POST /api/tasks/{id}/cancel
POST /api/tasks/{id}/retry
POST /api/tasks/{id}/resume
GET  /api/tasks/{id}/replay
```

下一阶段：**Phase 10 — E2E + docs**

# Y.Scape Architecture — Phase 1

## 设计目标

Y.Scape 是 **Transactional Agent Runtime**，不是 Chatbot。Phase 1 建立状态权威层：

```
API → RunManager → WAL → Snapshot (memory) → Checkpoint (disk)
```

## Phase 1 组件

| 模块 | 职责 |
|------|------|
| `runtime_state.py` | RunState、TaskType、PlannerContext、RunRecord |
| `wal.py` | 预写日志，所有 mutation 先落盘 |
| `checkpoint.py` | 可恢复 checkpoint + planner context |
| `status_snapshot.py` | `active_snapshots` 热缓存 |
| `run_manager.py` | 生命周期、状态迁移、heartbeat、stale watchdog |

## Status 轻量约束

`GET /api/tasks/{id}/status`：

- ✅ 读 `active_snapshots`
- ❌ 不读 WAL / audit log
- ❌ 不扫 workspace / artifacts 目录
- ❌ 不等待 worker / 不调 LLM

## WAL 事件（Phase 1 已用）

- `RUN_CREATED`
- `STATE_CHANGED`
- `SNAPSHOT_CREATED`

完整 WAL 事件集见 Section XVIII，Phase 3–7 逐步启用。

## 后续 Phase 预览

- **Phase 2**: EventBus + SSE + `execution_log.jsonl` Timeline
- **Phase 3–7**: Tools → Demo → Synthesis → Quality → Recovery
- **Phase 8**: Frontend Console
- **Integration**: ToolAdapter 已骨架化，真实 adapter 从 P1 起逐步实现

详见 [PHASES.md](./PHASES.md)

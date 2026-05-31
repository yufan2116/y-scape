# Y.Scape 开发阶段

## Phase 11 ✅（当前）

**QA / Bug Bash / Demo Readiness**

- 会话恢复（localStorage → status / events / preview）
- 全部 loading 超时 + fallback
- 按钮状态修正（Cancel / Retry / Resume / 新建任务）
- 布局溢出修复（1080p / 1366px）
- 安全文本渲染（无 undefined/null/NaN）
- E2E pytest：`test_phase11_e2e.py`（67 tests passed）

## Phase 10 ✅

**Visual Polish — Star-Rail-inspired sci-fi dashboard**

- `frontend/src/styles/starRailTheme.css` — design tokens
- 宇宙背景 / 玻璃卡片 / 金色边框 / HUD 状态 / 中英混排标题
- 布局：Sidebar + 中栏（Mission / Run State / Timeline / Thinking / Tools）+ 右栏（Artifacts / Preview）+ Footer
- 角色位占位卡片（用户自行填入）
- 纯 CSS 装饰（gradient / glow / pseudo-elements）
- `npm run build` ✅

## Phase 9 ✅

**Frontend Functional UI — 验收与稳定化**

- 7 块功能面板全部可用：Mission / Status / Timeline / Artifact / Preview / Recovery / Debug
- Timeline Replay（从 events API 重载）
- SSE 断线 events polling 回退
- 启动/恢复错误在 Mission Console 可见
- Windows 路径修复（`note_md_demo` artifact 写入）
- 冒烟脚本：`python frontend/scripts/smoke_api.py`

验收：`cd frontend && npm run build` ✅

## Phase 8 ✅

**Frontend Functional UI（初版）**

## Phase 7 ✅

**Recovery — cancel / retry / resume + WAL replay**

- `WalReplayEngine` — 从 `wal.jsonl` 重建 completed_steps / pending tool
- `POST /retry` — FAILED / QUALITY_BLOCKED / STALE 等状态重试
- `POST /resume` — WAL_REPLAY → CHECKPOINT_RESTORED → 继续 Agent Loop
- `POST /interrupt` — 协作式中断（区别于 cancel）
- `GET /replay` — 恢复决策（can_resume / can_retry）
- Resume 时跳过已完成步骤（证据/synthesis 等从磁盘 + WAL 推断）

## Phase 6 ✅

**Deliverable Quality Gate**

## Phase 5 ✅

**Research Memory + Synthesis**

## Phase 4 ✅

**Demo Mode + Agent Loop**

## Phase 1–3 ✅

Runtime / Events / Tools

## Phase 10 — E2E + docs

（待开始）

## Integration（并行于 Phase 3+）

- P0: ToolAdapter + adapter stubs ✅
- P1: GitHub Resume
- P2: Download-tool
- P3: QuickForge Launcher

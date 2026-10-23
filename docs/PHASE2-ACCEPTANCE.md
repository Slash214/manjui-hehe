# 阶段 2 中间验收记录

2026-10-23。本轮为中间交付，阶段 2 尚未全部完成。运行中的正式 Compose 服务未更新，用户仍访问原服务 http://127.0.0.1:15173 。没有执行真实 ComfyUI、GPU 或付费模型请求。

## 已完成代码

- models：Workflow、GenerationTask、Candidate、Shot 两个采用指针；迁移 bbbde02c0fd1；不可变任务快照及候选数据库保护。
- domain：task_state、snapshot、workflow_mapping；providers/generation：协议、FFmpeg mock、ComfyUI 适配器。
- services/generation、services/workflows、repos/generation；api/generation、api/events。
- workers/generate、workers/reconcile：可靠投递、任务执行、取消后丢弃输出、手动重试、心跳对账。
- 前端 GenerationPanel、导演页同屏接入、资产版本生成入口；候选最多两项对比、采用、任务抽屉、SSE 重连与轮询。
- 新版规格原样保存，旧版备份 docs/SPEC-v1-original-0-14.md；DECISIONS 新增 17–23。

## 已运行证据

- 后端全套 pytest：39 passed。Ruff：All checks passed。mypy：40 source files 通过。
- 前端 TypeScript 严格检查、Vite build、ESLint 通过；CSS 语义 token 修正后尚需最终再构建及视觉检查。
- SQLite 隔离库迁移 upgrade/downgrade/upgrade/check 通过。
- PostgreSQL 隔离库 `manju_phase2_verify_592fac453f00`：upgrade head/downgrade base/upgrade head/check 通过，应用库不回滚、不清空。
- `tests.verify_generation`：真实 Redis、独立 Celery worker、FFmpeg 与 MinIO 跑通关键画面生成/采用/视频生成/采用；ffprobe 校验 H.264。
- 同时提交同一幂等键返回同一任务；运行中改镜头后快照不变；直接 SQL 改快照被拒绝；候选不自动采用。
- 失败中文提示及新任务 retry_of_task_id、运行中取消通过；只强杀本脚本创建的隔离 worker，重启后失联任务变为 WORKER_LOST。
- 本轮曾因测试脚本错误预期旧 CRUD 返回 201 而失败；已修正为原接口 200，并完整重跑通过。

## 阶段 2 验收清单当前状态

| 验收项 | 当前结果 |
| --- | --- |
| mock 关键画面/采用/视频/采用 | 后端真实队列与存储通过；浏览器未验证 |
| 真实 ComfyUI 关键画面与视频 | 未验证：缺用户工作流及本轮执行授权 |
| 重复点击不重复任务 | 并发 API 测试通过；浏览器重复点击待验证 |
| 提交后编辑不改快照 | 通过，含真实队列运行中编辑及 DB 保护 |
| 候选不覆盖、错误提示、重试新任务 | 后端通过；浏览器显示待验证 |
| worker 中断恢复 | 通过，独立测试 worker 强杀后 WORKER_LOST |
| 无真实进度不显示百分比 | 后端 progress=null 通过；浏览器待验证 |

## 下一轮继续事项

1. 补完整 ComfyUI 协议受控测试、并发额度的 PostgreSQL 并行测试、资产生成/采用与跨目标拒绝测试；真实 ComfyUI 仍标未验证。
2. 检查导演旧普通图片 API 已采用画面的回退显示，保留旧体验；完善缩略图、状态与候选分页/历史可访问性。
3. 更新最新镜像并对正式应用库只执行升级；保持 15173。当前构建镜像早于最后少量代码修正，集成测试通过只读挂载最新源码运行，不能直接声称部署最新版本。
4. 浏览器完整路径、重复提交、取消/失败重试、两个桌面宽度与真实截图；补前端回归。
5. 收尾 README/工作流配置样例/启动说明；修订本清单最终结果。不得开始 2.5 或后续音视频阶段。

重跑隔离集成命令（项目目录）：
```powershell
docker compose run --rm --no-deps -v D:\github\manjui-hehe\backend:/app:ro api python -m tests.verify_generation
```
该脚本创建独立测试库和队列，仅结束自己创建的 worker。测试库与测试对象保留用于复核，不删除用户数据或卷。

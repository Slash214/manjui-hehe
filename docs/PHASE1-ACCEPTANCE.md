# 阶段 1 最新验收结论

2026-10-23：正式 Compose 路径已验证，阶段 1 五项验收通过。下方旧记录保留为历史，其中 Docker 阻塞已解决。

- Compose 六个服务启动，storage-init 成功退出；API/PostgreSQL/Redis 健康，worker inspect ping 返回 pong。
- 隔离库 manju_phase1_verify_6abcaa6f9464：PostgreSQL upgrade→downgrade→upgrade→check 通过，5项 API 测试通过。未回滚应用库。
- 真实 PNG 上传 MinIO，追加资产版本且旧版本/current 指针保持不变；下载哈希一致，签名有效期3600秒；无签名403，1秒签名过期403。
- 容器 Chrome：2 passed，含双页签409、刷新/重新登录恢复、Ant删除取消/确认、1440×900及1366×768截图。
- 阶段1后端14 passed，Ruff/mypy（19源码文件）、TS/ESLint/build 通过。新创作增量验收单列。
- 正式演示 http://127.0.0.1:15173 使用 PostgreSQL + MinIO。原5173演示是 SQLite + MinioStorage，保留原数据。
- MinIO旧镜像tag不可用，改为固定官方源码release容器构建；未安装宿主机软件。
- UI十条结论沿用历史记录，Ant 暗色算法映射 Radix，中文locale、无动画。CSS .5px在Windows Chrome DPR1计算为1px，此差异已记录。

## 历史记录（先前阻塞现已解决）

# 阶段 1 验收记录

2026-10-23，Windows 本机 D:\github\manjui-hehe。仅本项目，未初始化/提交/推送 Git，未公网部署，未连接 ComfyUI，未运行 GPU 或付费模型。

**结论：本地阶段 1 功能测试通过，整套基础设施验收待 Docker 环境恢复。阶段 1 尚不能标为全部验收通过，停止在阶段 1。**

| SPEC 验收项 | 实际结果与限制 |
| --- | --- |
| 一条命令启动全部服务，迁移可升可降 | **部分验证**：已提供 scripts/start-compose.ps1；SQLite 独立测试库 upgrade → downgrade → upgrade → check 通过，版本不可更新/删除触发器测试通过。PostgreSQL/Redis/MinIO/worker Compose 启动未验证，Docker Engine 未运行 |
| 创建项目、写剧本并确认、角色/地点资产版本、建立引用镜头 | **本地通过**：API 集成测试；真实本地 API 建立《大唐小饭馆》3 场、5 项资产、11 镜头。API 测试使用 MockStorage；真实 MinIO 上传未验证 |
| 确认后继续编辑，查看历史，恢复新草稿 | **通过**：修改后旧快照不变、恢复台词、历史记录仍保留；UI 提供确认、历史与恢复按钮 |
| 双页签修改同一镜头，后保存返回 409 并显示冲突 | **通过**：真实 Chrome 两页签，一页保存后另一页 PATCH 收到 409，中文提示可见、草稿保留，截图 conflict-1366.png |
| 刷新或重新登录后顺序、内容、选中镜头保留 | **通过**：API 排序冲突原子回滚；Chrome 刷新、入口切换、实际退出后重新登录恢复示例选中镜头，11 镜头仍在 |

## 已运行检查

- pytest：14 passed；包含 8 个纯函数测试、5 个 API 集成测试、1 个迁移升降与不可变触发器测试。
- Ruff：通过。
- mypy：19 个后端源码文件通过（新增 API 未增加文件数）。
- Python compileall：通过。
- TypeScript 严格模式：通过。
- ESLint：通过。
- Vite production build：通过。
- PostgreSQL 迁移离线 SQL 生成通过，循环外键与不可变版本触发器存在，文件 postgresql-migration.sql；这不等同于真实 PostgreSQL 执行通过。
- Playwright：2 passed，使用本机已有 Chrome，不下载浏览器。覆盖 409、草稿保留、刷新、导航、登录/重新登录、两个桌面尺寸和真实截图。
- 高级 JSON 参数 800ms 自动保存已通过真实浏览器及 API 回读验证。
- 测试期间修复过浏览器定位器名称与隐藏区域定位问题；最终结果以上述成功运行结果为准。
- 非阻断警告：Starlette TestClient 提示未来迁移 httpx2；本次 httpx 集成测试均成功。

## UI 十项要求

1. 界面中点分隔：已移除；原始 SPEC 不改写。
2. 说明文案：已减少，保留保存失败、冲突、版本和恢复后果。
3. 中文文案：使用创作术语与明确动作；未添加假进度/假生成结果。
4. Radix：使用官方 slate/gold/red/green 暗色阶，无自定义 hex 色。
5. 对齐：统一工具栏、列表、检查器内边距；导演、故事、资产截图人工检查。
6. 边框：CSS 0.5px。**实测差异**：Windows Chrome，deviceScaleFactor=1 时 computed border 为 1px；浏览器将半 CSS 像素按物理像素量化，已保留 0.5px 声明，未声称渲染为半个物理像素。
7. 动画：无装饰动画和过渡。
8. 字号：全站 12/14/20/28px 四档；导演实际检测到 12/14/28px，最小 12px。
9. 决策：常规编辑自动保存，明确资产版本引用与必要覆盖确认仍保留。
10. 圆角阴影：控件与容器使用固定少量半径，无装饰阴影或卡片左侧色条。

1440×900 与 1366×768 均无横向页面溢出。导演正文与右侧表单可独立滚动；故事页场次元数据折叠，让台词编辑保持在主要区域。

截图：[导演 1440](screenshots/sample-director-1440.png)、[导演 1366](screenshots/sample-director-1366.png)、[故事](screenshots/sample-story-1366.png)、[资产](screenshots/sample-assets-1366.png)、[冲突](screenshots/conflict-1366.png)。

## 阻塞与所需动作

### 用户启动 Docker 后的复检

用户确认已启动 Docker 后，普通命令 `docker version --format '{{.Server.Version}}'` 再次检查，未返回 Server 版本：

```
WARNING: Error loading config file: open C:\Users\Administrator\.docker\config.json: Access is denied.
permission denied while trying to connect to the docker API at npipe:////./pipe/docker_engine
```

`docker compose version` 返回 v5.3.1，同时仍有上述配置文件权限警告。与首次检查相比，Engine 管道不再报告不存在，而是连接权限被拒绝；不能据此声称 Engine 健康检查通过。

本次未启动 Compose 栈、未拉取镜像、未执行 PostgreSQL 迁移或 MinIO 上传、未修改容器/数据卷，未读取受限配置内容或变更 ACL。原有本地演示保留。

最小下一步：由用户在可访问 Docker Desktop 的本机 PowerShell 中运行 `docker version`，确认可显示 Server 信息。如果用户终端成功而本任务仍拒绝，需要为本任务提供具有 Docker 访问权限的授权执行会话；不需要提供 config.json 内容或任何凭证。恢复权限后，再使用本项目隔离测试库验证迁移回滚。

以下为首次检查记录，当前阻塞以上述复检为准：

- `docker info --format '{{.ServerVersion}}'`：失败，`//./pipe/docker_engine` 不存在。需要用户启动已有 Docker Desktop，确认 Linux containers/Engine 可用。
- Docker CLI 还报告读取 `C:\Users\Administrator\.docker\config.json` Access denied。未读取该文件内容，未绕路或复制凭证；需要用户保证当前执行账号可使用 Docker。此为系统访问拒绝，不是等待中的审批。
- 只读进程命令行诊断 Get-CimInstance 被 Windows 拒绝；未重试，不影响项目运行。
- npm 原来不在 PATH，已用项目内固定版本解决。Python/npm 依赖安装完成，没有待批准安装。
- FFmpeg 不在 PATH；阶段 1 无音视频处理，不阻塞此阶段业务。后续阶段若需系统安装应另行授权。
- 没有进行真实 PostgreSQL 并发或 MinIO 上传签名读取验证。不能把 SQLite/MockStorage 的通过结果当成这些验证已完成。

## 已知范围限制

- 常规字段和高级 JSON 参数按 800ms 自动保存，格式错误保留草稿。
- 全部复查矩阵已有纯函数与测试；完整触发、持久化和 SSE 在后续规定阶段接入。
- 当前本地演示 SQLite 数据库位于 backend/local.db，不提交到版本控制；生产 Compose 使用 PostgreSQL 数据卷。
- 目录原本不是 Git 仓库。现有 docs/SPEC.md 未改变，根 SPEC.md 与其 SHA-256 一致。

# 漫剧工作台

> 当前提交为阶段 2 WIP。后端 39 项测试及隔离 PostgreSQL/Redis/Celery/FFmpeg/MinIO 验证已通过；阶段 2 浏览器验收与最新版本部署未完成，真实 ComfyUI 未验证。完整状态见 [阶段 2 中间验收](docs/PHASE2-ACCEPTANCE.md)。

阶段 1：剧本、资产版本、镜头编排。React 18 / TypeScript / Vite / TanStack Query / Zustand / Tailwind，FastAPI / SQLAlchemy 2 / Alembic。界面为 Radix Colors 暗黑工作区。

规格见 [SPEC.md](SPEC.md)，实现选择见 [DECISIONS.md](DECISIONS.md)，实际验收见 [docs/PHASE1-ACCEPTANCE.md](docs/PHASE1-ACCEPTANCE.md)。生成、ComfyUI、配音、字幕、时间线和导出没有实现，也不会调用模型或 GPU。

## Docker 启动

前提：Docker Desktop 已安装并运行，当前账号可访问 Docker Engine。首次构建需要拉取镜像与依赖。仅绑定本机 127.0.0.1。

当前实测：官方提权审批路径已恢复 Docker 访问，Compose 已启动。独立 PostgreSQL 测试库迁移升降、真实 MinIO 上传/签名和 worker Redis ping 均通过。本次容器前端为 http://127.0.0.1:15173，API 为 http://127.0.0.1:18000；原 SQLite 演示 5173/8000 保留。

在项目目录执行一条命令（PowerShell 7）：

```powershell
pwsh -File scripts/start-compose.ps1
```

脚本仅在 .env 不存在时从 .env.example 建立配置并随机生成 JWT_SECRET，然后执行 `docker compose up --build -d`。不会覆盖已有 .env。默认本地 MinIO/PostgreSQL 密码请在任何非本地使用前自行更换。

- 前端 http://127.0.0.1:5173
- API 文档 http://127.0.0.1:8000/docs
- MinIO 控制台 http://127.0.0.1:9001
- API 启动前执行 Alembic upgrade；storage-init 等待 MinIO 并创建 bucket；worker 只有基础进程，不注册生成任务。
- 停止：`docker compose down`；保留数据卷。不要添加 `-v`，除非明确需要删除数据。

迁移验证仅在脚本新建的隔离测试库执行，不回滚应用库：

```powershell
docker compose exec -T api python -m tests.verify_infrastructure
```

## 当前 Windows 本地运行

已经建立项目内 `.venv`、`.tools/npm` 和 `frontend/node_modules`，未修改系统 PATH。Docker 尚未运行时，SQLite 仅供本地功能演示，不作为 PostgreSQL 验收。

后端终端：

```powershell
$env:JWT_SECRET='local-development-secret-at-least-32-characters'
Set-Location backend
../.venv/Scripts/python.exe -m alembic upgrade head
../.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

前端终端：

```powershell
Set-Location frontend
node node_modules/vite/bin/vite.js --host 127.0.0.1
```

从零安装本项目依赖（不是系统安装）：

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r backend/requirements.lock.txt
python scripts/bootstrap_npm.py
Set-Location frontend
node ../.tools/npm/package/bin/npm-cli.js install --ignore-scripts --cache ../.tools/npm-cache
```

npm 引导脚本下载固定版本并比对 registry SHA-512。可使用自己已有的 npm 替代。若网络受限，报告错误，不绕过凭证或访问限制。

## 演示

已用真实本地 API 建立附录示例《大唐小饭馆》，3 个场次、5 项资产、11 个镜头，没有伪造生成结果。当前示例地址保存在 [docs/demo.json](docs/demo.json)。

本地示例账号：`demo@manju.local`，密码：`Manju-Local-2026!`。仅用于本机测试数据。该账号不是应用内置账号，空数据库需运行 `.venv/Scripts/python.exe scripts/seed_demo.py` 创建。脚本每次运行创建新的示例项目。

## 测试

```powershell
Set-Location backend
../.venv/Scripts/python.exe -m pytest -q
../.venv/Scripts/python.exe -m ruff check app tests
../.venv/Scripts/python.exe -m mypy app
Set-Location ../frontend
node node_modules/typescript/bin/tsc -b
node node_modules/eslint/bin/eslint.js src
node node_modules/vite/bin/vite.js build
node node_modules/@playwright/test/cli.js test
```

浏览器测试使用已安装 Chrome（不会下载浏览器），需先启动本地 API/Vite 并运行 seed_demo。API 测试为 SQLite + MockStorage，真实 MinIO 仍需 Docker 环境验证。

## 内容与版本约定

- 更新必须带 `base_version`，镜头当前版本字段为 `content_version`；过期版本返回 409 `VERSION_CONFLICT`，不覆盖。
- 删除通过 `?base_version=N`，使用软删除。用户无法访问其他账号资源。
- 场次、台词、镜头排序：POST 集合 `/reorder`，`items` 对象按目标顺序列出全部 ID 及对应基线版本。
- 剧本确认生成完整不可变快照。恢复改写当前草稿，历史仍保留；将解除对恢复后不存在内容的镜头绑定。
- 参考图上传从指定资产版本追加新版本；不修改旧版本、镜头引用或当前版本。图片最大 20MB，PNG/JPEG/WebP；访问 URL 1 小时有效。
- 镜头动作、引用和台词绑定都会增加 content_version。手改提示词自动启用手动模式，不再覆盖；取消手动模式即可重建。
- 普通文本编辑防抖 800ms 自动保存。冲突保留页签草稿，需用户处理。高级 JSON 参数同样自动保存，格式错误时保留草稿并提供重试。草稿按账号与资源隔离，选中镜头写入 URL 和本地偏好。
- 复查传播矩阵全行已实现纯函数；完整持久化触发和人工清除在阶段 4 接入。

## 配置

`.env.example` 列出数据库、Redis、MinIO、JWT、ComfyUI/TTS 预留项。LLM_ENABLED=false；ComfyUI 和 TTS 环境项在阶段 1 不用于连接外部服务。

当前 `/healthz` 仅检查数据库；全依赖健康检查属于阶段 5。若 MinIO 不可达，上传会返回中文 STORAGE_ERROR。Docker 配置无权限时应由用户修复账户权限，不读取受限配置或绕过权限。

## AI 创作接入基础（独立增量）

单集点击“AI 创作”，展开“模型配置”，分别建立文本/图片演示 mock。生成剧本、对白、资产、镜头或提示词候选，预览后明确采用。追加类不覆盖旧内容，改写类显示原内容；输入版本变化返回409。

OpenAI 兼容文本与图片协议已经 mock HTTP 测试，真实网络传输未启用。配置只接收非秘密字段和 MANJU_MODEL_* 环境变量名，不接收真实 key。本轮没有配置凭证、素材外发或付费调用。图片演示没有图片文件，不能作为画面采用。

详情见 docs/CREATIVE-ACCEPTANCE.md、docs/SKILL-INTEGRATION-PLAN.md 和 THIRD_PARTY_NOTICES.md。MinIO 固定源码镜像说明见 infra/minio/README.md。原视频生成、配音和导出仍未开始。

# 阶段 1 决策

规格来源为根目录 SPEC.md，与最初已有 docs/SPEC.md 保持字节一致（419 行）。仅阶段 1。

1. 不创建生成、候选、音频、字幕、时间线和导出业务表。镜头的 adopted 指针在阶段 2 引入外键时添加。Celery 只有空 worker 骨架，LLM 默认关闭且没有调用入口。
2. 所有可编辑对象使用 version；镜头使用 content_version。更新、删除、排序、绑定、版本创建和设为当前均需基线版本；数据库条件更新负责 409。写操作按项目行加锁，避免剧本确认与场次修改交错。
3. API 中含糊的场次和台词单项地址明确为 /scenes/{id} 与 /lines/{id}，增加集合 /reorder；单集补齐 DELETE。列表以 offset/limit 分页，最多 500 条。
4. 剧本恢复复用原场次/台词 ID，恢复到可编辑草稿；旧快照不变。快照中不存在的当前内容软删除，并解除镜头对被移除内容的绑定。仍存在的绑定保留。恢复会提示覆盖当前草稿。
5. 上传参考图不可修改 asset_versions：从指定版本复制并追加版本，不自动设为当前、不自动更新镜头引用。第一条版本设为当前，之后由用户显式选择。仅接收真实可解码 PNG/JPEG/WebP，限制 20MB；文件地址有效 1 小时。
6. 删除被镜头引用的场次/台词返回 IN_USE，引导先解除引用；项目和集软删除后其下级内容不能访问。版本表有 ORM 写保护，PostgreSQL 迁移另加不可更新/删除触发器。
7. 前端普通编辑防抖 800ms，失败和 409 均保留草稿且暂停自动重试。草稿保存在当前页签 sessionStorage，按账号/资源隔离。选中镜头保存在 ?shot= 及按账号/集隔离的 localStorage。登录 JWT 保存在 localStorage，12 小时有效；本地 MVP 尚无刷新 token。
8. 生产存储是 MinIO，API 测试注入 MockStorage。SQLite 仅用于独立的本地/API 测试，不能代替 PostgreSQL Compose 验收。
9. UI 只读采用 @fan/b2b-saas-sap-patterns v1.0.1：稳定状态、列表/详情布局、显式标签、错误保留输入。来源 https://uiskill.sh/fan/b2b-saas-sap-patterns 。完整 SKILL.md 和三个 references 已阅读，不运行 CLI，不复制发布原技能。用户暗黑影视创作工具要求优先于 SAP 视觉方向。
10. 颜色采用 @radix-ui/colors 的 slate/gold/red/green 暗色阶。遵循官方 1–2 背景、3–5 控件、6–8 边框、9–10 实色、11–12 文本语义。全部字号归为 12/14/20/28px；边框为 0.5px，取消装饰阴影与动画。详见 docs/UI-GUIDELINES.md。
11. 本机缺少 npm；只在 .tools/npm 下载 npm 10.9.2 并验证 npm registry 提供的 SHA-512。Python 依赖装入 .venv；不修改系统 PATH，不安装系统软件。Docker Desktop 及其配置由用户管理，不读取或绕过受限配置。

12. Ant Design 6.6.7 支持 React18，仅用于操作按钮、错误提示和删除确认；ConfigProvider darkAlgorithm、Radix语义色、中文locale、motion=false，保留定制导演布局。字体4档，边框声明0.5px。
13. Docker通过官方审批执行访问，旧MinIO tag不可用，改为官方 RELEASE.2025-10-15T17-29-55Z 源码在容器中构建。当前本地Compose端口15173/18000，避免覆盖SQLite演示。
14. 用户新增授权的AI创作基础与原阶段2-5分开。模型配置追加保存非秘密环境变量引用；真实网络传输关闭；自有协议适配器只注入MockTransport测试。暂不承诺任意兼容供应商。
15. 创作候选保留完整输入版本与来源commit，必须明确采用。剧本/资产/镜头为追加，台词/提示词为定点改写；版本不一致409。候选快照数据库触发器保护，旧结果不删除。
16. 图片API当前只有配置、请求映射和明确mock候选元数据，不伪造图片文件；真实出图、队列、视频路线待独立授权与服务配置。

## 阶段 2（开发中，尚未全部验收）

17. 本轮以用户上传的 520 行新版规格为准，根目录与 docs/SPEC.md 原样同步；419 行旧版保存在 docs/SPEC-v1-original-0-14.md。第 15 节的 AuthoringProvider 与尾帧接力不在本轮实现。
18. 生成独立使用 workflows/generation_tasks/candidates，既有 CreativeCandidate 和 ShotCreativeImage 历史保留，不伪造其 ComfyUI 任务来源。
19. queued/running 均占并发额度，每镜头 2、每账号 3；账号行锁串行化提交。幂等键在账号内唯一，重复键参数不同返回 409。快照、目标、工作流、重试关系及种子由数据库触发器保护。
20. 已提交的 queued 数据库记录作为可靠投递源，worker 每 3 秒扫描投递；重复消息依靠任务行锁只执行一次。没有自动失败重试。失联 running 默认 90 秒后对账，无法确认输出则 WORKER_LOST。
21. 取消只终结平台任务并停止接收结果，不发送可能影响其他用户的 ComfyUI 全局 interrupt；远端已运行任务可能继续消耗算力。重试明确建立新任务，默认复制原快照。
22. mock 使用容器内 FFmpeg 产出有 MOCK 标记的 PNG/MP4；不在宿主系统安装 FFmpeg。ComfyUI 默认关闭，工作流必须显式登记；缺少映射的字段不可用。官方协议参考 https://raw.githubusercontent.com/comfyanonymous/ComfyUI/master/script_examples/websockets_api_example.py ，真实工作流尚未验证。
23. SSE 使用带 Bearer 的 fetch 流，断线重连后补拉当前任务与候选；不宣称重放所有历史事件。界面同时保留轮询恢复。资产采用会追加新版本，不修改原资产版本或镜头旧引用。

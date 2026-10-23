# 漫剧平台开发规格书（AI 实现版）

版本 1.0 ｜ 2026 年 10 月 23 日 ｜ 依据《漫剧平台产品流程与 MVP 方案》讨论稿整理，已把待定项落为默认决策

## 0. 如何使用本文档

本文档写给负责实现的 AI 或工程师，请严格遵守：

1. **分阶段实现。** 第 10 节把工作拆成 5 个阶段，每次只做一个阶段，通过该阶段验收后再进入下一阶段。不要一次生成整个系统。
2. **以本文档为准。** 第 2 节已把原讨论稿的所有「待确认」项落为默认决策，按默认执行，不要自行新增需求。文档没有规定的细节，选最简单的实现，并记录在仓库根目录的 `DECISIONS.md`。
3. **每阶段交付：** 可运行代码、数据库迁移、自动化测试、README 更新、该阶段验收清单的逐项结果。
4. **不要伪造。** 拿不到真实进度就不显示百分比；没有 ComfyUI 工作流文件就使用 mock 适配器并明确标注。
5. **第 5.2 节「铁律」优先级最高**，任何功能都不得违反。

## 1. 产品目标与范围

**一句话目标：** 用户在一个单集工作台里，从剧本到成片连续完成一集 AI 对话剧情漫剧，并始终知道做到哪里、哪些结果待确认、下一步做什么。

**分工：** 平台负责内容、资产、版本、确认和任务追溯；ComfyUI 等生成工具只负责执行，不替代创作判断。

**首期要做：** 项目与单集管理；剧本与场次编辑；角色、造型、地点、道具、音色资产及版本复用；可直接编辑的镜头列表；ComfyUI 关键画面与图生视频两条生成路径；任务状态、失败原因、受控重试；候选比较与采用；后期配音、字幕、最小时间线、整集预览与导出；自动保存与重新打开恢复；局部修改的复查提示。

**首期不做：** 动态解说制作方式；完整专业剪辑；多用户协作与权限；全季自动规划；批量生产；多模型同时接入；三维制作链路；自动口型同步与检测；九宫格视图。

## 2. 默认决策表

| 议题 | 默认决策 |
| --- | --- |
| 目标用户 | 个人创作者或小团队；一个项目只属于一个账号，不做协作 |
| 账号 | 邮箱加密码登录，JWT 鉴权 |
| 制作类型 | 只做 AI 对话剧情；`production_type` 字段预留，默认 `dialogue_drama` |
| 剧本输入 | 用户粘贴或手写，手动拆分场次；LLM 辅助拆分作为可选扩展（LLMProvider 接口，默认关闭） |
| 单集入口 | 四个主入口：故事、资产、导演、成片，路由 `/episodes/:id/story` 等 |
| 关键画面 | 默认先确认关键画面再生成视频；镜头可设 `use_keyframe=false` 跳过，此时由文本加参考图直接生成视频 |
| 声音路线 | 每镜 `dialogue_source` 取 `none`、`dubbed`、`native`。首期完整实现 `dubbed`（TTS 或上传音频）；`native` 仅表示使用视频自带声音并标记，不做分轨与识别 |
| 口型 | 不做自动检测；对白来源变更时仅标记待复查 |
| 时长 | 灵活；区分镜头预计时长、生成片段时长、时间线采用时长；10–15 个镜头仅作起稿参考 |
| 复查与确认 | 规则见 5.3；项目所有者可确认 |
| 重试 | 自动重试 0 次，全部手动；重试默认复用原快照建立新任务；同一镜头最多 2 个运行中任务，单账号最多 3 个并发 |
| 导出规格 | MP4（H.264 加 AAC），默认 9:16、1080×1920、24fps，项目可改为 16:9、1920×1080；字幕默认烧录并同时导出 SRT |
| ComfyUI 范围 | 首期 2 条工作流：文生图（关键画面）、图生视频；由用户提供工作流 JSON |
| 文件存储 | MinIO，经 StorageProvider 抽象 |
| 界面语言 | 中文，不做多语言 |

## 3. 技术架构

默认技术栈可整体替换，但接口边界保持不变：

| 层 | 选型 |
| --- | --- |
| 前端 | React 18、TypeScript、Vite、TanStack Query（服务端状态）、Zustand（工作台本地状态）、Tailwind CSS |
| 后端 API | Python 3.11、FastAPI、SQLAlchemy 2、Alembic |
| 数据库 | PostgreSQL 15 |
| 队列 | Redis 加 Celery |
| 文件存储 | MinIO（S3 协议） |
| 生成执行 | ComfyUI（HTTP API 提交，WebSocket 取进度），经 GenerationProvider 抽象 |
| 音视频处理 | FFmpeg |
| 语音合成 | TTSProvider 抽象（默认 mock，另配一个可由环境变量配置的真实实现） |
| 实时推送 | SSE（任务状态、复查标记变化） |
| 部署 | docker-compose：api、worker、postgres、redis、minio；ComfyUI 为外部服务，地址由环境变量配置 |

**后端分层：** routers → services → repositories；`providers/`（storage、generation、tts、llm，各含 mock 实现）；`workers/`（generate、tts、export 任务）；`domain/`（状态机、复查传播、快照构建，全部写成纯函数并必须有单元测试）。

**仓库结构：** `backend/app/{api,services,repos,domain,providers,workers,models,schemas}`、`backend/tests`、`frontend/src/{pages,components,stores,api}`、`workflows/`（ComfyUI JSON 与参数映射）、`docs/`、`docker-compose.yml`、`DECISIONS.md`。

## 4. 数据模型

**通用约定：** 主键 UUID；所有表带 `created_at`、`updated_at`；用户内容表软删除（`deleted_at`）；`*_versions` 表只追加、不可修改；外键建索引；枚举以字符串存储，并在代码中集中定义。

**用户与项目**

- `users`：id、email、password\_hash
- `projects`：owner\_id、name、description、style\_prompt（全局画风）、aspect\_ratio、resolution、fps、production\_type
- `episodes`：project\_id、episode\_no、title、target\_duration\_sec（仅参考）、confirmed\_script\_version\_id

**剧本**

- `script_versions`：episode\_id、version\_no、snapshot\_json（场次与台词完整快照）、note、confirmed\_by、confirmed\_at。确认剧本即生成一条，之后仍可继续编辑
- `scenes`：episode\_id、order\_no、time\_of\_day、location\_asset\_id、title、summary
- `scene_lines`：scene\_id、order\_no、line\_type（dialogue、narration、action）、character\_asset\_id（可空）、text、edited\_at

**资产**

- `assets`：project\_id、asset\_type（character、costume、location、prop、voice）、name、parent\_asset\_id（造型挂在角色下）、current\_version\_id
- `asset_versions`（只追加）：asset\_id、version\_no、description、prompt、params\_json、reference\_file\_id、voice\_config\_json（音色资产使用）

**镜头**

- `shots`：episode\_id、scene\_id、order\_no、action\_desc、shot\_size、camera\_angle、camera\_movement、blocking\_desc（站位与视线）、est\_duration\_ms、use\_keyframe、dialogue\_source、sfx\_note、prompt\_text、prompt\_overridden（用户是否手改过提示词）、params\_json、content\_version（每次内容编辑加 1）、adopted\_keyframe\_candidate\_id、adopted\_video\_candidate\_id、review\_status（confirmed、needs\_review）、review\_reasons\_json
- `shot_lines`：shot\_id、line\_id、order\_no（镜头承载哪些台词）
- `shot_asset_refs`：shot\_id、asset\_version\_id、role、order\_no（参考图顺序）

**生成**

- `workflows`：name、kind（keyframe、video）、comfy\_json、param\_map\_json、version、enabled
- `generation_tasks`：shot\_id、kind、status（queued、running、succeeded、failed、canceled）、snapshot\_json、workflow\_id、comfy\_prompt\_id、seed、retry\_of\_task\_id、idempotency\_key、progress（可空）、error\_code、error\_message、queued\_at、started\_at、finished\_at
- `candidates`：shot\_id、task\_id、kind（keyframe、video）、file\_id、duration\_ms、meta\_json。「已采用」不存在候选上，而是由 `shots` 的两个 adopted 指针表示
- `files`：storage\_key、mime、size\_bytes、sha256、width、height、duration\_ms

**声音、字幕、成片**

- `audio_clips`：shot\_id、line\_id、source（tts、upload、native）、text\_hash、voice\_asset\_version\_id、file\_id、duration\_ms、review\_status、is\_adopted
- `subtitles`：episode\_id、shot\_id、line\_id、text、start\_ms、end\_ms、review\_status
- `timelines`：episode\_id（唯一）、data\_json（视频、对白、音乐、音效四条轨道及片段）、version
- `exports`：episode\_id、timeline\_snapshot\_json、settings\_json、status、video\_file\_id、srt\_file\_id、error\_message
- `audit_events`：project\_id、actor\_id、entity\_type、entity\_id、action、payload\_json

**任务快照 `snapshot_json` 必含：** 镜头 content\_version、实际提示词、参考图文件及顺序、引用的 asset\_version\_id 列表、workflow\_id 与版本、模型标识、实际参数、seed（支持时）。快照在提交任务的同一事务内写入，此后只读。

## 5. 状态与规则

### 5.1 三类状态，互相独立

- **任务状态**（回答机器执行到哪）：queued → running → succeeded 或 failed 或 canceled。
- **采用状态**（回答用户选了什么）：候选，或已采用。由镜头上的 adopted 指针表达。
- **复查状态**（回答输入变化后结果是否仍可用）：confirmed 或 needs\_review。

集的对外状态由系统推导，不单独存储：存在已采用视频的镜头不足时为「制作中」；所有镜头都有已采用视频即「可预览」；存在 needs\_review 时为「待确认」；导出成功且之后无改动为「已确认导出」。

### 5.2 铁律

1. 新生成的候选永远不自动替换已采用结果，只有用户明确点击「采用」才改指针。
2. 版本表只追加；旧版本、旧候选、旧任务记录不删除。
3. 任务快照在提交时写入，之后修改镜头不影响已排队或运行中的任务。
4. 重试等于新建任务，`retry_of_task_id` 指向原任务；默认复用原快照，若用户改了参数则生成新快照。
5. 拿不到真实进度时 `progress` 为空，界面不显示百分比。
6. 任何镜头内容编辑都使 `content_version` 加 1，并触发 5.3 的复查传播，且只影响相关对象，不清空整集。
7. 任务成功不等于完成：整集是否完成由 5.4 的检查和人工确认决定。
8. 提交任务必须带 `idempotency_key`，重复点击不产生重复任务。

### 5.3 复查传播矩阵

| 触发修改 | 标记为 needs\_review 的对象 | reason code |
| --- | --- | --- |
| 修改台词文本 | 关联镜头的 dubbed 音频、对应字幕、该镜头预计时长；若 dialogue\_source 为 native，则该镜头已采用视频 | `line_changed` |
| 修改镜头动作、景别、机位、站位 | 本镜头已采用关键画面与视频；前后相邻镜头（仅提示衔接） | `shot_changed`、`adjacent_changed` |
| 更换或更新资产版本 | 列出所有引用旧版本的镜头，由用户选择更新范围；不自动改引用 | `asset_updated` |
| 变更对白来源 | 该镜头字幕、时长、已采用视频 | `dialogue_source_changed` |
| 修改镜头预计时长 | 时间线中对应片段（提示可能不匹配） | `duration_changed` |
| 修改音色资产 | 使用该音色的 TTS 音频 | `voice_changed` |

`review_reasons_json` 为列表，每项含 code、来源对象 id、时间。清除方式只有两种：用户点「确认仍可用」，或生成新候选并采用。导出前集中展示所有待复查项。

### 5.4 导出前检查（preflight）

- **阻断项：** 存在没有已采用视频的镜头；时间线为空；无法读取的文件。
- **警告项（用户确认后可继续导出）：** 存在 needs\_review 的镜头、音频或字幕；字幕与台词不一致；同一句台词同时存在原生声与后配音；时间线出现意外空段；对白轨被音乐轨盖住（对白音量低于音乐）。

## 6. API 规格

**约定：** REST 加 JSON，前缀 `/api/v1`；JWT Bearer 鉴权，所有资源接口校验归属；时间使用 ISO 8601 UTC；错误统一返回 `{code, message, details}`，`message` 为用户可读的中文；可编辑实体带版本号（镜头用 `content_version`），更新时必须回传 `base_version`，不一致返回 409 `VERSION_CONFLICT`；提交生成与导出必须带 `idempotency_key`。

| 模块 | 接口 | 说明 |
| --- | --- | --- |
| 认证 | `POST /auth/register`、`POST /auth/login`、`GET /me` | 注册、登录、当前用户 |
| 项目 | `GET/POST /projects`、`GET/PATCH/DELETE /projects/{id}` | 项目增删改查，含画风、画幅、分辨率、帧率 |
| 集 | `GET/POST /projects/{id}/episodes`、`GET/PATCH /episodes/{id}` | 单集管理 |
| 剧本 | `GET /episodes/{id}/script` | 返回场次与台词 |
|  | `POST/PATCH/DELETE /episodes/{id}/scenes`、`/scenes/{id}/lines` | 场次、台词增删改与排序 |
|  | `POST /episodes/{id}/script/confirm`、`GET /episodes/{id}/script/versions` | 确认剧本生成版本、查看历史 |
|  | `POST /episodes/{id}/script/versions/{vid}/restore` | 把旧版本复制为当前草稿，不删除历史 |
| 资产 | `GET/POST /projects/{id}/assets`、`GET/PATCH /assets/{id}` | 资产库 |
|  | `GET/POST /assets/{id}/versions`、`POST /asset-versions/{id}/reference-image` | 版本列表、新建版本、上传参考图 |
|  | `POST /asset-versions/{id}/generate` | 用关键画面工作流生成参考图 |
|  | `POST /assets/{id}/set-current` | 设置当前版本 |
| 镜头 | `GET/POST /episodes/{id}/shots`、`PATCH/DELETE /shots/{id}` | 镜头增删改，PATCH 触发复查传播 |
|  | `POST /episodes/{id}/shots/reorder` | 调整顺序 |
|  | `PUT /shots/{id}/refs`、`PUT /shots/{id}/lines` | 设置引用资产版本、承载台词 |
|  | `POST /shots/{id}/review/confirm` | 确认仍可用，清除复查标记 |
| 生成 | `POST /shots/{id}/generate` | 参数：kind、workflow\_id、overrides、idempotency\_key |
|  | `GET /shots/{id}/tasks`、`GET /tasks/{id}` | 任务列表与详情（含快照） |
|  | `POST /tasks/{id}/retry`、`POST /tasks/{id}/cancel` | 重试（可选沿用原快照）、取消 |
|  | `GET /shots/{id}/candidates`、`POST /shots/{id}/adopt` | 候选列表、采用 |
| 声音 | `GET /shots/{id}/audio`、`POST /shots/{id}/audio/tts`、`POST /shots/{id}/audio/upload` | 配音生成与上传 |
|  | `POST /audio/{id}/adopt` | 采用某段音频 |
| 字幕 | `GET/PUT /episodes/{id}/subtitles`、`POST /episodes/{id}/subtitles/regenerate` | 编辑，或按最新台词生成草稿（不覆盖手改） |
| 时间线 | `GET/PUT /episodes/{id}/timeline`、`POST /episodes/{id}/timeline/rebuild` | 编辑，或按镜头顺序重建 |
| 预览与导出 | `POST /episodes/{id}/previews`、`GET /episodes/{id}/preflight` | 生成低清整集预览、导出前检查 |
|  | `POST /episodes/{id}/exports`、`GET /exports/{id}` | 导出（有警告项时需 `acknowledge_warnings=true`） |
| 实时 | `GET /projects/{id}/events` | SSE，事件类型：`task.updated`、`shot.review_changed`、`export.updated`、`timeline.updated` |

## 7. ComfyUI 集成规格

**7.1 工作流注册。** 每条工作流由两部分组成：ComfyUI 的 API 格式 JSON，以及 `param_map`。`param_map` 描述平台字段到节点输入的映射（节点 id 加输入名）。平台字段固定为：`prompt`、`negative_prompt`、`seed`、`width`、`height`、`ref_image_1` 到 `ref_image_n`、`first_frame`、`frame_count`、`fps`。工作流文件放在 `workflows/`，启动时同步入库并记录版本；缺少某字段映射则该字段不可用，不得硬编码节点 id。

**7.2 提交与执行流程。**

1. service 校验镜头与参考资产，构建快照。
2. 同一事务内创建 task（queued）并写入快照，随后投递 Celery。
3. worker 把参考图上传到 ComfyUI，按 `param_map` 填入工作流，调用 `POST /prompt`，记录 `comfy_prompt_id`。
4. 通过 WebSocket 监听 executing、progress、executed 事件，状态置为 running。
5. 完成后读取 history，下载输出文件，存入 MinIO，创建 candidate，task 置为 succeeded，SSE 推送。
6. 新候选只进入候选区，不改变采用指针。

**7.3 进度。** ComfyUI 的 progress 事件只有在工作流含单个采样节点时才可信，否则 `progress` 置空，界面只显示「生成中」和已用时，不伪造百分比。

**7.4 失败分类与文案。**

| error\_code | 含义 | 建议 |
| --- | --- | --- |
| `COMFY_UNREACHABLE` | 连不上 ComfyUI | 可重试 |
| `COMFY_VALIDATION` | 工作流校验失败，如缺节点或缺模型 | 先修配置，重试无意义 |
| `COMFY_EXECUTION` | 执行报错 | 可重试，展示节点与报错摘要 |
| `TIMEOUT` | 超时（默认：关键画面 5 分钟，视频 20 分钟，可配置） | 可重试 |
| `OUTPUT_MISSING` | 执行成功但没有输出 | 可重试 |
| `STORAGE_ERROR` | 结果保存失败 | 可重试 |
| `WORKER_LOST` | worker 中断 | 先对账再决定 |

每种错误都要有面向用户的中文说明，并明确告知「重试会消耗额外算力」。不做自动重试。

**7.5 崩溃恢复。** worker 定期写心跳；启动时扫描心跳过期的 running 任务，用 `comfy_prompt_id` 查询 ComfyUI history 对账：已有输出则补完收尾，否则置为 failed（`WORKER_LOST`）。

**7.6 mock 适配器。** 无 GPU 或测试时使用，返回 FFmpeg 生成的带文字纯色图和视频，支持注入延迟和各类失败，所有自动化测试默认使用 mock。

**7.7 提示词构建。** 最终提示词由项目画风、引用资产描述、镜头动作、景别、机位、站位依次拼接。`prompt_overridden=false` 时随镜头内容自动重建；用户手改后不再自动覆盖，镜头内容变化时只提示「是否重新生成提示词」。

**7.8 对第 4 节的补充。** `generation_tasks` 增加可空字段 `asset_version_id`，用于资产参考图生成；`shot_id` 与 `asset_version_id` 必须二选一。

## 8. 前端页面规格

**8.1 全局。** 页面包括：项目列表、项目页（集列表、资产库、设置）、单集工作台。工作台顶部固定条常驻显示项目名、集名、保存状态、待确认数量徽标，以及故事、资产、导演、成片四个入口。切换入口不丢失当前集和选中镜头（选中镜头写入 URL 参数 `?shot=`）。编辑自动保存（防抖 800 毫秒），状态为「已保存」「保存中」「保存失败，点击重试」；有未保存内容时离开页面要提示。

**8.2 故事。** 左侧场次列表可拖拽排序；中间是台词编辑器，每行可选对白、旁白、动作，对白可选角色；右侧显示本集信息与「确认剧本」按钮。确认后生成版本，版本列表可查看，可恢复为新草稿。台词被已有镜头引用时，修改后触发 5.3 的复查传播并给出提示。

**8.3 资产。** 资产库分角色、造型、地点、道具、音色五个标签，以卡片展示。详情抽屉含版本列表、新建版本、上传或生成参考图、设为当前。工作区顶部显示「本集缺少的资产」：由场次地点和台词角色推导，每项可一键新建或选择复用。音色资产支持试听。

**8.4 导演（主工作区）。**

| 区域 | 内容 |
| --- | --- |
| 左侧 | 按场次折叠的镜头列表；每项含缩略图、序号、预计时长、状态标记（无画面、生成中、失败、已采用、待复查） |
| 中间 | 预览区，分「关键画面」「视频」两个页签；下方候选条，可点选预览、采用、并排对比（最多 2 个）；任务信息抽屉可查看快照 |
| 右侧 | 镜头表单：动作、景别、机位、运镜、站位视线、承载台词、对白来源、音效、预计时长、引用资产（带版本，有新版本时提示）、提示词（自动或手改）、高级参数（默认折叠） |
| 底部 | 全集镜头条带，宽度按时长比例；点击跳转；「从当前镜头连续预览」依次播放已采用视频，缺失的跳过并提示 |

主按钮顺序：先「生成关键画面」，采用后出现「生成视频」；`use_keyframe=false` 的镜头直接显示「生成视频」。采用后默认自动选中下一个镜头（可关闭），让用户在一处完成「改动作或台词、提交生成、比较候选、采用、下一镜」。

**8.5 成片。** 时间线（四轨）、播放器、字幕列表编辑、导出前检查面板、导出按钮与导出历史。

**8.6 通用规范。** 三类状态必须用不同的视觉元素：任务状态用图标徽标（排队中、生成中、成功、失败），采用状态用对勾标签，复查状态用黄色「待复查」标记且悬停显示原因。所有错误提示使用普通用户能看懂的中文，并给出下一步。空状态必须有引导。

## 9. 声音、字幕、时间线与导出

**9.1 对白。** 每个镜头的 `dialogue_source` 三选一。

- `dubbed`：对每条承载台词生成 audio\_clip（TTS 或上传），可试听并采用。界面显示「对白实际时长 / 镜头预计时长」，超出时只提示，用户可点「按对白时长调整预计时长」；不得为了凑时长自动加速声音。
- `native`：不生成 audio\_clip，只作标记，使用视频自带声音；提示用户检查对白是否准确。
- `none`：无对白。

同一句台词不能同时使用原生声与已采用的后配音。切换来源时，旧的已采用配音置为未采用但保留文件，并触发 `dialogue_source_changed` 复查。

**9.2 字幕。** 草稿由承载台词生成：文字取台词文本；起点为该镜头在时间线上的起点，终点按已采用音频时长，没有音频时按每字 0.25 秒估算。用户可改文字与时间。台词变更时字幕置为待复查，不自动覆盖手改内容，由用户点「按最新台词更新」。

**9.3 时间线数据（`timelines.data_json`）。** 四条轨道：video、dialogue、music、sfx。片段字段：id、track、source\_type（shot\_video、audio\_clip、upload）、source\_id、start\_ms、in\_ms、out\_ms、volume、fade\_in\_ms、fade\_out\_ms。规则：视频轨按镜头顺序自动重建，只支持裁剪与硬切，不支持叠层；对白轨按镜头起点自动放置；音乐与音效轨可上传音频、调整位置与音量；片段间出现空段时界面标出。

**9.4 预览。** 整集预览由服务端渲染低清代理文件（540 级分辨率，快速编码），与导出使用同一条 FFmpeg 管线，保证所听所见与导出一致；另提供逐镜头的前端快速预览用于编辑中检查。

**9.5 导出管线（FFmpeg）。**

1. 读取 timeline 的快照（不是实时数据），写入 `exports.timeline_snapshot_json`。
2. 视频：每个片段裁剪后统一缩放、补边到目标分辨率与帧率，像素格式 yuv420p，再拼接。
3. 音频：每个音频片段按 start\_ms 延迟、调音量、淡入淡出，与保留的视频原生音轨一起混合；视频的 `dialogue_source` 不是 native 时去掉其原生音轨，避免重复对白。
4. 字幕：同时生成 SRT 并烧录到画面；镜像内必须安装中文字体（如 Noto Sans CJK），位置底部居中，带描边。
5. 编码 H.264（crf 20）加 AAC（192k），输出到 MinIO。
6. 失败时保存 FFmpeg 报错末尾 50 行；`exports.settings_json` 同时记录实际执行的命令，保证可复现。

**「已确认导出」的判定：** 最近一次导出成功，其快照哈希与当前时间线一致，且集内没有 `needs_review` 项。

## 10. 分阶段开发计划与验收

每个阶段独立可运行、可演示。进入下一阶段的条件是上一阶段验收清单全部通过。

### 阶段 1：基础骨架与单集界面（不含生成）

**范围：** 工程骨架（docker-compose、迁移、鉴权、StorageProvider）；项目、集、场次、台词的增删改查与排序；剧本确认与版本；资产与资产版本（含上传参考图）；镜头列表编辑、引用资产版本、承载台词；工作台壳（四入口、固定顶栏、选中镜头保持）；自动保存、冲突检测、重新打开恢复；`domain/` 中的复查传播函数与单元测试（先实现函数，暂不接入全部触发点）。

**验收：**

- [ ] 一条命令启动全部服务，迁移可升可降。
- [ ] 用测试集完成：创建项目、写剧本并确认、新建角色与地点资产及其版本、建立镜头并引用资产版本。
- [ ] 修改已确认剧本后仍可继续编辑，历史版本可查看，可恢复为新草稿。
- [ ] 两个浏览器页签同时编辑同一镜头，后保存者收到 409 并看到冲突提示。
- [ ] 刷新或重新登录后，顺序、内容、选中镜头均保留。

### 阶段 2：生成任务、候选与采用

**范围：** GenerationProvider 抽象及 mock、ComfyUI 两个实现；工作流注册与 `param_map`；任务快照、Celery 队列、幂等；SSE；候选、采用、取消、重试；失败分类与中文文案；崩溃恢复对账；导演页的预览区、候选条、对比、任务抽屉；资产参考图生成。

**验收：**

- [ ] mock 下完整走通「生成关键画面、采用、生成视频、采用」。
- [ ] 连接真实 ComfyUI 时，至少一个镜头成功产出关键画面与视频（若暂无环境，注明「未验证」）。
- [ ] 连续快速点击两次生成只产生一个任务。
- [ ] 生成过程中修改镜头，已提交任务的快照不变。
- [ ] 新候选不会替换已采用结果；任务失败时展示可理解原因，重试产生带 `retry_of_task_id` 的新任务。
- [ ] 强杀 worker 后重启，运行中任务被对账收尾或标为 `WORKER_LOST`。
- [ ] 拿不到真实进度时界面不显示百分比。

### 阶段 3：声音、字幕、时间线与导出

**范围：** TTSProvider 及 mock；音频上传；`audio_clips` 与采用；对白时长回显；字幕草稿与编辑；时间线数据、编辑与重建；预览渲染；导出管线；preflight；成片页界面。

**验收：**

- [ ] 一集带对白和字幕，导出可播放的 MP4 与 SRT，`ffprobe` 校验分辨率、帧率、音轨存在、总时长与时间线一致。
- [ ] 同一句台词不会同时出现原生声与后配音。
- [ ] 对白实际时长超出镜头预计时长时只提示，不自动加速。
- [ ] 字幕文字与对应台词一致；手改字幕不被自动覆盖。
- [ ] 预览文件与导出文件在内容、顺序、声音上一致（仅分辨率不同）。
- [ ] 导出失败时可见错误摘要，可再次导出。

### 阶段 4：版本、复查与局部重做

**范围：** 5.3 复查矩阵的全部触发点接入；`review/confirm`；资产版本更新引导（列出引用旧版本的镜头并让用户选择范围）；导出前集中提示；「已确认导出」判定；集状态推导；SSE 推送复查变化。

**验收：**

- [ ] 只重做一个镜头，其他镜头的候选与采用结果完全不变。
- [ ] 修改台词后，对应配音、字幕、预计时长出现待复查标记，其他镜头不受影响。
- [ ] 更新资产版本后，列出受影响镜头，不自动改动引用。
- [ ] 有待复查项时导出，必须先看到集中提示并确认。
- [ ] 采用新结果或点击「确认仍可用」后，待复查标记消失。

### 阶段 5：加固与可选扩展

**范围：** 性能与错误文案打磨；审计日志查看；文件清理任务（软删除 30 天后清理孤儿文件）；备份与恢复说明；部署文档；可选的 LLM 辅助场次拆分（默认关闭）。

**验收：**

- [ ] 100 个镜头的单集，镜头列表和工作台操作保持流畅。
- [ ] `/healthz` 能报告数据库、Redis、MinIO、ComfyUI 的可达性。
- [ ] README 包含从零部署、配置项、备份恢复、常见故障排查。

### 总验收（对应原讨论稿的一集实测）

用一集真实作品逐项验证并记录测试集、复现步骤和实际结果：

- [ ] 创建并确认剧本，编辑场次和对白。
- [ ] 复用角色、地点、道具，并看到所引用的版本。
- [ ] 直接修改镜头动作、对白、预计时长。
- [ ] 提交真实任务，比较候选并明确采用一个。
- [ ] 任务失败后原因可见，可受控重试。
- [ ] 只重做一个镜头不影响其他镜头和已采用结果。
- [ ] 修改台词或资产后，相关下游出现局部复查提示。
- [ ] 带声音连续预览整集，并导出可播放文件。
- [ ] 退出后重新打开，顺序、进度、候选、采用版本都还在。

## 11. 非功能与测试要求

**测试。** `domain/` 的状态机、复查传播、快照构建、提示词构建必须有单元测试，覆盖 5.3 矩阵的每一行；API 层用 mock provider 写集成测试；前端用 Playwright 覆盖主路径「改动作、生成、采用、切到下一镜」；导出用小样本做 FFmpeg 集成测试，并用 `ffprobe` 校验结果。

**安全。** 密码使用 argon2 或 bcrypt；上传限制类型与大小（图片 20MB、音频 50MB）；文件通过有时效的预签名地址访问（默认 1 小时）；所有接口校验资源归属；生成与导出接口限流。

**性能与可靠性。** 列表接口分页；SSE 断线自动重连，重连后补拉最新状态；所有 worker 任务可重入。

**可观测。** 结构化日志，`task_id`、`shot_id`、`episode_id` 贯穿；提供 `/healthz`。

**数据。** 用户内容软删除；项目删除先标记，30 天后由清理任务删除文件；迁移必须可回滚。

**配置项（环境变量）。** `DATABASE_URL`、`REDIS_URL`、`S3_ENDPOINT`、`S3_ACCESS_KEY`、`S3_SECRET_KEY`、`S3_BUCKET`、`COMFYUI_BASE_URL`、`COMFY_TIMEOUT_KEYFRAME_SEC`、`COMFY_TIMEOUT_VIDEO_SEC`、`TTS_PROVIDER`、`TTS_API_KEY`、`JWT_SECRET`、`MAX_CONCURRENT_TASKS_PER_USER`。

**代码规范。** 后端类型标注并通过 ruff 与 mypy；前端通过 eslint 与 TypeScript 严格模式。

## 12. 开始前需要人工提供的输入

| 输入 | 提供方 | 缺失时的处理 |
| --- | --- | --- |
| ComfyUI 地址，以及文生图、图生视频两条 API 格式工作流 JSON 和节点说明 | 用户 | 使用 mock，并在 `workflows/` 放占位文件与 `param_map` 示例 |
| 显卡环境与单次生成耗时 | 用户 | 超时使用默认值 |
| TTS 服务与密钥 | 用户 | 使用 mock TTS，同时支持上传音频 |
| 一集测试剧本 | 用户 | 使用附录示例 |
| 项目画风与画幅 | 用户 | 默认 9:16、1080×1920 |
| 内容合规要求 | 用户 | 首期不做小说导入，只处理用户自己粘贴的文本，并在新建项目时提示需确认拥有内容使用权 |
| 中文字体 | 部署 | 镜像内置 Noto Sans CJK |

## 13. 给 AI 的启动提示词

**每阶段开始时使用：**

```
你是资深全栈工程师。请完整阅读《漫剧平台开发规格书》。
本次只实现「阶段 N」，不要触及其他阶段的范围。
要求：
1. 先输出实现计划：文件清单、数据库迁移、接口、页面，再开始写代码。
2. 严格遵守第 5.2 节铁律与第 2 节默认决策；规格未规定的细节选最简单方案，并记录到 DECISIONS.md。
3. 提供可运行代码、迁移、自动化测试、README 更新。
4. 完成后对照本阶段验收清单逐项自测并给出结果；无法验证的项标注「未验证」及原因，不得伪造。
```

**阶段结束时使用：**

```
请汇报阶段 N：已通过与未通过的验收项、已知问题、DECISIONS.md 的新增条目。
在我明确说「进入阶段 N+1」之前，不要开始下一阶段。
```

## 14. 附录

### 14.1 测试集示例：《大唐小饭馆》第 1 集（约 60 秒）

- **角色：** 沈知味、掌柜。**地点：** 饭馆大堂、后厨。**道具：** 饭碗。
- **场次 1，白天，饭馆大堂：** 掌柜拍桌，对白「三个月房租，今天必须结清！」；沈知味回应「掌柜的，您先坐，容我做碗饭，吃完再说。」
- **场次 2，白天，后厨：** 动作为沈知味颠勺、火光腾起；旁白「一碗蛋炒饭，粒粒分明。」
- **场次 3，白天，饭馆大堂：** 掌柜吃完，放下碗沉默片刻，对白「……再来一碗。」结尾旁白留悬念。
- **镜头起稿：** 10 到 12 个，时长不强求一致，对白镜头以配音时长为准。

### 14.2 术语

| 术语 | 定义 |
| --- | --- |
| 项目 | 一部作品，保存画风、资产和各集 |
| 集 | 可独立预览和导出的视频单元 |
| 场次 | 某时间某地点发生的一段戏 |
| 镜头 | 一次连续呈现的画面，一场次含多个镜头 |
| 资产 | 可复用的角色、造型、地点、道具、音色，按版本管理 |
| 生成任务 | 一次具体的 AI 执行，带输入快照 |
| 候选 | 任务返回的结果，需用户采用才生效 |
| 采用 | 用户明确选定某候选作为镜头当前结果 |
| 复查 | 输入变化后，对已有结果是否仍可用的人工确认 |

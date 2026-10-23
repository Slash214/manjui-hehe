# AI 创作接入基础验收

2026-10-23，独立于原 SPEC 阶段 2–5 的新增授权增量。当前可运行在 http://127.0.0.1:15173 ，从单集顶栏进入“AI 创作”。

## 已实现与实测

- `GET /creative/skills`：10项版本化目录，固定来源commit/路径/许可/状态及适配操作的输入输出schema。
- `GET/POST /creative/models`：文本与图片用途分开，mock或明确的OpenAI兼容协议；仅保存非秘密配置和服务端环境变量名。配置追加保存，旧候选保留原配置引用。
- `GET/POST /episodes/{id}/creative/candidates`：剧本草稿/对白改写、资产提取、镜头规划、提示词优化；严格JSON合同，保存输入快照、输入版本、来源、模型与结果。创建不修改现有内容。
- `POST /creative/candidates/{id}/adopt`：明确采用才追加场次/资产/镜头或定点改写台词/提示词。base_version与输入版本检查；重复采用和输入变化409。快照由ORM及数据库触发器保护，旧结果保留。
- 图片路径：独立配置、ImageProvider接口、兼容协议请求映射、mock候选元数据；明确没有图片文件，禁止采用为真实画面。
- 页面：操作→模型→要求→候选预览→采用；改写显示原文，追加显示拟新增内容；暗色Radix样式，中文标签，收起模型及来源详情。没有10套CLI按钮。

## 验证证据

- 后端全套：17 passed（原14项及新增3项组合测试）；Ruff通过，mypy24源码文件通过。
- PostgreSQL新建隔离库 `manju_phase1_verify_0f384abb24e6`：升级、降级、再次升级、alembic check通过；8项API/创作测试通过，包含四类操作、改写、人工采用、版本冲突、归属、未知schema字段拒绝、无密钥报错、图片边界和mock HTTP协议错误。
- SQLite迁移测试验证候选输入/输出不可修改或删除，人工采用状态允许变更；PostgreSQL检查保护触发器存在。应用数据库从未回滚。
- Chrome：3 passed，覆盖模型配置、候选预览、明确采用、刷新历史，及原工作台双页签409、重新登录恢复、Ant取消/确认。截图 [创作页](screenshots/creative-candidate-1366.png)、[导演页](screenshots/sample-director-1366.png)。
- TypeScript严格模式、ESLint、Vite生产构建通过；没有新增整包体积警告。

## 十项来源实际状态

|来源|当前结果|
|---|---|
|Screenwriting Skills|原创方法精简适配，剧本/对白规则、JSON合同及mock流程已测试；不含书籍/剧本摘录|
|Visual Skills|单镜提示规划方法适配、请求合同及mock测试；保留CC BY4归因和agentara致谢|
|shuohao-skills|仅登记审计版本/路径/Apache2许可；未复制脚本或启用character-refs|
|manju-laoli-skill|资产/镜头规划方法精简适配与mock流程测试；未整包复制根提示词或伪API载荷|
|Awesome Seedance|仅登记；代码技能MIT与编选CC BY4、原始媒体权利分开，未打包案例|
|Seedance 2.0|仅登记专用模型规划，未启用执行，不混入通用模板|
|Scenario Skills|需服务配置；MCP/OAuth/model_run未启用|
|Pexo Skills|需服务配置及执行安全审查；根MIT/frontmatter MIT-0差异记录，代理/token脚本未运行|
|Jianying Editor|来源不可访问，多路404；未猜测替换来源|
|Drama Skills|URL待用户确认；未安装|

许可原文及NOTICE见 `docs/licenses/`，改编说明见根 `THIRD_PARTY_NOTICES.md`。

## 明确未验证/未启用

真实模型生成质量、真实供应商连通、计费、素材外发均未测试。mock是固定演示输出，不能代表真实AI编剧。OpenAI兼容适配器只允许注入HTTP MockTransport，未创建网络传输；启用真实调用前还需供应商能力校验、DNS/IP绑定和出口策略及明确计费授权。模型密钥只接受环境变量引用，本轮未创建任何真实凭证。

图片API没有实际图片，也未进入原阶段2任务队列。ComfyUI视频、TTS、字幕、时间线、导出仍未展开。并非10个技能全部集成成功。

非阻断限制：Windows Chrome DPR1把CSS0.5px边框计算为1px；Starlette发出未来httpx2迁移提醒，当前测试均通过。原5173/8000SQLite演示保留，新增增量以15173/18000容器地址为准。

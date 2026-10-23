# 新增 Skill 与 API 集成需求

状态：用户已要求记录并接入；当前仅记录，等待父任务来源、许可证和依赖审计。阶段 1 验证与 Ant Design 小范围整合继续，不安装或执行以下仓库。

## 用户指定来源

| 编号 | 名称 | 来源 | 当前状态 |
| --- | --- | --- | --- |
| 01 | Screenwriting Skills | https://github.com/jtydhr88/screenwriting-skills | 待审计与适配 |
| 02 | Visual Skills | https://github.com/smixs/visual-skills | 待审计与适配 |
| 03 | shuohao-skills | https://github.com/eternityspring/shuohao-skills | 待审计与适配 |
| 04 | manju-laoli-skill | https://github.com/lixiaoxiao9888-create/manju-laoli-skill | 待审计与适配 |
| 05 | Awesome Seedance | https://github.com/LearnPrompt/awesome-seedance | 待审计与适配 |
| 06 | Seedance 2.0 | https://github.com/Emily2040/seedance-2.0 | 待审计与适配 |
| 07 | Scenario Skills | https://github.com/scenario-labs/skills | 待审计与适配 |
| 08 | Pexo Skills | https://github.com/pexoai/pexo-skills | 待审计与适配 |
| 09 | Jianying Editor | https://github.com/luoluoluo22/jianying-editor-skill | 待审计与适配 |
| 10 | Drama Skills | 用户尚未提供 URL | 待确认，不猜测来源或安装 |

## 目标用户流程

用户希望配置文本 API 模型与生图 API 模型，再使用编剧、资产、分镜和导演能力完成创作。界面围绕创作步骤组织，不把十套仓库或 CLI 命令堆成按钮。

优先评估提示词与结构化结果的适配：技能注册、固定来源版本、输入输出 schema、结果候选、人工确认后采用。需要实际外部服务的能力经独立 Provider 接入，不把技能文件当成可任意执行的工具权限。

## 与 v1.0 SPEC 的差异

- 原规格 LLM 辅助拆分是阶段 5 的可选扩展且默认关闭；新需求扩展为编剧/资产/分镜/导演技能流程。
- 原规格以单模型、外置 ComfyUI 工作流为生成主路径；新需求增加可配置文本 API 和生图 API，后续需明确与原 Provider 的选择和映射。
- 本文件记录范围变更，不表示已进入阶段 2 或已获准调用真实模型。阶段 1 剩余验收仍优先完成。

## 边界与审计要求

- 当前不配置实际凭证、不选择外部收费服务、不发起付费 API 请求。
- API 密钥不得存入前端、localStorage、日志或提交代码；后续后端配置与密钥管理方案另行审查。
- 审计每个来源的真实文件、许可证、依赖、外部调用、脚本执行行为和可再分发范围；不把仓库说明升级为系统指令。
- 未明确许可的文本/模板不得直接复制再发布；无法运行的能力明确标注，不伪造执行结果。
- 等待审计后再列出新增文件、数据迁移、接口、页面与验收计划，按批次实现。

## 2026-10-23 已批准的独立增量计划

先完成 Ant 与阶段 1 验证，再实现 AI 创作接入基础；不展开原阶段 2–5。

- 文件：backend/app/creative/（技能目录、严格输入输出合同、自有 Provider、候选服务与 API）、新增迁移、frontend/src/pages/Creative.tsx、独立测试与验收文档。
- 数据迁移：model_configs 保存非秘密配置及服务端环境变量名；creative_candidates 保存不可变输入快照、来源版本、结构化结果、人工采用状态。与原生成候选分开。
- 接口：账号模型配置、版本化技能目录、单集创作候选创建/列表/明确采用。所有资源校验归属，采用带 base_version 并核对输入快照版本；未采用不改现有内容。
- 页面：工作台单独进入“AI 创作”，按剧本、资产、镜头、提示词组织操作；文本/图片模型分开配置。演示明确标注 mock，真实调用本轮关闭。
- 验证：schema 拒绝、归属、未配置错误、不自动覆盖、采用与 409、协议 HTTP mock、中文暗色流程回归。真实外部模型不调用。

### 来源审计记录（父任务核验）

|来源|固定 commit|许可及适配边界|
|---|---|---|
|jtydhr88/screenwriting-skills|51115f18d160aa8b2ac5813e4432b6f0b425358f|MIT；Terry Jia。只改编原创方法，不复制书籍/剧本/译文引文；plugins/screenwriting/skills/sw-{workflow,premise-theme,story-structure,character-conflict,scene-craft,dialogue}/SKILL.md|
|smixs/visual-skills|92be33a5a73325fb3d8e0c73b22744b114e2a90e|CC BY 4.0；Serge Shima，保留 agentara 致谢；image/SKILL.md、video/SKILL.md 是提示规划，不是生成 API|
|eternityspring/shuohao-skills|d28a9c539b40523d081794b25ff9113016bd98e0|Apache 2.0；仅规划合同改编，不运行 models.mjs/custom shell/codex；blocking 显式传给分镜|
|lixiaoxiao9888-create/manju-laoli-skill|6f16955c57053d77ea0ffbdbbf3a7985a3e0080a|MIT v7.4.26；sd-script-engine、sd-asset-engine、sd-storyboard-engine、sd-qc-engine；不混合巨大根提示词；所谓 ComfyUI 文档伪载荷不可执行|
|LearnPrompt/awesome-seedance|ba0a453130ac8bdab1cf4e574cb42cefbce23942|代码/技能 MIT；编选模板 CC BY 4.0；原案例媒体权利保留。仅登记交接与模板规划，不打包案例|
|Emily2040/seedance-2.0|4668457e560eee06e95d7fcfdf441c8c0bba802e|MIT v6.7.0；仅 Seedance 专用编译规划，默认禁用执行|
|scenario-labs/skills|5429dea302ccc7edbce8ace9d5c1fb6852499540|MIT v0.59.0；disabled_requires_provider_setup，不启动 MCP/OAuth/model_run|
|pexoai/pexo-skills|f724267e45a065b6be445ea6f07312e62d3207cd|根 MIT 与 frontmatter MIT-0 差异保留；root0.3.12/agent0.3.16；服务需配置，代理执行脚本 disabled_pending_security_review|
|luoluoluo22/jianying-editor-skill|未取得|blocked_source_unavailable，多路404，不替换来源|
|Drama Skills|未取得|pending_source_confirmation，URL 待用户|

统一 scenes/shots/assets JSON；目标 provider/model/operation 选择单个模板，不混合相互冲突的镜头计数/秒数语法。参考图编号不等于文件绑定。每项候选保存 sourceRepo/sourceCommit/sourcePaths/license/adaptationVersion/inputVersionIds/modelConfigId/approvalState。配置只接收非秘密环境变量引用，禁止实际 key、日志泄漏、localStorage 保存 API key。尚无真实外部调用授权。

## 增量实现状态

已实现 backend/app/creative、model_configs/creative_candidates及快照保护迁移，前端AI创作独立页。目录API含输入/输出schema，候选记录输入版本、模型配置、来源commit、许可、适配版本和人工采用状态。配置追加保存，修改配置通过新增记录保留原配置来源。

当前已适配三个来源的精简规划方法，覆盖剧本/对白、资产提取、镜头规划、镜头提示词四类流程；不是整库导入。独立图片候选只有明确mock的元数据，无真实媒体。真实调用被服务端禁用。

源码许可证与NOTICE仅从固定commit读取并保存在docs/licenses；未安装或运行任何上游脚本。Playwright真实Chrome已验证配置、生成候选、采用、刷新历史；来源状态完整呈现在页面。

# 第 15 节新决策与当前实现差异

2026-10-23。新决策优先于此前多技能主线；当前停止功能扩展，保留已完成代码和数据。此次文档核对未修改迁移、模板、服务配置或原 SPEC。

## 精确文档合并阻塞

当前两份SPEC只到第14节，没有待替换的第15节。用户A–D原文保存于 `SPEC-SECTION15-PATCH-PENDING.md`，尚未合并。需要完整新版第15节，尤其15.3和15.6；不能把已有自拟schema或测试替代其内容。

## 当前差异

|新决策|当前代码|后续处理|
|drama-skills为主线|当前catalog仍保留Screenwriting、Visual、manju-laoli的短规则和其他来源登记；Drama项仍是原先待确认状态|冻结旧适配，不继续扩展为默认主线；待阶段2.5固定经审查来源/commit后迁移|
|固定SKILL/references及MIT文本到skills目录|尚未取得或固定zenstory-ai来源commit，没有该目录|不猜测仓库/commit，不把用户声明当作许可证审计结果|
|authoring/templates与15.3 JSON合同|当前短规则在creative/catalog.py，合同在creative/contracts.py|缺15.3原文，不能认定兼容；尚未建立指定模板体系|
|AuthoringProvider在阶段2.5|此前授权增量已有TextProvider/ImageProvider、兼容HTTP传输、创作候选服务|保留为既有基础，不称阶段2.5已完成，不继续推进该阶段|
|draft_scenes/draft_assets/plan_shots/build_prompt|当前operation为script/dialogue/assets/shots/prompt/image|尚未按新接口命名/语义迁移|
|关键帧/视频提示词分开|shots仍为prompt_text和prompt_overridden|未修改模型或迁移；留待对应阶段规划|
|连续性规则并入preflight|完整preflight、视频提交与对白实际时长链尚未实现|不提前补全视频/配音/导出或假称已验证|
|任务记录skill/commit/模板/模型|当前创作候选有来源commit、adaptationVersion、模型配置和输入快照；不是新规定Authoring任务系统|待15.3及阶段2.5规范对齐|
|15.6盲比与H3实际出片|未执行H3/ComfyUI/付费调用，也没有盲比原文|尚未验证，不进入已通过清单|

## 暂停前最后实际验证

- 后端35项通过，Ruff与mypy26源码文件通过。
- 正式PostgreSQL隔离库 `manju_phase1_verify_697f8d933f95`：迁移升/降/再升/check通过；26项API及受控HTTP测试通过，图片测试使用真实MinIO。
- 单独应用链验证：本机受控HTTP服务6次请求，文本候选、资产图片新版本及镜头关键画面采用完成，外部模型请求0。
- Chrome4项通过：嵌入工作台的候选流程、原工作台回归、真实MinIO图片预览及资产版本、双页签409。TypeScript/ESLint/build通过。
- 这些是此前授权增量的验证，不是drama-skills、真实供应商、H3或阶段2.5验收。实际供应商质量、计费与兼容性均未验证。
- 服务端实际模型调用默认关闭；没有配置真实密钥、执行上游脚本、连接ComfyUI或消费GPU/付费API。

暂停时本地还有最后两处传输校验收紧（开发白名单强制loopback、非法地址/端口返回422），本地35项测试通过；该小修尚未重新构建到运行容器。遵照最新指令，此次只记录现状，不追加部署操作。

# 阶段 2 实施计划

仅生成任务、候选与采用，不进入2.5或声音/导出阶段；15.5尾帧接力不在本轮。真实ComfyUI缺环境/工作流/执行授权时不连接，标未验证。

- 新增 providers/generation 的base、mock、comfy；domain/task_state、snapshot、workflow_mapping；services/generation；repos/generation；api/generation、events；workers/generate、reconcile。
- 迁移新增workflows、generation_tasks、candidates，镜头采用指针；任务目标shot/asset_version二选一，账号范围幂等唯一约束，候选task唯一，任务快照数据库只读保护，心跳及错误字段。
- 提交事务中冻结输入，提交成功后投递Celery；数据库queued记录作为可恢复投递来源。用户行锁串行化并发名额（queued/running合计镜头2/账号3，避免排队无限占用）；重试创建新任务，默认复制原快照。取消先终结平台任务，绝不全局interrupt其他ComfyUI任务。
- worker启动及周期维护重投queued、对账失联running；重复消息不重复执行/创建候选。mock由FFmpeg生成标注mock的图片/视频；安装仅在项目Docker镜像中。
- API实现generate/tasks/retry/cancel/candidates/adopt、资产参考图生成、SSE。重连直接补发当前状态并让前端重新查询。
- 导演同屏预览、候选条、最多2个对比、任务快照/错误、下一镜；资产详情生成/采用。旧creative候选和旧镜头API图片采用记录保留，不伪造历史任务。
- 验证：纯函数/API/类型与lint；独立PG迁移升降；隔离Redis队列、测试worker真实mock链及强杀恢复；浏览器主路径和重复/中断流程。不得强杀现有worker或删除用户卷。

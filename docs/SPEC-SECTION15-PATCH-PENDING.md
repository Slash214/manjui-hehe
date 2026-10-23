# 第 15 节修改补丁（待取得完整原节）

2026-10-23 核对：根目录 `SPEC.md` 与 `docs/SPEC.md` 均只有第 0–14 节，没有第 15 节、15.3 或 15.6。两份文件 SHA256 均为 `6e0118d86caae9149cc090d0fd991acafae8563eba427f7f2de66503254cabc2`，本次未修改。

因此尚不能执行替换第 15 节开头、替换 15.4、在 15.6 后追加的精确合并。需要完整新版第 15 节，特别是 15.3 的 JSON 合同和 15.6 的盲比规定。不得凭空补写缺失原文。

以下保存用户提供的操作及 A–D 原文。关于公开实测、许可证、成本和方案的陈述属于用户提供的决策文本，不表示本项目已独立验证；H3 对比尚未执行。AuthoringProvider 后续按阶段 2.5 安排，当前暂停扩展。

---

操作：
1. 用「改动 A」替换第 15 节开头的说明段落。
2. 用「改动 B」替换整个 15.4 小节（标题、表格、「首期不使用」段落）。
3. 在第 15.6 之后追加「改动 C」（15.7）和「改动 D」（15.8）。
4. 其余内容不变。

改动 A：
本节已定：以 **drama-skills**（zenstory-ai，MIT 许可证）为主线接入。其中故事环节有公开实测支撑；**镜头规划、关键帧、视频提示词环节尚无实测**，须经 15.6 的盲比后才能最终定案。

改动 B：
### 15.4 skill 搭配（以 drama-skills 为主线）
| 环节 | 采用的 drama-skills 子 skill | 对应接口 | 备选 |
| --- | --- | --- | --- |
| 故事：场次与台词 | short-drama-write | `draft_scenes` | 山音编剧大师 |
| 资产：拆角色、地点、道具，判断复用还是新变体 | short-drama-assets | `draft_assets` | 无 |
| 资产参考图提示词 | short-drama-image-prompts | 资产参考图生成（第 7 节） | 无 |
| 镜头规划与冻结关键帧提示词 | short-drama-storyboard | `plan_shots` | h3-storyboard-skill、Comfy-H3-Director |
| 视频提示词 | short-drama-video-prompts | `build_prompt` | minimax-h3-prompt-skill-T8（仅作写法参考） |
| 质检规则 | short-drama-review | 只借鉴检查规则，并入导出前检查（5.4），结论只作提示 | 无 |
**首期不使用：** drama-skills 中的 short-drama-produce（由本平台的生成任务取代）、short-drama-edit（由本平台的时间线与导出取代）、short-drama（总控）、short-drama-develop、short-drama-novel-analyze、short-drama-knowhow（首期不做全季规划与小说导入）；以及 infinite-creation、hardcore-director、short-drama-production 等总控或一键成片类，和打戏类 skill。

改动 C：
### 15.7 drama-skills 集成方案（已定）
**决策：** 首期把 drama-skills 当作「提示词来源」。由平台把它的创作规则改写成输出 JSON 的提示词模板，**不解析它生成的 Markdown 文档，不运行它的任何脚本**。理由：平台数据库是唯一数据源；JSON 格式稳定，上游改版不会弄坏平台。代价：享受不到上游更新，需要人工同步。
**落地步骤：**
1. **固定版本。** 把经审查的 SKILL.md 与 references 文本保存到 `skills/drama-skills@<commit>/`，附带 LICENSE 与版权声明（MIT 要求保留），commit 号写入 `DECISIONS.md`。
2. **改写模板。** 为 15.4 表中每个子 skill 建一份 `authoring/templates/<名称>.md`：保留创作规则，删去文件读写、脚本调用、付费生产相关指令，并明确要求按 15.3 的 JSON 输出。
3. **字段映射。** 见下表。
4. **提示词拆分（对第 4 节的补充）。** `shots.prompt_text` 拆为 `keyframe_prompt_text` 与 `video_prompt_text`，`prompt_overridden` 相应拆为两个布尔字段，分别记录用户是否手改过。
5. **连续性检查。** 参考它的 `creator_markdown_check.py` 的思路，用平台自己的代码并入 preflight：台词引用的镜头必须存在；承载对白的镜头预计时长不小于对白实际时长；引用的资产版本必须存在；`use_keyframe=true` 的镜头须已采用关键画面才能提交视频生成。
6. **H3 适配验证。** 它的视频提示词格式是否适用于本项目的 MiniMax H3 工作流尚未验证。阶段 2.5 中用同一镜头对比 short-drama-video-prompts 与 15.4 备选方案的提示词，以 H3 工作流的实际出片结果为准；不适配时在模板中追加 H3 写法约束。
7. **成本参考。** 它的 README 称一段 68 秒竖屏样片的视频生成成本约 40 元，这是它自带 API 方案的数字，不等于自建 ComfyUI 的成本，仅作量级参考，不进入验收。
| drama-skills 的概念 | 平台字段 |
| --- | --- |
| 剧本中的场次、对白 | `scenes`、`scene_lines` |
| 视觉设定中的人物、造型、地点、道具及状态 | `assets`、`asset_versions` |
| 资产的「新变体」 | 新建一条 `asset_versions` |
| 资产的「复用」 | 镜头引用已有 `asset_version_id` |
| 分镜中的镜头 | `shots` |
| 冻结关键帧提示词 | `shots.keyframe_prompt_text` |
| 视频提示词 | `shots.video_prompt_text` |
| 镜头时长 | `shots.est_duration_ms` |

改动 D：
### 15.8 阶段 2.5：AuthoringProvider 接入
插在阶段 2 与阶段 3 之间，不改变其他阶段编号。
**范围：** `AuthoringProvider` 接口及 mock 与 LLM 两个实现；15.4 所列子 skill 的平台模板；15.3 的结构化校验；草稿写入与界面入口（故事页「生成场次草稿」、资产页「提取资产」、导演页「生成镜头草稿」「生成提示词」）；任务记录 skill 名称与 commit。
**验收：**
- [ ] 用测试集依次走通 `draft_scenes`、`draft_assets`、`plan_shots`、`build_prompt`，结果全部为未确认的草稿，不自动覆盖已有内容。
- [ ] 结构化校验失败的输出被丢弃，界面显示「草稿不完整」及原因。
- [ ] 草稿被用户编辑并确认后，与手工创建的内容走同一套流程。
- [ ] 每次调用的 skill 名称、commit、模板版本、模型都记录在任务快照中。
- [ ] 自动化测试断言：运行期间没有执行 skill 目录下任何脚本，也没有发起 skill 触发的联网请求。
- [ ] 切换为 mock 后，整条链路仍可离线跑通。
- [ ] 完成 15.7 第 6 条的 H3 适配对比，结论写入 `DECISIONS.md`。

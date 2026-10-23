# 暗黑工作台 UI 约束

用户明确要求暗黑高级质感，导演工作区为视觉样板；业务规则以 SPEC.md 为准。

| 要求 | 实现与检查方式 |
| --- | --- |
| 不用中点分隔 | 界面文案不含 `·`，使用空白、结构或必要斜杠 |
| 减少解释 | 保留空态操作引导、保存/失败/冲突与版本后果说明；删除装饰性解释 |
| 文案精简 | 中文明确动词：新建、确认剧本、设为当前、载入最新版本 |
| Radix Colors | slate 暗色层级、gold 重点、red 错误、green 成功；CSS 无自定义十六进制颜色 |
| 对齐与圆角 | 工作区统一栏宽、内边距与标签对齐；区域圆角 7px，内部控件 4–5px |
| 0.5px 边框 | CSS 声明统一 0.5px；浏览器可能按设备像素取整，记录实际 computed style 与截图 |
| 减少动画 | 无动画与 transition；若未来必需，250ms ease-out |
| 最多四档字号 | 12/14/20/28px，最小 12px；用色阶与字重区分次序 |
| 减少决策 | 编辑自动保存；引用版本及不可逆或覆盖动作仍显式确认 |
| 圆角阴影克制 | 无装饰性 shadow；无卡片左侧彩色线条；选中用 Radix 背景和边框 |

参考：https://www.radix-ui.com/colors/docs/palette-composition/understanding-the-scale
及 https://www.radix-ui.com/colors/docs/overview/usage 。

视觉验收必须覆盖 1440×900 与 1366×768：无横向溢出，镜头编辑区可滚动，正文可读，冲突文本和按钮可见。

Ant 小范围整合：6.6.7，ConfigProvider darkAlgorithm，Radix暗色语义token，zh_CN，motion=false，按钮关闭中文自动插空格。仅Action/Alert/删除确认，保留自定义工作台。删除弹窗已实测取消/确认。AI创作页复用相同token、字号和边界；候选以可读中文内容预览，schema只在API元数据中保留。

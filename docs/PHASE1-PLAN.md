# 阶段 1 实施计划

已于实现前输出范围计划，此文件整理具体边界与交付清单。

- 文件：backend/app/{api,services,repos,models,schemas,domain,providers,workers}、backend/migrations、backend/tests；frontend/src/{api,stores,components,pages}；Dockerfile、docker-compose.yml、README.md、DECISIONS.md。
- 迁移：users、projects、episodes、scenes、scene_lines、script_versions、assets、asset_versions、files、shots、shot_lines、shot_asset_refs；UUID、时间戳、软删除、版本列、外键索引；版本表不可改写触发器；upgrade/downgrade。
- 接口：邮箱/JWT、项目/集/场次/台词 CRUD/排序、剧本确认/历史/恢复、五类资产与版本/当前版本/图片上传/签名 URL、镜头 CRUD/排序/台词绑定/固定版本引用。
- 页面：登录、项目列表、项目设置与集列表，单集四入口；故事编辑、资产详情与版本、导演镜头表单与预览空态、成片占位；固定保存状态、URL 选中恢复、800ms 保存、409 提示。
- 验证：复查矩阵纯函数、API 主链/归属/引用/冲突/版本/上传/排序、迁移升降、严格 TypeScript/ESLint/Ruff/mypy、真实浏览器双页签及刷新恢复、两种桌面尺寸截图。
- 不进入：生成、ComfyUI、配音、导出、完整复查触发/SSE，均保留后续阶段。

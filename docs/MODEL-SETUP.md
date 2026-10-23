# 文本和生图 API 配置

支持范围：OpenAI-compatible `POST {base_url}/chat/completions`（JSON对象响应）及 `POST {base_url}/images/generations`（单张 `data[0].b64_json` 或 HTTPS `data[0].url`）。不是任意供应商通用适配器，不支持 Responses、流式输出、图片编辑、参考图输入或视频API。

1. 用户在本项目 `.env` 自行设置 `MANJU_MODEL_NETWORK_ENABLED=true`，以及自选的 `MANJU_MODEL_TEXT_KEY`、`MANJU_MODEL_IMAGE_KEY`。值为自己的凭据，不提交Git，不通过聊天发送。可设置 `MANJU_MODEL_TIMEOUT_SEC=60`（1–180秒）。
2. `docker compose up -d --force-recreate api worker` 使env_file生效；这不自动调用模型。
3. 打开“模型设置”：选择文本或生图，协议OpenAI兼容，填写基础地址（如供应商文档要求的 `/v1`，不含末尾接口路径）、model和环境变量名。页面只显示配置是否就绪，不显示密钥。
4. 在本集故事、资产或导演展开对应AI区，选模型并填写要求。勾选“实际调用此模型”后点击生成。当前输入会发送给所选供应商，可能收费；系统不会自动重试。
5. 检查候选；文本可编辑保存为新的候选，旧结果保留。点击采用才更新当前内容。输入已变化返回409，需基于新输入重新生成。

图片：校验单张PNG/JPEG/WebP、20MB、最大8192边长/3200万像素，解码并去除元数据后以PNG存MinIO；预览使用时效签名。采用资产参考图会追加版本并设置为当前，旧镜头版本引用不自动改变；采用镜头关键画面只更新该镜头的独立采用指针。没有视频任务队列。

安全网络：要求HTTPS，不读取系统代理；DNS所有地址必须为公网，连接固定到已验证IP，TLS验证原域名；拒绝重定向、内网/metadata/linklocal、压缩及过大响应。输出图片URL重新独立校验，下载不携带模型认证。没有自动重试。

默认网络开关关闭，未配置明确报错，不自动转mock。测试mock只在“显示测试模型/配置”中出现。模型配置当前通过新增记录修改，旧记录保留候选来源。

## 本地受控测试（非生产）

只有模型配置勾选本地端点，且服务端 `MANJU_MODEL_DEV_AUTHORITIES=127.0.0.1:端口` 精确允许后，才可HTTP访问该loopback端点；其他私网地址仍禁止。该设置应留空于正常使用。`MANJU_MODEL_DEV_ONLY=true`可把验证进程限制为该本地白名单，禁止公网请求。图片输出URL不享受本地例外，测试服务返回base64。

当前自动测试只访问本机假HTTP服务，使用非供应商测试值；真实供应商连通/质量/计费仍未验证。真实服务可能对JSON响应模式、模型名称或图片参数有差异，需按其官方文档核实。

参考协议：[Chat API](https://developers.openai.com/api/reference/resources/chat)、[Images API](https://developers.openai.com/api/reference/resources/images)。

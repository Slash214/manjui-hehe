# MinIO 本项目构建

原 Docker Hub 与 Quay 的固定预构建镜像均不可用。根据官方发布说明，在本项目 Docker 构建阶段编译官方源码版本 RELEASE.2025-10-15T17-29-55Z（含官方列出的安全修复）。不安装宿主机 Go，不使用第三方 MinIO 镜像。

来源：https://github.com/minio/minio/releases/tag/RELEASE.2025-10-15T17-29-55Z

官方源码为 AGPLv3，镜像保留原 LICENSE；没有修改 MinIO 源码。首次构建需要下载 Go 模块，Go 模块校验机制保持开启。此版本控制台能力可能与早期发行版不同，本平台资产访问通过 S3 API 完成。

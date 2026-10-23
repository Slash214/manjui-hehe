# Official MinIO security release; public prebuilt legacy images are no longer available.
FROM golang:1.24.8-bookworm AS build
ENV CGO_ENABLED=0 GOBIN=/out GOMAXPROCS=2
RUN go install github.com/minio/minio@RELEASE.2025-10-15T17-29-55Z \
    && cp /go/pkg/mod/github.com/minio/minio@*/LICENSE /out/LICENSE
FROM debian:bookworm-slim
COPY --from=build /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt
COPY --from=build /out/minio /usr/local/bin/minio
COPY --from=build /out/LICENSE /usr/share/doc/minio/LICENSE
EXPOSE 9000 9001
ENTRYPOINT ["minio"]

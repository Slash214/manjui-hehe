from typing import Protocol

import boto3
from botocore.client import Config

from app.config import settings


class StorageProvider(Protocol):
    def put(self, key: str, content: bytes, mime: str) -> None: ...
    def url(self, key: str) -> str: ...
    def get(self, key: str) -> bytes: ...


class MinioStorage:
    def __init__(self) -> None:
        options = {
            "aws_access_key_id": settings.s3_access_key,
            "aws_secret_access_key": settings.s3_secret_key,
            "region_name": "us-east-1",
            "config": Config(signature_version="s3v4"),
        }
        self.client = boto3.client("s3", endpoint_url=settings.s3_endpoint, **options)
        self.public = boto3.client("s3", endpoint_url=settings.s3_public_endpoint, **options)

    def put(self, key: str, content: bytes, mime: str) -> None:
        self.client.put_object(Bucket=settings.s3_bucket, Key=key, Body=content, ContentType=mime)

    def get(self, key: str) -> bytes:
        response = self.client.get_object(Bucket=settings.s3_bucket, Key=key)
        try:
            return bytes(response["Body"].read())
        finally:
            response["Body"].close()

    def url(self, key: str) -> str:
        return str(
            self.public.generate_presigned_url(
                "get_object", Params={"Bucket": settings.s3_bucket, "Key": key}, ExpiresIn=3600
            )
        )


class MockStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put(self, key: str, content: bytes, mime: str) -> None:
        self.objects[key] = content

    def get(self, key: str) -> bytes:
        return self.objects[key]

    def url(self, key: str) -> str:
        return "https://mock.invalid/" + key


def storage() -> StorageProvider:
    return MinioStorage()

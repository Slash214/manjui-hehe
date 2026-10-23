import time

from app.config import settings
from app.providers.storage import MinioStorage

store = MinioStorage()
for attempt in range(30):
    try:
        buckets = store.client.list_buckets()["Buckets"]
        if not any(x["Name"] == settings.s3_bucket for x in buckets):
            store.client.create_bucket(Bucket=settings.s3_bucket)
        break
    except Exception:
        if attempt == 29:
            raise
        time.sleep(2)

"""Run inside this project's API container. Never migrate the application database backwards."""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from uuid import uuid4

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

from app.config import settings
from app.providers.storage import MinioStorage


def main() -> None:
    app_url = make_url(settings.database_url)
    if app_url.get_backend_name() != "postgresql":
        raise RuntimeError("PostgreSQL required for infrastructure verification")
    name = "manju_phase1_verify_" + uuid4().hex[:12]
    admin = create_engine(app_url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{name}"'))
    test_url = app_url.set(database=name).render_as_string(hide_password=False)
    env = {**os.environ, "DATABASE_URL": test_url, "TEST_DATABASE_URL": test_url}
    for command in ("upgrade head", "downgrade base", "upgrade head", "check"):
        result = subprocess.run([sys.executable, "-m", "alembic", *command.split()], env=env,
                                capture_output=True, text=True, check=False)
        if result.returncode:
            raise RuntimeError(f"Isolated migration {command} failed: {result.stderr[-2000:]}")
    engine = create_engine(test_url)
    with engine.connect() as connection:
        triggers = connection.execute(text("SELECT trigger_name FROM information_schema.triggers "
                                            "WHERE event_object_table IN ('asset_versions','script_versions')")).all()
        assert len(triggers) == 4  # PostgreSQL lists UPDATE and DELETE separately.
        guards = connection.execute(text("SELECT trigger_name FROM information_schema.triggers "
                                         "WHERE event_object_table = 'creative_candidates'")).all()
        assert len(guards) == 2
        assert len(inspect(connection).get_table_names()) == 16
    engine.dispose()
    # API suite builds its own isolated metadata. Reset ONLY this newly created database first.
    subprocess.run([sys.executable, "-m", "alembic", "downgrade", "base"], env=env, check=True)
    result = subprocess.run([sys.executable, "-m", "pytest", "tests/test_api.py", "tests/test_creative.py", "tests/test_creative_network.py", "-q"], env=env,
                            capture_output=True, text=True, check=False)
    print(result.stdout)
    if result.returncode:
        raise RuntimeError("PostgreSQL API suite failed")
    store = MinioStorage()
    key = "phase1-verification/" + uuid4().hex
    content = b"phase-one-storage-verification"
    store.put(key, content, "text/plain")
    short_url = store.client.generate_presigned_url("get_object", Params={
        "Bucket": settings.s3_bucket, "Key": key}, ExpiresIn=1)
    assert urllib.request.urlopen(short_url, timeout=10).read() == content
    time.sleep(2)
    try:
        urllib.request.urlopen(short_url, timeout=10)
        raise AssertionError("Expired URL remained readable")
    except urllib.error.HTTPError as error:
        assert error.code == 403
    print(json.dumps({"database": name, "application_database_untouched": True,
                      "postgres_migrations": "upgrade/downgrade/upgrade/check passed",
                      "postgres_api_and_creative_tests": "see pytest result above", "minio_signed_read": "passed",
                      "minio_expired_signature": "403 after 1-second expiry"}))


if __name__ == "__main__":
    main()

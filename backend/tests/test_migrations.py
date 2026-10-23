import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest


def test_migration_upgrade_immutable_and_downgrade(tmp_path: Path) -> None:
    target = tmp_path / "migration.db"
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{target.as_posix()}"}
    backend = Path(__file__).resolve().parents[1]

    def migrate(*arguments: str) -> None:
        subprocess.run(
            [sys.executable, "-m", "alembic", *arguments],
            cwd=backend,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )

    migrate("upgrade", "head")
    with sqlite3.connect(target) as connection:
        tables = {x[0] for x in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"users", "shots", "asset_versions", "script_versions"} <= tables
        # SQLite FK checks are off for this isolated raw trigger probe; application connections enable them.
        connection.execute("""INSERT INTO asset_versions
            (id, asset_id, version_no, description, prompt, params_json, voice_config_json, created_at, updated_at)
            VALUES ('version', 'asset', 1, 'original', '', '{}', '{}', '2026-10-23', '2026-10-23')""")
        with pytest.raises(sqlite3.IntegrityError, match="immutable version"):
            connection.execute("UPDATE asset_versions SET description='changed'")
        with pytest.raises(sqlite3.IntegrityError, match="immutable version"):
            connection.execute("DELETE FROM asset_versions")
        connection.execute("""INSERT INTO creative_candidates
            (id,episode_id,model_config_id,operation,input_json,output_json,provenance_json,approval_state,version,created_at,updated_at)
            VALUES ('candidate','episode','config','script','{}','{}','{}','pending',1,'2026-10-23','2026-10-23')""")
        connection.execute("UPDATE creative_candidates SET approval_state='adopted',version=2")
        with pytest.raises(sqlite3.IntegrityError, match="immutable creative snapshot"):
            connection.execute("UPDATE creative_candidates SET output_json='{}'")
        with pytest.raises(sqlite3.IntegrityError, match="immutable creative snapshot"):
            connection.execute("DELETE FROM creative_candidates")
    migrate("downgrade", "base")
    with sqlite3.connect(target) as connection:
        tables = {x[0] for x in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert tables == {"alembic_version"}
    migrate("upgrade", "head")
    migrate("check")

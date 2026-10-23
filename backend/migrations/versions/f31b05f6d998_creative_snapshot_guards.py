"""protect creative candidate snapshots"""
from alembic import op
revision = 'f31b05f6d998'
down_revision = 'ec89def09c1b'
branch_labels = None
depends_on = None

def upgrade():
    if op.get_bind().dialect.name == 'postgresql':
        op.execute("""CREATE FUNCTION protect_creative_snapshot() RETURNS trigger AS $$
        BEGIN
          IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'immutable creative snapshot'; END IF;
          IF NEW.input_json::text <> OLD.input_json::text OR NEW.output_json::text <> OLD.output_json::text
            OR NEW.provenance_json::text <> OLD.provenance_json::text OR NEW.operation <> OLD.operation
            OR NEW.episode_id <> OLD.episode_id OR NEW.model_config_id <> OLD.model_config_id
          THEN RAISE EXCEPTION 'immutable creative snapshot'; END IF;
          RETURN NEW;
        END; $$ LANGUAGE plpgsql""")
        op.execute('CREATE TRIGGER creative_snapshot_guard BEFORE UPDATE OR DELETE ON creative_candidates FOR EACH ROW EXECUTE FUNCTION protect_creative_snapshot()')
    else:
        op.execute("CREATE TRIGGER creative_snapshot_update BEFORE UPDATE OF input_json, output_json, provenance_json, operation, episode_id, model_config_id ON creative_candidates BEGIN SELECT RAISE(ABORT, 'immutable creative snapshot'); END")
        op.execute("CREATE TRIGGER creative_snapshot_delete BEFORE DELETE ON creative_candidates BEGIN SELECT RAISE(ABORT, 'immutable creative snapshot'); END")

def downgrade():
    if op.get_bind().dialect.name == 'postgresql':
        op.execute('DROP TRIGGER creative_snapshot_guard ON creative_candidates')
        op.execute('DROP FUNCTION protect_creative_snapshot()')
    else:
        op.execute('DROP TRIGGER creative_snapshot_update')
        op.execute('DROP TRIGGER creative_snapshot_delete')

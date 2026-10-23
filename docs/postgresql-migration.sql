BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> c66caa56dd82

CREATE TABLE users (
    email VARCHAR(254) NOT NULL, 
    password_hash TEXT NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (email)
);

CREATE TABLE projects (
    owner_id VARCHAR(36) NOT NULL, 
    name VARCHAR(200) NOT NULL, 
    description TEXT NOT NULL, 
    style_prompt TEXT NOT NULL, 
    aspect_ratio VARCHAR NOT NULL, 
    resolution VARCHAR NOT NULL, 
    fps INTEGER NOT NULL, 
    production_type VARCHAR NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    version INTEGER NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(owner_id) REFERENCES users (id)
);

CREATE INDEX ix_projects_owner_id ON projects (owner_id);

CREATE TABLE assets (
    project_id VARCHAR(36) NOT NULL, 
    asset_type VARCHAR NOT NULL, 
    name VARCHAR(200) NOT NULL, 
    parent_asset_id VARCHAR(36), 
    current_version_id VARCHAR(36), 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    version INTEGER NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(parent_asset_id) REFERENCES assets (id), 
    FOREIGN KEY(project_id) REFERENCES projects (id)
);

CREATE INDEX ix_assets_current_version_id ON assets (current_version_id);

CREATE INDEX ix_assets_parent_asset_id ON assets (parent_asset_id);

CREATE INDEX ix_assets_project_id ON assets (project_id);

CREATE TABLE episodes (
    project_id VARCHAR(36) NOT NULL, 
    episode_no INTEGER NOT NULL, 
    title VARCHAR(200) NOT NULL, 
    target_duration_sec INTEGER NOT NULL, 
    confirmed_script_version_id VARCHAR(36), 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    version INTEGER NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(project_id) REFERENCES projects (id)
);

CREATE INDEX ix_episodes_confirmed_script_version_id ON episodes (confirmed_script_version_id);

CREATE INDEX ix_episodes_project_id ON episodes (project_id);

CREATE TABLE files (
    project_id VARCHAR(36) NOT NULL, 
    storage_key VARCHAR NOT NULL, 
    mime VARCHAR NOT NULL, 
    size_bytes INTEGER NOT NULL, 
    sha256 VARCHAR NOT NULL, 
    width INTEGER, 
    height INTEGER, 
    duration_ms INTEGER, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(project_id) REFERENCES projects (id), 
    UNIQUE (storage_key)
);

CREATE INDEX ix_files_project_id ON files (project_id);

CREATE TABLE asset_versions (
    asset_id VARCHAR(36) NOT NULL, 
    version_no INTEGER NOT NULL, 
    description TEXT NOT NULL, 
    prompt TEXT NOT NULL, 
    params_json JSON NOT NULL, 
    reference_file_id VARCHAR(36), 
    voice_config_json JSON NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(asset_id) REFERENCES assets (id), 
    FOREIGN KEY(reference_file_id) REFERENCES files (id), 
    UNIQUE (asset_id, version_no)
);

CREATE INDEX ix_asset_versions_asset_id ON asset_versions (asset_id);

CREATE INDEX ix_asset_versions_reference_file_id ON asset_versions (reference_file_id);

CREATE TABLE scenes (
    episode_id VARCHAR(36) NOT NULL, 
    order_no INTEGER NOT NULL, 
    time_of_day VARCHAR NOT NULL, 
    location_asset_id VARCHAR(36), 
    title VARCHAR NOT NULL, 
    summary TEXT NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    version INTEGER NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(episode_id) REFERENCES episodes (id), 
    FOREIGN KEY(location_asset_id) REFERENCES assets (id)
);

CREATE INDEX ix_scenes_episode_id ON scenes (episode_id);

CREATE INDEX ix_scenes_location_asset_id ON scenes (location_asset_id);

CREATE TABLE script_versions (
    episode_id VARCHAR(36) NOT NULL, 
    version_no INTEGER NOT NULL, 
    snapshot_json JSON NOT NULL, 
    note TEXT NOT NULL, 
    confirmed_by VARCHAR(36) NOT NULL, 
    confirmed_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(confirmed_by) REFERENCES users (id), 
    FOREIGN KEY(episode_id) REFERENCES episodes (id), 
    UNIQUE (episode_id, version_no)
);

CREATE INDEX ix_script_versions_confirmed_by ON script_versions (confirmed_by);

CREATE INDEX ix_script_versions_episode_id ON script_versions (episode_id);

CREATE TABLE scene_lines (
    scene_id VARCHAR(36) NOT NULL, 
    order_no INTEGER NOT NULL, 
    line_type VARCHAR NOT NULL, 
    character_asset_id VARCHAR(36), 
    text TEXT NOT NULL, 
    edited_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    version INTEGER NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(character_asset_id) REFERENCES assets (id), 
    FOREIGN KEY(scene_id) REFERENCES scenes (id)
);

CREATE INDEX ix_scene_lines_character_asset_id ON scene_lines (character_asset_id);

CREATE INDEX ix_scene_lines_scene_id ON scene_lines (scene_id);

CREATE TABLE shots (
    episode_id VARCHAR(36) NOT NULL, 
    scene_id VARCHAR(36), 
    order_no INTEGER NOT NULL, 
    action_desc TEXT NOT NULL, 
    shot_size VARCHAR NOT NULL, 
    camera_angle VARCHAR NOT NULL, 
    camera_movement VARCHAR NOT NULL, 
    blocking_desc TEXT NOT NULL, 
    est_duration_ms INTEGER NOT NULL, 
    use_keyframe BOOLEAN NOT NULL, 
    dialogue_source VARCHAR NOT NULL, 
    sfx_note TEXT NOT NULL, 
    prompt_text TEXT NOT NULL, 
    prompt_overridden BOOLEAN NOT NULL, 
    params_json JSON NOT NULL, 
    content_version INTEGER NOT NULL, 
    review_status VARCHAR NOT NULL, 
    review_reasons_json JSON NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    version INTEGER NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(episode_id) REFERENCES episodes (id), 
    FOREIGN KEY(scene_id) REFERENCES scenes (id)
);

CREATE INDEX ix_shots_episode_id ON shots (episode_id);

CREATE INDEX ix_shots_scene_id ON shots (scene_id);

CREATE TABLE shot_asset_refs (
    shot_id VARCHAR(36) NOT NULL, 
    asset_version_id VARCHAR(36) NOT NULL, 
    role VARCHAR NOT NULL, 
    order_no INTEGER NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(asset_version_id) REFERENCES asset_versions (id), 
    FOREIGN KEY(shot_id) REFERENCES shots (id)
);

CREATE INDEX ix_shot_asset_refs_asset_version_id ON shot_asset_refs (asset_version_id);

CREATE INDEX ix_shot_asset_refs_shot_id ON shot_asset_refs (shot_id);

CREATE TABLE shot_lines (
    shot_id VARCHAR(36) NOT NULL, 
    line_id VARCHAR(36) NOT NULL, 
    order_no INTEGER NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(line_id) REFERENCES scene_lines (id), 
    FOREIGN KEY(shot_id) REFERENCES shots (id), 
    UNIQUE (shot_id, line_id)
);

CREATE INDEX ix_shot_lines_line_id ON shot_lines (line_id);

CREATE INDEX ix_shot_lines_shot_id ON shot_lines (shot_id);

ALTER TABLE assets ADD CONSTRAINT fk_asset_current FOREIGN KEY(current_version_id) REFERENCES asset_versions (id);

ALTER TABLE episodes ADD CONSTRAINT fk_episode_confirmed FOREIGN KEY(confirmed_script_version_id) REFERENCES script_versions (id);

CREATE FUNCTION reject_version_mutation() RETURNS trigger AS $$
            BEGIN RAISE EXCEPTION 'immutable version'; END; $$ LANGUAGE plpgsql;

CREATE TRIGGER immutable_script_versions BEFORE UPDATE OR DELETE ON script_versions FOR EACH ROW EXECUTE FUNCTION reject_version_mutation();

CREATE TRIGGER immutable_asset_versions BEFORE UPDATE OR DELETE ON asset_versions FOR EACH ROW EXECUTE FUNCTION reject_version_mutation();

INSERT INTO alembic_version (version_num) VALUES ('c66caa56dd82') RETURNING alembic_version.version_num;

COMMIT;


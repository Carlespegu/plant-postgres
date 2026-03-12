BEGIN;

-- =========================================================
-- 1) USERS
-- =========================================================

CREATE TABLE IF NOT EXISTS users (
    id              BIGSERIAL PRIMARY KEY,
    username        VARCHAR(100) NOT NULL UNIQUE,
    email           VARCHAR(255) NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =========================================================
-- 2) MASTER TABLES
-- =========================================================

CREATE TABLE IF NOT EXISTS installation_statuses (
    id              SMALLSERIAL PRIMARY KEY,
    code            VARCHAR(50) NOT NULL UNIQUE,
    name            VARCHAR(100) NOT NULL UNIQUE,
    description     TEXT
);

CREATE TABLE IF NOT EXISTS group_statuses (
    id              SMALLSERIAL PRIMARY KEY,
    code            VARCHAR(50) NOT NULL UNIQUE,
    name            VARCHAR(100) NOT NULL UNIQUE,
    description     TEXT
);

CREATE TABLE IF NOT EXISTS asset_types (
    id              SMALLSERIAL PRIMARY KEY,
    code            VARCHAR(50) NOT NULL UNIQUE,
    name            VARCHAR(100) NOT NULL UNIQUE,
    description     TEXT
);

CREATE TABLE IF NOT EXISTS asset_statuses (
    id              SMALLSERIAL PRIMARY KEY,
    code            VARCHAR(50) NOT NULL UNIQUE,
    name            VARCHAR(100) NOT NULL UNIQUE,
    description     TEXT
);

CREATE TABLE IF NOT EXISTS relation_types (
    id              SMALLSERIAL PRIMARY KEY,
    code            VARCHAR(50) NOT NULL UNIQUE,
    name            VARCHAR(100) NOT NULL UNIQUE,
    description     TEXT
);

-- =========================================================
-- 3) INSTALLATIONS
-- =========================================================

CREATE TABLE IF NOT EXISTS installations (
    id                  BIGSERIAL PRIMARY KEY,
    user_id             BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status_id           SMALLINT NOT NULL REFERENCES installation_statuses(id),
    name                VARCHAR(150) NOT NULL,
    description         TEXT,
    location_name       VARCHAR(255),
    address_line        VARCHAR(255),
    city                VARCHAR(120),
    region              VARCHAR(120),
    country             VARCHAR(120),
    postal_code         VARCHAR(30),
    latitude            NUMERIC(9,6),
    longitude           NUMERIC(9,6),
    altitude_m          NUMERIC(8,2),
    timezone            VARCHAR(100),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_installations_latitude
        CHECK (latitude IS NULL OR (latitude >= -90 AND latitude <= 90)),
    CONSTRAINT chk_installations_longitude
        CHECK (longitude IS NULL OR (longitude >= -180 AND longitude <= 180))
);

CREATE INDEX IF NOT EXISTS idx_installations_user_id
    ON installations(user_id);

CREATE INDEX IF NOT EXISTS idx_installations_status_id
    ON installations(status_id);

-- =========================================================
-- 4) INSTALLATION GROUPS
-- =========================================================

CREATE TABLE IF NOT EXISTS installation_groups (
    id                  BIGSERIAL PRIMARY KEY,
    installation_id     BIGINT NOT NULL REFERENCES installations(id) ON DELETE CASCADE,
    status_id           SMALLINT REFERENCES group_statuses(id),
    name                VARCHAR(150) NOT NULL,
    description         TEXT,
    sort_order          INTEGER,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (installation_id, name)
);

CREATE INDEX IF NOT EXISTS idx_installation_groups_installation_id
    ON installation_groups(installation_id);

CREATE INDEX IF NOT EXISTS idx_installation_groups_status_id
    ON installation_groups(status_id);

-- =========================================================
-- 5) ASSETS
-- =========================================================

CREATE TABLE IF NOT EXISTS assets (
    id                      BIGSERIAL PRIMARY KEY,
    external_id             VARCHAR(120) NOT NULL UNIQUE,
    name                    VARCHAR(150) NOT NULL,
    asset_type_id           SMALLINT NOT NULL REFERENCES asset_types(id),
    status_id               SMALLINT NOT NULL REFERENCES asset_statuses(id),
    installation_id         BIGINT NOT NULL REFERENCES installations(id) ON DELETE CASCADE,
    installation_group_id   BIGINT REFERENCES installation_groups(id) ON DELETE SET NULL,
    parent_asset_id         BIGINT REFERENCES assets(id) ON DELETE SET NULL,
    serial_number           VARCHAR(120),
    manufacturer            VARCHAR(120),
    model                   VARCHAR(120),
    firmware_version        VARCHAR(80),
    description             TEXT,
    notes                   TEXT,
    latitude                NUMERIC(9,6),
    longitude               NUMERIC(9,6),
    altitude_m              NUMERIC(8,2),
    installed_at            TIMESTAMPTZ,
    last_seen_at            TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_assets_latitude
        CHECK (latitude IS NULL OR (latitude >= -90 AND latitude <= 90)),
    CONSTRAINT chk_assets_longitude
        CHECK (longitude IS NULL OR (longitude >= -180 AND longitude <= 180))
);

CREATE INDEX IF NOT EXISTS idx_assets_installation_id
    ON assets(installation_id);

CREATE INDEX IF NOT EXISTS idx_assets_installation_group_id
    ON assets(installation_group_id);

CREATE INDEX IF NOT EXISTS idx_assets_parent_asset_id
    ON assets(parent_asset_id);

CREATE INDEX IF NOT EXISTS idx_assets_asset_type_id
    ON assets(asset_type_id);

CREATE INDEX IF NOT EXISTS idx_assets_status_id
    ON assets(status_id);

-- =========================================================
-- 6) ASSET RELATIONS
-- =========================================================

CREATE TABLE IF NOT EXISTS asset_relations (
    id                  BIGSERIAL PRIMARY KEY,
    source_asset_id     BIGINT NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    target_asset_id     BIGINT NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    relation_type_id    SMALLINT NOT NULL REFERENCES relation_types(id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (source_asset_id, target_asset_id, relation_type_id),
    CONSTRAINT chk_asset_relations_source_target_diff
        CHECK (source_asset_id <> target_asset_id)
);

CREATE INDEX IF NOT EXISTS idx_asset_relations_source_asset_id
    ON asset_relations(source_asset_id);

CREATE INDEX IF NOT EXISTS idx_asset_relations_target_asset_id
    ON asset_relations(target_asset_id);

CREATE INDEX IF NOT EXISTS idx_asset_relations_relation_type_id
    ON asset_relations(relation_type_id);

-- =========================================================
-- 7) READINGS
-- =========================================================

CREATE TABLE IF NOT EXISTS readings (
    id              BIGSERIAL PRIMARY KEY,
    asset_id        BIGINT NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    ts              TIMESTAMPTZ NOT NULL,
    temp_c          NUMERIC(6,2),
    hum_air         NUMERIC(6,2),
    ldr_raw         INTEGER,
    soil_percent    NUMERIC(6,2),
    rain            VARCHAR(50),
    rssi            INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_readings_asset_id
    ON readings(asset_id);

CREATE INDEX IF NOT EXISTS idx_readings_asset_id_ts
    ON readings(asset_id, ts DESC);

-- =========================================================
-- 8) SEED DATA
-- =========================================================

INSERT INTO installation_statuses (code, name, description)
VALUES
    ('active', 'Active', 'Installation is active'),
    ('inactive', 'Inactive', 'Installation is inactive'),
    ('maintenance', 'Maintenance', 'Installation under maintenance'),
    ('retired', 'Retired', 'Installation no longer in use')
ON CONFLICT (code) DO NOTHING;

INSERT INTO group_statuses (code, name, description)
VALUES
    ('active', 'Active', 'Group is active'),
    ('inactive', 'Inactive', 'Group is inactive'),
    ('maintenance', 'Maintenance', 'Group under maintenance')
ON CONFLICT (code) DO NOTHING;

INSERT INTO asset_types (code, name, description)
VALUES
    ('controller', 'Controller', 'Main controller device'),
    ('sensor', 'Sensor', 'Sensor device'),
    ('actuator', 'Actuator', 'Actuator device'),
    ('gateway', 'Gateway', 'Gateway or communication node'),
    ('transmitter', 'Transmitter', 'Transmission module'),
    ('receiver', 'Receiver', 'Receiver module'),
    ('power_module', 'Power Module', 'Power supply or battery module')
ON CONFLICT (code) DO NOTHING;

INSERT INTO asset_statuses (code, name, description)
VALUES
    ('active', 'Active', 'Asset is active'),
    ('inactive', 'Inactive', 'Asset is inactive'),
    ('maintenance', 'Maintenance', 'Asset is under maintenance'),
    ('failed', 'Failed', 'Asset has failed'),
    ('retired', 'Retired', 'Asset retired')
ON CONFLICT (code) DO NOTHING;

INSERT INTO relation_types (code, name, description)
VALUES
    ('reads_from', 'Reads From', 'Source reads data from target'),
    ('controls', 'Controls', 'Source controls target'),
    ('connected_to', 'Connected To', 'Assets are physically or logically connected'),
    ('powered_by', 'Powered By', 'Source is powered by target'),
    ('mounted_on', 'Mounted On', 'Source is mounted on target'),
    ('contains', 'Contains', 'Source contains target')
ON CONFLICT (code) DO NOTHING;

COMMIT;
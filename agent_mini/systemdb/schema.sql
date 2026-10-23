-- S17 system database schema (MySQL 8, idempotent)
CREATE TABLE IF NOT EXISTS sessions (
    session_id VARCHAR(128) NOT NULL PRIMARY KEY,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    created_at DATETIME(6) NOT NULL,
    last_active_at DATETIME(6) NOT NULL,
    message_count INT NOT NULL DEFAULT 0,
    meta JSON NULL,
    KEY idx_sessions_status_active (status, last_active_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS models (
    id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    provider VARCHAR(64) NOT NULL,
    base_url VARCHAR(512) NOT NULL,
    model VARCHAR(128) NOT NULL,
    max_context_tokens INT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME(6) NOT NULL,
    updated_at DATETIME(6) NOT NULL,
    UNIQUE KEY uq_models_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS tools (
    id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    version VARCHAR(64) NOT NULL,
    description TEXT NOT NULL,
    params_schema JSON NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME(6) NOT NULL,
    updated_at DATETIME(6) NOT NULL,
    UNIQUE KEY uq_tools_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS tool_invocations (
    id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(128) NOT NULL,
    trace_id VARCHAR(64) NOT NULL,
    tool_name VARCHAR(128) NOT NULL,
    ok BOOLEAN NOT NULL,
    error_code VARCHAR(64) NULL,
    duration_ms INT NOT NULL DEFAULT 0,
    created_at DATETIME(6) NOT NULL,
    KEY idx_tool_invocations_session_time (session_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS request_metrics (
    id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    trace_id VARCHAR(64) NOT NULL,
    session_id VARCHAR(128) NOT NULL,
    steps INT NOT NULL,
    tool_calls INT NOT NULL,
    prompt_tokens INT NOT NULL,
    completion_tokens INT NOT NULL,
    duration_ms INT NOT NULL DEFAULT 0,
    created_at DATETIME(6) NOT NULL,
    KEY idx_request_metrics_session_time (session_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

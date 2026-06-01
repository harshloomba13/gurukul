CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS project_context (
  id INTEGER PRIMARY KEY,
  topic TEXT NOT NULL,
  summary TEXT NOT NULL
);

INSERT INTO project_context (id, topic, summary) VALUES
  (1, 'runtime-boundary', 'OpenClaw is the outer agent runtime and SpiceAI is the backend for query, retrieval, and AI capabilities.'),
  (2, 'deployment', 'OpenClaw should run in Docker while SpiceAI can run on the host during the first iteration.'),
  (3, 'future-channel', 'Slack is a later transport layer and should not change the core OpenClaw to SpiceAI flow.')
ON CONFLICT (id) DO UPDATE
SET topic = EXCLUDED.topic,
    summary = EXCLUDED.summary;

CREATE TABLE IF NOT EXISTS integration_targets (
  id INTEGER PRIMARY KEY,
  service_name TEXT NOT NULL UNIQUE,
  base_url TEXT NOT NULL,
  notes TEXT NOT NULL
);

INSERT INTO integration_targets (id, service_name, base_url, notes) VALUES
  (1, 'spiceai-host', 'http://localhost:8090', 'Use this from the host when validating SpiceAI directly.'),
  (2, 'spiceai-from-openclaw-docker', 'http://host.docker.internal:8090', 'Use this from OpenClaw running inside Docker.'),
  (3, 'postgres', 'postgresql://postgres:postgres@localhost:5432/spiceai', 'Backing infrastructure for SpiceAI datasets and future vector workloads.')
ON CONFLICT (id) DO UPDATE
SET service_name = EXCLUDED.service_name,
    base_url = EXCLUDED.base_url,
    notes = EXCLUDED.notes;

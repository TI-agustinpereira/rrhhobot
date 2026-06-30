-- schema.sql

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documentos (
    id SERIAL PRIMARY KEY,
    texto TEXT NOT NULL,
    embedding VECTOR(1536) NOT NULL, -- pongo 1536 pq es la dim de text-embedding-3-small
    metadata JSONB DEFAULT '{}',
    creado_en TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS documentos_embedding_idx
    ON documentos 
    USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS documentos_metadata_idx
    ON documentos USING gin (metadata);

CREATE INDEX IF NOT EXISTS clausula_id_idx 
    ON documentos ((metadata->>'clausula_id'));
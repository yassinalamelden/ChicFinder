-- supabase/migrations/001_initial_schema.sql

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Products table
CREATE TABLE IF NOT EXISTS products (
    id BIGSERIAL PRIMARY KEY,
    product_id TEXT UNIQUE NOT NULL,
    title TEXT,
    brand TEXT,
    category TEXT,
    price DECIMAL(10,2),
    product_url TEXT,
    description TEXT,
    availability TEXT DEFAULT 'InStock',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_products_brand ON products(brand);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);

-- Embeddings table (one row per image, holds FashionCLIP 512-d vector)
CREATE TABLE IF NOT EXISTS embeddings (
    id BIGSERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    image_filename TEXT NOT NULL,   -- e.g. "tomato_9215097798909_0"
    embedding vector(512),
    UNIQUE(product_id, image_filename)
);

-- IVFFlat index for approximate cosine similarity search
-- (lists=100 is appropriate for ~1000 vectors; increase for larger datasets)
CREATE INDEX IF NOT EXISTS idx_embeddings_vector
    ON embeddings USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- RPC function called by the Python backend for similarity search
CREATE OR REPLACE FUNCTION match_embeddings(
    query_embedding vector(512),
    match_count int DEFAULT 50
)
RETURNS TABLE (
    image_filename  text,
    product_id_str  text,
    db_product_id   bigint,
    title           text,
    brand           text,
    category        text,
    price           decimal,
    product_url     text,
    similarity      float
)
LANGUAGE sql STABLE
AS $$
    SELECT
        e.image_filename,
        p.product_id   AS product_id_str,
        p.id           AS db_product_id,
        p.title,
        p.brand,
        p.category,
        p.price,
        p.product_url,
        1 - (e.embedding <=> query_embedding) AS similarity
    FROM embeddings e
    JOIN products p ON e.product_id = p.id
    ORDER BY e.embedding <=> query_embedding
    LIMIT match_count;
$$;

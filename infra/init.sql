-- Enable vector search (embeddings)
CREATE EXTENSION IF NOT EXISTS vector;

-- Warehouse layers
CREATE SCHEMA IF NOT EXISTS raw;       -- data exactly as it arrives
CREATE SCHEMA IF NOT EXISTS staging;   -- cleaned data
CREATE SCHEMA IF NOT EXISTS marts;     -- business-ready tables (sales, finance)
CREATE SCHEMA IF NOT EXISTS rag;       -- documents + embeddings
CREATE SCHEMA IF NOT EXISTS audit;     -- logs of every question asked
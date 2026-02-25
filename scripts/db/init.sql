-- scripts/db/init.sql
-- Executed automatically by PostgreSQL container on first run

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";      -- Trigram index for fuzzy search
CREATE EXTENSION IF NOT EXISTS "unaccent";      -- Accent-insensitive search (critical for Spanish)

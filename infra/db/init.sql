CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS movies (
  id BIGINT PRIMARY KEY,
  title TEXT,
  vote_average DOUBLE PRECISION,
  vote_count BIGINT,
  status TEXT,
  release_date DATE,
  revenue BIGINT,
  runtime INT,
  adult BOOLEAN,
  backdrop_path TEXT,
  budget BIGINT,
  homepage TEXT,
  imdb_id TEXT,
  original_language TEXT,
  original_title TEXT,
  overview TEXT,
  popularity DOUBLE PRECISION,
  poster_path TEXT,
  tagline TEXT,
  genres TEXT,
  production_companies TEXT,
  production_countries TEXT,
  spoken_languages TEXT,
  keywords TEXT
);

-- NOTE: embedding dimension must match your embedding model output.
-- Default is 1024 to fit Titan v2. If you use a different model, change it here.
CREATE TABLE IF NOT EXISTS movie_embeddings (
  movie_id BIGINT PRIMARY KEY REFERENCES movies(id) ON DELETE CASCADE,
  embedding vector(1024) NOT NULL,
  embedding_model TEXT NOT NULL,
  doc_hash TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_movies_language ON movies(original_language);
CREATE INDEX IF NOT EXISTS idx_movies_adult ON movies(adult);
CREATE INDEX IF NOT EXISTS idx_movies_release_date ON movies(release_date);

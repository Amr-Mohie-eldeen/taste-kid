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
-- Update this if you change the embedding model dimension.
CREATE TABLE IF NOT EXISTS movie_embeddings (
  movie_id BIGINT PRIMARY KEY REFERENCES movies(id) ON DELETE CASCADE,
  embedding vector(768) NOT NULL,
  embedding_model TEXT NOT NULL,
  doc_hash TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_movie_embeddings_embedding_hnsw_cosine
  ON movie_embeddings
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS idx_movies_language ON movies(original_language);
CREATE INDEX IF NOT EXISTS idx_movies_adult ON movies(adult);
CREATE INDEX IF NOT EXISTS idx_movies_release_date ON movies(release_date);

CREATE TABLE IF NOT EXISTS users (
  id BIGSERIAL PRIMARY KEY,
  display_name TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS user_movie_ratings (
  user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  movie_id BIGINT NOT NULL REFERENCES movies(id) ON DELETE CASCADE,
  rating INT,
  status TEXT NOT NULL DEFAULT 'watched',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, movie_id),
  CHECK (rating BETWEEN 0 AND 5 OR rating IS NULL)
);

CREATE INDEX IF NOT EXISTS idx_user_movie_ratings_user ON user_movie_ratings(user_id);
CREATE INDEX IF NOT EXISTS idx_user_movie_ratings_movie ON user_movie_ratings(movie_id);

-- NOTE: update vector dimension if embedding model changes.
CREATE TABLE IF NOT EXISTS user_profiles (
  user_id BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  embedding vector(768) NOT NULL,
  embedding_model TEXT,
  num_ratings INT NOT NULL DEFAULT 0,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);


const API_BASE_URL = (import.meta.env.VITE_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
const API_URL = API_BASE_URL.endsWith("/v1") ? API_BASE_URL : `${API_BASE_URL}/v1`;

export type UserSummary = {
  id: number;
  display_name: string | null;
  num_ratings: number;
  profile_updated_at: string | null;
};

export type MovieLookup = { id: number; title: string | null };

export type MovieDetail = {
  id: number;
  title: string | null;
  original_title: string | null;
  release_date: string | null;
  genres: string | null;
  overview: string | null;
  tagline: string | null;
  runtime: number | null;
  original_language: string | null;
  vote_average: number | null;
  vote_count: number | null;
  poster_path: string | null;
  backdrop_path: string | null;
  poster_url: string | null;
  backdrop_url: string | null;
};

export type SimilarMovie = {
  id: number;
  title: string | null;
  release_date: string | null;
  genres: string | null;
  distance: number;
  score: number | null;
  poster_url: string | null;
  backdrop_url: string | null;
};

export type Recommendation = {
  id: number;
  title: string | null;
  release_date: string | null;
  genres: string | null;
  distance: number;
  similarity: number | null;
  poster_url: string | null;
  backdrop_url: string | null;
};

export type RatedMovie = {
  id: number;
  title: string | null;
  poster_url: string | null;
  backdrop_url: string | null;
  rating: number | null;
  status: string;
  updated_at: string | null;
};

export type RatingQueueItem = {
  id: number;
  title: string | null;
  release_date: string | null;
  genres: string | null;
  poster_url: string | null;
  backdrop_url: string | null;
};

export type ProfileStats = {
  user_id: number;
  num_ratings: number;
  num_liked: number;
  embedding_norm: number | null;
  updated_at: string | null;
};

export type NextMovie = {
  id: number;
  title: string | null;
  release_date: string | null;
  genres: string | null;
  source: string;
  poster_url: string | null;
  backdrop_url: string | null;
};

export type FeedItem = {
  id: number;
  title: string | null;
  release_date: string | null;
  genres: string | null;
  distance: number | null;
  similarity: number | null;
  source: string;
  poster_url: string | null;
  backdrop_url: string | null;
};

export type UserMovieMatch = {
  score: number | null;
};

type ApiSuccess<T> = {
  data: T;
  meta?: Record<string, unknown>;
};

type ApiFailure = {
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
};

export class ApiError extends Error {
  status: number;
  code?: string;
  details?: unknown;
  constructor(status: number, message: string, code?: string, details?: unknown) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T | undefined> {
  const response = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  const rawText = await response.text();
  let payload: ApiSuccess<T> | ApiFailure | null = null;
  if (rawText) {
    try {
      payload = JSON.parse(rawText) as ApiSuccess<T> | ApiFailure;
    } catch {
      payload = null;
    }
  }

  if (!response.ok) {
    if (payload && "error" in payload) {
      throw new ApiError(response.status, payload.error.message, payload.error.code, payload.error.details);
    }
    throw new ApiError(response.status, response.statusText);
  }

  if (response.status === 204) {
    return undefined;
  }

  if (!payload) {
    throw new ApiError(response.status, "Empty response payload");
  }

  if ("data" in payload) {
    if (payload.data === null || payload.data === undefined) {
      throw new ApiError(response.status, "Response envelope missing data", "EMPTY_DATA");
    }
    return payload.data as T;
  }

  throw new ApiError(response.status, "Unexpected response shape", "UNEXPECTED_RESPONSE");
}

export const api = {
  health: () => request<{ status: string }>("/health"),
  createUser: (display_name: string | null) =>
    request<UserSummary>("/users", {
      method: "POST",
      body: JSON.stringify({ display_name }),
    }),
  getUserSummary: (userId: number) => request<UserSummary>(`/users/${userId}`),
  getProfileStats: (userId: number) => request<ProfileStats>(`/users/${userId}/profile`),
  getFeed: (userId: number, k = 20) => request<FeedItem[]>(`/users/${userId}/feed?k=${k}`),
  getRecommendations: (userId: number, k = 20) =>
    request<Recommendation[]>(`/users/${userId}/recommendations?k=${k}`),
  getRatings: (userId: number, k = 20) => request<RatedMovie[]>(`/users/${userId}/ratings?k=${k}`),
  getRatingQueue: (userId: number, k = 20) =>
    request<RatingQueueItem[]>(`/users/${userId}/rating-queue?k=${k}`),
  getNextMovie: (userId: number) => request<NextMovie>(`/users/${userId}/next`),
  getUserMovieMatch: (userId: number, movieId: number) =>
    request<UserMovieMatch>(`/users/${userId}/movies/${movieId}/match`),
  rateMovie: (userId: number, movieId: number, rating: number | null, status: string) =>
    request<{ status: string }>(`/users/${userId}/ratings/${movieId}`, {
      method: "PUT",
      body: JSON.stringify({ rating, status }),
    }),
  lookupMovie: (title: string) => request<MovieLookup>(`/movies/lookup?title=${encodeURIComponent(title)}`),
  getMovieDetail: (movieId: number) => request<MovieDetail>(`/movies/${movieId}`),
  getSimilar: (movieId: number, k = 10) =>
    request<SimilarMovie[]>(`/movies/${movieId}/similar?k=${k}`),
};

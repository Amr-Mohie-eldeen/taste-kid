import { useStore } from "./store";

const API_BASE_URL = (import.meta.env.VITE_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
const API_URL = API_BASE_URL.endsWith("/v1") ? API_BASE_URL : `${API_BASE_URL}/v1`;

export type UserSummary = {
  id: number;
  display_name: string | null;
  num_ratings: number;
  profile_updated_at: string | null;
};

export type AuthTokenResponse = {
  access_token: string;
  token_type: string;
  user: UserSummary;
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
  score: number | null;
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
  score: number | null;
  source: string;
  poster_url: string | null;
  backdrop_url: string | null;
};

export type UserMovieMatch = {
  score: number | null;
};

export type PaginationMeta = {
  next_cursor: string | null;
  has_more: boolean;
};

export type PaginatedResponse<T> = {
  items: T[];
  meta: PaginationMeta;
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
  const envelope = await fetchEnvelope<T>(path, options);
  return envelope?.data;
}

async function fetchEnvelope<T>(path: string, options?: RequestInit): Promise<ApiSuccess<T> | undefined> {
  const { token } = useStore.getState();

  const headers = new Headers(options?.headers);
  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
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
    return payload;
  }

  throw new ApiError(response.status, "Unexpected response shape", "UNEXPECTED_RESPONSE");
}

async function requestPaginated<T>(path: string, options?: RequestInit): Promise<PaginatedResponse<T>> {
  const envelope = await fetchEnvelope<T[]>(path, options);
  if (!envelope) {
    throw new ApiError(204, "Empty response payload", "EMPTY_RESPONSE");
  }
  if (!Array.isArray(envelope.data)) {
    throw new ApiError(500, "Response data is not an array", "INVALID_DATA");
  }
  const meta = envelope.meta ?? {};
  const next_cursor = typeof meta.next_cursor === "string" ? meta.next_cursor : null;
  const has_more = meta.has_more === true;
  return { items: envelope.data, meta: { next_cursor, has_more } };
}

export const api = {
  health: () => request<{ status: string }>("/health"),
  register: (email: string, password: string, display_name: string | null) =>
    request<AuthTokenResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, display_name }),
    }),
  login: (email: string, password: string) =>
    request<AuthTokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  me: () => request<UserSummary>("/auth/me"),
  createUser: (display_name: string | null) =>
    request<UserSummary>("/users", {
      method: "POST",
      body: JSON.stringify({ display_name }),
    }),
  getUserSummary: (userId: number) => request<UserSummary>(`/users/${userId}`),
  getProfileStats: (userId: number) => request<ProfileStats>(`/users/${userId}/profile`),
  getFeed: (userId: number, k = 20, cursor?: string | null) =>
    requestPaginated<FeedItem>(`/users/${userId}/feed${buildPaginationQuery(k, cursor)}`),
  getRecommendations: (userId: number, k = 20, cursor?: string | null) =>
    requestPaginated<Recommendation>(`/users/${userId}/recommendations${buildPaginationQuery(k, cursor)}`),
  getRatings: (userId: number, k = 20, cursor?: string | null) =>
    requestPaginated<RatedMovie>(`/users/${userId}/ratings${buildPaginationQuery(k, cursor)}`),
  getRatingQueue: (userId: number, k = 20, cursor?: string | null) =>
    requestPaginated<RatingQueueItem>(`/users/${userId}/rating-queue${buildPaginationQuery(k, cursor)}`),
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
  getSimilar: (movieId: number, k = 10, cursor?: string | null) =>
    requestPaginated<SimilarMovie>(`/movies/${movieId}/similar${buildPaginationQuery(k, cursor)}`),
};

function buildPaginationQuery(k: number, cursor?: string | null) {
  const params = new URLSearchParams({ k: String(k) });
  if (cursor) {
    params.set("cursor", cursor);
  }
  return `?${params.toString()}`;
}

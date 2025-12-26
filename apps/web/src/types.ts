import type {
  FeedItem,
  NextMovie,
  ProfileStats,
  RatingQueueItem,
  RatedMovie,
  Recommendation,
  UserSummary,
} from "./lib/api";

export type DashboardData = {
  feed: FeedItem[];
  recommendations: Recommendation[];
  ratings: RatedMovie[];
  ratingQueue: RatingQueueItem[];
  nextMovie: NextMovie | null;
  userSummary: UserSummary | null;
  profileStats: ProfileStats | null;
};

export type MovieDetailMap = Record<number, string | null>;

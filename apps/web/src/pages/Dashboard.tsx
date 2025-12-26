import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  api,
  type FeedItem,
  type MovieDetail,
  type NextMovie,
  type ProfileStats,
  type RatingQueueItem,
  type RatedMovie,
  type Recommendation,
  type SimilarMovie,
  type UserSummary,
} from "../lib/api";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Separator } from "../components/ui/separator";
import { Skeleton } from "../components/ui/skeleton";
import { EmptyState } from "../components/EmptyState";
import { MovieCard } from "../components/MovieCard";
import { PosterImage } from "../components/PosterImage";
import { PageHeader } from "../components/PageHeader";
import { SectionHeader } from "../components/SectionHeader";
import { StatCard } from "../components/StatCard";

const formatDate = (value?: string | null) => {
  if (!value) return "-";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleDateString();
};


type DashboardProps = {
  apiStatus: "checking" | "online" | "offline";
  userId: number | null;
  setUserId: (id: number | null) => void;
};

export function Dashboard({ apiStatus, userId, setUserId }: DashboardProps) {
  const [displayName, setDisplayName] = useState("");
  const [existingUserId, setExistingUserId] = useState("");
  const [userSummary, setUserSummary] = useState<UserSummary | null>(null);
  const [profileStats, setProfileStats] = useState<ProfileStats | null>(null);
  const [activeTab, setActiveTab] = useState("feed");
  const [sectionLoading, setSectionLoading] = useState(false);
  const [sectionError, setSectionError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const [feed, setFeed] = useState<FeedItem[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [ratings, setRatings] = useState<RatedMovie[]>([]);
  const [ratingQueue, setRatingQueue] = useState<RatingQueueItem[]>([]);
  const [nextMovie, setNextMovie] = useState<NextMovie | null>(null);
  const [watchedCount, setWatchedCount] = useState<number | null>(null);
  const [recommendationLimit, setRecommendationLimit] = useState(20);
  const [hasMoreRecommendations, setHasMoreRecommendations] = useState(true);
  const [isFetchingMore, setIsFetchingMore] = useState(false);
  const recommendationSentinel = useRef<HTMLDivElement | null>(null);

  const [searchQuery, setSearchQuery] = useState("");
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [searchedMovie, setSearchedMovie] = useState<MovieDetail | null>(null);
  const [similarMovies, setSimilarMovies] = useState<SimilarMovie[]>([]);

  const [posterMap, setPosterMap] = useState<Record<number, string | null>>({});

  useEffect(() => {
    if (!userId) return;
    setSectionError(null);
    api
      .getUserSummary(userId)
      .then((summary) => setUserSummary(summary))
      .catch((error) => setSectionError(error.message));
    api
      .getProfileStats(userId)
      .then((stats) => setProfileStats(stats))
      .catch(() => null);
    api
      .getRatings(userId, 100)
      .then((items) =>
        setWatchedCount(items.filter((item) => item.status === "watched").length)
      )
      .catch(() => null);
  }, [userId]);

  useEffect(() => {
    if (!userId) return;
    const isRecommendationLoadMore =
      activeTab === "recommendations" && recommendationLimit > 20 && recommendations.length > 0;
    if (isRecommendationLoadMore) {
      setIsFetchingMore(true);
    } else {
      setSectionLoading(true);
    }
    setSectionError(null);
    const load = async () => {
      try {
        if (activeTab === "feed") {
          const data = await api.getFeed(userId);
          setFeed(data);
          await hydratePosters(data.map((item) => item.id));
        }
        if (activeTab === "recommendations") {
          const data = await api.getRecommendations(userId, recommendationLimit);
          setRecommendations(data);
          setHasMoreRecommendations(data.length >= recommendationLimit);
          await hydratePosters(data.map((item) => item.id));
        }
        if (activeTab === "ratings") {
          const data = await api.getRatings(userId);
          setRatings(data);
          await hydratePosters(data.map((item) => item.id));
        }
        if (activeTab === "rate") {
          const [queue, next] = await Promise.all([
            api.getRatingQueue(userId),
            api.getNextMovie(userId).catch(() => null),
          ]);
          setRatingQueue(queue);
          setNextMovie(next);
          const ids = queue.map((item) => item.id);
          if (next) ids.push(next.id);
          await hydratePosters(ids);
        }
      } catch (error) {
        const message = error instanceof Error ? error.message : "Unable to load data";
        setSectionError(message);
      } finally {
        setSectionLoading(false);
        setIsFetchingMore(false);
      }
    };
    void load();
  }, [activeTab, recommendationLimit, userId]);

  useEffect(() => {
    if (activeTab !== "recommendations") return;
    setRecommendationLimit(20);
    setHasMoreRecommendations(true);
    setIsFetchingMore(false);
  }, [activeTab]);

  useEffect(() => {
    if (activeTab !== "recommendations") return;
    const target = recommendationSentinel.current;
    if (!target) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const [entry] = entries;
        if (!entry?.isIntersecting) return;
        if (!hasMoreRecommendations || sectionLoading || isFetchingMore) return;
        setIsFetchingMore(true);
        setRecommendationLimit((prev) => prev + 20);
      },
      { rootMargin: "200px" }
    );

    observer.observe(target);
    return () => observer.disconnect();
  }, [activeTab, hasMoreRecommendations, isFetchingMore, sectionLoading]);

  useEffect(() => {
    if (!sectionLoading && activeTab === "recommendations") {
      setIsFetchingMore(false);
    }
  }, [activeTab, sectionLoading]);

  const hydratePosters = async (ids: number[]) => {
    const missing = ids.filter((id) => !(id in posterMap));
    if (!missing.length) return;
    const results = await Promise.all(
      missing.map((id) => api.getMovieDetail(id).catch(() => null))
    );
    setPosterMap((prev) => {
      const next = { ...prev };
      results.forEach((detail, index) => {
        const id = missing[index];
        next[id] = detail?.poster_url ?? detail?.backdrop_url ?? null;
      });
      return next;
    });
  };

  const handleSetUserId = (id: number) => {
    setUserId(id);
    localStorage.setItem("tastekid:userId", id.toString());
  };

  const handleCreateUser = async () => {
    setSectionError(null);
    setStatusMessage(null);
    try {
      const summary = await api.createUser(displayName.trim() || null);
      setUserSummary(summary);
      handleSetUserId(summary.id);
      setStatusMessage("Profile created. Start rating to personalize your feed.");
    } catch (error) {
      setSectionError(error instanceof Error ? error.message : "Failed to create user");
    }
  };

  const handleUseExisting = () => {
    const id = Number(existingUserId);
    if (!Number.isFinite(id) || id <= 0) {
      setSectionError("Enter a valid user id.");
      return;
    }
    setSectionError(null);
    setStatusMessage(null);
    handleSetUserId(id);
  };

  const handleRateMovie = async (movieId: number, rating: number | null, status: string) => {
    if (!userId) return;
    setSectionLoading(true);
    setSectionError(null);
    try {
      await api.rateMovie(userId, movieId, rating, status);
      const [queue, next, stats, summary] = await Promise.all([
        api.getRatingQueue(userId),
        api.getNextMovie(userId).catch(() => null),
        api.getProfileStats(userId),
        api.getUserSummary(userId),
      ]);
      setRatingQueue(queue);
      setNextMovie(next);
      setProfileStats(stats);
      setUserSummary(summary);
      const ids = queue.map((item) => item.id);
      if (next) ids.push(next.id);
      await hydratePosters(ids);
      api
        .getRatings(userId, 100)
        .then((items) =>
          setWatchedCount(items.filter((item) => item.status === "watched").length)
        )
        .catch(() => null);
      setStatusMessage("Rating saved.");
    } catch (error) {
      setSectionError(error instanceof Error ? error.message : "Failed to update rating");
    } finally {
      setSectionLoading(false);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setSearchLoading(true);
    setSearchError(null);
    setSearchedMovie(null);
    setSimilarMovies([]);
    try {
      const lookup = await api.lookupMovie(searchQuery.trim());
      const [detail, similar] = await Promise.all([
        api.getMovieDetail(lookup.id),
        api.getSimilar(lookup.id),
      ]);
      setSearchedMovie(detail);
      setSimilarMovies(similar);
      await hydratePosters(similar.map((item) => item.id));
    } catch (error) {
      setSearchError(error instanceof Error ? error.message : "Search failed");
    } finally {
      setSearchLoading(false);
    }
  };

  const nextPoster = nextMovie ? posterMap[nextMovie.id] : null;
  const watchedRatings = useMemo(
    () => ratings.filter((item) => item.status === "watched"),
    [ratings]
  );
  const ratingsCount = watchedCount ?? userSummary?.num_ratings ?? 0;

  const gridClass = useMemo(
    () => "grid auto-rows-fr gap-4 sm:grid-cols-2 lg:grid-cols-3",
    []
  );

  return (
    <div className="space-y-10">
      <PageHeader
        title="Taste.io Studio"
        subtitle=""
        status={apiStatus}
        userId={userId}
      />

      <div className="grid gap-6 lg:grid-cols-[1.2fr_1fr]">
        <Card className="shadow-glow">
          <CardHeader>
            <CardTitle>Get started</CardTitle>
            <CardDescription>Create or load a profile.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="grid gap-3 sm:grid-cols-[1fr_auto]">
              <Input
                placeholder="Display name (optional)"
                value={displayName}
                onChange={(event) => setDisplayName(event.target.value)}
              />
              <Button onClick={handleCreateUser}>Create profile</Button>
            </div>
            <Separator />
            <div className="grid gap-3 sm:grid-cols-[1fr_auto]">
              <Input
                placeholder="Existing user id"
                value={existingUserId}
                onChange={(event) => setExistingUserId(event.target.value)}
              />
              <Button variant="outline" onClick={handleUseExisting}>
                Load profile
              </Button>
            </div>
            {statusMessage ? (
              <p className="text-sm text-primary">{statusMessage}</p>
            ) : null}
            {sectionError ? (
              <p className="text-sm text-destructive">{sectionError}</p>
            ) : null}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Profile snapshot</CardTitle>
            <CardDescription>Monitor how your taste vector evolves.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-2">
            <StatCard label="Ratings" value={ratingsCount} />
            <StatCard label="Likes" value={profileStats?.num_liked ?? 0} />
            <StatCard label="Embedding" value={profileStats?.embedding_norm?.toFixed(2)} />
            <StatCard
              label="Updated"
              value={profileStats?.updated_at ? formatDate(profileStats.updated_at) : "-"}
            />
          </CardContent>
        </Card>
        </div>

      <div>
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="flex flex-wrap justify-start gap-2">
            <TabsTrigger value="feed">Feed</TabsTrigger>
            <TabsTrigger value="rate">Rate</TabsTrigger>
            <TabsTrigger value="recommendations">Recommendations</TabsTrigger>
            <TabsTrigger value="ratings">Ratings</TabsTrigger>
            <TabsTrigger value="search">Search</TabsTrigger>
          </TabsList>

            <TabsContent value="feed">
              <div className="space-y-4">
                <SectionHeader title="For You" />
                {sectionLoading ? (
                  <Skeleton className="h-32" />
                ) : feed.length ? (
                  <div className={gridClass}>
                    {feed.map((item) => (
                      <MovieCard
                        key={item.id}
                        title={item.title}
                        releaseDateLabel={item.release_date ? formatDate(item.release_date) : null}
                        genres={item.genres}
                        imageUrl={posterMap[item.id]}
                        to={`/movie/${item.id}`}
                        similarity={item.similarity}
                      />
                    ))}
                  </div>
                ) : (
                  <EmptyState
                    title="No feed yet"
                  />
                )}
              </div>
            </TabsContent>

            <TabsContent value="rate">
              <div className="space-y-6">
                <SectionHeader title="Rate the next pick" />
                <div className="min-h-[320px]">
                  {sectionLoading ? (
                    <Skeleton className="h-64" />
                  ) : nextMovie ? (
                    <div key={nextMovie.id} className="swap-fade">
                      <MovieCard
                        title={nextMovie.title}
                        releaseDateLabel={nextMovie.release_date ? formatDate(nextMovie.release_date) : null}
                        genres={nextMovie.genres}
                        imageUrl={nextPoster}
                        layout="row"
                        imageClassName="sm:w-28"
                        actions={
                          <div className="flex flex-wrap gap-2">
                            {[5, 4, 3, 2, 1].map((rating) => (
                              <Button
                                key={rating}
                                size="sm"
                                variant="outline"
                                onClick={() => handleRateMovie(nextMovie.id, rating, "watched")}
                              >
                                {rating}★
                              </Button>
                            ))}
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => handleRateMovie(nextMovie.id, null, "unwatched")}
                            >
                              Skip
                            </Button>
                            <Button size="sm" variant="ghost" asChild>
                              <Link to={`/movie/${nextMovie.id}`}>Details</Link>
                            </Button>
                          </div>
                        }
                      />
                    </div>
                  ) : (
                    <EmptyState title="You're all caught up" />
                  )}
                </div>

                <Separator />
                <SectionHeader title="Up next" />
                {sectionLoading ? (
                  <Skeleton className="h-20" />
                ) : ratingQueue.length ? (
                  <Card>
                    <CardContent className="flex items-center justify-between gap-4 p-5">
                      <div>
                        <p className="text-sm font-medium text-foreground">
                          {ratingQueue.length} titles in your queue
                        </p>
                      </div>
                      <div className="relative flex h-14 w-28 items-center">
                        {ratingQueue.slice(0, 3).map((item, index) => (
                          <div
                            key={item.id}
                            className="absolute h-14 w-10 overflow-hidden rounded-md border border-border bg-muted shadow-sm"
                            style={{ left: `${index * 18}px`, zIndex: 10 - index }}
                          >
                            {posterMap[item.id] ? (
                              <PosterImage
                                src={posterMap[item.id] ?? ""}
                                alt={item.title ?? "Movie"}
                              />
                            ) : null}
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                ) : (
                  <EmptyState title="Queue empty" />
                )}
              </div>
            </TabsContent>

            <TabsContent value="recommendations">
              <div className="space-y-4">
                <SectionHeader title="Recommendations" />
                {sectionLoading && !recommendations.length ? (
                  <Skeleton className="h-32" />
                ) : recommendations.length ? (
                  <div className="space-y-4">
                    <div className={gridClass}>
                      {recommendations.map((item) => (
                        <MovieCard
                          key={item.id}
                          title={item.title}
                          releaseDateLabel={item.release_date ? formatDate(item.release_date) : null}
                          genres={item.genres}
                          imageUrl={posterMap[item.id]}
                          to={`/movie/${item.id}`}
                          similarity={item.similarity}
                        />
                      ))}
                    </div>
                    {isFetchingMore ? <Skeleton className="h-12" /> : null}
                    {hasMoreRecommendations ? (
                      <div ref={recommendationSentinel} className="h-10" />
                    ) : null}
                  </div>
                ) : (
                  <EmptyState title="No recommendations yet" />
                )}
              </div>
            </TabsContent>

            <TabsContent value="ratings">
              <div className="space-y-4">
                <SectionHeader title="Your ratings" />
                {sectionLoading ? (
                  <Skeleton className="h-32" />
                ) : watchedRatings.length ? (
                  <div className={gridClass}>
                    {watchedRatings.map((item) => (
                      <MovieCard
                        key={item.id}
                        title={item.title}
                        subtitle={item.updated_at ? `Updated ${formatDate(item.updated_at)}` : null}
                        meta={[`Rating: ${item.rating ?? "-"}`]}
                        imageUrl={posterMap[item.id]}
                        to={`/movie/${item.id}`}
                      />
                    ))}
                  </div>
                ) : (
                  <EmptyState title="No ratings yet" />
                )}
              </div>
            </TabsContent>

            <TabsContent value="search">
              <div className="space-y-6">
                <SectionHeader title="Search movies" />
                <div className="flex flex-col gap-3 sm:flex-row">
                  <Input
                    value={searchQuery}
                    placeholder="Search by movie title"
                    onChange={(event) => setSearchQuery(event.target.value)}
                  />
                  <Button disabled={!searchQuery.trim() || searchLoading} onClick={handleSearch}>
                    {searchLoading ? "Searching..." : "Search"}
                  </Button>
                </div>
                {searchError ? <p className="text-sm text-destructive">{searchError}</p> : null}

                {searchLoading ? (
                  <Skeleton className="h-48" />
                ) : searchedMovie ? (
                  <MovieCard
                    title={searchedMovie.title}
                    subtitle={searchedMovie.tagline}
                    releaseDateLabel={
                      searchedMovie.release_date ? formatDate(searchedMovie.release_date) : null
                    }
                    genres={searchedMovie.genres}
                    description={searchedMovie.overview}
                    imageUrl={searchedMovie.poster_url || searchedMovie.backdrop_url}
                    to={`/movie/${searchedMovie.id}`}
                  />
                ) : null}

                <Separator />
                <SectionHeader title="Similar movies" />
                {searchLoading ? (
                  <Skeleton className="h-24" />
                ) : similarMovies.length ? (
                  <div className={gridClass}>
                    {similarMovies.map((item) => (
                      <MovieCard
                        key={item.id}
                        title={item.title}
                        releaseDateLabel={item.release_date ? formatDate(item.release_date) : null}
                        genres={item.genres}
                        imageUrl={posterMap[item.id]}
                        to={`/movie/${item.id}`}
                        similarity={item.score}
                      />
                    ))}
                  </div>
                ) : (
                  <EmptyState title="No similar movies" />
                )}
              </div>
            </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

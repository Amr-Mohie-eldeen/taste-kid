import { useEffect, useMemo, useRef, useState } from "react";
import { useStore } from "../lib/store";
import {
  useUserSummary,
  useProfileStats,
  useFeed,
  useRecommendations,
  useRatings,
  useRatingQueue,
  useNextMovie,
  useRateMovie,
  useCreateUser,
} from "../lib/hooks";
import { usePosterHydration } from "../lib/usePosterHydration";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Separator } from "../components/ui/separator";
import { PageHeader } from "../components/PageHeader";
import { StatCard } from "../components/StatCard";
import { formatDate } from "../lib/utils";
import { Feed } from "./Dashboard/Feed";
import { Rate } from "./Dashboard/Rate";
import { Recommendations } from "./Dashboard/Recommendations";
import { Ratings } from "./Dashboard/Ratings";
import { Search } from "./Dashboard/Search";
import { api } from "../lib/api";
import { 
  UserPlus, 
  LogIn, 
  LayoutDashboard, 
  Star, 
  Compass, 
  History, 
  Search as SearchIcon,
  Zap
} from "lucide-react";

type DashboardProps = {
  userId: number | null;
  setUserId: (id: number | null) => void;
};

export function Dashboard({ userId, setUserId }: DashboardProps) {
  const { posterMap } = useStore();
  const [displayName, setDisplayName] = useState("");
  const [existingUserId, setExistingUserId] = useState("");
  const [activeTab, setActiveTab] = useState("feed");
  
  // Pagination State
  const [recommendationLimit, setRecommendationLimit] = useState(20);
  const [feedLimit, setFeedLimit] = useState(20);
  
  const recommendationSentinel = useRef<HTMLDivElement | null>(null);
  const feedSentinel = useRef<HTMLDivElement | null>(null);

  // Queries
  const { data: userSummary, error: summaryError } = useUserSummary(userId);
  const { data: profileStats } = useProfileStats(userId);
  
  const { 
    data: feed, 
    isLoading: feedLoading, 
    isPlaceholderData: feedIsPlaceholder 
  } = useFeed(userId, feedLimit);
  
  const { 
    data: recommendations, 
    isLoading: recsLoading, 
    isPlaceholderData: recsIsPlaceholder 
  } = useRecommendations(userId, recommendationLimit);
  
  const { data: ratings, isLoading: ratingsLoading } = useRatings(userId);
  const { data: ratingQueue, isLoading: queueLoading } = useRatingQueue(userId);
  const { data: nextMovie, isLoading: nextLoading } = useNextMovie(userId);

  const [searchedMovie, setSearchedMovie] = useState<any>(null);
  const [similarMovies, setSimilarMovies] = useState<any[]>([]);

  // Mutations
  const createUser = useCreateUser();
  const rateMovie = useRateMovie();

  // Consolidated Poster Hydration
  const allIds = useMemo(() => {
    const set = new Set<number>();
    feed?.forEach(m => set.add(m.id));
    recommendations?.forEach(m => set.add(m.id));
    ratings?.forEach(m => set.add(m.id));
    ratingQueue?.forEach(m => set.add(m.id));
    if (nextMovie) set.add(nextMovie.id);
    similarMovies?.forEach(m => set.add(m.id));
    return Array.from(set);
  }, [feed, recommendations, ratings, ratingQueue, nextMovie, similarMovies]);

  usePosterHydration(allIds);

  const hasMoreRecommendations = useMemo(() => {
    if (!recommendations) return false;
    if (recsIsPlaceholder) return true;
    return recommendations.length >= recommendationLimit;
  }, [recommendations, recsIsPlaceholder, recommendationLimit]);

  const hasMoreFeed = useMemo(() => {
    if (!feed) return false;
    if (feedIsPlaceholder) return true;
    return feed.length >= feedLimit;
  }, [feed, feedIsPlaceholder, feedLimit]);

  // Infinite Scroll Observer
  useEffect(() => {
    const isRecs = activeTab === "recommendations";
    const isFeed = activeTab === "feed";
    
    if (!isRecs && !isFeed) return;

    const target = isRecs ? recommendationSentinel.current : feedSentinel.current;
    if (!target) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const [entry] = entries;
        if (entry.isIntersecting) {
          if (isRecs && hasMoreRecommendations && !recsIsPlaceholder) {
            setRecommendationLimit(prev => prev + 20);
          } else if (isFeed && hasMoreFeed && !feedIsPlaceholder) {
            setFeedLimit(prev => prev + 20);
          }
        }
      },
      { rootMargin: "800px" } 
    );

    observer.observe(target);
    return () => observer.disconnect();
  }, [activeTab, hasMoreRecommendations, recsIsPlaceholder, hasMoreFeed, feedIsPlaceholder]);

  // Custom Search State
  const [manualSearchLoading, setManualSearchLoading] = useState(false);
  const [manualSearchError, setManualSearchError] = useState<string | null>(null);

  const performSearch = async (query: string) => {
    if (!query.trim()) return;
    setManualSearchLoading(true);
    setManualSearchError(null);
    setSearchedMovie(null);
    setSimilarMovies([]);
    
    try {
      const lookup = await api.lookupMovie(query);
      const [detail, similar] = await Promise.all([
        api.getMovieDetail(lookup.id),
        api.getSimilar(lookup.id),
      ]);
      setSearchedMovie(detail);
      setSimilarMovies(similar);
    } catch (error) {
      setManualSearchError(error instanceof Error ? error.message : "Search failed");
    } finally {
      setManualSearchLoading(false);
    }
  };

  const handleCreateUser = () => {
    createUser.mutate(displayName.trim() || null);
  };

  const handleUseExisting = () => {
    const id = Number(existingUserId);
    if (!Number.isFinite(id) || id <= 0) return;
    setUserId(id);
    localStorage.setItem("tastekid:userId", id.toString());
  };

  const handleRateMovie = (movieId: number, rating: number | null, status: string) => {
    if (!userId) return;
    rateMovie.mutate({ userId, movieId, rating, status });
  };

  const ratingsCount = ratings?.filter((r) => r.status === "watched").length ?? userSummary?.num_ratings ?? 0;
  
  const gridClass = useMemo(
    () => "grid auto-rows-fr gap-6 sm:grid-cols-2 lg:grid-cols-3",
    []
  );

  return (
    <div className="space-y-8 max-w-[1400px] mx-auto">
      <PageHeader
        title="Intelligence Studio"
        subtitle="Harnessing vector similarity to map your cinematic taste profile."
        userId={userId}
      />

      <div className="grid gap-8 lg:grid-cols-[1fr_320px]">
        {/* Main Content */}
        <div className="space-y-8 order-2 lg:order-1">
          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
            <div className="flex items-center justify-between mb-6 overflow-x-auto pb-2 scrollbar-hide">
              <TabsList className="bg-secondary/50 p-1 rounded-2xl border border-border/50">
                <TabsTrigger value="feed" className="rounded-xl gap-2 px-5">
                  <LayoutDashboard className="h-4 w-4" />
                  Feed
                </TabsTrigger>
                <TabsTrigger value="rate" className="rounded-xl gap-2 px-5">
                  <Star className="h-4 w-4" />
                  Rate
                </TabsTrigger>
                <TabsTrigger value="recommendations" className="rounded-xl gap-2 px-5">
                  <Compass className="h-4 w-4" />
                  Discovery
                </TabsTrigger>
                <TabsTrigger value="ratings" className="rounded-xl gap-2 px-5">
                  <History className="h-4 w-4" />
                  History
                </TabsTrigger>
                <TabsTrigger value="search" className="rounded-xl gap-2 px-5">
                  <SearchIcon className="h-4 w-4" />
                  Search
                </TabsTrigger>
              </TabsList>
            </div>

            <TabsContent value="feed" className="mt-0 focus-visible:ring-0">
              <Feed
                feed={feed || []}
                posterMap={posterMap}
                loading={feedLoading}
                gridClass={gridClass}
                isFetchingMore={feedIsPlaceholder}
                hasMore={hasMoreFeed}
                sentinelRef={feedSentinel}
              />
            </TabsContent>

            <TabsContent value="rate" className="mt-0 focus-visible:ring-0">
              <Rate
                nextMovie={nextMovie}
                ratingQueue={ratingQueue || []}
                posterMap={posterMap}
                loading={queueLoading || nextLoading}
                onRateMovie={handleRateMovie}
              />
            </TabsContent>

            <TabsContent value="recommendations" className="mt-0 focus-visible:ring-0">
              <Recommendations
                recommendations={recommendations || []}
                posterMap={posterMap}
                loading={recsLoading}
                gridClass={gridClass}
                isFetchingMore={recsIsPlaceholder}
                hasMoreRecommendations={hasMoreRecommendations}
                recommendationSentinel={recommendationSentinel}
              />
            </TabsContent>

            <TabsContent value="ratings" className="mt-0 focus-visible:ring-0">
              <Ratings
                ratings={ratings || []}
                posterMap={posterMap}
                loading={ratingsLoading}
                gridClass={gridClass}
              />
            </TabsContent>

            <TabsContent value="search" className="mt-0 focus-visible:ring-0">
              <Search
                onSearch={performSearch}
                searchLoading={manualSearchLoading}
                searchError={manualSearchError}
                searchedMovie={searchedMovie}
                similarMovies={similarMovies}
                posterMap={posterMap}
                gridClass={gridClass}
              />
            </TabsContent>
          </Tabs>
        </div>

        {/* Sidebar */}
        <div className="space-y-6 order-1 lg:order-2">
          {!userId ? (
            <Card className="border-primary/20 bg-primary/[0.02] shadow-sm rounded-3xl overflow-hidden">
              <CardHeader className="pb-4">
                <div className="flex items-center gap-2 text-primary mb-1">
                  <Zap className="h-4 w-4 fill-primary" />
                  <span className="text-[10px] font-bold uppercase tracking-wider">Quick Start</span>
                </div>
                <CardTitle className="text-xl">Initialize Profile</CardTitle>
                <CardDescription className="text-xs">Create a new identity or load an existing one.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Input
                    placeholder="Identity Name"
                    value={displayName}
                    onChange={(event) => setDisplayName(event.target.value)}
                    className="h-10 rounded-xl bg-background border-border/60"
                  />
                  <Button 
                    onClick={handleCreateUser} 
                    disabled={createUser.isPending}
                    className="w-full h-10 rounded-xl gap-2 font-bold shadow-md shadow-primary/20"
                  >
                    <UserPlus className="h-4 w-4" />
                    Generate Identity
                  </Button>
                </div>
                <div className="relative py-2">
                  <div className="absolute inset-0 flex items-center">
                    <Separator />
                  </div>
                  <div className="relative flex justify-center text-[10px] uppercase font-bold">
                    <span className="bg-background px-2 text-muted-foreground">OR</span>
                  </div>
                </div>
                <div className="space-y-2">
                  <Input
                    placeholder="Existing ID"
                    value={existingUserId}
                    onChange={(event) => setExistingUserId(event.target.value)}
                    className="h-10 rounded-xl bg-background border-border/60"
                  />
                  <Button 
                    variant="secondary" 
                    onClick={handleUseExisting}
                    className="w-full h-10 rounded-xl gap-2 font-bold"
                  >
                    <LogIn className="h-4 w-4" />
                    Resume Session
                  </Button>
                </div>
                {summaryError && (
                  <p className="text-[11px] font-medium text-destructive bg-destructive/5 p-2 rounded-lg border border-destructive/10 text-center">
                    Authentication failed. Check your ID.
                  </p>
                )}
              </CardContent>
            </Card>
          ) : (
            <Card className="border-border/40 shadow-sm rounded-3xl overflow-hidden">
              <CardHeader className="pb-4">
                <div className="flex items-center gap-2 text-muted-foreground mb-1">
                  <Zap className="h-4 w-4" />
                  <span className="text-[10px] font-bold uppercase tracking-wider">Profile Status</span>
                </div>
                <CardTitle className="text-xl">Taste Metrics</CardTitle>
                <CardDescription className="text-xs">Real-time profile vector analysis.</CardDescription>
              </CardHeader>
              <CardContent className="grid gap-3">
                <StatCard 
                  label="Computed Ratings" 
                  value={ratingsCount} 
                  className="rounded-2xl"
                />
                <StatCard 
                  label="Liked Patterns" 
                  value={profileStats?.num_liked ?? 0} 
                  className="rounded-2xl"
                />
                <StatCard 
                  label="Vector Norm" 
                  value={profileStats?.embedding_norm?.toFixed(3)} 
                  hint="Confidence"
                  className="rounded-2xl"
                />
                <div className="mt-2 text-center">
                  <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">
                    Last Synced: {profileStats?.updated_at ? formatDate(profileStats.updated_at) : "Never"}
                  </p>
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    onClick={() => setUserId(null)}
                    className="mt-4 text-[10px] h-7 font-bold uppercase tracking-wider text-muted-foreground hover:text-destructive"
                  >
                    Terminate Session
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

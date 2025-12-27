import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  useUserSummary,
  useProfileStats,
  useFeed,
  useRatings,
  useRatingQueue,
  useNextMovie,
  useRateMovie,
  useCreateUser,
  useMovieSearch,
} from "../lib/hooks";
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
// Discovery tab removed
import { Ratings } from "./Dashboard/Ratings";
import { Search } from "./Dashboard/Search";
import { 
  UserPlus, 
  LogIn, 
  LayoutDashboard, 
  Star, 
  History, 
  Search as SearchIcon,
  Zap
} from "lucide-react";

type DashboardProps = {
  userId: number | null;
  setUserId: (id: number | null) => void;
};

export function Dashboard({ userId, setUserId }: DashboardProps) {
  const [displayName, setDisplayName] = useState("");
  const [existingUserId, setExistingUserId] = useState("");
  const [activeTab, setActiveTab] = useState("feed");
  
  // Pagination State
  const [feedLimit, setFeedLimit] = useState(20);
  
  // Sentinel + observer for feed
  const feedSentinelRef = useRef<HTMLDivElement | null>(null);
  const feedObserverRef = useRef<IntersectionObserver | null>(null);

  // Search State
  const [searchQuery, setSearchQuery] = useState("");
  const [isSearchEnabled, setIsSearchEnabled] = useState(false);

  // Queries
  const { data: userSummary, error: summaryError } = useUserSummary(userId);
  const { data: profileStats } = useProfileStats(userId);
  
  const { 
    data: feed, 
    isLoading: feedLoading, 
    isPlaceholderData: feedIsPlaceholder,
    isFetching: feedFetching,
  } = useFeed(userId, feedLimit);
  
  const { data: ratings, isLoading: ratingsLoading } = useRatings(userId);
  const { data: ratingQueue, isLoading: queueLoading } = useRatingQueue(userId);
  const { data: nextMovie, isLoading: nextLoading } = useNextMovie(userId);

  const {
    data: searchData,
    isLoading: searchIsLoading,
    error: searchError,
  } = useMovieSearch(searchQuery, isSearchEnabled);

  // Mutations
  const createUser = useCreateUser();
  const rateMovie = useRateMovie();

  const hasMoreFeed = useMemo(() => {
    if (!feed) return false;
    if (feedIsPlaceholder) return true;
    return feed.length >= feedLimit;
  }, [feed, feedIsPlaceholder, feedLimit]);

  const lastTriggeredFeedLimit = useRef(20);

  // Setup observer for feed sentinel
  const setupFeedObserver = useCallback(() => {
    const node = feedSentinelRef.current;
    if (!node) return;
    if (feedObserverRef.current) feedObserverRef.current.disconnect();
    const isFeed = activeTab === "feed";
    const observer = new IntersectionObserver(
      (entries) => {
        const [entry] = entries;
        if (!entry.isIntersecting) return;
        if (!isFeed) return;
        if (!hasMoreFeed) return;
        if (feedIsPlaceholder || feedFetching) return;
        if (feedLimit !== lastTriggeredFeedLimit.current) return;
        const nextLimit = feedLimit + 20;
        lastTriggeredFeedLimit.current = nextLimit;
        setFeedLimit(nextLimit);
      },
      { rootMargin: "50px", threshold: 0.01 }
    );
    feedObserverRef.current = observer;
    observer.observe(node);
  }, [activeTab, hasMoreFeed, feedIsPlaceholder, feedFetching, feedLimit]);

  // Recreate observers when relevant state changes and sentinel exists
  useEffect(() => {
    setupFeedObserver();
    return () => {
      if (feedObserverRef.current) feedObserverRef.current.disconnect();
    };
  }, [setupFeedObserver]);

  // Callback ref to capture sentinel node when it mounts/unmounts
  const setFeedSentinel = useCallback((node: HTMLDivElement | null) => {
    feedSentinelRef.current = node;
    if (node) {
      setupFeedObserver();
    } else if (feedObserverRef.current) {
      feedObserverRef.current.disconnect();
      feedObserverRef.current = null;
    }
  }, [setupFeedObserver]);

  // When tab is not 'search', disable search query
  useEffect(() => {
    if (activeTab !== 'search') {
      setIsSearchEnabled(false);
    }
  }, [activeTab]);
  
  const performSearch = (query: string) => {
    setSearchQuery(query);
    setIsSearchEnabled(true);
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
                {/* Discovery tab removed */}
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
                loading={feedLoading}
                gridClass={gridClass}
                isFetchingMore={feedIsPlaceholder}
                hasMore={hasMoreFeed}
                sentinelRef={setFeedSentinel}
              />
            </TabsContent>

            <TabsContent value="rate" className="mt-0 focus-visible:ring-0">
              <Rate
                nextMovie={nextMovie}
                ratingQueue={ratingQueue || []}
                loading={queueLoading || nextLoading}
                onRateMovie={handleRateMovie}
              />
            </TabsContent>

            {/* Discovery content removed */}

            <TabsContent value="ratings" className="mt-0 focus-visible:ring-0">
              <Ratings
                ratings={ratings || []}
                loading={ratingsLoading}
                gridClass={gridClass}
              />
            </TabsContent>

            <TabsContent value="search" className="mt-0 focus-visible:ring-0">
              <Search
                onSearch={performSearch}
                searchLoading={searchIsLoading}
                searchError={searchError instanceof Error ? searchError.message : null}
                searchedMovie={searchData?.detail ?? null}
                similarMovies={searchData?.similar ?? []}
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

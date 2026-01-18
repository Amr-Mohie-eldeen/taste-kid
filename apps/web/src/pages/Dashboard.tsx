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
  useLogin,
  useMovieSearch,
} from "../lib/hooks";
import { ensureLoggedIn, logout } from "../lib/oidc";
import { queryClient } from "../lib/queryClient";
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
  History,
  LayoutDashboard,
  LogIn,
  Search as SearchIcon,
  Star,
  UserPlus,
  Zap,
  User,
  LogOut,
} from "lucide-react";

import { useStore } from "../lib/store";

type DashboardProps = {
  userId: number | null;
  setUserId: (id: number | null) => void;
};

export function Dashboard({ userId, setUserId }: DashboardProps) {
  const { resetSession, userProfile } = useStore();
  const [activeTab, setActiveTab] = useState("feed");
  
  const feedPageSize = 20;
  const ratingsPageSize = 20;
  
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
    isFetchingNextPage: feedFetchingNextPage,
    hasNextPage: feedHasNextPage,
    fetchNextPage: fetchNextFeedPage,
  } = useFeed(userId, feedPageSize);

  const {
    data: ratings,
    isLoading: ratingsLoading,
    isFetchingNextPage: ratingsFetchingNextPage,
    hasNextPage: ratingsHasNextPage,
    fetchNextPage: fetchNextRatingsPage,
  } = useRatings(userId, ratingsPageSize);
  const { data: ratingQueue, isLoading: queueLoading } = useRatingQueue(userId);
  const { data: nextMovie, isLoading: nextLoading } = useNextMovie(userId);

  const {
    data: searchData,
    isLoading: searchIsLoading,
    error: searchError,
  } = useMovieSearch(searchQuery, isSearchEnabled);

  // Mutations
  const rateMovie = useRateMovie();

  const feedItems = useMemo(
    () => feed?.pages.flatMap((page) => page.items) ?? [],
    [feed]
  );
  const ratingsItems = useMemo(
    () => ratings?.pages.flatMap((page) => page.items) ?? [],
    [ratings]
  );

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
        if (!feedHasNextPage) return;
        if (feedFetchingNextPage) return;
        fetchNextFeedPage();
      },
      { rootMargin: "50px", threshold: 0.01 }
    );
    feedObserverRef.current = observer;
    observer.observe(node);
  }, [activeTab, feedHasNextPage, feedFetchingNextPage, fetchNextFeedPage]);

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


  const handleRateMovie = (movieId: number, rating: number | null, status: string) => {
    if (!userId) return;
    rateMovie.mutate({ userId, movieId, rating, status });
  };

  const ratingsCount = userSummary?.num_ratings
    ?? profileStats?.num_ratings
    ?? ratingsItems.filter((r) => r.status === "watched" && r.rating !== null).length;
  
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
                feed={feedItems}
                loading={feedLoading}
                gridClass={gridClass}
                isFetchingMore={feedFetchingNextPage}
                hasMore={feedHasNextPage}
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
                ratings={ratingsItems}
                loading={ratingsLoading}
                gridClass={gridClass}
                hasMore={ratingsHasNextPage}
                isFetchingMore={ratingsFetchingNextPage}
                onLoadMore={fetchNextRatingsPage}
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
                  <span className="text-[10px] font-bold uppercase tracking-wider">Session</span>
                </div>
                <CardTitle className="text-xl">Sign in to continue</CardTitle>
                <CardDescription className="text-xs">Authentication is handled by the identity provider.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <Button
                  onClick={() => ensureLoggedIn({ action: "login" })}
                  className="w-full h-10 rounded-xl gap-2 font-bold shadow-md shadow-primary/20"
                >
                  <LogIn className="h-4 w-4" />
                  Continue with Login
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => ensureLoggedIn({ action: "register" })}
                  className="w-full h-10 rounded-xl gap-2 font-bold"
                >
                  <UserPlus className="h-4 w-4" />
                  Create Account
                </Button>
                {summaryError && (
                  <p className="text-[11px] font-medium text-destructive bg-destructive/5 p-2 rounded-lg border border-destructive/10 text-center">
                    Authentication failed.
                  </p>
                )}
              </CardContent>
            </Card>
          ) : (
            <Card className="border-border/40 shadow-sm rounded-3xl overflow-hidden">
              <CardHeader className="pb-4 relative">
                <div className="flex items-center justify-between">
                   <div className="flex items-center gap-2 text-muted-foreground mb-1">
                    <User className="h-4 w-4" />
                    <span className="text-[10px] font-bold uppercase tracking-wider">Your Profile</span>
                  </div>
                   <Button
                    variant="ghost"
                    size="sm"
                    onClick={async () => {
                      resetSession();
                      queryClient.clear();
                      try {
                        await logout({ redirectTo: "home" });
                      } catch {
                        window.location.assign("/");
                      }
                    }}
                    className="h-8 w-8 p-0 rounded-full text-muted-foreground hover:text-destructive absolute right-4 top-4"
                    title="Sign out"
                  >
                    <LogOut className="h-4 w-4" />
                  </Button>
                </div>
                
                <CardTitle className="text-xl truncate pr-8">
                  {userProfile?.name || userProfile?.email || "My Account"}
                </CardTitle>
                <CardDescription className="text-xs truncate">
                  {userProfile?.name ? userProfile.email : "Real-time profile vector analysis."}
                </CardDescription>
              </CardHeader>
              <CardContent className="grid gap-3">
                <StatCard 
                  label="Ratings" 
                  value={ratingsCount} 
                  className="rounded-2xl"
                />
                <StatCard 
                  label="Favorites" 
                  value={profileStats?.num_liked ?? 0} 
                  className="rounded-2xl"
                />
                <div className="mt-2 text-center">
                  <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">
                    Last Synced: {profileStats?.updated_at ? formatDate(profileStats.updated_at) : "Never"}
                  </p>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

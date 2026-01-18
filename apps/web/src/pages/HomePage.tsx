import { useCallback, useEffect, useMemo, useRef } from "react";
import {
  useUserSummary,
  useProfileStats,
  useFeed,
} from "../lib/hooks";
import { ensureLoggedIn, logout } from "../lib/oidc";
import { queryClient } from "../lib/queryClient";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { PageHeader } from "../components/PageHeader";
import { StatCard } from "../components/StatCard";
import { formatDate } from "../lib/utils";
import { Feed } from "../components/Feed";
import {
  LogIn,
  UserPlus,
  Zap,
  User,
  LogOut,
} from "lucide-react";

import { useStore } from "../lib/store";

type HomePageProps = {
  userId: number | null;
  setUserId: (id: number | null) => void;
};

export function HomePage({ userId }: HomePageProps) {
  const { resetSession, userProfile } = useStore();
  
  const feedPageSize = 20;
  
  const feedSentinelRef = useRef<HTMLDivElement | null>(null);
  const feedObserverRef = useRef<IntersectionObserver | null>(null);

  const { data: userSummary, error: summaryError } = useUserSummary(userId);
  const { data: profileStats } = useProfileStats(userId);
  
  const {
    data: feed,
    isLoading: feedLoading,
    isFetchingNextPage: feedFetchingNextPage,
    hasNextPage: feedHasNextPage,
    fetchNextPage: fetchNextFeedPage,
  } = useFeed(userId, feedPageSize);

  const feedItems = useMemo(
    () => feed?.pages.flatMap((page) => page.items) ?? [],
    [feed]
  );

  const setupFeedObserver = useCallback(() => {
    const node = feedSentinelRef.current;
    if (!node) return;
    if (feedObserverRef.current) feedObserverRef.current.disconnect();
    
    const observer = new IntersectionObserver(
      (entries) => {
        const [entry] = entries;
        if (!entry.isIntersecting) return;
        if (!feedHasNextPage) return;
        if (feedFetchingNextPage) return;
        fetchNextFeedPage();
      },
      { rootMargin: "50px", threshold: 0.01 }
    );
    feedObserverRef.current = observer;
    observer.observe(node);
  }, [feedHasNextPage, feedFetchingNextPage, fetchNextFeedPage]);

  useEffect(() => {
    setupFeedObserver();
    return () => {
      if (feedObserverRef.current) feedObserverRef.current.disconnect();
    };
  }, [setupFeedObserver]);

  const setFeedSentinel = useCallback((node: HTMLDivElement | null) => {
    feedSentinelRef.current = node;
    if (node) {
      setupFeedObserver();
    } else if (feedObserverRef.current) {
      feedObserverRef.current.disconnect();
      feedObserverRef.current = null;
    }
  }, [setupFeedObserver]);

  const ratingsCount = userSummary?.num_ratings
    ?? profileStats?.num_ratings
    ?? 0;
  
  const gridClass = "grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-x-4 gap-y-8";

  return (
    <div className="space-y-8 max-w-[1600px] mx-auto px-4 md:px-8 py-6">
      <PageHeader
        title="Top Picks"
        subtitle="Recommended for you"
        userId={userId}
      />

      <div className="grid gap-8 lg:grid-cols-[1fr_300px]">
        <div className="space-y-8 order-2 lg:order-1">
          <Feed
            feed={feedItems}
            loading={feedLoading}
            gridClass={gridClass}
            isFetchingMore={feedFetchingNextPage}
            hasMore={feedHasNextPage}
            sentinelRef={setFeedSentinel}
          />
        </div>

        <div className="space-y-6 order-1 lg:order-2">
          {!userId ? (
            <Card className="border-primary/10 bg-primary/[0.02] shadow-sm rounded-2xl overflow-hidden">
              <CardHeader className="pb-4">
                <div className="flex items-center gap-2 text-primary mb-1">
                  <Zap className="h-4 w-4 fill-primary" />
                  <span className="text-[10px] font-bold uppercase tracking-wider">Session</span>
                </div>
                <CardTitle className="text-lg">Sign in</CardTitle>
                <CardDescription className="text-xs">Save your taste profile.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <Button
                  onClick={() => ensureLoggedIn({ action: "login" })}
                  className="w-full h-9 rounded-lg gap-2 font-semibold shadow-sm"
                >
                  <LogIn className="h-4 w-4" />
                  Login
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => ensureLoggedIn({ action: "register" })}
                  className="w-full h-9 rounded-lg gap-2 font-semibold"
                >
                  <UserPlus className="h-4 w-4" />
                  Sign Up
                </Button>
                {summaryError && (
                  <p className="text-[11px] font-medium text-destructive bg-destructive/5 p-2 rounded-lg border border-destructive/10 text-center">
                    Authentication failed.
                  </p>
                )}
              </CardContent>
            </Card>
          ) : (
            <Card className="border-border/40 shadow-sm rounded-2xl overflow-hidden bg-card/50 backdrop-blur-sm">
              <CardHeader className="pb-4 relative">
                <div className="flex items-center justify-between">
                   <div className="flex items-center gap-2 text-muted-foreground mb-1">
                    <User className="h-4 w-4" />
                    <span className="text-[10px] font-bold uppercase tracking-wider">Profile</span>
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
                
                <CardTitle className="text-base truncate pr-8">
                  {userProfile?.name || userProfile?.email || "My Account"}
                </CardTitle>
              </CardHeader>
              <CardContent className="grid gap-3">
                <StatCard 
                  label="Ratings" 
                  value={ratingsCount} 
                  className="rounded-xl"
                />
                <div className="mt-2 text-center">
                  <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-widest">
                    Updated: {profileStats?.updated_at ? formatDate(profileStats.updated_at) : "Never"}
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

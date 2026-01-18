import { useCallback, useEffect, useMemo, useRef } from "react";
import { useFeed } from "../lib/hooks";
import { Feed } from "../components/Feed";


type HomePageProps = {
  userId: number | null;
  setUserId: (id: number | null) => void;
};

export function HomePage({ userId }: HomePageProps) {
  const feedPageSize = 20;
  
  const feedSentinelRef = useRef<HTMLDivElement | null>(null);
  const feedObserverRef = useRef<IntersectionObserver | null>(null);

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

  const gridClass = "grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-x-4 gap-y-8";

  return (
    <div className="space-y-8 max-w-[1600px] mx-auto px-4 md:px-8 py-6">

      <div className="space-y-8">
        <Feed
          feed={feedItems}
          loading={feedLoading}
          gridClass={gridClass}
          isFetchingMore={feedFetchingNextPage}
          hasMore={feedHasNextPage}
          sentinelRef={setFeedSentinel}
        />
      </div>
    </div>
  );
}

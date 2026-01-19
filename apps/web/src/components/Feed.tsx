import type { Ref } from "react";

import { MovieCard } from "./MovieCard";
import { EmptyState } from "./EmptyState";
import { Skeleton } from "./ui/skeleton";
import { formatDate } from "../lib/utils";
import type { FeedItem } from "../lib/api";

type FeedProps = {
  feed: FeedItem[];
  loading: boolean;
  gridClass: string;
  isFetchingMore?: boolean;
  hasMore?: boolean;
  sentinelRef?: Ref<HTMLDivElement>;
};

export function Feed({
  feed,
  loading,
  gridClass,
  isFetchingMore,
  hasMore,
  sentinelRef,
}: FeedProps) {
  if (loading && !feed.length) {
    return (
      <div className="space-y-6">
        <div className={gridClass}>
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Skeleton key={i} className="aspect-[2/3] w-full rounded-md" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {feed.length ? (
        <div className="space-y-8">
          <div className={gridClass}>
            {feed.map((item) => (
              <MovieCard
                key={item.id}
                title={item.title}
                releaseDateLabel={item.release_date ? formatDate(item.release_date) : null}
                genres={item.genres}
                imageUrl={item.poster_url ?? item.backdrop_url}
                to={`/movie/${item.id}`}
                similarity={item.similarity}
              />
            ))}
          </div>

          {isFetchingMore && (
            <div className={gridClass}>
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="aspect-[2/3] w-full rounded-md" />
              ))}
            </div>
          )}

          {hasMore && (
            <div
              ref={sentinelRef}
              className="mt-8 flex h-24 items-center justify-center border-t border-border/20"
            >
              <div className="flex items-center gap-3 text-muted-foreground animate-pulse">
                <div className="flex gap-1">
                  <div className="h-1.5 w-1.5 rounded-full bg-primary animate-bounce [animation-delay:-0.3s]" />
                  <div className="h-1.5 w-1.5 rounded-full bg-primary animate-bounce [animation-delay:-0.15s]" />
                  <div className="h-1.5 w-1.5 rounded-full bg-primary animate-bounce" />
                </div>
                <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-primary/70">
                  Loading...
                </span>
              </div>
            </div>
          )}
        </div>
      ) : (
        <EmptyState title="Start your feed" description="Rate a few movies to get recommendations." />
      )}
    </div>
  );
}

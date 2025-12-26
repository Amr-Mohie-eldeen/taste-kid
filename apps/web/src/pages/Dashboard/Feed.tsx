import { MovieCard } from "../../components/MovieCard";
import { EmptyState } from "../../components/EmptyState";
import { Skeleton } from "../../components/ui/skeleton";
import { SectionHeader } from "../../components/SectionHeader";
import { formatDate } from "../../lib/utils";
import { FeedItem } from "../../lib/api";

type FeedProps = {
  feed: FeedItem[];
  posterMap: Record<number, string | null>;
  loading: boolean;
  gridClass: string;
  isFetchingMore?: boolean;
  hasMore?: boolean;
  sentinelRef?: React.RefObject<HTMLDivElement>;
};

export function Feed({ 
  feed, 
  posterMap, 
  loading, 
  gridClass,
  isFetchingMore,
  hasMore,
  sentinelRef
}: FeedProps) {
  if (loading && !feed.length) {
    return (
      <div className="space-y-6">
        <SectionHeader title="Your Intelligence Feed" subtitle="Synthesizing recommendations based on your unique profile." />
        <div className={gridClass}>
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Skeleton key={i} className="h-[280px] w-full rounded-2xl" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <SectionHeader 
        title="Your Intelligence Feed" 
        subtitle="Synthesizing recommendations based on your unique profile." 
      />
      
      {feed.length ? (
        <div className="space-y-8">
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

          {isFetchingMore && (
            <div className={gridClass}>
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-[280px] w-full rounded-2xl" />
              ))}
            </div>
          )}
          
          {hasMore && (
            <div ref={sentinelRef} className="h-20 flex items-center justify-center">
              <div className="flex items-center gap-2 text-muted-foreground animate-pulse">
                <div className="h-1.5 w-1.5 rounded-full bg-primary" />
                <span className="text-[10px] font-bold uppercase tracking-[0.2em]">Expanding Feed</span>
              </div>
            </div>
          )}
        </div>
      ) : (
        <EmptyState
          title="Intelligence Engine Idle"
          description="Contribute ratings to activate your personalized intelligence feed."
        />
      )}
    </div>
  );
}

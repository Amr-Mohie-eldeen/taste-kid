import { MovieCard } from "../../components/MovieCard";
import { EmptyState } from "../../components/EmptyState";
import { Skeleton } from "../../components/ui/skeleton";
import { SectionHeader } from "../../components/SectionHeader";
import { formatDate } from "../../lib/utils";
import { FeedItem } from "../../lib/api";

type FeedProps = {
  feed: FeedItem[];
  loading: boolean;
  gridClass: string;
  isFetchingMore?: boolean;
  hasMore?: boolean;
  sentinelRef?: React.Ref<HTMLDivElement>;
};

export function Feed({ 
  feed, 
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
                imageUrl={item.poster_url ?? item.backdrop_url}
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
            <div ref={sentinelRef} className="h-24 flex items-center justify-center border-t border-border/20 mt-8">
              <div className="flex items-center gap-3 text-muted-foreground animate-pulse">
                <div className="flex gap-1">
                  <div className="h-1.5 w-1.5 rounded-full bg-primary animate-bounce [animation-delay:-0.3s]" />
                  <div className="h-1.5 w-1.5 rounded-full bg-primary animate-bounce [animation-delay:-0.15s]" />
                  <div className="h-1.5 w-1.5 rounded-full bg-primary animate-bounce" />
                </div>
                <span className="text-[10px] font-black uppercase tracking-[0.3em] text-primary">Expanding Feed Architecture</span>
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

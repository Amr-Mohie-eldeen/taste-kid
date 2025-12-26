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
};

export function Feed({ feed, posterMap, loading, gridClass }: FeedProps) {
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
          title="Intelligence Engine Idle"
          description="Contribute ratings to activate your personalized intelligence feed."
        />
      )}
    </div>
  );
}
import { MovieCard } from "../../components/MovieCard";
import { EmptyState } from "../../components/EmptyState";
import { Skeleton } from "../../components/ui/skeleton";
import { SectionHeader } from "../../components/SectionHeader";
import { formatDate } from "../../lib/utils";
import { Recommendation } from "../../lib/api";

type RecommendationsProps = {
  recommendations: Recommendation[];
  posterMap: Record<number, string | null>;
  loading: boolean;
  gridClass: string;
  isFetchingMore: boolean;
  hasMoreRecommendations: boolean;
  recommendationSentinel: React.RefObject<HTMLDivElement>;
};

export function Recommendations({
  recommendations,
  posterMap,
  loading,
  gridClass,
  isFetchingMore,
  hasMoreRecommendations,
  recommendationSentinel,
}: RecommendationsProps) {
  if (loading && !recommendations.length) {
    return (
      <div className="space-y-6">
        <SectionHeader 
          title="Predictive Discovery" 
          subtitle="Advanced vector matching to identify hidden cinematic patterns." 
        />
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
        title="Predictive Discovery" 
        subtitle="Advanced vector matching to identify hidden cinematic patterns." 
      />
      
      {recommendations.length ? (
        <div className="space-y-8">
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
          
          {isFetchingMore && (
            <div className={gridClass}>
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-[280px] w-full rounded-2xl" />
              ))}
            </div>
          )}
          
          {hasMoreRecommendations && (
            <div ref={recommendationSentinel} className="h-20 flex items-center justify-center">
              <div className="flex items-center gap-2 text-muted-foreground animate-pulse">
                <div className="h-1.5 w-1.5 rounded-full bg-primary" />
                <span className="text-[10px] font-bold uppercase tracking-[0.2em]">Expanding Results</span>
              </div>
            </div>
          )}
        </div>
      ) : (
        <EmptyState 
          title="Predictor Uninitialized" 
          description="Contribute more data to enable high-confidence predictive matching." 
        />
      )}
    </div>
  );
}
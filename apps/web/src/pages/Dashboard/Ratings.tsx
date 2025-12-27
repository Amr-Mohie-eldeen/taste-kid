import { MovieCard } from "../../components/MovieCard";
import { EmptyState } from "../../components/EmptyState";
import { Skeleton } from "../../components/ui/skeleton";
import { SectionHeader } from "../../components/SectionHeader";
import { formatDate } from "../../lib/utils";
import { RatedMovie } from "../../lib/api";

type RatingsProps = {
  ratings: RatedMovie[];
  loading: boolean;
  gridClass: string;
};

export function Ratings({ ratings, loading, gridClass }: RatingsProps) {
  const watchedRatings = ratings.filter((item) => item.status === "watched");

  if (loading && !ratings.length) {
    return (
      <div className="space-y-6">
        <SectionHeader 
          title="Rating Repository" 
          subtitle="Your historical interaction and preference database." 
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
        title="Rating Repository" 
        subtitle="Your historical interaction and preference database." 
      />
      
      {watchedRatings.length ? (
        <div className={gridClass}>
          {watchedRatings.map((item) => (
            <MovieCard
              key={item.id}
              title={item.title}
              subtitle={item.updated_at ? `Synchronized ${formatDate(item.updated_at)}` : null}
              meta={[`Score: ${item.rating ?? "-"}`]}
              imageUrl={item.poster_url ?? item.backdrop_url}
              to={`/movie/${item.id}`}
            />
          ))}
        </div>
      ) : (
        <EmptyState 
          title="Database Empty" 
          description="Your cinematic history is unrecorded. Start rating to build your profile." 
        />
      )}
    </div>
  );
}

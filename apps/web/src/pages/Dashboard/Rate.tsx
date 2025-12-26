import { Link } from "react-router-dom";
import { Button } from "../../components/ui/button";
import { Card, CardContent } from "../../components/ui/card";
import { Separator } from "../../components/ui/separator";
import { Skeleton } from "../../components/ui/skeleton";
import { EmptyState } from "../../components/EmptyState";
import { MovieCard } from "../../components/MovieCard";
import { PosterImage } from "../../components/PosterImage";
import { SectionHeader } from "../../components/SectionHeader";
import { NextMovie, RatingQueueItem } from "../../lib/api";
import { formatDate } from "../../lib/utils";
import { Layers } from "lucide-react";

type RateProps = {
  nextMovie: NextMovie | null;
  ratingQueue: RatingQueueItem[];
  posterMap: Record<number, string | null>;
  loading: boolean;
  onRateMovie: (movieId: number, rating: number | null, status: string) => void;
};

export function Rate({ nextMovie, ratingQueue, posterMap, loading, onRateMovie }: RateProps) {
  const nextPoster = nextMovie ? posterMap[nextMovie.id] : null;

  return (
    <div className="space-y-10">
      <div className="space-y-6">
        <SectionHeader 
          title="Active Sampling" 
          subtitle="Refine your taste profile by rating these curated selections." 
        />
        
        <div className="min-h-[320px]">
          {loading && !nextMovie ? (
            <Skeleton className="h-[320px] w-full rounded-3xl" />
          ) : nextMovie ? (
            <div key={nextMovie.id} className="swap-fade">
              <MovieCard
                title={nextMovie.title}
                releaseDateLabel={nextMovie.release_date ? formatDate(nextMovie.release_date) : null}
                genres={nextMovie.genres}
                imageUrl={nextPoster}
                layout="row"
                imageClassName="sm:w-48 sm:aspect-[2/3]"
                cardClassName="border-primary/10 bg-primary/[0.01] rounded-3xl p-2"
                actions={
                  <div className="flex flex-col gap-4 w-full mt-2">
                    <div className="flex flex-wrap gap-2">
                      {[5, 4, 3, 2, 1].map((rating) => (
                        <Button
                          key={rating}
                          variant="outline"
                          className="h-10 w-10 sm:h-12 sm:w-12 rounded-xl border-border/60 hover:border-primary hover:text-primary transition-all font-bold"
                          onClick={() => onRateMovie(nextMovie.id, rating, "watched")}
                        >
                          {rating}
                        </Button>
                      ))}
                    </div>
                    <div className="flex items-center gap-3">
                      <Button
                        variant="secondary"
                        className="rounded-xl px-6 font-bold text-xs uppercase tracking-wider"
                        onClick={() => onRateMovie(nextMovie.id, null, "unwatched")}
                      >
                        Skip for now
                      </Button>
                      <Button variant="ghost" className="rounded-xl px-6 font-bold text-xs uppercase tracking-wider" asChild>
                        <Link to={`/movie/${nextMovie.id}`}>Inspect Metadata</Link>
                      </Button>
                    </div>
                  </div>
                }
              />
            </div>
          ) : (
            <EmptyState 
              title="Pipeline Exhausted" 
              description="You have completed all active sampling tasks. Check discovery for more."
            />
          )}
        </div>
      </div>

      <Separator className="opacity-50" />

      <div className="space-y-6">
        <div className="flex items-center gap-2 text-muted-foreground mb-4">
          <Layers className="h-4 w-4" />
          <h4 className="text-sm font-bold uppercase tracking-widest">Sampling Queue</h4>
        </div>
        
        {loading && !ratingQueue.length ? (
          <Skeleton className="h-24 w-full rounded-2xl" />
        ) : ratingQueue.length ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {ratingQueue.slice(0, 6).map((item) => (
              <div key={item.id} className="group relative aspect-[16/9] overflow-hidden rounded-2xl border border-border/40 bg-muted/30">
                {posterMap[item.id] ? (
                  <PosterImage
                    src={posterMap[item.id] ?? ""}
                    alt={item.title ?? "Movie"}
                    className="opacity-60 transition-all duration-500 group-hover:scale-110 group-hover:opacity-100"
                  />
                ) : null}
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent p-4 flex flex-col justify-end">
                  <p className="text-xs font-bold text-white line-clamp-1">{item.title}</p>
                </div>
              </div>
            ))}
            {ratingQueue.length > 6 && (
              <div className="flex items-center justify-center rounded-2xl border border-dashed border-border bg-muted/10 p-4">
                <p className="text-xs font-bold text-muted-foreground uppercase tracking-widest">+{ratingQueue.length - 6} More queued</p>
              </div>
            )}
          </div>
        ) : (
          <EmptyState title="Queue Empty" description="Your selection queue is currently unpopulated." />
        )}
      </div>
    </div>
  );
}
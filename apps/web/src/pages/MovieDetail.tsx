import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  api,
  type MovieDetail as MovieDetailType,
  type SimilarMovie,
} from "../lib/api";
import { Button } from "../components/ui/button";
import { Card, CardContent } from "../components/ui/card";
import { Separator } from "../components/ui/separator";
import { Skeleton } from "../components/ui/skeleton";
import { EmptyState } from "../components/EmptyState";
import { MovieCard } from "../components/MovieCard";
import { PosterImage } from "../components/PosterImage";
import { SectionHeader } from "../components/SectionHeader";

const formatDate = (value?: string | null) => {
  if (!value) return "-";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleDateString();
};


type MovieDetailProps = {
  userId: number | null;
};

export function MovieDetail({ userId }: MovieDetailProps) {
  const { movieId } = useParams();
  const navigate = useNavigate();
  const [detail, setDetail] = useState<MovieDetailType | null>(null);
  const [similar, setSimilar] = useState<SimilarMovie[]>([]);
  const [posterMap, setPosterMap] = useState<Record<number, string | null>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [ratingStatus, setRatingStatus] = useState<string | null>(null);

  const id = Number(movieId);

  useEffect(() => {
    if (!Number.isFinite(id)) {
      setError("Invalid movie id.");
      setLoading(false);
      return;
    }
    window.scrollTo({ top: 0, behavior: "smooth" });
    setLoading(true);
    setError(null);
    setRatingStatus(null);
    const load = async () => {
      try {
        const [detailResponse, similarResponse] = await Promise.all([
          api.getMovieDetail(id),
          api.getSimilar(id),
        ]);
        setDetail(detailResponse);
        setSimilar(similarResponse);
        await hydratePosters(similarResponse.map((item) => item.id));
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unable to load movie");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [id]);

  const hydratePosters = async (ids: number[]) => {
    const missing = ids.filter((movie) => !(movie in posterMap));
    if (!missing.length) return;
    const results = await Promise.all(
      missing.map((movie) => api.getMovieDetail(movie).catch(() => null))
    );
    setPosterMap((prev) => {
      const next = { ...prev };
      results.forEach((movie, index) => {
        const movieId = missing[index];
        next[movieId] = movie?.poster_url ?? movie?.backdrop_url ?? null;
      });
      return next;
    });
  };

  const handleRate = async (rating: number | null, status: string) => {
    if (!userId || !detail) {
      setRatingStatus("Select a profile first on the dashboard.");
      return;
    }
    try {
      await api.rateMovie(userId, detail.id, rating, status);
      setRatingStatus("Rating saved.");
    } catch (err) {
      setRatingStatus(err instanceof Error ? err.message : "Failed to rate movie");
    }
  };

  const meta = useMemo(() => {
    if (!detail) return [] as string[];
    const list: string[] = [];
    if (detail.release_date) list.push(`Release ${formatDate(detail.release_date)}`);
    if (detail.runtime) list.push(`${detail.runtime} min`);
    if (detail.vote_average)
      list.push(`${detail.vote_average.toFixed(1)} / 10 (${detail.vote_count})`);
    if (detail.original_language) list.push(detail.original_language.toUpperCase());
    return list;
  }, [detail]);

  if (loading) {
    return (
      <div className="grid gap-8 lg:grid-cols-[1fr_1.2fr]">
        <Skeleton className="aspect-[2/3] w-full rounded-2xl" />
        <div className="space-y-4">
          <Skeleton className="h-10 w-2/3" />
          <Skeleton className="h-4 w-1/2" />
          <Skeleton className="h-24" />
          <Skeleton className="h-12 w-1/3" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <EmptyState title="Unable to load" description={error} />
        <Button className="mt-6" onClick={() => navigate("/")}>Back</Button>
      </div>
    );
  }

  if (!detail) return null;

  return (
    <div className="space-y-10">
      <div className="flex items-center justify-between">
        <Link className="text-sm text-muted-foreground hover:text-foreground" to="/">
          ← Back to dashboard
        </Link>
      </div>

      <div className="grid gap-8 lg:grid-cols-[1fr_1.2fr]">
        <Card className="overflow-hidden">
          <CardContent className="p-6">
            <div className="aspect-[2/3] w-full overflow-hidden rounded-2xl bg-muted">
              {detail.poster_url || detail.backdrop_url ? (
                <PosterImage
                  src={detail.poster_url ?? detail.backdrop_url ?? ""}
                  alt={detail.title ?? "Movie"}
                />
              ) : (
                <div className="flex h-full items-center justify-center bg-gradient-to-br from-slate-200 to-slate-100 text-xs text-muted-foreground">
                  No poster
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        <div className="space-y-5">
          <div>
            <h1 className="text-3xl font-semibold text-foreground">{detail.title}</h1>
            {detail.tagline ? (
              <p className="mt-1 text-sm text-muted-foreground">{detail.tagline}</p>
            ) : null}
          </div>
          <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
            {meta.map((item) => (
              <span key={item}>{item}</span>
            ))}
          </div>
          <p className="text-sm text-muted-foreground">{detail.overview}</p>

          <Separator />
          <SectionHeader title="Rate this movie" />
          <div className="flex flex-wrap gap-2">
            {[5, 4, 3, 2, 1].map((rating) => (
              <Button
                key={rating}
                size="sm"
                variant="outline"
                onClick={() => handleRate(rating, "watched")}
              >
                {rating}★
              </Button>
            ))}
            <Button size="sm" variant="ghost" onClick={() => handleRate(null, "unwatched")}>
              Mark as unwatched
            </Button>
          </div>
          {ratingStatus ? <p className="text-sm text-primary">{ratingStatus}</p> : null}
        </div>
      </div>

      <div className="space-y-4">
        <SectionHeader title="Similar picks" />
        {similar.length ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {similar.map((item) => (
              <MovieCard
                key={item.id}
                title={item.title}
                releaseDateLabel={item.release_date ? formatDate(item.release_date) : null}
                genres={item.genres}
                imageUrl={posterMap[item.id]}
                to={`/movie/${item.id}`}
                similarity={item.score}
              />
            ))}
          </div>
        ) : (
          <EmptyState title="No similar movies" />
        )}
      </div>
    </div>
  );
}

import { useState } from "react";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Separator } from "../../components/ui/separator";
import { Skeleton } from "../../components/ui/skeleton";
import { EmptyState } from "../../components/EmptyState";
import { MovieCard } from "../../components/MovieCard";
import { SectionHeader } from "../../components/SectionHeader";
import { MovieDetail, SimilarMovie } from "../../lib/api";
import { formatDate } from "../../lib/utils";
import { Search as SearchIcon } from "lucide-react";

type SearchProps = {
  onSearch: (query: string) => void;
  searchLoading: boolean;
  searchError: string | null;
  searchedMovie: MovieDetail | null;
  similarMovies: SimilarMovie[];
  gridClass: string;
};

export function Search({
  onSearch,
  searchLoading,
  searchError,
  searchedMovie,
  similarMovies,
  gridClass,
}: SearchProps) {
  const [searchQuery, setSearchQuery] = useState("");

  const handleSearch = () => {
    if (!searchQuery.trim()) return;
    onSearch(searchQuery.trim());
  };

  return (
    <div className="space-y-10">
      <div className="space-y-6">
        <SectionHeader 
          title="Vector Lookup" 
          subtitle="Query the global cinematic database using semantic search." 
        />
        
        <div className="relative group max-w-2xl">
          <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none text-muted-foreground group-focus-within:text-primary transition-colors">
            <SearchIcon className="h-5 w-5" />
          </div>
          <div className="flex gap-3">
            <Input
              value={searchQuery}
              placeholder="Search by cinematic title..."
              className="pl-12 h-12 rounded-2xl bg-secondary/30 border-border/40 focus-visible:ring-primary/20"
              onChange={(event) => setSearchQuery(event.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            />
            <Button 
              disabled={!searchQuery.trim() || searchLoading} 
              onClick={handleSearch}
              className="h-12 px-8 rounded-2xl font-bold shadow-lg shadow-primary/10"
            >
              {searchLoading ? "Analyzing..." : "Search"}
            </Button>
          </div>
        </div>
        
        {searchError && (
          <p className="text-[11px] font-medium text-destructive bg-destructive/5 p-3 rounded-xl border border-destructive/10">
            {searchError}
          </p>
        )}

        <div className="mt-8">
          {searchLoading ? (
            <Skeleton className="h-[200px] w-full rounded-3xl" />
          ) : searchedMovie ? (
            <div className="swap-fade">
              <MovieCard
                title={searchedMovie.title}
                subtitle={searchedMovie.tagline}
                releaseDateLabel={
                  searchedMovie.release_date ? formatDate(searchedMovie.release_date) : null
                }
                genres={searchedMovie.genres}
                description={searchedMovie.overview}
                imageUrl={searchedMovie.poster_url || searchedMovie.backdrop_url}
                to={`/movie/${searchedMovie.id}`}
                layout="row"
                imageClassName="sm:w-48 sm:aspect-[2/3]"
                cardClassName="bg-primary/[0.02] border-primary/10 rounded-3xl p-2"
              />
            </div>
          ) : null}
        </div>
      </div>

      {(searchedMovie || similarMovies.length > 0) && (
        <>
          <Separator className="opacity-50" />
          <div className="space-y-6">
            <SectionHeader 
              title="Semantic Proxies" 
              subtitle="Movies sharing high-dimensional vector space coordinates." 
            />
            
            {searchLoading ? (
              <div className={gridClass}>
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-[280px] w-full rounded-2xl" />
                ))}
              </div>
            ) : similarMovies.length ? (
              <div className={gridClass}>
                {similarMovies.map((item) => (
                  <MovieCard
                    key={item.id}
                    title={item.title}
                    releaseDateLabel={item.release_date ? formatDate(item.release_date) : null}
                    genres={item.genres}
                    imageUrl={item.poster_url ?? item.backdrop_url}
                    to={`/movie/${item.id}`}
                    similarity={item.score}
                  />
                ))}
              </div>
            ) : (
              <EmptyState title="No Proxies Found" description="The vector space search returned no significant matches." />
            )}
          </div>
        </>
      )}
    </div>
  );
}

import { useState, useEffect } from "react";
import { useMovieSearch } from "../lib/hooks";
import { MovieCard } from "../components/MovieCard";
import { Input } from "../components/ui/input";
import { Search as SearchIcon, Loader2, Sparkles } from "lucide-react";
import { cn } from "../lib/utils";
import { PosterImage } from "../components/PosterImage";

export function SearchPage() {
  const [query, setQuery] = useState("");
  const [activeSearch, setActiveSearch] = useState("");

  useEffect(() => {
    const timer = setTimeout(() => {
        if (query.trim()) {
            setActiveSearch(query);
        }
    }, 600);
    return () => clearTimeout(timer);
  }, [query]);

  const { data, isLoading, isError } = useMovieSearch(activeSearch, !!activeSearch);

  const hasResults = !!data;
  const showHero = !hasResults && !isLoading && !activeSearch;

  return (
    <div className="min-h-full flex flex-col p-6 md:p-12 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-transparent to-background/80 pointer-events-none" />
        <div className="absolute -top-40 -right-40 w-96 h-96 bg-primary/10 rounded-full blur-3xl opacity-50 pointer-events-none" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-primary/5 rounded-full blur-[120px] opacity-30 pointer-events-none" />

      <div className={cn(
          "w-full max-w-3xl mx-auto transition-all duration-700 ease-in-out z-10 flex flex-col items-center text-foreground",
          showHero ? "mt-[20vh]" : "mt-0"
      )}>
        <h1 className={cn(
            "text-4xl md:text-6xl font-bold tracking-tighter text-center mb-6 text-foreground transition-all duration-700",
            showHero ? "opacity-100 translate-y-0" : "opacity-0 -translate-y-10 absolute pointer-events-none"
        )}>
          Explore the Unknown
        </h1>
        
         <p className={cn(
             "text-lg text-muted-foreground text-center mb-12 max-w-lg transition-all duration-700 delay-100", 

            showHero ? "opacity-100 translate-y-0" : "opacity-0 -translate-y-10 absolute pointer-events-none"
        )}>
          Enter a movie you love. We'll find what you should watch next based on your taste.
        </p>

        <div className="relative w-full group">
          <div className="absolute inset-0 bg-primary/20 blur-xl rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
          <div className="relative flex items-center">
            <SearchIcon className="absolute left-4 w-5 h-5 text-muted-foreground group-focus-within:text-primary transition-colors duration-300" />
            <Input 
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Star Wars, Inception, Parasite..." 
                 className="h-14 pl-12 pr-4 rounded-2xl bg-secondary/20 border border-border/60 hover:bg-secondary/30 focus:bg-secondary/20 focus:border-primary/30 focus-visible:ring-4 focus-visible:ring-primary/15 transition-all duration-300 text-lg shadow-sm text-foreground placeholder:text-muted-foreground"
            />
             {isLoading && (
                <div className="absolute right-4 animate-spin text-primary">
                    <Loader2 className="w-5 h-5" />
                </div>
            )}
          </div>
        </div>
      </div>

      <div className={cn(
          "w-full max-w-7xl mx-auto mt-12 transition-all duration-1000 delay-300",
          (hasResults || isLoading) ? "opacity-100 translate-y-0" : "opacity-0 translate-y-20 pointer-events-none"
      )}>
        {isError && (
             <div className="text-center p-12 text-muted-foreground">
                <p>We couldn't find that movie. Try another title.</p>
            </div>
        )}

        {data && (
            <div className="space-y-12">
                <div className="flex flex-col md:flex-row gap-8 items-start bg-secondary/20 p-6 rounded-3xl border border-white/5 backdrop-blur-sm">
                     <div className="w-32 md:w-48 shrink-0 rounded-xl overflow-hidden shadow-2xl rotate-[-2deg] border-4 border-background/50">
                        {data.detail.poster_url ? (
                            <PosterImage src={data.detail.poster_url} alt={data.detail.title} className="w-full h-auto" />
                        ) : (
                             <div className="aspect-[2/3] bg-zinc-800 flex items-center justify-center text-zinc-600 font-bold">No Image</div>
                        )}
                    </div>
                    <div className="flex-1 space-y-4">
                        <div className="flex items-center gap-2">
                             <span className="bg-primary/10 text-primary text-xs font-bold px-2 py-1 rounded-full uppercase tracking-widest flex items-center gap-1">
                                <Sparkles className="w-3 h-3" /> Seed Movie
                             </span>
                        </div>
                        <h2 className="text-3xl font-bold">{data.detail.title}</h2>
                        <p className="text-muted-foreground leading-relaxed max-w-2xl">{data.detail.overview}</p>
                        <div className="flex gap-2 flex-wrap">
                            {data.detail.genres?.split(',').map(g => (
                                <span key={g} className="text-xs bg-secondary px-2 py-1 rounded-md text-secondary-foreground">{g.trim()}</span>
                            ))}
                        </div>
                    </div>
                </div>

                <div>
                     <h3 className="text-xl font-semibold mb-6 flex items-center gap-2">
                        Because you liked <span className="text-primary">{data.detail.title}</span>
                     </h3>
                    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-x-4 gap-y-8">
                        {data.similar.map((movie) => (
                            <MovieCard
                                key={movie.id}
                                title={movie.title}
                                releaseDateLabel={movie.release_date}
                                imageUrl={movie.poster_url}
                                to={`/movie/${movie.id}`}
                                similarity={movie.score}
                            />
                        ))}
                    </div>
                </div>
            </div>
        )}
      </div>
    </div>
  );
}

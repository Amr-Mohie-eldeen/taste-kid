import { Link } from "react-router-dom";
import { useStore } from "../lib/store";
import { Sparkles, User, ShieldCheck, Activity } from "lucide-react";
import { cn } from "../lib/utils";

export function NavBar() {
  const { userId, apiStatus } = useStore();

  return (
    <nav className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/80 backdrop-blur-xl">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 h-16 sm:px-6 lg:px-8">
        <Link to="/" className="flex items-center gap-2.5 group">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary shadow-[0_0_20px_-5px_rgba(59,130,246,0.5)] group-hover:scale-105 transition-transform duration-300">
            <Sparkles className="h-5 w-5 text-white" />
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-bold tracking-tight text-foreground leading-none">Taste.io</span>
            <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider mt-0.5">Studio</span>
          </div>
        </Link>

        <div className="flex items-center gap-4">
          <div className={cn(
            "hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full border text-[11px] font-semibold transition-colors duration-300",
            apiStatus === "online" ? "bg-emerald-500/5 border-emerald-500/20 text-emerald-600" : 
            apiStatus === "offline" ? "bg-red-500/5 border-red-500/20 text-red-600" :
            "bg-amber-500/5 border-amber-500/20 text-amber-600"
          )}>
            <Activity className="h-3 w-3" />
            <span className="uppercase tracking-wide">{apiStatus === "online" ? "Systems Active" : apiStatus === "offline" ? "System Offline" : "Syncing..."}</span>
          </div>

          <div className="h-8 w-px bg-border/60" />

          <div className="flex items-center gap-3">
            {userId ? (
              <div className="flex items-center gap-2.5 pl-1 pr-3 py-1 rounded-full bg-secondary/50 border border-border/50">
                <div className="h-7 w-7 rounded-full bg-primary/10 flex items-center justify-center text-primary">
                  <ShieldCheck className="h-4 w-4" />
                </div>
                <span className="text-xs font-bold text-foreground">ID: {userId}</span>
              </div>
            ) : (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-secondary/50 border border-border/50 text-muted-foreground">
                <User className="h-3.5 w-3.5" />
                <span className="text-[11px] font-bold uppercase tracking-wider">Guest Session</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}

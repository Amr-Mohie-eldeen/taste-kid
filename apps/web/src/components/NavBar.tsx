import { Link } from "react-router-dom";
import { LogOut, ShieldCheck, Sparkles } from "lucide-react";
import { useStore } from "../lib/store";
import { Button } from "./ui/button";
import { ensureLoggedIn } from "../lib/oidc";

export function NavBar() {
  const { userId, userProfile } = useStore();

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
          <div className="flex items-center gap-3">
            {userId ? (
              <div className="flex items-center gap-2 rounded-full bg-secondary/50 border border-border/50 pl-1 pr-1 py-1">
                <div className="h-7 w-7 rounded-full bg-primary/10 flex items-center justify-center text-primary">
                  <ShieldCheck className="h-4 w-4" />
                </div>
                <span className="text-xs font-bold text-foreground pr-2">
                  {userProfile?.name || userProfile?.email || "My Account"}
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  asChild
                  className="h-8 px-2 rounded-full text-muted-foreground hover:text-destructive"
                  title="Sign out"
                >
                  <Link to="/#signout">
                    <LogOut className="h-4 w-4" />
                  </Link>
                </Button>
              </div>
            ) : (
              <Button
                size="sm"
                onClick={() => ensureLoggedIn({ action: "login" })}
                className="rounded-full font-bold px-5"
              >
                Sign In
              </Button>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}

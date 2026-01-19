import { Badge } from "./ui/badge";
import { Sparkles } from "lucide-react";

type PageHeaderProps = {
  title: string;
  subtitle?: string;
  status?: string;
  userId?: number | null;
};

export function PageHeader({ title, subtitle, userId }: PageHeaderProps) {
  return (
    <header className="relative overflow-hidden rounded-3xl bg-card/60 backdrop-blur-xl border border-border/50 p-8 shadow-[0_8px_30px_rgb(0,0,0,0.25)]">
      {/* Abstract Background Element */}
      <div className="absolute -right-20 -top-20 h-64 w-64 rounded-full bg-primary/5 blur-3xl" />
      <div className="absolute -left-20 -bottom-20 h-64 w-64 rounded-full bg-primary/5 blur-3xl" />
      
        <div className="relative z-10 flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between text-foreground">
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-primary">
            <Sparkles className="h-4 w-4" />
            <span className="text-[10px] font-bold uppercase tracking-[0.2em]">Curated</span>
          </div>
          <h1 className="text-4xl font-extrabold tracking-tight text-foreground sm:text-5xl">
            {title}
          </h1>
          {subtitle ? (
            <p className="max-w-2xl text-base font-medium text-muted-foreground/80 leading-relaxed">
              {subtitle}
            </p>
          ) : (
            <p className="max-w-2xl text-base font-medium text-muted-foreground/80 leading-relaxed">
              A clean, personal space for discovering what to watch next.
            </p>
          )}
        </div>
        
        {userId && (
          <div className="flex shrink-0">
            <div className="flex items-center gap-3 rounded-2xl bg-secondary/50 border border-border/50 p-4">
              <div className="h-10 w-10 rounded-xl bg-primary/10 flex items-center justify-center text-primary">
                <span className="text-xs font-bold">U</span>
              </div>
              <div className="flex flex-col">
                <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Account</span>
                <span className="text-sm font-bold text-foreground">Signed in</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </header>
  );
}
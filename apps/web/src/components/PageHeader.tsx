import { Badge } from "./ui/badge";

type PageHeaderProps = {
  title: string;
  subtitle?: string;
  status?: string;
  userId?: number | null;
};

export function PageHeader({ title, subtitle, status, userId }: PageHeaderProps) {
  return (
    <header className="flex flex-col gap-4 rounded-3xl border border-border/70 bg-white/70 p-6 shadow-soft sm:flex-row sm:items-center sm:justify-between">
      <div>
        <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">taste-kid</p>
        <h1 className="text-3xl font-semibold text-foreground">{title}</h1>
        {subtitle ? <p className="text-sm text-muted-foreground">{subtitle}</p> : null}
      </div>
      <div className="flex items-center gap-3">
        {status ? <Badge variant="secondary">API {status}</Badge> : null}
        {userId ? <Badge>User #{userId}</Badge> : null}
      </div>
    </header>
  );
}

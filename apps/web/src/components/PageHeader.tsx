import { Badge } from "./ui/badge";

type PageHeaderProps = {
  title: string;
  subtitle?: string;
  status?: string;
  userId?: number | null;
};

export function PageHeader({ title, subtitle, status, userId }: PageHeaderProps) {
  return (
    <header className="flex flex-col gap-6 rounded-2xl bg-white/50 p-6 shadow-soft sm:flex-row sm:items-center sm:justify-between">
      <div>
        <p className="text-xs uppercase tracking-widest text-muted-foreground/80">taste-kid</p>
        <h1 className="text-4xl font-medium text-foreground">{title}</h1>
        {subtitle ? <p className="text-muted-foreground">{subtitle}</p> : null}
      </div>
      <div className="flex shrink-0 items-center gap-3">
        {status ? (
          <Badge
            variant="secondary"
            className="border-transparent bg-green-100 text-green-800"
          >
            API {status}
          </Badge>
        ) : null}
        {userId ? <Badge>User #{userId}</Badge> : null}
      </div>
    </header>
  );
}

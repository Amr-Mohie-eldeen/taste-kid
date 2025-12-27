import { Card, CardContent } from "./ui/card";
import { cn } from "../lib/utils";

type StatCardProps = {
  label: string;
  value: string | number | null | undefined;
  hint?: string;
  className?: string;
};

export function StatCard({ label, value, hint, className }: StatCardProps) {
  return (
    <Card className={cn("overflow-hidden border-border/40 bg-white/50 backdrop-blur-sm shadow-sm", className)}>
      <CardContent className="p-5">
        <div className="flex flex-col space-y-1">
          <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground/70">
            {label}
          </span>
          <div className="flex items-baseline gap-1">
            <span className="text-2xl font-black tracking-tight text-foreground">
              {value ?? "-"}
            </span>
            {hint && (
              <span className="text-[10px] font-medium text-muted-foreground">
                {hint}
              </span>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
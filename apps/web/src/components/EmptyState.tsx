import { Card, CardContent } from "./ui/card";
import { Inbox } from "lucide-react";

type EmptyStateProps = {
  title: string;
  description?: string;
};

export function EmptyState({ title, description }: EmptyStateProps) {
  return (
    <Card className="border-dashed border-2 border-border/40 bg-muted/10">
      <CardContent className="py-16 flex flex-col items-center text-center">
        <div className="h-12 w-12 rounded-2xl bg-secondary flex items-center justify-center mb-4 text-muted-foreground/60">
          <Inbox className="h-6 w-6" />
        </div>
        <h4 className="text-lg font-black tracking-tight text-foreground">{title}</h4>
        {description && (
          <p className="mt-2 text-sm font-medium text-muted-foreground/70 max-w-[280px]">
            {description}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
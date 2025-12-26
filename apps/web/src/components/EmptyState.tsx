import { Card, CardContent } from "./ui/card";

type EmptyStateProps = {
  title: string;
  description?: string;
};

export function EmptyState({ title, description }: EmptyStateProps) {
  return (
    <Card className="border-dashed bg-surface/40">
      <CardContent className="py-10 text-center">
        <p className="text-base font-semibold text-foreground">{title}</p>
        {description ? <p className="mt-2 text-sm text-muted-foreground">{description}</p> : null}
      </CardContent>
    </Card>
  );
}

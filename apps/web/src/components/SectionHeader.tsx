type SectionHeaderProps = {
  title: string;
  subtitle?: string;
};

export function SectionHeader({ title, subtitle }: SectionHeaderProps) {
  return (
    <div className="flex flex-col space-y-1 mb-6">
      <h3 className="text-xl font-black tracking-tight text-foreground">{title}</h3>
      {subtitle && (
        <p className="text-sm font-medium text-muted-foreground/80 leading-relaxed">
          {subtitle}
        </p>
      )}
      <div className="h-1 w-12 bg-primary rounded-full mt-2" />
    </div>
  );
}
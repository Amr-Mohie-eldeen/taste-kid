import { useState } from "react";
import { cn } from "../lib/utils";

type PosterImageProps = {
  src: string;
  alt: string;
  className?: string;
};

export function PosterImage({ src, alt, className }: PosterImageProps) {
  const [loaded, setLoaded] = useState(false);

  return (
    <div className="relative h-full w-full overflow-hidden">
      <div className="absolute inset-0 animate-pulse bg-muted" />
      <img
        src={src}
        alt={alt}
        loading="lazy"
        onLoad={() => setLoaded(true)}
        className={cn(
          "relative h-full w-full object-cover transition-opacity duration-500 ease-out",
          loaded ? "opacity-100" : "opacity-0",
          className
        )}
      />
    </div>
  );
}

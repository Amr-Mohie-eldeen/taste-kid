import { Link } from "react-router-dom";

export function NavBar() {
  return (
    <div className="sticky top-0 z-30 border-b border-border/70 bg-white/70 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link to="/" className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-2xl bg-primary text-white shadow-sm">
            tk
          </div>
          <div>
            <p className="text-sm font-semibold text-foreground">Taste.io</p>
            <p className="text-xs text-muted-foreground">Taste intelligence</p>
          </div>
        </Link>
        <div className="text-xs text-muted-foreground">Sleek, adaptive, personal.</div>
      </div>
    </div>
  );
}

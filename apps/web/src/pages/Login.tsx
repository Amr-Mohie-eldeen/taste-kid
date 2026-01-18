import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { ensureLoggedIn } from "../lib/oidc";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";

export function Login() {
  const location = useLocation();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const to = params.get("to");
    if (to) {
      navigate(to, { replace: true });
    }
  }, [location.search, navigate]);

  const onLogin = async () => {
    setError(null);
    setLoading(true);
    try {
      await ensureLoggedIn({ action: "login" });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Login failed");
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-64px)] px-4 py-10">
      <div className="mx-auto w-full max-w-[980px]">
        <div className="grid items-stretch gap-6 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="relative overflow-hidden rounded-3xl border border-border/60 bg-gradient-to-br from-slate-50 via-white to-slate-100 p-8 shadow-sm">
            <div className="absolute inset-0 opacity-[0.35] [background:radial-gradient(circle_at_20%_10%,rgba(14,165,233,0.18),transparent_55%),radial-gradient(circle_at_80%_40%,rgba(16,185,129,0.16),transparent_55%),radial-gradient(circle_at_40%_90%,rgba(244,63,94,0.10),transparent_60%)]" />
            <div className="relative space-y-5">
              <div className="space-y-2">
                <p className="text-[11px] font-bold uppercase tracking-[0.24em] text-muted-foreground">
                  Taste-Kid Identity
                </p>
                <h1 className="text-3xl font-semibold tracking-tight">Welcome back</h1>
                <p className="text-sm text-muted-foreground">
                  Sign in with your identity provider to unlock your personal feed, ratings history, and taste metrics.
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <Button
                  onClick={onLogin}
                  disabled={loading}
                  className="h-11 rounded-2xl px-5 font-bold"
                >
                  {loading ? "Redirecting…" : "Continue to Login"}
                </Button>
                <Button
                  variant="secondary"
                  asChild
                  className="h-11 rounded-2xl px-5 font-bold"
                >
                  <Link to="/signup">Create account</Link>
                </Button>
              </div>

              {error && (
                <div className="rounded-2xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive">
                  {error}
                </div>
              )}

              <div className="pt-2 text-xs text-muted-foreground">
                By continuing, you agree to authenticate via the configured provider.
              </div>
            </div>
          </div>

          <Card className="rounded-3xl border-border/60 shadow-sm">
            <CardHeader>
              <CardTitle className="text-lg">What you get</CardTitle>
              <CardDescription className="text-xs">
                Fast, secure access with refresh handled by the provider.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div className="rounded-2xl border border-border/60 bg-secondary/20 p-4">
                <p className="font-semibold">Personalized feed</p>
                <p className="text-xs text-muted-foreground">Recommendations tuned by your ratings and dislikes.</p>
              </div>
              <div className="rounded-2xl border border-border/60 bg-secondary/20 p-4">
                <p className="font-semibold">Taste metrics</p>
                <p className="text-xs text-muted-foreground">Profile vector norms, liked patterns, and recency.</p>
              </div>
              <div className="rounded-2xl border border-border/60 bg-secondary/20 p-4">
                <p className="font-semibold">Session security</p>
                <p className="text-xs text-muted-foreground">Short-lived access tokens, auto refresh, no manual password UI.</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

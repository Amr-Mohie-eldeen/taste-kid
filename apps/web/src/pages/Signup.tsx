import { useState } from "react";
import { Link } from "react-router-dom";
import { ensureLoggedIn } from "../lib/oidc";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";

export function Signup() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSignup = async () => {
    setError(null);
    setLoading(true);
    try {
      await ensureLoggedIn();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Signup failed");
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-64px)] px-4 py-10">
      <div className="mx-auto w-full max-w-[980px]">
        <div className="grid items-stretch gap-6 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="relative overflow-hidden rounded-3xl border border-border/60 bg-gradient-to-br from-emerald-50 via-white to-slate-50 p-8 shadow-sm">
            <div className="absolute inset-0 opacity-[0.35] [background:radial-gradient(circle_at_25%_15%,rgba(16,185,129,0.20),transparent_55%),radial-gradient(circle_at_75%_25%,rgba(59,130,246,0.14),transparent_55%),radial-gradient(circle_at_30%_85%,rgba(244,63,94,0.10),transparent_60%)]" />
            <div className="relative space-y-5">
              <div className="space-y-2">
                <p className="text-[11px] font-bold uppercase tracking-[0.24em] text-muted-foreground">
                  Taste-Kid Identity
                </p>
                <h1 className="text-3xl font-semibold tracking-tight">Create your account</h1>
                <p className="text-sm text-muted-foreground">
                  Sign up through the identity provider. You’ll be redirected back ready to start rating.
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <Button
                  onClick={onSignup}
                  disabled={loading}
                  className="h-11 rounded-2xl px-5 font-bold"
                >
                  {loading ? "Redirecting…" : "Continue to Signup"}
                </Button>
                <Button
                  variant="secondary"
                  asChild
                  className="h-11 rounded-2xl px-5 font-bold"
                >
                  <Link to="/login">I already have an account</Link>
                </Button>
              </div>

              {error && (
                <div className="rounded-2xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive">
                  {error}
                </div>
              )}

              <div className="pt-2 text-xs text-muted-foreground">
                Your email and profile are managed by the provider.
              </div>
            </div>
          </div>

          <Card className="rounded-3xl border-border/60 shadow-sm">
            <CardHeader>
              <CardTitle className="text-lg">Next steps</CardTitle>
              <CardDescription className="text-xs">
                After signup, you can start building your taste profile immediately.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div className="rounded-2xl border border-border/60 bg-secondary/20 p-4">
                <p className="font-semibold">Rate a few movies</p>
                <p className="text-xs text-muted-foreground">The model learns fast from a handful of signals.</p>
              </div>
              <div className="rounded-2xl border border-border/60 bg-secondary/20 p-4">
                <p className="font-semibold">See your feed adapt</p>
                <p className="text-xs text-muted-foreground">Dislikes refine results just as much as likes.</p>
              </div>
              <div className="rounded-2xl border border-border/60 bg-secondary/20 p-4">
                <p className="font-semibold">Own your identity</p>
                <p className="text-xs text-muted-foreground">Identity and sessions stay with the provider.</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

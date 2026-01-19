import { Link, useNavigate } from "react-router-dom";
import { LogOut, User as UserIcon } from "lucide-react";

import { useProfileStats, useUserSummary } from "../lib/hooks";
import { useStore } from "../lib/store";
import { queryClient } from "../lib/queryClient";
import { ensureLoggedIn, logout } from "../lib/oidc";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { StatCard } from "../components/StatCard";

export function ProfilePage() {
  const navigate = useNavigate();
  const { userId, userProfile, resetSession } = useStore();

  const { data: summary } = useUserSummary(userId);
  const { data: stats } = useProfileStats(userId);

  if (!userId) {
    return (
      <div className="mx-auto flex min-h-[70vh] w-full max-w-2xl flex-col items-center justify-center px-6 text-center">
        <div className="mb-6 flex h-14 w-14 items-center justify-center rounded-2xl bg-secondary/50">
          <UserIcon className="h-7 w-7 text-muted-foreground" />
        </div>
        <h1 className="text-3xl font-semibold tracking-tight">Your profile</h1>
        <p className="mt-2 text-muted-foreground">
          Sign in to save your ratings and keep your recommendations in sync.
        </p>
        <div className="mt-6 flex w-full max-w-sm gap-3">
           <Button className="w-full" onClick={() => void ensureLoggedIn({ action: "login" })}>
             Sign in
           </Button>
           <Button
             variant="secondary"
             className="w-full"
             onClick={() => void ensureLoggedIn({ action: "register" })}
           >
             Create account
           </Button>
        </div>
      </div>
    );
  }

  const displayName =
    userProfile?.name || userProfile?.preferred_username || userProfile?.email || "Account";
  const email = userProfile?.email ?? "";

  return (
    <div className="mx-auto w-full max-w-5xl p-6 md:p-12">
      <div className="mb-8 flex items-center justify-between">
        <div className="space-y-1">
          <h1 className="text-3xl font-semibold tracking-tight">Profile</h1>
          <p className="text-muted-foreground">Account details and quick stats.</p>
        </div>
          <Button
            variant="outline"
            className="gap-2"
            onClick={async () => {
              resetSession();
              queryClient.clear();
              try {
                await logout({ redirectTo: "home" });
              } catch {
              }
              navigate("/login", { replace: true });
              window.location.reload();
            }}
          >
          <LogOut className="h-4 w-4" />
          Sign out
        </Button>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
        <div className="space-y-6">
          <Card className="bg-card/60 backdrop-blur-sm">
            <CardHeader>
              <CardTitle>Overview</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-3">
              <div className="rounded-xl border border-border/50 bg-secondary/20 p-4">
                <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Name
                </div>
                <div className="mt-1 text-lg font-semibold">{displayName}</div>
              </div>
              {email ? (
                <div className="rounded-xl border border-border/50 bg-secondary/20 p-4">
                  <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Email
                  </div>
                  <div className="mt-1 text-sm text-foreground/90">{email}</div>
                </div>
              ) : null}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card className="bg-card/60 backdrop-blur-sm">
            <CardHeader>
              <CardTitle>Stats</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-3">
              <StatCard label="Ratings" value={summary?.num_ratings ?? stats?.num_ratings ?? 0} />
              <StatCard label="Favorites" value={stats?.num_liked ?? 0} />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

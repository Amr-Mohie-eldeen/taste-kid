import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useNavigate, Link } from "react-router-dom";
import { Loader2, Film } from "lucide-react";
import { api } from "../lib/api";

import { useStore } from "../lib/store";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { cn } from "../lib/utils";

const loginSchema = z.object({
  email: z.string().email("Please enter a valid email"),
  password: z.string().min(1, "Password is required"),
});

type LoginForm = z.infer<typeof loginSchema>;

export function Login() {
  const navigate = useNavigate();
  const { setToken, setUserId, setUserProfile, setApiStatus } = useStore();
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginForm) => {
    setError(null);
    try {
      const response = await api.login(data.email, data.password);

      setToken(response.access_token);
      setUserId(response.user.id);
      setUserProfile(null);
      setApiStatus("online");

      navigate("/");
    } catch (e) {
      console.error(e);
      setError(e instanceof Error ? e.message : "Invalid email or password");
    }
  };

  return (
    <div className="flex min-h-screen w-full">
      <div className="hidden w-1/2 flex-col justify-between bg-zinc-900 p-12 text-white lg:flex relative overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-indigo-500/30 via-zinc-900/0 to-zinc-900/0" />
        <div className="absolute inset-0 bg-[url('https://images.unsplash.com/photo-1626814026160-2237a95fc5a0?q=80&w=2940&auto=format&fit=crop')] bg-cover bg-center opacity-10 mix-blend-overlay" />
        
        <div className="relative z-10">
          <div className="flex items-center gap-2 text-lg font-bold tracking-tight">
            <Film className="h-6 w-6" />
            <span>Taste-Kid</span>
          </div>
        </div>

        <div className="relative z-10 max-w-md space-y-4">
          <h1 className="text-4xl font-medium tracking-tight font-serif text-zinc-100">
            Cinematic Intelligence.
          </h1>
          <p className="text-lg text-zinc-400 font-light leading-relaxed">
            Discover your next favorite film with recommendations tuned to your taste.
            Designed for those who crave more than just "popular now".
          </p>
        </div>

        <div className="relative z-10 text-sm text-zinc-600">
          &copy; 2026 Taste-Kid. All rights reserved.
        </div>
      </div>

      <div className="flex flex-1 flex-col items-center justify-center bg-background px-4 sm:px-12 lg:px-24">
        <div className="w-full max-w-sm space-y-8">
          <div className="space-y-2 text-center lg:text-left">
            <h2 className="text-3xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
              Welcome back
            </h2>
            <p className="text-sm text-zinc-500 dark:text-zinc-400">
              Enter your credentials to access your dashboard.
            </p>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="space-y-2">
              <label className="text-xs font-medium uppercase tracking-wider text-zinc-500" htmlFor="email">
                Email
              </label>
              <Input
                id="email"
                placeholder="name@example.com"
                type="email"
                autoCapitalize="none"
                autoComplete="email"
                autoCorrect="off"
                disabled={isSubmitting}
                 className={cn(
                   "h-11 bg-background",
                   errors.email && "border-red-500 focus-visible:ring-red-500"
                 )}
                {...register("email")}
              />
              {errors.email && (
                <p className="text-xs text-red-500">{errors.email.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-xs font-medium uppercase tracking-wider text-zinc-500" htmlFor="password">
                  Password
                </label>
                <Link 
                  to="/forgot-password" 
                  className="text-xs text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-50"
                >
                  Forgot?
                </Link>
              </div>
              <Input
                id="password"
                placeholder="••••••••"
                type="password"
                autoComplete="current-password"
                disabled={isSubmitting}
                 className={cn(
                   "h-11 bg-background",
                   errors.password && "border-red-500 focus-visible:ring-red-500"
                 )}
                {...register("password")}
              />
              {errors.password && (
                <p className="text-xs text-red-500">{errors.password.message}</p>
              )}
            </div>

            {error && (
              <div className="rounded-md bg-red-50 p-3 text-sm text-red-600 dark:bg-red-950/50 dark:text-red-400">
                {error}
              </div>
            )}

            <Button
              type="submit"
              disabled={isSubmitting}
              className="h-11 w-full rounded-full bg-zinc-900 text-zinc-50 hover:bg-zinc-800 dark:bg-zinc-50 dark:text-zinc-900 dark:hover:bg-zinc-200"
            >
              {isSubmitting ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                "Sign In"
              )}
            </Button>
          </form>

          <div className="text-center text-sm text-zinc-500">
            Don't have an account?{" "}
            <Link 
              to="/signup" 
              className="font-medium text-zinc-900 hover:underline dark:text-zinc-50"
            >
              Sign up
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

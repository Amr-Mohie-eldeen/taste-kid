import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Link } from "react-router-dom";
import { Loader2, Film } from "lucide-react";
import { api } from "../lib/api";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { cn } from "../lib/utils";

const signupSchema = z
  .object({
    name: z.string().min(2, "Name must be at least 2 characters"),
    email: z.string().email("Please enter a valid email"),
    password: z.string().min(8, "Password must be at least 8 characters"),
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
  });

type SignupForm = z.infer<typeof signupSchema>;

export function Signup() {
  const [success, setSuccess] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<SignupForm>({
    resolver: zodResolver(signupSchema),
  });

  const onSubmit = async (data: SignupForm) => {
    setSuccess(true);
    await api.register(data.email, data.password, data.name);
  };

  if (success) {
    return (
      <div className="flex min-h-screen w-full flex-col items-center justify-center bg-background p-4 text-center">
        <div className="flex max-w-md flex-col items-center space-y-4">
          <Loader2 className="h-5 w-5 animate-spin text-zinc-400" />
          <p className="text-zinc-500 dark:text-zinc-400">Redirecting to Keycloak registration...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen w-full">
      <div className="hidden w-1/2 flex-col justify-between bg-zinc-900 p-12 text-white lg:flex relative overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-emerald-500/20 via-zinc-900/0 to-zinc-900/0" />
        <div className="absolute inset-0 bg-[url('https://images.unsplash.com/photo-1536440136628-849c177e76a1?q=80&w=2825&auto=format&fit=crop')] bg-cover bg-center opacity-10 mix-blend-overlay" />

        <div className="relative z-10">
          <div className="flex items-center gap-2 text-lg font-bold tracking-tight">
            <Film className="h-6 w-6" />
            <span>Taste-Kid</span>
          </div>
        </div>

        <div className="relative z-10 max-w-md space-y-4">
          <h1 className="text-4xl font-medium tracking-tight font-serif text-zinc-100">
            Join the Community.
          </h1>
          <p className="text-lg text-zinc-400 font-light leading-relaxed">
            Start building your taste profile today. Rate movies, get personalized recommendations, and discover hidden gems.
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
              Create an account
            </h2>
            <p className="text-sm text-zinc-500 dark:text-zinc-400">
              Enter your details to get started.
            </p>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="space-y-2">
              <label className="text-xs font-medium uppercase tracking-wider text-zinc-500" htmlFor="name">
                Full Name
              </label>
              <Input
                id="name"
                placeholder="John Doe"
                type="text"
                autoComplete="name"
                disabled={isSubmitting}
                className={cn(
                  "h-11 bg-background",
                  errors.name && "border-red-500 focus-visible:ring-red-500"
                )}
                {...register("name")}
              />
              {errors.name && (
                <p className="text-xs text-red-500">{errors.name.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <label className="text-xs font-medium uppercase tracking-wider text-zinc-500" htmlFor="email">
                Email
              </label>
              <Input
                id="email"
                placeholder="name@example.com"
                type="email"
                autoComplete="email"
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
              <label className="text-xs font-medium uppercase tracking-wider text-zinc-500" htmlFor="password">
                Password
              </label>
              <Input
                id="password"
                placeholder="Min. 8 characters"
                type="password"
                autoComplete="new-password"
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

            <div className="space-y-2">
              <label className="text-xs font-medium uppercase tracking-wider text-zinc-500" htmlFor="confirmPassword">
                Confirm Password
              </label>
              <Input
                id="confirmPassword"
                placeholder="Confirm password"
                type="password"
                autoComplete="new-password"
                disabled={isSubmitting}
                className={cn(
                  "h-11 bg-background",
                  errors.confirmPassword && "border-red-500 focus-visible:ring-red-500"
                )}
                {...register("confirmPassword")}
              />
              {errors.confirmPassword && (
                <p className="text-xs text-red-500">{errors.confirmPassword.message}</p>
              )}
            </div>

            <Button
              type="submit"
              disabled={isSubmitting}
              className="h-11 w-full rounded-full bg-zinc-900 text-zinc-50 hover:bg-zinc-800 dark:bg-zinc-50 dark:text-zinc-900 dark:hover:bg-zinc-200"
            >
              {isSubmitting ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                "Create Account"
              )}
            </Button>
          </form>

          <div className="text-center text-sm text-zinc-500">
            Already have an account?{" "}
            <Link 
              to="/login" 
              className="font-medium text-zinc-900 hover:underline dark:text-zinc-50"
            >
              Sign in
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

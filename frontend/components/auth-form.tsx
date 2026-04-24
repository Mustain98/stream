"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { api } from "../lib/api";
import { useSession } from "./session-provider";

type AuthFormProps = {
  mode: "login" | "signup";
};

export function AuthForm({ mode }: AuthFormProps) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const router = useRouter();
  const params = useSearchParams();
  const { signIn, user, isLoading } = useSession();

  const nextPath = params.get("next") || "/";

  useEffect(() => {
    if (!isLoading && user) {
      router.replace(nextPath);
    }
  }, [isLoading, nextPath, router, user]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      const response =
        mode === "login"
          ? await api.login(username, password)
          : await api.signup(username, password);
      await signIn(response.access_token);
      router.replace(nextPath);
    } catch (submissionError) {
      const message =
        submissionError instanceof Error ? submissionError.message : "Unable to continue";
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="auth-layout">
      <div className="auth-panel auth-copy">
        <p className="eyebrow">Live room access</p>
        <h1>{mode === "login" ? "Step back into the control room." : "Open your channel."}</h1>
        <p className="muted">
          Authenticate once, browse every live room, and jump into the stream experience without
          juggling links by hand.
        </p>
      </div>
      <form className="auth-panel auth-form" onSubmit={handleSubmit}>
        <label className="field">
          <span>Username</span>
          <input
            autoComplete="username"
            onChange={(event) => setUsername(event.target.value)}
            required
            value={username}
          />
        </label>
        <label className="field">
          <span>Password</span>
          <input
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            minLength={4}
            onChange={(event) => setPassword(event.target.value)}
            required
            type="password"
            value={password}
          />
        </label>
        {error ? <p className="error-banner">{error}</p> : null}
        <button className="primary-button" disabled={isSubmitting} type="submit">
          {isSubmitting
            ? "Working..."
            : mode === "login"
              ? "Log in to continue"
              : "Create account"}
        </button>
        <p className="muted fine-print">
          {mode === "login" ? "New here?" : "Already have an account?"}{" "}
          <Link href={mode === "login" ? "/signup" : "/login"}>
            {mode === "login" ? "Create one" : "Log in"}
          </Link>
        </p>
      </form>
    </section>
  );
}

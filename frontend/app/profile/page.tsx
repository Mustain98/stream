"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";

import { RequireAuth } from "../../components/require-auth";
import { useSession } from "../../components/session-provider";
import { api } from "../../lib/api";

export default function ProfilePage() {
  return (
    <RequireAuth>
      <ProfileContent />
    </RequireAuth>
  );
}

function ProfileContent() {
  const { token, user, refreshUser } = useSession();

  const [email, setEmail] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setEmail(user?.email || "");
  }, [user?.email]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!token) {
      return;
    }

    setIsSaving(true);
    setMessage(null);
    setError(null);

    try {
      await api.updateMe(token, {
        email: email.trim() || null,
      });

      await refreshUser();

      setMessage("Profile updated.");
    } catch (updateError) {
      const errorMessage =
        updateError instanceof Error ? updateError.message : "Failed to update profile";

      setError(errorMessage);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <section className="stack-xl">
      <div className="hero-panel">
        <div>
          <p className="eyebrow">Profile</p>
          <h1>Manage your account info.</h1>
          <p className="muted hero-copy">
            Add an email before connecting Stripe for paid streams.
          </p>
        </div>

        <div className="stat-block">
          <span>Username</span>
          <strong>{user?.username}</strong>
        </div>
      </div>

      <form className="panel stack-md" onSubmit={handleSubmit}>
        <div>
          <p className="eyebrow">Account details</p>
          <h2>Email address</h2>
        </div>

        <label className="field">
          <span>Email</span>
          <input
            type="email"
            value={email}
            placeholder="you@example.com"
            onChange={(event) => setEmail(event.target.value)}
          />
        </label>

        {message ? <p className="success-banner">{message}</p> : null}
        {error ? <p className="error-banner">{error}</p> : null}

        <div className="hero-actions">
          <button className="primary-button" disabled={isSaving} type="submit">
            {isSaving ? "Saving..." : "Save profile"}
          </button>

          <Link className="ghost-button" href="/dashboard/stripe">
            Go to Stripe setup
          </Link>
        </div>
      </form>
    </section>
  );
}
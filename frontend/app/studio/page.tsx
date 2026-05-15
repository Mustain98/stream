"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { LiveStreamCard } from "../../components/live-stream-card";
import { RequireAuth } from "../../components/require-auth";
import { useSession } from "../../components/session-provider";
import { api } from "../../lib/api";
import type { StreamSummary } from "../../lib/types";
import { useStripeConnect } from "../../lib/use-stripe-connect";
import { useUserDashboard } from "../../lib/use-user-dashboard";

export default function StudioPage() {
  return (
    <RequireAuth>
      <StudioContent />
    </RequireAuth>
  );
}

function StudioContent() {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [ownedStreams, setOwnedStreams] = useState<StreamSummary[]>([]);
  const [isLoadingOwned, setIsLoadingOwned] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const router = useRouter();
  const { token, user } = useSession();

  const stripeConnect = useStripeConnect({
    token,
  });
  const userDashboard = useUserDashboard({
    token,
  });

  useEffect(() => {
    if (!token) {
      return;
    }

    const loadOwnedStreams = async () => {
      try {
        const dashboard = await userDashboard.loadDashboard();
        setOwnedStreams(dashboard?.owned_streams ?? []);
      } catch (loadError) {
        const message =
          loadError instanceof Error ? loadError.message : "Failed to load owned streams";
        setError(message);
      } finally {
        setIsLoadingOwned(false);
      }
    };

    void loadOwnedStreams();
    void stripeConnect.loadStatus();
  }, [token, stripeConnect.loadStatus, userDashboard.loadDashboard]);

  const handleCreate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!token) {
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const stream = await api.createStream(token, { title, description });
      setOwnedStreams((current) => [
        {
          id: stream.id,
          title: stream.title,
          description: stream.description,
          status: stream.status,
          broadcaster_id: stream.broadcaster_id,
          started_at: stream.started_at,
          viewer_count: 0,
        },
        ...current,
      ]);
      router.push(`/studio/${stream.id}`);
    } catch (createError) {
      const message = createError instanceof Error ? createError.message : "Failed to create";
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const stripeReady = Boolean(stripeConnect.status?.onboarding_completed);

  return (
    <section className="stack-xl">
      <div className="hero-panel">
        <div>
          <p className="eyebrow">Broadcast studio</p>
          <h1>Set the stage, then go live.</h1>
          <p className="muted hero-copy">
            Create a stream space, launch your camera, and share a live room that instantly appears
            on the homepage.
          </p>
        </div>
        <div className="stat-block">
          <span>Signed in as</span>
          <strong>{user?.username}</strong>
        </div>
      </div>

      <div className="panel stack-md">
        <div>
          <p className="eyebrow">Payments</p>
          <h2>{stripeReady ? "Stripe ready for paid streams" : "Want paid streams?"}</h2>
        </div>

        <p className="muted">
          Stripe is only required if you want to make a stream paid. Free streams do not need
          Stripe setup.
        </p>

        <div className="hero-actions">
          <Link className={stripeReady ? "ghost-button" : "primary-button"} href="/dashboard/stripe">
            {stripeReady ? "Manage Stripe" : "Connect Stripe"}
          </Link>
        </div>
      </div>

      <div className="studio-grid">
        <form className="panel stack-md" onSubmit={handleCreate}>
          <div>
            <p className="eyebrow">Create stream</p>
            <h2>Open a new live room</h2>
          </div>
          <label className="field">
            <span>Title</span>
            <input onChange={(event) => setTitle(event.target.value)} required value={title} />
          </label>
          <label className="field">
            <span>Description</span>
            <textarea
              onChange={(event) => setDescription(event.target.value)}
              required
              rows={5}
              value={description}
            />
          </label>
          {error ? <p className="error-banner">{error}</p> : null}
          <button className="primary-button" disabled={isSubmitting} type="submit">
            {isSubmitting ? "Creating..." : "Create stream"}
          </button>
        </form>

        <div className="panel stack-md">
          <div>
            <p className="eyebrow">Your stream rooms</p>
            <h2>Click a card to reopen your studio</h2>
          </div>
          {isLoadingOwned ? <p className="muted">Loading your streams...</p> : null}
          {!isLoadingOwned && ownedStreams.length === 0 ? (
            <div className="stack-sm">
              <p className="muted">You have not created any stream rooms yet.</p>
              <Link className="ghost-button compact" href="/">
                View live homepage
              </Link>
            </div>
          ) : null}
          {!isLoadingOwned && ownedStreams.length > 0 ? (
            <div className="stream-grid studio-owned-grid">
              {ownedStreams.map((stream) => (
                <LiveStreamCard
                  ctaLabel="Open studio"
                  href={`/studio/${stream.id}`}
                  key={stream.id}
                  stream={stream}
                />
              ))}
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}

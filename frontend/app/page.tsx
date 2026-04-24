"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useSession } from "../components/session-provider";
import { LiveStreamCard } from "../components/live-stream-card";
import { api } from "../lib/api";
import type { StreamSummary } from "../lib/types";

export default function HomePage() {
  const [streams, setStreams] = useState<StreamSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { user } = useSession();

  useEffect(() => {
    const loadStreams = async () => {
      try {
        const liveStreams = await api.getLiveStreams();
        setStreams(
          user ? liveStreams.filter((stream) => stream.broadcaster_id !== user.id) : liveStreams
        );
      } catch (loadError) {
        const message = loadError instanceof Error ? loadError.message : "Failed to load streams";
        setError(message);
      } finally {
        setIsLoading(false);
      }
    };

    void loadStreams();
  }, [user]);

  return (
    <section className="stack-xl">
      <div className="hero-panel">
        <div>
          <p className="eyebrow">Live stream browser</p>
          <h1>Choose a live room and join with one click.</h1>
          <p className="muted hero-copy">
            Every live broadcast surfaces here. Open a stream card, jump into the watch page, and
            let the signaling layer handle the connection details.
          </p>
        </div>
        <div className="hero-actions">
          <Link className="primary-button" href="/studio">
            Open Studio
          </Link>
          <Link className="ghost-button" href="/signup">
            Create account
          </Link>
        </div>
      </div>

      {isLoading ? (
        <section className="center-card">
          <p className="eyebrow">Loading</p>
          <h2>Scanning for live rooms.</h2>
        </section>
      ) : null}

      {error ? (
        <section className="center-card error-surface">
          <p className="eyebrow">Backend unavailable</p>
          <h2>{error}</h2>
          <p className="muted">
            Check that the FastAPI server is running and that `NEXT_PUBLIC_API_BASE_URL` points to
            it.
          </p>
        </section>
      ) : null}

      {!isLoading && !error && streams.length === 0 ? (
        <section className="center-card">
          <p className="eyebrow">Quiet stage</p>
          <h2>No live streams are running right now.</h2>
          <p className="muted">
            Open the studio, start a stream, and this page will immediately become the browse grid
            viewers can click.
          </p>
        </section>
      ) : null}

      {!isLoading && !error && streams.length > 0 ? (
        <section className="stream-grid">
          {streams.map((stream) => (
            <LiveStreamCard key={stream.id} stream={stream} />
          ))}
        </section>
      ) : null}
    </section>
  );
}

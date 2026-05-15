"use client";

import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState, useCallback } from "react";

import { PaymentRequiredOverlay } from "../../../components/payment-required-overlay";
import { RequireAuth } from "../../../components/require-auth";
import { useSession } from "../../../components/session-provider";
import { StreamChatPanel } from "../../../components/stream-chat-panel";
import { isLiveStatus } from "../../../lib/stream-utils";
import { useSfuViewer } from "../../../lib/use-sfu-viewer";
import { useStreamAccess } from "../../../lib/use-stream-access";
import { useStreamRoom } from "../../../lib/use-stream-room";

export default function WatchPage() {
  return (
    <RequireAuth>
      <WatchContent />
    </RequireAuth>
  );
}

function WatchContent() {
  const params = useParams<{ streamId: string }>();
  const streamId = params.streamId;

  const router = useRouter();
  const searchParams = useSearchParams();

  const { token, user } = useSession();

  const videoRef = useRef<HTMLVideoElement | null>(null);

  const [paymentRequired, setPaymentRequired] = useState(false);
  const [isPaying, setIsPaying] = useState(false);
  const [paymentError, setPaymentError] = useState<string | null>(null);
  const [paymentMessage, setPaymentMessage] = useState<string | null>(null);

  const room = useStreamRoom(streamId, token);
  const streamAccess = useStreamAccess({
    token,
    streamId,
  });

  const stream = room.stream;
  const isLive = isLiveStatus(stream?.status);
  const isOwner = Boolean(stream && user && stream.broadcaster_id === user.id);

  const shouldShowPayment =
    paymentRequired || streamAccess.access?.access_mode === "payment_required";

  const canConnectToSfu = Boolean(
    token &&
      stream &&
      user &&
      isLive &&
      !isOwner &&
      streamAccess.access &&
      streamAccess.access.can_watch &&
      !shouldShowPayment
  );

  const handlePaymentRequired = useCallback(() => {
    setPaymentMessage(null);
    setPaymentError(null);
    setPaymentRequired(true);
  }, []);

  const viewer = useSfuViewer({
    token,
    streamId,
    videoRef,
    enabled: canConnectToSfu,
    onPaymentRequired: handlePaymentRequired,
  });

  const viewerCount = isLive ? viewer.viewerCount : room.apiViewerCount;
  const canUseChat = Boolean(
    token &&
      user &&
      stream &&
      isLive &&
      streamAccess.access?.can_watch &&
      !shouldShowPayment &&
      viewer.isConnected
  );

  const chatDisabledReason = (() => {
    if (!isLive) {
      return "Chat opens when the stream goes live.";
    }

    if (shouldShowPayment) {
      return "Unlock the full stream to join the chat.";
    }

    if (!streamAccess.access?.can_watch) {
      return "Stream access is required before you can chat.";
    }

    if (!viewer.isConnected) {
      return "Connecting you to the live room...";
    }

    return "Chat is ready.";
  })();

  const error = room.error || viewer.error || streamAccess.accessError || paymentError;

  const status = (() => {
    if (paymentMessage) {
      return paymentMessage;
    }

    if (!isLive) {
      return "This stream is not live right now.";
    }

    if (shouldShowPayment) {
      return "Payment required to continue watching.";
    }

    if (streamAccess.access?.access_mode === "preview") {
      return `Preview access. You can watch for ${streamAccess.access.free_preview_seconds} seconds.`;
    }

    return viewer.status;
  })();

  useEffect(() => {
    if (!token) {
      return;
    }

    void streamAccess.loadAccess();
  }, [token, streamAccess.loadAccess]);

  useEffect(() => {
    const paymentStatus = searchParams.get("payment");

    if (!token || paymentStatus !== "success") {
      return;
    }

    let cancelled = false;

    const confirmPayment = async () => {
      setPaymentRequired(false);
      setPaymentError(null);
      setPaymentMessage("Confirming payment...");

      for (let attempt = 1; attempt <= 10; attempt += 1) {
        if (cancelled) {
          return;
        }

        try {
          const latestAccess = await streamAccess.loadAccess();

          if (latestAccess?.access_mode === "paid" || latestAccess?.has_paid) {
            setPaymentRequired(false);
            setPaymentMessage(null);
            return;
          }
        } catch {
          // streamAccess hook already stores error.
        }

        await new Promise((resolve) => setTimeout(resolve, 1500));
      }

      if (!cancelled) {
        setPaymentMessage(
          "Payment is still being confirmed. Refresh in a moment if access does not unlock."
        );
      }
    };

    void confirmPayment();

    return () => {
      cancelled = true;
    };

    // Intentionally only react to payment success URL.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, searchParams]);

  useEffect(() => {
    if (isOwner) {
      router.replace(`/studio/${streamId}`);
    }
  }, [isOwner, router, streamId]);

  useEffect(() => {
    if (!streamAccess.access) {
      return;
    }

    if (streamAccess.access.access_mode === "payment_required") {
      setPaymentRequired(true);
      return;
    }

    setPaymentRequired(false);
  }, [streamAccess.access]);

  const handlePay = async () => {
    if (!token) {
      return;
    }

    setIsPaying(true);
    setPaymentError(null);
    setPaymentMessage(null);

    try {
      const response = await streamAccess.createCheckout();

      if (response?.status === "already_paid") {
        setPaymentRequired(false);
        await streamAccess.loadAccess();
        return;
      }

      if (response?.checkout_url) {
        window.location.href = response.checkout_url;
        return;
      }

      setPaymentError("Checkout URL was not returned.");
    } catch (payError) {
      const message =
        payError instanceof Error ? payError.message : "Failed to open checkout";

      setPaymentError(message);
    } finally {
      setIsPaying(false);
    }
  };

  return (
    <section className="stack-xl">
      <div className="hero-panel">
        <div>
          <p className="eyebrow">Watch</p>
          <h1>{stream?.title || "Opening stream..."}</h1>
          <p className="muted hero-copy">
            {stream?.description || "Waiting for metadata."}
          </p>
        </div>

        <div className="stat-block">
          <span>{isLive ? "Live viewers" : "Viewers"}</span>
          <strong>{viewerCount}</strong>
        </div>
      </div>

      {error ? <p className="error-banner">{error}</p> : null}

      {room.isLoading || streamAccess.isLoadingAccess ? (
        <section className="center-card">
          <p className="eyebrow">Loading</p>
          <h2>Opening stream.</h2>
        </section>
      ) : null}

      {!room.isLoading && stream ? (
        <div className="watch-room-grid">
          <div className="panel stack-md">
            <div className="video-frame">
              <video
                autoPlay
                controls
                playsInline
                ref={videoRef}
                className={shouldShowPayment ? "blurred-video" : ""}
              />

              {viewer.isPaused ? (
                <div className="pause-overlay">
                  <strong>Stream paused</strong>
                </div>
              ) : null}

              {!isLive ? (
                <div className="pause-overlay">
                  <strong>Stream is not live</strong>
                </div>
              ) : null}

              {shouldShowPayment && streamAccess.access ? (
                <PaymentRequiredOverlay
                  priceAmount={streamAccess.access.price_amount}
                  currency={streamAccess.access.currency}
                  isPaying={isPaying}
                  onPay={handlePay}
                />
              ) : null}
            </div>

            <div className="status-bar">
              <span className="status-dot" />
              <span>{status}</span>
            </div>
          </div>

          <StreamChatPanel
            audienceCount={viewerCount}
            canSend={canUseChat}
            currentUserId={user?.id ?? null}
            currentUsername={user?.username ?? null}
            disabledReason={chatDisabledReason}
            heading="Join the room"
            messages={viewer.chatMessages}
            onSend={viewer.sendChat}
            participants={viewer.viewers.map((liveViewer) => ({
              peerId: liveViewer.peerId,
              userId: liveViewer.userId,
              username: liveViewer.username,
              role: "subscriber",
            }))}
          />
        </div>
      ) : null}
    </section>
  );
}

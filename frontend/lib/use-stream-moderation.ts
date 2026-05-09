"use client";

import { useCallback, useState } from "react";

import { api } from "./api";
import type { BlockedUser } from "./types";

type UseStreamModerationOptions = {
  token: string | null;
  streamId: string;
};

export function useStreamModeration({ token, streamId }: UseStreamModerationOptions) {
  const [blockedUsers, setBlockedUsers] = useState<BlockedUser[]>([]);
  const [isLoadingBlockedUsers, setIsLoadingBlockedUsers] = useState(false);
  const [moderationError, setModerationError] = useState<string | null>(null);

  const loadBlockedUsers = useCallback(async () => {
    if (!token) {
      return;
    }

    try {
      setIsLoadingBlockedUsers(true);
      setModerationError(null);

      const response = await api.getBlockedUsers(token, streamId);
      setBlockedUsers(response.blocked_users);
    } catch (loadError) {
      const message =
        loadError instanceof Error ? loadError.message : "Failed to load blocked users";

      setModerationError(message);
    } finally {
      setIsLoadingBlockedUsers(false);
    }
  }, [streamId, token]);

  const blockViewer = useCallback(
    async (userId: string | null, username: string) => {
      if (!token || !userId) {
        return;
      }

      const confirmed = window.confirm(`Block ${username} from this stream?`);

      if (!confirmed) {
        return;
      }

      try {
        setModerationError(null);

        await api.blockViewer(token, streamId, userId, "blocked");

        setBlockedUsers((current) => {
          const alreadyExists = current.some((blocked) => blocked.user_id === userId);

          if (alreadyExists) {
            return current;
          }

          return [
            {
              id: `${streamId}:${userId}`,
              stream_id: streamId,
              user_id: userId,
              username,
              reason: "blocked",
              created_at: new Date().toISOString(),
            },
            ...current,
          ];
        });
      } catch (blockError) {
        const message =
          blockError instanceof Error ? blockError.message : "Failed to block viewer";

        setModerationError(message);
      }
    },
    [streamId, token]
  );

  const unblockViewer = useCallback(
    async (userId: string) => {
      if (!token) {
        return;
      }

      try {
        setModerationError(null);

        await api.unblockViewer(token, streamId, userId);

        setBlockedUsers((current) =>
          current.filter((blocked) => blocked.user_id !== userId)
        );
      } catch (unblockError) {
        const message =
          unblockError instanceof Error ? unblockError.message : "Failed to unblock viewer";

        setModerationError(message);
      }
    },
    [streamId, token]
  );

  return {
    blockedUsers,
    isLoadingBlockedUsers,
    moderationError,
    loadBlockedUsers,
    blockViewer,
    unblockViewer,
  };
}
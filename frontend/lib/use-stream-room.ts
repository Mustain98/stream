"use client";

import { useCallback, useEffect, useState } from "react";

import { api } from "./api";
import { isLiveStatus } from "./stream-utils";
import type { StreamDetailsResponse, StreamRecord } from "./types";

type StreamApiResponse = StreamDetailsResponse | StreamRecord;

function normalizeStreamResponse(response: StreamApiResponse): StreamRecord {
  if (
    response &&
    typeof response === "object" &&
    "stream" in response &&
    response.stream
  ) {
    return response.stream;
  }

  return response as StreamRecord;
}

export function useStreamRoom(streamId: string, token?: string | null) {
  const [stream, setStream] = useState<StreamRecord | null>(null);
  const [apiViewerCount, setApiViewerCount] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadApiViewerCount = useCallback(async () => {
    if (!token) {
      setApiViewerCount(0);
      return;
    }

    try {
      const response = await api.getViewerCount(token, streamId);
      setApiViewerCount(response.viewer_count);
    } catch {
      setApiViewerCount(0);
    }
  }, [streamId, token]);

  const refresh = useCallback(async () => {
    try {
      setError(null);

      const response = await api.getStream(streamId);
      const loadedStream = normalizeStreamResponse(response as StreamApiResponse);

      if (!loadedStream || !loadedStream.status) {
        throw new Error("Invalid stream response from backend");
      }

      setStream(loadedStream);

      if (!isLiveStatus(loadedStream.status)) {
        await loadApiViewerCount();
      } else {
        setApiViewerCount(0);
      }
    } catch (loadError) {
      const message =
        loadError instanceof Error ? loadError.message : "Failed to load stream";

      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [streamId, loadApiViewerCount]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return {
    stream,
    setStream,
    apiViewerCount,
    loadApiViewerCount,
    isLoading,
    error,
    setError,
    refresh,
  };
}

export function isLiveStatus(status?: string | null) {
  return status?.toLowerCase() === "live";
}

export function isEndedStatus(status?: string | null) {
  return status?.toLowerCase() === "ended";
}

export function formatStreamStatus(status?: string | null) {
  if (!status) {
    return "Unknown";
  }

  const normalized = status.toLowerCase();

  if (normalized === "live") {
    return "Live";
  }

  if (normalized === "ended") {
    return "Ended";
  }

  if (normalized === "offline") {
    return "Offline";
  }

  return status;
}
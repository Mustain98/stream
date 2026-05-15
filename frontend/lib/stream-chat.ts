import type { ChatMentionUser, StreamChatMessage } from "./types";

const MAX_CHAT_MESSAGES = 150;

export function appendChatMessage(
  messages: StreamChatMessage[],
  nextMessage: StreamChatMessage
) {
  return [...messages, nextMessage].slice(-MAX_CHAT_MESSAGES);
}

export function buildMentionableUsers(
  participants: ChatMentionUser[],
  messages: StreamChatMessage[],
  currentUserId?: string | null,
  currentUsername?: string | null
) {
  const users = new Map<string, ChatMentionUser>();

  const addUser = (user?: ChatMentionUser | null) => {
    if (!user?.username) {
      return;
    }

    if (currentUserId && user.userId && user.userId === currentUserId) {
      return;
    }

    if (currentUsername && user.username.toLowerCase() === currentUsername.toLowerCase()) {
      return;
    }

    const key = user.username.toLowerCase();
    const existing = users.get(key);

    if (!existing) {
      users.set(key, user);
      return;
    }

    users.set(key, {
      peerId: existing.peerId || user.peerId,
      userId: existing.userId || user.userId,
      username: existing.username || user.username,
      role: existing.role || user.role,
    });
  };

  participants.forEach(addUser);

  messages.forEach((message) => {
    addUser({
      peerId: message.peerId,
      userId: message.userId,
      username: message.username,
      role: message.role,
    });

    message.mentions.forEach(addUser);
  });

  return Array.from(users.values()).sort((left, right) => {
    if (left.role === "publisher" && right.role !== "publisher") {
      return -1;
    }

    if (left.role !== "publisher" && right.role === "publisher") {
      return 1;
    }

    return left.username.localeCompare(right.username);
  });
}

export function getActiveMention(value: string, caret: number) {
  const prefix = value.slice(0, caret);
  const match = /(?:^|\s)@([a-zA-Z0-9_]*)$/.exec(prefix);

  if (!match) {
    return null;
  }

  return {
    query: match[1] ?? "",
    start: caret - (match[1]?.length ?? 0) - 1,
    end: caret,
  };
}

export function applyMention(
  value: string,
  selectionStart: number,
  selectionEnd: number,
  username: string
) {
  const before = value.slice(0, selectionStart);
  const after = value.slice(selectionEnd);
  const replacement = `@${username}`;
  const suffix = after.startsWith(" ") || after.length === 0 ? "" : " ";
  const nextValue = `${before}${replacement}${suffix}${after}`;
  const nextCaret = before.length + replacement.length + suffix.length;

  return {
    nextValue,
    nextCaret,
  };
}

export function isOwnChatMessage(
  message: StreamChatMessage,
  currentUserId?: string | null,
  currentUsername?: string | null
) {
  if (currentUserId && message.userId) {
    return message.userId === currentUserId;
  }

  if (currentUsername) {
    return message.username.toLowerCase() === currentUsername.toLowerCase();
  }

  return false;
}

export function messageMentionsUser(
  message: StreamChatMessage,
  currentUserId?: string | null,
  currentUsername?: string | null
) {
  const normalizedUsername = currentUsername?.toLowerCase();

  const matchesMentionPayload = message.mentions.some((mention) => {
    if (currentUserId && mention.userId) {
      return mention.userId === currentUserId;
    }

    if (normalizedUsername) {
      return mention.username.toLowerCase() === normalizedUsername;
    }

    return false;
  });

  if (matchesMentionPayload) {
    return true;
  }

  if (!normalizedUsername) {
    return false;
  }

  const mentionPattern = new RegExp(`(^|\\s)@${normalizedUsername}(?=\\b)`, "i");
  return mentionPattern.test(message.message);
}

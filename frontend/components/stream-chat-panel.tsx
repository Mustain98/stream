"use client";

import type { ReactNode } from "react";
import { useDeferredValue, useEffect, useRef, useState } from "react";

import {
  applyMention,
  buildMentionableUsers,
  getActiveMention,
  isOwnChatMessage,
  messageMentionsUser,
} from "../lib/stream-chat";
import type { ChatMentionUser, StreamChatMessage } from "../lib/types";

const MAX_DRAFT_LENGTH = 280;

type StreamChatPanelProps = {
  audienceCount: number;
  canSend: boolean;
  currentUserId: string | null;
  currentUsername: string | null;
  disabledReason: string;
  heading: string;
  messages: StreamChatMessage[];
  onSend: (message: string) => Promise<boolean>;
  participants: ChatMentionUser[];
};

function formatTime(value: string) {
  return new Intl.DateTimeFormat("en-US", {
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

function renderMessageText(message: StreamChatMessage, currentUsername: string | null) {
  const content: ReactNode[] = [];
  const mentionPattern = /@([a-zA-Z0-9_]{1,32})/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = mentionPattern.exec(message.message)) !== null) {
    const [rawMention, username] = match;
    const startIndex = match.index;

    if (startIndex > lastIndex) {
      content.push(message.message.slice(lastIndex, startIndex));
    }

    const isSelfMention =
      Boolean(currentUsername) && username.toLowerCase() === currentUsername?.toLowerCase();

    content.push(
      <span
        key={`${message.id}-${startIndex}`}
        className={isSelfMention ? "chat-mention chat-mention-self" : "chat-mention"}
      >
        {rawMention}
      </span>
    );

    lastIndex = startIndex + rawMention.length;
  }

  if (lastIndex < message.message.length) {
    content.push(message.message.slice(lastIndex));
  }

  return content;
}

export function StreamChatPanel({
  audienceCount,
  canSend,
  currentUserId,
  currentUsername,
  disabledReason,
  heading,
  messages,
  onSend,
  participants,
}: StreamChatPanelProps) {
  const [draft, setDraft] = useState("");
  const [caret, setCaret] = useState(0);
  const [selectedMentionIndex, setSelectedMentionIndex] = useState(0);
  const [isSending, setIsSending] = useState(false);
  const [composerError, setComposerError] = useState<string | null>(null);
  const [mentionNotification, setMentionNotification] = useState<StreamChatMessage | null>(null);
  const [unreadMentionCount, setUnreadMentionCount] = useState(0);

  const transcriptEndRef = useRef<HTMLDivElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const lastProcessedMessageIdRef = useRef<string | null>(null);
  const baseTitleRef = useRef("Streamline Live");

  const activeMention = getActiveMention(draft, caret);
  const deferredMentionQuery = useDeferredValue(activeMention?.query.toLowerCase() ?? "");

  const mentionableUsers = buildMentionableUsers(
    participants,
    messages,
    currentUserId,
    currentUsername
  );

  const mentionOptions = activeMention
    ? mentionableUsers
        .filter((user) => {
          if (!deferredMentionQuery) {
            return true;
          }

          return user.username.toLowerCase().includes(deferredMentionQuery);
        })
        .slice(0, 6)
    : [];

  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({
      behavior: messages.length > 1 ? "smooth" : "auto",
      block: "end",
    });
  }, [messages]);

  useEffect(() => {
    if (typeof document === "undefined") {
      return;
    }

    baseTitleRef.current = document.title;
  }, []);

  useEffect(() => {
    setSelectedMentionIndex(0);
  }, [deferredMentionQuery, activeMention?.start, mentionOptions.length]);

  useEffect(() => {
    const latestMessage = messages[messages.length - 1];

    if (!latestMessage || lastProcessedMessageIdRef.current === latestMessage.id) {
      return;
    }

    lastProcessedMessageIdRef.current = latestMessage.id;

    const isOwnMessage = isOwnChatMessage(
      latestMessage,
      currentUserId,
      currentUsername
    );

    if (
      isOwnMessage ||
      !messageMentionsUser(latestMessage, currentUserId, currentUsername)
    ) {
      return;
    }

    setMentionNotification(latestMessage);
    setUnreadMentionCount((currentCount) => currentCount + 1);

    if (typeof document === "undefined" || !document.hidden) {
      return;
    }

    if (typeof Notification !== "undefined" && Notification.permission === "granted") {
      const browserNotification = new Notification(
        `${latestMessage.username} mentioned you`,
        {
          body: latestMessage.message,
          tag: `stream-mention-${currentUsername ?? currentUserId ?? "viewer"}`,
        }
      );

      window.setTimeout(() => {
        browserNotification.close();
      }, 6000);
    }
  }, [messages, currentUserId, currentUsername]);

  useEffect(() => {
    if (typeof document === "undefined") {
      return;
    }

    document.title =
      unreadMentionCount > 0
        ? `(${unreadMentionCount}) Mention${unreadMentionCount > 1 ? "s" : ""} • ${baseTitleRef.current}`
        : baseTitleRef.current;

    return () => {
      document.title = baseTitleRef.current;
    };
  }, [unreadMentionCount]);

  useEffect(() => {
    if (typeof document === "undefined") {
      return;
    }

    const handleVisibilityChange = () => {
      if (!document.hidden) {
        setUnreadMentionCount(0);
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, []);

  const dismissMentionNotification = () => {
    setMentionNotification(null);
    setUnreadMentionCount(0);
  };

  const insertMention = (username: string) => {
    const textarea = textareaRef.current;

    if (!textarea) {
      return;
    }

    let nextValue = draft;
    let nextCaret = caret;

    if (activeMention) {
      const appliedMention = applyMention(
        draft,
        activeMention.start,
        activeMention.end,
        username
      );

      nextValue = appliedMention.nextValue;
      nextCaret = appliedMention.nextCaret;
    } else {
      const spacer = draft.length > 0 && !/\s$/.test(draft) ? " " : "";
      nextValue = `${draft}${spacer}@${username} `;
      nextCaret = nextValue.length;
    }

    setDraft(nextValue);
    setCaret(nextCaret);
    setComposerError(null);

    window.requestAnimationFrame(() => {
      textarea.focus();
      textarea.setSelectionRange(nextCaret, nextCaret);
    });
  };

  const submitMessage = async () => {
    const nextMessage = draft.trim();

    if (!nextMessage || !canSend || isSending) {
      return;
    }

    setIsSending(true);
    setComposerError(null);

    try {
      const didSend = await onSend(nextMessage);

      if (!didSend) {
        setComposerError("Message could not be sent right now.");
        return;
      }

      setDraft("");
      setCaret(0);

      window.requestAnimationFrame(() => {
        textareaRef.current?.focus();
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to send message";
      setComposerError(message);
    } finally {
      setIsSending(false);
    }
  };

  return (
    <aside className="panel chat-panel">
      <div className="chat-panel-header">
        <div>
          <p className="eyebrow">Live chat</p>
          <h2>{heading}</h2>
        </div>

        <div className="chat-panel-header-meta">
          {unreadMentionCount > 0 ? (
            <div className="chat-notification-pill">
              <strong>{unreadMentionCount}</strong>
              <span>mention{unreadMentionCount > 1 ? "s" : ""}</span>
            </div>
          ) : null}

          <div className="chat-count-pill">
            <strong>{audienceCount}</strong>
            <span>online</span>
          </div>
        </div>
      </div>

      {mentionNotification ? (
        <div className="chat-mention-toast" role="status" aria-live="assertive">
          <div className="chat-mention-toast-copy">
            <p className="eyebrow">Mention alert</p>
            <strong>{mentionNotification.username} mentioned you</strong>
            <p>{mentionNotification.message}</p>
          </div>

          <button
            className="ghost-button compact"
            onClick={dismissMentionNotification}
            type="button"
          >
            Dismiss
          </button>
        </div>
      ) : null}

      {mentionableUsers.length > 0 ? (
        <div className="chat-quick-mentions">
          <span>Quick mention</span>

          <div className="chat-chip-row">
            {mentionableUsers.slice(0, 6).map((user) => (
              <button
                key={user.peerId || `${user.username}-${user.userId ?? "guest"}`}
                className="chat-chip"
                disabled={!canSend}
                onClick={() => insertMention(user.username)}
                type="button"
              >
                @{user.username}
              </button>
            ))}
          </div>
        </div>
      ) : null}

      <div className="chat-transcript" role="log" aria-live="polite">
        {messages.length === 0 ? (
          <div className="chat-empty-state">
            <strong>No messages yet.</strong>
            <span>{canSend ? "Be the first one to say hello." : disabledReason}</span>
          </div>
        ) : (
          <ul className="chat-message-list">
            {messages.map((message) => {
              const isOwnMessage = isOwnChatMessage(
                message,
                currentUserId,
                currentUsername
              );
              const isMentionedMessage = messageMentionsUser(
                message,
                currentUserId,
                currentUsername
              );
              const messageRole =
                message.role === "publisher" ? "Host" : "Viewer";

              return (
                <li
                  key={message.id}
                  className={[
                    "chat-message-item",
                    isOwnMessage ? "chat-message-own" : "",
                    !isOwnMessage && isMentionedMessage ? "chat-message-mentioned" : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                >
                  <div className="chat-avatar" aria-hidden="true">
                    {message.username.slice(0, 1).toUpperCase()}
                  </div>

                  <div className="chat-bubble">
                    <div className="chat-message-meta">
                      <strong>{message.username}</strong>
                      <span className="chat-role-pill">{messageRole}</span>
                      <time>{formatTime(message.receivedAt)}</time>
                    </div>

                    <p>{renderMessageText(message, currentUsername)}</p>
                  </div>
                </li>
              );
            })}
          </ul>
        )}

        <div ref={transcriptEndRef} />
      </div>

      <div className="chat-composer-shell">
        <div className="chat-composer-headline">
          <strong>Say something</strong>
          <span>{draft.length}/{MAX_DRAFT_LENGTH}</span>
        </div>

        <div className="chat-composer">
          <textarea
            ref={textareaRef}
            className="chat-textarea"
            disabled={!canSend || isSending}
            maxLength={MAX_DRAFT_LENGTH}
            onChange={(event) => {
              setDraft(event.target.value);
              setCaret(event.target.selectionStart ?? event.target.value.length);
              setComposerError(null);
            }}
            onClick={(event) => {
              setCaret(event.currentTarget.selectionStart ?? event.currentTarget.value.length);
            }}
            onKeyDown={(event) => {
              if (mentionOptions.length > 0) {
                if (event.key === "ArrowDown") {
                  event.preventDefault();
                  setSelectedMentionIndex((currentIndex) =>
                    currentIndex >= mentionOptions.length - 1 ? 0 : currentIndex + 1
                  );
                  return;
                }

                if (event.key === "ArrowUp") {
                  event.preventDefault();
                  setSelectedMentionIndex((currentIndex) =>
                    currentIndex <= 0 ? mentionOptions.length - 1 : currentIndex - 1
                  );
                  return;
                }

                if ((event.key === "Enter" || event.key === "Tab") && !event.shiftKey) {
                  event.preventDefault();
                  insertMention(
                    mentionOptions[selectedMentionIndex]?.username ?? mentionOptions[0].username
                  );
                  return;
                }
              }

              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                void submitMessage();
              }
            }}
            onSelect={(event) => {
              setCaret(event.currentTarget.selectionStart ?? event.currentTarget.value.length);
            }}
            placeholder={
              canSend
                ? "Type a message. Use @ to mention someone."
                : disabledReason
            }
            rows={4}
            value={draft}
          />

          {canSend && mentionOptions.length > 0 ? (
            <div className="mention-popover">
              {mentionOptions.map((user, index) => (
                <button
                  key={user.peerId || `${user.username}-${user.userId ?? "guest"}`}
                  className={
                    index === selectedMentionIndex
                      ? "mention-option mention-option-active"
                      : "mention-option"
                  }
                  onClick={() => insertMention(user.username)}
                  type="button"
                >
                  <div>
                    <strong>@{user.username}</strong>
                    <span>{user.role === "publisher" ? "Host" : "Live viewer"}</span>
                  </div>
                </button>
              ))}
            </div>
          ) : null}
        </div>

        <div className="chat-composer-footer">
          <span>{canSend ? "Press Enter to send. Shift+Enter adds a new line." : disabledReason}</span>

          <button
            className="primary-button compact"
            disabled={!canSend || isSending || draft.trim().length === 0}
            onClick={() => {
              void submitMessage();
            }}
            type="button"
          >
            {isSending ? "Sending..." : "Send"}
          </button>
        </div>

        {composerError ? <p className="chat-composer-error">{composerError}</p> : null}
      </div>
    </aside>
  );
}

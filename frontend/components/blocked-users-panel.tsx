import type { BlockedUser } from "../lib/types";

type BlockedUsersPanelProps = {
  blockedUsers: BlockedUser[];
  isLoading: boolean;
  onUnblock: (userId: string) => void;
};

export function BlockedUsersPanel({
  blockedUsers,
  isLoading,
  onUnblock,
}: BlockedUsersPanelProps) {
  return (
    <div className="panel stack-md">
      <div>
        <p className="eyebrow">Blocked users</p>
        <h2>Moderation</h2>
      </div>

      {isLoading ? <p className="muted">Loading blocked users...</p> : null}

      {!isLoading && blockedUsers.length === 0 ? (
        <p className="muted">No blocked users.</p>
      ) : null}

      {!isLoading && blockedUsers.length > 0 ? (
        <ul className="blocked-user-list">
          {blockedUsers.map((blocked) => (
            <li key={blocked.id}>
              <div>
                <strong>{blocked.username}</strong>
                <span>{blocked.reason || "blocked"}</span>
              </div>

              <button
                className="mini-ghost-button"
                onClick={() => onUnblock(blocked.user_id)}
                type="button"
              >
                Unblock
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
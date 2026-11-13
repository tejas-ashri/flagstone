import type { User } from "../types/project";

export function Avatar({ user, size = 28 }: { user: Pick<User, "name" | "email" | "avatar_url">; size?: number }) {
  const label = user.name || user.email;
  if (user.avatar_url) {
    return (
      <img
        className="avatar"
        src={user.avatar_url}
        alt=""
        width={size}
        height={size}
        referrerPolicy="no-referrer"
      />
    );
  }
  return (
    <span className="avatar initials" style={{ width: size, height: size }} aria-hidden>
      {label.slice(0, 1).toUpperCase()}
    </span>
  );
}

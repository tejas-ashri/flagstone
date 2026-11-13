import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { messageOf } from "../api/http";
import { cancelInvitation, inviteMember, listMembers, removeMember, setMemberRole } from "../api/projects";
import { useAuth, useMe } from "../auth/context";
import { Avatar } from "../components/Avatar";
import { ConfirmDialog } from "../components/Modal";
import { useToast } from "../components/toast/context";
import { useLoad } from "../lib/useLoad";
import { useProject } from "../project/context";
import type { Member, Members, Role } from "../types/project";

const ROLE_HELP: Record<Role, string> = {
  admin: "Can change flags, SDK keys, members and settings",
  viewer: "Can see flags and results, but not change them",
};

export function MembersPage() {
  const { project, isAdmin } = useProject();
  const { user: me } = useMe();
  const { refresh } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const members = useLoad(() => listMembers(project.id), [project.id]);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<Role>("viewer");
  const [busy, setBusy] = useState(false);
  const [removing, setRemoving] = useState<Member | null>(null);

  // Every mutation returns the new member list.
  const run = async (action: () => Promise<Members>, success: string) => {
    setBusy(true);
    try {
      members.setData(await action());
      toast(success, { kind: "success" });
      return true;
    } catch (err) {
      toast(messageOf(err), { kind: "error" });
      return false;
    } finally {
      setBusy(false);
    }
  };

  const invite = async (e: FormEvent) => {
    e.preventDefault();
    const target = email.trim();
    if (await run(() => inviteMember(project.id, target, role), `Added ${target} as ${role}`)) setEmail("");
  };

  const changeRole = async (m: Member, next: Role) => {
    await run(() => setMemberRole(project.id, m.user.id, next), `${m.user.email} is now ${next}`);
    if (m.user.id === me.id) refresh(); // own role changed: update what this page allows
  };

  const remove = async () => {
    if (!removing) return;
    const self = removing.user.id === me.id;
    if (await run(() => removeMember(project.id, removing.user.id), `Removed ${removing.user.email}`)) {
      setRemoving(null);
      if (self) {
        await refresh();
        navigate("/projects");
      }
    }
  };

  const data = members.data;

  return (
    <>
      <header className="page-head">
        <div>
          <h1>Members</h1>
          <p className="muted">People who can sign in and see this project. Sign-in is by GitHub, Google or Slack using the same email.</p>
        </div>
      </header>

      {isAdmin && (
        <form className="card invite-form" onSubmit={invite}>
          <h3>Invite someone</h3>
          <div className="row wrap">
            <input
              type="email"
              className="grow"
              placeholder="teammate@company.com"
              aria-label="Email to invite"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
            />
            <select value={role} onChange={e => setRole(e.target.value as Role)} aria-label="Role">
              <option value="viewer">Viewer</option>
              <option value="admin">Admin</option>
            </select>
            <button type="submit" className="btn primary" disabled={busy}>Invite</button>
          </div>
          <p className="muted small">{ROLE_HELP[role]}. They get access the next time they sign in with this email.</p>
        </form>
      )}

      {members.error && <div className="banner" role="alert"><span>{members.error}</span><button type="button" className="btn" onClick={members.reload}>Retry</button></div>}
      {members.loading && !data && <p className="muted">Loading members…</p>}

      {data && (
        <div className="card flush">
          <ul className="member-list">
            {data.members.map(m => (
              <li key={m.user.id}>
                <Avatar user={m.user} size={32} />
                <div className="grow">
                  <div>{m.user.name || m.user.email}{m.user.id === me.id && <span className="badge">you</span>}</div>
                  <div className="muted small">{m.user.email}</div>
                </div>
                {isAdmin ? (
                  <>
                    <select
                      value={m.role}
                      aria-label={`Role of ${m.user.email}`}
                      disabled={busy}
                      onChange={e => changeRole(m, e.target.value as Role)}
                    >
                      <option value="admin">Admin</option>
                      <option value="viewer">Viewer</option>
                    </select>
                    <button type="button" className="btn ghost danger" disabled={busy} onClick={() => setRemoving(m)}>
                      Remove
                    </button>
                  </>
                ) : (
                  <span className={`role-badge ${m.role}`}>{m.role}</span>
                )}
              </li>
            ))}
            {data.invitations.map(i => (
              <li key={i.email} className="pending">
                <span className="avatar initials" aria-hidden>?</span>
                <div className="grow">
                  <div>{i.email}</div>
                  <div className="muted small">Invited as {i.role} · hasn't signed in yet</div>
                </div>
                {isAdmin && (
                  <button
                    type="button"
                    className="btn ghost danger"
                    disabled={busy}
                    onClick={() => run(() => cancelInvitation(project.id, i.email), `Cancelled invite for ${i.email}`)}
                  >
                    Cancel invite
                  </button>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      <ConfirmDialog
        open={removing !== null}
        title={removing?.user.id === me.id ? "Leave this project?" : `Remove ${removing?.user.email}?`}
        message={
          removing?.user.id === me.id
            ? "You'll lose access to this project until an admin invites you again."
            : "They lose access to this project's flags, keys and results immediately."
        }
        confirmLabel={removing?.user.id === me.id ? "Leave project" : "Remove member"}
        danger
        busy={busy}
        onConfirm={remove}
        onCancel={() => setRemoving(null)}
      />
    </>
  );
}

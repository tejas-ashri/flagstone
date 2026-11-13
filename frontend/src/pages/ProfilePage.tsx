import { Link } from "react-router-dom";
import { useAuth, useMe } from "../auth/context";
import { Avatar } from "../components/Avatar";
import { projectPath } from "../project/context";

const PROVIDER_NAMES: Record<string, string> = {
  github: "GitHub",
  google: "Google",
  slack: "Slack",
  dev: "Development sign-in",
};

export function ProfilePage() {
  const { user, identities, projects } = useMe();
  const { signOut } = useAuth();
  return (
    <main className="page narrow">
      <header className="page-head">
        <h1>Profile</h1>
        <button type="button" className="btn" onClick={signOut}>Sign out</button>
      </header>

      <section className="card">
        <div className="row">
          <Avatar user={user} size={56} />
          <div>
            <h2>{user.name || user.email}</h2>
            <p className="muted">{user.email}</p>
          </div>
        </div>
      </section>

      <section className="card">
        <h3>Sign-in methods</h3>
        <p className="muted small">Any provider that reports this verified email signs in to this account.</p>
        <ul className="plain-list">
          {identities.map(i => <li key={i}>{PROVIDER_NAMES[i] ?? i}</li>)}
        </ul>
      </section>

      <section className="card">
        <h3>Projects</h3>
        {projects.length === 0 ? (
          <p className="muted">You aren't a member of any project.</p>
        ) : (
          <ul className="plain-list">
            {projects.map(p => (
              <li key={p.id} className="row between">
                <Link to={projectPath(p.id, "flags")}>{p.name}</Link>
                <span className={`role-badge ${p.role}`}>{p.role}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}

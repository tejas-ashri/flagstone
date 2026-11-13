import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { messageOf } from "../api/http";
import { createProject } from "../api/projects";
import { useAuth, useMe } from "../auth/context";
import { Modal } from "../components/Modal";
import { projectPath } from "../project/context";

export function ProjectsPage() {
  const { projects, user } = useMe();
  const { refresh } = useAuth();
  const navigate = useNavigate();
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const project = await createProject(name);
      await refresh();
      navigate(projectPath(project.id, "flags"));
    } catch (err) {
      setError(messageOf(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="page narrow">
      <header className="page-head">
        <div>
          <h1>Projects</h1>
          <p className="muted">
            Each project has its own flags, SDK keys and members. An SDK key only sees its own project's flags.
          </p>
        </div>
        <button type="button" className="btn primary" onClick={() => setCreating(true)}>New project</button>
      </header>

      {projects.length === 0 ? (
        <div className="empty">
          <h2>Welcome, {user.name || user.email}</h2>
          <p>You're not in any project yet. Create one, or ask an admin to invite <strong>{user.email}</strong>.</p>
          <button type="button" className="btn primary" onClick={() => setCreating(true)}>Create a project</button>
        </div>
      ) : (
        <div className="project-grid">
          {projects.map(p => (
            <Link key={p.id} to={projectPath(p.id, "flags")} className="project-card">
              <div className="row between">
                <h3>{p.name}</h3>
                <span className={`role-badge ${p.role}`}>{p.role}</span>
              </div>
              <p className="muted small">
                {p.flag_count} flag{p.flag_count === 1 ? "" : "s"} · {p.member_count} member
                {p.member_count === 1 ? "" : "s"}
              </p>
            </Link>
          ))}
        </div>
      )}

      <Modal open={creating} title="New project" onClose={() => setCreating(false)}>
        <form className="stack" onSubmit={submit}>
          <label className="field">
            <span>Name</span>
            <input autoFocus value={name} onChange={e => setName(e.target.value)} maxLength={80} required placeholder="Checkout web app" />
          </label>
          {error && <p className="error-text" role="alert">{error}</p>}
          <div className="modal-footer">
            <button type="button" className="btn" onClick={() => setCreating(false)}>Cancel</button>
            <button type="submit" className="btn primary" disabled={busy}>{busy ? "Creating…" : "Create project"}</button>
          </div>
        </form>
      </Modal>
    </main>
  );
}

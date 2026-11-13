import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { messageOf } from "../api/http";
import { deleteProject, renameProject } from "../api/projects";
import { useAuth } from "../auth/context";
import { ConfirmDialog } from "../components/Modal";
import { useToast } from "../components/toast/context";
import { useProject } from "../project/context";

export function SettingsPage() {
  const { project, isAdmin } = useProject();
  const { refresh } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const [name, setName] = useState(project.name);
  const [busy, setBusy] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [typed, setTyped] = useState("");
  const isDefault = project.id === "default";

  const rename = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      await renameProject(project.id, name);
      await refresh();
      toast("Project renamed", { kind: "success" });
    } catch (err) {
      toast(messageOf(err), { kind: "error" });
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    setBusy(true);
    try {
      await deleteProject(project.id);
      await refresh();
      toast(`Deleted ${project.name}`, { kind: "success" });
      navigate("/projects");
    } catch (err) {
      toast(messageOf(err), { kind: "error" });
      setBusy(false);
    }
  };

  return (
    <>
      <header className="page-head">
        <div>
          <h1>Settings</h1>
          <p className="muted">Project ID <code>{project.id}</code></p>
        </div>
      </header>

      <form className="card" onSubmit={rename}>
        <h3>Name</h3>
        <fieldset className="row wrap plain" disabled={!isAdmin}>
          <input className="grow" value={name} onChange={e => setName(e.target.value)} maxLength={80} required aria-label="Project name" />
          <button type="submit" className="btn primary" disabled={busy || name.trim() === project.name}>Save</button>
        </fieldset>
      </form>

      {isAdmin && (
        <section className="card danger-zone">
          <h3>Delete project</h3>
          {isDefault ? (
            <p className="muted">
              The Default project can't be deleted: it holds the flags that existed before projects, and the original{" "}
              <code>/api/flags</code> paths and the <code>SDK_KEY</code> setting point at it.
            </p>
          ) : (
            <>
              <p className="muted">
                Deletes all {project.flag_count} flag{project.flag_count === 1 ? "" : "s"}, their results, every SDK key and
                all memberships. Apps using this project's keys will start getting 401 errors.
              </p>
              <button type="button" className="btn danger-solid" onClick={() => { setTyped(""); setConfirming(true); }}>
                Delete this project
              </button>
            </>
          )}
        </section>
      )}

      <ConfirmDialog
        open={confirming}
        title={`Delete ${project.name}?`}
        message="This cannot be undone."
        confirmLabel="Delete project"
        danger
        busy={busy}
        requireText={project.name}
        typedText={typed}
        onTypedTextChange={setTyped}
        onConfirm={remove}
        onCancel={() => setConfirming(false)}
      />
    </>
  );
}

import { useCallback, useMemo, useState } from "react";
import { Link, NavLink, Outlet, useNavigate, useParams } from "react-router-dom";
import { deleteFlag, getFlag } from "../api/flags";
import { messageOf } from "../api/http";
import { useAuth } from "../auth/context";
import { ConfirmDialog } from "../components/Modal";
import { Toggle } from "../components/Toggle";
import { useToast } from "../components/toast/context";
import { FlagContext } from "../flag/context";
import { useFlagToggle } from "../lib/useFlagToggle";
import { useLoad } from "../lib/useLoad";
import { flagPath, projectPath, useProject } from "../project/context";
import type { FlagResponse } from "../types/flag";

const TABS = [
  { to: "", label: "Targeting", end: true },
  { to: "test", label: "Test a user" },
  { to: "results", label: "Results" },
  { to: "sdk", label: "SDK usage" },
];

export function FlagLayout() {
  const { flagKey = "" } = useParams();
  const { project, isAdmin } = useProject();
  const { refresh } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();
  const loaded = useLoad(() => getFlag(project.id, flagKey), [project.id, flagKey]);
  const { setData } = loaded;
  const setFlag = useCallback((f: FlagResponse) => setData(f), [setData]);
  const toggle = useFlagToggle(project.id, setFlag);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [typed, setTyped] = useState("");
  const [deleting, setDeleting] = useState(false);

  const flag = loaded.data;
  const ctx = useMemo(() => (flag ? { flag, setFlag } : null), [flag, setFlag]);

  const remove = async () => {
    setDeleting(true);
    try {
      await deleteFlag(project.id, flagKey);
      toast(`Deleted ${flagKey}`, { kind: "success" });
      refresh();
      navigate(projectPath(project.id, "flags"));
    } catch (err) {
      toast(messageOf(err), { kind: "error" });
      setDeleting(false);
    }
  };

  if (!ctx) {
    if (loaded.error) {
      return (
        <div className="empty">
          <h2>Couldn't load this flag</h2>
          <p>{loaded.error}</p>
          <div className="row center">
            <Link className="btn" to={projectPath(project.id, "flags")}>Back to flags</Link>
            <button type="button" className="btn" onClick={loaded.reload}>Retry</button>
          </div>
        </div>
      );
    }
    return <p className="muted">Loading flag…</p>;
  }

  return (
    <FlagContext.Provider value={ctx}>
      <nav className="breadcrumbs" aria-label="Breadcrumb">
        <Link to={projectPath(project.id, "flags")}>Flags</Link>
        <span aria-hidden>/</span>
        <code>{ctx.flag.key}</code>
      </nav>
      <header className="page-head">
        <div>
          <h1><code>{ctx.flag.key}</code></h1>
          <p className="muted small">Updated {new Date(ctx.flag.updated_at).toLocaleString()}</p>
        </div>
        <div className="row">
          <span className={`status${ctx.flag.enabled ? " on" : ""}`}>{ctx.flag.enabled ? "On" : "Off"}</span>
          <Toggle
            checked={ctx.flag.enabled}
            disabled={!isAdmin}
            onChange={() => toggle(ctx.flag)}
            label={isAdmin ? (ctx.flag.enabled ? "Turn flag off" : "Turn flag on") : "Only admins can change flags"}
          />
          {isAdmin && (
            <button type="button" className="btn danger" onClick={() => { setTyped(""); setConfirmDelete(true); }}>
              Delete
            </button>
          )}
        </div>
      </header>

      {!isAdmin && (
        <p className="notice">You have view access to this project. Ask an admin to make changes.</p>
      )}

      <nav className="tabs" aria-label="Flag sections">
        {TABS.map(t => (
          <NavLink key={t.label} to={flagPath(project.id, ctx.flag.key, t.to)} end={t.end} className="tab">
            {t.label}
          </NavLink>
        ))}
      </nav>

      <Outlet />

      <ConfirmDialog
        open={confirmDelete}
        title={`Delete ${ctx.flag.key}?`}
        message={
          <>
            Its experiment events are deleted too, and SDKs that still check this flag will get{" "}
            <code>false</code> / variation 0. This cannot be undone.
          </>
        }
        confirmLabel="Delete flag"
        danger
        busy={deleting}
        requireText={ctx.flag.key}
        typedText={typed}
        onTypedTextChange={setTyped}
        onConfirm={remove}
        onCancel={() => setConfirmDelete(false)}
      />
    </FlagContext.Provider>
  );
}

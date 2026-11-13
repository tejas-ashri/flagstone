import { useState, type FormEvent } from "react";
import { messageOf } from "../api/http";
import { createKey, listKeys, revokeKey } from "../api/projects";
import { CopyButton } from "../components/CopyButton";
import { ConfirmDialog, Modal } from "../components/Modal";
import { useToast } from "../components/toast/context";
import { useLoad } from "../lib/useLoad";
import { useProject } from "../project/context";
import type { SdkKey, SdkKeyCreated } from "../types/project";

const fmt = (iso: string | null) => (iso ? new Date(iso).toLocaleString() : "—");

export function KeysPage() {
  const { project, isAdmin } = useProject();
  const toast = useToast();
  const keys = useLoad(() => listKeys(project.id), [project.id]);
  const [creating, setCreating] = useState(false);
  const [label, setLabel] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [created, setCreated] = useState<SdkKeyCreated | null>(null);
  const [revoking, setRevoking] = useState<SdkKey | null>(null);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const key = await createKey(project.id, label.trim());
      setCreating(false);
      setLabel("");
      setCreated(key);
      keys.reload();
    } catch (err) {
      setError(messageOf(err));
    } finally {
      setBusy(false);
    }
  };

  const revoke = async () => {
    if (!revoking) return;
    setBusy(true);
    try {
      await revokeKey(project.id, revoking.id);
      toast(`Revoked "${revoking.label}"`, { kind: "success" });
      setRevoking(null);
      keys.reload();
    } catch (err) {
      toast(messageOf(err), { kind: "error" });
    } finally {
      setBusy(false);
    }
  };

  const active = (keys.data ?? []).filter(k => !k.revoked_at);
  const revoked = (keys.data ?? []).filter(k => k.revoked_at);

  return (
    <>
      <header className="page-head">
        <div>
          <h1>SDK keys</h1>
          <p className="muted">
            Your apps pass one of these to <code>FlagClient(sdk_key=…)</code>. A key can only read this project's flags
            and send events for them.
          </p>
        </div>
        {isAdmin && (
          <button type="button" className="btn primary" onClick={() => { setError(""); setCreating(true); }}>
            New key
          </button>
        )}
      </header>

      {keys.error && <div className="banner" role="alert"><span>{keys.error}</span><button type="button" className="btn" onClick={keys.reload}>Retry</button></div>}
      {keys.loading && !keys.data && <p className="muted">Loading keys…</p>}
      {keys.data && active.length === 0 && (
        <div className="empty">
          <h2>No active keys</h2>
          <p>Create a key for each app or environment so you can revoke one without affecting the others.</p>
        </div>
      )}

      {active.length > 0 && (
        <div className="card flush">
          <div className="table-wrap">
            <table>
              <thead>
                <tr><th>Label</th><th>Key</th><th>Created</th><th>Last used</th>{isAdmin && <th />}</tr>
              </thead>
              <tbody>
                {active.map(k => (
                  <tr key={k.id}>
                    <td>{k.label}</td>
                    <td><code>{k.prefix}…</code></td>
                    <td className="muted">{fmt(k.created_at)}</td>
                    <td className="muted">{k.last_used_at ? fmt(k.last_used_at) : "Never"}</td>
                    {isAdmin && (
                      <td className="num">
                        <button type="button" className="btn ghost danger" onClick={() => setRevoking(k)}>Revoke</button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {revoked.length > 0 && (
        <details className="revoked">
          <summary className="muted">{revoked.length} revoked key{revoked.length === 1 ? "" : "s"}</summary>
          <ul>
            {revoked.map(k => (
              <li key={k.id} className="muted small">
                {k.label} · <code>{k.prefix}…</code> · revoked {fmt(k.revoked_at)}
              </li>
            ))}
          </ul>
        </details>
      )}

      <Modal open={creating} title="New SDK key" onClose={() => setCreating(false)}>
        <form className="stack" onSubmit={submit}>
          <label className="field">
            <span>Label</span>
            <input autoFocus value={label} onChange={e => setLabel(e.target.value)} placeholder="checkout-web production" maxLength={80} required />
            <span className="muted small">Where this key will be used, so you know what breaks if you revoke it.</span>
          </label>
          {error && <p className="error-text" role="alert">{error}</p>}
          <div className="modal-footer">
            <button type="button" className="btn" onClick={() => setCreating(false)}>Cancel</button>
            <button type="submit" className="btn primary" disabled={busy}>{busy ? "Creating…" : "Create key"}</button>
          </div>
        </form>
      </Modal>

      <Modal
        open={created !== null}
        title="Copy your new key"
        onClose={() => setCreated(null)}
        footer={<button type="button" className="btn primary" onClick={() => setCreated(null)}>I've saved it</button>}
      >
        <p className="notice">This is the only time the full key is shown. Store it in your app's secrets now.</p>
        {created && (
          <div className="row">
            <input className="grow mono" readOnly value={created.key} onFocus={e => e.target.select()} aria-label="New SDK key" />
            <CopyButton text={created.key} />
          </div>
        )}
      </Modal>

      <ConfirmDialog
        open={revoking !== null}
        title={`Revoke "${revoking?.label}"?`}
        message="Apps using this key get 401 errors straight away and fall back to their cached flags. This cannot be undone."
        confirmLabel="Revoke key"
        danger
        busy={busy}
        onConfirm={revoke}
        onCancel={() => setRevoking(null)}
      />
    </>
  );
}

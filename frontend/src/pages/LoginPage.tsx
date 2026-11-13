import { useState, type FormEvent } from "react";
import { Navigate, useSearchParams } from "react-router-dom";
import { messageOf } from "../api/http";
import { devLogin, getProviders } from "../api/projects";
import { useAuth } from "../auth/context";
import { ProviderLogo } from "../components/ProviderLogo";
import { useLoad } from "../lib/useLoad";

function safeNext(next: string | null): string {
  return next && next.startsWith("/") && !next.startsWith("//") ? next : "/projects";
}

export function LoginPage() {
  const { status, refresh } = useAuth();
  const [params] = useSearchParams();
  const next = safeNext(params.get("next"));
  const providers = useLoad(getProviders, []);
  const [email, setEmail] = useState("admin@example.com");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [devError, setDevError] = useState("");

  if (status === "signedIn") return <Navigate to={next} replace />;

  const submitDev = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setDevError("");
    try {
      await devLogin(email, name);
      await refresh();
    } catch (err) {
      setDevError(messageOf(err));
    } finally {
      setBusy(false);
    }
  };

  const list = providers.data?.providers ?? [];
  const error = params.get("error");

  return (
    <div className="login">
      <div className="login-card">
        <div className="login-brand">
          <span className="brand-mark" aria-hidden>⚑</span>
          <h1>Flagstone</h1>
        </div>
        <p className="muted">Sign in to manage feature flags and experiments.</p>

        {error && <p className="banner-inline error" role="alert">{error}</p>}
        {providers.error && <p className="banner-inline error" role="alert">{providers.error}</p>}
        {providers.loading && <p className="muted">Loading sign-in options…</p>}

        <div className="stack">
          {list.map(p => (
            <a
              key={p.id}
              className={`btn provider ${p.id}`}
              href={`/auth/${p.id}/login?next=${encodeURIComponent(next)}`}
            >
              <ProviderLogo provider={p.id} />
              Continue with {p.label}
            </a>
          ))}
        </div>

        {providers.data?.dev_login && (
          <form className="dev-login" onSubmit={submitDev}>
            <div className="divider"><span>Development sign-in</span></div>
            <label className="field">
              <span>Email</span>
              <input type="email" value={email} onChange={e => setEmail(e.target.value)} required />
            </label>
            <label className="field">
              <span>Name (optional)</span>
              <input value={name} onChange={e => setName(e.target.value)} />
            </label>
            {devError && <p className="error-text" role="alert">{devError}</p>}
            <button type="submit" className="btn primary" disabled={busy}>
              {busy ? "Signing in…" : "Sign in without a provider"}
            </button>
            <p className="muted small">Enabled by DEV_LOGIN. Turn it off anywhere others can reach.</p>
          </form>
        )}

        {providers.data && !list.length && !providers.data.dev_login && (
          <div className="notice">
            No sign-in method is configured. Set <code>GITHUB_CLIENT_ID</code> and{" "}
            <code>GITHUB_CLIENT_SECRET</code> (or Google/Slack) on the backend, or{" "}
            <code>DEV_LOGIN=true</code> for local development.
          </div>
        )}
      </div>
    </div>
  );
}

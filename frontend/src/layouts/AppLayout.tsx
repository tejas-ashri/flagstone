import { useEffect, useRef, useState } from "react";
import { Link, Outlet, useLocation, useNavigate, useParams } from "react-router-dom";
import { useMe, useAuth } from "../auth/context";
import { Avatar } from "../components/Avatar";
import { projectPath } from "../project/context";

function ProjectSwitcher() {
  const { projects } = useMe();
  const { projectId } = useParams();
  const navigate = useNavigate();
  if (!projectId || !projects.some(p => p.id === projectId)) return null;
  return (
    <select
      className="project-switcher"
      aria-label="Switch project"
      value={projectId}
      onChange={e => navigate(projectPath(e.target.value, "flags"))}
    >
      {projects.map(p => (
        <option key={p.id} value={p.id}>{p.name}</option>
      ))}
    </select>
  );
}

function UserMenu() {
  const { user } = useMe();
  const { signOut } = useAuth();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const location = useLocation();

  useEffect(() => setOpen(false), [location.pathname]);

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent | KeyboardEvent) => {
      if (e instanceof KeyboardEvent ? e.key === "Escape" : !ref.current?.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", close);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", close);
    };
  }, [open]);

  return (
    <div className="menu" ref={ref}>
      <button
        type="button"
        className="menu-trigger"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen(o => !o)}
      >
        <Avatar user={user} />
        <span className="menu-name">{user.name || user.email}</span>
      </button>
      {open && (
        <div className="menu-panel" role="menu">
          <div className="menu-header">
            <strong>{user.name}</strong>
            <span className="muted small">{user.email}</span>
          </div>
          <Link role="menuitem" to="/projects">All projects</Link>
          <Link role="menuitem" to="/profile">Profile</Link>
          <button role="menuitem" type="button" onClick={signOut}>Sign out</button>
        </div>
      )}
    </div>
  );
}

export function AppLayout() {
  return (
    <div className="shell">
      <header className="topbar">
        <Link to="/projects" className="brand">
          <span className="brand-mark" aria-hidden>⚑</span> Flagstone
        </Link>
        <ProjectSwitcher />
        <div className="grow" />
        <UserMenu />
      </header>
      <Outlet />
    </div>
  );
}

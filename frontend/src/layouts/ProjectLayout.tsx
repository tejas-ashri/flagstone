import { useMemo } from "react";
import { Link, NavLink, Outlet, useParams } from "react-router-dom";
import { useMe } from "../auth/context";
import { ProjectContext, projectPath } from "../project/context";

const NAV = [
  { to: "flags", label: "Flags" },
  { to: "keys", label: "SDK keys" },
  { to: "members", label: "Members" },
  { to: "settings", label: "Settings" },
];

export function ProjectLayout() {
  const { projectId = "" } = useParams();
  const { projects } = useMe();
  const project = projects.find(p => p.id === projectId);
  const value = useMemo(
    () => (project ? { project, isAdmin: project.role === "admin" } : null),
    [project],
  );

  if (!value) {
    return (
      <main className="page narrow">
        <div className="empty">
          <h2>Project not found</h2>
          <p>It doesn't exist, or you aren't a member. Ask a project admin to invite you.</p>
          <Link className="btn" to="/projects">Back to projects</Link>
        </div>
      </main>
    );
  }

  return (
    <ProjectContext.Provider value={value}>
      <div className="project-layout">
        <nav className="sidenav" aria-label="Project">
          <div className="sidenav-head">
            <strong>{value.project.name}</strong>
            <span className={`role-badge ${value.project.role}`}>{value.project.role}</span>
          </div>
          {NAV.map(n => (
            <NavLink key={n.to} to={projectPath(projectId, n.to)} className="sidenav-link">
              {n.label}
            </NavLink>
          ))}
        </nav>
        <main className="page">
          <Outlet />
        </main>
      </div>
    </ProjectContext.Provider>
  );
}

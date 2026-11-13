import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <main className="page narrow">
      <div className="empty">
        <h2>Page not found</h2>
        <p>The link may be out of date.</p>
        <Link className="btn" to="/projects">Go to projects</Link>
      </div>
    </main>
  );
}

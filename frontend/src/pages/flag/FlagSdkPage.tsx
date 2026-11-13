import { Link } from "react-router-dom";
import { CopyButton } from "../../components/CopyButton";
import { useFlag } from "../../flag/context";
import { projectPath, useProject } from "../../project/context";
import type { FlagResponse } from "../../types/flag";

function snippet(flag: FlagResponse): string {
  const key = JSON.stringify(flag.key);
  const isBoolean = flag.variations.every(v => typeof v === "boolean");
  const attrs = [...new Set(flag.rules.map(r => r.attribute).filter(a => a && a !== "id"))];
  const user = [`"id": "user-123"`, ...attrs.map(a => `${JSON.stringify(a)}: ...`)].join(", ");
  const check = isBoolean
    ? `if client.is_enabled(${key}, user):\n    ...  # new behaviour`
    : `index = client.get_variation(${key}, user)  # index into the variations list`;
  return [
    "from sdk.client import FlagClient",
    "",
    "client = FlagClient(",
    '    sdk_key="<an SDK key of this project>",',
    '    base_url="http://localhost:8000",',
    ")",
    "",
    `user = {${user}}`,
    "",
    check,
    "",
    "# When the user completes the goal you're measuring:",
    `client.track_conversion(${key}, user)`,
  ].join("\n");
}

export function FlagSdkPage() {
  const { flag } = useFlag();
  const { project } = useProject();
  const code = snippet(flag);
  return (
    <section className="card">
      <header className="card-head split">
        <div>
          <h3>Use this flag from Python</h3>
          <p className="muted small">
            Use an SDK key from <Link to={projectPath(project.id, "keys")}>this project's keys</Link>. A key from another
            project won't see this flag. <code>id</code> drives the percentage rollout.
          </p>
        </div>
        <CopyButton text={code} />
      </header>
      <pre><code>{code}</code></pre>
    </section>
  );
}

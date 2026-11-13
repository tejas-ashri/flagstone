import { createContext, useContext } from "react";
import type { Project } from "../types/project";

export interface ProjectState {
  project: Project;
  isAdmin: boolean;
}

export const ProjectContext = createContext<ProjectState | null>(null);

export function useProject(): ProjectState {
  const ctx = useContext(ProjectContext);
  if (!ctx) throw new Error("useProject must be used inside a project route");
  return ctx;
}

export const projectPath = (projectId: string, ...rest: string[]) =>
  ["/projects", encodeURIComponent(projectId), ...rest].join("/");

export const flagPath = (projectId: string, flagKey: string, tab?: string) =>
  projectPath(projectId, "flags", encodeURIComponent(flagKey), ...(tab ? [tab] : []));

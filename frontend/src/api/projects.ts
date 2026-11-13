import type {
  AuthProviders,
  Me,
  Members,
  Project,
  Role,
  SdkKey,
  SdkKeyCreated,
  User,
} from "../types/project";
import { enc, jsonBody, request } from "./http";

const projectUrl = (id: string) => `/api/projects/${enc(id)}`;

export const getMe = (): Promise<Me> => request("/api/me");

export const getProviders = (): Promise<AuthProviders> => request("/auth/providers");

export const devLogin = (email: string, name: string): Promise<User> =>
  request("/auth/dev-login", jsonBody("POST", { email, name }));

export const logout = (): Promise<void> => request("/auth/logout", { method: "POST" });

export const listProjects = (): Promise<Project[]> => request("/api/projects");

export const getProject = (id: string): Promise<Project> => request(projectUrl(id));

export const createProject = (name: string): Promise<Project> =>
  request("/api/projects", jsonBody("POST", { name }));

export const renameProject = (id: string, name: string): Promise<Project> =>
  request(projectUrl(id), jsonBody("PUT", { name }));

export const deleteProject = (id: string): Promise<void> =>
  request(projectUrl(id), { method: "DELETE" });

export const listKeys = (id: string): Promise<SdkKey[]> => request(`${projectUrl(id)}/keys`);

export const createKey = (id: string, label: string): Promise<SdkKeyCreated> =>
  request(`${projectUrl(id)}/keys`, jsonBody("POST", { label }));

export const revokeKey = (id: string, keyId: string): Promise<SdkKey> =>
  request(`${projectUrl(id)}/keys/${enc(keyId)}`, { method: "DELETE" });

export const listMembers = (id: string): Promise<Members> => request(`${projectUrl(id)}/members`);

export const inviteMember = (id: string, email: string, role: Role): Promise<Members> =>
  request(`${projectUrl(id)}/members`, jsonBody("POST", { email, role }));

export const setMemberRole = (id: string, userId: string, role: Role): Promise<Members> =>
  request(`${projectUrl(id)}/members/${enc(userId)}`, jsonBody("PUT", { role }));

export const removeMember = (id: string, userId: string): Promise<Members> =>
  request(`${projectUrl(id)}/members/${enc(userId)}`, { method: "DELETE" });

export const cancelInvitation = (id: string, email: string): Promise<Members> =>
  request(`${projectUrl(id)}/invitations/${enc(email)}`, { method: "DELETE" });

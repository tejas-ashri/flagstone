export type Role = "admin" | "viewer";

export interface User {
  id: string;
  email: string;
  name: string;
  avatar_url: string | null;
}

export interface Project {
  id: string;
  name: string;
  role: Role;
  flag_count: number;
  member_count: number;
}

export interface Me {
  user: User;
  identities: string[];
  projects: Project[];
}

export interface AuthProviders {
  providers: { id: string; label: string }[];
  dev_login: boolean;
}

export interface SdkKey {
  id: string;
  label: string;
  prefix: string;
  created_at: string;
  last_used_at: string | null;
  revoked_at: string | null;
}

export interface SdkKeyCreated extends SdkKey {
  key: string;
}

export interface Member {
  user: User;
  role: Role;
  created_at: string;
}

export interface Invitation {
  email: string;
  role: Role;
  created_at: string;
}

export interface Members {
  members: Member[];
  invitations: Invitation[];
}

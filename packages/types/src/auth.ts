export type UserRole = "admin" | "manager" | "analyst" | "viewer";

export interface User {
  id: string;
  clerkId: string;
  email: string;
  firstName: string;
  lastName: string;
  role: UserRole;
  orgId: string;
  avatarUrl?: string;
  createdAt: string;
  updatedAt: string;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  type: "investor" | "ally";
  logoUrl?: string;
  createdAt: string;
  updatedAt: string;
}

export interface OrganizationMember {
  userId: string;
  orgId: string;
  role: UserRole;
  joinedAt: string;
}

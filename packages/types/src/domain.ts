export type ProjectStatus =
  | "draft"
  | "under_review"
  | "active"
  | "funded"
  | "completed"
  | "archived";

export interface Project {
  id: string;
  orgId: string;
  name: string;
  description: string;
  status: ProjectStatus;
  sector: string;
  country: string;
  targetAmount: number;
  raisedAmount: number;
  currency: string;
  esgScore?: ESGScore;
  createdAt: string;
  updatedAt: string;
}

export type InvestmentStage =
  | "prospecting"
  | "due_diligence"
  | "negotiation"
  | "committed"
  | "deployed"
  | "exited";

export interface Investment {
  id: string;
  orgId: string;
  projectId: string;
  investorOrgId: string;
  stage: InvestmentStage;
  amount: number;
  currency: string;
  committedAt?: string;
  deployedAt?: string;
  createdAt: string;
  updatedAt: string;
}

export type ESGCategory = "environmental" | "social" | "governance";

export interface ESGScore {
  overall: number;
  environmental: number;
  social: number;
  governance: number;
  lastAssessedAt: string;
}

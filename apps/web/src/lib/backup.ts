"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface PostgresBackupStep {
  status: string;
  s3_key?: string;
  size_mb?: number;
  sha256?: string;
  verified?: boolean;
  reason?: string;
  error?: string;
}

export interface DRCopyStep {
  status: string;
  dr_bucket?: string;
  dr_region?: string;
  size_mb?: number;
  reason?: string;
}

export interface OpenSearchStep {
  status: string;
  snapshot?: string;
  reason?: string;
  error?: string;
}

export interface SecretsStep {
  status: string;
  secret_count?: number;
  s3_key?: string;
  reason?: string;
}

export interface RDSSnapshotsStep {
  status: string;
  snapshot_count?: number;
  latest?: string;
  age_hours?: number;
  reason?: string;
}

export interface S3ReplicationStep {
  status: string;
  buckets?: Record<string, string>;
}

export interface TableAuditStep {
  status: string;
  table_count?: number;
  expected_min?: number;
  reason?: string;
}

export interface BackupStatus {
  overall: string;
  last_run: string | null;
  postgresql: PostgresBackupStep | null;
  dr_copy: DRCopyStep | null;
  opensearch: OpenSearchStep | null;
  secrets_inventory: SecretsStep | null;
  rds_snapshots: RDSSnapshotsStep | null;
  s3_replication: S3ReplicationStep | null;
  table_audit: TableAuditStep | null;
  last_restore_test: string | null;
  restore_test_result: string | null;
}

export function useBackupStatus() {
  return useQuery<BackupStatus>({
    queryKey: ["admin", "backup-status"],
    queryFn: () => api.get("/admin/backup-status").then((r) => r.data),
    staleTime: 5 * 60 * 1000,        // 5 minutes
    refetchInterval: 10 * 60 * 1000, // auto-refresh every 10 minutes
  });
}

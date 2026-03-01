import { BackupStatusPanel } from "@/components/admin/backup-status";

export default function AdminBackupPage() {
  return (
    <div className="max-w-3xl mx-auto py-8 px-4 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-neutral-900">Backup & Recovery</h1>
        <p className="text-sm text-neutral-500 mt-1">
          Real-time backup health across all data stores
        </p>
      </div>
      <BackupStatusPanel />
    </div>
  );
}

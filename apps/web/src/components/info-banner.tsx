import { Info } from "lucide-react";
import { cn } from "@scr/ui";

export function InfoBanner({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex items-start gap-3 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-800",
        className
      )}
    >
      <Info className="mt-0.5 h-4 w-4 shrink-0 text-blue-500" />
      <span>{children}</span>
    </div>
  );
}

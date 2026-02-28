"use client";

interface CertificationBadgeProps {
  certified: boolean;
  tier?: string | null;
  score?: number | null;
  certifiedSince?: string | null;
  size?: "sm" | "md" | "lg";
}

export function CertificationBadge({ certified, tier, score, certifiedSince, size = "md" }: CertificationBadgeProps) {
  if (!certified) return null;

  // Tier styling
  const tierConfig = {
    elite: { label: "Elite", bg: "from-purple-600 to-indigo-600", ring: "ring-purple-400", icon: "💎" },
    premium: { label: "Premium", bg: "from-amber-500 to-yellow-400", ring: "ring-amber-400", icon: "⭐" },
    standard: { label: "Standard", bg: "from-blue-500 to-cyan-500", ring: "ring-blue-400", icon: "✓" },
  };

  const config = tierConfig[tier as keyof typeof tierConfig] ?? tierConfig.standard;

  const sizeClasses = {
    sm: "px-2 py-0.5 text-xs gap-1",
    md: "px-3 py-1 text-sm gap-1.5",
    lg: "px-4 py-2 text-base gap-2",
  };

  return (
    <div
      title={`Investor Ready — ${config.label} tier${score ? ` · Score: ${score}` : ""}${certifiedSince ? ` · Since ${new Date(certifiedSince).toLocaleDateString()}` : ""}`}
      className={`inline-flex items-center rounded-full bg-gradient-to-r ${config.bg} text-white font-semibold ring-2 ${config.ring} ring-offset-1 ${sizeClasses[size]} cursor-default`}
    >
      <span>{config.icon}</span>
      <span>Investor Ready</span>
      {tier !== "standard" && <span className="opacity-80">· {config.label}</span>}
    </div>
  );
}

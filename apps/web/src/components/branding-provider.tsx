"use client";

import { useEffect } from "react";
import { useBranding, hexToHsl } from "@/lib/branding";

export function BrandingProvider({ children }: { children: React.ReactNode }) {
  const { data: branding } = useBranding();

  useEffect(() => {
    if (!branding) return;
    const root = document.documentElement;

    if (branding.primary_color) {
      const { h, s, l } = hexToHsl(branding.primary_color);
      root.style.setProperty("--brand-primary", `${h} ${s}% ${l}%`);
      root.style.setProperty("--color-primary", branding.primary_color);
    }
    if (branding.accent_color) {
      const { h, s, l } = hexToHsl(branding.accent_color);
      root.style.setProperty("--brand-accent", `${h} ${s}% ${l}%`);
    }
    if (branding.font_family) {
      root.style.setProperty("--font-sans", branding.font_family);
    }
    if (branding.company_name) {
      document.title = `${branding.company_name} | SCR Platform`;
    }
  }, [branding]);

  return <>{children}</>;
}

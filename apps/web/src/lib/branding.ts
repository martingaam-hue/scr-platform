import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface BrandingSettings {
  primary_color: string;
  logo_url: string | null;
  company_name: string | null;
  accent_color: string;
  font_family: string;
  org_id?: string;
}

export const defaultBranding: BrandingSettings = {
  primary_color: "#6366f1",
  logo_url: null,
  company_name: null,
  accent_color: "#8b5cf6",
  font_family: "Inter",
};

export function useBranding() {
  return useQuery<BrandingSettings>({
    queryKey: ["branding"],
    queryFn: async () => {
      try {
        const { data } = await api.get("/settings/branding");
        return data;
      } catch {
        return defaultBranding;
      }
    },
    staleTime: 5 * 60 * 1000,
  });
}

export function useUpdateBranding() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (settings: Partial<BrandingSettings>) => {
      const { data } = await api.put("/settings/branding", settings);
      return data as BrandingSettings;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["branding"] }),
  });
}

// Helper: convert hex to HSL CSS variables
export function hexToHsl(hex: string): { h: number; s: number; l: number } {
  const r = parseInt(hex.slice(1, 3), 16) / 255;
  const g = parseInt(hex.slice(3, 5), 16) / 255;
  const b = parseInt(hex.slice(5, 7), 16) / 255;
  const max = Math.max(r, g, b),
    min = Math.min(r, g, b);
  let h = 0,
    s = 0;
  const l = (max + min) / 2;
  if (max !== min) {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    switch (max) {
      case r:
        h = ((g - b) / d + (g < b ? 6 : 0)) / 6;
        break;
      case g:
        h = ((b - r) / d + 2) / 6;
        break;
      case b:
        h = ((r - g) / d + 4) / 6;
        break;
    }
  }
  return { h: Math.round(h * 360), s: Math.round(s * 100), l: Math.round(l * 100) };
}
